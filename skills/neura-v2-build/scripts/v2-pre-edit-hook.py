#!/usr/bin/env python3
"""
PreToolUse hook — защищает v1 файлы при работе над v2.
Когда работаем в /opt/neura-v2, блокирует редактирование production capsules.
"""
import sys
import json
import os

# Защищённые пути при работе над v2
PROTECTED_PATHS = [
    "/srv/capsules/",           # Production capsules
    "/opt/neura-app/bridge/",   # Production bridge
    "/opt/neura-app/client/",   # Production web UI
]

# Разрешённые пути (даже внутри protected)
_BASE = os.environ.get("NEURA_BASE", "/opt/neura-v2")
ALLOWED_PATTERNS = [
    f"{_BASE}/",                # Платформа — всегда OK
    f"{_BASE}/docs/",           # Документация — всегда OK
    f"{_BASE}/skills/",         # Скиллы — всегда OK
]

def main():
    # Only activate when v2 build is in progress
    if not os.path.exists("/opt/neura-v2"):
        return

    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    tool_name = data.get("tool_name", "")
    if tool_name not in ("Edit", "Write"):
        return

    file_path = data.get("tool_input", {}).get("file_path", "")

    # Always allow certain paths
    for pattern in ALLOWED_PATTERNS:
        if file_path.startswith(pattern):
            return  # OK

    # Block protected paths
    for protected in PROTECTED_PATHS:
        if file_path.startswith(protected):
            print(json.dumps({
                "decision": "block",
                "reason": (
                    f"🛡️ ЗАЩИТА V1: Файл {file_path} принадлежит production-системе.\n"
                    f"Сейчас мы строим v2 в /opt/neura-v2/.\n"
                    f"Если нужно изменить v1 — сначала выйди из v2-workflow."
                )
            }))
            return

if __name__ == "__main__":
    main()
