#!/usr/bin/env python3
"""
Stop hook — проверяет что текущий модуль v2 завершён корректно.
Работает ТОЛЬКО когда активна v2-сборка (есть /opt/neura-v2).
"""
import sys
import json
import os
import subprocess
import time

MARKER = "/tmp/.neura-v2-stop-checked"
COOLDOWN_SEC = 120
V2_DIR = "/opt/neura-v2"
PROGRESS_FILE = "/root/Antigravity/docs/neura-v2/PROGRESS.md"

def main():
    # Skip in capsule context
    if os.environ.get("NEURA_CAPSULE") == "1":
        return

    # Only activate when v2 exists
    if not os.path.exists(V2_DIR):
        return

    # Cooldown
    if os.path.exists(MARKER):
        try:
            if time.time() - os.path.getmtime(MARKER) < COOLDOWN_SEC:
                return
        except OSError:
            pass

    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    issues = []

    # Check 1: Run all v2 tests
    test_dir = os.path.join(V2_DIR, "tests")
    if os.path.exists(test_dir) and os.listdir(test_dir):
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", test_dir, "-q", "--tb=line", "--no-header"],
                capture_output=True, text=True, timeout=120,
                cwd=V2_DIR
            )
            if result.returncode != 0:
                failed_lines = [l for l in result.stdout.split('\n') if 'FAILED' in l]
                issues.append(f"🔴 Тесты падают: {'; '.join(failed_lines[:3])}")
        except subprocess.TimeoutExpired:
            issues.append("⏱️ Тесты не завершились за 120 сек")
        except Exception:
            pass

    # Check 2: PROGRESS.md updated recently
    if os.path.exists(PROGRESS_FILE):
        try:
            mtime = os.path.getmtime(PROGRESS_FILE)
            if time.time() - mtime > 3600:  # More than 1 hour old
                issues.append("📋 PROGRESS.md не обновлён (>1 час)")
        except OSError:
            pass
    else:
        issues.append("📋 PROGRESS.md не существует")

    # Touch marker
    try:
        with open(MARKER, 'w') as f:
            f.write(str(time.time()))
    except OSError:
        pass

    if issues:
        print(json.dumps({
            "decision": "block",
            "reason": (
                "🏗️ Neura v2 Build — проверка перед завершением:\n" +
                "\n".join(f"  {i}" for i in issues) +
                "\nИсправь перед завершением, или добавь 💾 если это промежуточный шаг."
            )
        }))

if __name__ == "__main__":
    main()
