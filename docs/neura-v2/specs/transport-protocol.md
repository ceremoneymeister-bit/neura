# Spec: transport/protocol.py

## Назначение
Transport-agnostic типы сообщений и парсинг ответов Claude. Используется всеми транспортами (Telegram, Web, Mobile).

## Интерфейс

### Типы
- `MessageType(Enum)`: TEXT, VOICE, PHOTO, DOCUMENT, COMMAND
- `IncomingMessage`: capsule_id, user_id, user_name, text, message_type, file_path, reply_context, source
- `MessageFile`: path, filename, is_photo, caption
- `OutgoingMessage`: text, files, learnings, corrections, telegraph_url, is_long

### ResponseParser (static methods)
- `parse(engine_text, allowed_prefixes=["/tmp/"]) -> OutgoingMessage`
- `_parse_markers(text) -> tuple[str, list[str], list[str]]`
- `_extract_files(text, allowed_prefixes) -> tuple[str, list[MessageFile]]`
- `_humanize_filename(filename) -> str`

### Telegraph
- `create_telegraph_page(title, content) -> str | None`
- `_get_telegraph_token() -> str | None`
- `_md_to_telegraph_nodes(md_text) -> list`

### Voice
- `transcribe_voice(file_path) -> str` (async)
- `_transcribe_deepgram(file_path) -> str` (async)
- `_transcribe_whisper(file_path) -> str` (async)

## Зависимости
- os, re, json, asyncio, urllib.request (stdlib)
- DEEPGRAM_API_KEY из os.environ (optional)
- faster-whisper (optional fallback)

## Edge Cases
- Empty text → OutgoingMessage(text="", is_long=False)
- Path traversal: /etc/passwd → blocked
- No DEEPGRAM_API_KEY → straight to Whisper
- Both fail → error string starting with "❌"
- >4000 chars → is_long=True, telegraph_url populated

## Тест-кейсы
See test_protocol.py
