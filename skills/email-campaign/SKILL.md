---
name: email-campaign
description: "Создание и отправка email-воронок: лид-магнит → прогрев → продажа. Интеграция с SMTP/SendPulse/Mailchimp."
version: 0.1.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-04-02
updated: 2026-04-02
category: marketing
tags: [email, рассылка, воронка, funnel, «email-воронка», «серия писем», «рассылка», SendPulse, Mailchimp, SMTP, «прогрев по email»]
risk: safe
source: crystallized
usage_count: 0
maturity: seed
last_used: null
created_from: "Архитектура универсальных скиллов для капсул Neura"
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "запуск продукта"
proactive_trigger_1_action: "предложить email-воронку"
proactive_trigger_2_type: schedule
proactive_trigger_2_condition: "среда"
proactive_trigger_2_action: "проверить метрики рассылки"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# email-campaign

Создание и отправка email-воронок: лид-магнит → прогрев → продажа. Интеграция с SMTP/SendPulse/Mailchimp.

## Workflow

1. **Настройка провайдера:** SMTP (универсальный) / SendPulse API / Mailchimp API
2. **Создание воронки:** определить этапы (лид-магнит скачан → день 1: знакомство → день 3: кейс → день 7: оффер)
3. **Генерация писем:** copywriting скилл генерирует тексты, auto-funnel — структуру
4. **HTML-шаблоны:** базовый шаблон с брендом клиента (цвета, лого)
5. **Отправка:** по триггерам (время, действие) через выбранный провайдер
6. **Аналитика:** track opens/clicks через pixel + UTM-метки

## Anti-patterns

- НЕ отправлять без DKIM/SPF — письма попадут в спам
- НЕ слать >1 письма в день одному человеку
- НЕ использовать SMTP для >100 получателей — только API (SendPulse/Mailchimp)
- НЕ хранить email-адреса в открытом виде — шифровать или использовать ID провайдера

## Tools

- **auto-funnel** — структура воронки
- **copywriting** — генерация текстов писем
- **smtplib** — Python, отправка через SMTP
- **SendPulse API** — массовая рассылка
- **Mailchimp API** — массовая рассылка

## Конфиг

`funnel-config.json`:
```json
{
  "provider": "sendpulse",
  "from_email": "hello@example.com",
  "funnel_steps": [
    {
      "day": 0,
      "subject_template": "Ваш подарок готов!",
      "body_template": "lead_magnet.html",
      "cta": "Скачать"
    },
    {
      "day": 1,
      "subject_template": "Привет! Давайте познакомимся",
      "body_template": "intro.html",
      "cta": "Подробнее"
    },
    {
      "day": 3,
      "subject_template": "Как {{client_name}} увеличил продажи на 40%",
      "body_template": "case_study.html",
      "cta": "Читать кейс"
    },
    {
      "day": 7,
      "subject_template": "Специальное предложение для вас",
      "body_template": "offer.html",
      "cta": "Получить скидку"
    }
  ]
}
```

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
