#!/usr/bin/env python3
"""
Zen Analytics -- scrapes channel analytics from Dzen Studio via Playwright.

Extracts: subscribers, views, top articles, CTR, read-through rate.
Outputs JSON + formatted Markdown report.

Usage:
    python3 zen-analytics.py --channel "https://dzen.ru/my_channel"
    python3 zen-analytics.py --channel "https://dzen.ru/my_channel" --period 30
    python3 zen-analytics.py --channel "https://dzen.ru/my_channel" --period 90 --output /tmp/report.md
    python3 zen-analytics.py --channel "https://dzen.ru/my_channel" --json

Requirements:
    pip install playwright
    playwright install chromium
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime

COOKIES_PATH = os.path.expanduser("~/.secrets/yandex_cookies.json")
STUDIO_BASE = "https://dzen.ru/profile/editor/statistics"
SCREENSHOT_DIR = "/tmp/zen-analytics"

LOGIN_INSTRUCTIONS = """
=== Yandex Login Required ===

Cookies file not found or expired: {path}

To capture cookies, run:
    python3 zen-publish.py --login

This will open a visible browser window for manual Yandex login.
After logging in, cookies will be saved to {path}.

Alternatively, export cookies manually from your browser.
"""

# ---------------------------------------------------------------------------
# Benchmarks from analytics-guide.md
# ---------------------------------------------------------------------------
CTR_BENCHMARKS = {
    "excellent": (15, 100, "15-30%+ -- excellent for Dzen"),
    "good":     (10, 15, "10-15% -- good for most niches"),
    "normal":   (6, 10, "6-10% -- acceptable"),
    "low":      (0, 6, "<6% -- needs improvement: rework titles & covers"),
}

READTHROUGH_BENCHMARKS = {
    "excellent": (80, 100, "80%+ -- platform target"),
    "good":     (60, 80, "60-80% -- solid performance"),
    "average":  (40, 60, "40-60% -- review structure, cut filler"),
    "low":      (0, 40, "<40% -- critical: analyze heatmaps, shorten text"),
}


def assess_ctr(ctr: float) -> str:
    """Return benchmark assessment for CTR value."""
    for level, (low, high, desc) in CTR_BENCHMARKS.items():
        if low <= ctr < high or (level == "excellent" and ctr >= low):
            return f"{level.upper()}: {desc}"
    return "unknown"


def assess_readthrough(rate: float) -> str:
    """Return benchmark assessment for read-through rate."""
    for level, (low, high, desc) in READTHROUGH_BENCHMARKS.items():
        if low <= rate < high or (level == "excellent" and rate >= low):
            return f"{level.upper()}: {desc}"
    return "unknown"


async def load_cookies(context) -> bool:
    """Load cookies from file into browser context."""
    if not os.path.isfile(COOKIES_PATH):
        return False

    try:
        with open(COOKIES_PATH, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        if not isinstance(cookies, list) or len(cookies) == 0:
            return False

        await context.add_cookies(cookies)
        return True

    except (json.JSONDecodeError, Exception) as e:
        print(f"[WARN] Failed to load cookies: {e}", file=sys.stderr)
        return False


def parse_number(text: str) -> float:
    """Parse a number from text that may contain Russian formatting (spaces, commas)."""
    if not text:
        return 0.0
    # Remove spaces and non-breaking spaces
    cleaned = text.replace("\u00a0", "").replace("\u2009", "").replace(" ", "")
    # Handle Russian comma as decimal separator
    cleaned = cleaned.replace(",", ".")
    # Remove everything except digits, dots, minus
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_percentage(text: str) -> float:
    """Parse a percentage value from text."""
    if not text:
        return 0.0
    cleaned = text.replace("%", "").strip()
    return parse_number(cleaned)


async def scrape_analytics(channel_url: str, period: int = 7) -> dict:
    """
    Scrape analytics from Dzen Studio.

    Returns a dict with:
        subscribers, total_views, avg_ctr, avg_readthrough,
        top_articles, period, channel_url, scraped_at
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print(
            "[ERROR] Playwright is not installed.\n"
            "Install it with:\n"
            "  pip install playwright\n"
            "  playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.path.isfile(COOKIES_PATH):
        print(LOGIN_INSTRUCTIONS.format(path=COOKIES_PATH))
        sys.exit(1)

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    data = {
        "channel_url": channel_url,
        "period_days": period,
        "scraped_at": datetime.now().isoformat(),
        "subscribers": 0,
        "total_views": 0,
        "avg_ctr": 0.0,
        "avg_readthrough": 0.0,
        "top_articles": [],
        "raw_metrics": {},
        "errors": [],
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
        )

        cookies_ok = await load_cookies(context)
        if not cookies_ok:
            print(LOGIN_INSTRUCTIONS.format(path=COOKIES_PATH))
            await browser.close()
            sys.exit(1)

        page = await context.new_page()

        # --- Navigate to Studio ---
        print(f"[INFO] Opening Dzen Studio analytics (period: {period} days)...")

        try:
            # Try the statistics page directly
            stats_url = STUDIO_BASE
            await page.goto(stats_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            # Check if we got redirected to login
            if "passport" in page.url:
                data["errors"].append("Session expired -- redirected to login page")
                print(
                    f"[ERROR] Not logged in. Cookies expired.\n"
                    f"Run: python3 zen-publish.py --login"
                )
                await browser.close()
                return data

            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_stats_page.png"))
            print(f"[OK] Analytics page loaded: {page.url}")

        except Exception as e:
            data["errors"].append(f"Failed to load analytics page: {e}")
            print(f"[ERROR] Could not load analytics page: {e}", file=sys.stderr)
            await browser.close()
            return data

        # --- Select Period ---
        print(f"[INFO] Setting period to {period} days...")
        try:
            period_selectors = {
                7: ['button:has-text("7 дней")', 'button:has-text("Неделя")', '[data-period="7"]'],
                30: ['button:has-text("30 дней")', 'button:has-text("Месяц")', '[data-period="30"]'],
                90: ['button:has-text("90 дней")', 'button:has-text("3 месяца")', '[data-period="90"]'],
            }
            selectors = period_selectors.get(period, period_selectors[7])

            for sel in selectors:
                try:
                    elem = page.locator(sel).first
                    if await elem.is_visible(timeout=2000):
                        await elem.click()
                        await page.wait_for_timeout(2000)
                        print(f"[OK] Period set (selector: {sel})")
                        break
                except Exception:
                    continue

        except Exception as e:
            data["errors"].append(f"Could not set period: {e}")
            print(f"[WARN] Could not set period: {e}")

        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_period_set.png"))

        # --- Extract Subscribers ---
        print("[INFO] Extracting metrics...")
        try:
            sub_selectors = [
                '[data-testid="subscribers-count"]',
                '.subscribers-count',
                'text=/подписчик/i',
            ]
            for sel in sub_selectors:
                try:
                    elem = page.locator(sel).first
                    if await elem.is_visible(timeout=2000):
                        text = await elem.inner_text()
                        data["subscribers"] = int(parse_number(text))
                        print(f"[OK] Subscribers: {data['subscribers']}")
                        break
                except Exception:
                    continue

        except Exception as e:
            data["errors"].append(f"Could not extract subscribers: {e}")

        # --- Extract Views ---
        try:
            view_selectors = [
                '[data-testid="total-views"]',
                '.total-views',
                'text=/показ/i',
                'text=/просмотр/i',
            ]
            for sel in view_selectors:
                try:
                    elem = page.locator(sel).first
                    if await elem.is_visible(timeout=2000):
                        text = await elem.inner_text()
                        data["total_views"] = int(parse_number(text))
                        print(f"[OK] Total views: {data['total_views']}")
                        break
                except Exception:
                    continue

        except Exception as e:
            data["errors"].append(f"Could not extract views: {e}")

        # --- Extract CTR ---
        try:
            ctr_selectors = [
                '[data-testid="avg-ctr"]',
                '.avg-ctr',
                'text=/CTR/i',
            ]
            for sel in ctr_selectors:
                try:
                    elem = page.locator(sel).first
                    if await elem.is_visible(timeout=2000):
                        text = await elem.inner_text()
                        data["avg_ctr"] = parse_percentage(text)
                        print(f"[OK] Avg CTR: {data['avg_ctr']}%")
                        break
                except Exception:
                    continue

        except Exception as e:
            data["errors"].append(f"Could not extract CTR: {e}")

        # --- Extract Read-Through Rate ---
        try:
            rt_selectors = [
                '[data-testid="readthrough-rate"]',
                '.readthrough-rate',
                'text=/дочит/i',
            ]
            for sel in rt_selectors:
                try:
                    elem = page.locator(sel).first
                    if await elem.is_visible(timeout=2000):
                        text = await elem.inner_text()
                        data["avg_readthrough"] = parse_percentage(text)
                        print(f"[OK] Avg Read-through: {data['avg_readthrough']}%")
                        break
                except Exception:
                    continue

        except Exception as e:
            data["errors"].append(f"Could not extract read-through rate: {e}")

        # --- Extract Top Articles ---
        print("[INFO] Looking for top articles...")
        try:
            # Try to find article list/table
            article_selectors = [
                '.publication-stat-row',
                '.publication-item',
                '[data-testid="publication-row"]',
                'table tbody tr',
                '.statistics-table-row',
            ]

            for sel in article_selectors:
                try:
                    rows = page.locator(sel)
                    count = await rows.count()
                    if count > 0:
                        print(f"[OK] Found {count} article rows (selector: {sel})")
                        for i in range(min(count, 10)):  # Top 10
                            row = rows.nth(i)
                            try:
                                row_text = await row.inner_text()
                                parts = row_text.strip().split("\n")
                                article_data = {
                                    "rank": i + 1,
                                    "title": parts[0] if parts else "Unknown",
                                    "raw_text": row_text.strip()[:200],
                                }
                                # Try to extract numbers from the row
                                numbers = re.findall(r"[\d\s]+", row_text)
                                if len(numbers) >= 1:
                                    article_data["views"] = int(parse_number(numbers[-1]))
                                data["top_articles"].append(article_data)
                            except Exception:
                                continue
                        break
                except Exception:
                    continue

            if not data["top_articles"]:
                print("[WARN] Could not extract individual article stats.")

        except Exception as e:
            data["errors"].append(f"Could not extract top articles: {e}")

        # --- Try to extract any visible metrics from page text ---
        try:
            page_text = await page.inner_text("body")

            # Extract any numbers near known metric labels
            metrics_patterns = {
                "shows": r"(?:показ[оыв]*|impressions?)[\s:]*?([\d\s,.]+)",
                "views": r"(?:просмотр[оыов]*|views?)[\s:]*?([\d\s,.]+)",
                "subscribers": r"(?:подписчик[оыов]*|subscribers?)[\s:]*?([\d\s,.]+)",
                "read_pct": r"(?:дочит[а-я]*|read-?through)[\s:]*?([\d,.]+)\s*%",
                "ctr_pct": r"CTR[\s:]*?([\d,.]+)\s*%",
            }

            for key, pattern in metrics_patterns.items():
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    val = match.group(1)
                    data["raw_metrics"][key] = val.strip()
                    # Fill in main data if missing
                    if key == "subscribers" and data["subscribers"] == 0:
                        data["subscribers"] = int(parse_number(val))
                    elif key == "views" and data["total_views"] == 0:
                        data["total_views"] = int(parse_number(val))
                    elif key == "ctr_pct" and data["avg_ctr"] == 0:
                        data["avg_ctr"] = parse_percentage(val)
                    elif key == "read_pct" and data["avg_readthrough"] == 0:
                        data["avg_readthrough"] = parse_percentage(val)

        except Exception:
            pass

        # Final screenshot
        await page.screenshot(
            path=os.path.join(SCREENSHOT_DIR, "03_final.png"),
            full_page=True,
        )

        # Save updated cookies
        updated_cookies = await context.cookies()
        with open(COOKIES_PATH, "w", encoding="utf-8") as f:
            json.dump(updated_cookies, f, ensure_ascii=False, indent=2)

        await browser.close()

    return data


def format_markdown_report(data: dict) -> str:
    """Format analytics data as a Markdown report."""
    lines = []
    lines.append(f"# Dzen Channel Analytics Report")
    lines.append("")
    lines.append(f"- **Channel:** {data['channel_url']}")
    lines.append(f"- **Period:** last {data['period_days']} days")
    lines.append(f"- **Scraped:** {data['scraped_at']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Key Metrics
    lines.append("## Key Metrics")
    lines.append("")
    lines.append(f"| Metric | Value | Assessment |")
    lines.append(f"|--------|-------|------------|")

    subs = data.get("subscribers", 0)
    views = data.get("total_views", 0)
    ctr = data.get("avg_ctr", 0.0)
    rt = data.get("avg_readthrough", 0.0)

    lines.append(f"| Subscribers | {subs:,} | -- |")
    lines.append(f"| Total Views | {views:,} | -- |")
    lines.append(f"| Avg CTR | {ctr:.1f}% | {assess_ctr(ctr)} |")
    lines.append(f"| Read-Through | {rt:.1f}% | {assess_readthrough(rt)} |")
    lines.append("")

    # Top Articles
    if data.get("top_articles"):
        lines.append("## Top Articles by Views")
        lines.append("")
        lines.append("| # | Title | Views |")
        lines.append("|---|-------|-------|")
        for article in data["top_articles"]:
            title = article.get("title", "N/A")[:60]
            article_views = article.get("views", "N/A")
            lines.append(f"| {article['rank']} | {title} | {article_views} |")
        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")

    if ctr > 0:
        if ctr < 6:
            lines.append("- **CTR is low.** Rework your titles and covers. Use A/B testing (3 covers + 5 titles).")
        elif ctr < 10:
            lines.append("- **CTR is acceptable.** Test different cover styles and title formats to improve.")
        else:
            lines.append("- **CTR is good.** Maintain quality of titles and covers.")

    if rt > 0:
        if rt < 40:
            lines.append("- **Read-through is critical.** Shorten articles, improve structure, add subheadings and images.")
        elif rt < 60:
            lines.append("- **Read-through needs work.** Review structure, cut filler content, use heatmaps (Metrika).")
        elif rt < 80:
            lines.append("- **Read-through is solid.** Fine-tune engagement with better hooks and visuals.")
        else:
            lines.append("- **Read-through is excellent.** Keep up the content quality.")

    if views == 0 and subs == 0 and ctr == 0:
        lines.append("- **No data extracted.** The Dzen Studio layout may have changed. Check screenshots in " + SCREENSHOT_DIR)

    lines.append("")

    # Errors
    if data.get("errors"):
        lines.append("## Errors During Scraping")
        lines.append("")
        for err in data["errors"]:
            lines.append(f"- {err}")
        lines.append("")

    lines.append("---")
    lines.append(f"*Screenshots saved to `{SCREENSHOT_DIR}/`*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Scrape channel analytics from Dzen Studio.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 zen-analytics.py --channel "https://dzen.ru/my_channel"
  python3 zen-analytics.py --channel "https://dzen.ru/my_channel" --period 30
  python3 zen-analytics.py --channel "https://dzen.ru/my_channel" --period 90 --output report.md
  python3 zen-analytics.py --channel "https://dzen.ru/my_channel" --json

Notes:
  - Requires Playwright: pip install playwright && playwright install chromium
  - Requires Yandex login cookies. Run: python3 zen-publish.py --login
  - Dzen Studio UI may change; selectors are best-effort.
  - Screenshots are saved to /tmp/zen-analytics/ for debugging.
""",
    )
    parser.add_argument(
        "--channel", "-c",
        required=True,
        help="Dzen channel URL (e.g. https://dzen.ru/my_channel)",
    )
    parser.add_argument(
        "--period", "-p",
        type=int,
        choices=[7, 30, 90],
        default=7,
        help="Analytics period in days (default: 7)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path for Markdown report (default: stdout)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON data instead of Markdown report",
    )
    args = parser.parse_args()

    data = asyncio.run(scrape_analytics(args.channel, args.period))

    if args.json:
        output = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        output = format_markdown_report(data)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\n[OK] Report saved to: {args.output}")
        print(f"[INFO] Screenshots: {SCREENSHOT_DIR}/")
    else:
        print(output)


if __name__ == "__main__":
    main()
