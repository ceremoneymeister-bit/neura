---
name: neura-reels
description: This skill should be used when creating Reels/Shorts scripts for selling Neura AI agent service. It generates ready-to-film scripts with hooks, timings, visual directions, and CTAs optimized for converting entrepreneurs into Neura clients.
version: 4.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-03-19
updated: 2026-04-01
category: content
tags: [reels, video, sales, neura, short-form, instagram, tiktok, youtube-shorts]
risk: safe
source: internal
usage_count: 1
last_used: 2026-04-01
maturity: seed
---

# neura-reels

## Purpose

Generate ready-to-film Reels scripts that sell Neura AI agent service to entrepreneurs. Each script includes: hook with psychological trigger, timed structure, visual directions, on-screen text, voiceover text, and CTA with conversion mechanism. Built on Maxim Belousov's brand voice and Neura product DNA.

## When to Use

Activate this skill when:
- User asks to create a Reel/Short script for Neura
- User says "рилс", "reels", "сценарий", "сними видео", "контент для Instagram/TikTok/Shorts"
- User wants video content to sell AI agent services
- User needs a content batch (multiple scripts at once)

Do NOT use when:
- Writing text posts for Telegram/VK (use `social-content` instead)
- Creating long-form video (> 90 seconds) or YouTube tutorials
- Working on written sales copy (use `copywriting` instead)

## Dependent Skills

Before generating, load and apply principles from:
- `viral-reels-psychology` — attention mechanics, retention, viral triggers
- `marketing-psychology` — behavioral science for CTA design
- `copywriting` — claim discipline, feature→benefit→outcome

## Core Workflow

### Phase 1: Brief — Determine Script Parameters

Ask or infer these parameters:

| Parameter | Options | Default |
|-----------|---------|---------|
| **Format** | Demo / Myth / Story / Proof / Challenge / Meta-AI / Niche-Lifehack / Showcase | Demo |
| **Duration** | 15s / 30s / 45s / 60s / 90s | 45s |
| **Hook type** | See `references/hooks-catalog.md` | Auto-select |
| **Audience niche** | General entrepreneurs / specific niche | General |
| **CTA type** | Comment-trigger / DM / Link-in-bio / Follow | Comment-trigger |
| **Filming style** | Face-to-camera / Screen-record / Split / Mixed | Mixed |

If user provides a topic/idea — map it to the closest format. If user says "сделай рилс" without details — generate 3 different scripts using different formats.

**Idea-to-Script flow:** When user says "вот идея" / "можно сделать рилс про..." — сохрани идею в `references/ideas-bank.md` + сразу определи формат и сгенерируй сценарий. Идеи не должны теряться.

**Decision gate:** Parameters confirmed (explicitly or by default).

### Phase 2: Script Generation

Load `references/product-dna.md` for factual accuracy.
Load `references/brand-voice.md` for tone calibration.
Load `references/script-templates.md` for the chosen format template.
Load `references/hooks-catalog.md` for hook selection.
Load `references/sound-and-energy.md` for energy curve + WPS limits.
Load `references/platform-rules.md` for platform-specific adaptations.

Generate the script using this structure:

```
## [НАЗВАНИЕ РИЛСА] — [формат], [длительность]

### Хук: [тип хука из каталога]
> Психологический триггер: [какой механизм задействован]

---

### СЦЕНАРИЙ

[ТАЙМИНГ] ВИЗУАЛ | ГОЛОС | ТЕКСТ НА ЭКРАНЕ

[0-3 сек]
📹 {что в кадре}
🎙️ "{точный текст голосом}"
📝 {текст на экране — крупно, контрастно}

[3-8 сек]
📹 {что в кадре}
🎙️ "{точный текст}"
📝 {текст на экране}

... продолжение по секундам ...

[последние 5-7 сек]
📹 {что в кадре}
🎙️ "{CTA текст}"
📝 {CTA на экране + визуал}

---

### Монтажные указания
- Переходы: {тип}
- Музыка: {рекомендация}
- Субтитры: {стиль}
- Loop point: {как зациклить}

### CTA-механика
- Триггерное слово: {СЛОВО}
- Что происходит после комментария: {описание воронки}

### Хештеги
{3-5 хештегов}
```

**Rules during generation:**
1. Every sentence in voiceover ≤ 9 words (for oral delivery)
2. Visual change every 2-3 seconds minimum
3. At least 1 open loop in first 5 seconds
4. Peak moment (strongest insight) at 60-70% of duration
5. CTA only in last 15-20% of duration
6. Never start with "Привет" or self-introduction
7. Always include at least one concrete metric (time, money, quantity)
8. Always contrast Neura with the "old way" (ChatGPT, freelancers, manual work)
9. Use Maxim's voice patterns from `references/brand-voice.md`
10. All product claims must be factually grounded — see `references/product-dna.md`

**Decision gate:** Script generated. Proceed to scoring.

### Phase 2.5: Validation — Before Scoring

Run these **binary checks** (pass/fail). If ANY fails — fix before scoring:

| # | Check | How to verify |
|---|-------|---------------|
| 1 | **WPS limit** | Count all words in 🎙️ lines. Compare with limit from `references/sound-and-energy.md`. FAIL if over |
| 2 | **Open loop in 0-5 sec** | Re-read first 5 seconds. Is there a question the viewer needs answered? |
| 3 | **No "Привет" or self-intro** | First word is NOT greeting |
| 4 | **Peak at 60-70%** | Strongest moment is at ~60-70% of duration |
| 5 | **CTA in last 15-20%** | CTA does NOT appear before 80% mark |
| 6 | **Concrete metric** | At least 1 number (time, money, quantity) |
| 7 | **Visual change ≤ 3 sec** | No single camera angle longer than 3 seconds |
| 8 | **Loop point exists** | Last frame visually connects to first frame |
| 9 | **Energy curve assigned** | Curve A/B/C from `references/sound-and-energy.md` marked |
| 10 | **No banned words** | Check against `references/brand-voice.md` "НЕ используй" list |

**All 10 must PASS. No exceptions.**

### Phase 3: Quality Scoring

Score each script on 7 axes (1-10):

| Axis | What to evaluate |
|------|-----------------|
| **Hook Power** | Will it stop the scroll in < 1.5 seconds? Pattern interrupt present? |
| **Retention** | Open loops? Micro-tension every 3-5 sec? Peak moment clear? |
| **Clarity** | Short sentences? Concrete? No jargon? Would a non-tech person understand? |
| **Sales Power** | Does it create desire for Neura? Is the contrast clear? Is the CTA actionable? |
| **Filmability** | Can Maxim film this alone with a phone? Are visual directions clear? |
| **Brand Fit** | Does it sound like Maxim? Direct, proof-first, no fluff? |
| **Viral Potential** | Save-worthy? Share-worthy? Will people tag friends? Rewatch triggers? |

**Thresholds:**
- **≥ 56/70** — Ready to film
- **45-55/70** — Good, minor polish needed
- **< 45/70** — Rework required

If any single axis < 6 — fix that axis specifically before delivering.

**Anti-bias rule:** When scoring your own script, ask for each axis: "Would a viewer with NO context about Neura still score this ≥ 7?" If not — the score is inflated.

### Phase 4: Delivery

Output the final script with:
1. The complete script (Phase 2 format)
2. Validation checklist (Phase 2.5) — all 10 checks with pass/fail
3. Score card (Phase 3)
4. **Instagram caption** (see below)
5. **Cover text** — 3-5 слов для обложки (see `references/platform-rules.md`)
6. **Energy curve** — какая кривая (A/B/C) + голосовые маркеры в сценарии
7. "Shooting checklist" — 5-7 bullet points for Maxim to prepare before filming
8. Optional: 2-3 alternative hooks for A/B testing
9. Optional: Platform adaptations (TikTok shorter version, YouTube description)

### Caption Generation (для Instagram)

Генерируй caption по формуле:

```
[Хук-строка — то, что видно до "ещё..." (≤ 125 символов)]

[Развитие — 2-3 предложения с ценностью или историей]

[CTA — "Напиши [СЛОВО] в комментариях" или "Сохрани, чтобы не потерять"]

[Хештеги — 3-5 штук по стратегии из platform-rules.md]
```

**Правила caption:**
- Первая строка = hook (видна без клика). Должна вызывать желание развернуть
- НЕ дублировать voiceover дословно — дополнять
- Emoji: 0-2 максимум. Не "🔥🚀💥" на каждой строке
- Вопрос в конце caption → буст комментариев

### Rewatch Triggers

В каждом сценарии включить минимум 1 rewatch trigger:

| Trigger | Как работает | Пример |
|---------|-------------|--------|
| **Speed text** | Текст на экране мелькает на 0.5 сек — зритель не успевает прочитать → пересматривает | Мелкий текст "а ты уже попробовал?" на сек 25 |
| **Hidden detail** | Деталь в скринкасте, которую замечаешь только при повторе | Другие чаты в Telegram с названиями задач |
| **Callback** | Финал ссылается на начало — зритель хочет проверить | "То, что ты смотришь — создал он" (ссылка на хук) |
| **Counter-intuitive** | Факт, который заставляет пересмотреть в контексте | Ценовой якорь: зритель пересматривает демо, думая "серьёзно, за 2 минуты?" |

## Strategy: Content Mix for Maximum Growth

Оптимальная стратегия публикаций — три типа контента в миксе:

### 1. Продающие рилсы (40% контента)
Форматы: Demo, Myth, Story, Proof, Challenge, Split, While You Sleep, Rapid Fire, Showcase
Цель: конверсия в лиды (комментарий → DM → тест-драйв)
Метрика: комментарии с триггерным словом, DM

### 2. Viral лайфхаки (30% контента)
Формат: Niche Lifehack (Format 8)
Цель: максимальный охват, saves, shares → рост подписчиков
Метрика: просмотры, saves, новые подписчики
**PROOF:** Рилс "доступ к нейросетям через App Store" = 200k+ просмотров, 1000+ подписчиков

### 3. Мета-AI контент (20% контента)
Формат: Meta-AI (Format 7)
Цель: wow-эффект, позиционирование, viral через "inception"
Метрика: shares, комментарии "как?!", saves

### 4. Эксперименты (10% контента)
Новые форматы, коллабы, тренды. Тестировать и замерять.

## Batch Planning (недельное планирование)

При запросе "контент на неделю" / "план рилсов" — генерировать пакет по формуле:

**7 рилсов/неделю:**
| День | Тип | Формат | Цель |
|------|-----|--------|------|
| Пн | Продающий | Speed Demo (1) | Конверсия |
| Вт | Лайфхак | Niche Lifehack (8) | Охват |
| Ср | Продающий | Myth Destroyer (2) | Авторитет |
| Чт | Мета | Meta-AI (7) | Wow |
| Пт | Продающий | Client Story (3) | Доверие |
| Сб | Лайфхак | Niche Lifehack (8) | Охват |
| Вс | Продающий | Showcase (9) | Конверсия |

**Правила серии:**
- Никогда 2 одинаковых формата подряд
- Никогда 2 одинаковых хука подряд
- Лайфхаки = Вт и Сб (пиковые дни discovery)
- Мета = Чт (середина недели, "отдых" от продажи)
- Каждая неделя начинается с самого сильного рилса (понедельник = демо)

## Idea Bank

Идеи для рилсов собираются в `references/ideas-bank.md`. Процесс:
1. Пользователь кидает идею (голосом, текстом, ссылкой)
2. Агент сохраняет идею в банк с датой и предложенным форматом
3. При запросе "сгенерируй рилс" — можно выбрать из банка или создать новый
4. После генерации — идея помечается как "✅ сценарий готов"

## Anti-Patterns

1. **Feature dump** — Listing Neura's features without showing outcomes. "113 скиллов, векторная база, Claude Opus" means nothing to the viewer. Show what these features DO: "За 2 минуты — рабочий сайт для твоего бизнеса"
2. **Tutorial mode** — Teaching viewers how to use AI instead of showing what Neura does for them. Tutorials build audience. Demos build pipeline. This skill generates demos, not tutorials
3. **Generic hooks** — "5 способов использовать ИИ в бизнесе" — scrolled past instantly. Every hook must be specific, surprising, or contradictory. See `references/hooks-catalog.md`
4. **Overproduction** — Studio lighting, corporate graphics, transitions = lower trust. Phone camera + screen recording + natural voice = higher trust for AI/tech content
5. **Selling in the reel** — The reel's job is NOT to sell. It generates a micro-commitment (comment/DM). The sale happens in the funnel after. Never mention price in the reel. **Исключение:** в 90-секундных Showcase-рилсах допускается ценовой рефрейм ("стоимость 2 кофе в день") через технику «5 пальцев» — но НИКОГДА конкретная цифра
6. **Ignoring loop point** — The last visual frame must connect to the first frame. Seamless loops increase watch time 40-60%, which triggers algorithmic distribution
7. **Weak endings** — Peak-End Rule (Kahneman): people remember the peak and the end. Never end on a whimper. The final line must be the most memorable

## Proven Viral Case Studies

### Case 1: "Доступ к нейросетям через App Store" (Дмитрий)
- **Формат:** Niche Lifehack (скринкаст + voice over)
- **Тема:** Как получить доступ к ChatGPT/Claude в России, когда подписка Apple не позволяет сменить регион Apple ID
- **Результат:** 200k+ просмотров, 1000+ новых подписчиков
- **Почему залетел:** Узкая проблема (Apple ID + подписки + регион) × огромная аудитория (все iPhone в РФ) × пошаговое решение = максимальный save + share
- **Урок:** Лайфхак-контент НЕ продаёт напрямую, но приводит массовую аудиторию, из которой конвертируется часть

### Принцип из кейса:
Чем УЖЕ и КОНКРЕТНЕЕ проблема — тем ШИРЕ охват (парадокс). "Как использовать AI" = никто не смотрит. "Как обойти блокировку Apple ID без потери подписок" = 200k.

## Selling Frameworks (НЕЧ20, Пыриков, Тимочко)

### Техника «5 пальцев» — закрытие в Reels (60-90 сек)

Используй в последних 15-20% продающего рилса. Каждый «палец» = 1 предложение, максимум 2. Порядок строгий.

| # | Палец | Что делает | Пример для Neura |
|---|-------|-----------|-----------------|
| 1 | **Суммируйте выгоды** | Recap того, что зритель только что увидел | "Ты только что видел, как агент за 2 минуты сделал анализ конкурентов, написал пост и ответил клиенту" |
| 2 | **Цена в контексте** | Сравнить стоимость с чем-то обыденным | "За стоимость одного ужина в ресторане — у тебя сотрудник, который работает 24/7" |
| 3 | **Добавьте бонус** | Неожиданный довесок, который не ожидали | "А ещё — настрою под твою нишу бесплатно в первую неделю" |
| 4 | **Создайте срочность** | Ограничение по времени/местам | "Беру только 5 клиентов в месяц. Два места уже заняты" |
| 5 | **Снимите риск** | Убрать страх потери денег | "Не подойдёт — просто не продлевай. Без договоров и штрафов" |

**Когда применять:** Format 9 (Showcase), Format 1 (Speed Demo), Format 4 (Number Proof) — любые продающие рилсы 60+ секунд.
**Когда НЕ применять:** Lifehack (Format 8), Meta-AI (Format 7) — там не продаём.

### OTO 7-блочная структура — для длинных рилсов (90 сек)

Для showcase-рилсов и развёрнутых демо. Каждый блок = чёткий тайминг.

| # | Блок | Тайминг | Что происходит | Энергия |
|---|------|---------|---------------|---------|
| 1 | **Hook** | 0-3 сек | Pattern interrupt. Шок, вопрос, парадокс | 🔴 Максимум |
| 2 | **Problem** | 3-10 сек | Боль зрителя, конкретная ситуация | 🟡 Напряжение |
| 3 | **Solution intro** | 10-20 сек | "Вот что реально работает" — без деталей | 🟢 Надежда |
| 4 | **Demo/proof** | 20-50 сек | Показать продукт в действии, скринкаст | 🟢→🔴 Нарастание |
| 5 | **Results** | 50-65 сек | Цифры, before/after, конкретика | 🔴 Пик (Peak Moment) |
| 6 | **Offer** | 65-80 сек | Что получает зритель + ценовой контекст | 🟡 Уверенность |
| 7 | **CTA** | 80-90 сек | Закрытие по «5 пальцев» (сжато) | 🔴 Финал |

**Правило:** Блок 4 (Demo) = самый длинный. Здесь зритель должен увидеть РЕАЛЬНЫЙ результат, не рассказ о нём. Скринкаст > слова.

### CTA Amplification — 3 метода усиления призыва (НЕЧ20)

Применять ПЕРЕД финальным CTA для увеличения конверсии. Можно комбинировать 2 из 3.

#### 1. Stack Benefits (стэк выгод)
Перед CTA — перечислить 3 конкретных результата. Не фичи, а исходы.

```
🎙️ "Он отвечает клиентам за 5 секунд.
     Он пишет посты в твоём стиле.
     Он работает, пока ты спишь.
     Напиши АГЕНТ — покажу как."
```

**Почему работает:** Зритель соглашается с каждым пунктом → micro-yes → легче совершить действие.

#### 2. Price Reframe (ценовой рефрейм)
Сравнить стоимость с чем-то тривиальным. Число должно быть МАЛЕНЬКИМ.

```
🎙️ "Стоимость двух кофе в день — а у тебя сотрудник без выходных."
```

**Формулы:**
- "За стоимость [мелочь] — [большой результат]"
- "[X] рублей в день — это [что это даёт]"
- "Дешевле чем [привычная трата] — но [в 10 раз ценнее]"

#### 3. Risk Reversal (снятие риска)
Убрать барьер. Зритель должен почувствовать: "мне нечего терять".

```
🎙️ "Не понравится — просто не продлевай. Без договоров."
```

**Формулы:**
- "Тест-драйв бесплатно. Не подойдёт — ничего не должен"
- "Первая неделя — за мой счёт"
- "Никаких контрактов. Уйти можно в любой момент"

### Лестница Ханта — Batch Planning (недельный цикл по Пырикову)

Альтернативная система планирования контента на неделю. Каждый день = своя ступень осведомлённости зрителя.

| День | Ступень | Тип контента | Пример для Neura |
|------|---------|-------------|-----------------|
| Пн | **Ниша** | Почему AI важен, тренд индустрии | "К 2027 году 40% бизнесов без AI закроются. Вот почему" |
| Вт | **Эксперт** | Tutorial, behind-the-scenes создания AI | "Как я настраиваю агента за 30 минут — закулисье" |
| Ср | **Продукт** | Feature showcase, живое демо | Speed Demo: клиент пишет → агент отвечает за 5 сек |
| Чт | **Возражения** | "Дорого?", "Сложно?", "А если не сработает?" | Myth Destroyer: "AI-агент — это только для больших компаний" |
| Пт | **Продажа** | Прямой CTA, оффер, отзыв клиента | Showcase с «5 пальцев» + триггерное слово |

**Когда использовать вместо основного Batch Planning:**
- Если аудитория Максима "холодная" (мало знает о AI-агентах)
- Если нужно прогреть перед запуском/вебинаром
- Если недельный цикл — 5 рилсов (рабочие дни), а не 7

**Можно комбинировать** с основным планом (см. секцию Batch Planning выше): Пн-Пт по лестнице Ханта, Сб-Вс — лайфхаки для охвата.

### Банк инфоповодов — AI-специфические триггеры для рилсов (Тимочко)

10 типов инфоповодов, которые генерируют идеи для рилсов. При запросе "о чём снять рилс?" — пройтись по списку и найти актуальный.

| # | Инфоповод | Формат | Пример |
|---|-----------|--------|--------|
| 1 | **Выход новой модели** (GPT/Claude/Gemini update) | Meta-AI / Lifehack | "Claude 4 вышел. Вот что изменилось для бизнеса за 24 часа" |
| 2 | **AI-регулирование / новости** | Myth Destroyer | "Закон об AI в России. Что это значит для тебя?" |
| 3 | **Провал / успех конкурента** | Story / Proof | "Один бизнесмен заменил 3 сотрудников ботом. Через месяц уволил бота. Почему?" |
| 4 | **Milestone клиента** | Number Proof / Story | "Мой клиент заработал первые 100к с помощью AI-агента. Вот его история" |
| 5 | **Before/After трансформация** | Speed Demo / Showcase | "ДО: 4 часа на ответы клиентам. ПОСЛЕ: 0 минут. Всё автоматически" |
| 6 | **"Я ошибался насчёт..."** (myth-busting) | Myth Destroyer | "Я 3 месяца говорил что ChatGPT хватит всем. Я ошибался. Вот почему" |
| 7 | **Сравнение инструментов** (live test) | Challenge | "ChatGPT vs Neura-агент. Одна задача. Кто быстрее?" |
| 8 | **Speed Challenge** (AI vs человек) | Challenge | "Фрилансер vs AI-агент. 10 задач. Засекаем время" |
| 9 | **День с AI** (day-in-the-life) | Meta-AI / Showcase | "Я не трогал телефон весь день. AI-агент вёл мой бизнес. Результат?" |
| 10 | **Горячий прогноз** (hot take) | Myth Destroyer | "Через 2 года профессия SMM-менеджера исчезнет. Серьёзно" |

**Как использовать:** При генерации пакета рилсов — проверить: есть ли сейчас актуальный инфоповод из списка? Если да — один рилс в пакете должен быть привязан к нему. Инфоповоды дают буст к просмотрам на 20-40% (по данным Тимочко).

Идеи на основе инфоповодов сохранять в `references/ideas-bank.md` с тегом `[ИНФОПОВОД]`.

## Источники фреймворков

- **НЕЧ20** — продающее видео: техника «5 пальцев», CTA Amplification, OTO 7-блочная структура
- **Пыриков** — лестница Ханта для контент-планирования (5-дневный цикл прогрева)
- **Тимочко** — банк инфоповодов, триггеры для AI-контента

## References

- `references/hooks-catalog.md` — 28 hook formulas in 9 categories (incl. RF-specific)
- `references/script-templates.md` — 9 format templates with timings
- `references/product-dna.md` — Neura facts, metrics, and claims library
- `references/brand-voice.md` — Maxim's communication patterns and voice rules
- `references/filming-guide.md` — How to film each format with a phone
- `references/sound-and-energy.md` — Energy curves, sound design, WPS validation
- `references/platform-rules.md` — Instagram/TikTok/YouTube rules, hashtags, covers
- `references/ideas-bank.md` — Raw ideas for future scripts
