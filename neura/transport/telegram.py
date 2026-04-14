"""Multi-bot Telegram transport — one process, all capsules.

@arch scope=platform  affects=all_capsules(14)
@arch depends=core.engine, core.memory, core.queue, core.context, core.capsule
@arch depends=core.session_tracker, core.skill_learning, transport.protocol
@arch risk=HIGH  restart=neura-v2  test="systemctl status neura-v2"
@arch role=Main message handler. Changes here affect EVERY user interaction.
@arch sync=transport.protocol (file parsing), core.engine (Claude CLI calls)

Handles: text, voice, photo, document messages.
Features: streaming response (progressive edit), BTW queue, Telegraph for long messages.
Uploads: user files saved to homes/<capsule>/uploads/ (persistent across sessions).
"""
import asyncio
import logging
import os
import re
import tempfile
import time as _time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
    MessageHandler, filters,
)

from neura.core.capsule import Capsule
from neura.core.context import ContextBuilder
from neura.core.directives import parse_directives
from neura.core.engine import ClaudeEngine, Chunk, EngineConfig
from neura.core.link_understanding import enrich_with_links, extract_urls
from neura.core.session_tracker import SessionTracker
from neura.core.memory import DiaryEntry, MemoryStore
from neura.core.queue import QueuedMessage, RequestQueue
from neura.core.skill_learning import SkillUsageCollector, SkillUsageEntry, SkillEvolver
from neura.provisioning.onboarding import OnboardingManager
from neura.provisioning.onboarding_state import OnboardingState
from neura.transport.protocol import (
    IncomingMessage, MessageType, OutgoingMessage, ResponseParser,
    create_telegraph_page, download_via_mtproto, transcribe_voice,
)
from neura.transport.topic_sync import (
    ensure_web_conversation, save_web_message,
)

logger = logging.getLogger(__name__)


# ── Persistent uploads ────────────────────────────────────────
def _upload_path(capsule: "Capsule", suffix: str, original_name: str = "") -> str:
    """Return a persistent file path inside capsule's uploads/ dir.

    Files survive across sessions (unlike /tmp/).
    Structure: homes/<capsule>/uploads/YYYY-MM-DD/<timestamp>_<name>.<ext>
    """
    today = datetime.now().strftime("%Y-%m-%d")
    upload_dir = Path(capsule.config.home_dir) / "uploads" / today
    upload_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%H%M%S")
    if original_name:
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in original_name)
        fname = f"{ts}_{safe_name}"
    else:
        fname = f"{ts}_{os.getpid()}{suffix}"
    return str(upload_dir / fname)


# ── Streaming Responder ────────────────────────────────────────

class StreamingResponder:
    """Progressive message editing during streaming.

    Throttled: edit every EDIT_INTERVAL seconds. Stops inline editing
    when text exceeds MAX_INLINE to avoid Telegram errors.
    """

    EDIT_INTERVAL = 3.0
    MAX_INLINE = 3800

    def __init__(self, message, existing_msg=None):
        self._message = message
        self._response_msg = existing_msg
        self._last_edit_time: float = 0
        self._last_text: str = ""
        self._exceeded_limit = False
        self._tool_label: str | None = None

    async def start(self) -> None:
        if not self._response_msg:
            try:
                self._response_msg = await self._message.reply_text("🧠 Думаю...")
            except Exception:
                # Сообщение удалено до ответа — отправляем без reply_to
                self._response_msg = await self._message.get_bot().send_message(
                    chat_id=self._message.chat_id,
                    text="🧠 Думаю...",
                )
            self._last_edit_time = _time.monotonic()

    async def on_text(self, accumulated: str) -> None:
        if self._exceeded_limit or not self._response_msg:
            return

        if len(accumulated) > self.MAX_INLINE:
            self._exceeded_limit = True
            try:
                await self._response_msg.edit_text("⏳ Формирую полный ответ...")
            except Exception:
                pass
            return

        now = _time.monotonic()
        if now - self._last_edit_time < self.EDIT_INTERVAL:
            return

        display = accumulated
        if self._tool_label:
            display = f"{self._tool_label}\n\n{accumulated}"

        try:
            await self._response_msg.edit_text(display[:self.MAX_INLINE])
            self._last_edit_time = now
            self._last_text = display
        except Exception:
            pass

    async def on_tool(self, tool_label: str) -> None:
        self._tool_label = tool_label
        if self._response_msg and not self._exceeded_limit:
            now = _time.monotonic()
            if now - self._last_edit_time >= self.EDIT_INTERVAL:
                try:
                    await self._response_msg.edit_text(tool_label)
                    self._last_edit_time = now
                except Exception:
                    pass

    async def finalize(self, response) -> None:
        """Delete streaming message so final response is sent as new message.

        This ensures Telegram shows a notification badge for the response.
        Previously, short responses were sent via edit_text which doesn't
        trigger notifications — users didn't know the bot had answered.
        """
        if not self._response_msg:
            return
        try:
            await self._response_msg.delete()
        except Exception:
            pass
        self._response_msg = None


# ── Auto-extraction of facts from conversations ──────────────

# Patterns for automatic fact extraction
_EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
_URL_RE = re.compile(r'https?://[^\s<>\]"\')+]+')
_PHONE_RE = re.compile(r'(?:\+7|8)[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}')
_GOOGLE_SHEET_RE = re.compile(r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)')
_GOOGLE_DOC_RE = re.compile(r'https://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)')

# Keywords that signal important facts worth saving
_IMPORTANT_KEYWORDS = {
    'ru': ['пароль', 'логин', 'доступ', 'ключ', 'токен', 'api', 'email',
           'почта', 'адрес', 'телефон', 'ссылк', 'таблиц', 'документ',
           'договор', 'контракт', 'дедлайн', 'крайний срок', 'бюджет',
           'цена', 'стоимость', 'зарплат', 'оплат'],
}


def _auto_extract_facts(user_msg: str, bot_response: str) -> list[str]:
    """Extract structured facts from conversation for long-term memory.

    Returns list of fact strings to save. Keeps only high-signal data:
    emails, links to shared resources, phone numbers.
    Avoids noise by requiring facts to appear in both user message context
    and bot response (confirmation pattern).
    """
    facts: list[str] = []
    combined = f"{user_msg}\n{bot_response}"

    # 1. Extract emails mentioned in conversation
    emails = set(_EMAIL_RE.findall(combined))
    # Filter out common service emails
    service_domains = {'noreply', 'no-reply', 'mailer-daemon', 'postmaster'}
    for email in emails:
        local = email.split('@')[0].lower()
        if local not in service_domains and 'example' not in email:
            facts.append(f"Email упомянут в разговоре: {email}")

    # 2. Extract Google Sheets/Docs links (high-value shared resources)
    for match in _GOOGLE_SHEET_RE.finditer(combined):
        url = match.group(0)
        facts.append(f"Google Таблица: {url}")
    for match in _GOOGLE_DOC_RE.finditer(combined):
        url = match.group(0)
        facts.append(f"Google Документ: {url}")

    # 3. Extract phone numbers
    phones = set(_PHONE_RE.findall(combined))
    for phone in phones:
        facts.append(f"Телефон упомянут: {phone}")

    # Deduplicate
    return list(dict.fromkeys(facts))


# ── Telegram Transport ─────────────────────────────────────────

class TelegramTransport:
    """Multi-bot Telegram transport. One process, all capsules."""

    def __init__(self, capsules: dict[str, Capsule], engine: ClaudeEngine,
                 memory: MemoryStore, queue: RequestQueue,
                 metrics=None, alert_sender=None,
                 skill_collector: SkillUsageCollector | None = None,
                 skill_evolver: SkillEvolver | None = None):
        self._capsules = capsules
        self._engine = engine
        self._memory = memory
        self._queue = queue
        self._metrics = metrics
        self._alert_sender = alert_sender
        self._skill_collector = skill_collector
        self._skill_evolver = skill_evolver
        self._apps: list[Application] = []
        self._token_to_capsule: dict[str, Capsule] = {}
        self._onboarding: OnboardingManager | None = None  # Set after Redis connected
        # Per-(capsule, user) lock to prevent toggle race conditions
        self._user_locks: dict[tuple[str, int], asyncio.Lock] = defaultdict(asyncio.Lock)
        # Session resume: one active Claude CLI session per (capsule, user)
        self._session_tracker = SessionTracker(ttl=10800)  # 3 hours TTL

    def _build_app(self, capsule: Capsule) -> Application:
        """Build an Application for a single capsule."""
        token = capsule.config.bot_token
        self._token_to_capsule[token] = capsule

        app = Application.builder().token(token).get_updates_request(
            HTTPXRequest(connect_timeout=10, read_timeout=15)
        ).request(
            HTTPXRequest(connect_timeout=10, read_timeout=30)
        ).build()
        app.bot_data["capsule"] = capsule
        app.bot_data["transport"] = self

        app.add_handler(CommandHandler("start", self._handle_start))
        app.add_handler(CommandHandler("cancel", self._handle_cancel))
        app.add_handler(CommandHandler("test_onboarding", self._handle_test_onboarding))
        app.add_handler(CommandHandler("connect_google", self._handle_connect_google))
        app.add_handler(CommandHandler("connect_telegram", self._handle_connect_telegram))
        app.add_handler(CommandHandler("rule", self._handle_rule))
        app.add_handler(CallbackQueryHandler(self._handle_callback, pattern=r"^onb:"))
        app.add_handler(CallbackQueryHandler(self._handle_action_callback, pattern=r"^action:"))
        app.add_handler(MessageHandler(
            filters.VOICE | filters.AUDIO, self._handle_voice))
        app.add_handler(MessageHandler(
            filters.PHOTO, self._handle_photo))
        app.add_handler(MessageHandler(
            filters.Document.ALL, self._handle_document))
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self._handle_text))
        app.add_error_handler(self._handle_error)

        return app

    def set_onboarding(self, redis_client) -> None:
        """Initialize onboarding manager. Called after Redis is connected."""
        state_store = OnboardingState(redis_client)
        self._onboarding = OnboardingManager(state_store, self._engine, self._memory)

    async def start(self) -> None:
        for capsule in self._capsules.values():
            app = self._build_app(capsule)
            self._apps.append(app)

        started = 0
        failed_apps = []
        for app in self._apps:
            cap = app.bot_data.get("capsule")
            capsule_id = getattr(cap, "id", "?") if cap else "?"
            try:
                await app.initialize()
                await app.updater.start_polling(
                    drop_pending_updates=True,
                    allowed_updates=["message", "callback_query"],
                )
                await app.start()
                started += 1
            except Exception as e:
                logger.error(f"Failed to start bot {capsule_id} (will retry): {e}")
                failed_apps.append(app)

        logger.info(f"Telegram transport started: {started}/{len(self._apps)} bot(s)")

        # Background retry for bots that failed (e.g. DNS was down at startup)
        if failed_apps:
            asyncio.create_task(self._retry_failed_bots(failed_apps))

    async def _retry_failed_bots(self, failed_apps: list, max_retries: int = 10) -> None:
        """Retry starting bots that failed during initial startup."""
        delay = 30  # start with 30s, double each attempt up to 5min
        for attempt in range(1, max_retries + 1):
            await asyncio.sleep(delay)
            still_failed = []
            for app in failed_apps:
                cap = app.bot_data.get("capsule")
                capsule_id = getattr(cap, "id", "?") if cap else "?"
                try:
                    await app.initialize()
                    await app.updater.start_polling(
                        drop_pending_updates=True,
                        allowed_updates=["message", "callback_query"],
                    )
                    await app.start()
                    logger.info(f"Bot {capsule_id} started on retry #{attempt}")
                except Exception as e:
                    logger.warning(f"Bot {capsule_id} retry #{attempt} failed: {e}")
                    still_failed.append(app)
            if not still_failed:
                logger.info(f"All failed bots recovered after {attempt} retries")
                return
            failed_apps = still_failed
            delay = min(delay * 2, 300)  # cap at 5 minutes
        # After all retries exhausted
        capsule_ids = [getattr(a.bot_data.get("capsule"), "id", "?") for a in failed_apps]
        logger.error(f"Bots permanently failed after {max_retries} retries: {capsule_ids}")

    async def stop(self) -> None:
        for app in reversed(self._apps):
            try:
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
            except Exception as e:
                logger.error(f"Error stopping app: {e}")
        # Cleanup all onboarding connectors/tasks on shutdown
        if self._onboarding:
            await self._onboarding.cleanup_all()
        logger.info("Telegram transport stopped")

    # ── Handlers ────────────────────────────────────────────────

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        capsule: Capsule = context.bot_data["capsule"]
        msg = update.effective_message
        if not msg:
            return
        user_id = update.effective_user.id
        logger.info(f"/start from user_id={user_id}, capsule={capsule.config.id}")

        # Onboarding check
        if self._onboarding:
            try:
                should = await self._onboarding.should_onboard(capsule, user_id)
                logger.info(f"Onboarding should_onboard={should} for {capsule.config.id}:{user_id}")
                if should:
                    text, keyboard = await self._onboarding.handle_start(capsule, user_id)
                    await msg.reply_text(text, reply_markup=keyboard)
                    return
            except Exception as e:
                logger.error(f"Onboarding error in /start: {e}", exc_info=True)

        # Personalized greeting: try onboarding profile name, then TG first_name
        user_name = None
        if self._onboarding:
            try:
                state = await self._onboarding._state.get(capsule.config.id, user_id)
                if state and state.get("profile", {}).get("name"):
                    user_name = state["profile"]["name"].split()[0]  # First name only
            except Exception:
                pass
        if not user_name and update.effective_user:
            user_name = update.effective_user.first_name

        capsule_name = capsule.config.name
        if user_name:
            await msg.reply_text(f"Привет, {user_name}! Я — {capsule_name}. Чем помогу?")
        else:
            await msg.reply_text(f"Привет! Я — {capsule_name}. Чем помогу?")

    async def _handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cancel — cancel current processing for this capsule."""
        capsule: Capsule = context.bot_data["capsule"]
        msg = update.effective_message
        if not msg:
            return
        user_id = update.effective_user.id

        if not capsule.is_employee(user_id):
            return

        cap_id = capsule.config.id
        thread_id = getattr(msg, "message_thread_id", None)
        was_cancelled = await self._queue.cancel_processing(cap_id)
        if was_cancelled:
            # Invalidate session so next message starts fresh
            await self._session_tracker.invalidate(cap_id, user_id, thread_id)
            await msg.reply_text("⏹️ Обработка отменена. Следующее сообщение начнёт новую сессию.")
            logger.info(f"/cancel: processing cancelled for {cap_id} by user {user_id}")
        else:
            await msg.reply_text("ℹ️ Нет активной обработки для отмены.")

    async def _handle_test_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /test_onboarding — reset onboarding state and restart from phase 0.

        Only available to Dmitry (producer) for testing purposes.
        """
        PRODUCER_ID = 1260958591
        capsule: Capsule = context.bot_data["capsule"]
        msg = update.effective_message
        if not msg:
            return
        user_id = update.effective_user.id
        if user_id != PRODUCER_ID:
            await msg.reply_text("⛔ Эта команда доступна только продюсеру.")
            return

        if not self._onboarding:
            await msg.reply_text("⚠️ Онбординг не активен для этой капсулы.")
            return

        # Delete existing onboarding state → next /start will treat as new user
        await self._onboarding._state.delete(capsule.config.id, user_id)
        logger.info(f"/test_onboarding: reset state for {capsule.config.id}:{user_id}")

        # Auto-trigger onboarding as if /start from a new user
        try:
            text, keyboard = await self._onboarding.handle_start(capsule, user_id)
            await msg.reply_text(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"test_onboarding error: {e}", exc_info=True)
            await msg.reply_text(f"✅ Состояние сброшено. Нажми /start чтобы пройти онбординг заново.\n\n⚠️ Ошибка автозапуска: {e}")

    async def _handle_connect_google(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /connect_google — OAuth2 flow for Google services."""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        capsule: Capsule = context.bot_data["capsule"]
        msg = update.effective_message
        if not msg:
            return
        user_id = update.effective_user.id

        if not capsule.is_employee(user_id):
            return

        home = capsule.config.home_dir
        if not home:
            await msg.reply_text("⚠️ Домашняя директория капсулы не настроена.")
            return

        # Check for Google client credentials
        creds_candidates = [
            Path(home) / "data" / "google_credentials.json",
            Path(home) / "data" / "credentials.json",
            Path(home) / "data" / "legacy" / "credentials.json",
        ]
        creds_file = None
        for p in creds_candidates:
            if p.exists():
                creds_file = p
                break

        if not creds_file:
            await msg.reply_text("⚠️ Файл Google OAuth credentials не найден. Обратитесь к администратору.")
            return

        text = msg.text or ""
        url_in_text = ""
        if "localhost" in text or "code=" in text:
            url_in_text = text.replace("/connect_google", "").strip()

        if url_in_text:
            # Step 2: User sent back the redirect URL with code
            import re
            from urllib.parse import urlparse, parse_qs
            code_match = re.search(r'[?&]code=([^&\s]+)', url_in_text)
            if not code_match:
                await msg.reply_text("❌ Не удалось найти код авторизации. Скопируйте полный URL из адресной строки.")
                return

            code = code_match.group(1)
            try:
                from google_auth_oauthlib.flow import InstalledAppFlow
                SCOPES = [
                    "https://www.googleapis.com/auth/calendar",
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive.file",
                    "https://www.googleapis.com/auth/documents",
                ]
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES, redirect_uri="http://localhost")
                flow.fetch_token(code=code)
                creds = flow.credentials

                token_data = {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": list(creds.scopes) if creds.scopes else SCOPES,
                    "expiry": creds.expiry.isoformat() if creds.expiry else None,
                }

                token_path = Path(home) / "data" / "gcal_token.json"
                import json as _json_mod
                token_path.write_text(_json_mod.dumps(token_data, ensure_ascii=False))
                logger.info(f"Google OAuth tokens saved for {capsule.config.id}:{user_id}")

                scope_names = [s.split("/")[-1] for s in (creds.scopes or SCOPES)]
                await msg.reply_text(
                    f"✅ Google подключён!\n\n"
                    f"Доступные сервисы: {', '.join(scope_names)}\n\n"
                    f"Теперь я могу работать с Calendar, Sheets, Drive и Docs."
                )
            except Exception as e:
                logger.error(f"Google OAuth exchange failed: {e}", exc_info=True)
                await msg.reply_text(f"❌ Ошибка обмена кода: {e}\n\nПопробуйте /connect_google заново.")
            return

        # Step 1: Generate auth URL
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            SCOPES = [
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/documents",
            ]
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES, redirect_uri="http://localhost")
            auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

            # Store flow state in context for this user
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Авторизоваться в Google", url=auth_url)]
            ])
            await msg.reply_text(
                "🔗 **Подключение Google**\n\n"
                "1. Нажми кнопку ниже\n"
                "2. Google покажет предупреждение — это нормально (приложение наше, просто не прошло проверку Google)\n"
                "3. Нажми «Дополнительные» → «Перейти на сайт (небезопасно)»\n"
                "4. Выбери свой Google-аккаунт и разреши доступ\n"
                "5. Страница не загрузится — это ОК\n"
                "6. Скопируй URL из адресной строки\n"
                "7. Отправь сюда: `/connect_google <URL>`",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Google OAuth URL generation failed: {e}", exc_info=True)
            await msg.reply_text(f"❌ Ошибка генерации ссылки: {e}")

    async def _handle_connect_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /connect_telegram — QR-code userbot auth (reusable, not just onboarding)."""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from neura.provisioning.userbot_connect import UserbotConnector

        capsule: Capsule = context.bot_data["capsule"]
        msg = update.effective_message
        if not msg:
            return
        user_id = update.effective_user.id

        if not capsule.is_employee(user_id):
            return

        cap_id = capsule.config.id
        home = capsule.config.home_dir or f"/tmp/neura-homes/{cap_id}"

        # Check if already authorized
        session_path = Path(home) / f"{cap_id}_userbot.session"
        if session_path.exists():
            from telethon import TelegramClient
            client = TelegramClient(
                str(session_path).replace(".session", ""),
                33869550, "bcc80776767204e74d728936e1e124a3",
            )
            try:
                await client.connect()
                if await client.is_user_authorized():
                    me = await client.get_me()
                    await client.disconnect()
                    await msg.reply_text(
                        f"✅ Telegram уже подключён!\n\n"
                        f"Авторизован как: {me.first_name} (ID: {me.id})\n\n"
                        f"Если хотите переподключить — удалю старую сессию и создам новую.\n"
                        f"Отправьте /connect_telegram force",
                    )
                    return
                await client.disconnect()
            except Exception:
                pass

        # Force reconnect — delete stale session
        text_cmd = (msg.text or "").strip()
        if "force" in text_cmd.lower() and session_path.exists():
            session_path.unlink(missing_ok=True)
            journal = Path(f"{session_path}-journal")
            journal.unlink(missing_ok=True)
            logger.info(f"[{cap_id}] Deleted stale session for reconnect")

        # Start QR flow
        connector = UserbotConnector(home, cap_id)
        result = await connector.request_qr()

        if result.get("error"):
            await msg.reply_text(f"❌ {result['error']}")
            return

        qr_path = result["qr_path"]

        # Store connector for background wait
        if not hasattr(self, "_tg_connectors"):
            self._tg_connectors = {}
        self._tg_connectors[(cap_id, user_id)] = connector

        # Send QR image
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Обновить QR", callback_data="onb:tgconnect_refresh")],
            [InlineKeyboardButton("❌ Отмена", callback_data="onb:tgconnect_cancel")],
        ])
        try:
            with open(qr_path, "rb") as f:
                await msg.reply_photo(
                    f,
                    caption=(
                        "📲 Сканируйте QR-код для подключения Telegram:\n\n"
                        "1️⃣ Откройте Telegram на телефоне\n"
                        "2️⃣ Настройки → Устройства → Привязать устройство\n"
                        "3️⃣ Наведите камеру на QR-код\n\n"
                        "⏳ QR действует 2 минуты"
                    ),
                    reply_markup=keyboard,
                )
        except Exception:
            await msg.reply_text(
                "📲 QR-код сгенерирован, но не удалось отправить картинку.\n"
                "Попробуйте /connect_telegram ещё раз.",
            )
            return

        # Background wait for scan (with hard timeout to prevent blocking)
        async def _wait_and_notify():
            needs_cleanup = True
            try:
                scan_result = await connector.wait_for_qr_scan(timeout=120)

                if scan_result.get("ok"):
                    await context.bot.send_message(
                        msg.chat_id,
                        f"✅ Telegram подключён!\n\n"
                        f"Авторизован как: {scan_result.get('name', '?')} "
                        f"(ID: {scan_result.get('user_id', '?')})\n\n"
                        f"Теперь я могу отправлять сообщения от вашего имени.",
                    )
                    return

                if scan_result.get("2fa"):
                    # Keep connector alive for 2FA password input
                    needs_cleanup = False
                    self._tg_connectors[(cap_id, user_id)] = connector
                    if not hasattr(self, "_tg_2fa_pending"):
                        self._tg_2fa_pending = {}
                    self._tg_2fa_pending[(cap_id, user_id)] = connector
                    await context.bot.send_message(
                        msg.chat_id,
                        "🔐 QR отсканирован! У вас включена двухфакторная аутентификация.\n\n"
                        "Отправьте пароль 2FA в этот чат:",
                    )
                    return

                # Expired or error — just notify, no recreate (prevents blocking)
                await context.bot.send_message(
                    msg.chat_id,
                    "⏳ QR истёк (2 минуты). Отправьте /connect_telegram чтобы получить новый.",
                )
            except Exception as e:
                logger.error(f"[{cap_id}] connect_telegram wait error: {e}", exc_info=True)
            finally:
                if needs_cleanup:
                    await connector.cleanup()

        asyncio.create_task(_wait_and_notify())

    async def _handle_rule(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /rule command — add user-defined rule to CLAUDE.md."""
        capsule: Capsule = context.bot_data["capsule"]
        msg = update.effective_message
        if not msg or not msg.text:
            return
        rule_text = msg.text.replace("/rule", "", 1).strip()
        if not rule_text:
            await msg.reply_text("Использование: /rule <ваше правило>\nПример: /rule всегда отвечай списком")
            return
        home = capsule.config.home_dir
        if home and self._append_user_rule(home, rule_text):
            await msg.reply_text(f"✅ Правило добавлено: «{rule_text}»")
        else:
            await msg.reply_text("⚠️ Не удалось сохранить правило.")

    @staticmethod
    def _append_user_rule(home_dir: str | None, rule: str) -> bool:
        """Append a user rule to CLAUDE.md in the capsule home directory."""
        if not home_dir or not rule:
            return False
        claude_md = Path(home_dir) / "CLAUDE.md"
        try:
            content = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""
            if "## Пользовательские правила" not in content:
                content += "\n\n## Пользовательские правила\n"
            content += f"- {rule}\n"
            claude_md.write_text(content, encoding="utf-8")
            logger.info(f"User rule added to {claude_md}: {rule}")
            return True
        except Exception as e:
            logger.error(f"Failed to save user rule: {e}")
            return False

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle onboarding callback queries (onb:* pattern)."""
        query = update.callback_query
        if not query or not query.data:
            return

        capsule: Capsule = context.bot_data["capsule"]
        user_id = update.effective_user.id

        if not self._onboarding:
            await query.answer("Онбординг не настроен")
            return

        await query.answer()

        data = query.data

        # /connect_telegram callbacks (outside onboarding)
        if data == "onb:tgconnect_refresh":
            cap_id = capsule.config.id
            connector = self._tg_connectors.get((cap_id, user_id)) if hasattr(self, "_tg_connectors") else None
            if connector:
                new_qr = await connector.recreate_qr()
                if new_qr.get("ok"):
                    try:
                        with open(new_qr["qr_path"], "rb") as f:
                            await query.message.reply_photo(f, caption="🔄 QR обновлён. Сканируйте заново (ещё 2 минуты):")
                    except Exception:
                        pass
            else:
                await query.message.reply_text("❌ Сессия потеряна. Отправьте /connect_telegram заново.")
            return

        if data == "onb:tgconnect_cancel":
            cap_id = capsule.config.id
            connector = self._tg_connectors.pop((cap_id, user_id), None) if hasattr(self, "_tg_connectors") else None
            if connector:
                await connector.cleanup()
            await query.message.reply_text("❌ Подключение отменено.")
            return

        text, keyboard, action = await self._onboarding.handle_callback(capsule, user_id, data)

        if not text:
            return

        # Handle toggle: atomic read-modify-write under lock (prevents race on double-click)
        if action == "toggle":
            cap_id = capsule.config.id
            lock = self._user_locks[(cap_id, user_id)]
            async with lock:
                state = await self._onboarding._state.get(cap_id, user_id)
                if state:
                    selected = state.get("integrations", {}).get("selected", [])
                    toggle_key = data.split(":")[2] if data.startswith("onb:toggle:") else None
                    if toggle_key:
                        if toggle_key in selected:
                            selected.remove(toggle_key)
                        else:
                            selected.append(toggle_key)
                        state["integrations"]["selected"] = selected
                        await self._onboarding._state.set(cap_id, user_id, state)
                        keyboard = self._onboarding._build_checklist_keyboard(state)
            try:
                await query.edit_message_reply_markup(reply_markup=keyboard)
            except Exception:
                pass
            return

        if action == "qr_send":
            # Send QR image + text + start background wait
            import asyncio as _asyncio
            state = await self._onboarding._state.get(capsule.config.id, user_id)
            qr_path = state.get("userbot_qr_path") if state else None
            if qr_path:
                try:
                    with open(qr_path, "rb") as f:
                        await query.message.reply_photo(f, caption=text, reply_markup=keyboard)
                except Exception:
                    await query.message.reply_text(text, reply_markup=keyboard)
                # Start background wait for QR scan (tracked for cleanup)
                cap_id_qr = capsule.config.id
                task = _asyncio.create_task(
                    self._onboarding.start_qr_background_wait(
                        cap_id_qr, user_id, capsule,
                        context.bot, query.message.chat_id,
                    )
                )
                self._onboarding._qr_tasks[(cap_id_qr, user_id)] = task
            else:
                await query.message.reply_text(text, reply_markup=keyboard)
            return

        if action == "qr_refresh":
            # Send refreshed QR image
            state = await self._onboarding._state.get(capsule.config.id, user_id)
            qr_path = state.get("userbot_qr_path") if state else None
            if qr_path:
                try:
                    with open(qr_path, "rb") as f:
                        await query.message.reply_photo(f, caption="\U0001f504 QR обновлён. Сканируйте:")
                except Exception:
                    pass
            return

        if action == "edit":
            try:
                await query.edit_message_text(text, reply_markup=keyboard)
            except Exception:
                await query.message.reply_text(text, reply_markup=keyboard)
        else:  # "reply"
            await query.message.reply_text(text, reply_markup=keyboard)

    async def _handle_action_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle action confirmation callbacks (action:confirm / action:reject)."""
        query = update.callback_query
        if not query or not query.data:
            return

        await query.answer()

        capsule: Capsule = context.bot_data["capsule"]
        data = query.data  # "action:confirm" or "action:reject"
        parts = data.split(":")
        action = parts[1] if len(parts) > 1 else ""

        user_id = update.effective_user.id
        cap_id = capsule.config.id
        thread_id = getattr(query.message, "message_thread_id", None)

        # Remove inline buttons from the original message
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        if action == "confirm":
            # Send confirmation back to Claude session via resume
            follow_up = IncomingMessage(
                capsule_id=cap_id, user_id=user_id,
                user_name=update.effective_user.first_name or "",
                text="Подтверждено. Выполняй действие.",
                thread_id=thread_id,
                chat_id=query.message.chat_id,
            )
            await self._process_message(query.message, capsule, follow_up)
        else:
            # Rejected — notify user, send cancellation to Claude session
            await query.message.reply_text(
                "❌ Действие отменено.",
                message_thread_id=thread_id,
            )
            # Also inform Claude so it knows the action was rejected
            follow_up = IncomingMessage(
                capsule_id=cap_id, user_id=user_id,
                user_name=update.effective_user.first_name or "",
                text="Отменено пользователем. Не выполняй действие.",
                thread_id=thread_id,
                chat_id=query.message.chat_id,
            )
            await self._process_message(query.message, capsule, follow_up)

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message
        if not msg or not msg.text:
            return

        capsule: Capsule = context.bot_data["capsule"]
        user = update.effective_user
        if user and user.is_bot:
            return
        user_id = user.id
        logger.info(f"Text from user_id={user_id}, name={user.first_name}, text={msg.text[:200]!r}")

        # /connect_telegram 2FA intercept
        cap_id = capsule.config.id
        if hasattr(self, "_tg_2fa_pending") and (cap_id, user_id) in self._tg_2fa_pending:
            connector = self._tg_2fa_pending.pop((cap_id, user_id))
            try:
                result = await connector.sign_in_2fa(msg.text.strip())
                if result.get("ok"):
                    await msg.reply_text(
                        f"✅ Telegram подключён!\n\n"
                        f"Авторизован как: {result.get('name', '?')} "
                        f"(ID: {result.get('user_id', '?')})\n\n"
                        f"Теперь я могу отправлять сообщения от вашего имени.",
                    )
                else:
                    await msg.reply_text(f"❌ {result.get('error', 'Ошибка 2FA')}. Попробуйте /connect_telegram заново.")
            except Exception as e:
                await msg.reply_text(f"❌ Ошибка: {e}. Попробуйте /connect_telegram заново.")
            return

        # Onboarding intercept — BEFORE employee check
        if self._onboarding:
            try:
                result = await self._onboarding.handle_text(capsule, user_id, msg.text.strip())
                if result is not None:
                    text, keyboard = result
                    await msg.reply_text(text, reply_markup=keyboard)
                    # Save onboarding interaction to diary
                    incoming = IncomingMessage(capsule_id=capsule.config.id, user_id=user_id, user_name=msg.from_user.first_name or "", text=msg.text.strip(), source="telegram", thread_id=None)
                    await self._save_diary(capsule, incoming, text, ["onboarding"])
                    return
            except Exception as e:
                logger.error(f"Onboarding text error: {e}", exc_info=True)

        if not capsule.is_employee(user_id):
            logger.warning(f"User {user_id} not authorized for capsule {capsule.config.id} (owner={capsule.config.owner_telegram_id})")
            if self._metrics:
                await self._metrics.record_request(capsule.config.id, 0, success=False, error_type="UNAUTHORIZED")
            return

        # Group chat: only respond when bot is mentioned by name or tagged
        # Exception: internal groups (HQ) — always respond (employees only, already checked above)
        # mention_required_groups overrides internal_groups for TEXT (require mention even in internal)
        if msg.chat.type in ("group", "supergroup"):
            is_internal = msg.chat.id in capsule.config.internal_groups
            mention_required = capsule.config.mention_required_groups
            if not is_internal or msg.chat.id in mention_required:
                bot_username = context.bot.username or ""
                text_lower = (msg.text or "").lower()
                mentioned = (
                    (bot_username and f"@{bot_username}".lower() in text_lower)
                    or "нэйра" in text_lower
                    or "нейра" in text_lower
                )
                # Also respond if replying directly to bot's message
                if not mentioned and msg.reply_to_message and msg.reply_to_message.from_user:
                    mentioned = msg.reply_to_message.from_user.is_bot
                if not mentioned:
                    logger.info(f"Group msg from {user_id} ignored — bot not mentioned (chat={msg.chat.title!r}, chat_id={msg.chat.id})")
                    return

        if capsule.is_trial_expired():
            expired_msg = capsule.config.trial.get(
                "expired_message",
                "⏰ Пробный период завершён. Свяжитесь с администратором.",
            )
            await msg.reply_text(expired_msg)
            if self._metrics:
                await self._metrics.record_request(capsule.config.id, 0, success=False, error_type="TRIAL_EXPIRED")
            return

        cap_id = capsule.config.id
        max_per_day = capsule.config.rate_limit.get("max_per_day", 100)
        rl = await self._queue.check_rate_limit(cap_id, max_per_day)
        if rl == "blocked":
            await msg.reply_text("🚫 Лимит запросов на сегодня достигнут.")
            if self._metrics:
                await self._metrics.record_request(cap_id, 0, success=False, error_type="RATE_BLOCKED")
            return

        text = msg.text.strip()
        if not text:
            return

        # Parse !directives (before any other processing)
        directives = parse_directives(text)
        text = directives.clean_text
        if not text:
            return

        # !queue — add to queue without processing
        if directives.queue:
            count = await self._queue.add_btw(
                cap_id, QueuedMessage(text=text, timestamp=_time.time()),
                user_id=user_id)
            await msg.reply_text(f"📋 Добавлено в очередь (+{count}). Будет обработано с следующим запросом.")
            return

        # Reply context
        reply_ctx = await self._get_reply_context(msg, context.bot)
        if reply_ctx:
            text = f"[Ответ на сообщение]: {reply_ctx}\n\n{text}"

        # BTW queue — per user_id to prevent cross-contamination in multi-employee capsules
        if await self._queue.is_processing(cap_id):
            processing_user = await self._queue.get_processing_user(cap_id)
            if processing_user == user_id:
                # Same user — batch as BTW
                count = await self._queue.add_btw(
                    cap_id, QueuedMessage(text=text, timestamp=_time.time()),
                    user_id=user_id)
                await msg.reply_text(f"📎 Принято (+{count}), добавлю к текущему запросу")
            else:
                # Different user — queue separately, don't mix contexts
                count = await self._queue.add_btw(
                    cap_id, QueuedMessage(text=text, timestamp=_time.time()),
                    user_id=user_id)
                await msg.reply_text(f"⏳ Сейчас работаю над запросом другого сотрудника. Ваше сообщение в очереди (+{count}), отвечу сразу после.")
            return

        incoming = IncomingMessage(
            capsule_id=cap_id, user_id=user_id,
            user_name=update.effective_user.first_name or "",
            text=text, message_type=MessageType.TEXT,
            thread_id=getattr(msg, "message_thread_id", None),
            chat_id=msg.chat.id,
        )
        await self._process_message(
            msg, capsule, incoming,
            warn_rate=(rl == "warn"), directives=directives,
        )

    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message
        if not msg:
            return

        capsule: Capsule = context.bot_data["capsule"]
        user = update.effective_user
        if user and user.is_bot:
            return
        user_id = user.id

        if not capsule.is_employee(user_id):
            if self._metrics:
                await self._metrics.record_request(capsule.config.id, 0, success=False, error_type="UNAUTHORIZED")
            return

        # Group chat: voice messages processed only in internal groups
        if msg.chat.type in ("group", "supergroup"):
            if msg.chat.id not in capsule.config.internal_groups:
                logger.info(f"Voice in group from {user_id} ignored — not internal group (chat={msg.chat.title!r}, chat_id={msg.chat.id})")
                return

        cap_id = capsule.config.id

        max_per_day = capsule.config.rate_limit.get("max_per_day", 100)
        rl = await self._queue.check_rate_limit(cap_id, max_per_day)
        if rl == "blocked":
            await msg.reply_text("🚫 Лимит запросов достигнут.")
            if self._metrics:
                await self._metrics.record_request(cap_id, 0, success=False, error_type="RATE_BLOCKED")
            return

        voice_obj = msg.voice or msg.audio
        # Also handle audio files sent as documents
        if not voice_obj and msg.document:
            mime = getattr(msg.document, "mime_type", "") or ""
            if mime.startswith("audio/") or mime in ("video/ogg",):
                voice_obj = msg.document
        if not voice_obj:
            await msg.reply_text("❌ Не удалось получить аудио.")
            return

        try:
            duration = int(getattr(voice_obj, 'duration', 0) or 0)
        except (TypeError, ValueError):
            duration = 0
        file_size = getattr(voice_obj, 'file_size', 0) or 0
        dur_text = f" ({duration // 60}:{duration % 60:02d})" if duration > 10 else ""
        size_mb = file_size / (1024 * 1024) if file_size else 0
        if size_mb > 20:
            dur_text += f", {size_mb:.0f}MB"
        status_msg = await msg.reply_text(f"🎙 Расшифровываю голосовое{dur_text}...")

        # Determine file extension from mime_type
        mime = getattr(voice_obj, 'mime_type', '') or 'audio/ogg'
        ext_map = {
            "audio/ogg": ".ogg", "audio/mpeg": ".mp3", "audio/mp4": ".m4a",
            "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/webm": ".webm",
            "audio/flac": ".flac", "audio/aac": ".aac", "video/ogg": ".ogg",
        }
        suffix = ext_map.get(mime, ".ogg")

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                tmp_path = f.name

            # Try Bot API first (<20MB), fallback to MTProto for large files
            downloaded = False
            if file_size <= 20 * 1024 * 1024:
                try:
                    file = await context.bot.get_file(voice_obj.file_id)
                    await file.download_to_drive(tmp_path)
                    downloaded = True
                except Exception as e:
                    if "too big" in str(e).lower() or "file is too big" in str(e).lower():
                        logger.info(f"Bot API download failed (too big), trying MTProto: {e}")
                    else:
                        raise

            if not downloaded:
                # MTProto fallback — no 20MB limit
                bot_token = capsule.config.bot_token
                ok = await download_via_mtproto(
                    bot_token, msg.chat.id, msg.message_id, tmp_path
                )
                if not ok:
                    await status_msg.edit_text("❌ Файл слишком большой для скачивания.")
                    return

            text = await transcribe_voice(tmp_path)
        except Exception as e:
            logger.error(f"Voice error: {e}")
            await status_msg.edit_text("❌ Ошибка обработки голосового.")
            return
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        if text.startswith("❌"):
            await status_msg.edit_text(text)
            return

        # For long transcriptions — also send as TXT file
        if len(text) > 4000:
            txt_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as f:
                    f.write(text)
                    txt_path = f.name
                thread_id = getattr(msg, "message_thread_id", None)
                await msg.reply_document(
                    document=open(txt_path, "rb"),
                    filename="transcription.txt",
                    caption=f"📝 Транскрипция ({len(text)} символов)",
                    message_thread_id=thread_id,
                )
            except Exception as e:
                logger.warning(f"Failed to send TXT transcription: {e}")
            finally:
                if txt_path:
                    try:
                        os.unlink(txt_path)
                    except Exception:
                        pass

        preview = text[:100] + "..." if len(text) > 100 else text

        # BTW queue check — AFTER transcription so the actual text goes into queue
        if await self._queue.is_processing(cap_id):
            count = await self._queue.add_btw(
                cap_id, QueuedMessage(text=f"[Голосовое сообщение]: {text}", timestamp=_time.time()),
                user_id=user_id)
            try:
                await status_msg.edit_text(f"📎 Голосовое принято (+{count}): _{preview}_\nОбработаю после текущего запроса",
                                           parse_mode="Markdown")
            except Exception:
                pass
            return

        try:
            await status_msg.edit_text(f"✍️ Обрабатываю: _{preview}_", parse_mode="Markdown")
        except Exception:
            pass

        # Onboarding intercept for voice (same as text handler)
        if self._onboarding:
            result = await self._onboarding.handle_text(capsule, user_id, text.strip())
            if result is not None:
                onb_text, keyboard = result
                try:
                    await status_msg.delete()
                except Exception:
                    pass
                await msg.reply_text(onb_text, reply_markup=keyboard)
                return

        incoming = IncomingMessage(
            capsule_id=cap_id, user_id=user_id,
            user_name=update.effective_user.first_name or "",
            text=f"[Голосовое сообщение]: {text}",
            message_type=MessageType.VOICE,
            thread_id=getattr(msg, "message_thread_id", None),
            chat_id=msg.chat.id,
        )
        await self._process_message(msg, capsule, incoming, status_msg=status_msg)

    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message
        if not msg:
            return

        capsule: Capsule = context.bot_data["capsule"]
        if not capsule.is_employee(update.effective_user.id):
            return

        if msg.chat.type in ("group", "supergroup"):
            if msg.chat.id not in capsule.config.internal_groups:
                return

        photos = msg.photo
        if not photos:
            return

        largest = photos[-1]
        tmp_path = None
        try:
            tmp_path = _upload_path(capsule, ".jpg")
            file = await context.bot.get_file(largest.file_id)
            await file.download_to_drive(tmp_path)
        except Exception as e:
            logger.error(f"Photo download error: {e}")
            await msg.reply_text("❌ Ошибка загрузки фото.")
            return

        caption = msg.caption or "Проанализируй это изображение."
        prompt = f"Пользователь отправил фото: {tmp_path}\n\nЗадача: {caption}"

        incoming = IncomingMessage(
            capsule_id=capsule.config.id,
            user_id=update.effective_user.id,
            user_name=update.effective_user.first_name or "",
            text=prompt, message_type=MessageType.PHOTO,
            file_path=tmp_path,
            thread_id=getattr(msg, "message_thread_id", None),
            chat_id=msg.chat.id,
        )
        await self._process_message(msg, capsule, incoming)

    async def _handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message
        if not msg or not msg.document:
            return

        capsule: Capsule = context.bot_data["capsule"]
        if not capsule.is_employee(update.effective_user.id):
            return

        if msg.chat.type in ("group", "supergroup"):
            if msg.chat.id not in capsule.config.internal_groups:
                return

        doc = msg.document
        filename = doc.file_name or "document"

        tmp_path = None
        try:
            ext = os.path.splitext(filename)[1] or ".bin"
            tmp_path = _upload_path(capsule, ext, filename)
            file = await context.bot.get_file(doc.file_id)
            await file.download_to_drive(tmp_path)
        except Exception as e:
            logger.error(f"Document download error: {e}")
            await msg.reply_text("❌ Ошибка загрузки документа.")
            return

        caption = msg.caption or f"Обработай этот документ: {filename}"

        # Extract text via markitdown (DOCX, XLSX, PPTX, HTML, TXT, CSV)
        # PDF goes directly to Claude CLI (native Read tool support)
        # .doc (legacy Word) — markitdown не поддерживает, сообщаем пользователю
        extracted_text = None
        ext_lower = ext.lower()
        if ext_lower == ".doc":
            # Auto-convert .doc → .docx via LibreOffice
            try:
                import subprocess
                conv_dir = os.path.dirname(tmp_path)
                conv_result = subprocess.run(
                    ["libreoffice", "--headless", "--convert-to", "docx", "--outdir", conv_dir, tmp_path],
                    capture_output=True, text=True, timeout=30,
                )
                docx_path = tmp_path.rsplit(".", 1)[0] + ".docx"
                if os.path.exists(docx_path):
                    tmp_path = docx_path
                    ext_lower = ".docx"
                    logger.info(f"Auto-converted .doc → .docx: {docx_path}")
                else:
                    logger.warning(f"LibreOffice conversion failed: {conv_result.stderr[:200]}")
                    await msg.reply_text(
                        "⚠️ Файл в старом формате Word (.doc). "
                        "Не удалось конвертировать автоматически. "
                        "Пожалуйста, пересохраните как .docx и отправьте заново."
                    )
                    return
            except Exception as e:
                logger.warning(f".doc auto-convert failed: {e}")
                await msg.reply_text(
                    "⚠️ Файл в старом формате Word (.doc). "
                    "Пожалуйста, пересохраните его как .docx "
                    "(Файл → Сохранить как → DOCX) и отправьте заново."
                )
                return
        if ext_lower not in (".pdf",):
            try:
                from markitdown import MarkItDown
                md_converter = MarkItDown()
                result = md_converter.convert(tmp_path)
                extracted_text = result.text_content
                logger.info(f"markitdown extracted: {len(extracted_text)} chars from {filename}")
            except Exception as e:
                logger.warning(f"markitdown failed for {filename}: {e}")

        if extracted_text:
            if len(extracted_text) > 50000:
                extracted_text = extracted_text[:50000] + "\n\n... (документ обрезан, слишком большой)"
            prompt = (f"Пользователь отправил документ {filename}.\n\n"
                      f"Содержимое документа:\n\n{extracted_text}\n\n"
                      f"Задача: {caption}")
        else:
            prompt = f"Пользователь отправил документ {filename}: {tmp_path}\n\nЗадача: {caption}"

        incoming = IncomingMessage(
            capsule_id=capsule.config.id,
            user_id=update.effective_user.id,
            user_name=update.effective_user.first_name or "",
            text=prompt, message_type=MessageType.DOCUMENT,
            file_path=tmp_path, file_name=filename,
            thread_id=getattr(msg, "message_thread_id", None),
            chat_id=msg.chat.id,
        )
        await self._process_message(msg, capsule, incoming)

    async def _handle_error(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(f"Telegram error: {context.error}", exc_info=context.error)

    # ── Core Pipeline ───────────────────────────────────────────

    async def _process_message(self, msg, capsule: Capsule,
                               incoming: IncomingMessage,
                               status_msg=None, warn_rate: bool = False,
                               directives=None) -> None:
        """Core pipeline: context → stream → parse → send → diary → BTW flush.

        Session resume: if we have an active session_id for this (capsule, user),
        we send only the user message via --resume instead of rebuilding full context.
        This saves tokens, preserves conversation history, and keeps file references.
        """
        cap_id = capsule.config.id
        user_id = incoming.user_id
        await self._queue.set_processing(cap_id, True, user_id=user_id)
        start_time = _time.monotonic()

        accumulated_text = ""
        tools_used: list[str] = []
        engine_error: str | None = None
        result_session_id: str = ""

        thread_id = incoming.thread_id

        try:
            # 1. Check for existing session to resume (per-topic in forum groups)
            existing_session = await self._session_tracker.get(cap_id, user_id, thread_id)
            engine_cfg = capsule.get_engine_config()

            # Apply !directives to engine config (model, effort, tools)
            if directives and directives.has_any:
                directives.apply_to_engine_config(engine_cfg)
                logger.info(f"[{cap_id}] Directives applied: {directives.raw_directives} → model={engine_cfg.model}")

            if existing_session:
                # RESUME: send user message + vector context for relevant knowledge
                vector_ctx = ""
                try:
                    vector_ctx = self._memory._vector_search(capsule, incoming.text)
                except Exception as e:
                    logger.debug(f"[{cap_id}] Resume vector search failed: {e}")
                if vector_ctx:
                    full_prompt = incoming.text + "\n\n" + vector_ctx
                else:
                    full_prompt = incoming.text
                engine_cfg.resume_session_id = existing_session
                logger.info(f"[{cap_id}] Resuming session {existing_session[:12]}… prompt={len(full_prompt)} chars (vector: {'yes' if vector_ctx else 'no'})")
            else:
                # NEW SESSION: build full context (system prompt, diary, memory)
                parts = await self._memory.build_context_parts(
                    capsule, incoming.text, thread_id=incoming.thread_id)
                builder = ContextBuilder(capsule)
                full_prompt = builder.build(incoming.text, parts, is_first_message=True)
                logger.info(f"[{cap_id}] New session, context built, prompt={len(full_prompt)} chars")

            # Apply directive prompt modifications (think/brief/web)
            if directives and directives.has_any:
                full_prompt = directives.apply_to_prompt(full_prompt)

            # Link understanding: enrich prompt with URL metadata
            if extract_urls(incoming.text):
                try:
                    link_context = await enrich_with_links(
                        incoming.text, self._queue._r
                    )
                    if link_context:
                        full_prompt += link_context
                        logger.info(f"[{cap_id}] Link context added: {len(link_context)} chars")
                except Exception as e:
                    logger.warning(f"[{cap_id}] Link understanding failed: {e}")

            # 2. Stream response
            responder = StreamingResponder(msg, existing_msg=status_msg)
            await responder.start()

            chunk_count = 0
            cancelled = False
            async for chunk in self._engine.stream(full_prompt, engine_cfg):
                # Check for cancellation every 10 chunks
                if chunk_count % 10 == 0 and chunk_count > 0:
                    if await self._queue.is_cancelled(cap_id):
                        cancelled = True
                        logger.info(f"[{cap_id}] Stream cancelled by user after {chunk_count} chunks")
                        break

                chunk_count += 1
                # Capture session_id from any chunk that has it
                if chunk.session_id and not result_session_id:
                    result_session_id = chunk.session_id
                if chunk.type == "text":
                    accumulated_text += chunk.text
                    await responder.on_text(accumulated_text)
                elif chunk.type == "tool_start":
                    tools_used.append(chunk.tool)
                    await responder.on_tool(chunk.text)
                elif chunk.type == "result":
                    accumulated_text = chunk.text or accumulated_text
                    if chunk.session_id:
                        result_session_id = chunk.session_id
                elif chunk.type == "error":
                    engine_error = chunk.text
                    logger.error(f"[{cap_id}] Engine error chunk: {chunk.text}")

            if cancelled:
                await responder.finalize(None)
                await msg.reply_text("⏹️ Запрос отменён.")
                await self._queue.set_processing(cap_id, False)
                return

            logger.info(f"[{cap_id}] Stream done: {chunk_count} chunks, {len(accumulated_text)} chars")

            # 2.0 Save session_id for next message (or invalidate on error)
            if engine_error and existing_session:
                # Resume failed — invalidate and will start fresh next time
                await self._session_tracker.invalidate(cap_id, user_id, thread_id)
                logger.info(f"[{cap_id}] Session invalidated after error, will start fresh next time")
            elif result_session_id:
                await self._session_tracker.set(cap_id, user_id, result_session_id, thread_id)
                logger.info(f"[{cap_id}] Session saved: {result_session_id[:12]}…")

            # 2a. Intercept engine errors — never show raw API errors to user
            if engine_error:
                logger.warning(f"[{cap_id}] Replacing error response with user-friendly message")
                await responder.finalize(None)
                await msg.reply_text("⚠️ Временная ошибка. Попробуйте ещё раз через минуту.")
                # Save error to diary for debugging but don't show to user
                await self._save_diary(capsule, incoming, f"[ENGINE_ERROR] {engine_error}", tools_used)
                if self._metrics:
                    duration = _time.monotonic() - start_time
                    await self._metrics.record_request(cap_id, duration, success=False)
                return

            # 2b. Guard against empty response
            if not accumulated_text.strip():
                if tools_used:
                    # Tools ran but no text output — still a valid response
                    logger.info(f"[{cap_id}] Tool-only response ({len(tools_used)} tools, 0 text chars)")
                    await responder.finalize(None)
                    await msg.reply_text(f"✅ Выполнено ({', '.join(tools_used[:3])})")
                else:
                    logger.warning(f"[{cap_id}] Empty response (0 chars, 0 tools). Notifying user.")
                    await responder.finalize(None)
                    await msg.reply_text("⚠️ Не удалось получить ответ. Попробуйте ещё раз.")
                return

            # 3. Parse response (allow files from capsule home_dir + /tmp/)
            home = capsule.config.home_dir
            prefixes = ["/tmp/"]
            if home:
                prefixes.append(str(Path(home).resolve()) + "/")
            response = ResponseParser.parse(accumulated_text, allowed_prefixes=prefixes)

            # 4. Save learnings/corrections/rules/memory/facts
            for learn in response.learnings:
                await self._memory.add_learning(cap_id, learn)
            for corr in response.corrections:
                await self._memory.add_correction(cap_id, corr)
            for rule in response.rules:
                self._append_user_rule(home, rule)
            for mem in response.memory_entries:
                await self._memory.add_memory(cap_id, mem, source="agent")
            for subj, pred, obj in response.facts:
                await self._memory.add_triple(cap_id, subj, pred, obj, source="agent")

            # 4a. Auto-extract facts from conversation
            auto_mem = _auto_extract_facts(incoming.text, accumulated_text)
            for mem in auto_mem:
                await self._memory.add_memory(cap_id, mem, source="auto")

            # 5. Rate warning
            if warn_rate:
                response.text += "\n\n⚠️ Приближаетесь к лимиту запросов на сегодня."

            # 6. Finalize streaming message
            await responder.finalize(response)

            # 7. Send response as new message (finalize always deletes streaming msg)
            await self._send_response(msg, response)

            # 8. Diary
            await self._save_diary(capsule, incoming, accumulated_text, tools_used)

            # 8a. Sync to web platform (topic → conversation)
            try:
                if self._memory and self._memory._pool:
                    conv_id = await ensure_web_conversation(
                        self._memory._pool, cap_id,
                        incoming.chat_id, incoming.thread_id,
                    )
                    if conv_id:
                        duration = _time.monotonic() - start_time
                        await save_web_message(
                            self._memory._pool, conv_id,
                            "user", incoming.text[:4000],
                        )
                        await save_web_message(
                            self._memory._pool, conv_id,
                            "assistant", accumulated_text[:8000],
                            model=capsule.config.model, duration_sec=duration,
                        )
            except Exception as e:
                logger.debug(f"Web sync skipped: {e}")

            # 9. Rate counter
            await self._queue.increment_rate(cap_id)

            # 10. Metrics (success)
            duration = _time.monotonic() - start_time
            if self._metrics:
                await self._metrics.record_request(cap_id, duration, success=True)

            # 11. Skill learning — detect & record skill usage
            if self._skill_collector:
                try:
                    skill_name = self._skill_collector.detect_skill(
                        incoming.text, accumulated_text, tools_used,
                        capsule.config.skills,
                    )
                    if skill_name:
                        entry = SkillUsageEntry(
                            capsule_id=cap_id, skill_name=skill_name,
                            success=True, duration_sec=duration,
                            user_intent=incoming.text[:200],
                            tools_used=tools_used,
                            correction="",
                        )
                        await self._skill_collector.record(entry)
                        logger.debug(f"[{cap_id}] Skill recorded: {skill_name}")

                        # Check if skill should evolve
                        if self._skill_evolver and await self._skill_evolver.should_evolve(skill_name):
                            evolved = await self._skill_evolver.apply_evolution(skill_name)
                            if evolved:
                                logger.info(f"Skill auto-evolved: {skill_name}")
                except Exception as e_skill:
                    logger.warning(f"Skill learning error: {e_skill}")

        except Exception as e:
            logger.error(f"Processing error for {cap_id}: {e}", exc_info=True)
            # Invalidate session on crash — next message will start fresh
            await self._session_tracker.invalidate(cap_id, user_id, thread_id)
            # Metrics (error)
            if self._metrics:
                duration = _time.monotonic() - start_time
                await self._metrics.record_request(cap_id, duration, success=False,
                                                   error_type="EXCEPTION")
            # Alert
            if self._alert_sender:
                await self._alert_sender.send(
                    f"{cap_id}: {type(e).__name__}: {e}",
                    alert_type="CAPSULE_ERROR",
                    capsule_id=cap_id,
                )
            try:
                await msg.reply_text("Техническая ошибка. Попробуйте ещё раз.")
            except Exception:
                pass
        finally:
            # Cleanup temp file (only /tmp/, never persistent uploads/)
            if incoming.file_path and incoming.file_path.startswith("/tmp/"):
                try:
                    os.unlink(incoming.file_path)
                except Exception:
                    pass

            # BTW follow-up — flush per user_id (INSIDE lock to prevent race)
            try:
                btw_messages = await self._queue.flush_btw(cap_id, user_id=user_id)
            except Exception:
                btw_messages = []

            # Release lock AFTER BTW flush
            await self._queue.set_processing(cap_id, False, user_id=user_id)

        # Process BTW follow-up outside lock
        if btw_messages:
            combined = "\n\n".join(m.text for m in btw_messages)
            follow_up = IncomingMessage(
                capsule_id=cap_id, user_id=incoming.user_id,
                user_name=incoming.user_name, text=combined,
                thread_id=incoming.thread_id, chat_id=incoming.chat_id,
            )
            await self._process_message(msg, capsule, follow_up)

    async def _send_response(self, msg, response: OutgoingMessage,
                             files_only: bool = False) -> None:
        """Send files + text with Telegraph/Markdown fallback."""
        thread_id = getattr(msg, "message_thread_id", None)

        # 1. Send files
        for f in response.files:
            if not os.path.exists(f.path):
                logger.warning(f"File not found at send time: {f.path}")
                try:
                    await msg.reply_text(
                        f"\u26a0\ufe0f Не удалось отправить файл: файл не найден.",
                        message_thread_id=thread_id,
                    )
                except Exception:
                    pass
                continue
            try:
                file_size = os.path.getsize(f.path)
                if file_size > 50 * 1024 * 1024:
                    size_mb = file_size / (1024 * 1024)
                    await msg.reply_text(
                        f"\u26a0\ufe0f Файл слишком большой ({size_mb:.0f} МБ). "
                        f"Лимит Telegram — 50 МБ.",
                        message_thread_id=thread_id,
                    )
                    continue
                if f.is_photo:
                    with open(f.path, "rb") as fh:
                        await msg.reply_photo(fh, caption=f.caption,
                                              message_thread_id=thread_id)
                else:
                    with open(f.path, "rb") as fh:
                        await msg.reply_document(fh, filename=f.filename,
                                                 caption=f.caption,
                                                 message_thread_id=thread_id)
                if f.path.startswith("/tmp/"):
                    try:
                        os.unlink(f.path)
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"File send error: {e}")
                try:
                    await msg.reply_text(
                        f"\u26a0\ufe0f Не удалось отправить файл. Попробуйте ещё раз.",
                        message_thread_id=thread_id,
                    )
                except Exception:
                    pass

        if not response.text or files_only:
            return

        # 1b. Action confirmation with inline buttons
        if response.pending_action:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Да", callback_data="action:confirm"),
                InlineKeyboardButton("❌ Нет", callback_data="action:reject"),
            ]])
            try:
                await msg.reply_text(
                    response.text, reply_markup=keyboard,
                    message_thread_id=thread_id, parse_mode="Markdown",
                )
            except Exception:
                await msg.reply_text(
                    response.text, reply_markup=keyboard,
                    message_thread_id=thread_id,
                )
            return

        # 2. Telegraph for long messages
        if response.is_long:
            url = response.telegraph_url
            if not url:
                title = response.text[:50].replace('\n', ' ')
                url = create_telegraph_page(title, response.text)
            if url:
                preview = response.text[:300].replace('*', '').replace('#', '').replace('`', '')
                await msg.reply_text(
                    f"{preview}...\n\n📖 Полный ответ: {url}",
                    message_thread_id=thread_id,
                    disable_web_page_preview=False,
                )
                return

        # 3. Regular send with Markdown fallback
        if len(response.text) <= 4000:
            try:
                await msg.reply_text(response.text, message_thread_id=thread_id,
                                     parse_mode="Markdown")
                return
            except Exception:
                try:
                    await msg.reply_text(response.text, message_thread_id=thread_id)
                    return
                except Exception as e:
                    logger.error(f"Reply error: {e}")
                    return

        # 4. Chunked send
        chunks: list[str] = []
        current = ""
        for line in response.text.split("\n"):
            if len(current) + len(line) + 1 > 4000:
                if current:
                    chunks.append(current)
                current = line
            else:
                current = current + "\n" + line if current else line
        if current:
            chunks.append(current)

        for chunk in chunks[:10]:
            try:
                await msg.reply_text(chunk, message_thread_id=thread_id)
            except Exception as e:
                logger.error(f"Chunk send error: {e}")
                break

    async def _get_reply_context(self, message, bot=None) -> str:
        """Extract text from replied-to message."""
        reply = message.reply_to_message
        if not reply:
            return ""

        # Voice reply — transcribe (with MTProto fallback for large files)
        voice_obj = getattr(reply, "voice", None) or getattr(reply, "audio", None)
        # Also handle audio documents in reply
        if not voice_obj and getattr(reply, "document", None):
            doc_mime = getattr(reply.document, "mime_type", "") or ""
            if doc_mime.startswith("audio/"):
                voice_obj = reply.document
        if voice_obj and bot:
            tmp_path = None
            try:
                mime = getattr(voice_obj, 'mime_type', '') or 'audio/ogg'
                ext_map = {
                    "audio/ogg": ".ogg", "audio/mpeg": ".mp3", "audio/mp4": ".m4a",
                    "audio/wav": ".wav", "audio/webm": ".webm", "audio/flac": ".flac",
                }
                suffix = ext_map.get(mime, ".ogg")
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                    tmp_path = f.name

                downloaded = False
                file_size = getattr(voice_obj, 'file_size', 0) or 0
                if file_size <= 20 * 1024 * 1024:
                    try:
                        file = await bot.get_file(voice_obj.file_id)
                        await file.download_to_drive(tmp_path)
                        downloaded = True
                    except Exception as e:
                        if "too big" not in str(e).lower():
                            raise
                        logger.info(f"Reply voice too big for Bot API, trying MTProto")

                if not downloaded:
                    ok = await download_via_mtproto(
                        bot.token, reply.chat.id, reply.message_id, tmp_path
                    )
                    if not ok:
                        return "[Голосовое сообщение — файл слишком большой]"

                text = await transcribe_voice(tmp_path)
                if text and not text.startswith("❌"):
                    return f"[Голосовое сообщение]: {text.strip()}"
            except Exception as e:
                logger.warning(f"Reply voice transcription error: {e}")
            finally:
                if tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
            return "[Голосовое сообщение — не удалось расшифровать]"

        reply_text = getattr(reply, "text", "") or getattr(reply, "caption", "") or ""
        if not reply_text:
            return ""

        # Skip status messages
        status_prefixes = ("⏳ ", "🎙 ", "✍️ ", "🧠 Думаю")
        is_bot = getattr(reply.from_user, "is_bot", False) if reply.from_user else False
        if is_bot and len(reply_text) < 100 and any(reply_text.startswith(p) for p in status_prefixes):
            return ""

        if len(reply_text) > 2000:
            reply_text = reply_text[:2000] + "..."

        if is_bot:
            return (
                f"[Ответ на твоё сообщение]: {reply_text}\n"
                "Пользователь ответил — реагируй тепло, продолжи тему."
            )

        return reply_text

    async def _save_diary(self, capsule: Capsule, incoming: IncomingMessage,
                          response_text: str, tools_used: list[str]) -> None:
        """Save interaction to diary via MemoryStore."""
        now = datetime.now(timezone.utc)
        entry = DiaryEntry(
            capsule_id=capsule.config.id,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            user_message=incoming.text[:2000],
            bot_response=response_text[:2000],
            model=capsule.config.model,
            tools_used=tools_used,
            source=incoming.source,
            thread_id=incoming.thread_id,
        )
        try:
            await self._memory.add_diary(entry)
        except Exception as e:
            logger.error(f"Diary save error: {e}")
