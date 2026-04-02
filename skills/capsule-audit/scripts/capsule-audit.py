#!/usr/bin/env python3
"""
capsule-audit.py — оркестратор тестирования капсул
CLI для запуска Layer 1 (функциональных) и Layer 2 (инфраструктурных) тестов.

Usage:
    python3 capsule-audit.py --capsule victoria
    python3 capsule-audit.py --capsule all --category health
    python3 capsule-audit.py --capsule victoria --test M-01
    python3 capsule-audit.py --capsule all --report /tmp/audit.md
    python3 capsule-audit.py --capsule all --dry-run
    python3 capsule-audit.py --capsule all --no-layer1
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_utils import (
    load_profiles,
    load_test_registry,
    validate_bot_token,
    get_service_status,
    get_logs_since,
    filter_errors,
    check_recent_errors,
    validate_sessions_json,
    check_sessions_overloaded,
    check_zombie_claude,
    check_memory_usage,
    check_disk_usage,
    check_diary_exists,
    check_file_valid,
    check_code_contains,
    check_file_exists_in_capsule,
    get_telethon_tester,
    TestResult,
)
from report_generator import generate_report, generate_summary


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "WARN": "⚠️"}.get(level, "")
    print(f"[{ts}] {icon} {msg}")


# ─── Layer 2: Infrastructure tests ─────────────────────────────────

def run_health_test(test, capsule_key, capsule, registry):
    """Run a single health (Layer 2) test."""
    r = TestResult(test["id"], test["name"], capsule_key)
    start = time.time()

    check = test["check"]

    try:
        if check == "service_active":
            ok, details = get_service_status(capsule)
            r.passed(details) if ok else r.failed(details)

        elif check == "recent_errors":
            window = test.get("window_minutes", 10)
            has_errors, snippet = check_recent_errors(capsule, window)
            if has_errors:
                r.failed(f"Errors in last {window} min")
                r.log_snippet = snippet
            else:
                r.passed(f"Clean logs ({window} min)")

        elif check == "sessions_valid":
            path = capsule.get("sessions_path")
            ok, details = validate_sessions_json(path)
            if ok is None:
                r.skipped(details)
            elif ok:
                r.passed(details)
            else:
                r.failed(details)

        elif check == "zombie_claude":
            ok, details = check_zombie_claude(capsule)
            r.passed(details) if ok else r.failed(details)

        elif check == "memory_usage":
            ok, details = check_memory_usage(capsule)
            r.passed(details) if ok else r.failed(details)

        elif check == "disk_usage":
            threshold = test.get("threshold_percent", 90)
            ok, details = check_disk_usage(threshold)
            r.passed(details) if ok else r.failed(details)

        elif check == "bot_token_valid":
            token = capsule.get("bot_token")
            ok, details = validate_bot_token(token)
            if ok is None or not token:
                r.skipped("No token configured")
            elif ok:
                r.passed(details)
            else:
                r.failed(details)

        elif check == "sessions_overloaded":
            path = capsule.get("sessions_path")
            max_msgs = test.get("max_messages", 80)
            ok, details = check_sessions_overloaded(path, max_msgs)
            if ok is None:
                r.skipped(details)
            elif ok:
                r.passed(details)
            else:
                r.failed(details)

        else:
            r.skipped(f"Unknown check: {check}")

    except Exception as e:
        r.errored(str(e))

    r.duration_ms = int((time.time() - start) * 1000)
    log(f"[{capsule_key}] {test['id']} {test['name']}: {r.status} — {r.details}", r.status.upper())
    return r


# ─── Layer 1: Functional tests ─────────────────────────────────────

def get_test_chat(capsule):
    """Determine chat_id and topic_id for testing."""
    # Prefer HQ group with test topic
    hq = capsule.get("hq_group_id")
    topic = capsule.get("test_topic_id")
    if hq:
        return hq, topic
    # For capsules without HQ (like Yulia), try DM to bot
    return None, None


async def run_messaging_test(test, capsule_key, capsule, dry_run=False):
    """Run a single messaging (Layer 1) test via Telethon userbot."""
    r = TestResult(test["id"], test["name"], capsule_key)
    start = time.time()

    bot_id = capsule.get("bot_id")
    if not bot_id:
        r.skipped("No bot_id configured")
        return r

    chat_id, topic_id = get_test_chat(capsule)
    bot_username = capsule.get("bot_username")

    # Need either HQ group or bot_username for DM
    if not chat_id and not bot_username:
        r.skipped("No test chat or bot_username configured")
        return r

    if dry_run:
        r.skipped(f"DRY RUN: would send '{test.get('message', test.get('messages', [''])[0])[:50]}...'")
        return r

    tester = get_telethon_tester()
    check = test["check"]
    timeout = test.get("timeout", 90)
    use_dm = not chat_id  # Fallback to DM if no HQ group

    try:
        ts_before = datetime.now()

        if check == "send_and_wait":
            msg_text = test["message"]

            if use_dm:
                sent = await tester.send_to_dm(bot_username, msg_text)
            else:
                try:
                    sent = await tester.send_to_topic(chat_id, topic_id, msg_text)
                except Exception as hq_err:
                    # Fallback to DM if HQ entity is not accessible
                    if bot_username and "Could not find the input entity" in str(hq_err):
                        use_dm = True
                        sent = await tester.send_to_dm(bot_username, msg_text)
                    else:
                        raise

            if not sent:
                r.failed("Could not send message")
                return r

            if use_dm:
                reply_text, has_file, reply_msg = await tester.wait_for_dm_reply(
                    bot_username, bot_id, sent.id, timeout
                )
            else:
                reply_text, has_file, reply_msg = await tester.wait_for_bot_reply(
                    chat_id, topic_id, bot_id, sent.id, timeout
                )

            if reply_text is None and not has_file:
                r.failed(f"Timeout ({timeout}s)")
                logs = get_logs_since(capsule, ts_before)
                r.log_snippet = filter_errors(logs)
                return r

            # Validate expectation
            expect = test.get("expect", "non_empty")
            if expect == "non_empty":
                if reply_text or has_file:
                    r.passed(f"Got reply ({len(reply_text or '')} chars)")
                else:
                    r.failed("Empty reply")

            elif expect == "has_file":
                if has_file:
                    r.passed("File received")
                else:
                    r.failed("No file in reply")

            elif expect.startswith("contains_any:"):
                keywords = expect.split(":", 1)[1].split(",")
                text_lower = (reply_text or "").lower()
                found = [k for k in keywords if k.lower() in text_lower]
                if found:
                    r.passed(f"Contains: {', '.join(found)}")
                else:
                    r.failed(f"None of [{', '.join(keywords)}] found in reply")

            elif expect.startswith("not_contains:"):
                keywords = expect.split(":", 1)[1].split(",")
                text_lower = (reply_text or "").lower()
                found = [k for k in keywords if k.lower() in text_lower]
                if not found:
                    r.passed("No negative markers")
                else:
                    r.failed(f"Found negative: {', '.join(found)}")

            elif expect == "long_or_telegraph":
                min_len = test.get("min_length", 500)
                is_long = reply_text and len(reply_text) >= min_len
                has_telegraph = reply_text and "telegra.ph" in reply_text
                if is_long or has_telegraph:
                    r.passed(
                        f"{'Telegraph' if has_telegraph else f'{len(reply_text)} chars'}"
                    )
                else:
                    r.failed(
                        f"Too short: {len(reply_text or '')} chars, no Telegraph"
                    )
            else:
                r.passed(f"Reply received ({len(reply_text or '')} chars)")

        elif check == "cancel_and_recover":
            messages = test.get("messages", ["/cancel", "Привет"])
            try:
                if use_dm:
                    await tester.send_to_dm(bot_username, messages[0])
                else:
                    await tester.send_to_topic(chat_id, topic_id, messages[0])
            except Exception as hq_err:
                if bot_username and "Could not find the input entity" in str(hq_err):
                    use_dm = True
                    await tester.send_to_dm(bot_username, messages[0])
                else:
                    raise

            await asyncio.sleep(3)

            if use_dm:
                sent = await tester.send_to_dm(bot_username, messages[1])
            else:
                sent = await tester.send_to_topic(chat_id, topic_id, messages[1])

            if not sent:
                r.failed("Could not send recovery message")
                return r

            if use_dm:
                reply_text, has_file, _ = await tester.wait_for_dm_reply(
                    bot_username, bot_id, sent.id, timeout
                )
            else:
                reply_text, has_file, _ = await tester.wait_for_bot_reply(
                    chat_id, topic_id, bot_id, sent.id, timeout
                )

            if reply_text:
                r.passed(f"Recovered OK ({len(reply_text)} chars)")
            else:
                r.failed("No reply after cancel")

        elif check == "send_file_and_wait":
            file_content = test.get("file_content", "Test content")
            file_name = test.get("file_name", "audit_test.txt")
            tmp_path = f"/tmp/{file_name}"
            with open(tmp_path, "w") as f:
                f.write(file_content)

            caption = test.get("message", "[AUDIT] Что в этом файле?")
            if use_dm:
                sent = await tester.send_file_to_dm(bot_username, tmp_path, caption)
            else:
                try:
                    sent = await tester.send_file_to_topic(chat_id, topic_id, tmp_path, caption)
                except Exception as hq_err:
                    if bot_username and "Could not find the input entity" in str(hq_err):
                        use_dm = True
                        sent = await tester.send_file_to_dm(bot_username, tmp_path, caption)
                    else:
                        os.unlink(tmp_path)
                        raise
            os.unlink(tmp_path)

            if not sent:
                r.failed("Could not send file")
                return r

            if use_dm:
                reply_text, _, _ = await tester.wait_for_dm_reply(
                    bot_username, bot_id, sent.id, timeout
                )
            else:
                reply_text, _, _ = await tester.wait_for_bot_reply(
                    chat_id, topic_id, bot_id, sent.id, timeout
                )

            if reply_text is None:
                r.failed(f"Timeout ({timeout}s)")
            else:
                expect = test.get("expect", "non_empty")
                if expect.startswith("contains_any:"):
                    keywords = expect.split(":", 1)[1].split(",")
                    text_lower = reply_text.lower()
                    found = [k for k in keywords if k.lower() in text_lower]
                    if found:
                        r.passed(f"Contains: {', '.join(found)}")
                    else:
                        r.failed("Expected keywords not found")
                else:
                    r.passed(f"Reply: {len(reply_text)} chars")

        else:
            r.skipped(f"Check type not implemented: {check}")

    except Exception as e:
        r.errored(str(e))

    r.duration_ms = int((time.time() - start) * 1000)
    log(f"[{capsule_key}] {test['id']} {test['name']}: {r.status} — {r.details}", r.status.upper())
    return r


# ─── Layer 2: Personalization tests ────────────────────────────────

async def run_personalization_test(test, capsule_key, capsule, dry_run=False):
    """Run personalization/memory test."""
    r = TestResult(test["id"], test["name"], capsule_key)
    start = time.time()
    check = test["check"]

    try:
        if check == "diary_exists":
            diary_dir = capsule.get("diary_dir")
            ok, details = check_diary_exists(diary_dir)
            if ok is None:
                r.skipped(details)
            elif ok:
                r.passed(details)
            else:
                r.failed(details)

        elif check == "file_valid":
            code_dir = capsule.get("code_dir", "")
            rel_path = test.get("file", "")
            max_entries = test.get("max_entries", 50)
            ok, details = check_file_valid(code_dir, rel_path, max_entries)
            if ok is None:
                r.skipped(details)
            elif ok:
                r.passed(details)
            else:
                r.failed(details)

        elif check == "send_and_wait":
            # This is a Layer 1 test within personalization
            return await run_messaging_test(test, capsule_key, capsule, dry_run)

        else:
            r.skipped(f"Unknown check: {check}")

    except Exception as e:
        r.errored(str(e))

    r.duration_ms = int((time.time() - start) * 1000)
    log(f"[{capsule_key}] {test['id']} {test['name']}: {r.status} — {r.details}", r.status.upper())
    return r


# ─── Cross-capsule tests ───────────────────────────────────────────

def run_cross_capsule_test(test, capsule_key, capsule):
    """Run cross-capsule consistency test."""
    r = TestResult(test["id"], test["name"], capsule_key)
    start = time.time()
    check = test["check"]

    try:
        code_dir = capsule.get("code_dir", "")

        if check == "function_signature":
            func = test.get("function", "")
            ok, details = check_code_contains(code_dir, [func])
            if ok:
                r.passed(f"Found {func}")
            else:
                r.failed(details)

        elif check == "code_contains":
            patterns = test.get("patterns", [])
            ok, details = check_code_contains(code_dir, patterns)
            if ok:
                r.passed(details)
            else:
                r.failed(details)

        elif check == "file_exists":
            filename = test.get("file", "")
            ok, details = check_file_exists_in_capsule(code_dir, filename)
            if ok:
                r.passed(details)
            else:
                r.failed(details)

        elif check == "sessions_schema":
            path = capsule.get("sessions_path")
            ok, details = validate_sessions_json(path)
            if ok is None:
                r.skipped(details)
            elif ok:
                r.passed(details)
            else:
                r.failed(details)

        else:
            r.skipped(f"Unknown check: {check}")

    except Exception as e:
        r.errored(str(e))

    r.duration_ms = int((time.time() - start) * 1000)
    log(f"[{capsule_key}] {test['id']} {test['name']}: {r.status} — {r.details}", r.status.upper())
    return r


# ─── Orchestrator ───────────────────────────────────────────────────

LAYER1_CATEGORIES = {"messaging", "files", "integrations"}


async def run_audit(capsule_keys, categories=None, test_id=None, dry_run=False, no_layer1=False):
    """Run full audit. Returns list of TestResult."""
    profiles = load_profiles()
    registry = load_test_registry()
    results = []

    all_categories = registry.get("categories", {})

    # Filter categories
    if categories:
        run_cats = {k: v for k, v in all_categories.items() if k in categories}
    else:
        run_cats = all_categories

    # Check if we need Telethon (any Layer 1 tests to run)
    needs_telethon = not no_layer1 and not dry_run and any(
        cat in LAYER1_CATEGORIES for cat in run_cats
    )
    # Also personalization can have send_and_wait tests
    if not needs_telethon and "personalization" in run_cats and not no_layer1 and not dry_run:
        for test in run_cats.get("personalization", {}).get("tests", []):
            if test.get("check") == "send_and_wait":
                needs_telethon = True
                break

    tester = None
    if needs_telethon:
        try:
            tester = get_telethon_tester()
            me = await tester.connect()
            log(f"Telethon подключён: {me.first_name} (@{me.username})")
        except Exception as e:
            log(f"Telethon ошибка: {e} — Layer 1 тесты будут пропущены", "WARN")
            no_layer1 = True

    try:
        for cap_key in capsule_keys:
            capsule = profiles.get(cap_key)
            if not capsule:
                log(f"Unknown capsule: {cap_key}", "WARN")
                continue

            log(f"=== Аудит: {capsule.get('name', cap_key)} ===")

            for cat_name, cat_data in run_cats.items():
                tests = cat_data.get("tests", [])

                for test in tests:
                    if test_id and test["id"] != test_id:
                        continue

                    req_cap = test.get("requires_capability")
                    if req_cap and req_cap not in capsule.get("capabilities", []):
                        r = TestResult(test["id"], test["name"], cap_key)
                        r.skipped(f"Requires: {req_cap}")
                        results.append(r)
                        continue

                    if cat_name == "health":
                        r = run_health_test(test, cap_key, capsule, registry)
                    elif cat_name in LAYER1_CATEGORIES:
                        if no_layer1:
                            r = TestResult(test["id"], test["name"], cap_key)
                            r.skipped("Layer 1 отключён (--no-layer1)")
                        else:
                            r = await run_messaging_test(test, cap_key, capsule, dry_run)
                    elif cat_name == "personalization":
                        r = await run_personalization_test(test, cap_key, capsule, dry_run if not no_layer1 else True)
                    elif cat_name == "cross_capsule":
                        r = run_cross_capsule_test(test, cap_key, capsule)
                    else:
                        r = TestResult(test["id"], test["name"], cap_key)
                        r.skipped(f"Unknown category: {cat_name}")

                    results.append(r)
    finally:
        if tester:
            await tester.disconnect()
            log("Telethon отключён")

    return results


async def async_main():
    parser = argparse.ArgumentParser(description="Capsule Audit — тестирование ботов")
    parser.add_argument(
        "--capsule", required=True,
        help="Capsule key (victoria/marina/yulia/maxim) or 'all'"
    )
    parser.add_argument(
        "--category",
        help="Comma-separated categories: health,messaging,files,integrations,personalization,cross_capsule"
    )
    parser.add_argument("--test", help="Run specific test by ID (e.g., H-01, M-01)")
    parser.add_argument("--report", help="Save markdown report to file")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without sending messages")
    parser.add_argument("--no-layer1", action="store_true", help="Skip Layer 1 (messaging) tests")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    # Determine capsules
    profiles = load_profiles()
    if args.capsule == "all":
        capsule_keys = list(profiles.keys())
    else:
        capsule_keys = [k.strip() for k in args.capsule.split(",")]

    # Determine categories
    categories = None
    if args.category:
        categories = [c.strip() for c in args.category.split(",")]

    log(f"Capsule Audit начат: {', '.join(capsule_keys)}")
    if args.dry_run:
        log("🏜️ DRY RUN — сообщения НЕ будут отправлены")
    if args.no_layer1:
        log("⏭️ Layer 1 (messaging) тесты отключены")
    if categories:
        log(f"Категории: {', '.join(categories)}")
    if args.test:
        log(f"Конкретный тест: {args.test}")

    print()

    # Run
    results = await run_audit(
        capsule_keys,
        categories=categories,
        test_id=args.test,
        dry_run=args.dry_run,
        no_layer1=args.no_layer1,
    )

    print()

    # Output
    if args.json:
        output = [r.to_dict() for r in results]
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        # Summary
        passed = sum(1 for r in results if r.status == "pass")
        failed = sum(1 for r in results if r.status == "fail")
        skipped = sum(1 for r in results if r.status == "skip")
        total = len(results)
        print(f"{'='*50}")
        print(f"Итого: {total} тестов | ✅ {passed} | ❌ {failed} | ⏭️ {skipped}")
        print(f"{'='*50}")

        if failed > 0:
            print("\n❌ Провалено:")
            for r in results:
                if r.status == "fail":
                    print(f"  {r.test_id} [{r.capsule_name}] {r.name}: {r.details}")
                    if r.log_snippet:
                        for line in r.log_snippet.split("\n")[:3]:
                            print(f"    | {line}")

    # Report
    if args.report:
        report = generate_report(results, capsule_keys)
        with open(args.report, "w") as f:
            f.write(report)
        log(f"Отчёт сохранён: {args.report}")

        summary = generate_summary(results, capsule_keys)
        print(f"\n{summary}")

    return 0 if failed == 0 else 1


def main():
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
