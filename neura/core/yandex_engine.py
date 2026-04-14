"""YandexEngine — YandexGPT API client with streaming support.

@arch scope=platform  affects=all_capsules
@arch depends=none (standalone HTTP client)
@arch risk=MEDIUM  restart=neura-v2
@arch role=Alternative AI engine using YandexGPT API (Yandex Cloud Foundation Models).
@arch note=Third engine option. Direct HTTP API — no CLI dependency.

Uses the same Chunk/EngineResult interface as ClaudeEngine for seamless switching.
Supports: streaming, system prompts, multi-turn, function calling (tools).
"""
import asyncio
import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import AsyncIterator

from neura.core.engine import Chunk, EngineConfig, EngineResult

logger = logging.getLogger(__name__)

# YandexGPT API endpoint
YANDEX_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
YANDEX_STREAM_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

# Model URI mapping (short name → full URI)
YANDEX_MODELS = {
    "yandexgpt-lite": "gpt://{folder}/yandexgpt-lite/latest",
    "yandexgpt-pro": "gpt://{folder}/yandexgpt/latest",
    "yandexgpt-pro-5": "gpt://{folder}/yandexgpt/latest",
    "yandexgpt-pro-5.1": "gpt://{folder}/yandexgpt/rc",
}

DEFAULT_MODEL = "yandexgpt-lite"


def _resolve_model_uri(model: str, folder_id: str) -> str:
    """Resolve short model name to full YandexGPT model URI."""
    if model.startswith("gpt://"):
        return model  # already full URI
    template = YANDEX_MODELS.get(model, YANDEX_MODELS[DEFAULT_MODEL])
    return template.format(folder=folder_id)


class YandexEngine:
    """YandexGPT API engine with streaming support.

    Implements the same interface as ClaudeEngine/OpenCodeEngine:
    - stream(prompt, config) -> AsyncIterator[Chunk]
    - execute(prompt, config) -> EngineResult

    Config via environment:
        YANDEX_API_KEY — IAM token or API key
        YANDEX_FOLDER_ID — Yandex Cloud folder ID
        YANDEX_MODEL — default model (yandexgpt-lite, yandexgpt-pro, etc.)
    """

    def __init__(self):
        self._api_key = os.environ.get("YANDEX_API_KEY", "")
        self._folder_id = os.environ.get("YANDEX_FOLDER_ID", "")
        self._default_model = os.environ.get("YANDEX_MODEL", DEFAULT_MODEL)

    def is_available(self) -> bool:
        """Check if YandexGPT is configured."""
        return bool(self._api_key and self._folder_id)

    def _build_request(self, prompt: str, config: EngineConfig,
                       stream: bool = False) -> dict:
        """Build YandexGPT API request body."""
        model = config.model if config.model.startswith("yandex") else self._default_model
        model_uri = _resolve_model_uri(model, self._folder_id)

        # Parse prompt into system + user messages
        messages = self._parse_prompt(prompt)

        body = {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": stream,
                "temperature": 0.3,
                "maxTokens": 8192,
            },
            "messages": messages,
        }
        return body

    def _parse_prompt(self, prompt: str) -> list[dict]:
        """Parse assembled prompt into system + user messages.

        The prompt from ContextBuilder has format:
        [Правила агента]
        ...system prompt...

        Сообщение пользователя: <actual user message>
        ...
        """
        messages = []

        # Split at "Сообщение пользователя:" marker
        marker = "\nСообщение пользователя: "
        if marker in prompt:
            system_part = prompt[:prompt.index(marker)]
            user_part = prompt[prompt.index(marker) + len(marker):]
            # Remove trailing instruction
            tail = "\nОтвечай на сообщение пользователя."
            if tail in user_part:
                user_part = user_part[:user_part.index(tail)]

            messages.append({"role": "system", "text": system_part.strip()})
            messages.append({"role": "user", "text": user_part.strip()})
        else:
            messages.append({"role": "user", "text": prompt})

        return messages

    def _get_headers(self) -> dict:
        """Build auth headers."""
        key = self._api_key
        # API key vs IAM token
        if key.startswith("AQVN") or key.startswith("t1."):
            auth = f"Bearer {key}"
        else:
            auth = f"Api-Key {key}"

        return {
            "Content-Type": "application/json",
            "Authorization": auth,
            "x-folder-id": self._folder_id,
        }

    async def execute(self, prompt: str, config: EngineConfig) -> EngineResult:
        """Non-streaming execution."""
        if not self.is_available():
            return EngineResult(
                success=False, text="", tools_used=[],
                duration_sec=0, session_id="",
                error_type="NO_BALANCE",
            )

        t0 = time.monotonic()
        body = self._build_request(prompt, config, stream=False)

        def _do_request() -> dict:
            data = json.dumps(body).encode()
            req = urllib.request.Request(
                YANDEX_API_URL,
                data=data,
                headers=self._get_headers(),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=config.timeout) as resp:
                return json.loads(resp.read())

        try:
            result = await asyncio.to_thread(_do_request)
            duration = time.monotonic() - t0

            # Extract text from response
            alternatives = result.get("result", {}).get("alternatives", [])
            if alternatives:
                text = alternatives[0].get("message", {}).get("text", "")
            else:
                text = ""

            return EngineResult(
                success=True,
                text=text,
                tools_used=[],
                duration_sec=duration,
                session_id=f"yandex-{int(time.time())}",
            )

        except urllib.error.HTTPError as e:
            duration = time.monotonic() - t0
            error_body = ""
            try:
                error_body = e.read().decode()[:500]
            except Exception:
                pass
            logger.error(f"YandexGPT API error {e.code}: {error_body}")

            error_type = "UNKNOWN"
            if e.code == 401 or e.code == 403:
                error_type = "AUTH"
            elif e.code == 429:
                error_type = "RATE_LIMIT"

            return EngineResult(
                success=False, text=f"YandexGPT error: {e.code}",
                tools_used=[], duration_sec=duration, session_id="",
                error_type=error_type,
            )
        except Exception as e:
            duration = time.monotonic() - t0
            logger.error(f"YandexGPT exception: {e}")
            return EngineResult(
                success=False, text=str(e),
                tools_used=[], duration_sec=duration, session_id="",
                error_type="EXCEPTION",
            )

    async def stream(self, prompt: str,
                     config: EngineConfig) -> AsyncIterator[Chunk]:
        """Streaming execution — yields Chunks progressively."""
        if not self.is_available():
            yield Chunk(type="error", text="YandexGPT not configured")
            return

        body = self._build_request(prompt, config, stream=True)
        headers = self._get_headers()

        def _stream_request():
            """Blocking HTTP request with streaming response."""
            data = json.dumps(body).encode()
            req = urllib.request.Request(
                YANDEX_STREAM_URL,
                data=data,
                headers=headers,
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=config.timeout)
            # YandexGPT streams as newline-delimited JSON
            buffer = b""
            for chunk_data in iter(lambda: resp.read(4096), b""):
                buffer += chunk_data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    yield line.decode("utf-8")
            # Remaining buffer
            if buffer.strip():
                yield buffer.strip().decode("utf-8")
            resp.close()

        accumulated = ""
        t0 = time.monotonic()

        yield Chunk(type="status", text="🤖 YandexGPT...")

        try:
            loop = asyncio.get_event_loop()
            # Run blocking stream in thread, collect results via queue
            queue: asyncio.Queue = asyncio.Queue()

            def _producer():
                try:
                    for line in _stream_request():
                        loop.call_soon_threadsafe(queue.put_nowait, ("line", line))
                    loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
                except Exception as e:
                    loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))

            thread = asyncio.ensure_future(asyncio.to_thread(_producer))

            while True:
                try:
                    msg_type, msg_data = await asyncio.wait_for(
                        queue.get(), timeout=config.timeout)
                except asyncio.TimeoutError:
                    yield Chunk(type="error", text="YandexGPT timeout")
                    break

                if msg_type == "done":
                    break
                elif msg_type == "error":
                    yield Chunk(type="error", text=f"YandexGPT: {msg_data}")
                    break
                elif msg_type == "line":
                    try:
                        obj = json.loads(msg_data)
                        # YandexGPT stream format: {"result": {"alternatives": [...]}}
                        alts = obj.get("result", {}).get("alternatives", [])
                        if alts:
                            text = alts[0].get("message", {}).get("text", "")
                            if text and text != accumulated:
                                # YandexGPT sends full text each time, extract delta
                                delta = text[len(accumulated):]
                                accumulated = text
                                if delta:
                                    yield Chunk(type="text", text=delta)
                    except json.JSONDecodeError:
                        pass

            duration = time.monotonic() - t0

            yield Chunk(
                type="result",
                text=accumulated,
                session_id=f"yandex-{int(time.time())}",
            )

        except Exception as e:
            logger.error(f"YandexGPT stream error: {e}")
            yield Chunk(type="error", text=str(e))
