"""Unified message protocol — transport-agnostic types + response parsing.

Used by ALL transports (Telegram, Web, Mobile).
Contains: message data classes, response parser (markers, files),
Telegraph helper, voice transcription (Deepgram + Whisper).

Ported from v1:
  - neura-capsule/bot/utils/response.py (markers, files, telegraph)
  - neura-capsule/bot/engine/transcribe.py (deepgram, whisper)
"""
import asyncio
import json
import logging
import os
import re
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Message Types ──────────────────────────────────────────────

class MessageType(Enum):
    TEXT = "text"
    VOICE = "voice"
    PHOTO = "photo"
    DOCUMENT = "document"
    COMMAND = "command"


@dataclass
class IncomingMessage:
    """Transport-agnostic incoming message."""
    capsule_id: str
    user_id: int
    user_name: str
    text: str
    message_type: MessageType = MessageType.TEXT
    file_path: str | None = None
    file_name: str | None = None
    reply_context: str = ""
    source: str = "telegram"
    thread_id: int | None = None
    chat_id: int | None = None


@dataclass
class MessageFile:
    """A file to send with the response."""
    path: str
    filename: str
    is_photo: bool = False
    caption: str = ""


@dataclass
class OutgoingMessage:
    """Transport-agnostic response."""
    text: str
    files: list[MessageFile] = field(default_factory=list)
    learnings: list[str] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    telegraph_url: str | None = None
    is_long: bool = False


# ── Response Parser ────────────────────────────────────────────

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_MSG_LENGTH = 4000
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB — Telegram Bot API limit
DEFAULT_ALLOWED_PREFIXES = ["/tmp/", "/opt/neura-v2/homes/"]


class ResponseParser:
    """Parse engine output into structured OutgoingMessage."""

    @staticmethod
    def parse(engine_text: str,
              allowed_prefixes: list[str] | None = None) -> OutgoingMessage:
        """Full parse pipeline: markers → files → telegraph check."""
        text = engine_text

        # 1. Extract markers
        text, learnings, corrections, rules = ResponseParser._parse_markers(text)

        # 2. Extract files
        prefixes = allowed_prefixes or list(DEFAULT_ALLOWED_PREFIXES)
        text, files = ResponseParser._extract_files(text, prefixes)

        # 3. Long text flag
        is_long = len(text) > MAX_MSG_LENGTH

        return OutgoingMessage(
            text=text,
            files=files,
            learnings=learnings,
            corrections=corrections,
            rules=rules,
            is_long=is_long,
        )

    @staticmethod
    def _parse_markers(text: str) -> tuple[str, list[str], list[str], list[str]]:
        """Extract [LEARN:...], [CORRECTION:...], and [RULE:...] markers."""
        learnings = re.findall(r'\[LEARN:(.*?)\]', text, re.DOTALL)
        corrections = re.findall(r'\[CORRECTION:(.*?)\]', text, re.DOTALL)
        rules = re.findall(r'\[RULE:(.*?)\]', text, re.DOTALL)

        cleaned = re.sub(r'\[LEARN:.*?\]', '', text, flags=re.DOTALL)
        cleaned = re.sub(r'\[CORRECTION:.*?\]', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'\[RULE:.*?\]', '', cleaned, flags=re.DOTALL)
        cleaned = cleaned.strip()

        return cleaned, [l.strip() for l in learnings], [c.strip() for c in corrections], [r.strip() for r in rules]

    @staticmethod
    def _extract_files(text: str,
                       allowed_prefixes: list[str]) -> tuple[str, list[MessageFile]]:
        """Extract [FILE:/path] markers with path traversal protection."""
        raw_files = re.findall(r'\[FILE:(.*?)\]', text)
        cleaned = re.sub(r'\[FILE:.*?\]', '', text).strip()

        safe_files: list[MessageFile] = []
        for fp in raw_files:
            fp = fp.strip()
            resolved = str(Path(fp).resolve())
            if not any(resolved.startswith(p) for p in allowed_prefixes):
                logger.warning(f"Blocked file send (path traversal): {fp}")
                continue
            if not os.path.exists(resolved):
                logger.warning(f"File not found, skipping: {resolved}")
                continue
            file_size = os.path.getsize(resolved)
            if file_size > MAX_FILE_SIZE:
                size_mb = file_size / (1024 * 1024)
                logger.warning(f"File too large ({size_mb:.1f} MB > 50 MB): {resolved}")
                continue
            ext = os.path.splitext(resolved)[1].lower()
            filename = os.path.basename(resolved)
            is_photo = ext in PHOTO_EXTENSIONS

            if is_photo:
                caption = "\U0001f5bc Сгенерировано по вашему запросу"
            elif ext == ".pdf":
                caption = f"\U0001f4c4 {ResponseParser._humanize_filename(filename)}"
            elif ext in {".docx", ".doc"}:
                caption = f"\U0001f4dd {ResponseParser._humanize_filename(filename)}"
            elif ext in {".xlsx", ".xls"}:
                caption = f"\U0001f4ca {ResponseParser._humanize_filename(filename)}"
            elif ext in {".pptx", ".ppt"}:
                caption = f"\U0001f4ca {ResponseParser._humanize_filename(filename)}"
            else:
                caption = filename

            safe_files.append(MessageFile(
                path=resolved, filename=filename,
                is_photo=is_photo, caption=caption,
            ))

        return cleaned, safe_files

    @staticmethod
    def _humanize_filename(filename: str) -> str:
        """Convert 'annual_report_2026.pdf' -> 'Annual report 2026'."""
        name = os.path.splitext(filename)[0]
        name = name.replace('_', ' ').replace('-', ' ')
        return name.capitalize()


# ── Telegraph ──────────────────────────────────────────────────

TELEGRAPH_API = "https://api.telegra.ph"
TELEGRAPH_TOKEN_FILE = Path("/opt/neura-v2/data/.telegraph_token")


def _md_to_telegraph_nodes(md_text: str) -> list:
    """Convert Markdown to Telegraph node format."""
    nodes: list = []
    lines = md_text.split('\n')

    for line in lines:
        line = line.rstrip()
        if not line:
            nodes.append({"tag": "br"})
            continue

        if line.startswith('### '):
            nodes.append({"tag": "h4", "children": [line[4:]]})
        elif line.startswith('## '):
            nodes.append({"tag": "h3", "children": [line[3:]]})
        elif line.startswith('# '):
            nodes.append({"tag": "h3", "children": [line[2:]]})
        elif line.startswith('- ') or line.startswith('\u2022 '):
            nodes.append({"tag": "li", "children": [line[2:]]})
        elif line.startswith('> '):
            nodes.append({"tag": "blockquote", "children": [line[2:]]})
        elif re.match(r'^\d+\. ', line):
            text = re.sub(r'^\d+\. ', '', line)
            nodes.append({"tag": "li", "children": [text]})
        elif line.startswith('```'):
            continue
        elif line.startswith('**') and line.endswith('**'):
            nodes.append({"tag": "p", "children": [{"tag": "b", "children": [line.strip('*')]}]})
        else:
            children: list = []
            parts = re.split(r'(\*\*.*?\*\*|\*.*?\*|`.*?`)', line)
            for part in parts:
                if part.startswith('**') and part.endswith('**') and len(part) > 4:
                    children.append({"tag": "b", "children": [part[2:-2]]})
                elif part.startswith('*') and part.endswith('*') and len(part) > 2:
                    children.append({"tag": "i", "children": [part[1:-1]]})
                elif part.startswith('`') and part.endswith('`') and len(part) > 2:
                    children.append({"tag": "code", "children": [part[1:-1]]})
                elif part:
                    children.append(part)
            nodes.append({"tag": "p", "children": children if children else [line]})

    return nodes if nodes else [{"tag": "p", "children": ["(пустой ответ)"]}]


def _get_telegraph_token() -> str | None:
    """Get or create Telegraph access token (cached in file)."""
    if TELEGRAPH_TOKEN_FILE.exists():
        token = TELEGRAPH_TOKEN_FILE.read_text().strip()
        if token:
            return token

    try:
        acc_data = json.dumps({
            "short_name": "Нэйра",
            "author_name": "Нэйра",
        }).encode()

        req = urllib.request.Request(
            f"{TELEGRAPH_API}/createAccount",
            data=acc_data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            acc_result = json.loads(resp.read())

        if not acc_result.get("ok"):
            return None

        token = acc_result["result"]["access_token"]
        TELEGRAPH_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TELEGRAPH_TOKEN_FILE.write_text(token)
        return token
    except Exception as e:
        logger.error(f"Telegraph account creation error: {e}")
        return None


def create_telegraph_page(title: str, content: str) -> str | None:
    """Create a Telegraph page. Returns URL or None."""
    try:
        access_token = _get_telegraph_token()
        if not access_token:
            return None

        nodes = _md_to_telegraph_nodes(content)
        page_data = json.dumps({
            "access_token": access_token,
            "title": title[:256],
            "content": nodes,
            "author_name": "Нэйра",
        }).encode()

        req = urllib.request.Request(
            f"{TELEGRAPH_API}/createPage",
            data=page_data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            page_result = json.loads(resp.read())

        if page_result.get("ok"):
            return page_result["result"]["url"]
        return None
    except Exception as e:
        logger.error(f"Telegraph error: {e}")
        return None


# ── Voice Transcription ────────────────────────────────────────

_whisper_model = None


async def transcribe_voice(file_path: str) -> str:
    """Transcribe voice: Deepgram (primary) -> Whisper (fallback)."""
    deepgram_key = os.environ.get("DEEPGRAM_API_KEY")
    if deepgram_key:
        try:
            result = await _transcribe_deepgram(file_path)
            if result and not result.startswith("\u274c"):
                return result
            logger.warning(f"Deepgram failed, falling back to Whisper: {result}")
        except Exception as e:
            logger.warning(f"Deepgram error, falling back to Whisper: {e}")

    return await _transcribe_whisper(file_path)


def _guess_audio_content_type(file_path: str) -> str:
    """Guess audio MIME type from file extension."""
    ext = Path(file_path).suffix.lower()
    types = {
        ".ogg": "audio/ogg", ".oga": "audio/ogg",
        ".mp3": "audio/mpeg", ".mp4": "audio/mp4",
        ".m4a": "audio/mp4", ".wav": "audio/wav",
        ".webm": "audio/webm", ".flac": "audio/flac",
        ".aac": "audio/aac", ".opus": "audio/ogg",
    }
    return types.get(ext, "audio/ogg")


async def download_via_mtproto(bot_token: str, chat_id: int, message_id: int, dest_path: str) -> bool:
    """Download file via Telethon MTProto userbot — no 20MB limit.

    Uses the parser userbot session (already authorized) to download files
    that exceed the 20MB Bot API limit.
    """
    try:
        from telethon import TelegramClient

        api_id = int(os.environ.get("TELETHON_API_ID", "33869550"))
        api_hash = os.environ.get("TELETHON_API_HASH", "")
        if not api_hash:
            logger.warning("TELETHON_API_HASH not set, MTProto download unavailable")
            return False

        # Use parser userbot session (already authorized, no login needed)
        session_path = os.environ.get(
            "TELETHON_SESSION_PATH",
            "/root/Antigravity/.secrets/telegram_userbot_parser",
        )
        client = TelegramClient(session_path, api_id, api_hash)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                logger.error("MTProto userbot session not authorized")
                return False
            msg = await client.get_messages(chat_id, ids=message_id)
            if msg and msg.media:
                await client.download_media(msg, file=dest_path)
                return True
            return False
        finally:
            await client.disconnect()
    except Exception as e:
        logger.error(f"MTProto download failed: {e}")
        return False


async def _transcribe_deepgram(file_path: str) -> str:
    """Transcribe using Deepgram nova-2 API."""
    def _do_request():
        with open(file_path, "rb") as f:
            audio_data = f.read()

        key = os.environ["DEEPGRAM_API_KEY"]
        url = "https://api.deepgram.com/v1/listen?model=nova-2&language=ru&smart_format=true"
        content_type = _guess_audio_content_type(file_path)

        req = urllib.request.Request(
            url, data=audio_data,
            headers={
                "Authorization": f"Token {key}",
                "Content-Type": content_type,
            },
        )
        with urllib.request.urlopen(req, timeout=180) as resp:  # 3 min for long voice (10+ min audio)
            result = json.loads(resp.read())

        transcript = (
            result.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("transcript", "")
        )
        return transcript.strip()

    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, _do_request)
    return text if text else "\u274c Deepgram: пустой результат"


async def _transcribe_whisper(file_path: str) -> str:
    """Fallback: transcribe using faster-whisper base model."""
    try:
        def _do_transcribe():
            global _whisper_model
            if _whisper_model is None:
                from faster_whisper import WhisperModel
                logger.info("Loading Whisper base (CPU, int8)...")
                _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
                logger.info("Whisper loaded.")

            segments, _ = _whisper_model.transcribe(file_path, language="ru", beam_size=3)
            return " ".join(s.text for s in segments)

        loop = asyncio.get_event_loop()
        text = await asyncio.wait_for(
            loop.run_in_executor(None, _do_transcribe),
            timeout=120,
        )
        return text.strip() if text.strip() else "\u274c Не удалось расшифровать"
    except asyncio.TimeoutError:
        logger.error("Whisper timeout (120s)")
        return "\u274c Аудио слишком длинное для расшифровки"
    except Exception as e:
        logger.error(f"Whisper error: {e}")
        return f"\u274c Ошибка расшифровки: {e}"
