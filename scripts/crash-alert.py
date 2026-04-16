#!/usr/bin/env python3
"""Send crash alert to HQ infra channel when neura-v2 stops unexpectedly.

Called via systemd ExecStopPost=. Uses $SERVICE_RESULT env var:
  success    — clean shutdown (no alert)
  exit-code  — non-zero exit (crash)
  signal     — killed by SIGKILL/OOM
  core-dump  — process core dumped
  watchdog   — watchdog timeout
  timeout    — stop timeout
"""
import json
import os
import sys
import urllib.parse
import urllib.request

SERVICE_RESULT = os.environ.get("SERVICE_RESULT", "unknown")

# Clean stop — no alert needed
if SERVICE_RESULT == "success":
    sys.exit(0)

BOT_TOKEN = "8674618358:AAHINXfvxnungqyUnmNwh8UEIPKjBaDnifY"
GROUP_ID = -1003417427556
TOPIC_ID = 8

RESULT_LABELS = {
    "exit-code":  "Ненулевой код выхода",
    "signal":     "Убит сигналом (SIGKILL/OOM)",
    "core-dump":  "Core dump",
    "watchdog":   "Watchdog timeout",
    "timeout":    "Timeout при остановке",
    "resources":  "Ресурсы исчерпаны",
}
label = RESULT_LABELS.get(SERVICE_RESULT, SERVICE_RESULT)
server_name = os.environ.get("SERVER_NAME", "Aeza")

text = (
    f"<b>[NEURA-V2]</b> 💥 SERVICE_CRASH\n"
    f"{server_name} | Причина: {label}\n"
    f"systemd перезапустит через 10 сек...\n"
    f"<i>Лог: journalctl -u neura-v2 -n 30</i>"
)

data = urllib.parse.urlencode({
    "chat_id": GROUP_ID,
    "message_thread_id": TOPIC_ID,
    "text": text,
    "parse_mode": "HTML",
}).encode()

try:
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=data,
    )
    urllib.request.urlopen(req, timeout=10)
except Exception as e:
    print(f"crash-alert: failed to send: {e}", file=sys.stderr)
    sys.exit(1)
