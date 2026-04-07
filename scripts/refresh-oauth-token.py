#!/usr/bin/env python3
"""Auto-refresh Claude Code OAuth tokens.

Single token architecture: all capsules symlink to /root/.claude/.credentials.json.
Run via cron every 3 hours. Token lifetime ~8h, refresh threshold 5h.

Architecture (since 2026-04-07):
  - /root/.claude/.credentials.json → ALL capsules (via symlinks)
  - Legacy files (.claude-bots, .claude-maxim) — ignored, refresh tokens invalid
"""

import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

TOKEN_ENDPOINT = "https://platform.claude.com/v1/oauth/token"
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
SCOPES = "user:inference user:profile user:sessions:claude_code user:file_upload user:mcp_servers"

CREDENTIAL_FILES = [
    Path("/root/.claude/.credentials.json"),        # Дмитрий 20x — основные капсулы
    Path("/root/.claude-maxim/.credentials.json"),  # Максим 5x — Максим + его команда
]

LOG_PATH = Path("/root/Antigravity/logs/oauth-refresh.log")


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


def refresh_one(cred_path: Path) -> bool:
    """Refresh a single credentials file. Returns True on success."""
    label = cred_path.parent.name  # e.g. ".claude", ".claude-bots"

    if not cred_path.exists():
        log(f"[{label}] SKIP: file not found")
        return True  # not an error, just not configured yet

    with open(cred_path) as f:
        creds = json.load(f)

    oauth = creds.get("claudeAiOauth", {})
    refresh_token = oauth.get("refreshToken")
    if not refresh_token:
        log(f"[{label}] SKIP: no refreshToken")
        return True

    # Check if token still has >5h of life — skip refresh
    # Cron runs every 3h, so 5h threshold ensures we always refresh in time
    expires_at = oauth.get("expiresAt", 0)
    remaining_ms = expires_at - int(time.time() * 1000)
    remaining_h = remaining_ms / 3_600_000
    if remaining_h > 5:
        log(f"[{label}] OK: valid for {remaining_h:.1f}h, skip")
        return True

    log(f"[{label}] Token expires in {remaining_h:.1f}h — refreshing...")

    payload = json.dumps({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "scope": SCOPES,
    }).encode()

    req = urllib.request.Request(
        TOKEN_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "claude-code/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        log(f"[{label}] ERROR: HTTP {e.code} — {body[:300]}")
        return False
    except Exception as e:
        log(f"[{label}] ERROR: {e}")
        return False

    new_access = data.get("access_token")
    new_refresh = data.get("refresh_token", refresh_token)
    expires_in = data.get("expires_in", 28800)

    if not new_access:
        log(f"[{label}] ERROR: no access_token in response: {json.dumps(data)[:200]}")
        return False

    # Update credentials
    oauth["accessToken"] = new_access
    oauth["refreshToken"] = new_refresh
    oauth["expiresAt"] = int(time.time() * 1000) + (expires_in * 1000)
    creds["claudeAiOauth"] = oauth

    # Atomic write
    tmp = cred_path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(creds, f, indent=2)
    tmp.replace(cred_path)
    cred_path.chmod(0o600)

    new_expires = datetime.fromtimestamp(oauth["expiresAt"] / 1000)
    log(f"[{label}] OK: refreshed, new expiry: {new_expires.strftime('%Y-%m-%d %H:%M')}")
    return True


def main():
    errors = 0
    for path in CREDENTIAL_FILES:
        if not refresh_one(path):
            errors += 1
    if errors:
        log(f"DONE with {errors} error(s)")
        sys.exit(1)
    else:
        log("DONE: all tokens OK")


if __name__ == "__main__":
    main()
