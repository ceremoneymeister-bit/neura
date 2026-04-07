#!/usr/bin/env python3
"""Generate PDF documents from HTML templates.

Uses templates from scripts/templates/ directory and renders via html-to-pdf.py (Playwright).

Usage:
    # Commercial Proposal
    python3 doc-from-template.py commercial-proposal \
        --title "AI-агент под ключ" \
        --subtitle "Персональный AI-ассистент для вашего бизнеса" \
        --client "ООО Рога и Копыта" \
        --author "Neura Platform" \
        --content content.html \
        -o /tmp/proposal.pdf

    # Price List
    python3 doc-from-template.py price-list \
        --title "Тарифы Neura 2026" \
        --content prices.html \
        -o /tmp/prices.pdf

    # Certificate
    python3 doc-from-template.py certificate \
        --title "Сертификат" \
        --subtitle "об успешном прохождении курса" \
        --recipient "Иванов Иван Иванович" \
        --description "Успешно завершил курс AI для бизнеса" \
        --number "CERT-2026-001" \
        -o /tmp/cert.pdf

    # List available templates
    python3 doc-from-template.py --list

Templates can also be used from Python:
    from doc_from_template import generate_document
    generate_document("commercial-proposal", output="/tmp/kp.pdf",
                      title="КП", client="Клиент", content_html="<h2>...</h2>")
"""
import argparse
import asyncio
import os
import re
import sys
from datetime import datetime
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"
SCRIPT_DIR = Path(__file__).parent

# Default colors per template type
TEMPLATE_COLORS = {
    "commercial-proposal": {"brand": "#6c5ce7", "dark": "#0f0c29", "accent": "#00cec9"},
    "price-list": {"brand": "#2d6cdf", "dark": "#0a1929", "accent": "#00b894"},
    "certificate": {"brand": "#b8860b", "dark": "#1a1a2e", "accent": "#daa520"},
}


def list_templates() -> list[str]:
    """List available template names."""
    return sorted(p.stem for p in TEMPLATES_DIR.glob("*.html"))


def load_template(name: str) -> str:
    """Load template HTML by name."""
    path = TEMPLATES_DIR / f"{name}.html"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {name}\nAvailable: {', '.join(list_templates())}")
    return path.read_text(encoding="utf-8")


def fill_template(html: str, **kwargs) -> str:
    """Replace {{placeholders}} in template with values."""
    for key, value in kwargs.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))
    # Remove unfilled placeholders
    html = re.sub(r"\{\{[a-z_]+\}\}", "", html)
    return html


def generate_document(
    template_name: str,
    output: str = "/tmp/document.pdf",
    *,
    title: str = "",
    subtitle: str = "",
    client: str = "",
    author: str = "",
    logo: str = "",
    content_html: str = "",
    content_file: str = "",
    recipient: str = "",
    description: str = "",
    number: str = "",
    footer: str = "",
    brand: str = "",
    dark: str = "",
    accent: str = "",
    landscape: bool = False,
) -> str:
    """Generate PDF from template. Returns output path."""
    # Load template
    html = load_template(template_name)

    # Get default colors
    colors = TEMPLATE_COLORS.get(template_name, TEMPLATE_COLORS["commercial-proposal"])
    brand = brand or colors["brand"]
    dark = dark or colors["dark"]
    accent = accent or colors["accent"]

    # Load content
    content = content_html
    if content_file and Path(content_file).exists():
        raw = Path(content_file).read_text(encoding="utf-8")
        # If it's Markdown, convert to HTML
        if content_file.endswith(".md"):
            sys.path.insert(0, str(SCRIPT_DIR))
            from importlib import import_module
            # Import md_to_html from html-to-pdf.py
            spec = __import__("importlib").util.spec_from_file_location(
                "html_to_pdf", SCRIPT_DIR / "html-to-pdf.py"
            )
            mod = __import__("importlib").util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            content = mod.md_to_html(raw)
        else:
            content = raw

    date_str = datetime.now().strftime("%d.%m.%Y")

    # Fill template
    filled = fill_template(
        html,
        title=title or "Document",
        subtitle=subtitle,
        client=client,
        author=author,
        logo=logo or (author.upper() if author else ""),
        content=content,
        date=date_str,
        recipient=recipient,
        description=description,
        number=number or f"DOC-{datetime.now().strftime('%Y-%m%d')}",
        footer=footer,
        brand=brand,
        dark=dark,
        accent=accent,
    )

    # Render via Playwright
    spec = __import__("importlib").util.spec_from_file_location(
        "html_to_pdf", SCRIPT_DIR / "html-to-pdf.py"
    )
    mod = __import__("importlib").util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    return asyncio.run(mod.render_pdf_async(
        filled, output,
        landscape=landscape or template_name == "certificate",
    ))


def main():
    parser = argparse.ArgumentParser(description="Generate PDF from HTML templates")
    parser.add_argument("template", nargs="?", help="Template name (e.g. commercial-proposal)")
    parser.add_argument("-o", "--output", default="/tmp/document.pdf", help="Output PDF path")
    parser.add_argument("--title", default="", help="Document title")
    parser.add_argument("--subtitle", default="", help="Subtitle")
    parser.add_argument("--client", default="", help="Client name (for proposals)")
    parser.add_argument("--author", default="", help="Author/company")
    parser.add_argument("--logo", default="", help="Logo text")
    parser.add_argument("--content", default="", help="Content HTML/MD file")
    parser.add_argument("--recipient", default="", help="Recipient name (certificates)")
    parser.add_argument("--description", default="", help="Description text")
    parser.add_argument("--number", default="", help="Document number")
    parser.add_argument("--brand", default="", help="Brand color (hex)")
    parser.add_argument("--dark", default="", help="Dark color (hex)")
    parser.add_argument("--accent", default="", help="Accent color (hex)")
    parser.add_argument("--landscape", action="store_true", help="Landscape orientation")
    parser.add_argument("--list", action="store_true", help="List available templates")
    args = parser.parse_args()

    if args.list or not args.template:
        templates = list_templates()
        print("Available templates:")
        for t in templates:
            colors = TEMPLATE_COLORS.get(t, {})
            print(f"  {t}  (brand: {colors.get('brand', 'default')})")
        return

    result = generate_document(
        args.template, args.output,
        title=args.title,
        subtitle=args.subtitle,
        client=args.client,
        author=args.author,
        logo=args.logo,
        content_file=args.content,
        recipient=args.recipient,
        description=args.description,
        number=args.number,
        brand=args.brand,
        dark=args.dark,
        accent=args.accent,
        landscape=args.landscape,
    )
    print(f"PDF saved: {result}")


if __name__ == "__main__":
    main()
