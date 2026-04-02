"""Tests for transport/telegram.py — multi-bot Telegram adapter.

Written BEFORE implementation (TDD Red Phase).
All tests must FAIL until Gate 3 implementation.
"""
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from dataclasses import dataclass


# ── Helpers: mock TG objects ───────────────────────────────────

def _make_capsule(capsule_id="test_cap", bot_token="123:ABC",
                  owner_tg_id=111, trial_expired=False,
                  rate_max=100):
    """Create a mock Capsule with config."""
    cap = MagicMock()
    cap.config = MagicMock()
    cap.config.id = capsule_id
    cap.config.name = "Test Capsule"
    cap.config.bot_token = bot_token
    cap.config.owner_telegram_id = owner_tg_id
    cap.config.rate_limit = {"max_per_day": rate_max, "warn_at": 50}
    cap.config.home_dir = f"/tmp/test-homes/{capsule_id}"
    cap.config.model = "sonnet"
    cap.config.features = {"streaming": True, "voice": True}
    cap.config.trial = {"enabled": trial_expired, "days": 5}
    cap.is_employee = MagicMock(return_value=True)
    cap.is_trial_expired = MagicMock(return_value=trial_expired)
    cap.get_engine_config = MagicMock()
    cap.get_system_prompt = MagicMock(return_value="System prompt")
    return cap


def _make_update(user_id=111, text="Hello", is_bot=False,
                 message_thread_id=None, voice=None, photo=None,
                 document=None, caption=None):
    """Create a mock TG Update."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.first_name = "Test"
    update.effective_user.is_bot = is_bot

    msg = AsyncMock()
    msg.text = text
    msg.caption = caption
    msg.voice = voice
    msg.audio = None
    msg.photo = photo
    msg.document = document
    msg.message_thread_id = message_thread_id
    msg.reply_to_message = None
    msg.reply_text = AsyncMock(return_value=MagicMock())
    update.effective_message = msg
    return update


def _make_context(capsule=None, bot_token="123:ABC"):
    """Create a mock TG context with capsule in bot_data."""
    ctx = MagicMock()
    ctx.bot = AsyncMock()
    ctx.bot.token = bot_token
    ctx.bot_data = {}
    if capsule:
        ctx.bot_data["capsule"] = capsule
    return ctx


# ── TelegramTransport ─────────────────────────────────────────

class TestTelegramTransportInit:
    def test_init_stores_dependencies(self):
        from neura.transport.telegram import TelegramTransport
        capsules = {"test": _make_capsule()}
        engine = MagicMock()
        memory = MagicMock()
        queue = MagicMock()
        transport = TelegramTransport(capsules, engine, memory, queue)
        assert transport._capsules == capsules
        assert transport._engine is engine
        assert transport._memory is memory
        assert transport._queue is queue

    def test_token_to_capsule_mapping(self):
        from neura.transport.telegram import TelegramTransport
        cap1 = _make_capsule("cap1", "token1")
        cap2 = _make_capsule("cap2", "token2")
        transport = TelegramTransport(
            {"cap1": cap1, "cap2": cap2},
            MagicMock(), MagicMock(), MagicMock(),
        )
        # Mapping built during _build_app
        app1 = transport._build_app(cap1)
        app2 = transport._build_app(cap2)
        assert transport._token_to_capsule["token1"] is cap1
        assert transport._token_to_capsule["token2"] is cap2


# ── Handle Text ────────────────────────────────────────────────

class TestHandleText:
    @pytest.mark.asyncio
    async def test_unauthorized_user_ignored(self):
        from neura.transport.telegram import TelegramTransport
        cap = _make_capsule()
        cap.is_employee.return_value = False
        transport = TelegramTransport({"t": cap}, MagicMock(), MagicMock(), AsyncMock())

        update = _make_update(user_id=999, text="Hello")
        ctx = _make_context(capsule=cap)

        await transport._handle_text(update, ctx)
        # No reply should be sent
        update.effective_message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_trial_expired_blocked(self):
        from neura.transport.telegram import TelegramTransport
        cap = _make_capsule(trial_expired=True)
        transport = TelegramTransport({"t": cap}, MagicMock(), MagicMock(), AsyncMock())

        update = _make_update(text="Hello")
        ctx = _make_context(capsule=cap)

        await transport._handle_text(update, ctx)
        update.effective_message.reply_text.assert_called_once()
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "пробный" in call_text.lower() or "триал" in call_text.lower() or "период" in call_text.lower()

    @pytest.mark.asyncio
    async def test_rate_limited_blocked(self):
        from neura.transport.telegram import TelegramTransport
        queue = AsyncMock()
        queue.check_rate_limit = AsyncMock(return_value="blocked")
        cap = _make_capsule()
        transport = TelegramTransport({"t": cap}, MagicMock(), MagicMock(), queue)

        update = _make_update(text="Hello")
        ctx = _make_context(capsule=cap)

        await transport._handle_text(update, ctx)
        update.effective_message.reply_text.assert_called_once()
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "лимит" in call_text.lower()

    @pytest.mark.asyncio
    async def test_btw_queue_when_processing(self):
        from neura.transport.telegram import TelegramTransport
        queue = AsyncMock()
        queue.check_rate_limit = AsyncMock(return_value=None)
        queue.is_processing = AsyncMock(return_value=True)
        queue.add_btw = AsyncMock(return_value=2)
        cap = _make_capsule()
        transport = TelegramTransport({"t": cap}, MagicMock(), MagicMock(), queue)

        update = _make_update(text="BTW message")
        ctx = _make_context(capsule=cap)

        await transport._handle_text(update, ctx)
        queue.add_btw.assert_called_once()
        update.effective_message.reply_text.assert_called_once()
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "принято" in call_text.lower() or "📎" in call_text

    @pytest.mark.asyncio
    async def test_empty_text_ignored(self):
        from neura.transport.telegram import TelegramTransport
        cap = _make_capsule()
        queue = AsyncMock()
        queue.check_rate_limit = AsyncMock(return_value=None)
        queue.is_processing = AsyncMock(return_value=False)
        transport = TelegramTransport({"t": cap}, MagicMock(), MagicMock(), queue)

        update = _make_update(text="   ")
        ctx = _make_context(capsule=cap)

        await transport._handle_text(update, ctx)
        # _process_message should NOT be called for empty text


# ── Handle Voice ───────────────────────────────────────────────

class TestHandleVoice:
    @pytest.mark.asyncio
    @patch("neura.transport.telegram.transcribe_voice", new_callable=AsyncMock)
    async def test_voice_download_and_transcribe(self, mock_transcribe):
        from neura.transport.telegram import TelegramTransport
        mock_transcribe.return_value = "Transcribed text"

        cap = _make_capsule()
        queue = AsyncMock()
        queue.check_rate_limit = AsyncMock(return_value=None)
        queue.is_processing = AsyncMock(return_value=False)
        queue.set_processing = AsyncMock()
        queue.flush_btw = AsyncMock(return_value=[])
        queue.increment_rate = AsyncMock()

        memory = AsyncMock()
        memory.build_context_parts = AsyncMock()
        memory.add_diary = AsyncMock()

        engine = MagicMock()
        # Mock stream to return empty async iterator
        async def empty_stream(*a, **kw):
            if False:
                yield  # pragma: no cover
        engine.stream = MagicMock(return_value=empty_stream())

        transport = TelegramTransport({"t": cap}, engine, memory, queue)

        voice_obj = MagicMock()
        voice_obj.file_id = "voice_123"
        update = _make_update(text=None, voice=voice_obj)
        ctx = _make_context(capsule=cap)

        mock_file = AsyncMock()
        mock_file.download_to_drive = AsyncMock()
        ctx.bot.get_file = AsyncMock(return_value=mock_file)

        await transport._handle_voice(update, ctx)
        mock_transcribe.assert_called_once()

    @pytest.mark.asyncio
    @patch("neura.transport.telegram.transcribe_voice", new_callable=AsyncMock)
    async def test_voice_transcription_error(self, mock_transcribe):
        from neura.transport.telegram import TelegramTransport
        mock_transcribe.return_value = "❌ Transcription failed"

        cap = _make_capsule()
        queue = AsyncMock()
        queue.is_processing = AsyncMock(return_value=False)
        queue.check_rate_limit = AsyncMock(return_value=None)
        transport = TelegramTransport({"t": cap}, MagicMock(), MagicMock(), queue)

        voice_obj = MagicMock()
        voice_obj.file_id = "voice_err"
        update = _make_update(text=None, voice=voice_obj)
        # status_msg needs async edit_text
        status_msg = AsyncMock()
        update.effective_message.reply_text = AsyncMock(return_value=status_msg)
        ctx = _make_context(capsule=cap)

        mock_file = AsyncMock()
        mock_file.download_to_drive = AsyncMock()
        ctx.bot.get_file = AsyncMock(return_value=mock_file)

        await transport._handle_voice(update, ctx)
        # Should show error to user via edit_text
        status_msg.edit_text.assert_called()


# ── StreamingResponder ────────────────────────��────────────────

class TestStreamingResponder:
    @pytest.mark.asyncio
    async def test_start_sends_thinking(self):
        from neura.transport.telegram import StreamingResponder
        msg = AsyncMock()
        msg.reply_text = AsyncMock(return_value=MagicMock())
        responder = StreamingResponder(msg)
        await responder.start()
        msg.reply_text.assert_called_once()
        call_text = msg.reply_text.call_args[0][0]
        assert "думаю" in call_text.lower() or "🧠" in call_text

    @pytest.mark.asyncio
    async def test_on_text_throttled(self):
        from neura.transport.telegram import StreamingResponder
        msg = AsyncMock()
        resp_msg = AsyncMock()
        resp_msg.edit_text = AsyncMock()
        responder = StreamingResponder(msg, existing_msg=resp_msg)
        # First call should edit
        responder._last_edit_time = 0  # Force allow edit
        await responder.on_text("Hello world")

        # Second call immediately should be throttled (no edit)
        resp_msg.edit_text.reset_mock()
        await responder.on_text("Hello world updated")
        # Should NOT edit because not enough time passed

    @pytest.mark.asyncio
    async def test_on_text_exceeds_max_length(self):
        from neura.transport.telegram import StreamingResponder
        msg = AsyncMock()
        resp_msg = AsyncMock()
        resp_msg.edit_text = AsyncMock()
        responder = StreamingResponder(msg, existing_msg=resp_msg)
        responder._last_edit_time = 0

        long_text = "x" * 4000
        await responder.on_text(long_text)
        # Should stop editing inline after exceeding limit

    @pytest.mark.asyncio
    async def test_on_tool_shows_label(self):
        from neura.transport.telegram import StreamingResponder
        msg = AsyncMock()
        resp_msg = AsyncMock()
        resp_msg.edit_text = AsyncMock()
        responder = StreamingResponder(msg, existing_msg=resp_msg)
        responder._last_edit_time = 0

        await responder.on_tool("📖 Читаю")
        # Tool label should be stored
        assert responder._tool_label is not None

    @pytest.mark.asyncio
    async def test_finalize_deletes_for_long_response(self):
        from neura.transport.telegram import StreamingResponder
        from neura.transport.protocol import OutgoingMessage
        msg = AsyncMock()
        resp_msg = AsyncMock()
        resp_msg.delete = AsyncMock()
        resp_msg.edit_text = AsyncMock()
        responder = StreamingResponder(msg, existing_msg=resp_msg)

        response = OutgoingMessage(text="x" * 5000, is_long=True)
        await responder.finalize(response)
        # Should delete the streaming message for re-send
        resp_msg.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_finalize_edits_short_response(self):
        from neura.transport.telegram import StreamingResponder
        from neura.transport.protocol import OutgoingMessage
        msg = AsyncMock()
        resp_msg = AsyncMock()
        resp_msg.edit_text = AsyncMock()
        responder = StreamingResponder(msg, existing_msg=resp_msg)

        response = OutgoingMessage(text="Short answer")
        await responder.finalize(response)
        resp_msg.edit_text.assert_called()


# ── Process Message Pipeline ──────────────────────────────────

class TestProcessMessage:
    @pytest.mark.asyncio
    async def test_processing_lock_released_on_error(self):
        """Processing lock must be released even if engine raises."""
        from neura.transport.telegram import TelegramTransport
        cap = _make_capsule()
        queue = AsyncMock()
        queue.set_processing = AsyncMock()
        queue.flush_btw = AsyncMock(return_value=[])
        queue.increment_rate = AsyncMock()

        memory = AsyncMock()
        memory.build_context_parts = AsyncMock(side_effect=Exception("DB error"))

        engine = MagicMock()
        transport = TelegramTransport({"t": cap}, engine, memory, queue)

        from neura.transport.protocol import IncomingMessage
        incoming = IncomingMessage(capsule_id="test_cap", user_id=111,
                                  user_name="Test", text="Hello")
        msg = AsyncMock()
        msg.reply_text = AsyncMock(return_value=MagicMock())

        # Should not raise — error handled internally
        await transport._process_message(msg, cap, incoming)

        # Lock must be released
        calls = queue.set_processing.call_args_list
        assert any(c.args == ("test_cap", False) or c.kwargs.get("active") is False
                   for c in calls)

    @pytest.mark.asyncio
    async def test_diary_saved_after_success(self):
        from neura.transport.telegram import TelegramTransport
        from neura.transport.protocol import IncomingMessage
        from neura.core.context import ContextParts

        cap = _make_capsule()
        queue = AsyncMock()
        queue.set_processing = AsyncMock()
        queue.flush_btw = AsyncMock(return_value=[])
        queue.increment_rate = AsyncMock()

        memory = AsyncMock()
        memory.build_context_parts = AsyncMock(return_value=ContextParts())
        memory.add_diary = AsyncMock(return_value=1)
        memory.add_learning = AsyncMock()
        memory.add_correction = AsyncMock()

        # Mock engine stream
        from neura.core.engine import Chunk
        async def mock_stream(*a, **kw):
            yield Chunk(type="result", text="Response text", session_id="s1")
        engine = MagicMock()
        engine.stream = MagicMock(return_value=mock_stream())

        transport = TelegramTransport({"t": cap}, engine, memory, queue)

        incoming = IncomingMessage(capsule_id="test_cap", user_id=111,
                                  user_name="Test", text="Hello")
        msg = AsyncMock()
        msg.reply_text = AsyncMock(return_value=AsyncMock())

        await transport._process_message(msg, cap, incoming)
        memory.add_diary.assert_called_once()


# ── Send Response ──────────────────────────────────────────────

class TestSendResponse:
    @pytest.mark.asyncio
    async def test_send_short_text_markdown(self):
        from neura.transport.telegram import TelegramTransport
        from neura.transport.protocol import OutgoingMessage
        transport = TelegramTransport({}, MagicMock(), MagicMock(), MagicMock())

        msg = AsyncMock()
        msg.reply_text = AsyncMock()
        msg.message_thread_id = None

        response = OutgoingMessage(text="Short answer")
        await transport._send_response(msg, response)
        msg.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_send_long_text_telegraph(self):
        from neura.transport.telegram import TelegramTransport
        from neura.transport.protocol import OutgoingMessage
        transport = TelegramTransport({}, MagicMock(), MagicMock(), MagicMock())

        msg = AsyncMock()
        msg.reply_text = AsyncMock()
        msg.message_thread_id = None

        response = OutgoingMessage(
            text="x" * 5000, is_long=True,
            telegraph_url="https://telegra.ph/test",
        )
        await transport._send_response(msg, response)
        msg.reply_text.assert_called()
        call_text = msg.reply_text.call_args[0][0]
        assert "telegra.ph" in call_text

    @pytest.mark.asyncio
    async def test_send_files_photo(self):
        from neura.transport.telegram import TelegramTransport
        from neura.transport.protocol import OutgoingMessage, MessageFile
        transport = TelegramTransport({}, MagicMock(), MagicMock(), MagicMock())

        msg = AsyncMock()
        msg.reply_photo = AsyncMock()
        msg.reply_text = AsyncMock()
        msg.message_thread_id = None

        f = MessageFile(path="/tmp/test.jpg", filename="test.jpg",
                       is_photo=True, caption="Photo")
        response = OutgoingMessage(text="Here:", files=[f])

        with patch("builtins.open", MagicMock()):
            with patch("os.path.exists", return_value=True):
                await transport._send_response(msg, response)
        msg.reply_photo.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_files_document(self):
        from neura.transport.telegram import TelegramTransport
        from neura.transport.protocol import OutgoingMessage, MessageFile
        transport = TelegramTransport({}, MagicMock(), MagicMock(), MagicMock())

        msg = AsyncMock()
        msg.reply_document = AsyncMock()
        msg.reply_text = AsyncMock()
        msg.message_thread_id = None

        f = MessageFile(path="/tmp/report.pdf", filename="report.pdf",
                       is_photo=False, caption="Report")
        response = OutgoingMessage(text="Here:", files=[f])

        with patch("builtins.open", MagicMock()):
            with patch("os.path.exists", return_value=True):
                await transport._send_response(msg, response)
        msg.reply_document.assert_called_once()


# ── Reply Context ──────────────────────────────────────────────

class TestReplyContext:
    @pytest.mark.asyncio
    async def test_no_reply(self):
        from neura.transport.telegram import TelegramTransport
        transport = TelegramTransport({}, MagicMock(), MagicMock(), MagicMock())
        msg = MagicMock()
        msg.reply_to_message = None
        result = await transport._get_reply_context(msg, bot=None)
        assert result == ""

    @pytest.mark.asyncio
    async def test_reply_to_text(self):
        from neura.transport.telegram import TelegramTransport
        transport = TelegramTransport({}, MagicMock(), MagicMock(), MagicMock())
        msg = MagicMock()
        reply = MagicMock()
        reply.text = "Original message"
        reply.caption = None
        reply.voice = None
        reply.audio = None
        reply.from_user = MagicMock()
        reply.from_user.is_bot = False
        msg.reply_to_message = reply
        result = await transport._get_reply_context(msg, bot=None)
        assert "Original message" in result

    @pytest.mark.asyncio
    async def test_reply_to_status_ignored(self):
        from neura.transport.telegram import TelegramTransport
        transport = TelegramTransport({}, MagicMock(), MagicMock(), MagicMock())
        msg = MagicMock()
        reply = MagicMock()
        reply.text = "🧠 Думаю..."
        reply.caption = None
        reply.voice = None
        reply.audio = None
        reply.from_user = MagicMock()
        reply.from_user.is_bot = True
        msg.reply_to_message = reply
        result = await transport._get_reply_context(msg, bot=None)
        assert result == ""

    @pytest.mark.asyncio
    async def test_reply_to_bot_message(self):
        from neura.transport.telegram import TelegramTransport
        transport = TelegramTransport({}, MagicMock(), MagicMock(), MagicMock())
        msg = MagicMock()
        reply = MagicMock()
        reply.text = "This is my previous long answer about topic..."
        reply.caption = None
        reply.voice = None
        reply.audio = None
        reply.from_user = MagicMock()
        reply.from_user.is_bot = True
        msg.reply_to_message = reply
        result = await transport._get_reply_context(msg, bot=None)
        assert "твоё сообщение" in result.lower() or "ответ на" in result.lower()
