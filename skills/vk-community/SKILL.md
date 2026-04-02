---
name: vk-community
description: "Use when managing VK communities - posting, messages, Long Poll monitoring, photo uploads, wall management. For any client needing VK integration."
version: 1.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-03-19
updated: 2026-03-19
category: integration
tags: [vk, vkontakte, social-media, community, posting, messages]
risk: low
source: internal
---

# vk-community

## Purpose

Управление сообществами ВКонтакте через CLI. Публикация постов, загрузка фото, чтение/отправка сообщений, мониторинг через Long Poll. Используется для любого клиента, которому нужна VK-интеграция (Victoria Sel, Marina Biryukova и др.).

## When to Use

- Пользователь говорит "опубликуй в ВК", "пост ВКонтакте", "VK сообщество"
- Нужно отправить/прочитать сообщения сообщества ВК
- Загрузка фото на стену сообщества
- Мониторинг входящих сообщений через Long Poll
- Управление стеной: просмотр, удаление постов
- Любая интеграция с VK API

## Requirements

### VK User Token

Для работы нужен токен с правами (scopes):
- `wall` — публикация и управление стеной
- `groups` — доступ к сообществам
- `photos` — загрузка фото
- `video` — работа с видео
- `messages` — сообщения сообщества
- `offline` — бессрочный токен

### Как получить токен

**Implicit Flow (самый простой):**

1. Создать Standalone-приложение на https://dev.vk.com/
2. Перейти по URL (подставить APP_ID):
   ```
   https://oauth.vk.com/authorize?client_id=APP_ID&scope=wall,groups,photos,video,messages,offline&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&v=5.199
   ```
3. Разрешить доступ — токен будет в URL после редиректа (`access_token=...`)

**Для токена сообщества:**
- Настройки сообщества → Работа с API → Создать ключ

## Core Workflow

### 1. Публикация поста

```bash
python3 scripts/vk-cli.py post TOKEN -GROUP_ID "Текст поста"
python3 scripts/vk-cli.py post TOKEN -GROUP_ID "Текст" --photo ./image.jpg
```

- `GROUP_ID` передаётся с минусом (владелец = сообщество)
- При `--photo` — автоматически загружает фото перед публикацией

### 2. Загрузка фото

```bash
python3 scripts/vk-cli.py upload-photo TOKEN GROUP_ID ./image.jpg
```

Трёхшаговый процесс:
1. `photos.getWallUploadServer` — получить URL для загрузки
2. POST файла на полученный URL
3. `photos.saveWallPhoto` — сохранить фото

### 3. Чтение сообщений

```bash
python3 scripts/vk-cli.py get-messages TOKEN GROUP_ID --count 20
```

Получает историю сообщений сообщества.

### 4. Отправка сообщения

```bash
python3 scripts/vk-cli.py send-message TOKEN PEER_ID "Текст сообщения"
```

### 5. Long Poll мониторинг

```bash
python3 scripts/vk-cli.py poll TOKEN GROUP_ID --auto-read
```

- Подключается к Long Poll серверу сообщества
- Выводит входящие события в реальном времени
- `--auto-read` — автоматически помечает сообщения как прочитанные

### 6. Управление стеной

```bash
python3 scripts/vk-cli.py wall-get TOKEN -GROUP_ID --count 10
python3 scripts/vk-cli.py wall-delete TOKEN -GROUP_ID POST_ID
```

## CLI Reference

| Команда | Описание |
|---------|----------|
| `post` | Публикация на стену (с опциональным фото) |
| `upload-photo` | Загрузка фото для стены |
| `get-messages` | Получение сообщений сообщества |
| `send-message` | Отправка сообщения |
| `poll` | Long Poll мониторинг |
| `wall-get` | Получение постов со стены |
| `wall-delete` | Удаление поста |

Токен можно передать аргументом или через переменную окружения `VK_TOKEN`.

## Security

- Токены хранить ТОЛЬКО в `.env` (файл в `.gitignore`)
- НЕ коммитить токены в репозиторий
- Использовать переменную `VK_TOKEN` вместо передачи токена в аргументах
- User Token даёт полный доступ — обращаться осторожно
- Для ограниченных задач предпочитать Community Token

## Anti-Patterns

1. **Хардкод токена в скрипт** — токен ТОЛЬКО через аргумент или env var, никогда в коде
2. **Игнорирование rate limits** — VK ограничивает до 3 запросов/сек для User Token, 20/сек для Server Token. Скрипт обрабатывает ошибку 6 (Too many requests)
3. **Публикация без проверки** — перед массовыми действиями проверить owner_id и содержимое

## References

- `references/api.md` — справочник методов VK API с примерами
- CLI скрипт: `scripts/vk-cli.py`
