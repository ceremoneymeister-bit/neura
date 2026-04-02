#!/usr/bin/env python3
"""
Notion-style PDF generator — unified script for all Neura bots.
Converts Markdown → clean A4 PDF with Notion aesthetics.

Usage:
    python3 md2pdf.py --input doc.md --output /tmp/doc.pdf --title "My Doc"
    echo "# Hello" | python3 md2pdf.py --output /tmp/hello.pdf
    python3 md2pdf.py --input a.md b.md c.md --output /tmp/combined.pdf

Engines (auto-detected, best-first):
    1. wkhtmltopdf  — full CSS, best quality
    2. weasyprint   — full CSS, needs cairo/pango
    3. fpdf2        — basic layout, zero deps fallback
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------------------
# Notion-like CSS
# ---------------------------------------------------------------------------
NOTION_CSS = """
@page {
    size: A4;
    margin: 20mm 25mm;
}
body {
    font-family: 'DejaVu Sans', 'Noto Sans', 'Liberation Sans', Arial, sans-serif;
    color: #37352F;
    background: #fff;
    font-size: 11pt;
    line-height: 1.6;
    max-width: 100%;
    margin: 0;
    padding: 0;
}
h1 {
    font-size: 24pt;
    font-weight: 700;
    margin-top: 0;
    margin-bottom: 16px;
    border-bottom: 2px solid #37352F;
    padding-bottom: 8px;
}
h2 {
    font-size: 16pt;
    font-weight: 700;
    margin-top: 28px;
    margin-bottom: 10px;
    color: #37352F;
}
h3 {
    font-size: 13pt;
    font-weight: 600;
    margin-top: 20px;
    margin-bottom: 8px;
    color: #37352F;
}
h4 {
    font-size: 11pt;
    font-weight: 600;
    margin-top: 16px;
    margin-bottom: 6px;
}
p { margin: 6px 0; }
ul, ol { margin: 6px 0; padding-left: 24px; }
li { margin: 3px 0; }
blockquote {
    border-left: 3px solid #37352F;
    padding: 8px 16px;
    margin: 12px 0;
    background: #F7F6F3;
    color: #37352F;
    font-style: italic;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 10pt;
}
th {
    background: #F7F6F3;
    font-weight: 600;
    text-align: left;
    padding: 8px 10px;
    border: 1px solid #E9E9E7;
}
td {
    padding: 6px 10px;
    border: 1px solid #E9E9E7;
    vertical-align: top;
}
tr:nth-child(even) td {
    background: #FAFAF9;
}
code {
    background: #F7F6F3;
    padding: 2px 5px;
    border-radius: 3px;
    font-family: 'DejaVu Sans Mono', 'Liberation Mono', monospace;
    font-size: 9pt;
}
pre {
    background: #F7F6F3;
    padding: 12px 16px;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 9pt;
    line-height: 1.4;
}
pre code {
    background: none;
    padding: 0;
}
hr {
    border: none;
    border-top: 1px solid #E9E9E7;
    margin: 20px 0;
}
strong { font-weight: 700; }
em { font-style: italic; }
.page-break { page-break-before: always; }
.footer-line {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    text-align: center;
    font-size: 9pt;
    color: #9B9A97;
    padding: 8px 0;
}
"""

# Claude Code dark theme — dark background, orange accent
CLAUDE_CSS = """
@page {
    size: A4;
    margin: 18mm 22mm;
}
body {
    font-family: 'DejaVu Sans', 'Noto Sans', 'Liberation Sans', Arial, sans-serif;
    color: #E8E8E8;
    background: #1A1A2E;
    font-size: 11pt;
    line-height: 1.65;
    max-width: 100%;
    margin: 0;
    padding: 0;
}
h1 {
    font-size: 26pt;
    font-weight: 700;
    margin-top: 0;
    margin-bottom: 18px;
    color: #FF6B2B;
    border-bottom: 2px solid #FF6B2B;
    padding-bottom: 10px;
}
h2 {
    font-size: 17pt;
    font-weight: 700;
    margin-top: 30px;
    margin-bottom: 10px;
    color: #FF8C42;
}
h3 {
    font-size: 13pt;
    font-weight: 600;
    margin-top: 22px;
    margin-bottom: 8px;
    color: #FFB067;
}
h4 {
    font-size: 11pt;
    font-weight: 600;
    margin-top: 16px;
    margin-bottom: 6px;
    color: #CCCCCC;
}
p { margin: 6px 0; }
ul, ol { margin: 6px 0; padding-left: 24px; }
li { margin: 3px 0; }
li::marker { color: #FF6B2B; }
blockquote {
    border-left: 3px solid #FF6B2B;
    padding: 10px 16px;
    margin: 12px 0;
    background: #16213E;
    color: #C8C8C8;
    font-style: italic;
    border-radius: 0 6px 6px 0;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 10pt;
}
th {
    background: #0F3460;
    color: #FF8C42;
    font-weight: 600;
    text-align: left;
    padding: 10px 12px;
    border: 1px solid #1A1A40;
}
td {
    padding: 8px 12px;
    border: 1px solid #1A1A40;
    vertical-align: top;
    color: #D0D0D0;
}
tr:nth-child(even) td {
    background: #16213E;
}
tr:nth-child(odd) td {
    background: #1A1A2E;
}
code {
    background: #0F3460;
    color: #FF8C42;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'DejaVu Sans Mono', 'Liberation Mono', monospace;
    font-size: 9pt;
}
pre {
    background: #0F3460;
    padding: 14px 18px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 9pt;
    line-height: 1.5;
    border-left: 3px solid #FF6B2B;
}
pre code {
    background: none;
    color: #E8E8E8;
    padding: 0;
}
hr {
    border: none;
    border-top: 1px solid #0F3460;
    margin: 24px 0;
}
strong { font-weight: 700; color: #FFFFFF; }
em { font-style: italic; color: #FFB067; }
a { color: #FF6B2B; text-decoration: none; }
.page-break { page-break-before: always; }
.footer-line {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    text-align: center;
    font-size: 9pt;
    color: #666;
    padding: 8px 0;
}
"""

THEMES = {
    "notion": NOTION_CSS,
    "claude": CLAUDE_CSS,
}

# ---------------------------------------------------------------------------
# Engine detection
# ---------------------------------------------------------------------------

def detect_engine(force=None):
    """Detect best available PDF engine."""
    if force:
        return force

    # 1. wkhtmltopdf
    if shutil.which("wkhtmltopdf"):
        return "wkhtmltopdf"

    # 2. weasyprint
    try:
        import weasyprint  # noqa: F401
        return "weasyprint"
    except ImportError:
        pass

    # 3. fpdf2
    try:
        from fpdf import FPDF  # noqa: F401
        return "fpdf2"
    except ImportError:
        pass

    # 4. Try to install fpdf2 on the fly
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "fpdf2", "-q", "--break-system-packages"],
            capture_output=True, timeout=30,
        )
        from fpdf import FPDF  # noqa: F401
        return "fpdf2"
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# Markdown → HTML
# ---------------------------------------------------------------------------

def md_to_html(md_text, title="Document", footer="Neura", show_footer=True, theme="notion"):
    """Convert Markdown to styled HTML string."""
    try:
        import markdown as md_lib
        body = md_lib.markdown(md_text, extensions=["tables", "fenced_code", "nl2br"])
    except ImportError:
        # Minimal fallback: just wrap in <pre>
        body = f"<pre>{_escape_html(md_text)}</pre>"

    css = THEMES.get(theme, NOTION_CSS)

    footer_html = ""
    if show_footer and footer:
        footer_html = f'<div class="footer-line">{_escape_html(footer)}</div>'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>{_escape_html(title)}</title>
<style>{css}</style>
</head>
<body>
{body}
{footer_html}
</body>
</html>"""


def _escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Engine: wkhtmltopdf
# ---------------------------------------------------------------------------

def render_wkhtmltopdf(html_content, output_path, footer_text="Neura"):
    """Render HTML to PDF using wkhtmltopdf."""
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as f:
        f.write(html_content)
        html_path = f.name

    try:
        cmd = [
            "wkhtmltopdf",
            "--encoding", "utf-8",
            "--page-size", "A4",
            "--margin-top", "20mm",
            "--margin-bottom", "20mm",
            "--margin-left", "25mm",
            "--margin-right", "25mm",
            "--footer-center", f"[page] — {footer_text}",
            "--footer-font-name", "DejaVu Sans",
            "--footer-font-size", "9",
            "--enable-local-file-access",
            "--quiet",
            html_path,
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=60)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    finally:
        os.unlink(html_path)


# ---------------------------------------------------------------------------
# Engine: WeasyPrint
# ---------------------------------------------------------------------------

def render_weasyprint(html_content, output_path):
    """Render HTML to PDF using WeasyPrint."""
    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(output_path)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        print(f"WeasyPrint error: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Engine: fpdf2 (fallback)
# ---------------------------------------------------------------------------

def render_fpdf2(md_text, output_path, title="Document", footer="Neura"):
    """Render Markdown to PDF using fpdf2 (basic layout, no CSS)."""
    from fpdf import FPDF

    class NotionPDF(FPDF):
        def __init__(self, footer_text):
            super().__init__()
            self._footer_text = footer_text

        def header(self):
            pass

        def footer(self):
            self.set_y(-15)
            self.set_font("DejaVu", size=8)
            self.set_text_color(155, 154, 151)
            self.cell(0, 10, f"{self.page_no()} — {self._footer_text}", align="C")

    pdf = NotionPDF(footer)
    pdf.set_auto_page_break(auto=True, margin=20)

    # Try to load DejaVu font
    font_loaded = False
    for font_dir in [
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/dejavu",
        "/usr/local/share/fonts",
    ]:
        regular = os.path.join(font_dir, "DejaVuSans.ttf")
        bold = os.path.join(font_dir, "DejaVuSans-Bold.ttf")
        mono = os.path.join(font_dir, "DejaVuSansMono.ttf")
        if os.path.exists(regular):
            pdf.add_font("DejaVu", "", regular, uni=True)
            if os.path.exists(bold):
                pdf.add_font("DejaVu", "B", bold, uni=True)
            if os.path.exists(mono):
                pdf.add_font("DejaVuMono", "", mono, uni=True)
            font_loaded = True
            break

    if not font_loaded:
        # Use built-in font (no Cyrillic)
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 6, md_text)
        pdf.output(output_path)
        return True

    pdf.add_page()
    text_color = (55, 53, 47)  # #37352F

    in_code_block = False
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal table_rows, in_table
        if not table_rows:
            return
        # Calculate column widths
        num_cols = max(len(row) for row in table_rows)
        page_width = pdf.w - pdf.l_margin - pdf.r_margin
        col_width = page_width / max(num_cols, 1)

        for i, row in enumerate(table_rows):
            fill = i == 0  # header
            for j, cell in enumerate(row):
                if i == 0:
                    pdf.set_font("DejaVu", "B", 9)
                    pdf.set_fill_color(247, 246, 243)
                else:
                    pdf.set_font("DejaVu", "", 9)
                    if i % 2 == 0:
                        pdf.set_fill_color(250, 250, 249)
                        fill = True
                    else:
                        fill = False
                pdf.set_text_color(*text_color)
                x = pdf.get_x()
                y = pdf.get_y()
                # Draw cell border
                pdf.rect(x, y, col_width, 7)
                pdf.set_xy(x + 1, y)
                pdf.cell(col_width - 2, 7, cell.strip()[:40], fill=fill)
                pdf.set_xy(x + col_width, y)
            pdf.ln(7)

        table_rows = []
        in_table = False
        pdf.ln(3)

    for line in md_text.split("\n"):
        stripped = line.strip()

        # Code blocks
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            pdf.set_font("DejaVuMono" if font_loaded else "Courier", "", 9)
            pdf.set_fill_color(247, 246, 243)
            pdf.set_text_color(*text_color)
            pdf.cell(0, 5, stripped[:100], fill=True, new_x="LMARGIN", new_y="NEXT")
            continue

        # Page break marker
        if '<div class="page-break">' in stripped:
            flush_table()
            pdf.add_page()
            continue

        # Table rows
        if "|" in stripped and not stripped.startswith("#"):
            cells = [c.strip() for c in stripped.split("|")]
            cells = [c for c in cells if c]
            # Skip separator rows like |---|---|
            if all(re.match(r'^[-:]+$', c) for c in cells):
                continue
            if not in_table:
                in_table = True
            table_rows.append(cells)
            continue
        elif in_table:
            flush_table()

        # Headers
        if stripped.startswith("# "):
            pdf.set_font("DejaVu", "B", 20)
            pdf.set_text_color(*text_color)
            pdf.ln(4)
            pdf.multi_cell(0, 9, stripped[2:])
            # Underline
            y = pdf.get_y()
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(4)
            continue
        if stripped.startswith("## "):
            pdf.set_font("DejaVu", "B", 14)
            pdf.set_text_color(*text_color)
            pdf.ln(6)
            pdf.multi_cell(0, 7, stripped[3:])
            pdf.ln(2)
            continue
        if stripped.startswith("### "):
            pdf.set_font("DejaVu", "B", 12)
            pdf.set_text_color(*text_color)
            pdf.ln(4)
            pdf.multi_cell(0, 6, stripped[4:])
            pdf.ln(2)
            continue
        if stripped.startswith("#### "):
            pdf.set_font("DejaVu", "B", 11)
            pdf.set_text_color(*text_color)
            pdf.ln(3)
            pdf.multi_cell(0, 6, stripped[5:])
            pdf.ln(1)
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            flush_table()
            y = pdf.get_y() + 3
            pdf.set_draw_color(233, 233, 231)
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.set_draw_color(0, 0, 0)
            pdf.ln(8)
            continue

        # Blockquote
        if stripped.startswith("> "):
            pdf.set_font("DejaVu", "", 10)
            pdf.set_text_color(55, 53, 47)
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.set_fill_color(247, 246, 243)
            pdf.rect(x, y, pdf.w - pdf.l_margin - pdf.r_margin, 7, "F")
            pdf.set_x(x + 5)
            pdf.cell(0, 7, stripped[2:])
            pdf.ln(8)
            continue

        # Bullet list
        if stripped.startswith("- ") or stripped.startswith("* "):
            pdf.set_font("DejaVu", "", 10)
            pdf.set_text_color(*text_color)
            pdf.cell(5, 5, "•")
            pdf.multi_cell(0, 5, stripped[2:])
            continue

        # Numbered list
        m = re.match(r'^(\d+)\.\s+(.+)', stripped)
        if m:
            pdf.set_font("DejaVu", "", 10)
            pdf.set_text_color(*text_color)
            pdf.cell(8, 5, f"{m.group(1)}.")
            pdf.multi_cell(0, 5, m.group(2))
            continue

        # Empty line
        if not stripped:
            pdf.ln(3)
            continue

        # Regular paragraph
        pdf.set_font("DejaVu", "", 10)
        pdf.set_text_color(*text_color)
        # Strip markdown bold/italic for fpdf2
        clean = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
        clean = re.sub(r'\*(.+?)\*', r'\1', clean)
        clean = re.sub(r'`(.+?)`', r'\1', clean)
        pdf.multi_cell(0, 5, clean)

    flush_table()
    pdf.output(output_path)
    return os.path.exists(output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Notion-style PDF generator")
    parser.add_argument("--input", "-i", nargs="*", help="Input .md file(s). Reads stdin if omitted.")
    parser.add_argument("--output", "-o", default="/tmp/output.pdf", help="Output PDF path")
    parser.add_argument("--title", "-t", default=None, help="Document title")
    parser.add_argument("--footer", "-f", default="Neura", help="Footer text")
    parser.add_argument("--engine", "-e", choices=["wkhtmltopdf", "weasyprint", "fpdf2", "auto"],
                        default="auto", help="PDF engine")
    parser.add_argument("--no-footer", action="store_true", help="Disable footer")
    parser.add_argument("--theme", choices=list(THEMES.keys()), default="notion",
                        help="PDF theme: notion (light) or claude (dark+orange)")
    parser.add_argument("--no-page-break", action="store_true",
                        help="No page break between multiple input files")
    args = parser.parse_args()

    # Read input
    if args.input:
        parts = []
        for fpath in args.input:
            with open(fpath, "r", encoding="utf-8") as f:
                parts.append(f.read())
        if args.no_page_break:
            md_text = "\n\n---\n\n".join(parts)
        else:
            md_text = ('\n\n<div class="page-break"></div>\n\n').join(parts)
        if not args.title:
            args.title = os.path.splitext(os.path.basename(args.input[0]))[0]
    else:
        md_text = sys.stdin.read()
        if not args.title:
            args.title = "Document"

    footer = "" if args.no_footer else args.footer

    # Detect engine
    engine = detect_engine(None if args.engine == "auto" else args.engine)
    if not engine:
        print("ERROR: No PDF engine available. Install wkhtmltopdf or fpdf2.", file=sys.stderr)
        sys.exit(1)

    print(f"Engine: {engine}", file=sys.stderr)

    # Ensure markdown lib for HTML-based engines
    if engine in ("wkhtmltopdf", "weasyprint"):
        try:
            import markdown  # noqa: F401
        except ImportError:
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "markdown", "-q", "--break-system-packages"],
                    capture_output=True, timeout=30,
                )
            except Exception:
                pass

    # Render
    success = False
    if engine == "wkhtmltopdf":
        html = md_to_html(md_text, args.title, footer, show_footer=False, theme=args.theme)
        success = render_wkhtmltopdf(html, args.output, footer)
    elif engine == "weasyprint":
        html = md_to_html(md_text, args.title, footer, theme=args.theme)
        success = render_weasyprint(html, args.output)
    elif engine == "fpdf2":
        success = render_fpdf2(md_text, args.output, args.title, footer)

    if success:
        size = os.path.getsize(args.output)
        print(f"OK: {args.output} ({size:,} bytes)", file=sys.stderr)
    else:
        # Try fallback
        if engine != "fpdf2":
            print(f"Falling back to fpdf2...", file=sys.stderr)
            try:
                success = render_fpdf2(md_text, args.output, args.title, footer)
                if success:
                    size = os.path.getsize(args.output)
                    print(f"OK (fpdf2 fallback): {args.output} ({size:,} bytes)", file=sys.stderr)
                else:
                    print("FAIL: Could not generate PDF", file=sys.stderr)
                    sys.exit(1)
            except Exception as e:
                print(f"FAIL: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print("FAIL: Could not generate PDF", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
