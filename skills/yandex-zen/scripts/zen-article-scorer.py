#!/usr/bin/env python3
"""
Zen Article Scorer -- scores a markdown/text article on 6 axes for Yandex Dzen readiness.

Axes (weighted total 0-100):
  1. Title Quality   (25%)  -- length, keyword presence, no clickbait
  2. Structure        (20%)  -- paragraphs, subheadings, lists
  3. Length           (15%)  -- 3000-5000 chars optimal
  4. Images           (15%)  -- image references/placeholders (3-4 ideal)
  5. SEO              (15%)  -- keyword in title & first paragraph, meta desc
  6. AI Check         (10%)  -- scans for AI-marker phrases

Usage:
    python3 zen-article-scorer.py article.md
    python3 zen-article-scorer.py article.md --keyword "искусственный интеллект"
    python3 zen-article-scorer.py article.md --keyword "дзен" --json
"""

import argparse
import json
import os
import re
import sys


# ---------------------------------------------------------------------------
# AI marker phrases (from article-writing.md reference + extended list)
# ---------------------------------------------------------------------------
AI_MARKER_PHRASES = [
    # Introductory constructions
    "важно отметить",
    "следует подчеркнуть",
    "необходимо учитывать",
    "стоит обратить внимание",
    "нельзя не отметить",
    "давайте рассмотрим",
    "давайте разберёмся",
    "давайте разберемся",
    # "Modern world" cliches
    "в современном мире",
    "в эпоху цифровизации",
    "в наше время",
    "на сегодняшний день",
    "в мире где",
    "в мире, где",
    # Bureaucratic language
    "данный",
    "вышеупомянутый",
    "осуществлять",
    "в рамках",
    "в целях",
    "посредством",
    "в соответствии с",
    "на основании",
    # Verbal cliches
    "играет важную роль",
    "оказывает влияние",
    "имеет большое значение",
    "является неотъемлемой частью",
    "является ключевым",
    "способствует развитию",
    "открывает новые горизонты",
    # Concluding phrases
    "подводя итог",
    "резюмируя вышесказанное",
    "таким образом, можно сделать вывод",
    "в заключение хотелось бы отметить",
    "в заключение",
    # Inter-paragraph connectors (overused by AI)
    "кроме того",
    "более того",
    "помимо этого",
    "также стоит отметить",
    "при этом важно понимать",
    # Extra markers
    "стоит отметить",
    "важно понимать",
    "реализовывать",
    "указанный",
]

CLICKBAIT_WORDS = [
    "шок",
    "сенсация",
    "не поверите",
    "вы не поверите",
    "невероятно",
    "скандал",
    "жесть",
    "срочно",
    "только сегодня",
    "секрет раскрыт",
]


def read_article(path: str) -> str:
    """Read article text from file."""
    if not os.path.isfile(path):
        print(f"[ERROR] File not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_title(text: str) -> str:
    """Extract the first heading (# ...) or the first non-empty line as title."""
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Markdown heading
        m = re.match(r"^#{1,3}\s+(.+)$", line)
        if m:
            return m.group(1).strip()
        # First non-empty line as fallback
        return line
    return ""


def extract_first_paragraph(text: str) -> str:
    """Extract the first paragraph of body text (after title)."""
    lines = text.split("\n")
    body_started = False
    para_lines = []
    for line in lines:
        stripped = line.strip()
        if not body_started:
            if stripped and not re.match(r"^#{1,6}\s+", stripped):
                body_started = True
                para_lines.append(stripped)
            elif re.match(r"^#{1,6}\s+", stripped):
                # skip title line
                body_started = True
                continue
        else:
            if stripped == "":
                if para_lines:
                    break
            else:
                para_lines.append(stripped)
    return " ".join(para_lines)


def count_subheadings(text: str) -> int:
    """Count ## or ### headings (excluding the main title)."""
    headings = re.findall(r"^#{2,6}\s+.+$", text, re.MULTILINE)
    return len(headings)


def count_list_items(text: str) -> int:
    """Count markdown list items (- or * or 1.)."""
    items = re.findall(r"^[\s]*[-*]\s+.+$|^[\s]*\d+\.\s+.+$", text, re.MULTILINE)
    return len(items)


def count_paragraphs(text: str) -> int:
    """Count non-empty paragraph blocks."""
    blocks = re.split(r"\n\s*\n", text)
    return sum(1 for b in blocks if b.strip())


def count_images(text: str) -> int:
    """Count image references: ![...], [IMAGE], {image}, <img ...>, or common placeholders."""
    patterns = [
        r"!\[.*?\]\(.*?\)",          # ![alt](url)
        r"\[IMAGE\]",                # [IMAGE] placeholder
        r"\[ИЗОБРАЖЕНИЕ\]",          # [ИЗОБРАЖЕНИЕ] placeholder
        r"\{image[^}]*\}",           # {image} placeholder
        r"<img\s[^>]*>",             # HTML img tag
        r"\[cover\]",                # [cover] placeholder
        r"\[обложка\]",              # [обложка] placeholder
        r"\[фото\]",                 # [фото] placeholder
        r"\[картинка\]",             # [картинка] placeholder
        r"!\[",                      # partial markdown image
    ]
    total = 0
    for pat in patterns:
        total += len(re.findall(pat, text, re.IGNORECASE))
    return total


def check_meta_description(text: str) -> bool:
    """Check if there's a meta description marker (common in CMS-ready articles)."""
    patterns = [
        r"^meta[\s_-]*desc",
        r"^description:",
        r"^описание:",
        r"^\*\*описание\*\*",
        r"^<!-- desc",
    ]
    for line in text.split("\n")[:15]:
        for pat in patterns:
            if re.search(pat, line.strip(), re.IGNORECASE):
                return True
    return False


# ---------------------------------------------------------------------------
# Scoring functions (each returns score 0-10 + list of recommendations)
# ---------------------------------------------------------------------------

def score_title(title: str, keyword: str | None) -> tuple[float, list[str]]:
    """Score title quality (0-10)."""
    score = 10.0
    recs = []
    length = len(title)

    if not title:
        return 0.0, ["Title is missing. Add a compelling headline."]

    # Length scoring: 50-60 ideal
    if 50 <= length <= 60:
        pass  # perfect
    elif 40 <= length < 50 or 60 < length <= 70:
        score -= 1.5
        recs.append(f"Title length {length} chars -- ideal is 50-60 chars (won't be cut off in feed).")
    elif 30 <= length < 40 or 70 < length <= 80:
        score -= 3.0
        recs.append(f"Title length {length} chars -- too {'short' if length < 50 else 'long'}. Aim for 50-60.")
    else:
        score -= 5.0
        recs.append(f"Title length {length} chars -- significantly outside optimal range 50-60.")

    # Keyword check
    if keyword:
        if keyword.lower() not in title.lower():
            score -= 2.5
            recs.append(f'Keyword "{keyword}" not found in title. Include it for SEO.')

    # Clickbait check
    title_lower = title.lower()
    found_clickbait = [w for w in CLICKBAIT_WORDS if w in title_lower]
    if found_clickbait:
        score -= 3.0
        recs.append(f"Clickbait words detected: {', '.join(found_clickbait)}. Dzen penalizes clickbait (shows only to subscribers).")

    # Has numbers (positive signal)
    if re.search(r"\d+", title):
        score += 0.5
        # Cap at 10
        score = min(score, 10.0)

    return max(0.0, score), recs


def score_structure(text: str) -> tuple[float, list[str]]:
    """Score article structure (0-10)."""
    score = 10.0
    recs = []

    paragraphs = count_paragraphs(text)
    subheadings = count_subheadings(text)
    list_items = count_list_items(text)

    # Paragraphs: 5-15 ideal
    if paragraphs < 3:
        score -= 4.0
        recs.append(f"Only {paragraphs} paragraph(s). Break text into 5-15 logical blocks for better readability.")
    elif paragraphs < 5:
        score -= 2.0
        recs.append(f"{paragraphs} paragraphs -- add more structure. Aim for 5-15.")
    elif paragraphs > 20:
        score -= 1.0
        recs.append(f"{paragraphs} paragraphs -- might be too fragmented. Consider merging some.")

    # Subheadings: at least 2-3 for a full article
    if subheadings == 0:
        score -= 3.0
        recs.append("No subheadings found. Add 2-4 subheadings (##) to improve structure and scannability.")
    elif subheadings == 1:
        score -= 1.5
        recs.append("Only 1 subheading. Add at least 2-3 for better navigation.")
    elif subheadings > 8:
        score -= 0.5
        recs.append(f"{subheadings} subheadings -- consider consolidating to avoid over-segmentation.")

    # List items (bonus)
    if list_items == 0:
        score -= 1.0
        recs.append("No list items. Lists improve scannability and reader retention.")
    elif list_items > 20:
        score -= 0.5
        recs.append(f"{list_items} list items -- consider converting some to prose for variety.")

    return max(0.0, score), recs


def score_length(text: str) -> tuple[float, list[str]]:
    """Score article length (0-10). Optimal: 3000-5000 chars."""
    # Strip markdown formatting for char count
    plain = re.sub(r"!\[.*?\]\(.*?\)", "", text)  # remove images
    plain = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", plain)  # links -> text
    plain = re.sub(r"[#*_~`>]", "", plain)  # remove md formatting
    char_count = len(plain.strip())

    score = 10.0
    recs = []

    if 3000 <= char_count <= 5000:
        recs.append(f"Article length: {char_count} chars -- optimal range.")
    elif 2500 <= char_count < 3000:
        score -= 2.0
        recs.append(f"Article length: {char_count} chars -- slightly short. Add 500+ chars for optimal 3000-5000 range.")
    elif 5000 < char_count <= 6000:
        score -= 1.0
        recs.append(f"Article length: {char_count} chars -- slightly above optimal. Consider trimming or ensure strong engagement.")
    elif 1500 <= char_count < 2500:
        score -= 4.0
        recs.append(f"Article length: {char_count} chars -- too short. Dzen articles need 3000-5000 chars to rank well.")
    elif 6000 < char_count <= 8000:
        score -= 2.5
        recs.append(f"Article length: {char_count} chars -- long. Ensure high engagement or split into a series.")
    elif char_count < 1500:
        score -= 7.0
        recs.append(f"Article length: {char_count} chars -- critically short. Minimum 3000 chars needed.")
    else:
        score -= 4.0
        recs.append(f"Article length: {char_count} chars -- very long ({char_count}). Risk of low read-through rate.")

    return max(0.0, score), recs


def score_images(text: str) -> tuple[float, list[str]]:
    """Score image count (0-10). Ideal: 3-4 images."""
    img_count = count_images(text)
    score = 10.0
    recs = []

    if img_count == 0:
        score = 2.0
        recs.append("No image references found. Add 3-4 images (first one becomes the cover on Dzen).")
    elif img_count == 1:
        score = 5.0
        recs.append(f"{img_count} image -- add 2-3 more to break up text and improve engagement.")
    elif img_count == 2:
        score = 7.0
        recs.append(f"{img_count} images -- close to ideal. One more would help.")
    elif 3 <= img_count <= 4:
        recs.append(f"{img_count} images -- ideal count for Dzen articles.")
    elif 5 <= img_count <= 6:
        score = 8.0
        recs.append(f"{img_count} images -- slightly above ideal, but OK if each carries meaning.")
    else:
        score = 6.0
        recs.append(f"{img_count} images -- too many. Each image should add value, not pad the article.")

    return max(0.0, score), recs


def score_seo(text: str, title: str, keyword: str | None) -> tuple[float, list[str]]:
    """Score SEO readiness (0-10)."""
    score = 10.0
    recs = []

    first_para = extract_first_paragraph(text)
    has_meta = check_meta_description(text)

    if not keyword:
        score = 5.0
        recs.append("No keyword provided (--keyword). Cannot fully assess SEO. Provide a target keyword for accurate scoring.")
        if not has_meta:
            score -= 1.0
            recs.append("No meta description found. Add a 150-160 char description for search engines.")
        return max(0.0, score), recs

    kw_lower = keyword.lower()

    # Keyword in title
    if kw_lower not in title.lower():
        score -= 3.0
        recs.append(f'Keyword "{keyword}" not in title. Critical for Dzen SEO.')

    # Keyword in first paragraph
    if kw_lower not in first_para.lower():
        score -= 3.0
        recs.append(f'Keyword "{keyword}" not in first paragraph. Place it early for better ranking.')

    # Meta description
    if not has_meta:
        score -= 2.0
        recs.append("No meta description found. Add a 150-160 char description for search discoverability.")

    # Keyword density check (rough)
    text_lower = text.lower()
    kw_count = text_lower.count(kw_lower)
    word_count = len(text.split())
    if word_count > 0:
        density = (kw_count / word_count) * 100
        if density < 0.5:
            score -= 1.0
            recs.append(f'Keyword density ~{density:.1f}% -- low. Mention "{keyword}" a few more times naturally.')
        elif density > 3.0:
            score -= 1.5
            recs.append(f'Keyword density ~{density:.1f}% -- too high. Risk of keyword stuffing penalty.')

    return max(0.0, score), recs


def score_ai_check(text: str) -> tuple[float, list[str]]:
    """Score AI detection risk (0-10). Higher = cleaner from AI markers."""
    score = 10.0
    recs = []

    text_lower = text.lower()
    found_markers = []

    for phrase in AI_MARKER_PHRASES:
        if phrase.lower() in text_lower:
            found_markers.append(phrase)

    marker_count = len(found_markers)

    if marker_count == 0:
        recs.append("No AI-marker phrases detected. Clean text.")
    elif marker_count <= 2:
        score -= 2.0
        recs.append(f"Found {marker_count} AI-marker phrase(s): {', '.join(found_markers[:5])}. Consider rephrasing.")
    elif marker_count <= 5:
        score -= 4.0
        recs.append(f"Found {marker_count} AI-marker phrases. High risk of AI detection. Rephrase these: {', '.join(found_markers[:5])}.")
    elif marker_count <= 10:
        score -= 6.0
        recs.append(f"Found {marker_count} AI-marker phrases. Text will likely be flagged by Dzen's AI detector. Major rewrite needed.")
    else:
        score -= 8.0
        recs.append(f"Found {marker_count} AI-marker phrases! Text is almost certainly AI-generated in Dzen's eyes. Full rewrite required.")

    if found_markers and marker_count > 2:
        recs.append(f"Full list: {', '.join(found_markers)}")

    return max(0.0, score), recs


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

AXIS_NAMES = [
    ("Title Quality", 0.25),
    ("Structure", 0.20),
    ("Length", 0.15),
    ("Images", 0.15),
    ("SEO", 0.15),
    ("AI Check", 0.10),
]


def grade_label(score: float) -> str:
    """Convert 0-10 score to a letter grade."""
    if score >= 9.0:
        return "A+"
    elif score >= 8.0:
        return "A"
    elif score >= 7.0:
        return "B"
    elif score >= 5.5:
        return "C"
    elif score >= 4.0:
        return "D"
    else:
        return "F"


def bar_visual(score: float, width: int = 20) -> str:
    """Create a simple text bar visualization."""
    filled = int(round(score / 10.0 * width))
    empty = width - filled
    return "[" + "#" * filled + "-" * empty + "]"


def generate_report(
    scores: list[tuple[float, list[str]]],
    title: str,
    keyword: str | None,
    filepath: str,
) -> str:
    """Generate formatted text report."""
    lines = []
    lines.append("=" * 60)
    lines.append("  ZEN ARTICLE SCORER -- Report Card")
    lines.append("=" * 60)
    lines.append(f"  File:    {filepath}")
    lines.append(f"  Title:   {title[:55]}{'...' if len(title) > 55 else ''}")
    if keyword:
        lines.append(f"  Keyword: {keyword}")
    lines.append("-" * 60)
    lines.append("")

    weighted_total = 0.0
    max_possible = 0.0

    for i, ((axis_name, weight), (score, recs)) in enumerate(zip(AXIS_NAMES, scores)):
        weighted = score * weight * 10  # scale to 0-25/20/15 etc.
        weighted_total += weighted
        max_possible += 10 * weight * 10

        grade = grade_label(score)
        bar = bar_visual(score)

        lines.append(f"  {i+1}. {axis_name} ({int(weight*100)}%)")
        lines.append(f"     Score: {score:.1f}/10  {bar}  [{grade}]")
        for rec in recs:
            lines.append(f"     -> {rec}")
        lines.append("")

    # Total score (0-100)
    total_pct = (weighted_total / max_possible) * 100 if max_possible > 0 else 0
    total_grade = grade_label(total_pct / 10)

    lines.append("-" * 60)
    lines.append(f"  TOTAL SCORE: {total_pct:.0f}/100  [{total_grade}]")
    lines.append("-" * 60)

    # Summary recommendation
    if total_pct >= 85:
        lines.append("  -> Ready to publish! Minor tweaks optional.")
    elif total_pct >= 70:
        lines.append("  -> Good article. Address the recommendations above before publishing.")
    elif total_pct >= 50:
        lines.append("  -> Needs work. Fix the highlighted issues for better Dzen performance.")
    else:
        lines.append("  -> Major revisions needed. Rewrite sections with low scores.")

    lines.append("=" * 60)
    return "\n".join(lines)


def generate_json_report(
    scores: list[tuple[float, list[str]]],
    title: str,
    keyword: str | None,
    filepath: str,
) -> dict:
    """Generate JSON report structure."""
    axes = {}
    weighted_total = 0.0
    max_possible = 0.0

    for (axis_name, weight), (score, recs) in zip(AXIS_NAMES, scores):
        weighted = score * weight * 10
        weighted_total += weighted
        max_possible += 10 * weight * 10
        axes[axis_name] = {
            "score": round(score, 1),
            "weight": weight,
            "grade": grade_label(score),
            "recommendations": recs,
        }

    total_pct = (weighted_total / max_possible) * 100 if max_possible > 0 else 0

    return {
        "file": filepath,
        "title": title,
        "keyword": keyword,
        "total_score": round(total_pct, 1),
        "total_grade": grade_label(total_pct / 10),
        "axes": axes,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Score a markdown/text article for Yandex Dzen readiness.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 zen-article-scorer.py article.md
  python3 zen-article-scorer.py article.md --keyword "заработок на дзене"
  python3 zen-article-scorer.py article.md --keyword "рецепты" --json
""",
    )
    parser.add_argument("article", help="Path to markdown or text file to score")
    parser.add_argument(
        "--keyword", "-k",
        default=None,
        help="Target keyword/keyphrase for SEO scoring",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report as JSON instead of formatted text",
    )
    args = parser.parse_args()

    text = read_article(args.article)
    title = extract_title(text)

    # Run all scoring axes
    scores = [
        score_title(title, args.keyword),
        score_structure(text),
        score_length(text),
        score_images(text),
        score_seo(text, title, args.keyword),
        score_ai_check(text),
    ]

    if args.json:
        report = generate_json_report(scores, title, args.keyword, args.article)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        report = generate_report(scores, title, args.keyword, args.article)
        print(report)


if __name__ == "__main__":
    main()
