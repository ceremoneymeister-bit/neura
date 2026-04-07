"""
audit_utils.py — утилиты для capsule-audit
Telethon userbot для Layer 1, Bot API для валидации токенов,
log readers, SSH wrapper, validators
"""

import asyncio
import json
import os
import re
import subprocess
import time
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"

# Status message patterns to skip when waiting for bot reply
SKIP_PATTERNS = [
    "Думаю", "Анализирую", "Обрабатываю", "Генерирую",
    "Ищу", "Читаю", "Загружаю", "⏳", "🔄", "💭",
    "Подождите", "Секунду", "Минутку",
]

ERROR_PATTERNS = [
    "ERROR", "CRITICAL", "Traceback", "Exception",
    "oom-kill", "Out of memory", "SIGKILL",
]


def load_profiles():
    """Load capsule profiles from config."""
    with open(CONFIG_DIR / "capsule-profiles.json") as f:
        return json.load(f)


def load_test_registry():
    """Load test registry from config."""
    with open(CONFIG_DIR / "test-registry.json") as f:
        return json.load(f)


# ─── Bot API helpers ───────────────────────────────────────────────

def bot_api_call(token, method, params=None):
    """Call Telegram Bot API method."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    if params:
        data = json.dumps(params).encode()
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
    else:
        req = Request(url)
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except URLError as e:
        return {"ok": False, "error": str(e)}


def bot_api_upload(token, method, file_path, params=None):
    """Upload file via Bot API multipart/form-data."""
    import mimetypes
    boundary = f"----AuditBoundary{int(time.time())}"
    body = b""

    # Add params
    if params:
        for key, val in params.items():
            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
            body += f"{val}\r\n".encode()

    # Add file
    fname = os.path.basename(file_path)
    mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="document"; filename="{fname}"\r\n'.encode()
    body += f"Content-Type: {mime}\r\n\r\n".encode()
    with open(file_path, "rb") as f:
        body += f.read()
    body += f"\r\n--{boundary}--\r\n".encode()

    url = f"https://api.telegram.org/bot{token}/{method}"
    req = Request(url, data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except URLError as e:
        return {"ok": False, "error": str(e)}


def validate_bot_token(token):
    """Validate bot token via getMe."""
    if not token:
        return False, "No token"
    result = bot_api_call(token, "getMe")
    if result.get("ok"):
        bot = result["result"]
        return True, f"@{bot.get('username', 'unknown')}"
    return False, result.get("description", "Unknown error")


# ─── Telethon-based Layer 1 tester ─────────────────────────────────

class TelethonTester:
    """Telethon userbot for sending test messages and receiving bot replies."""

    SESSION = os.environ.get("TELETHON_SESSION", os.path.join(
        os.environ.get("NEURA_BASE", "/opt/neura-v2"), "data", "telegram_userbot_parser"))
    API_ID = 33869550
    API_HASH = "bcc80776767204e74d728936e1e124a3"

    def __init__(self):
        self.client = None

    async def connect(self):
        """Connect Telethon client."""
        from telethon import TelegramClient
        self.client = TelegramClient(self.SESSION, self.API_ID, self.API_HASH)
        await self.client.start()
        me = await self.client.get_me()
        return me

    async def send_to_topic(self, group_id, topic_id, text):
        """Send message to HQ group topic. Returns message object."""
        group = await self.client.get_entity(group_id)
        msg = await self.client.send_message(group, text, reply_to=topic_id)
        return msg

    async def send_to_dm(self, bot_username, text):
        """Send DM to bot (for capsules without HQ group). Returns message object."""
        entity = await self.client.get_entity(bot_username)
        msg = await self.client.send_message(entity, text)
        return msg

    async def send_file_to_topic(self, group_id, topic_id, file_path, caption=None):
        """Send file to HQ group topic. Returns message object."""
        group = await self.client.get_entity(group_id)
        msg = await self.client.send_file(
            group, file_path, caption=caption, reply_to=topic_id
        )
        return msg

    async def send_file_to_dm(self, bot_username, file_path, caption=None):
        """Send file DM to bot. Returns message object."""
        entity = await self.client.get_entity(bot_username)
        msg = await self.client.send_file(entity, file_path, caption=caption)
        return msg

    async def wait_for_bot_reply(self, group_id, topic_id, bot_id, after_msg_id, timeout=90):
        """
        Wait for bot reply in topic after our message.
        Returns (text, has_file, msg) or (None, False, None) on timeout.
        """
        group = await self.client.get_entity(group_id)
        start = time.time()

        while time.time() - start < timeout:
            await asyncio.sleep(3)

            if topic_id:
                messages = []
                async for msg in self.client.iter_messages(group, limit=10, reply_to=topic_id):
                    if msg.id > after_msg_id:
                        messages.append(msg)
            else:
                messages = []
                async for msg in self.client.iter_messages(group, limit=10):
                    if msg.id > after_msg_id:
                        messages.append(msg)

            for msg in messages:
                # Check sender is the bot
                if msg.sender_id != bot_id:
                    continue

                text = msg.text or ""

                # Skip status messages
                if any(p.lower() in text.lower() for p in SKIP_PATTERNS):
                    continue

                has_file = bool(msg.document or msg.photo)
                return text, has_file, msg

        return None, False, None

    async def wait_for_dm_reply(self, bot_username, bot_id, after_msg_id, timeout=90):
        """
        Wait for bot reply in DM.
        Returns (text, has_file, msg) or (None, False, None) on timeout.
        """
        entity = await self.client.get_entity(bot_username)
        start = time.time()

        while time.time() - start < timeout:
            await asyncio.sleep(3)

            async for msg in self.client.iter_messages(entity, limit=5):
                if msg.id > after_msg_id and msg.sender_id == bot_id:
                    text = msg.text or ""
                    if any(p.lower() in text.lower() for p in SKIP_PATTERNS):
                        continue
                    has_file = bool(msg.document or msg.photo)
                    return text, has_file, msg

        return None, False, None

    async def disconnect(self):
        """Disconnect Telethon client."""
        if self.client:
            await self.client.disconnect()


# Global tester instance (initialized lazily in capsule-audit.py)
_telethon_tester = None


def get_telethon_tester():
    """Get or create global TelethonTester instance."""
    global _telethon_tester
    if _telethon_tester is None:
        _telethon_tester = TelethonTester()
    return _telethon_tester


# ─── Service & log helpers ──────────────────────────────────────────

def run_cmd(cmd, timeout=30):
    """Run shell command, return (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"


def ssh_cmd(host, password, cmd, timeout=15):
    """Run command on remote host via sshpass."""
    full_cmd = (
        f"sshpass -p '{password}' ssh -o ConnectTimeout=10 "
        f"-o StrictHostKeyChecking=no root@{host} \"{cmd}\""
    )
    return run_cmd(full_cmd, timeout=timeout)


def get_service_status(capsule):
    """Check if service is active. Returns (is_active, details)."""
    transport = capsule.get("transport", "systemd")

    if transport == "systemd":
        rc, out, _ = run_cmd(f"systemctl is-active {capsule['service']}")
        return out == "active", out

    elif transport == "docker":
        container = capsule.get("container_name", capsule["service"])
        rc, out, _ = run_cmd(f"docker inspect -f '{{{{.State.Running}}}}' {container}")
        return out == "true", out

    elif transport == "ssh":
        host = capsule["ssh_host"]
        pwd = capsule.get("ssh_password", "")
        rc, out, _ = ssh_cmd(host, pwd, f"systemctl is-active {capsule['service']}")
        return out == "active", out

    return False, f"Unknown transport: {transport}"


def get_logs_since(capsule, since_dt):
    """Get logs since datetime. Returns string."""
    since_str = since_dt.strftime("%Y-%m-%d %H:%M:%S")
    transport = capsule.get("transport", "systemd")
    log_cmd = capsule.get("log_cmd", "")

    if not log_cmd:
        if transport == "systemd":
            log_cmd = f"journalctl -u {capsule['service']} --since '{{since}}' --no-pager -q"
        elif transport == "docker":
            container = capsule.get("container_name", capsule["service"])
            # Docker uses relative time
            log_cmd = f"docker logs {container} --since '{{since}}'"
        else:
            return ""

    cmd = log_cmd.replace("{since}", since_str)

    if transport == "ssh":
        rc, out, _ = ssh_cmd(capsule["ssh_host"], capsule.get("ssh_password", ""), cmd)
    else:
        rc, out, _ = run_cmd(cmd, timeout=15)

    return out


def filter_errors(log_text):
    """Extract error lines from log text."""
    if not log_text:
        return ""
    lines = log_text.split("\n")
    errors = []
    for i, line in enumerate(lines):
        if any(p in line for p in ERROR_PATTERNS):
            # Include context: 1 line before, error line, 2 lines after
            start = max(0, i - 1)
            end = min(len(lines), i + 3)
            snippet = lines[start:end]
            errors.append("\n".join(snippet))
    return "\n---\n".join(errors[:10])  # Max 10 error snippets


def check_recent_errors(capsule, window_minutes=10):
    """Check for recent errors in logs. Returns (has_errors, error_snippet)."""
    since = datetime.now() - timedelta(minutes=window_minutes)
    logs = get_logs_since(capsule, since)
    errors = filter_errors(logs)
    return bool(errors), errors


# ─── Path resolution ────────────────────────────────────────────────

# Project root (Antigravity dir)
PROJECT_ROOT = Path(os.environ.get("NEURA_BASE", "/opt/neura-v2"))


def resolve_capsule_path(path):
    """Resolve relative capsule path to absolute. Absolute paths pass through."""
    if not path:
        return None
    p = Path(path)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p


# ─── Validators ─────────────────────────────────────────────────────

def validate_sessions_json(path):
    """Validate sessions.json structure. Returns (is_valid, details)."""
    if not path:
        return None, "No sessions path configured"
    p = resolve_capsule_path(path)
    if not p.exists():
        return False, f"File not found: {path}"
    try:
        with open(p) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return False, "Root is not a dict"
        return True, f"{len(data)} sessions"
    except json.JSONDecodeError as e:
        return False, f"JSON parse error: {e}"


def check_sessions_overloaded(path, max_messages=80):
    """Check if any session topic has too many messages."""
    if not path:
        return None, "No sessions path"
    p = resolve_capsule_path(path)
    if not p.exists():
        return True, "No sessions file"  # OK — no sessions
    try:
        with open(p) as f:
            data = json.load(f)
        overloaded = []
        # Handle nested format: {"dm": {...}, "topics": {...}, "model": "..."}
        if "dm" in data or "topics" in data:
            items = {}
            if isinstance(data.get("dm"), dict) and "sessions" in data["dm"]:
                items.update(data["dm"]["sessions"])
            if isinstance(data.get("topics"), dict):
                items.update(data["topics"])
        else:
            items = data
        for topic_id, session in items.items():
            if not isinstance(session, dict):
                continue
            msgs = session.get("messages", 0)
            # messages can be int (count) or list
            count = msgs if isinstance(msgs, int) else len(msgs)
            if count > max_messages:
                overloaded.append(f"topic {topic_id}: {count} msgs")
        if overloaded:
            return False, "; ".join(overloaded)
        return True, "All sessions OK"
    except Exception as e:
        return False, str(e)


def check_zombie_claude(capsule):
    """Check for zombie claude processes (>10 min). Returns (ok, details)."""
    transport = capsule.get("transport", "systemd")
    cmd = "ps -eo pid,etimes,args --no-headers | grep 'claude.*-p' | grep -v grep"

    if transport == "ssh":
        rc, out, _ = ssh_cmd(capsule["ssh_host"], capsule.get("ssh_password", ""), cmd)
    elif transport == "docker":
        container = capsule.get("container_name", capsule["service"])
        rc, out, _ = run_cmd(f"docker exec {container} {cmd}")
    else:
        rc, out, _ = run_cmd(cmd)

    if not out:
        return True, "No claude processes"

    zombies = []
    for line in out.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 2:
            try:
                elapsed = int(parts[1])
                if elapsed > 600:  # >10 min
                    zombies.append(f"PID {parts[0]}: {elapsed}s")
            except ValueError:
                pass

    if zombies:
        return False, "; ".join(zombies)
    return True, "All claude processes OK"


def check_memory_usage(capsule):
    """Check memory usage. Returns (ok, details)."""
    transport = capsule.get("transport", "systemd")

    if transport == "docker":
        container = capsule.get("container_name", capsule["service"])
        rc, out, _ = run_cmd(
            f"docker stats {container} --no-stream --format '{{{{.MemPerc}}}}'"
        )
        if out:
            try:
                pct = float(out.replace("%", ""))
                return pct < 90, f"{pct:.1f}%"
            except ValueError:
                return True, out
    elif transport == "systemd":
        service = capsule["service"]
        rc, out, _ = run_cmd(
            f"systemctl show {service} -p MemoryCurrent,MemoryMax"
        )
        current = max_mem = None
        for line in out.split("\n"):
            if line.startswith("MemoryCurrent="):
                val = line.split("=")[1]
                if val != "[not set]" and val.isdigit():
                    current = int(val)
            elif line.startswith("MemoryMax="):
                val = line.split("=")[1]
                if val != "infinity" and val != "[not set]" and val.isdigit():
                    max_mem = int(val)
        if current and max_mem:
            pct = (current / max_mem) * 100
            return pct < 90, f"{pct:.1f}% ({current // 1048576}MB / {max_mem // 1048576}MB)"
        elif current:
            return True, f"{current // 1048576}MB (no limit)"
    elif transport == "ssh":
        rc, out, _ = ssh_cmd(
            capsule["ssh_host"], capsule.get("ssh_password", ""),
            f"systemctl show {capsule['service']} -p MemoryCurrent,MemoryMax"
        )
        # Same parsing as systemd above
        current = max_mem = None
        for line in out.split("\n"):
            if line.startswith("MemoryCurrent="):
                val = line.split("=")[1]
                if val != "[not set]" and val.isdigit():
                    current = int(val)
            elif line.startswith("MemoryMax="):
                val = line.split("=")[1]
                if val != "infinity" and val != "[not set]" and val.isdigit():
                    max_mem = int(val)
        if current and max_mem:
            pct = (current / max_mem) * 100
            return pct < 90, f"{pct:.1f}% ({current // 1048576}MB / {max_mem // 1048576}MB)"
        elif current:
            return True, f"{current // 1048576}MB (no limit)"

    return True, "Could not determine"


def check_disk_usage(threshold=90):
    """Check disk usage on /. Returns (ok, details)."""
    rc, out, _ = run_cmd("df -h / | tail -1 | awk '{print $5}'")
    if out:
        try:
            pct = int(out.replace("%", ""))
            return pct < threshold, f"{pct}%"
        except ValueError:
            return True, out
    return True, "Could not determine"


def check_diary_exists(diary_dir, days=3):
    """Check if diary has recent entries. Returns (ok, details)."""
    if not diary_dir:
        return None, "No diary dir configured"
    d = resolve_capsule_path(diary_dir)
    if not d.exists():
        return False, f"Directory not found: {diary_dir}"
    today = datetime.now().date()
    for i in range(days):
        check_date = today - timedelta(days=i)
        pattern = check_date.strftime("%Y-%m-%d")
        matches = list(d.glob(f"*{pattern}*"))
        if matches:
            return True, f"Found: {matches[0].name}"
    return False, f"No diary entries in last {days} days"


def check_file_valid(code_dir, relative_path, max_entries=50):
    """Check if a memory file exists and is not overloaded."""
    p = resolve_capsule_path(code_dir) / relative_path
    if not p.exists():
        return None, f"Not found: {relative_path}"
    try:
        content = p.read_text()
        # Count entries (lines starting with - or numbered)
        entries = len(re.findall(r"^[-\d]+[\.\)]\s", content, re.MULTILINE))
        if entries > max_entries:
            return False, f"{entries} entries (max {max_entries})"
        return True, f"{entries} entries, OK"
    except Exception as e:
        return False, str(e)


def check_code_contains(code_dir, patterns):
    """Check if bot code contains required patterns."""
    # Find main bot file
    d = resolve_capsule_path(code_dir)
    bot_files = list(d.glob("*.py"))
    if not bot_files:
        return False, "No .py files found"

    all_code = ""
    for f in bot_files:
        try:
            all_code += f.read_text()
        except Exception:
            pass

    missing = [p for p in patterns if p not in all_code]
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    return True, "All patterns found"


def check_file_exists_in_capsule(code_dir, filename):
    """Check if file exists in capsule directory."""
    base = resolve_capsule_path(code_dir)
    p = base / filename
    if p.exists():
        return True, str(p)
    # Check parent dir
    parent = base.parent
    p2 = parent / filename
    if p2.exists():
        return True, str(p2)
    return False, f"Not found: {filename} in {code_dir}"


# ─── Result model ──────────────────────────────────────────────────

class TestResult:
    """Single test result."""

    def __init__(self, test_id, name, capsule_name):
        self.test_id = test_id
        self.name = name
        self.capsule_name = capsule_name
        self.status = "pending"  # pass, fail, skip, error
        self.details = ""
        self.log_snippet = ""
        self.duration_ms = 0

    def passed(self, details=""):
        self.status = "pass"
        self.details = details

    def failed(self, details=""):
        self.status = "fail"
        self.details = details

    def skipped(self, reason=""):
        self.status = "skip"
        self.details = reason

    def errored(self, details=""):
        self.status = "error"
        self.details = details

    @property
    def icon(self):
        return {"pass": "✅", "fail": "❌", "skip": "⏭️", "error": "⚠️"}.get(
            self.status, "❓"
        )

    def to_dict(self):
        return {
            "test_id": self.test_id,
            "name": self.name,
            "capsule": self.capsule_name,
            "status": self.status,
            "details": self.details,
            "log_snippet": self.log_snippet,
            "duration_ms": self.duration_ms,
        }
