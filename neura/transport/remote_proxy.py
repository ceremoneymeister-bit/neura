"""Remote capsule proxy — routes API/WS requests to external Neura servers.

When a capsule is migrated to a remote server (KZ cluster), the Aeza web
platform proxies requests transparently so the user sees a single URL.

Config: /opt/neura-v2/config/remote_capsules.yaml
"""

import asyncio
import logging
from pathlib import Path

import httpx
import websockets
import yaml
from fastapi import WebSocket

logger = logging.getLogger("neura.remote_proxy")

_CONFIG_PATH = Path("/opt/neura-v2/config/remote_capsules.yaml")
_remote_map: dict[str, str] = {}  # capsule_id → base URL


def load_remote_capsules() -> dict[str, str]:
    """Load remote capsules config. Returns {capsule_id: host_url}."""
    global _remote_map
    if not _CONFIG_PATH.exists():
        _remote_map = {}
        return _remote_map
    try:
        data = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
        _remote_map = {k: v["host"] for k, v in data.items() if isinstance(v, dict) and "host" in v}
        logger.info(f"Remote capsules loaded: {list(_remote_map.keys())}")
    except Exception as e:
        logger.error(f"Failed to load remote_capsules.yaml: {e}")
        _remote_map = {}
    return _remote_map


def is_remote(capsule_id: str | None) -> bool:
    """Check if capsule is on a remote server."""
    return bool(capsule_id and capsule_id in _remote_map)


def get_remote_host(capsule_id: str) -> str | None:
    """Get remote server URL for capsule."""
    return _remote_map.get(capsule_id)


async def proxy_rest(
    capsule_id: str,
    method: str,
    path: str,
    token: str,
    body: bytes | None = None,
    query_params: str = "",
) -> httpx.Response:
    """Proxy a REST request to the remote server."""
    host = _remote_map[capsule_id]
    url = f"{host}{path}"
    if query_params:
        url += f"?{query_params}"

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.request(
            method=method,
            url=url,
            content=body,
            headers=headers,
        )
    return resp


async def proxy_websocket(
    client_ws: WebSocket,
    capsule_id: str,
    conv_id: int,
    token: str,
):
    """Bidirectional WebSocket proxy to remote server.

    Client (browser) ↔ Aeza (this proxy) ↔ KZ server
    """
    host = _remote_map[capsule_id]
    # Convert http:// → ws://
    ws_url = host.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/ws/chat/{conv_id}?token={token}"

    logger.info(f"[proxy] WS connecting to {ws_url[:60]}… for capsule={capsule_id}")

    try:
        async with websockets.connect(
            ws_url,
            additional_headers={"Origin": "https://app.ceremoneymeister.ru"},
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5,
            open_timeout=10,
        ) as remote_ws:
            logger.info(f"[proxy] WS connected to remote for capsule={capsule_id}")

            async def client_to_remote():
                """Forward messages from browser → remote server."""
                try:
                    while True:
                        data = await client_ws.receive_text()
                        await remote_ws.send(data)
                except Exception:
                    pass

            async def remote_to_client():
                """Forward messages from remote server → browser."""
                try:
                    async for msg in remote_ws:
                        await client_ws.send_text(msg)
                except Exception:
                    pass

            # Run both directions concurrently
            tasks = [
                asyncio.create_task(client_to_remote()),
                asyncio.create_task(remote_to_client()),
            ]
            # Wait for either to finish (means connection closed on one side)
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()

    except websockets.exceptions.InvalidStatusCode as e:
        logger.error(f"[proxy] Remote WS rejected: {e}")
        await client_ws.send_json({"type": "error", "content": "Удалённый сервер недоступен. Попробуйте позже."})
    except ConnectionRefusedError:
        logger.error(f"[proxy] Remote server refused connection: {host}")
        await client_ws.send_json({"type": "error", "content": "Сервер агента недоступен."})
    except Exception as e:
        logger.error(f"[proxy] WS proxy error: {e}", exc_info=True)
        await client_ws.send_json({"type": "error", "content": "Ошибка подключения к агенту."})
