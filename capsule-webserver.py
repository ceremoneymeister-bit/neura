#!/usr/bin/env python3
"""Capsule Web Server — раздаёт статику из web/ каждой капсулы на отдельном порту.

Каждая капсула может создавать сайты в своей директории web/.
Сервер раздаёт их на персональном порту без доступа к системным конфигам.

Порты:
  9001 — marina_biryukova
  9002 — maxim_belousov
  9003 — yulia_gudymo
  9004 — victoria_sel
  9005 — yana_berezhnaya
  9006 — nikita_maltsev

Запуск: systemctl start capsule-webserver
"""

import http.server
import os
import signal
import socketserver
import sys
import threading
import logging
from pathlib import Path
from functools import partial
from urllib.parse import unquote

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("capsule-webserver")

HOMES_DIR = Path("/opt/neura-v2/homes")

# Порт → капсула (можно расширять)
PORT_MAP = {
    9001: "marina_biryukova",
    9002: "maxim_belousov",
    9003: "yulia_gudymo",
    9004: "victoria_sel",
    9005: "yana_berezhnaya",
    9006: "nikita_maltsev",
}

# Также обслуживаем /srv/capsules/ (bridge capsules)
CAPSULE_DIRS = {
    "marina_biryukova": "/srv/capsules/marina_biryukova",
    "maxim_belousov": "/srv/capsules/maxim_belousov",
    "yulia_gudymo": "/srv/capsules/yulia_gudymo",
    "victoria_sel": "/root/Antigravity/projects/Producing/Victoria_Sel",
    "yana_berezhnaya": "/srv/capsules/yana_berezhnaya",
    "nikita_maltsev": "/srv/capsules/nikita_maltsev",
}


class CapsuleHandler(http.server.SimpleHTTPRequestHandler):
    """Handler с path traversal защитой и SPA fallback."""

    def __init__(self, *args, web_root: str, capsule_name: str, **kwargs):
        self.web_root = web_root
        self.capsule_name = capsule_name
        super().__init__(*args, directory=web_root, **kwargs)

    def do_GET(self):
        # Path traversal protection
        path = unquote(self.path.split("?")[0].split("#")[0])
        resolved = Path(self.web_root).joinpath(path.lstrip("/")).resolve()
        if not str(resolved).startswith(self.web_root):
            self.send_error(403, "Forbidden")
            return

        # If file exists — serve it
        if resolved.is_file():
            super().do_GET()
            return

        # Try with .html extension (e.g. /mobile → /mobile.html)
        if not resolved.suffix:
            html_resolved = Path(str(resolved) + ".html")
            if html_resolved.is_file():
                self.path = path.rstrip("/") + ".html"
                super().do_GET()
                return

        # SPA fallback: if path has no extension and index.html exists
        if not resolved.suffix and (Path(self.web_root) / "index.html").exists():
            self.path = "/index.html"

        super().do_GET()

    def log_message(self, format, *args):
        logger.info(f"[{self.capsule_name}] {args[0]}")


def get_web_root(capsule_name: str) -> str:
    """Возвращает путь к web/ директории капсулы. Создаёт если нет."""
    # Проверяем оба расположения
    for base in [CAPSULE_DIRS.get(capsule_name, ""), str(HOMES_DIR / capsule_name)]:
        if base and Path(base).exists():
            web_dir = Path(base) / "web"
            web_dir.mkdir(exist_ok=True)
            # Создаём placeholder если пусто
            index = web_dir / "index.html"
            if not index.exists():
                index.write_text(
                    f'<!DOCTYPE html><html><head><meta charset="utf-8">'
                    f'<title>{capsule_name}</title></head>'
                    f'<body><h1>🚀 {capsule_name} — web space</h1>'
                    f'<p>Создайте файлы в <code>web/</code> для вашего сайта.</p>'
                    f'</body></html>',
                    encoding="utf-8",
                )
            return str(web_dir)
    return ""


servers: list[socketserver.TCPServer] = []


def start_server(port: int, capsule_name: str):
    """Запуск HTTP-сервера для одной капсулы."""
    web_root = get_web_root(capsule_name)
    if not web_root:
        logger.warning(f"Capsule {capsule_name} not found, skipping port {port}")
        return

    handler = partial(CapsuleHandler, web_root=web_root, capsule_name=capsule_name)

    try:
        server = socketserver.TCPServer(("0.0.0.0", port), handler)
        server.allow_reuse_address = True
        servers.append(server)
        logger.info(f"✅ {capsule_name} → http://0.0.0.0:{port} (root: {web_root})")
        server.serve_forever()
    except OSError as e:
        logger.error(f"❌ Port {port} for {capsule_name}: {e}")


def shutdown(signum, frame):
    logger.info("Shutting down all servers...")
    for s in servers:
        s.shutdown()
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info(f"Starting capsule web servers ({len(PORT_MAP)} capsules)...")

    threads = []
    for port, capsule_name in PORT_MAP.items():
        t = threading.Thread(target=start_server, args=(port, capsule_name), daemon=True)
        t.start()
        threads.append(t)

    # Wait forever
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
