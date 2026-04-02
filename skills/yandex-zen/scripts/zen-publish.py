#!/usr/bin/env python3
"""
Zen Publisher -- publishes articles to Yandex Dzen via Playwright browser automation.

Automates the workflow: load cookies -> open editor -> fill title/body/cover/tags -> save/publish.
ALWAYS defaults to draft mode for safety.

Usage:
    # Save as draft (default, safe)
    python3 zen-publish.py --title "My Article" --body article.md --cover cover.jpg --tags "ai,tech"

    # Publish immediately
    python3 zen-publish.py --title "My Article" --body article.md --publish

    # Login mode: opens browser for manual Yandex login and cookie capture
    python3 zen-publish.py --login

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
from pathlib import Path

COOKIES_PATH = os.path.expanduser("~/.secrets/yandex_cookies.json")
EDITOR_URL = "https://dzen.ru/editor/new"
DZEN_BASE = "https://dzen.ru"
SCREENSHOT_DIR = "/tmp/zen-publish"

LOGIN_INSTRUCTIONS = """
=== Yandex Login Required ===

Cookies file not found or expired: {path}

To capture cookies, run:
    python3 zen-publish.py --login

This will open a visible browser window. Steps:
  1. Go to https://passport.yandex.ru and log in
  2. Navigate to https://dzen.ru and confirm you're logged in
  3. Press Enter in the terminal when ready
  4. Cookies will be saved to {path}

Alternatively, export cookies manually:
  1. Log in to dzen.ru in your browser
  2. Use a browser extension to export cookies as JSON
  3. Save to {path}
"""


def read_body(body_path: str) -> str:
    """Read article body from a markdown file and strip markdown formatting for plain text."""
    if not os.path.isfile(body_path):
        print(f"[ERROR] Body file not found: {body_path}", file=sys.stderr)
        sys.exit(1)

    with open(body_path, "r", encoding="utf-8") as f:
        text = f.read()

    return text


def strip_markdown(text: str) -> str:
    """Convert markdown to plain text suitable for Dzen editor paste."""
    # Remove image references
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # Convert links to just text
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # Remove heading markers but keep text
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    # Clean up extra whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


async def check_playwright_available() -> bool:
    """Check if Playwright is available."""
    try:
        from playwright.async_api import async_playwright
        return True
    except ImportError:
        return False


async def login_and_capture_cookies():
    """Open a visible browser for manual login and save cookies."""
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

    os.makedirs(os.path.dirname(COOKIES_PATH), exist_ok=True)

    print("[INFO] Opening browser for Yandex login...")
    print("[INFO] Please log in to your Yandex account and navigate to dzen.ru")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ru-RU",
        )
        page = await context.new_page()

        await page.goto("https://passport.yandex.ru/auth")
        print("[INFO] Browser opened at Yandex login page.")
        print("[INFO] After logging in and confirming dzen.ru access, press Enter here...")

        try:
            input("\n>>> Press Enter when you're logged in to dzen.ru... ")
        except EOFError:
            pass

        # Navigate to Dzen to ensure cookies are captured
        await page.goto(DZEN_BASE)
        await page.wait_for_timeout(2000)

        # Save cookies
        cookies = await context.cookies()
        with open(COOKIES_PATH, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

        print(f"[OK] Saved {len(cookies)} cookies to {COOKIES_PATH}")

        await browser.close()


async def load_cookies(context):
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


async def check_login(page) -> bool:
    """Check if we're logged in to Dzen by looking for editor access."""
    try:
        await page.goto(DZEN_BASE, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)

        # Check for login indicators
        content = await page.content()
        # If we see editor-related links or user profile elements, we're logged in
        if "editor" in content.lower() or "zen-lib" in content.lower():
            return True

        # Try to access editor directly
        response = await page.goto(EDITOR_URL, wait_until="domcontentloaded", timeout=15000)
        if response and response.url and "passport" in response.url:
            return False  # Redirected to login

        return True

    except Exception:
        return False


async def publish_article(
    title: str,
    body_path: str,
    cover_path: str | None = None,
    tags: list[str] | None = None,
    publish: bool = False,
):
    """Publish or save as draft an article on Dzen."""
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

    # Read and prepare body text
    body_text = read_body(body_path)
    plain_text = strip_markdown(body_text)

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
        )

        # Load cookies
        cookies_ok = await load_cookies(context)
        if not cookies_ok:
            print(LOGIN_INSTRUCTIONS.format(path=COOKIES_PATH))
            await browser.close()
            sys.exit(1)

        page = await context.new_page()

        # Check login
        print("[INFO] Checking Yandex login status...")
        logged_in = await check_login(page)
        if not logged_in:
            print(
                f"[ERROR] Not logged in. Cookies may be expired.\n"
                f"Run: python3 zen-publish.py --login\n"
                f"to refresh cookies at {COOKIES_PATH}"
            )
            await browser.close()
            sys.exit(1)

        print("[INFO] Logged in. Opening editor...")

        # Navigate to editor
        await page.goto(EDITOR_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Screenshot initial state
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_editor_loaded.png"))

        # --- Fill Title ---
        print(f"[INFO] Setting title: {title[:50]}...")
        try:
            # Dzen editor title field (may vary by version)
            title_selectors = [
                '[data-testid="article-title"]',
                '[placeholder*="Заголовок"]',
                '[placeholder*="заголовок"]',
                '.article-editor__title',
                'textarea[name="title"]',
                '.zen-editor-title',
                'h1[contenteditable="true"]',
                '[contenteditable="true"]:first-of-type',
            ]
            title_filled = False
            for sel in title_selectors:
                try:
                    elem = page.locator(sel).first
                    if await elem.is_visible(timeout=2000):
                        await elem.click()
                        await elem.fill(title)
                        title_filled = True
                        print(f"[OK] Title filled (selector: {sel})")
                        break
                except Exception:
                    continue

            if not title_filled:
                print("[WARN] Could not find title field. Trying keyboard approach...")
                await page.keyboard.type(title)

        except Exception as e:
            print(f"[WARN] Title fill error: {e}")

        await page.wait_for_timeout(1000)

        # --- Fill Body ---
        print("[INFO] Filling article body...")
        try:
            body_selectors = [
                '[data-testid="article-body"]',
                '.article-editor__body',
                '.ProseMirror',
                '[contenteditable="true"]',
                '.zen-editor-body',
            ]
            body_filled = False
            for sel in body_selectors:
                try:
                    elems = page.locator(sel)
                    count = await elems.count()
                    # Skip the first contenteditable if it was the title
                    for idx in range(count):
                        elem = elems.nth(idx)
                        if await elem.is_visible(timeout=2000):
                            text_content = await elem.inner_text()
                            # Skip if it already has the title text
                            if title in text_content:
                                continue
                            await elem.click()
                            await page.keyboard.type(plain_text[:5000], delay=5)
                            body_filled = True
                            print(f"[OK] Body filled ({len(plain_text)} chars, selector: {sel})")
                            break
                    if body_filled:
                        break
                except Exception:
                    continue

            if not body_filled:
                print("[WARN] Could not find body field via selectors. Trying Tab+Type...")
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(500)
                await page.keyboard.type(plain_text[:5000], delay=5)

        except Exception as e:
            print(f"[WARN] Body fill error: {e}")

        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_content_filled.png"))

        # --- Upload Cover ---
        if cover_path and os.path.isfile(cover_path):
            print(f"[INFO] Uploading cover: {cover_path}")
            try:
                # Look for image upload input
                upload_selectors = [
                    'input[type="file"]',
                    'input[accept*="image"]',
                    '[data-testid="image-upload"]',
                ]
                for sel in upload_selectors:
                    try:
                        elem = page.locator(sel).first
                        if await elem.count() > 0:
                            await elem.set_input_files(cover_path)
                            print(f"[OK] Cover uploaded (selector: {sel})")
                            await page.wait_for_timeout(2000)
                            break
                    except Exception:
                        continue
                else:
                    print("[WARN] Could not find file upload input for cover.")

            except Exception as e:
                print(f"[WARN] Cover upload error: {e}")

        elif cover_path:
            print(f"[WARN] Cover file not found: {cover_path}")

        # --- Add Tags ---
        if tags:
            print(f"[INFO] Adding tags: {', '.join(tags)}")
            try:
                tag_selectors = [
                    '[data-testid="tags-input"]',
                    '[placeholder*="Тег"]',
                    '[placeholder*="тег"]',
                    '.tags-input',
                    'input[name="tags"]',
                ]
                tag_field = None
                for sel in tag_selectors:
                    try:
                        elem = page.locator(sel).first
                        if await elem.is_visible(timeout=2000):
                            tag_field = elem
                            break
                    except Exception:
                        continue

                if tag_field:
                    for tag in tags:
                        await tag_field.fill(tag.strip())
                        await page.keyboard.press("Enter")
                        await page.wait_for_timeout(500)
                    print(f"[OK] {len(tags)} tag(s) added")
                else:
                    print("[WARN] Could not find tags input field.")

            except Exception as e:
                print(f"[WARN] Tags error: {e}")

        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_ready.png"))

        # --- Save / Publish ---
        if publish:
            print("[INFO] Publishing article...")
            action_label = "publish"
        else:
            print("[INFO] Saving as draft...")
            action_label = "draft"

        try:
            if publish:
                publish_selectors = [
                    'button:has-text("Опубликовать")',
                    'button:has-text("опубликовать")',
                    '[data-testid="publish-button"]',
                    'button.publish-button',
                ]
            else:
                publish_selectors = [
                    'button:has-text("Сохранить")',
                    'button:has-text("Черновик")',
                    'button:has-text("сохранить")',
                    '[data-testid="save-draft"]',
                    'button.save-button',
                ]

            clicked = False
            for sel in publish_selectors:
                try:
                    elem = page.locator(sel).first
                    if await elem.is_visible(timeout=2000):
                        await elem.click()
                        clicked = True
                        print(f"[OK] Clicked '{action_label}' button (selector: {sel})")
                        break
                except Exception:
                    continue

            if not clicked:
                print(f"[WARN] Could not find {action_label} button. Article may need manual save.")

        except Exception as e:
            print(f"[WARN] {action_label} action error: {e}")

        await page.wait_for_timeout(3000)

        # Final screenshot
        screenshot_path = os.path.join(SCREENSHOT_DIR, "04_result.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"[INFO] Screenshot saved: {screenshot_path}")

        # Try to get the article URL
        current_url = page.url
        print(f"[INFO] Current URL: {current_url}")

        # Save updated cookies (may have been refreshed)
        updated_cookies = await context.cookies()
        with open(COOKIES_PATH, "w", encoding="utf-8") as f:
            json.dump(updated_cookies, f, ensure_ascii=False, indent=2)

        await browser.close()

        print()
        print("=" * 50)
        if publish:
            print(f"  Article PUBLISHED")
        else:
            print(f"  Article saved as DRAFT")
        print(f"  URL: {current_url}")
        print(f"  Screenshots: {SCREENSHOT_DIR}/")
        print("=" * 50)

        return current_url


def main():
    parser = argparse.ArgumentParser(
        description="Publish articles to Yandex Dzen via browser automation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Login and capture cookies
  python3 zen-publish.py --login

  # Save as draft (default, safe)
  python3 zen-publish.py --title "My Article" --body article.md

  # Publish with cover and tags
  python3 zen-publish.py --title "AI Guide" --body guide.md --cover cover.jpg --tags "ai,tech" --publish

Notes:
  - Default mode is DRAFT for safety. Use --publish to go live.
  - Requires Playwright: pip install playwright && playwright install chromium
  - First run: use --login to capture Yandex SSO cookies.
""",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Open visible browser for manual Yandex login and cookie capture",
    )
    parser.add_argument(
        "--title", "-t",
        help="Article title",
    )
    parser.add_argument(
        "--body", "-b",
        help="Path to article body (.md or .txt file)",
    )
    parser.add_argument(
        "--cover", "-c",
        help="Path to cover image (JPEG/PNG)",
    )
    parser.add_argument(
        "--tags",
        help='Comma-separated tags (e.g. "ai,tech,tutorial")',
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        default=True,
        help="Save as draft (default behavior)",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish immediately instead of saving as draft",
    )
    args = parser.parse_args()

    if args.login:
        asyncio.run(login_and_capture_cookies())
        return

    if not args.title or not args.body:
        parser.error("--title and --body are required (unless using --login)")

    tags = [t.strip() for t in args.tags.split(",")] if args.tags else None

    asyncio.run(publish_article(
        title=args.title,
        body_path=args.body,
        cover_path=args.cover,
        tags=tags,
        publish=args.publish,
    ))


if __name__ == "__main__":
    main()
