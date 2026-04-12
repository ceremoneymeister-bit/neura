#!/usr/bin/env python3
"""Auto-refresh Google OAuth tokens for capsules.

Scans all capsule homes for gcal_token.json, refreshes if expired or near-expiry.
Run via cron every 2 hours. Token lifetime ~1h, refresh threshold 30min.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

LOG_PATH = Path("/root/Antigravity/logs/google-token-refresh.log")
HOMES = Path("/opt/neura-v2/homes")
TOKEN_NAME = "gcal_token.json"
REFRESH_THRESHOLD_MIN = 30  # refresh if <30 min remaining


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def refresh_one(token_path: Path) -> bool:
    """Refresh a single Google OAuth token. Returns True on success."""
    capsule = token_path.parent.parent.name  # homes/<name>/data/gcal_token.json

    with open(token_path) as f:
        data = json.load(f)

    if not data.get("refresh_token"):
        log(f"[{capsule}] SKIP: no refresh_token")
        return True

    # Check expiry
    expiry_str = data.get("expiry")
    if expiry_str:
        expiry = datetime.fromisoformat(expiry_str)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        remaining = expiry - datetime.now(timezone.utc)
        remaining_min = remaining.total_seconds() / 60

        if remaining_min > REFRESH_THRESHOLD_MIN:
            log(f"[{capsule}] OK: valid for {remaining_min:.0f}min, skip")
            return True

        log(f"[{capsule}] Token expires in {remaining_min:.0f}min — refreshing...")
    else:
        log(f"[{capsule}] No expiry set — refreshing...")

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        creds = Credentials.from_authorized_user_info(data)
        creds.refresh(Request())

        new_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else data.get("scopes", []),
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }

        with open(token_path, "w") as f:
            json.dump(new_data, f, indent=2)

        log(f"[{capsule}] OK: refreshed, new expiry: {creds.expiry}")
        return True

    except Exception as e:
        log(f"[{capsule}] ERROR: {e}")
        return False


def main():
    tokens = list(HOMES.rglob(TOKEN_NAME))
    if not tokens:
        log("No Google tokens found in capsule homes")
        return

    errors = 0
    for tp in tokens:
        if not refresh_one(tp):
            errors += 1

    if errors:
        log(f"DONE with {errors} error(s)")
        sys.exit(1)
    else:
        log(f"DONE: {len(tokens)} token(s) OK")


if __name__ == "__main__":
    main()
