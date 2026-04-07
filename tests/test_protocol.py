"""Tests for transport/protocol.py — unified message types + response parsing.

Written BEFORE implementation (TDD Red Phase).
All tests must FAIL until Gate 3 implementation.
"""
import json
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path


# === Data Classes ===

class TestMessageType:
    def test_enum_values(self):
        from neura.transport.protocol import MessageType
        assert MessageType.TEXT.value == "text"
        assert MessageType.VOICE.value == "voice"
        assert MessageType.PHOTO.value == "photo"
        assert MessageType.DOCUMENT.value == "document"
        assert MessageType.COMMAND.value == "command"


class TestIncomingMessage:
    def test_defaults(self):
        from neura.transport.protocol import IncomingMessage, MessageType
        msg = IncomingMessage(capsule_id="test", user_id=123, user_name="Test", text="hello")
        assert msg.capsule_id == "test"
        assert msg.user_id == 123
        assert msg.text == "hello"
        assert msg.message_type == MessageType.TEXT
        assert msg.file_path is None
        assert msg.reply_context == ""
        assert msg.source == "telegram"

    def test_voice_type(self):
        from neura.transport.protocol import IncomingMessage, MessageType
        msg = IncomingMessage(
            capsule_id="t", user_id=1, user_name="U",
            text="[voice]", message_type=MessageType.VOICE,
            file_path="/tmp/voice.ogg",
        )
        assert msg.message_type == MessageType.VOICE
        assert msg.file_path == "/tmp/voice.ogg"


class TestMessageFile:
    def test_defaults(self):
        from neura.transport.protocol import MessageFile
        f = MessageFile(path="/tmp/report.pdf", filename="report.pdf")
        assert f.path == "/tmp/report.pdf"
        assert f.is_photo is False
        assert f.caption == ""

    def test_photo_flag(self):
        from neura.transport.protocol import MessageFile
        f = MessageFile(path="/tmp/img.jpg", filename="img.jpg", is_photo=True, caption="Photo")
        assert f.is_photo is True
        assert f.caption == "Photo"


class TestOutgoingMessage:
    def test_defaults(self):
        from neura.transport.protocol import OutgoingMessage
        msg = OutgoingMessage(text="Hello")
        assert msg.text == "Hello"
        assert msg.files == []
        assert msg.learnings == []
        assert msg.corrections == []
        assert msg.telegraph_url is None
        assert msg.is_long is False


# === ResponseParser ===

class TestResponseParserMarkers:
    def test_clean_text_no_markers(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("Simple answer")
        assert result.text == "Simple answer"
        assert result.learnings == []
        assert result.corrections == []

    def test_learn_marker_extracted(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("Answer [LEARN:User prefers short answers]")
        assert "LEARN" not in result.text
        assert "User prefers short answers" in result.learnings

    def test_correction_marker_extracted(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("Answer [CORRECTION:Don't use formal tone]")
        assert "CORRECTION" not in result.text
        assert "Don't use formal tone" in result.corrections

    def test_multiple_markers(self):
        from neura.transport.protocol import ResponseParser
        text = "OK [LEARN:fact1] some text [CORRECTION:fix1] [LEARN:fact2]"
        result = ResponseParser.parse(text)
        assert len(result.learnings) == 2
        assert len(result.corrections) == 1
        assert "fact1" in result.learnings
        assert "fact2" in result.learnings
        assert "fix1" in result.corrections

    def test_markers_cleaned_from_text(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("Hello [LEARN:x] world [CORRECTION:y]")
        assert "[LEARN" not in result.text
        assert "[CORRECTION" not in result.text
        assert "Hello" in result.text
        assert "world" in result.text


class TestResponseParserFiles:
    def test_file_marker_extracted(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("Here: [FILE:/tmp/report.pdf]")
        assert len(result.files) == 1
        assert result.files[0].path == "/tmp/report.pdf"
        assert result.files[0].filename == "report.pdf"
        assert "[FILE:" not in result.text

    def test_photo_detected(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("[FILE:/tmp/photo.jpg]")
        assert result.files[0].is_photo is True

    def test_document_not_photo(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("[FILE:/tmp/doc.pdf]")
        assert result.files[0].is_photo is False

    def test_path_traversal_blocked(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("[FILE:/etc/passwd]")
        assert len(result.files) == 0

    def test_path_traversal_dotdot_blocked(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("[FILE:/tmp/../etc/passwd]")
        assert len(result.files) == 0

    def test_allowed_prefix_tmp(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("[FILE:/tmp/safe.txt]")
        assert len(result.files) == 1

    def test_multiple_files(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("[FILE:/tmp/a.pdf] text [FILE:/tmp/b.jpg]")
        assert len(result.files) == 2

    def test_homes_dir_allowed_by_default(self):
        """Files in /opt/neura-v2/homes/ should be allowed (DEFAULT_ALLOWED_PREFIXES)."""
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("[FILE:/opt/neura-v2/homes/dmitry_test/report.pdf]")
        assert len(result.files) == 1
        assert result.files[0].filename == "report.pdf"

    def test_homes_dir_allowed_via_explicit_prefix(self):
        """Files in capsule home_dir should be allowed when passed explicitly."""
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse(
            "[FILE:/opt/neura-v2/homes/test_capsule/doc.docx]",
            allowed_prefixes=["/tmp/", "/opt/neura-v2/homes/test_capsule/"],
        )
        assert len(result.files) == 1

    def test_xlsx_caption(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("[FILE:/tmp/data.xlsx]")
        assert len(result.files) == 1
        assert result.files[0].filename == "data.xlsx"


class TestResponseParserLongText:
    def test_short_text_not_long(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("Short")
        assert result.is_long is False

    def test_long_text_flagged(self):
        from neura.transport.protocol import ResponseParser
        long_text = "x" * 4500
        result = ResponseParser.parse(long_text)
        assert result.is_long is True

    def test_empty_text(self):
        from neura.transport.protocol import ResponseParser
        result = ResponseParser.parse("")
        assert result.text == ""
        assert result.is_long is False


class TestResponseParserCombined:
    def test_all_features(self):
        from neura.transport.protocol import ResponseParser
        text = "Answer [LEARN:fact] [FILE:/tmp/out.pdf] [CORRECTION:fix]"
        result = ResponseParser.parse(text)
        assert "Answer" in result.text
        assert len(result.learnings) == 1
        assert len(result.corrections) == 1
        assert len(result.files) == 1
        assert "[LEARN" not in result.text
        assert "[FILE" not in result.text


class TestHumanizeFilename:
    def test_snake_case(self):
        from neura.transport.protocol import ResponseParser
        assert ResponseParser._humanize_filename("annual_report_2026.pdf") == "Annual report 2026"

    def test_dashes(self):
        from neura.transport.protocol import ResponseParser
        assert ResponseParser._humanize_filename("my-document.docx") == "My document"

    def test_simple(self):
        from neura.transport.protocol import ResponseParser
        assert ResponseParser._humanize_filename("report.pdf") == "Report"


# === Telegraph ===

class TestMdToTelegraphNodes:
    def test_header_h3(self):
        from neura.transport.protocol import _md_to_telegraph_nodes
        nodes = _md_to_telegraph_nodes("## Title")
        assert any(n.get("tag") == "h3" for n in nodes)

    def test_header_h4(self):
        from neura.transport.protocol import _md_to_telegraph_nodes
        nodes = _md_to_telegraph_nodes("### Subtitle")
        assert any(n.get("tag") == "h4" for n in nodes)

    def test_list_items(self):
        from neura.transport.protocol import _md_to_telegraph_nodes
        nodes = _md_to_telegraph_nodes("- Item one\n- Item two")
        li_nodes = [n for n in nodes if n.get("tag") == "li"]
        assert len(li_nodes) == 2

    def test_blockquote(self):
        from neura.transport.protocol import _md_to_telegraph_nodes
        nodes = _md_to_telegraph_nodes("> Quote text")
        assert any(n.get("tag") == "blockquote" for n in nodes)

    def test_inline_bold(self):
        from neura.transport.protocol import _md_to_telegraph_nodes
        nodes = _md_to_telegraph_nodes("Text **bold** here")
        # Should contain a <p> with <b> child
        p_nodes = [n for n in nodes if n.get("tag") == "p"]
        assert len(p_nodes) >= 1
        children = p_nodes[0].get("children", [])
        has_bold = any(
            isinstance(c, dict) and c.get("tag") == "b" for c in children
        )
        assert has_bold

    def test_empty_text(self):
        from neura.transport.protocol import _md_to_telegraph_nodes
        nodes = _md_to_telegraph_nodes("")
        assert isinstance(nodes, list)
        assert len(nodes) >= 1  # Should have at least a default node

    def test_code_fences_skipped(self):
        from neura.transport.protocol import _md_to_telegraph_nodes
        nodes = _md_to_telegraph_nodes("```\ncode\n```")
        # ``` lines should not produce their own nodes
        assert not any("```" in str(n.get("children", "")) for n in nodes)


class TestCreateTelegraphPage:
    @patch("neura.transport.protocol._get_telegraph_token", return_value="test_token")
    @patch("neura.transport.protocol.urllib.request.urlopen")
    def test_success(self, mock_urlopen, mock_token):
        from neura.transport.protocol import create_telegraph_page
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({
            "ok": True,
            "result": {"url": "https://telegra.ph/test-page"}
        }).encode()
        mock_urlopen.return_value = mock_resp

        url = create_telegraph_page("Test", "Content")
        assert url == "https://telegra.ph/test-page"

    @patch("neura.transport.protocol._get_telegraph_token", return_value=None)
    def test_no_token_returns_none(self, mock_token):
        from neura.transport.protocol import create_telegraph_page
        assert create_telegraph_page("Test", "Content") is None


# === Voice Transcription ===

class TestTranscribeVoice:
    @pytest.mark.asyncio
    @patch("neura.transport.protocol._transcribe_deepgram", new_callable=AsyncMock)
    async def test_deepgram_success(self, mock_dg):
        from neura.transport.protocol import transcribe_voice
        mock_dg.return_value = "Hello world"
        with patch.dict(os.environ, {"DEEPGRAM_API_KEY": "test_key"}):
            result = await transcribe_voice("/tmp/test.ogg")
        assert result == "Hello world"

    @pytest.mark.asyncio
    @patch("neura.transport.protocol._transcribe_whisper", new_callable=AsyncMock)
    @patch("neura.transport.protocol._transcribe_deepgram", new_callable=AsyncMock)
    async def test_deepgram_fails_whisper_fallback(self, mock_dg, mock_whisper):
        from neura.transport.protocol import transcribe_voice
        mock_dg.return_value = "❌ Deepgram error"
        mock_whisper.return_value = "Fallback text"
        with patch.dict(os.environ, {"DEEPGRAM_API_KEY": "test_key"}):
            result = await transcribe_voice("/tmp/test.ogg")
        assert result == "Fallback text"

    @pytest.mark.asyncio
    @patch("neura.transport.protocol._transcribe_whisper", new_callable=AsyncMock)
    async def test_no_deepgram_key_uses_whisper(self, mock_whisper):
        from neura.transport.protocol import transcribe_voice
        mock_whisper.return_value = "Whisper text"
        with patch.dict(os.environ, {}, clear=False):
            env = os.environ.copy()
            env.pop("DEEPGRAM_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                result = await transcribe_voice("/tmp/test.ogg")
        assert result == "Whisper text"
