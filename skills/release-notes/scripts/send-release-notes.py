#!/usr/bin/env python3
"""
Release Notes — рассылка обновлений в топик «Обновления» всех HQ-групп.

Usage:
  python3 send-release-notes.py "HTML-текст обновления"
  echo "текст" | python3 send-release-notes.py -

Автоматически:
  - Создаёт топик «📦 Обновления» если его нет (topic_id = null в config)
  - Сохраняет topic_id обратно в config.json
  - Пропускает disabled группы и группы без bot_token
  - Выводит отчёт по каждой группе
"""

import json
import sys
import urllib.request
import urllib.parse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "config.json"

# Цвет иконки для топика (зелёный)
TOPIC_ICON_COLOR = 7322096


def tg_api(token: str, method: str, data: dict) -> dict:
    """Вызов Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        return {"ok": False, "description": str(e)}


def create_topic(token: str, group_id: int, name: str = "📦 Обновления") -> int | None:
    """Создаёт топик в группе, возвращает topic_id."""
    result = tg_api(token, "createForumTopic", {
        "chat_id": group_id,
        "name": name,
        "icon_color": TOPIC_ICON_COLOR,
    })
    if result.get("ok"):
        topic_id = result["result"]["message_thread_id"]
        return topic_id
    else:
        print(f"  ⚠️  Не удалось создать топик: {result.get('description', 'unknown')}")
        return None


def send_message(token: str, group_id: int, topic_id: int, text: str) -> bool:
    """Отправляет сообщение в топик."""
    result = tg_api(token, "sendMessage", {
        "chat_id": group_id,
        "message_thread_id": topic_id,
        "text": text,
        "parse_mode": "HTML",
    })
    if result.get("ok"):
        return True
    else:
        print(f"  ❌ Ошибка отправки: {result.get('description', 'unknown')}")
        return False


def main():
    # Получаем текст сообщения
    if len(sys.argv) < 2:
        print("Usage: send-release-notes.py \"HTML-текст\"")
        print("       echo \"текст\" | send-release-notes.py -")
        sys.exit(1)

    if sys.argv[1] == "-":
        message = sys.stdin.read().strip()
    else:
        message = sys.argv[1]

    if not message:
        print("❌ Пустое сообщение")
        sys.exit(1)

    # Загружаем конфиг
    if not CONFIG_PATH.exists():
        print(f"❌ Конфиг не найден: {CONFIG_PATH}")
        sys.exit(1)

    config = json.loads(CONFIG_PATH.read_text())
    config_modified = False

    sent = []
    failed = []
    skipped = []

    for group in config["groups"]:
        name = group["name"]

        # Пропускаем disabled
        if not group.get("enabled", True):
            skipped.append(name)
            print(f"⏭️  {name} — disabled, пропущено")
            continue

        # Пропускаем без токена
        token = group.get("bot_token")
        if not token:
            skipped.append(name)
            print(f"⏭️  {name} — нет bot_token, пропущено")
            continue

        group_id = group["group_id"]
        topic_id = group.get("updates_topic_id")

        print(f"\n📤 {name} (group {group_id})...")

        # Создаём топик если нет
        if topic_id is None:
            print("  Создаю топик «📦 Обновления»...")
            topic_id = create_topic(token, group_id)
            if topic_id:
                group["updates_topic_id"] = topic_id
                config_modified = True
                print(f"  ✅ Топик создан (id={topic_id})")
            else:
                failed.append(name)
                continue

        # Отправляем
        if send_message(token, group_id, topic_id, message):
            sent.append(name)
            print(f"  ✅ Отправлено")
        else:
            failed.append(name)

    # Сохраняем обновлённый конфиг (topic_id)
    if config_modified:
        CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2))
        print("\n💾 Конфиг обновлён (сохранены topic_id)")

    # Итог
    print(f"\n{'='*40}")
    print(f"✅ Отправлено: {', '.join(sent) if sent else '—'}")
    if failed:
        print(f"❌ Ошибки: {', '.join(failed)}")
    if skipped:
        print(f"⏭️  Пропущено: {', '.join(skipped)}")
    print(f"Всего: {len(sent)}/{len(config['groups'])} групп")


if __name__ == "__main__":
    main()
