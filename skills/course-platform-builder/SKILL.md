---
name: course-platform-builder
description: Full-stack course platform builder. Covers frontend (React+Vite+Tailwind), backend (Express+PostgreSQL+Redis), auth (JWT+bcrypt), video pipeline (HLS+AES-128), admin panel, deployment (nginx+systemd+SSL), and migration. Use for: обучающая платформа, курсы, LMS, онлайн-школа, 'свой GetCourse'.
version: 3.0.0
author: Дмитрий Ростовцев
created: 2026-03-17
updated: 2026-04-02
category: development
tags: [lms, course-platform, react, express, postgresql, hls, video-encryption]
risk: safe
usage_count: 4
last_used: 2026-04-02
maturity: tested
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "клиент просит обучающую платформу/LMS"
proactive_trigger_1_action: "запустить Full-Stack Playbook"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 3
learning_auto_update: [anti-patterns, triggers, changelog]
---

# course-platform-builder v3 — Full-Stack Playbook

## Purpose

Создание полноценной обучающей платформы (аналог GetCourse/Teachable) с нуля за 1-2 сессии. Фронтенд + бэкенд + БД + auth + защищённое видео + деплой.

## When to Use

- Клиент просит "обучающую платформу" / "онлайн-школу"
- Нужна альтернатива GetCourse на собственном хостинге
- Проект с видеоуроками, модулями, прогрессом, оплатой

## Reference Implementation

`/root/Antigravity/projects/course-platform/` — шаблон (Семён Пискунов, «Тренировочное место»)

---

## Стек (фиксированный)

### Frontend
- React 19 + Vite 7 + Tailwind CSS 4
- react-router-dom v7, Lucide React, Framer Motion
- hls.js (видео)

### Backend
- Express.js 4, Node.js 22+
- PostgreSQL 16 (pg), Redis 7 (ioredis)
- bcrypt, jsonwebtoken, cors, helmet, cookie-parser, express-rate-limit
- multer (upload)

### System
- nginx (reverse proxy + HLS segment serving)
- systemd (process management)
- FFmpeg + OpenSSL (video HLS+AES-128 encryption)
- certbot (SSL)

---

## Proactive Excellence — на каждом шаге

| # | Проверка | Как |
|---|---------|-----|
| 1 | Copy quality (4U заголовки, Feature→Benefit→Outcome) | headline-lab |
| 2 | CTA stress ↔ температура трафика | CTA Stress Matrix |
| 3 | Psychology triggers (social proof, authority, risk reversal) | PLFS |
| 4 | Consistency (FAQ↔Pricing↔Hero↔CTA — одни термины) | Grep |
| 5 | Visual (контраст ≥4.5:1, hover states, mobile OK) | Playwright |
| 6 | Data integrity (нет placeholder, дублей, негативных отзывов) | Grep |
| 7 | Product ladder (≥3 уровня: lead magnet→main→premium) | product-ladder |
| 8 | Wow-момент (интерактив, анимация) | UX "Восторг" |
| 9 | About author (фото, регалии, доверие) | Секция |
| 10 | Numbers (конкретные цифры: уроки, часы, ученики) | Min 3 числа |

---

## Workflow: 8 фаз от нуля до production

### Фаза 1: Сбор требований (5 мин)

Спросить:
1. Название платформы, автор, описание
2. Акцентный цвет (hex), логотип
3. Контакты: telegram, email, домен
4. Структура курса: направления, модули, уроки, длительности
5. Тарифы: названия, цены, фичи, какие уроки бесплатные
6. Есть ли ЮKassa/Robokassa аккаунт?
7. Домен + хостинг (VPS/shared)

### Фаза 2: Frontend (шаблон)

**Клонировать шаблон:**
```bash
cp -r projects/course-platform/ projects/Producing/{Client}/platform/
cd projects/Producing/{Client}/platform/ && npm install
```

**Кастомизация (порядок):**

| # | Файл | Что менять |
|---|------|-----------|
| 1 | `src/config.js` | name, author, accent, telegram, email, domain, API_BASE |
| 2 | `src/index.css` | --color-accent* в @theme |
| 3 | `src/data/courses.js` | Реальная структура курса |
| 4 | `src/data/pricing.js` | Тарифы с ценами |
| 5 | `src/data/testimonials.js` | Отзывы (или удалить секцию) |
| 6 | `public/` | Логотип, фото, favicon |
| 7 | Landing-секции | Hero, Problems, ForWhom под нишу |

**Ключевые файлы фронтенда:**

```
src/
├── lib/
│   ├── api.js          ← fetch wrapper + auto-refresh JWT
│   ├── auth.js         ← login/register/logout/restoreSession
│   └── progress.js     ← markComplete/updateWatched/getDashboard
├── hooks/
│   └── useAuth.jsx     ← AuthProvider + useAuth hook (async + session restore)
├── components/
│   ├── ui/VideoPlayer.jsx  ← hls.js + AES key auth + custom controls
│   ├── cabinet/            ← CourseCard, LessonCard, ModuleAccordion, ProgressBar
│   ├── landing/            ← Hero, Problems, ForWhom, Program, Testimonials, Pricing, FAQ, CTA
│   └── layout/             ← PublicNavbar, CabinetSidebar, CabinetLayout, Footer
├── pages/              ← Landing, Login, Register, Payment, Dashboard, Catalog, Detail, Lesson, Profile, Admin, NotFound
└── config.js           ← SITE object + API_BASE
```

**Vite proxy (dev):**
```javascript
// vite.config.js
server: { proxy: { '/cp-api': { target: 'http://127.0.0.1:3001', changeOrigin: true } } }
```

### Фаза 3: Backend

**Создать `backend/`:**
```bash
mkdir -p backend/src/{config,middleware,routes,services,db/migrations}
```

**package.json:**
```json
{
  "type": "module",
  "dependencies": {
    "express": "^4.21", "pg": "^8.13", "ioredis": "^5.4",
    "bcrypt": "^5.1", "jsonwebtoken": "^9.0", "cors": "^2.8",
    "helmet": "^8.0", "express-rate-limit": "^7.5", "dotenv": "^16.4",
    "uuid": "^11.1", "multer": "^1.4", "cookie-parser": "^1.4"
  }
}
```

**Файлы бэкенда:**

| Файл | Назначение |
|------|-----------|
| `server.js` | Entry: express + routes + middleware + helmet + cors + cookie-parser |
| `src/config/database.js` | pg.Pool (connectionString из .env) |
| `src/config/redis.js` | ioredis клиент (db index 2) |
| `src/middleware/auth.js` | JWT Bearer verify, TOKEN_EXPIRED code |
| `src/middleware/admin.js` | role === 'admin' check |
| `src/middleware/errorHandler.js` | 23505→409, generic→500 |
| `src/services/authService.js` | bcrypt(12), JWT sign/verify, refresh tokens (SHA-256 hash) |
| `src/routes/auth.js` | register/login/refresh/logout + rate limiting |
| `src/routes/courses.js` | GET courses, GET course/:id, GET lesson (+ access control) |
| `src/routes/progress.js` | POST complete, PUT watch, GET dashboard |
| `src/routes/profile.js` | GET/PUT profile, PUT password (+ revoke tokens) |
| `src/routes/payments.js` | Заглушка → ЮKassa когда готова |
| `src/routes/video.js` | GET playlist (rewrite key URL), GET key (signed token) |
| `src/routes/admin.js` | GET stats, GET users, PUT user/plan |
| `src/db/migrate.js` | File-based migration runner |
| `src/db/seed.js` | Импорт из courses.js + pricing.js → PostgreSQL |

### Фаза 4: Database

**Создать БД:**
```bash
docker exec {postgres_container} psql -U {superuser} -d postgres -c "CREATE USER course_platform WITH PASSWORD '{password}';"
docker exec {postgres_container} psql -U {superuser} -d postgres -c "CREATE DATABASE course_platform OWNER course_platform;"
```

**9 таблиц (5 миграций):**

| Таблица | Ключевые колонки | Назначение |
|---------|-----------------|-----------|
| users | id UUID, email, password_hash, name, role, plan_id, plan_expires_at | Студенты + админы |
| courses | id VARCHAR, title, subtitle, description, color, sort_order, is_active | Курсы |
| modules | id, course_id FK, title, sort_order | Модули внутри курса |
| lessons | id, module_id FK, title, duration, video_path, **is_free**, sort_order | Уроки (is_free — доступ без оплаты) |
| plans | id, name, price (kopecks!), features JSONB | Тарифы |
| payments | id UUID, user_id FK, plan_id FK, amount, status, yukassa_id | Платежи |
| lesson_progress | user_id FK, lesson_id FK, completed, watched_seconds, UNIQUE(user+lesson) | Прогресс |
| refresh_tokens | user_id FK, token_hash (SHA-256), expires_at | Refresh tokens |
| video_keys | lesson_id FK UNIQUE, key_path, iv_hex | AES ключи для HLS |
| _migrations | name UNIQUE, applied_at | Трекинг миграций |

**Seed:** `npm run setup` = migrate + seed (courses.js + pricing.js → БД + admin user)

### Фаза 5: Auth system

**Токены:**
- Access token: JWT, 15 мин, в памяти React (НЕ localStorage!)
- Refresh token: random hex 64, 30 дней, httpOnly cookie, SHA-256 хэш в БД
- Пароли: bcrypt, 12 rounds

**Frontend api.js:**
- Хранит accessToken в module-level variable
- Interceptor: на 401+TOKEN_EXPIRED → POST /auth/refresh (cookie) → retry
- Deduplicate concurrent refresh calls (refreshPromise singleton)

**Access control:**
```
lesson.is_free → доступен всем зарегистрированным
user.plan_id IN ('full','personal') AND NOT expired → все уроки
иначе → 403 PLAN_REQUIRED
```

### Фаза 6: Video Pipeline

**Конвертация (scripts/convert-video.sh):**
```bash
# Генерация AES-128 ключа
openssl rand 16 > keys/{courseId}/{lessonId}/enc.key
# FFmpeg: MP4 → encrypted HLS
ffmpeg -i input.mp4 -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k \
  -hls_time 10 -hls_list_size 0 -hls_playlist_type vod \
  -hls_key_info_file keyinfo.txt \
  -hls_segment_filename "media/hls/{courseId}/{lessonId}/seg_%04d.ts" \
  media/hls/{courseId}/{lessonId}/playlist.m3u8
```

**Serving:**
- GET `/cp-api/video/:lessonId/playlist` → backend переписывает EXT-X-KEY URI с signed JWT (5 мин TTL)
- GET `/cp-api/video/key/:lessonId/:signedToken` → backend проверяет JWT, отдаёт 16-byte ключ
- nginx: .ts сегменты раздаёт напрямую (зашифрованы), .m3u8/.key → deny

**Frontend VideoPlayer.jsx:**
```javascript
// hls.js с auth token injection
const hls = new Hls({
  xhrSetup: (xhr, url) => {
    xhr.setRequestHeader('Authorization', `Bearer ${accessToken}`)
  }
})
hls.loadSource(`/cp-api/video/${lessonId}/playlist`)
hls.attachMedia(videoRef.current)
```

**Защита от скачивания (85-95%):**
1. Сегменты зашифрованы AES-128 (бесполезны без ключа)
2. Ключ по signed JWT (5 мин TTL)
3. Плейлист через API (не напрямую)
4. context menu disabled
5. Не защищает от screen recording (DRM-level нужен для этого)

### Фаза 7: Deployment

**Структура на VPS:**
```
/opt/course-platform/
├── backend/     ← Express.js + .env
├── frontend/    ← Vite build output
├── media/       ← originals/ + hls/{course}/{lesson}/
└── keys/        ← AES ключи
```

**systemd:**
```ini
[Service]
WorkingDirectory=/opt/course-platform/backend
ExecStart=/usr/bin/node server.js
MemoryMax=1G
Restart=always
```

**nginx:**
```nginx
server {
    server_name yourdomain.com;
    location /cp-api/ { proxy_pass http://127.0.0.1:3001; }
    location /hls/ {
        alias /opt/course-platform/media/hls/;
        location ~ \.(m3u8|key)$ { return 403; }
    }
    location / {
        root /opt/course-platform/frontend;
        try_files $uri /index.html;
    }
}
```

**SSL:** `certbot --nginx -d yourdomain.com`

**Deploy script:**
```bash
cd /root/Antigravity/projects/{Client}/platform
npm run build
rsync -av --exclude=node_modules --exclude=.env backend/ /opt/course-platform/backend/
rsync -av dist/ /opt/course-platform/frontend/
systemctl restart course-platform
```

### Фаза 8: Migration (к клиенту)

```bash
# Export
pg_dump course_platform > dump.sql
tar czf export.tar.gz backend/ frontend/ media/ keys/ dump.sql nginx.conf service.conf
# На сервере клиента
tar xzf export.tar.gz && psql < dump.sql
# Обновить .env (домен, пароли), nginx (домен, SSL), DNS
```

---

## .env template (backend)

```
PORT=3001
NODE_ENV=production
DOMAIN=https://yourdomain.com
DATABASE_URL=postgresql://course_platform:PASSWORD@127.0.0.1:5432/course_platform
REDIS_URL=redis://127.0.0.1:6379/2
JWT_SECRET=<openssl rand -hex 32>
JWT_REFRESH_SECRET=<unused, можно убрать>
MEDIA_DIR=/opt/course-platform/media
KEYS_DIR=/opt/course-platform/keys
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_NAME=Admin
ADMIN_PASSWORD=<openssl rand -base64 12>
```

---

## API Endpoints (20 total)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /cp-api/auth/register | No | {name, email, password} → {user, accessToken} + cookie |
| POST | /cp-api/auth/login | No | {email, password} → {user, accessToken} + cookie |
| POST | /cp-api/auth/refresh | No | cookie → {user, accessToken} + new cookie |
| POST | /cp-api/auth/logout | Yes | Revoke all refresh tokens |
| GET | /cp-api/courses | Yes | All courses + user progress |
| GET | /cp-api/courses/:id | Yes | Course with modules/lessons + progress |
| GET | /cp-api/courses/:id/lessons/:lid | Yes | Lesson + access check + prev/next |
| POST | /cp-api/progress/:lessonId/complete | Yes | Mark lesson completed |
| PUT | /cp-api/progress/:lessonId/watch | Yes | Update watched seconds |
| GET | /cp-api/progress/dashboard | Yes | Stats + lastLesson + per-course progress |
| GET | /cp-api/profile | Yes | User + plan info |
| PUT | /cp-api/profile | Yes | Update name/email |
| PUT | /cp-api/profile/password | Yes | Change password (revokes tokens) |
| POST | /cp-api/payments/create | Yes | Create payment (stub → ЮKassa) |
| POST | /cp-api/payments/webhook | No* | ЮKassa callback |
| GET | /cp-api/payments/history | Yes | User's payments |
| GET | /cp-api/video/:lid/playlist | Yes | Signed HLS playlist |
| GET | /cp-api/video/key/:lid/:token | No* | AES key (token in URL) |
| GET | /cp-api/admin/stats | Admin | Dashboard stats |
| GET | /cp-api/admin/users | Admin | Users list + search + pagination |
| PUT | /cp-api/admin/users/:id/plan | Admin | Assign plan manually |
| GET | /cp-api/health | No | Server health check |

---

## Ошибки из опыта (ИЗБЕГАТЬ!)

### Frontend
1. **JSX в .js файлах** → расширение `.jsx` для файлов с JSX
2. **Хардкод цветов** → ТОЛЬКО тем-токены (text-text, bg-accent)
3. **Рассогласование API** → создавать lib/ ПЕРВЫМИ, контракты в промпт
4. **FAQ↔Pricing несоответствие** → единый источник данных для названий тарифов
5. **Негативные отзывы** → каждый отзыв = проблема → результат
6. **Config placeholder** → grep example.ru перед деплоем
7. **Лого дубль** → навбар скрывает лого до скролла
8. **Hero mobile** → раздельные bg для mobile/desktop, НИКОГДА cover
9. **dynamic import api.js** → всегда static import

### Backend
10. **Email validation** → regex на регистрации/логине
11. **UUID validation** → перед каждым query по userId
12. **Plan expiry** → ВСЕГДА проверять plan_expires_at при access control
13. **Rate limiting** → обязательно на /register и /login
14. **Token revocation** → при смене пароля → revokeUserTokens()
15. **Admin password в .env** → убрать после первого запуска, использовать password reset

### Deploy
16. **SSL cert paths** → certbot создаёт в /etc/letsencrypt/live/{domain}/
17. **Nginx SNI** → добавить домен в stream map если используется SNI router
18. **CORS domain** → обновить DOMAIN в .env при деплое

---

## Чеклист для агентов

```
ПРАВИЛА ДЛЯ ГЕНЕРАЦИИ:
- Расширение: .jsx для файлов с JSX
- Цвета: ТОЛЬКО тем-токены (text-text, bg-accent, border-border)
- ЗАПРЕЩЕНЫ: gray-*, indigo-* и другие прямые цвета Tailwind
- Auth: useAuth() hook, НЕ localStorage напрямую
- API: import { api } from '../lib/api.js', НЕ fetch напрямую
- Progress: import { markLessonCompleted, updateWatchedSeconds } from '../lib/progress.js'
- Анимации: FadeIn from '../components/ui/FadeIn.jsx'
- Иконки: из 'lucide-react'
- Видео: VideoPlayer принимает lessonId, НЕ src
```

---

## Верификация (каждая фаза)

```bash
# Фаза 3: Backend
curl localhost:3001/cp-api/health  # → {status: ok}

# Фаза 4: Database
npm run setup  # → Applied: 001-005, Seed: 4 courses, 18 lessons, 3 plans

# Фаза 5: Auth
curl -X POST localhost:3001/cp-api/auth/register -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@test.ru","password":"123456"}'
# → 201 + {user, accessToken}

# Фаза 6: Video
bash scripts/convert-video.sh sample.mp4 test test-1
# → seg_0000.ts (encrypted), playlist.m3u8 with EXT-X-KEY

# Фаза 7: Deploy
curl -sk --resolve yourdomain:443:127.0.0.1 https://yourdomain/cp-api/health
# → {status: ok}

# Полный flow
npm run build  # frontend
systemctl restart course-platform  # backend
```

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->

### 2026-03-17 — скелет платформы + первый аудит
- Реализован скелет (38 файлов, React+Vite+TW4, 10 маршрутов, landing+кабинет+admin)
- Аудит: 8 багов, 3 critical (тем-токены, auth persistence, video tracking)
- Урок: ВСЕГДА проводить аудит после генерации скелета — critical баги в 100% случаев

### 2026-04-01 — кастомизация под «Тренировочное место»
- Полная кастомизация: dark→light (#F5F4F0/#201712/#E4AB70), golden gradient CTA, Oswald uppercase
- Hero: 12 итераций (v1→v12) — фоновое фото + текст поверх на mobile = основная проблема
- Решение: раздельные bg для mobile/desktop, CSS gradient text заголовок, marquee бегущая строка
- Антипаттерн: background-size cover на hero с человеком = обрезает на mobile. Использовать contain + position tuning
- Антипаттерн: логотип в navbar + hero = дубль. Скрывать navbar logo до скролла
- Антипаттерн: НЕ уменьшать на mobile — position split (текст вверху, фото внизу)
- Урок: ВСЕГДА верифицировать скриншотами (Playwright) на 3 viewport (390/430/1440)

### 2026-04-01 — конструктор занятий v2
- 3 концепции (Interactive Picker + Weekly Grid + Accordion Details) вместо фото (однотипные)
- Иконки вместо фото (Leaf/Dumbbell/Wind/Zap) — решение проблемы плохого фотоконтента
- Добавлена секция Proactive Excellence (10-point checklist) в SKILL.md
- Урок: если фото клиента однотипны → переходить на иконки/иллюстрации

### 2026-04-02 — архитектурное проектирование + тотальный аудит + v3
- Архитектура: Express+SQLite на VPS, SPA на REG.ru. 7 таблиц, 12 API endpoints, YouTube unlisted, ЮKassa
- Тотальный аудит (3 параллельных агента): Backend 6C/8H/11M/9L, Frontend 0C/0H/1M/1L
- Пофикшено: email validation, rate limiting, plan expiry check, token revocation
- SKILL.md полностью переписан v2→v3 (full-stack playbook, 8 фаз)
- Антипаттерн: dynamic import() для api.js в React = race condition. ТОЛЬКО static import
- Антипаттерн: plan_expires_at ВСЕГДА проверять при access control
- Урок: всегда предлагать 2-3 варианта архитектуры с trade-offs перед стартом
