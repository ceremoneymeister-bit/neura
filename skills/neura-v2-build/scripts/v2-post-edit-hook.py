#!/usr/bin/env python3
"""
PostToolUse hook — автоматически запускает pytest после изменения файлов Neura v2.
Только для файлов в /opt/neura-v2/neura/ (не для тестов, конфигов, доков).
"""
import sys
import json
import os
import subprocess
import time

COOLDOWN_SEC = 30
MARKER = "/tmp/.neura-v2-pytest-ran"
V2_SRC = "/opt/neura-v2/neura/"
V2_TESTS = "/opt/neura-v2/tests/"

def main():
    # Skip in capsule context
    if os.environ.get("NEURA_CAPSULE") == "1":
        return

    # Read hook input
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    tool_name = data.get("tool_name", "")
    if tool_name not in ("Edit", "Write"):
        return

    file_path = data.get("tool_input", {}).get("file_path", "")

    # Only trigger for v2 source files (not tests, not configs)
    if not file_path.startswith(V2_SRC):
        return

    # Cooldown
    if os.path.exists(MARKER):
        try:
            if time.time() - os.path.getmtime(MARKER) < COOLDOWN_SEC:
                return
        except OSError:
            pass

    # Touch marker
    try:
        with open(MARKER, 'w') as f:
            f.write(str(time.time()))
    except OSError:
        pass

    # Determine which test file to run
    # neura/core/engine.py → tests/test_engine.py
    module_name = os.path.basename(file_path).replace('.py', '')
    test_file = os.path.join(V2_TESTS, f"test_{module_name}.py")

    if not os.path.exists(test_file):
        # No test file yet — remind to create one
        print(json.dumps({
            "decision": "approve",
            "reason": f"⚠️ Нет тестов для {module_name}! Создай {test_file} (Gate 2 workflow)."
        }))
        return

    # Run pytest
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", test_file, "-v", "--tb=short", "--no-header", "-q"],
            capture_output=True, text=True, timeout=60,
            cwd="/opt/neura-v2"
        )

        output = result.stdout.strip()
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")

        if failed > 0:
            print(json.dumps({
                "decision": "approve",
                "reason": f"🔴 pytest: {failed} FAILED, {passed} PASSED в {test_file}\n{output[-500:]}"
            }))
        elif passed > 0:
            print(json.dumps({
                "decision": "approve",
                "reason": f"🟢 pytest: {passed} PASSED в {test_file}"
            }))
    except subprocess.TimeoutExpired:
        print(json.dumps({
            "decision": "approve",
            "reason": f"⏱️ pytest timeout (60s) для {test_file}"
        }))
    except Exception as e:
        # Don't block on hook errors
        pass

if __name__ == "__main__":
    main()
