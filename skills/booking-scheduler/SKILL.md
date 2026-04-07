---
name: booking-scheduler
description: "This skill should be used when managing bookings for master classes, consultations, workshops. Handles scheduling, reminders, cancellations, waitlist. Proactive: fill rate alerts, seasonal suggestions."
version: 2.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-04-02
updated: 2026-04-03
category: integration
tags: [запись, бронирование, мастер-класс, МК, консультация, booking, расписание, «запиши на», «хочу на МК», «записаться», «ближайший МК», воркшоп, йога]
risk: low
source: internal
usage_count: 0
maturity: seed
last_used: null
proactive_enabled: true
proactive_trigger_1_type: threshold
proactive_trigger_1_condition: "записей на неделю < 2"
proactive_trigger_1_action: "предложить рассылку/напоминание"
proactive_trigger_2_type: event
proactive_trigger_2_condition: "новый МК/воркшоп"
proactive_trigger_2_action: "настроить запись"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# booking-scheduler v2 — Claude-centric

## 1. Purpose

Manage the full booking lifecycle for {{EVENT_TYPES}} (master classes, consultations, workshops, yoga sessions) through a Telegram bot. Claude IS the brain: intent detection, slot lookup, booking creation, cancellation, waitlist, analytics — all happen inline when Claude processes a message. Only time-triggered actions (reminders, recurring event creation) require cron scripts.

## 2. When to Use

Activate this skill when any of these triggers appear:

- Client writes "хочу на МК", "запиши на", "записаться", "ближайший МК", "свободные даты"
- Client asks to cancel or reschedule a booking
- Client asks about price, payment status, or available spots
- Operator requests booking dashboard, fill rates, or revenue summary
- System detects a full event and needs to manage waitlist
- Seasonal calendar event approaches (8 March, New Year, etc.)

## 3. Core Workflow

### Phase 0 — Event Creation (Claude inline, operator only)

**Trigger:** Operator says "создай МК", "открой запись", "новое событие", "добавь консультацию".

0a. Parse operator request for event parameters: name, date/time, duration, max_participants, price.
0b. If recurring: parse recurrence rule (e.g., "каждую субботу в 14:00" → `weekly:saturday:14:00`).
0c. Create the event record:
   - **Google Calendar mode:** create event via Calendar API with title, time, description.
   - **Local JSON mode:** append to `{{CAPSULE_PATH}}/data/booking/events.json`:
   ```json
   {"event_id": "mk-2026-04-15", "type_id": "mk-candles", "date": "2026-04-15", "time": "14:00", "duration_min": 120, "max_participants": 8, "current_participants": 0, "price": 3000, "status": "open"}
   ```
0d. If `events.json` doesn't exist — create it with `{"events": []}` via Write tool.
0e. If `booking-config.json` doesn't exist — create it from the Config Template (Section 10), filling in values from operator's request.
0f. Confirm to operator: "МК создан: [название], [дата] [время], макс [N] человек, [цена] руб."

**Bootstrap:** On first use of the skill, Phase 0 runs automatically — Claude creates config + first event from operator's instructions.

---

### Phase 1 — Intent Detection (Claude inline)
1. Parse the client message for booking intent (record, cancel, reschedule, query). Claude does this natively — no script needed.
2. Identify event type from {{EVENT_TYPES}} list. If ambiguous, present options as inline buttons.
3. If intent is "cancel" or "reschedule", jump to Section 5.

### Phase 2 — Slot Lookup (Claude inline)
4. Read the storage backend:
   - **Google Calendar mode:** Claude reads events via inline Python (`google-oauth` skill provides the token, Claude uses `google.oauth2` + `googleapiclient` to call Calendar API). The bot must have `google-api-python-client` installed.
   - **Local JSON mode:** Claude reads `{{CAPSULE_PATH}}/data/booking/events.json` directly via Read tool.
5. Filter out events where `current_participants >= max_participants` (show only available slots).
6. If zero available slots exist, offer waitlist (Phase 5) and show the next date with openings.
7. Present available dates/times as Telegram inline buttons (max 6 options per message).

### Phase 3 — Booking Creation (Claude inline)
8. Client selects a date. Confirm with a summary: event name, date, time, duration, price, spots remaining.
9. Wait for explicit client confirmation ("Да", button tap, or equivalent).
10. Create the booking record:
    - Google Calendar: add attendee to event via API.
    - Google Sheets: append row (client_name, tg_id, event_id, date, status=confirmed, payment_status, timestamp).
    - Local JSON fallback: append to `bookings.json` with same schema.
11. Increment `current_participants` counter.
12. Send confirmation message to client with event details and payment link (if applicable).

### Phase 4 — Reminders (cron script REQUIRED)
13. `booking-reminder.py` runs every hour via cron. Checks events within the next 24 hours.
14. For each upcoming event, sends reminder to all confirmed attendees who have not yet been reminded (via `tg-send.py`).
15. Marks `reminder_sent=true` in the booking record to prevent duplicates.

**Why cron:** Claude is not invoked on a schedule. Reminders must fire whether or not anyone is chatting with the bot.

### Phase 5 — Waitlist (Claude inline)
16. When `current_participants >= max_participants`, offer: "Мест нет. Записать в лист ожидания?"
17. On confirmation, create a waitlist entry (client_name, tg_id, event_id, position, timestamp).
18. When a cancellation frees a spot, Claude notifies the first person on the waitlist immediately within the cancellation flow.
19. Give the waitlisted client 2 hours to confirm. If no response, move to the next person.

### Phase 6 — Recurring Event Creation (cron script REQUIRED)
20. `booking-recurrence.py` runs daily at 06:00 via cron. Looks 14 days ahead and creates missing events per `recurrence_rule` in config.
21. Checks for existing events on the target date before creating (prevents duplicates).

**Why cron:** Recurring events must appear on the calendar even if nobody interacted with the bot that day.

## 4. Booking Lifecycle

```
CREATE → CONFIRM → REMIND (24h before) → ATTEND → FEEDBACK
  |         |          |                     |         |
  |         |          |                     |         └─ Post-event: ask "Как вам МК? (1-5)"
  |         |          |                     └─ Mark attended=true in Sheets/JSON
  |         |          └─ Cron: booking-reminder.py → TG message
  |         └─ Client taps "Да" → record created (Claude inline)
  └─ Bot shows slots → client selects (Claude inline)
```

## 5. Cancel/Reschedule Rules

### Cancellation (Claude inline)
- Client can cancel **no later than 24 hours before** the event start time.
- If within 24h window: deny cancellation, explain the policy, offer to find a replacement.
- On successful cancellation: set `status=cancelled`, decrement `current_participants`, trigger waitlist notification.
- If `payment_status=paid`: notify operator about refund needed, do NOT auto-refund.

### Reschedule (Claude inline)
- Treat as cancel + new booking in a single flow.
- Apply the same 24h rule to the original event.
- Show available alternative dates immediately after cancellation confirmation.
- Preserve payment status if rescheduling to an event with the same price.

### Operator Override
- Operator ({{CLIENT_NAME}}) can cancel/reschedule at any time regardless of the 24h rule via HQ group command: `/cancel_booking <booking_id>` or `/reschedule_booking <booking_id>`.

## 6. Storage

### Mode A: Google Calendar + Sheets (when `google-oauth` connected)
- Events: Google Calendar events (read/write via Google Calendar API).
- Bookings: Google Sheets tab "Bookings" (client_name, tg_id, event_id, date, status, payment_status, timestamp).
- Analytics: Google Sheets tab "Analytics".
- Use `google-oauth` skill for auth. Pattern similar to `scripts/icloud_calendar.py`.

### Mode B: Local JSON (fallback, no Google)
- `{{CAPSULE_PATH}}/data/booking/events.json` — event definitions and recurrence rules.
- `{{CAPSULE_PATH}}/data/booking/bookings.json` — all booking records.
- `{{CAPSULE_PATH}}/data/booking/waitlist.json` — waitlist entries.
- `{{CAPSULE_PATH}}/data/booking/booking-analytics.json` — metrics.
- Create directory on first use. Display notice to operator: "Google не подключён. Работаю в локальном режиме."

### Config
`{{CAPSULE_PATH}}/booking-config.json` at the capsule root.

## 7. Tools & Scripts

### What Claude does inline (no scripts needed)
- Intent detection — natural language understanding
- Slot lookup — reads events from Google Calendar or local JSON
- Booking creation — writes to Google Sheets or local JSON
- Cancel/reschedule — applies business rules, updates records
- Waitlist management — FIFO queue logic, inline notifications on cancellation
- Dashboard (`/booking_dashboard`) — reads data, summarizes fill rates, revenue, waitlist counts
- Seasonal suggestions — calendar knowledge, suggests themed events when holidays approach
- Feedback collection — asks post-event rating, stores in booking record
- Analytics queries — reads booking history, computes fill speed, cancellation patterns when asked

### Required cron scripts (MUST exist)
| Script | Purpose | Trigger | Status |
|--------|---------|---------|--------|
| `booking-reminder.py` | Send TG reminders to confirmed attendees for events within 24h | Cron: hourly | EXISTS (120 lines) |
| `booking-recurrence.py` | Auto-create recurring events 14 days ahead per recurrence rules | Cron: daily 06:00 | EXISTS (120 lines) |

Both scripts need Telegram delivery. **In Antigravity context:** use `tg-send.py` (sends as Dmitry's userbot). **In capsule context:** use Bot API via the capsule's bot token (the script must detect its environment). Read/write the same storage (Google or local JSON).

### Existing tools used
| Tool | Path | Purpose |
|------|------|---------|
| `tg-send.py` | `scripts/tg-send.py` | Send Telegram messages (reminders, confirmations) |
| `icloud_calendar.py` | `scripts/icloud_calendar.py` | iCloud CalDAV integration (NOT Google Calendar — different API, for reference only) |
| `google-oauth` skill | `.agent/skills/google-oauth/` | Google Calendar + Sheets auth |

### Future automation (Phase 3, TODO)
- `booking-proactive.py` — daily cron for fill rate alerts, low-fill warnings to HQ group. Currently Claude checks fill rate when asked.
- `booking-analytics.py` — weekly cron for automated analytics report. Currently Claude computes analytics on demand.
- `booking-migrate.py` — one-time migration from local JSON to Google after OAuth connect.

## 8. Proactive Behaviors

### При вызове скилла (Claude inline)
| Trigger | Condition | Action |
|---------|-----------|--------|
| Fill rate check | Operator asks about bookings or runs `/booking_dashboard` | Claude computes fill rates and alerts if < 30% |
| Waitlist promotion | Cancellation frees a spot | Claude notifies next-in-line immediately |
| Seasonal suggestion | Operator asks about upcoming events and a holiday is within 3 weeks | Claude suggests themed event |

### Требует cron-скрипт (TODO — не реализовано)
| Trigger | Condition | Script needed |
|---------|-----------|---------------|
| Pre-event fill check | Event in 24h, confirmations < max | `booking-proactive.py` |
| Low fill alert | Event in 7 days, registrations < 30% | `booking-proactive.py` |
| Weekly analytics digest | Every Sunday 20:00 | `booking-analytics.py` |

## 9. Self-Learning

Claude tracks patterns from booking history **when asked**. No automated weekly analytics yet.

### What Claude can do now (inline)
- **Fill speed analysis:** Compare `created_at` vs `filled_at` by day-of-week. "Субботние МК заполняются за 2 дня, вторник — за неделю."
- **Cancellation patterns:** Aggregate cancellation timing relative to event start. Suggest extra reminders if >30% cancel in last 24h.
- **Pricing impact:** Compare fill rate by price point. Suggest keeping higher price if fill rate unchanged.
- **Feedback scores:** Aggregate post-event ratings (1-5) per event type. Flag events with avg < 3.5.

### TODO — automated analytics
- Weekly cron report to HQ group (`booking-analytics.py` — не написан).
- Auto-detect anomalies (sudden drop in bookings, spike in cancellations).

## 10. Event Config Schema

Store in `booking-config.json` at the capsule root:

```json
{
  "event_types": [
    {
      "id": "mk-candles",
      "name": "Мастер-класс по свечам",
      "category": "мастер-класс",
      "duration_min": 120,
      "max_participants": 10,
      "price": 3000,
      "currency": "RUB",
      "payment_link": "https://pay.example.com/mk-candles",
      "reminder_hours": [24, 2],
      "recurrence_rule": "weekly:saturday:14:00",
      "recurrence_end": "2026-12-31",
      "location": "Студия, ул. Примерная, 10",
      "instructor": "{{CLIENT_NAME}}",
      "waitlist_enabled": true,
      "auto_create_recurring": true,
      "feedback_enabled": true,
      "tags": ["свечи", "хендмейд"]
    }
  ],
  "global_settings": {
    "cancel_min_hours": 24,
    "waitlist_confirm_hours": 2,
    "timezone": "Europe/Moscow",
    "storage_backend": "google",
    "fallback_storage": "local_json",
    "seasonal_holidays": [
      {"name": "8 Марта", "date": "03-08", "lead_weeks": 3},
      {"name": "Новый год", "date": "12-20", "lead_weeks": 4},
      {"name": "День матери", "date": "11-24", "lead_weeks": 3}
    ]
  }
}
```

### Recurrence Rule Format
`<frequency>:<day>:<time>` — frequency is `weekly` or `monthly`, day is lowercase English day name or day-of-month (1-28), time is HH:MM in configured timezone.

## 11. Anti-Patterns

1. **Never create a booking without explicit client confirmation.** Show summary, wait for "Да" or button tap.
2. **Never book when slots are full.** Re-check `current_participants < max_participants` after confirmation, before writing.
3. **Never send a reminder for a cancelled event.** Check `status != cancelled` before every reminder dispatch.
4. **Never store data only in memory.** Persist to Google Sheets or local JSON immediately.
5. **Never auto-refund payments.** Notify operator. Only the operator initiates refunds.
6. **Never send proactive messages directly to clients.** All proactive alerts go to HQ group first.
7. **Never allow cancellation within 24h without operator override.** Enforce `cancel_min_hours`.
8. **Never hardcode event types, prices, or participant limits.** All values from `booking-config.json`.
9. **Never skip the waitlist queue.** FIFO order. No new client books ahead of the waitlist.
10. **Never create duplicate recurring events.** Check for existing events on the target date before creating.
11. **Never reference a script that does not exist.** Mark unwritten scripts as "TODO — не написан".

## 12. Fallback Mode (No Google)

When Google OAuth is not connected:
1. Store all data in local JSON files (see Section 6, Mode B).
2. Slot lookup reads from `events.json` instead of Google Calendar.
3. Cron scripts (`booking-reminder.py`, `booking-recurrence.py`) read/write local JSON.
4. When Google OAuth is later connected, migrate local data to Google (manual or `booking-migrate.py` — TODO).
5. Display one-time notice: "Google не подключён. Работаю в локальном режиме. Данные сохранятся и синхронизируются при подключении."

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
