#!/usr/bin/env python3
"""PDF, QR-код, озвучка (TTS) — утилиты капсулы

Usage:
    python3 tools/capsule-tools.py pdf "Title" input.md [output.pdf]
    python3 tools/capsule-tools.py qr "https://example.com" [output.png]
    python3 tools/capsule-tools.py tts "Текст для озвучки" [output.ogg]
    python3 tools/capsule-tools.py list
"""

import sys
import os


def cmd_pdf(args):
    """Generate PDF from text/markdown file."""
    if len(args) < 2:
        print("Usage: capsule-tools.py pdf \"Title\" input.md [output.pdf]")
        return 1

    title = args[0]
    input_path = args[1]
    output_path = args[2] if len(args) > 2 else "/tmp/output.pdf"

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        print("Error: reportlab not installed. Run: pip install reportlab")
        return 1

    if not os.path.exists(input_path):
        print(f"Error: file not found: {input_path}")
        return 1

    content = open(input_path, "r", encoding="utf-8").read()

    # Register a font that supports Cyrillic if available
    font_name = "Helvetica"
    for font_path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("CyrFont", font_path))
                font_name = "CyrFont"
                break
            except Exception:
                pass

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Title"],
        fontName=font_name, fontSize=18, spaceAfter=20
    )
    body_style = ParagraphStyle(
        "CustomBody", parent=styles["Normal"],
        fontName=font_name, fontSize=11, leading=16, spaceAfter=8
    )
    heading_style = ParagraphStyle(
        "CustomHeading", parent=styles["Heading2"],
        fontName=font_name, fontSize=14, spaceAfter=10, spaceBefore=16
    )

    story = [Paragraph(title, title_style), Spacer(1, 12)]

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 6))
        elif stripped.startswith("## "):
            story.append(Paragraph(stripped[3:], heading_style))
        elif stripped.startswith("# "):
            story.append(Paragraph(stripped[2:], heading_style))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            story.append(Paragraph(f"• {stripped[2:]}", body_style))
        else:
            # Escape XML special chars
            safe = stripped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe, body_style))

    doc.build(story)
    print(f"OK: {output_path}")
    return 0


def cmd_qr(args):
    """Generate QR code image."""
    if len(args) < 1:
        print("Usage: capsule-tools.py qr \"https://...\" [output.png]")
        return 1

    data = args[0]
    output_path = args[1] if len(args) > 1 else "/tmp/qr.png"

    try:
        import qrcode
    except ImportError:
        print("Error: qrcode not installed. Run: pip install qrcode[pil]")
        return 1

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_path)
    print(f"OK: {output_path}")
    return 0


def cmd_tts(args):
    """Generate speech audio from text using edge-tts."""
    if len(args) < 1:
        print("Usage: capsule-tools.py tts \"Текст\" [output.ogg]")
        return 1

    text = args[0]
    output_path = args[1] if len(args) > 1 else "/tmp/speech.ogg"

    try:
        import asyncio
        import edge_tts
    except ImportError:
        print("Error: edge-tts not installed. Run: pip install edge-tts")
        return 1

    async def _generate():
        # Russian female voice
        communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
        mp3_path = output_path.replace(".ogg", ".mp3")
        await communicate.save(mp3_path)

        # Convert to ogg if ffmpeg available
        if output_path.endswith(".ogg"):
            import subprocess
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "libopus", output_path],
                    capture_output=True, timeout=30
                )
                os.unlink(mp3_path)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # ffmpeg not available, keep mp3
                os.rename(mp3_path, output_path)
        return output_path

    result = asyncio.run(_generate())
    print(f"OK: {result}")
    return 0


def cmd_list(_args):
    """List available tools."""
    tools = {
        "pdf": "Generate PDF from markdown/text file",
        "qr": "Generate QR code image",
        "tts": "Text-to-speech (Russian, edge-tts)",
    }
    print("Available tools:")
    for name, desc in tools.items():
        print(f"  {name:10s} — {desc}")
    return 0


COMMANDS = {
    "pdf": cmd_pdf,
    "qr": cmd_qr,
    "tts": cmd_tts,
    "list": cmd_list,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]
    sys.exit(COMMANDS[cmd](args))


if __name__ == "__main__":
    main()
