"""Multi-bot Telegram transport — one process, all capsules.

Handles: text, voice, photo, document messages.
Features: streaming response (progressive edit), BTW queue, Telegraph for long messages.

Ported from v1:
  - neura-capsule/bot/handlers/text.py (BTW pattern, message handling)
  - neura-capsule/bot/handlers/voice.py (voice download + transcribe)
  - neura-capsule/bot/handlers/_common.py (reply context)
  - neura-capsule/bot/utils/progress.py (streaming updater)
"""
import logging
import os
import tempfile
import time as _time
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters,
)

from neura.core.capsule import Capsule
from neura.core.context import ContextBuilder
from neura.core.engine import ClaudeEngine, Chunk
from neura.core.memory import DiaryEntry, MemoryStore
from neura.core.queue import QueuedMessage, RequestQueue
from neura.transport.protocol import (
    IncomingMessage, MessageType, OutgoingMessage, ResponseParser,
    create_telegraph_page, transcribe_voice,
)

logger = logging.getLogger(__name__)


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
            self._response_msg = await self._message.reply_text("🧠 Думаю...")
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

    async def finalize(self, response: OutgoingMessage) -> None:
        if not self._response_msg:
            return

        if response.is_long:
            try:
                await self._response_msg.delete()
            except Exception:
                pass
            self._response_msg = None
            return

        try:
            text = response.text or "Готово."
            await self._response_msg.edit_text(
                text[:4000], parse_mode="Markdown",
            )
        except Exception:
            try:
                await self._response_msg.edit_text(
                    response.text[:4000] if response.text else "Готово.",
                )
            except Exception:
                pass


# ── Telegram Transport ─────────────────────────────────────────

class TelegramTransport:
    """Multi-bot Telegram transport. One process, all capsules."""

    def __init__(self, capsules: dict[str, Capsule], engine: ClaudeEngine,
                 memory: MemoryStore, queue: RequestQueue):
        self._capsules = capsules
        self._engine = engine
        self._memory = memory
        self._queue = queue
        self._apps: list[Application] = []
        self._token_to_capsule: dict[str, Capsule] = {}

    def _build_app(self, capsule: Capsule) -> Application:
        """Build an Application for a single capsule."""
        token = capsule.config.bot_token
        self._token_to_capsule[token] = capsule

        app = Application.builder().token(token).build()
        app.bot_data["capsule"] = capsule
        app.bot_data["transport"] = self

        app.add_handler(CommandHandler("start", self._handle_start))
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

    async def start(self) -> None:
        for capsule in self._capsules.values():
            app = self._build_app(capsule)
            self._apps.append(app)

        for app in self._apps:
            await app.initialize()
            await app.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"],
            )
            await app.start()

        logger.info(f"Telegram transport started: {len(self._apps)} bot(s)")

    async def stop(self) -> None:
        for app in reversed(self._apps):
            try:
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
            except Exception as e:
                logger.error(f"Error stopping app: {e}")
        logger.info("Telegram transport stopped")

    # ── Handlers ────────────────────────────────────────────────

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        capsule: Capsule = context.bot_data["capsule"]
        msg = update.effective_message
        if not msg:
            return
        name = capsule.config.name
        await msg.reply_text(
            f"Привет! Я — {name}, ваш AI-ассистент. Напишите что-нибудь, и я помогу."
        )

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message
        if not msg or not msg.text:
            return

        capsule: Capsule = context.bot_data["capsule"]
        user_id = update.effective_user.id
        logger.info(f"Text from user_id={user_id}, name={update.effective_user.first_name}, text={msg.text[:50]!r}")

        if not capsule.is_employee(user_id):
            logger.warning(f"User {user_id} not authorized for capsule {capsule.config.id} (owner={capsule.config.owner_telegram_id})")
            return

        if capsule.is_trial_expired():
            await msg.reply_text("⏰ Пробный период завершён. Свяжитесь с администратором.")
            return

        cap_id = capsule.config.id
        max_per_day = capsule.config.rate_limit.get("max_per_day", 100)
        rl = await self._queue.check_rate_limit(cap_id, max_per_day)
        if rl == "blocked":
            await msg.reply_text("🚫 Лимит запросов на сегодня достигнут.")
            return

        text = msg.text.strip()
        if not text:
            return

        # Reply context
        reply_ctx = await self._get_reply_context(msg, context.bot)
        if reply_ctx:
            text = f"[Ответ на сообщение]: {reply_ctx}\n\n{text}"

        # BTW queue
        if await self._queue.is_processing(cap_id):
            count = await self._queue.add_btw(
                cap_id, QueuedMessage(text=text, timestamp=_time.time()))
            await msg.reply_text(f"📎 Принято (+{count}), добавлю к текущему запросу")
            return

        incoming = IncomingMessage(
            capsule_id=cap_id, user_id=user_id,
            user_name=update.effective_user.first_name or "",
            text=text, message_type=MessageType.TEXT,
        )
        await self._process_message(msg, capsule, incoming, warn_rate=(rl == "warn"))

    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message
        if not msg:
            return

        capsule: Capsule = context.bot_data["capsule"]
        user_id = update.effective_user.id

        if not capsule.is_employee(user_id):
            return

        cap_id = capsule.config.id
        max_per_day = capsule.config.rate_limit.get("max_per_day", 100)
        rl = await self._queue.check_rate_limit(cap_id, max_per_day)
        if rl == "blocked":
            await msg.reply_text("🚫 Лимит запросов достигнут.")
            return

        status_msg = await msg.reply_text("🎙 Расшифровываю голосовое...")

        voice_obj = msg.voice or msg.audio
        if not voice_obj:
            await status_msg.edit_text("❌ Не удалось получить аудио.")
            return

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                tmp_path = f.name
            file = await context.bot.get_file(voice_obj.file_id)
            await file.download_to_drive(tmp_path)

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

        preview = text[:100] + "..." if len(text) > 100 else text
        try:
            await status_msg.edit_text(f"✍️ Обрабатываю: _{preview}_", parse_mode="Markdown")
        except Exception:
            pass

        incoming = IncomingMessage(
            capsule_id=cap_id, user_id=user_id,
            user_name=update.effective_user.first_name or "",
            text=f"[Голосовое сообщение]: {text}",
            message_type=MessageType.VOICE,
        )
        await self._process_message(msg, capsule, incoming, status_msg=status_msg)

    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message
        if not msg:
            return

        capsule: Capsule = context.bot_data["capsule"]
        if not capsule.is_employee(update.effective_user.id):
            return

        photos = msg.photo
        if not photos:
            return

        largest = photos[-1]
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                tmp_path = f.name
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
        )
        await self._process_message(msg, capsule, incoming)

    async def _handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message
        if not msg or not msg.document:
            return

        capsule: Capsule = context.bot_data["capsule"]
        if not capsule.is_employee(update.effective_user.id):
            return

        doc = msg.document
        filename = doc.file_name or "document"

        tmp_path = None
        try:
            ext = os.path.splitext(filename)[1] or ".bin"
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                tmp_path = f.name
            file = await context.bot.get_file(doc.file_id)
            await file.download_to_drive(tmp_path)
        except Exception as e:
            logger.error(f"Document download error: {e}")
            await msg.reply_text("❌ Ошибка загрузки документа.")
            return

        caption = msg.caption or f"Обработай этот документ: {filename}"
        prompt = f"Пользователь отправил документ {filename}: {tmp_path}\n\nЗадача: {caption}"

        incoming = IncomingMessage(
            capsule_id=capsule.config.id,
            user_id=update.effective_user.id,
            user_name=update.effective_user.first_name or "",
            text=prompt, message_type=MessageType.DOCUMENT,
            file_path=tmp_path, file_name=filename,
        )
        await self._process_message(msg, capsule, incoming)

    async def _handle_error(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(f"Telegram error: {context.error}", exc_info=context.error)

    # ── Core Pipeline ───────────────────────────────────────────

    async def _process_message(self, msg, capsule: Capsule,
                               incoming: IncomingMessage,
                               status_msg=None, warn_rate: bool = False) -> None:
        """Core pipeline: context → stream → parse → send → diary → BTW flush."""
        cap_id = capsule.config.id
        await self._queue.set_processing(cap_id, True)

        accumulated_text = ""
        tools_used: list[str] = []

        try:
            # 1. Build context
            parts = await self._memory.build_context_parts(capsule, incoming.text)
            builder = ContextBuilder(capsule)
            full_prompt = builder.build(incoming.text, parts, is_first_message=True)
            logger.info(f"[{cap_id}] Context built, prompt length={len(full_prompt)}")

            # 2. Stream response
            engine_cfg = capsule.get_engine_config()
            responder = StreamingResponder(msg, existing_msg=status_msg)
            await responder.start()

            chunk_count = 0
            async for chunk in self._engine.stream(full_prompt, engine_cfg):
                chunk_count += 1
                if chunk.type == "text":
                    accumulated_text += chunk.text
                    await responder.on_text(accumulated_text)
                elif chunk.type == "tool_start":
                    tools_used.append(chunk.tool)
                    await responder.on_tool(chunk.text)
                elif chunk.type == "result":
                    accumulated_text = chunk.text or accumulated_text
                elif chunk.type == "error":
                    logger.error(f"[{cap_id}] Engine error chunk: {chunk.text}")

            logger.info(f"[{cap_id}] Stream done: {chunk_count} chunks, {len(accumulated_text)} chars")

            # 3. Parse response
            response = ResponseParser.parse(accumulated_text)

            # 4. Save learnings/corrections
            for learn in response.learnings:
                await self._memory.add_learning(cap_id, learn)
            for corr in response.corrections:
                await self._memory.add_correction(cap_id, corr)

            # 5. Rate warning
            if warn_rate:
                response.text += "\n\n⚠️ Приближаетесь к лимиту запросов на сегодня."

            # 6. Finalize streaming message
            await responder.finalize(response)

            # 7. Send response (only if finalize deleted the message — long/files)
            if not responder._response_msg or response.files:
                await self._send_response(msg, response)

            # 8. Diary
            await self._save_diary(capsule, incoming, accumulated_text, tools_used)

            # 9. Rate counter
            await self._queue.increment_rate(cap_id)

        except Exception as e:
            logger.error(f"Processing error for {cap_id}: {e}", exc_info=True)
            try:
                await msg.reply_text("Техническая ошибка. Попробуйте ещё раз.")
            except Exception:
                pass
        finally:
            await self._queue.set_processing(cap_id, False)
            # Cleanup temp file
            if incoming.file_path:
                try:
                    os.unlink(incoming.file_path)
                except Exception:
                    pass

        # 9. BTW follow-up
        btw_messages = await self._queue.flush_btw(cap_id)
        if btw_messages:
            combined = "\n\n".join(m.text for m in btw_messages)
            follow_up = IncomingMessage(
                capsule_id=cap_id, user_id=incoming.user_id,
                user_name=incoming.user_name, text=combined,
            )
            await self._process_message(msg, capsule, follow_up)

    async def _send_response(self, msg, response: OutgoingMessage) -> None:
        """Send files + text with Telegraph/Markdown fallback."""
        thread_id = getattr(msg, "message_thread_id", None)

        # 1. Send files
        for f in response.files:
            if not os.path.exists(f.path):
                continue
            try:
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

        if not response.text:
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

        # Voice reply — transcribe
        voice_obj = getattr(reply, "voice", None) or getattr(reply, "audio", None)
        if voice_obj and bot:
            try:
                with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                    tmp_path = f.name
                file = await bot.get_file(voice_obj.file_id)
                await file.download_to_drive(tmp_path)
                text = await transcribe_voice(tmp_path)
                os.unlink(tmp_path)
                if text and not text.startswith("❌"):
                    return f"[Голосовое сообщение]: {text.strip()}"
            except Exception as e:
                logger.warning(f"Reply voice transcription error: {e}")
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
            user_message=incoming.text[:500],
            bot_response=response_text[:500],
            model=capsule.config.model,
            tools_used=tools_used,
            source=incoming.source,
        )
        try:
            await self._memory.add_diary(entry)
        except Exception as e:
            logger.error(f"Diary save error: {e}")
