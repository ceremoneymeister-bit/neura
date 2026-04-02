"""
report_generator.py — генерация markdown-отчёта аудита капсул
"""

from datetime import datetime
from collections import defaultdict


def generate_report(results, capsule_names):
    """
    Generate markdown audit report.
    results: list of TestResult objects
    capsule_names: list of capsule keys tested
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M MSK")

    # Group by capsule
    by_capsule = defaultdict(list)
    cross_capsule = []
    for r in results:
        if r.test_id.startswith("X-"):
            cross_capsule.append(r)
        else:
            by_capsule[r.capsule_name].append(r)

    # Stats
    total = len(results)
    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")
    skipped = sum(1 for r in results if r.status == "skip")
    errored = sum(1 for r in results if r.status == "error")

    # Score: pass=100%, skip=neutral, fail/error=0%
    scorable = total - skipped
    score = int((passed / scorable * 100)) if scorable > 0 else 0

    # Critical = any H-01 fail or M-01 fail
    critical_ids = {"H-01", "H-07", "M-01"}
    critical_count = sum(
        1 for r in results if r.status == "fail" and r.test_id in critical_ids
    )

    lines = []
    lines.append("# 🔍 Capsule Audit Report")
    lines.append(f"**Дата:** {now}")
    lines.append(f"**Капсулы:** {', '.join(capsule_names)}")
    lines.append(f"**Общий балл:** {score}/100")
    lines.append("")
    lines.append("## Сводка")
    lines.append(f"- Протестировано: {len(capsule_names)} капсул, {total} тестов")
    lines.append(
        f"- ✅ Пройдено: {passed} | ❌ Провалено: {failed} | "
        f"⏭️ Пропущено: {skipped} | ⚠️ Ошибок: {errored}"
    )
    if critical_count:
        lines.append(f"- **🚨 Критические проблемы: {critical_count}**")
    else:
        lines.append("- Критические проблемы: 0")
    lines.append("")

    # Per-capsule sections
    for capsule_key in capsule_names:
        cap_results = by_capsule.get(capsule_key, [])
        if not cap_results:
            continue

        cap_passed = sum(1 for r in cap_results if r.status == "pass")
        cap_scorable = sum(1 for r in cap_results if r.status != "skip")
        cap_score = int((cap_passed / cap_scorable * 100)) if cap_scorable > 0 else 0

        lines.append(f"## {capsule_key.title()} ({cap_score}/100)")
        lines.append("")

        # Group by category
        by_category = defaultdict(list)
        for r in cap_results:
            prefix = r.test_id.split("-")[0]
            by_category[prefix].append(r)

        category_labels = {
            "H": "Health",
            "M": "Messaging",
            "F": "Files",
            "I": "Integrations",
            "P": "Personalization",
        }

        for cat_prefix, cat_results in by_category.items():
            cat_passed = sum(1 for r in cat_results if r.status == "pass")
            cat_total = len(cat_results)
            cat_label = category_labels.get(cat_prefix, cat_prefix)
            all_pass = all(r.status in ("pass", "skip") for r in cat_results)
            icon = "✅" if all_pass else "❌"

            lines.append(f"### {cat_label} {icon} {cat_passed}/{cat_total}")
            lines.append("")
            lines.append("| # | Тест | Статус | Детали |")
            lines.append("|---|------|--------|--------|")
            for r in cat_results:
                details = r.details[:80] if r.details else "—"
                details = details.replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {r.test_id} | {r.name} | {r.icon} | {details} |")
            lines.append("")

        # Problems section
        problems = [r for r in cap_results if r.status in ("fail", "error")]
        if problems:
            lines.append("### ❌ Проблемы и рекомендации")
            for r in problems:
                lines.append(f"- **{r.test_id} ({r.name}):** {r.details}")
                if r.log_snippet:
                    lines.append(f"  ```\n  {r.log_snippet[:300]}\n  ```")
            lines.append("")
        else:
            lines.append("### ✅ Проблем не обнаружено")
            lines.append("")

    # Cross-capsule section
    if cross_capsule:
        lines.append("## Cross-Capsule Consistency")
        lines.append("")
        lines.append("| Проверка | " + " | ".join(c.title() for c in capsule_names) + " |")
        lines.append("|----------|" + "|".join(["-------"] * len(capsule_names)) + "|")

        # Group X-tests by ID
        by_test = defaultdict(dict)
        for r in cross_capsule:
            by_test[r.test_id][r.capsule_name] = r

        for test_id in sorted(by_test.keys()):
            row_results = by_test[test_id]
            first = next(iter(row_results.values()))
            cells = []
            for cap in capsule_names:
                r = row_results.get(cap)
                if r:
                    cells.append(r.icon)
                else:
                    cells.append("—")
            lines.append(f"| {test_id}: {first.name} | " + " | ".join(cells) + " |")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Сгенерировано capsule-audit {now}*")

    return "\n".join(lines)


def generate_summary(results, capsule_names):
    """Generate short 1-paragraph summary for HQ notification."""
    total = len(results)
    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")

    score = int((passed / total * 100)) if total > 0 else 0

    if failed == 0:
        return f"🔍 Аудит {', '.join(capsule_names)}: {score}/100 — все {total} тестов пройдены ✅"

    fail_list = [f"{r.test_id}" for r in results if r.status == "fail"]
    return (
        f"🔍 Аудит {', '.join(capsule_names)}: {score}/100 — "
        f"❌ {failed}/{total} провалено: {', '.join(fail_list[:5])}"
    )
