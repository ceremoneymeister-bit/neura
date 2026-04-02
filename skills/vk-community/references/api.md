# VK API — справочник методов

Базовый URL: `https://api.vk.com/method/`
Версия API: `5.199`

Все запросы — POST или GET с параметрами. Ответ — JSON.

---

## wall.post — Публикация на стену

**Запрос:**
```
POST https://api.vk.com/method/wall.post
Content-Type: application/x-www-form-urlencoded

owner_id=-GROUP_ID
message=Текст поста
attachments=photo123456_789012
from_group=1
access_token=TOKEN
v=5.199
```

**Ответ (успех):**
```json
{
  "response": {
    "post_id": 123
  }
}
```

**Параметры:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| owner_id | int | ID владельца стены (отрицательный для сообщества) |
| message | string | Текст поста |
| attachments | string | Вложения (через запятую): photo{owner}_{id} |
| from_group | int | 1 = от имени сообщества |

---

## wall.get — Получение постов со стены

**Запрос:**
```
GET https://api.vk.com/method/wall.get?owner_id=-GROUP_ID&count=10&access_token=TOKEN&v=5.199
```

**Ответ:**
```json
{
  "response": {
    "count": 150,
    "items": [
      {
        "id": 123,
        "from_id": -GROUP_ID,
        "date": 1710000000,
        "text": "Текст поста",
        "attachments": [...]
      }
    ]
  }
}
```

---

## wall.delete — Удаление поста

**Запрос:**
```
POST https://api.vk.com/method/wall.delete
owner_id=-GROUP_ID&post_id=123&access_token=TOKEN&v=5.199
```

**Ответ:**
```json
{
  "response": 1
}
```

---

## photos.getWallUploadServer — URL для загрузки фото

**Запрос:**
```
GET https://api.vk.com/method/photos.getWallUploadServer?group_id=GROUP_ID&access_token=TOKEN&v=5.199
```

**Ответ:**
```json
{
  "response": {
    "upload_url": "https://pu.vk.com/c123/upload.php?act=wall_photo&mid=...",
    "album_id": -14,
    "user_id": 12345
  }
}
```

**Важно:** `group_id` передаётся БЕЗ минуса (положительное число).

---

## Загрузка файла на upload_url

**Запрос:**
```
POST {upload_url}
Content-Type: multipart/form-data

photo=@image.jpg
```

**Ответ:**
```json
{
  "server": 123456,
  "photo": "[{\"id\":...}]",
  "hash": "abc123def456"
}
```

---

## photos.saveWallPhoto — Сохранение загруженного фото

**Запрос:**
```
POST https://api.vk.com/method/photos.saveWallPhoto
group_id=GROUP_ID&server=123456&photo=[...]&hash=abc123def456&access_token=TOKEN&v=5.199
```

**Ответ:**
```json
{
  "response": [
    {
      "id": 789012,
      "album_id": -14,
      "owner_id": -GROUP_ID,
      "sizes": [...],
      "text": ""
    }
  ]
}
```

**Attachment string:** `photo{owner_id}_{id}` — используется в wall.post.

---

## messages.send — Отправка сообщения

**Запрос:**
```
POST https://api.vk.com/method/messages.send
peer_id=PEER_ID&message=Текст&random_id=RANDOM_INT&access_token=TOKEN&v=5.199
```

**Ответ:**
```json
{
  "response": 12345
}
```

**Параметры:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| peer_id | int | ID получателя (user_id или 2000000000+chat_id) |
| message | string | Текст сообщения |
| random_id | int | Уникальный ID для предотвращения дублей |

---

## messages.getHistory — История сообщений

**Запрос:**
```
GET https://api.vk.com/method/messages.getHistory?peer_id=PEER_ID&count=20&access_token=TOKEN&v=5.199
```

**Ответ:**
```json
{
  "response": {
    "count": 100,
    "items": [
      {
        "id": 456,
        "from_id": 12345,
        "date": 1710000000,
        "text": "Привет!",
        "out": 0
      }
    ]
  }
}
```

---

## groups.getLongPollServer — Получение Long Poll сервера

**Запрос:**
```
GET https://api.vk.com/method/groups.getLongPollServer?group_id=GROUP_ID&access_token=TOKEN&v=5.199
```

**Ответ:**
```json
{
  "response": {
    "key": "abc123",
    "server": "https://lp.vk.com/wh123456",
    "ts": "1"
  }
}
```

**Подключение к Long Poll:**
```
GET {server}?act=a_check&key={key}&ts={ts}&wait=25
```

**Ответ Long Poll:**
```json
{
  "ts": "2",
  "updates": [
    {
      "type": "message_new",
      "object": {
        "message": {
          "id": 789,
          "from_id": 12345,
          "text": "Новое сообщение",
          "date": 1710000000
        }
      }
    }
  ]
}
```

**Параметры Long Poll:**
| Параметр | Описание |
|----------|----------|
| key | Ключ сессии |
| server | URL сервера |
| ts | Номер последнего события |
| wait | Таймаут ожидания (макс. 90 сек) |

---

## Коды ошибок VK API

| Код | Описание | Действие |
|-----|----------|----------|
| 1 | Неизвестная ошибка | Повторить запрос |
| 5 | Авторизация не удалась | Проверить токен |
| 6 | Слишком много запросов | Подождать 0.5 сек и повторить |
| 7 | Нет прав | Проверить scopes токена |
| 14 | Требуется капча | Показать captcha_img, ввести captcha_key |
| 15 | Доступ запрещён | Проверить настройки сообщества |
| 100 | Невалидные параметры | Проверить параметры запроса |
| 200 | Нет доступа к альбому | Проверить права на фото |
| 214 | Нет прав на публикацию | Проверить права в сообществе |
