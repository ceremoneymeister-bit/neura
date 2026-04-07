"""Userbot (Telethon) auto-connection via bot chat.

Two auth methods:
  A) QR Code — user scans QR from Telegram app (no phone code needed)
  B) Phone Code — classic phone+code flow (file session survives TCP reconnect)

One API ID for all users (33869550).
"""
import asyncio
import logging
import tempfile
from pathlib import Path

import qrcode

from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PhoneNumberInvalidError,
    FloodWaitError,
)

logger = logging.getLogger(__name__)

API_ID = 33869550
API_HASH = "bcc80776767204e74d728936e1e124a3"


class UserbotConnector:
    """Manages Telethon session creation for a capsule user."""

    def __init__(self, capsule_home: str, capsule_id: str):
        self._home = Path(capsule_home)
        self._home.mkdir(parents=True, exist_ok=True)
        self._capsule_id = capsule_id
        self._session_path = str(self._home / f"{capsule_id}_userbot")
        self._client: TelegramClient | None = None
        self._phone_code_hash: str | None = None
        self._qr_login = None  # QRLogin object

    @property
    def session_file_exists(self) -> bool:
        return Path(f"{self._session_path}.session").exists()

    def _delete_stale_session(self):
        """Delete .session file from failed attempts."""
        for ext in (".session", ".session-journal"):
            p = Path(f"{self._session_path}{ext}")
            if p.exists():
                p.unlink()
                logger.info(f"[{self._capsule_id}] Deleted stale {ext}")

    def _create_client(self) -> TelegramClient:
        """Create TelegramClient with file-based session."""
        return TelegramClient(
            self._session_path, API_ID, API_HASH,
            device_model="Neura Agent",
            system_version="Ubuntu 24.04",
            app_version="2.0",
            lang_code="ru",
            system_lang_code="ru",
        )

    # ── Method A: QR Code Login ────────────────────────────────

    async def request_qr(self) -> dict:
        """Start QR login. Returns {"ok": True, "qr_path": "/tmp/...", "url": "tg://..."}.

        User scans QR → Telegram authorizes device.
        """
        try:
            self._delete_stale_session()
            self._client = self._create_client()
            await self._client.connect()

            self._qr_login = await self._client.qr_login()
            url = self._qr_login.url
            logger.info(f"[{self._capsule_id}] QR login started: {url[:40]}...")

            # Generate QR image
            qr_img = qrcode.make(url)
            with tempfile.NamedTemporaryFile(suffix=".png", prefix="neura_qr_",
                                               delete=False) as f:
                qr_path = f.name
            qr_img.save(qr_path)

            return {"ok": True, "qr_path": qr_path, "url": url}

        except Exception as e:
            logger.error(f"[{self._capsule_id}] QR request error: {type(e).__name__}: {e}")
            return {"error": f"Ошибка QR: {e}"}

    async def wait_for_qr_scan(self, timeout: int = 120) -> dict:
        """Wait for user to scan QR. Blocking (run as background task).

        Returns: {"ok": True, ...}, {"2fa": True}, {"expired": True}, or {"error": ...}
        """
        if not self._qr_login or not self._client:
            return {"error": "QR сессия не инициализирована."}

        try:
            await asyncio.wait_for(self._qr_login.wait(), timeout=timeout)

            # Check if authorized
            if await self._client.is_user_authorized():
                return await self._on_auth_success()
            else:
                return {"error": "Авторизация не завершена."}

        except asyncio.TimeoutError:
            logger.info(f"[{self._capsule_id}] QR expired (timeout={timeout}s)")
            return {"expired": True}
        except SessionPasswordNeededError:
            logger.info(f"[{self._capsule_id}] QR scanned, 2FA required")
            return {"2fa": True}
        except Exception as e:
            logger.error(f"[{self._capsule_id}] QR wait error: {type(e).__name__}: {e}")
            return {"error": f"Ошибка: {e}"}

    async def recreate_qr(self) -> dict:
        """Recreate expired QR token. Returns new QR image path."""
        if not self._qr_login or not self._client:
            return {"error": "QR сессия потеряна."}

        try:
            await self._qr_login.recreate()
            url = self._qr_login.url

            qr_img = qrcode.make(url)
            with tempfile.NamedTemporaryFile(suffix=".png", prefix="neura_qr_",
                                               delete=False) as f:
                qr_path = f.name
            qr_img.save(qr_path)

            return {"ok": True, "qr_path": qr_path, "url": url}

        except Exception as e:
            logger.error(f"[{self._capsule_id}] QR recreate error: {e}")
            return {"error": f"Ошибка: {e}"}

    # ── Method B: Phone Code Login ─────────────────────────────

    async def request_code(self, phone: str) -> dict:
        """Send code request. Uses FILE session (survives TCP reconnect)."""
        try:
            self._delete_stale_session()
            self._client = self._create_client()
            await self._client.connect()

            result = await self._client.send_code_request(phone)
            self._phone_code_hash = result.phone_code_hash

            code_type = "app"
            if "Sms" in type(result.type).__name__:
                code_type = "sms"

            logger.info(f"[{self._capsule_id}] Code sent to {phone[:5]}*** "
                        f"(type={type(result.type).__name__}, hash={self._phone_code_hash[:8]}...)")
            return {"ok": True, "code_type": code_type}

        except PhoneNumberInvalidError:
            return {"error": "Неверный номер телефона. Формат: +79991234567"}
        except FloodWaitError as e:
            return {"error": f"Telegram просит подождать {e.seconds} секунд. Попробуйте позже."}
        except Exception as e:
            logger.error(f"[{self._capsule_id}] Code request error: {type(e).__name__}: {e}")
            return {"error": f"Ошибка: {e}"}

    async def sign_in_code(self, phone: str, code: str) -> dict:
        """Sign in with phone code. File session preserves auth_key through reconnect."""
        if not self._phone_code_hash:
            return {"error": "Хэш кода потерян. Начните заново."}

        # Reconnect from file session (auth_key persisted in SQLite)
        try:
            if self._client:
                try:
                    await self._client.disconnect()
                except Exception:
                    pass
            self._client = self._create_client()
            await self._client.connect()
        except Exception as e:
            logger.error(f"[{self._capsule_id}] Reconnect failed: {e}")
            return {"error": "Не удалось подключиться. Начните заново."}

        logger.info(f"[{self._capsule_id}] sign_in: phone={phone[:5]}*** "
                    f"code={code[:2]}** hash={self._phone_code_hash[:8]}...")

        try:
            await self._client.sign_in(
                phone=phone, code=code,
                phone_code_hash=self._phone_code_hash,
            )
            return await self._on_auth_success()

        except SessionPasswordNeededError:
            return {"2fa": True}
        except PhoneCodeInvalidError:
            logger.warning(f"[{self._capsule_id}] Invalid code")
            return {"error": "Неверный код. Проверьте и попробуйте ещё раз."}
        except PhoneCodeExpiredError:
            logger.warning(f"[{self._capsule_id}] Code expired")
            return {"error": "Код истёк. Возможно, Telegram ограничил число попыток. Попробуйте через QR-код или подождите пару часов."}
        except Exception as e:
            logger.error(f"[{self._capsule_id}] Sign-in error: {type(e).__name__}: {e}")
            return {"error": f"Ошибка входа: {e}"}

    # ── Shared: 2FA + Success ──────────────────────────────────

    async def sign_in_2fa(self, password: str) -> dict:
        """Enter 2FA password (works for both QR and phone code)."""
        if not self._client:
            return {"error": "Сессия потеряна. Начните заново."}

        if not self._client.is_connected():
            try:
                await self._client.connect()
            except Exception:
                return {"error": "Соединение потеряно. Начните заново."}

        try:
            await self._client.sign_in(password=password)
            return await self._on_auth_success()
        except Exception as e:
            logger.error(f"[{self._capsule_id}] 2FA error: {type(e).__name__}: {e}")
            return {"error": f"Неверный пароль: {e}"}

    async def _on_auth_success(self) -> dict:
        """Save session and return user info."""
        me = await self._client.get_me()
        logger.info(f"[{self._capsule_id}] Userbot connected: {me.first_name} ({me.id})")
        # Session file already saved by Telethon (file-based session)
        await self._client.disconnect()
        self._client = None
        return {"ok": True, "user_id": me.id, "name": me.first_name}

    async def cleanup(self):
        """Disconnect and remove incomplete session."""
        if self._client:
            try:
                if self._client.is_connected():
                    await self._client.disconnect()
            except Exception:
                pass
            self._client = None
        self._qr_login = None
        self._phone_code_hash = None
        # Remove incomplete session
        if not self.session_file_exists:
            return
        # Check if session is authorized
        try:
            client = self._create_client()
            await client.connect()
            authorized = await client.is_user_authorized()
            await client.disconnect()
            if not authorized:
                self._delete_stale_session()
        except Exception:
            self._delete_stale_session()
