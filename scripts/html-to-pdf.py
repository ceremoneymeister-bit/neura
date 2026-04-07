#!/usr/bin/env python3
"""HTML → PDF renderer via Playwright (Chromium).

Universal document generator for all Neura capsules and skills.
Renders any HTML file or string into a pixel-perfect A4 PDF
with full CSS support (flexbox, grid, gradients, custom fonts, @page).

Usage:
    # From HTML file
    python3 html-to-pdf.py input.html -o output.pdf

    # From stdin (pipe)
    echo "<h1>Hello</h1>" | python3 html-to-pdf.py -o output.pdf

    # From Markdown file (auto-converts via built-in MD→HTML)
    python3 html-to-pdf.py document.md -o output.pdf

    # With template (wraps content in styled HTML)
    python3 html-to-pdf.py content.html -o output.pdf --template report

    # Landscape, custom margins
    python3 html-to-pdf.py input.html -o output.pdf --landscape --margin 10

    # Generate from Python (importable)
    from html_to_pdf import render_pdf
    render_pdf("<h1>Hello</h1>", "/tmp/out.pdf")

Templates:
    report   — business report (neutral, serif headings)
    proposal — sales proposal (gradient header, cards)
    invoice  — invoice/receipt (clean, tabular)
    minimal  — no header/footer, clean body
    dark     — dark theme with light text

Advantages over WeasyPrint/wkhtmltopdf:
    - Full modern CSS (flexbox, grid, clamp(), custom properties)
    - JavaScript execution (charts, dynamic content)
    - Web fonts (@import Google Fonts works)
    - Print media queries respected
    - Same render engine as Chrome/Edge
    - Already installed (Playwright + Chromium on server)
"""
import argparse
import asyncio
import os
import re
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Markdown → HTML (lightweight, no external deps)
# ---------------------------------------------------------------------------

def md_to_html(md_text: str) -> str:
    """Convert basic Markdown to HTML (headers, bold, italic, lists, tables, code, links)."""
    lines = md_text.split("\n")
    html_parts = []
    in_code_block = False
    in_list = False
    in_table = False
    table_rows = []

    for line in lines:
        # Code blocks
        if line.strip().startswith("```"):
            if in_code_block:
                html_parts.append("</code></pre>")
                in_code_block = False
            else:
                lang = line.strip()[3:].strip()
                html_parts.append(f'<pre><code class="language-{lang}">')
                in_code_block = True
            continue
        if in_code_block:
            html_parts.append(line.replace("&", "&amp;").replace("<", "&lt;"))
            continue

        stripped = line.strip()

        # Tables
        if "|" in stripped and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if all(re.match(r"^[-:]+$", c) for c in cells):
                continue  # separator row
            if not in_table:
                in_table = True
                table_rows = []
            table_rows.append(cells)
            continue
        elif in_table:
            # Emit table
            html_parts.append("<table>")
            for i, row in enumerate(table_rows):
                tag = "th" if i == 0 else "td"
                cells_html = "".join(f"<{tag}>{c}</{tag}>" for c in row)
                html_parts.append(f"<tr>{cells_html}</tr>")
            html_parts.append("</table>")
            in_table = False
            table_rows = []

        # Empty line
        if not stripped:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append("")
            continue

        # Headers
        hm = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if hm:
            level = len(hm.group(1))
            text = _inline_md(hm.group(2))
            html_parts.append(f"<h{level}>{text}</h{level}>")
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}$", stripped):
            html_parts.append("<hr>")
            continue

        # Blockquote
        bq = re.match(r"^>\s*(.*)$", stripped)
        if bq:
            content = _inline_md(bq.group(1))
            html_parts.append(f"<blockquote>{content}</blockquote>")
            continue

        # List items
        lm = re.match(r"^[-*+]\s+(.+)$", stripped)
        if lm:
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{_inline_md(lm.group(1))}</li>")
            continue

        # Numbered list
        nm = re.match(r"^\d+\.\s+(.+)$", stripped)
        if nm:
            if not in_list:
                html_parts.append("<ol>")
                in_list = True
            html_parts.append(f"<li>{_inline_md(nm.group(1))}</li>")
            continue

        # Paragraph
        if in_list:
            html_parts.append("</ul>")
            in_list = False
        html_parts.append(f"<p>{_inline_md(stripped)}</p>")

    # Close open elements
    if in_list:
        html_parts.append("</ul>")
    if in_table and table_rows:
        html_parts.append("<table>")
        for i, row in enumerate(table_rows):
            tag = "th" if i == 0 else "td"
            cells_html = "".join(f"<{tag}>{c}</{tag}>" for c in row)
            html_parts.append(f"<tr>{cells_html}</tr>")
        html_parts.append("</table>")

    return "\n".join(html_parts)


def _inline_md(text: str) -> str:
    """Process inline Markdown: bold, italic, code, links, images."""
    # Images
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', text)
    # Links
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Inline code
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_PAGE_BREAK_CSS = """
/* Page break protection — prevents elements from being cut across pages */
h1, h2, h3, h4 {{ break-after: avoid; page-break-after: avoid; }}
table, pre, blockquote, img {{ break-inside: avoid; page-break-inside: avoid; }}
.card, .intro, .price-box, .highlight-box, .highlight,
.columns, .cta, .col, .tariff, .note, .steps,
.check-list {{ break-inside: avoid; page-break-inside: avoid; }}
tr {{ break-inside: avoid; page-break-inside: avoid; }}
thead {{ display: table-header-group; }}  /* repeat table headers on new pages */
ul, ol {{ break-inside: avoid; page-break-inside: avoid; }}
/* Orphan/widow protection */
p {{ orphans: 3; widows: 3; }}
/* Section spacing — ensure headings stay with their content */
h2 + *, h3 + * {{ break-before: avoid; page-break-before: avoid; }}
"""

TEMPLATES = {
    "minimal": """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: {margin}mm; }}
body {{ font-family: 'DejaVu Sans', system-ui, sans-serif; color: #1a1a2e;
       line-height: 1.7; font-size: 12px; }}
h1 {{ font-size: 24px; margin-bottom: 8px; }}
h2 {{ font-size: 18px; color: #333; margin-top: 24px; border-bottom: 1px solid #eee; padding-bottom: 6px; }}
h3 {{ font-size: 14px; color: #555; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
th {{ background: #f5f5f5; padding: 10px; text-align: left; font-size: 11px; border-bottom: 2px solid #ddd; }}
td {{ padding: 8px 10px; border-bottom: 1px solid #f0f0f0; font-size: 12px; }}
code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; font-size: 11px; }}
pre {{ background: #f8f8f8; padding: 16px; border-radius: 8px; overflow-x: auto; }}
pre code {{ background: none; padding: 0; }}
ul, ol {{ padding-left: 24px; }}
li {{ margin: 4px 0; }}
blockquote {{ border-left: 3px solid #ddd; margin: 16px 0; padding: 8px 16px; color: #666; }}
img {{ max-width: 100%; height: auto; }}
hr {{ border: none; height: 1px; background: #eee; margin: 24px 0; }}
""" + _PAGE_BREAK_CSS + """
</style></head><body>{content}</body></html>""",

    "report": """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@page {{
    size: A4;
    margin: 40px 0 60px 0;  /* top padding for content on page 2+, bottom for footer */
}}
@page :first {{
    margin-top: 0;  /* first page: header is full-bleed */
}}
body {{ font-family: 'DejaVu Sans', system-ui, sans-serif; color: #2c3e50; line-height: 1.7; font-size: 12px; margin: 0; }}
.header {{ background: linear-gradient(135deg, {dark} 0%, {brand} 100%); color: white; padding: 40px 50px 30px; }}
.header h1 {{ font-size: 26px; margin: 0 0 6px; }}
.header .sub {{ opacity: 0.8; font-size: 13px; }}
.body {{ padding: 30px 50px 20px; }}
h2 {{ color: {brand}; font-size: 17px; margin-top: 28px; padding-bottom: 6px; border-bottom: 2px solid {brand}; }}
h3 {{ font-size: 14px; color: #34495e; }}
table {{ width: 100%; border-collapse: separate; border-spacing: 0; border-radius: 8px; overflow: hidden; margin: 14px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
thead tr {{ background: linear-gradient(135deg, {brand}, {dark}); }}
th {{ color: white; padding: 12px 14px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }}
td {{ padding: 10px 14px; border-bottom: 1px solid #f0f0f0; font-size: 12px; }}
tbody tr:nth-child(even) {{ background: #fafafa; }}
.card {{ background: #f8f7ff; border-left: 4px solid {brand}; padding: 16px 20px; border-radius: 0 10px 10px 0; margin: 14px 0; }}
ul {{ list-style: none; padding: 0; }}
ul li {{ padding: 8px 0 8px 28px; position: relative; border-bottom: 1px solid #f5f5f5; }}
ul li::before {{ content: "\\2713"; position: absolute; left: 4px; color: {accent}; font-weight: bold; }}
code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; font-size: 11px; }}
pre {{ background: #2d2d2d; color: #f8f8f2; padding: 16px; border-radius: 8px; }}
pre code {{ background: none; color: inherit; }}
blockquote {{ border-left: 3px solid {accent}; padding: 12px 20px; color: #555; background: #f9fffe; border-radius: 0 6px 6px 0; margin: 16px 0; }}
/* Footer: fixed to bottom of EVERY page */
.footer {{
    background: {dark}; color: white; padding: 16px 50px; font-size: 10px;
    display: flex; justify-content: space-between;
    position: fixed; bottom: 0; left: 0; right: 0;
}}
img {{ max-width: 100%; }}
hr {{ border: none; height: 1px; background: linear-gradient(90deg, transparent, {brand}40, transparent); margin: 24px 0; }}
""" + _PAGE_BREAK_CSS + """
</style></head><body>
<div class="header"><h1>{title}</h1><div class="sub">{subtitle}</div></div>
<div class="body">{content}</div>
<div class="footer"><div>{author}</div><div>{date}</div></div>
</body></html>""",

    "proposal": """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@page {{
    size: A4;
    margin: 40px 0 60px 0;
}}
@page :first {{
    margin-top: 0;
}}
body {{ font-family: 'DejaVu Sans', system-ui, sans-serif; color: #1a1a2e; line-height: 1.7; font-size: 12px; margin: 0; }}
.hero {{ background: linear-gradient(135deg, {dark} 0%, {brand} 50%, {accent} 100%); color: white; padding: 60px; }}
.hero h1 {{ font-size: 32px; margin: 0 0 8px; letter-spacing: -0.5px; }}
.hero .sub {{ font-size: 15px; opacity: 0.85; }}
.hero .date {{ font-size: 10px; opacity: 0.5; margin-top: 24px; text-transform: uppercase; letter-spacing: 1px; }}
.body {{ padding: 40px 60px 20px; }}
h2 {{ color: {brand}; font-size: 18px; margin-top: 30px; }}
.highlight {{ background: linear-gradient(135deg, {brand}, {dark}); color: white; padding: 30px; border-radius: 16px; margin: 20px 0; text-align: center; }}
.highlight .value {{ font-size: 36px; font-weight: bold; }}
.highlight .label {{ font-size: 14px; opacity: 0.85; margin-top: 6px; }}
.columns {{ display: flex; gap: 16px; margin: 16px 0; }}
.col {{ flex: 1; background: #f9f9fd; padding: 20px; border-radius: 12px; border-top: 3px solid {brand}; }}
.col h3 {{ margin: 0 0 8px; color: {brand}; font-size: 14px; }}
.col p {{ margin: 0; font-size: 11px; color: #555; }}
table {{ width: 100%; border-collapse: separate; border-spacing: 0; border-radius: 12px; overflow: hidden; margin: 16px 0; }}
thead tr {{ background: linear-gradient(135deg, {brand}, {dark}); }}
th {{ color: white; padding: 14px 16px; text-align: left; font-size: 11px; text-transform: uppercase; }}
td {{ padding: 12px 16px; border-bottom: 1px solid #f0f0f0; }}
tbody tr:nth-child(even) {{ background: #fafafe; }}
ul {{ list-style: none; padding: 0; }}
ul li {{ padding: 10px 0 10px 30px; position: relative; border-bottom: 1px solid #f0f0f0; }}
ul li::before {{ content: "\\2713"; position: absolute; left: 4px; color: {accent}; font-weight: bold; font-size: 14px; }}
blockquote {{ border-left: 4px solid {accent}; padding: 14px 20px; color: #555; background: #f8fffe; border-radius: 0 8px 8px 0; margin: 16px 0; font-style: italic; }}
code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }}
pre {{ background: #1e1e2e; color: #cdd6f4; padding: 16px; border-radius: 8px; }}
pre code {{ background: none; color: inherit; }}
img {{ max-width: 100%; }}
hr {{ border: none; height: 1px; background: linear-gradient(90deg, transparent, {brand}40, transparent); margin: 28px 0; }}
.footer {{
    background: {dark}; color: white; padding: 16px 60px; font-size: 11px;
    display: flex; justify-content: space-between;
    position: fixed; bottom: 0; left: 0; right: 0;
}}
""" + _PAGE_BREAK_CSS + """
</style></head><body>
<div class="hero"><h1>{title}</h1><div class="sub">{subtitle}</div><div class="date">{date}</div></div>
<div class="body">{content}</div>
<div class="footer"><div>{author}</div><div>{date}</div></div>
</body></html>""",

    "invoice": """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: {margin}mm; }}
body {{ font-family: 'DejaVu Sans', system-ui, sans-serif; color: #333; font-size: 12px; line-height: 1.6; }}
.header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid {brand}; }}
.header h1 {{ font-size: 28px; color: {brand}; margin: 0; }}
.header .info {{ text-align: right; font-size: 11px; color: #666; }}
h2 {{ font-size: 14px; color: {brand}; text-transform: uppercase; letter-spacing: 1px; margin-top: 24px; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
th {{ background: {brand}; color: white; padding: 10px 12px; text-align: left; font-size: 11px; }}
td {{ padding: 10px 12px; border-bottom: 1px solid #eee; }}
.total {{ font-size: 18px; font-weight: bold; text-align: right; margin-top: 16px; color: {brand}; }}
code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }}
img {{ max-width: 100%; }}
""" + _PAGE_BREAK_CSS + """
</style></head><body>
<div class="header"><div><h1>{title}</h1><p>{subtitle}</p></div><div class="info">{date}<br>{author}</div></div>
{content}
</body></html>""",

    "dark": """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: {margin}mm; }}
body {{ font-family: 'DejaVu Sans', system-ui, sans-serif; background: #1a1a2e; color: #e0e0e0; font-size: 12px; line-height: 1.7; }}
h1 {{ color: #fff; font-size: 26px; }}
h2 {{ color: {accent}; font-size: 17px; border-bottom: 1px solid #333; padding-bottom: 6px; margin-top: 28px; }}
h3 {{ color: #ccc; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
th {{ background: {brand}; color: white; padding: 10px 14px; text-align: left; font-size: 11px; }}
td {{ padding: 10px 14px; border-bottom: 1px solid #2a2a3e; color: #ccc; }}
tbody tr:nth-child(even) {{ background: #22223a; }}
code {{ background: #2a2a3e; color: {accent}; padding: 2px 6px; border-radius: 4px; }}
pre {{ background: #0f0f1a; padding: 16px; border-radius: 8px; }}
pre code {{ background: none; }}
blockquote {{ border-left: 3px solid {accent}; padding: 10px 16px; color: #aaa; }}
a {{ color: {accent}; }}
ul {{ list-style: none; padding: 0; }}
ul li {{ padding: 6px 0 6px 24px; position: relative; }}
ul li::before {{ content: "\\25B8"; position: absolute; left: 4px; color: {accent}; }}
img {{ max-width: 100%; }}
hr {{ border: none; height: 1px; background: #333; margin: 20px 0; }}
""" + _PAGE_BREAK_CSS + """
</style></head><body>{content}</body></html>""",
}

# ---------------------------------------------------------------------------
# Default colors
# ---------------------------------------------------------------------------

DEFAULT_COLORS = {
    "brand": "#6c5ce7",
    "dark": "#0f0c29",
    "accent": "#00cec9",
}


# ---------------------------------------------------------------------------
# Core render function (importable)
# ---------------------------------------------------------------------------

async def render_pdf_async(
    html_content: str,
    output_path: str,
    *,
    landscape: bool = False,
    margin_mm: int = 20,
    template: str | None = None,
    title: str = "",
    subtitle: str = "",
    author: str = "",
    brand: str = "",
    dark: str = "",
    accent: str = "",
    wait_for_fonts: bool = True,
) -> str:
    """Render HTML string to PDF via Playwright Chromium.

    Args:
        html_content: Raw HTML string or Markdown (auto-detected).
        output_path: Where to save the PDF.
        landscape: Landscape orientation.
        margin_mm: Page margins in mm.
        template: Template name (report, proposal, invoice, minimal, dark).
        title: Document title (for templates with headers).
        subtitle: Document subtitle.
        author: Author name (for footers).
        brand/dark/accent: Color overrides.

    Returns:
        Absolute path to the generated PDF.
    """
    from playwright.async_api import async_playwright
    from datetime import datetime

    # Auto-detect Markdown
    if not html_content.strip().startswith("<"):
        html_content = md_to_html(html_content)

    # Apply template
    colors = {
        "brand": brand or DEFAULT_COLORS["brand"],
        "dark": dark or DEFAULT_COLORS["dark"],
        "accent": accent or DEFAULT_COLORS["accent"],
    }
    date_str = datetime.now().strftime("%d.%m.%Y")

    if template and template in TEMPLATES:
        full_html = TEMPLATES[template].format(
            content=html_content,
            title=title or "Document",
            subtitle=subtitle,
            author=author,
            date=date_str,
            margin=margin_mm,
            **colors,
        )
    elif "<html" in html_content.lower() or "<!doctype" in html_content.lower():
        # Already a full HTML document
        full_html = html_content
    else:
        # Wrap in minimal template
        full_html = TEMPLATES["minimal"].format(
            content=html_content,
            margin=margin_mm,
        )

    # Write to temp file (Playwright needs a file: URL for local resources)
    tmp_dir = tempfile.mkdtemp(prefix="neura_pdf_")
    html_path = os.path.join(tmp_dir, "document.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.goto(f"file://{html_path}", wait_until="networkidle")

            # Wait for web fonts to load
            if wait_for_fonts:
                try:
                    await page.wait_for_function(
                        "document.fonts.ready.then(() => true)",
                        timeout=3000,
                    )
                except Exception:
                    pass  # Proceed without fonts if timeout

            # Templates with full-bleed headers/footers need zero PDF margins
            # (CSS @page handles margins internally)
            full_bleed = template in ("proposal", "report")
            margin_str = f"{margin_mm}mm"
            pdf_margin = {
                "top": "0", "right": "0", "bottom": "0", "left": "0",
            } if full_bleed else {
                "top": margin_str, "right": margin_str,
                "bottom": margin_str, "left": margin_str,
            }
            await page.pdf(
                path=output_path,
                format="A4",
                landscape=landscape,
                print_background=True,
                margin=pdf_margin,
            )

            await browser.close()
    finally:
        # Cleanup temp files
        try:
            os.unlink(html_path)
            os.rmdir(tmp_dir)
        except Exception:
            pass

    return os.path.abspath(output_path)


def render_pdf(
    html_content: str,
    output_path: str,
    **kwargs,
) -> str:
    """Synchronous wrapper for render_pdf_async."""
    return asyncio.run(render_pdf_async(html_content, output_path, **kwargs))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="HTML/Markdown → PDF via Playwright (Chromium)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 html-to-pdf.py report.html -o report.pdf
  python3 html-to-pdf.py doc.md -o doc.pdf --template report --title "Q1 Report"
  echo "<h1>Hello</h1>" | python3 html-to-pdf.py -o hello.pdf
  python3 html-to-pdf.py content.md -o proposal.pdf --template proposal \\
      --title "AI-агент под ключ" --brand "#e84393" --author "Neura"
        """,
    )
    parser.add_argument("input", nargs="?", help="Input HTML/MD file (or stdin)")
    parser.add_argument("-o", "--output", default="/tmp/output.pdf", help="Output PDF path")
    parser.add_argument("--template", choices=list(TEMPLATES.keys()), help="Document template")
    parser.add_argument("--title", default="", help="Document title (for templates)")
    parser.add_argument("--subtitle", default="", help="Subtitle")
    parser.add_argument("--author", default="", help="Author (for footer)")
    parser.add_argument("--brand", default="", help="Brand color (hex)")
    parser.add_argument("--dark", default="", help="Dark color (hex)")
    parser.add_argument("--accent", default="", help="Accent color (hex)")
    parser.add_argument("--landscape", action="store_true", help="Landscape orientation")
    parser.add_argument("--margin", type=int, default=20, help="Margin in mm (default: 20)")
    args = parser.parse_args()

    # Read input
    if args.input:
        path = Path(args.input)
        if not path.exists():
            print(f"Error: file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        content = path.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        print("Error: provide input file or pipe content via stdin", file=sys.stderr)
        sys.exit(1)

    if not content.strip():
        print("Error: empty input", file=sys.stderr)
        sys.exit(1)

    result = render_pdf(
        content, args.output,
        template=args.template,
        title=args.title,
        subtitle=args.subtitle,
        author=args.author,
        brand=args.brand,
        dark=args.dark,
        accent=args.accent,
        landscape=args.landscape,
        margin_mm=args.margin,
    )
    print(f"PDF saved: {result}")


if __name__ == "__main__":
    main()
