#!/usr/bin/env python3
"""OpenRouter balance check — alerts when balance drops below threshold.

Usage:
  python3 scripts/openrouter-balance-check.py          # Check and alert if low
  python3 scripts/openrouter-balance-check.py --json    # JSON output
  python3 scripts/openrouter-balance-check.py --quiet   # Only alert, no output

Cron example (every 6 hours):
  0 */6 * * * cd /opt/neura-v2 && python3 scripts/openrouter-balance-check.py --quiet
"""
import json
import os
import sys
import urllib.request
import urllib.error

# Config
ALERT_THRESHOLD_USD = 1.0  # Alert when remaining < $1
WARNING_THRESHOLD_USD = 2.0  # Warning when remaining < $2
OPENROUTER_DEPOSIT = 5.0  # Total deposit (update when you top up)

def get_balance():
    """Fetch current usage from OpenRouter API."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        # Try loading from .env
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.strip().startswith("OPENROUTER_API_KEY="):
                    api_key = line.strip().split("=", 1)[1]
                    break
    if not api_key:
        return None, "OPENROUTER_API_KEY not found"

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/auth/key",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())["data"]
            return {
                "usage_total": data.get("usage", 0),
                "usage_daily": data.get("usage_daily", 0),
                "usage_weekly": data.get("usage_weekly", 0),
                "usage_monthly": data.get("usage_monthly", 0),
                "deposit": OPENROUTER_DEPOSIT,
                "remaining": round(OPENROUTER_DEPOSIT - data.get("usage", 0), 4),
            }, None
    except Exception as e:
        return None, str(e)


def send_alert(message, level="warning"):
    """Send alert via tg-send.py to Dmitry."""
    tg_send = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'tg-send.py')
    if not os.path.exists(tg_send):
        tg_send = os.path.join(os.path.dirname(__file__), 'tg-send.py')
    if not os.path.exists(tg_send):
        # Fallback: just print
        print(f"ALERT [{level}]: {message}", file=sys.stderr)
        return

    emoji = "🔴" if level == "critical" else "🟡"
    import subprocess
    try:
        subprocess.run(
            ["python3", tg_send, "me", f"{emoji} OpenRouter Balance\n\n{message}"],
            timeout=15, capture_output=True,
        )
    except Exception as e:
        print(f"Alert send failed: {e}", file=sys.stderr)


def main():
    args = sys.argv[1:]
    quiet = "--quiet" in args
    as_json = "--json" in args

    balance, error = get_balance()
    if error:
        if not quiet:
            print(f"Error: {error}")
        sys.exit(1)

    if as_json:
        print(json.dumps(balance, indent=2))
        sys.exit(0)

    remaining = balance["remaining"]

    if not quiet:
        print(f"OpenRouter Balance")
        print(f"  Deposit:    ${balance['deposit']:.2f}")
        print(f"  Used total: ${balance['usage_total']:.4f}")
        print(f"  Used today: ${balance['usage_daily']:.4f}")
        print(f"  Remaining:  ${remaining:.2f}")
        print()

    if remaining < ALERT_THRESHOLD_USD:
        msg = (
            f"Баланс критически низкий: ${remaining:.2f}\n"
            f"Потрачено: ${balance['usage_total']:.2f} из ${balance['deposit']:.2f}\n"
            f"Сегодня: ${balance['usage_daily']:.4f}\n\n"
            f"Нужно пополнить OpenRouter!"
        )
        send_alert(msg, level="critical")
        if not quiet:
            print(f"🔴 CRITICAL: Balance ${remaining:.2f} < ${ALERT_THRESHOLD_USD}")
        sys.exit(2)

    elif remaining < WARNING_THRESHOLD_USD:
        msg = (
            f"Баланс снижается: ${remaining:.2f}\n"
            f"Потрачено: ${balance['usage_total']:.2f} из ${balance['deposit']:.2f}\n"
            f"Сегодня: ${balance['usage_daily']:.4f}"
        )
        send_alert(msg, level="warning")
        if not quiet:
            print(f"🟡 WARNING: Balance ${remaining:.2f} < ${WARNING_THRESHOLD_USD}")
        sys.exit(0)

    else:
        if not quiet:
            print(f"✅ Balance OK: ${remaining:.2f}")
        sys.exit(0)


if __name__ == "__main__":
    main()
