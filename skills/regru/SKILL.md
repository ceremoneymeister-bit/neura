---
name: regru
description: Управление хостингом REG.ru — деплой через FTP, DNS, SSL, домены
version: 1.0.0
category: infrastructure
tags: [regru, ftp, deploy, dns, ssl, hosting]
usage_count: 0
maturity: seed
last_used: null
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "после деплоя сайта"
proactive_trigger_1_action: "проверить SSL, DNS, .htaccess"
proactive_trigger_2_type: event
proactive_trigger_2_condition: "новый домен/поддомен"
proactive_trigger_2_action: "настроить DNS и SSL"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 3
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Скилл: regru — Управление хостингом REG.ru

> Универсальный скилл для работы с REG.ru: деплой через FTP, управление DNS, SSL, доменами.
> Работает с любым аккаунтом REG.ru — креды берутся из `CREDENTIALS.md` по alias хостинга.

---

## Конфигурация хостингов

| Hosting ID | FTP Host | FTP User | Сайты |
|-----------|----------|----------|-------|
| host-argisht | 31.31.197.39 | u3233563_Claude | argisht.ru, ceremoneymeister.ru |
| host-yana | 31.31.198.57 | u3449681_claudecode | бережная.space |
| host-maxim | 37.140.192.242 | u3457812 | нэйра.рф |

---

## Реестр сайтов

| Alias | Hosting ID | Локальный путь | Remote путь | URL | RewriteBase |
|-------|-----------|---------------|-------------|-----|-------------|
| promassage | host-argisht | projects/Producing/Argisht_Mamreyan/website/pro_массаж-landing-page | /www/argisht.ru/promassage | https://argisht.ru/promassage/ | /promassage/ |
| ceremoneymeister | host-argisht | projects/ceremoneymeister | /www/ceremoneymeister.ru | https://ceremoneymeister.ru/ | / |
| yana | host-argisht | projects/Producing/Ian_Berezhnaya/website/corporate-wellness-landing-page | /www/berezhnaya.space | https://berezhnaya.space/ | / |
| ag-radio | host-argisht | projects/antigravity-radio | /www/music.ceremoneymeister.ru | https://music.ceremoneymeister.ru/ | / |
| neura | host-argisht | projects/Producing/Maxim_Belousov/website | /www/ceremoneymeister.ru/neura | https://ceremoneymeister.ru/neura/ | /neura/ |
| neyra-rf | host-maxim | projects/Producing/Maxim_Belousov/website | /www/xn--80arln7d.xn--p1ai | https://нэйра.рф/ | / |

---

## Workflows

### 1. Deploy (деплой сайта)

**Триггеры:** "задеплой", "деплой", "deploy", "залей на хостинг", "обнови сайт"

**Процесс:**

1. **Pre-flight** — найти сайт в реестре по alias, проверить `package.json`, оценить объём изменений
   - 1–3 файла = деплой автоматически
   - 4+ файлов = спросить подтверждение
2. **Build** — `npm run build` в директории проекта, проверить `dist/`
3. **.htaccess** — сгенерировать SPA rewrite с правильным `RewriteBase`:
   ```apache
   RewriteEngine On
   RewriteBase <RewriteBase из реестра>

   # HTTPS redirect (nginx proxy перед Apache)
   RewriteCond %{HTTP:X-Forwarded-Proto} !https
   RewriteCond %{HTTPS} off
   RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

   # SPA routing
   RewriteCond %{REQUEST_FILENAME} !-f
   RewriteCond %{REQUEST_FILENAME} !-d
   RewriteRule . index.html [L]
   ```
   **⚠️ НЕ использовать только `%{HTTPS} off` — REG.ru nginx проксирует, Apache не видит HTTPS. Нужен `%{HTTP:X-Forwarded-Proto}`.**
4. **FTP Upload** — скрипт `scripts/ftp-deploy.py`:
   ```bash
   python3 .agent/skills/regru/scripts/ftp-deploy.py \
     --host <ftp_host> --user <ftp_user> --password <pwd> \
     --local-dir <dist_path> --remote-dir <remote_path> \
     --clean-assets --skip-media --timeout 30
   ```
5. **Verify** — `curl -sI <URL>` → HTTP 200

### 2. DNS Setup (настройка DNS)

**Триггеры:** "настрой DNS", "привяжи домен"

**Процесс:**
1. Определить домен и IP хостинга
2. В ЛК REG.ru → DNS-серверы домена → установить ns1.hosting.reg.ru / ns2.hosting.reg.ru
3. Или вручную: A-запись → IP хостинга, CNAME www → домен
4. Проверить: `dig <домен> A` (ожидание до 24–48ч)

**Документация:** help.reg.ru/support/dns-servery-i-nastroyka-zony/

### 3. SSL Setup (установка SSL)

**Триггеры:** "установи SSL", "настрой HTTPS"

**Процесс:**
1. В панели хостинга → SSL-сертификаты → Let's Encrypt (бесплатный)
2. Добавить в .htaccess редирект HTTP→HTTPS:
   ```apache
   RewriteCond %{HTTPS} off
   RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
   ```
3. Проверить: `curl -sI https://<домен>`

**Документация:** help.reg.ru/support/ssl-sertifikaty/

### 4. New Site Setup (добавление нового сайта)

**Триггеры:** "добавь сайт", "новый проект на REG.ru"

**Процесс:**
1. Получить: домен, хостинг-аккаунт, FTP-креды
2. Добавить хостинг в `CREDENTIALS.md` (если новый аккаунт)
3. Добавить строку в реестр сайтов (этот файл)
4. Проверить FTP доступ: `python3 scripts/ftp-deploy.py --dry-run ...`
5. Настроить DNS → SSL → первый деплой

---

## Справочник документации REG.ru

| Раздел | URL |
|--------|-----|
| База знаний | help.reg.ru/support/ |
| Хостинг | help.reg.ru/support/hosting/ |
| FTP доступ | help.reg.ru/support/hosting/dostupy-i-podklyucheniye-panel-upravleniya-ftp-ssh/ |
| .htaccess | help.reg.ru/support/hosting/fayly-web-config-i-htaccess/ |
| SSL-сертификаты | help.reg.ru/support/ssl-sertifikaty/ |
| DNS-серверы | help.reg.ru/support/dns-servery-i-nastroyka-zony/ |
| Привязка домена | help.reg.ru/support/hosting/privyazka-domena-k-hostingu/ |
| Редиректы | help.reg.ru/support/hosting/redirekty/ |
| REG.API 2.0 | reg.ru/reseller/api2doc |
| Личный кабинет | reg.ru/user/account (dmitryvernale@icloud.com) |

---

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| FTP timeout | Увеличить `--timeout 60`, retry до 3 раз |
| 404 после деплоя | Проверить .htaccess — отсутствует или неправильный RewriteBase |
| Старые assets | Очистить remote `assets/` перед деплоем (`--clean-assets`). Vite хэширует имена |
| Капча в панели | ТОЛЬКО FTP, никогда Playwright для панели REG.ru |
| DNS не работает | Подождать 24–48ч, проверить `dig домен` |
| Redirect loop (301) | DDoS-Guard/proxy делает HTTPS — НЕ добавлять `RewriteCond %{HTTPS}` в .htaccess |
| «Домен не привязан» | Файлы в корне FTP вместо `www/<домен>/`. Document root = `www/xn--domain/` |
| Кириллический домен | Punycode-конвертация (бережная.space → xn--...space) |

---

## Важные ограничения

- REG.ru **НЕ** предоставляет SSH на shared hosting — только FTP
- REG.ru **НЕ** имеет API для файлового менеджера — только FTP для файлов
- REG.API 2.0 — только для доменов, DNS, заказов услуг
- Панель управления защищена Yandex SmartCaptcha — headless-браузер не пройдёт

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
