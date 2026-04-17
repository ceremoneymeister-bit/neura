"""
Intelligent document analysis for the Neura platform.

Analyzes PDFs (structure, type, TOC, scan detection) and builds
prompt context for Claude to efficiently read documents.

Also provides parse_document() for markdown extraction (pymupdf4llm, OCR, Firecrawl).

Standalone module — no Neura imports required.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

# PyMuPDF — graceful degradation if not installed
try:
    import fitz  # PyMuPDF

    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

# pymupdf4llm — PDF → markdown with tables (LLM-optimised)
try:
    import pymupdf4llm

    HAS_PYMUPDF4LLM = True
except ImportError:
    HAS_PYMUPDF4LLM = False

# pytesseract + pdf2image — OCR for scanned PDFs
try:
    import pytesseract
    from pdf2image import convert_from_path

    HAS_OCR = True
except ImportError:
    HAS_OCR = False


# ---------------------------------------------------------------------------
# Russian doc-type mapping
# ---------------------------------------------------------------------------

DOC_TYPE_RU = {
    "contract": "юридический документ (договор)",
    "report": "отчёт",
    "invoice": "счёт/инвойс",
    "article": "статья/документ",
    "presentation": "презентация",
    "unknown": "документ",
}

# Keywords for type detection (lowercase)
_TYPE_KEYWORDS: dict[str, list[str]] = {
    "contract": ["договор", "контракт", "соглашение", "стороны", "реквизиты"],
    "report": ["отчёт", "результаты", "показатели", "квартал"],
    "invoice": ["счёт", "invoice", "к оплате", "итого"],
    "article": ["содержание", "глава", "раздел"],
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_size(size_bytes: int) -> tuple[float, str]:
    """Return (size_mb, human-readable string in Russian)."""
    mb = size_bytes / (1024 * 1024)
    if mb >= 1.0:
        return round(mb, 1), f"{round(mb, 1)} МБ"
    kb = size_bytes / 1024
    return round(mb, 2), f"{round(kb, 0):.0f} КБ"


def _get_page_text(doc: "fitz.Document", page_num: int) -> str:
    """Safely extract text from a page."""
    try:
        return doc[page_num].get_text()
    except Exception:
        return ""


def _detect_doc_type(doc: "fitz.Document") -> str:
    """Detect document type by scanning first 5 pages for keywords."""
    sample_text = ""
    for i in range(min(5, len(doc))):
        sample_text += _get_page_text(doc, i).lower() + "\n"

    scores: dict[str, int] = {}
    for doc_type, keywords in _TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in sample_text)
        if score > 0:
            scores[doc_type] = score

    if not scores:
        return "unknown"

    return max(scores, key=scores.get)  # type: ignore[arg-type]


def _extract_toc(doc: "fitz.Document") -> list[dict]:
    """Extract table of contents: built-in first, then heuristic scan."""
    # Try PyMuPDF built-in TOC
    raw_toc = doc.get_toc()
    if raw_toc:
        return [
            {"title": entry[1].strip(), "page": entry[2], "level": entry[0]}
            for entry in raw_toc
            if len(entry) >= 3
        ]

    # Heuristic: scan first 3 pages for TOC-like patterns
    toc: list[dict] = []
    patterns = [
        # "1. Title ...... 5" or "1. Title ... 5"
        re.compile(r"^(\d+)\.\s+(.+?)[\s.]{3,}(\d+)\s*$", re.MULTILINE),
        # "Глава 1. Title" / "Раздел 2. Title"
        re.compile(r"^(Глава|Раздел)\s+(\d+)[.\s]+(.+?)$", re.MULTILINE),
    ]

    for i in range(min(3, len(doc))):
        text = _get_page_text(doc, i)

        for match in patterns[0].finditer(text):
            toc.append({
                "title": match.group(2).strip().rstrip("."),
                "page": int(match.group(3)),
                "level": 1,
            })

        for match in patterns[1].finditer(text):
            toc.append({
                "title": f"{match.group(1)} {match.group(2)}. {match.group(3).strip()}",
                "page": 0,  # page unknown from this pattern
                "level": 1,
            })

    return toc


def _is_scanned(doc: "fitz.Document") -> bool:
    """Check if document is likely scanned (image-based) by sampling pages."""
    total_pages = len(doc)
    if total_pages == 0:
        return False

    # Sample: first, middle, last
    indices = list({0, total_pages // 2, total_pages - 1})
    total_chars = 0

    for idx in indices:
        total_chars += len(_get_page_text(doc, idx).strip())

    avg_chars = total_chars / len(indices)
    return avg_chars < 50


def _select_strategy(pages: int, is_scan: bool) -> tuple[str, str]:
    """Select reading strategy based on page count."""
    if is_scan:
        return "question_only", "Сканированный документ. Задавайте конкретные вопросы — буду читать нужные страницы"

    if pages <= 10:
        return "full_read", "Прочитаю целиком"
    elif pages <= 50:
        return "chunked", "Прочитаю порциями по 15-20 страниц"
    elif pages <= 200:
        return "targeted", "Проиндексирую структуру, буду читать целевые разделы"
    else:
        return "question_only", "Проиндексирую документ. Задавайте конкретные вопросы"


def _summarize_sections(toc: list[dict]) -> str:
    """Generate a short summary of document structure."""
    if not toc:
        return "структура не определена"

    top_level = [e for e in toc if e["level"] == 1]
    sub_level = [e for e in toc if e["level"] > 1]

    parts: list[str] = []
    if top_level:
        parts.append(f"{len(top_level)} разделов")
    if sub_level:
        parts.append(f"{len(sub_level)} подразделов")

    # Check for appendices
    appendix_count = sum(
        1 for e in toc
        if any(kw in e["title"].lower() for kw in ("приложение", "appendix", "annex"))
    )
    if appendix_count:
        parts.append(f"{appendix_count} приложения" if appendix_count < 5 else f"{appendix_count} приложений")

    return ", ".join(parts) if parts else f"{len(toc)} записей в оглавлении"


def _extract_metadata(doc: "fitz.Document") -> dict:
    """Extract PDF metadata."""
    meta = doc.metadata or {}
    return {
        "title": meta.get("title", "").strip() or None,
        "author": meta.get("author", "").strip() or None,
        "creation_date": meta.get("creationDate", "").strip() or None,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_document(file_path: str) -> dict:
    """
    Analyze a PDF document and return structured metadata.

    Returns a dict with filename, pages, size, doc_type, TOC,
    scan detection, reading strategy, and warnings.
    """
    path = Path(file_path)

    if not path.exists():
        return {
            "filename": path.name,
            "pages": 0,
            "size_mb": 0.0,
            "size_str": "0 КБ",
            "doc_type": "unknown",
            "has_toc": False,
            "toc": [],
            "sections_summary": "",
            "metadata": {},
            "is_scanned": False,
            "strategy": "question_only",
            "strategy_description": "Файл не найден",
            "warnings": [f"Файл не найден: {file_path}"],
        }

    file_size = path.stat().st_size
    size_mb, size_str = _format_size(file_size)

    # Non-PDF files — minimal info
    if path.suffix.lower() != ".pdf":
        return {
            "filename": path.name,
            "pages": 0,
            "size_mb": size_mb,
            "size_str": size_str,
            "doc_type": "unknown",
            "has_toc": False,
            "toc": [],
            "sections_summary": "",
            "metadata": {},
            "is_scanned": False,
            "strategy": "full_read",
            "strategy_description": "Прочитаю файл целиком",
            "warnings": [],
        }

    if not HAS_FITZ:
        return {
            "filename": path.name,
            "pages": 0,
            "size_mb": size_mb,
            "size_str": size_str,
            "doc_type": "unknown",
            "has_toc": False,
            "toc": [],
            "sections_summary": "",
            "metadata": {},
            "is_scanned": False,
            "strategy": "full_read",
            "strategy_description": "PyMuPDF не установлен — базовый анализ",
            "warnings": ["PyMuPDF (fitz) не установлен — детальный анализ недоступен"],
        }

    # Full PDF analysis
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return {
            "filename": path.name,
            "pages": 0,
            "size_mb": size_mb,
            "size_str": size_str,
            "doc_type": "unknown",
            "has_toc": False,
            "toc": [],
            "sections_summary": "",
            "metadata": {},
            "is_scanned": False,
            "strategy": "question_only",
            "strategy_description": "Не удалось открыть PDF",
            "warnings": [f"Ошибка открытия PDF: {e}"],
        }

    pages = len(doc)
    doc_type = _detect_doc_type(doc)
    toc = _extract_toc(doc)
    scanned = _is_scanned(doc)
    metadata = _extract_metadata(doc)
    strategy, strategy_desc = _select_strategy(pages, scanned)
    sections_summary = _summarize_sections(toc)

    warnings: list[str] = []
    if scanned:
        warnings.append("Сканированные страницы — качество OCR может быть ниже")
    if pages > 200:
        warnings.append(f"Большой документ ({pages} стр.) — рекомендуется работать с конкретными разделами")
    if file_size > 50 * 1024 * 1024:
        warnings.append(f"Тяжёлый файл ({size_str}) — возможны задержки при чтении")

    doc.close()

    return {
        "filename": path.name,
        "pages": pages,
        "size_mb": size_mb,
        "size_str": size_str,
        "doc_type": doc_type,
        "has_toc": bool(toc),
        "toc": toc,
        "sections_summary": sections_summary,
        "metadata": metadata,
        "is_scanned": scanned,
        "strategy": strategy,
        "strategy_description": strategy_desc,
        "warnings": warnings,
    }


def build_file_context(file_path: str) -> str:
    """
    Build a formatted prompt context string for a given file.

    For PDFs: full analysis with TOC, strategy, and reading instructions.
    For images: simple one-liner.
    For other files: simple one-liner.
    """
    path = Path(file_path)
    name = path.name
    ext = path.suffix.lower()

    # Images
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"):
        size_str = _format_size(path.stat().st_size)[1] if path.exists() else "?"
        return f"[Изображение: {name}, {size_str}] — прочитай через Read tool: {file_path}"

    # PDFs — full analysis
    if ext == ".pdf":
        info = analyze_document(file_path)

        lines: list[str] = []
        lines.append(f"📄 Получен: {info['filename']} ({info['pages']} стр., {info['size_str']})")

        doc_type_ru = DOC_TYPE_RU.get(info["doc_type"], "документ")
        lines.append(f"Тип: {doc_type_ru}")

        if info["sections_summary"]:
            lines.append(f"Структура: {info['sections_summary']}")

        if info["metadata"].get("title"):
            lines.append(f"Заголовок: {info['metadata']['title']}")
        if info["metadata"].get("author"):
            lines.append(f"Автор: {info['metadata']['author']}")

        # TOC — abbreviated to first 10 entries
        if info["toc"]:
            lines.append("")
            lines.append("Оглавление:")
            for entry in info["toc"][:10]:
                indent = "  " * (entry["level"] - 1)
                page_info = f" (стр. {entry['page']})" if entry["page"] > 0 else ""
                lines.append(f"  {indent}{entry['title']}{page_info}")
            if len(info["toc"]) > 10:
                lines.append(f"  ... и ещё {len(info['toc']) - 10} записей")

        lines.append("")
        lines.append(f"Стратегия: {info['strategy_description']}")

        for warning in info["warnings"]:
            lines.append(f"⚠️ {warning}")

        lines.append("")
        lines.append(f"Путь: {file_path}")
        lines.append("Инструкция: используй Read tool с параметром pages. Max 20 страниц за вызов.")

        # Strategy-specific instructions
        if info["strategy"] == "full_read":
            lines.append(f"Прочитай страницы 1-{info['pages']}.")
        elif info["strategy"] == "chunked":
            lines.append("Читай порциями: 1-20, 21-40 и т.д. Суммируй после каждой порции.")
        elif info["strategy"] == "targeted":
            lines.append("Сначала прочитай оглавление/первые страницы, затем запроси нужные разделы.")
        elif info["strategy"] == "question_only":
            lines.append("Не читай весь документ. Жди вопросов и читай только релевантные страницы.")

        return "\n".join(lines)

    # Other files
    size_str = _format_size(path.stat().st_size)[1] if path.exists() else "?"
    return f"[Файл: {name}, {size_str}] — прочитай через Read tool: {file_path}"


# ---------------------------------------------------------------------------
# Document Parsing (markdown extraction for LLM context and auto-ingest)
# ---------------------------------------------------------------------------

_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


def parse_document(file_path: str) -> str:
    """Extract document content as markdown.

    Routing:
    - PDF (non-scanned) → pymupdf4llm (tables preserved as GFM)
    - PDF (scanned)     → OCR via pytesseract
    - DOCX/XLSX/PPTX   → markitdown (unchanged existing path)
    - Other            → raw text read

    Returns markdown string (may be empty on failure).
    """
    path = Path(file_path)
    if not path.exists():
        return ""

    ext = path.suffix.lower()

    if ext == ".pdf":
        return _parse_pdf(file_path)

    # DOCX / XLSX / PPTX / HTML / TXT / CSV → markitdown
    if ext in (".docx", ".xlsx", ".xls", ".pptx", ".html", ".htm", ".txt", ".csv", ".md"):
        return _parse_via_markitdown(file_path)

    # Fallback: try markitdown for anything else
    return _parse_via_markitdown(file_path)


def parse_url(url: str) -> str:
    """Fetch and parse a URL (web page or public PDF) via Firecrawl API.

    Requires FIRECRAWL_API_KEY env variable.
    Returns markdown string or empty string on failure.
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY", "")
    if not api_key:
        return ""

    try:
        from firecrawl import Firecrawl
        app = Firecrawl(api_key=api_key)
        result = app.scrape(url, formats=["markdown"])
        # firecrawl-py v2 returns Document object
        if hasattr(result, "markdown"):
            return result.markdown or ""
        if isinstance(result, dict):
            return result.get("markdown", "") or ""
        return ""
    except Exception:
        return ""


def _parse_pdf(file_path: str) -> str:
    """Parse PDF to markdown. Uses pymupdf4llm; falls back to OCR if scanned."""
    # Detect scanned first (fast check)
    scanned = False
    if HAS_FITZ:
        try:
            doc = fitz.open(file_path)
            scanned = _is_scanned(doc)
            doc.close()
        except Exception:
            pass

    if scanned:
        return _parse_scanned_pdf(file_path)

    if HAS_PYMUPDF4LLM:
        try:
            md = pymupdf4llm.to_markdown(
                file_path,
                table_strategy="lines_strict",
                force_text=True,
            )
            return md or ""
        except Exception:
            pass

    # Final fallback: plain text via PyMuPDF
    if HAS_FITZ:
        try:
            doc = fitz.open(file_path)
            pages_text = []
            for page in doc:
                pages_text.append(page.get_text())
            doc.close()
            return "\n\n".join(pages_text)
        except Exception:
            pass

    return ""


def _parse_scanned_pdf(file_path: str) -> str:
    """OCR a scanned PDF using pdf2image + pytesseract."""
    if not HAS_OCR:
        return ""
    try:
        images = convert_from_path(file_path, dpi=200)
        pages_text: list[str] = []
        for img in images:
            text = pytesseract.image_to_string(img, lang="rus+eng")
            pages_text.append(text.strip())
        return "\n\n---\n\n".join(pages_text)
    except Exception:
        return ""


def _parse_via_markitdown(file_path: str) -> str:
    """Convert document to text via markitdown."""
    try:
        from markitdown import MarkItDown
        md_converter = MarkItDown()
        result = md_converter.convert(file_path)
        return result.text_content or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python document_processor.py <file_path>")
        print("\nExample:")
        print("  python document_processor.py /tmp/contract.pdf")
        sys.exit(1)

    target = sys.argv[1]
    print("=" * 60)
    print("analyze_document()")
    print("=" * 60)
    result = analyze_document(target)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print()
    print("=" * 60)
    print("build_file_context()")
    print("=" * 60)
    print(build_file_context(target))
