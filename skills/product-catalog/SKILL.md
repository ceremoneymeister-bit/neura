---
name: product-catalog
description: "This skill should be used when managing product catalogs: intake from TG/photos, CRUD, variants, pricing, search, descriptions. Proactive: detects new media, suggests cataloging, seasonal hints, upsell."
version: 2.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-04-03
updated: 2026-04-03
category: business
tags: [каталог, товар, продукт, цена, варианты, фото, intake, «сколько стоит», «покажи товары», каталогизация, «разложи по категориям»]
risk: safe
source: internal
usage_count: 0
maturity: seed
last_used: null
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "новые товары/услуги"
proactive_trigger_1_action: "обновить каталог"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# product-catalog

## Purpose

Unified skill for end-to-end product catalog management. Claude IS the brain: classification, pricing, descriptions, deduplication, cross-sell, seasonal logic — all inline, no scripts needed. The only required script is `product-db.py` for SQLite persistence across sessions. Replaces the former `catalog-organizer` and `product-manager` seed skills.

## When to Use

- "Разложи фото по категориям" / "Каталогизируй"
- "Сколько стоит?" / "Покажи товары" / "Прайс-лист"
- "Добавь товар" / "Удали товар" / "Обнови цену"
- "Найди товар по тегу/категории/цене"
- "Сгенерируй описание для товара"
- "Экспорт каталога в PDF/Excel"
- "Какие товары предложить к свече?" (upsell/cross-sell)
- "Подготовь сезонную подборку"
- Client forwards photos/videos to the bot for cataloging

## Core Workflow

### Phase 1 — Intake (media -> raw catalog entries)

**Claude inline** + existing script.

1. Determine the source: local folder path, TG channel ID, or forwarded media in bot chat.
2. For **local folder**: scan recursively for files matching `jpg|jpeg|png|webp|mp4|mov|heic`. Batch into groups of 20 (hard limit — Claude times out above 50).
3. For **TG channel**: run `python3 scripts/tg-download-channel-media.py --channel {{CHANNEL_ID}}` to pull media. Script EXISTS at `scripts/tg-download-channel-media.py`.
4. For **forwarded media**: the bot handler saves the file to `assets/inbox/` and triggers intake for that single file.
5. **Decision gate**: if zero new files found, report "No new media" and stop.

### Phase 2 — Classification

**Claude inline.** No scripts needed — Claude does this with vision + reasoning.

1. For each image: use the Read tool to analyze visual content. Extract: subject, material, estimated category, color palette, distinguishing features.
2. For each video: use `batch-transcription` skill to get transcript, then Claude summarizes the product shown.
3. Match against categories in `config/categories.json`. If file doesn't exist — ask operator to define initial categories or propose them based on the analyzed content. If no confident match — propose a new category and await confirmation.
4. **Deduplication gate** (Claude inline): compare new entry against existing catalog by (a) exact file hash (SHA-256 via bash `sha256sum`), (b) name similarity (Claude compares strings, no library needed). If duplicate found, skip and log.
5. Generate suggested `name`, `tags[]`, and `category` for each item.

### Phase 3 — Product Record Creation (CRUD)

**Two storage modes** (auto-detect):

**Mode A — SQLite (recommended, if `product-db.py` exists):**
1. For each classified item: `python3 scripts/product-db.py create --name "X" --category "Y" --base-price 1200 --tags '["a","b"]'`.
2. Search: `python3 scripts/product-db.py search --query "Лотос"` or `--category "свечи"` or `--tag "воск"`.
3. Update: `python3 scripts/product-db.py update --id 5 --base-price 1500`.
4. Delete: `python3 scripts/product-db.py delete --id 5`.
5. Export: `python3 scripts/product-db.py export --format json > /tmp/catalog.json`.

**Mode B — JSON fallback (if `product-db.py` not available):**
1. Store catalog in `data/catalog.json` (create on first use via Write tool).
2. Read via Read tool, update via Edit tool.
3. JSON format: `{"products": [{...schema...}]}` — same schema as SQLite mode.
4. This mode works immediately, no setup required. Migrate to SQLite later by importing JSON.

**For both modes:**
5. Product schema (see full schema below) includes: name, category, base_price (nullable until set), variants[], stock_status, tags[], photos[], description.
6. If base_price is unknown, set `stock_status = "made_to_order"` and flag for human pricing.
7. **Decision gate**: present a summary table to the operator — "12 products created, 3 need pricing, 2 duplicates skipped. Confirm or edit?"

### Phase 4 — Description Generation

**Claude inline.** Text generation is a core capability.

1. Load brand voice profile from `config/brand-voice.json` if it exists. If not — use `brand-voice-clone` skill (`.agent/skills/brand-voice-clone/`) to extract style from the client's TG channel, or ask operator to describe the desired tone.
2. For each product without a description, Claude generates text using the brand voice profile. Include: key features, materials, use cases, emotional hook.
3. Generate platform-specific variants: TG post (short), Instagram caption (medium + hashtags), website card (structured).
4. Store all variants in `descriptions` JSON field of the product record via `product-db.py update`.

### Phase 5 — Pricing & Variants

**Claude inline.** Price calculation is arithmetic — no script needed.

1. For each product, define variants as first-class records: `{variant_id, product_id, attribute, value, price_delta, stock_status}`.
2. Example: product "Свеча Лотос" -> variants: `[{color: "белый", +0}, {color: "золотой", +200}, {size: "большая", +500}]`.
3. Price calculation (Claude computes): `final_price = base_price + SUM(selected_variant.price_delta) + delivery_option.price`.
4. Store variants via `product-db.py update --product_id X --variants '[...]'`.

### Phase 6 — Export & Delivery

**Uses existing skills.**

1. **Price list PDF**: use `notion-pdf` skill (`.agent/skills/notion-pdf/`).
2. **Price list Excel**: use `excel-xlsx` skill (`.agent/skills/excel-xlsx/`).
3. **TG delivery**: send the file via bot response using `[FILE:/tmp/pricelist_...]` marker in Claude's reply (the bot handler picks it up). For direct sending outside bot context: `python3 scripts/tg-send.py {{CLIENT_TG}} "Прайс-лист готов"` + attach file path. Script EXISTS at `scripts/tg-send.py`.

## Tools & Scripts

### What Claude Does Inline (no scripts needed)

| Capability | How |
|-----------|-----|
| Category classification | Vision (Read tool on images) + reasoning |
| Description generation | Text generation with brand voice profile |
| Price calculation | Arithmetic: base + variant deltas + delivery |
| Deduplication by name | String comparison, no Levenshtein library needed |
| Seasonal suggestions | Calendar knowledge (Claude knows what month it is) |
| Cross-sell recommendations | Category/tag reasoning over catalog data |
| FAQ answers | Knowledge base reasoning |

### Required Scripts

| Script | Status | Purpose |
|--------|--------|---------|
| `scripts/product-db.py` | EXISTS | SQLite CRUD: create, read, update, delete, search, export. Persistence across sessions. |

**Fallback without script:** Claude works directly with `data/catalog.json` via Read/Write tools. All features work, only persistence format differs (JSON vs SQLite).

### Existing Tools Used

| Tool | Path | Purpose |
|------|------|---------|
| `tg-download-channel-media.py` | `scripts/tg-download-channel-media.py` | Pull media from TG channels (Phase 1) |
| `tg-send.py` | `scripts/tg-send.py` | Send files/messages to TG users (Phase 6) |
| `notion-pdf` skill | `.agent/skills/notion-pdf/` | Export catalog to PDF |
| `excel-xlsx` skill | `.agent/skills/excel-xlsx/` | Export catalog to Excel |
| `brand-voice-clone` skill | `.agent/skills/brand-voice-clone/` | Load brand voice profile |
| `batch-transcription` skill | `~/.claude/skills/batch-transcription/` | Video transcription during intake |

### Future Automation (Phase 3, TODO)

| Item | Priority | Description |
|------|----------|-------------|
| `tg-channel-watcher.py` | SHOULD | Cron: detect new media in monitored channels, notify operator. Requires `cron-guardian` slot. |
| `export-pricelist.py` | NICE | Wrapper that queries `product-db.py` + calls `notion-pdf`/`excel-xlsx`. Convenience, not essential — Claude can orchestrate manually. |
| Conversion tracking | NICE | Store view/inquiry/purchase events per product. Requires integration with bot analytics. |
| Description A/B analysis | NICE | Compare conversion rates between description styles. Requires conversion tracking first. |

## Proactive Behaviors

### New Media Detection
- **При вызове скилла**: when operator asks "что нового в канале?" — Claude runs `tg-download-channel-media.py`, classifies, reports.
- **Требует cron-скрипт (TODO)**: `tg-channel-watcher.py` for automatic 30-min polling. Needs `cron-guardian` slot.

### Seasonal Suggestions
- **При вызове скилла**: Claude knows the current date. When catalog is queried, Claude checks if seasonal products exist and suggests: "Сезон {{SEASON}}! У тебя есть {{N}} подходящих товаров."
- No cron needed — triggers naturally during catalog interactions.

### Upsell / Cross-sell
- **При вызове скилла**: when a customer asks about product X, Claude reads the catalog, finds related products by category/tags, and appends: "К этому часто берут: {{RELATED_PRODUCT}} ({{PRICE}})."
- No script needed — pure reasoning over catalog data.

### Low Stock Alert
- **При вызове скилла**: during any catalog query, Claude checks `stock_status`. If `low_stock` items found, appends warning: "Внимание: {{PRODUCT}} — остаток на исходе."
- No script needed — reads directly from `product-db.py read`.

## Self-Learning (Feedback Loops)

### Description Quality Tracking
- **Claude tracks via diary/logs**: after generating descriptions, log which style was used (storytelling, feature-list, emotional). When operator reports "это описание зашло" or "переделай" — Claude updates its preference model in the session diary.
- **Требует скрипт (TODO)**: automated conversion tracking needs bot-side event logging + analytics script.

### FAQ Expansion
- **Claude tracks via diary/logs**: when bot chat contains product questions that Claude couldn't answer confidently, log to diary. On next skill invocation, review unanswered questions and suggest FAQ additions.
- No script needed — Claude reviews its own interaction history.

### Competitive Monitoring
- **При вызове скилла**: when `competitive-ads-extractor` skill produces data, Claude can cross-reference with catalog on request. Flag: price gaps, missing categories, trending products.
- No automated sync — operator triggers comparison manually.

## Product Schema

```json
{
  "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
  "name": "TEXT NOT NULL",
  "category": "TEXT NOT NULL",
  "base_price": "REAL",
  "stock_status": "TEXT CHECK(stock_status IN ('in_stock','low_stock','out_of_stock','made_to_order')) DEFAULT 'in_stock'",
  "description": "TEXT",
  "descriptions_multi": "JSON — {tg: str, instagram: str, website: str}",
  "tags": "JSON — ['str']",
  "photos": "JSON — ['path']",
  "variants": "JSON — [{variant_id, attribute, value, price_delta, stock_status}]",
  "source_channel": "TEXT — TG channel ID if intake from channel",
  "file_hash": "TEXT — SHA-256 for dedup",
  "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
  "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP"
}
```

**Variant sub-schema:**
```json
{
  "variant_id": "TEXT — uuid4",
  "attribute": "TEXT — e.g. 'color', 'size', 'material'",
  "value": "TEXT — e.g. 'золотой', 'большая', 'воск соевый'",
  "price_delta": "REAL — added to base_price",
  "stock_status": "TEXT — same enum as parent product",
  "sku": "TEXT — optional external SKU"
}
```

## Anti-Patterns

1. **Batch overflow**: DO NOT process more than 20 files per batch. Split into sequential batches of 20 with a flush between them.

2. **Hardcoded categories**: DO NOT embed category names in skill logic. Always read from `config/categories.json`. Different clients have completely different taxonomies.

3. **Ignoring deduplication**: DO NOT skip the dedup gate. TG channels frequently contain reposts and similar angles. Without dedup, catalogs bloat 2-3x.

4. **Price without variants**: DO NOT return a single price when the product has variants. Always ask which variant, or show a range: "от {{MIN}} до {{MAX}} руб."

5. **Exposing internal IDs**: DO NOT show SQLite row IDs or UUIDs to end customers. Use product names and human-readable slugs.

6. **Stale stock status**: DO NOT trust `in_stock` indefinitely. If not updated in 30+ days, flag as "статус не подтверждён" and prompt operator.

7. **Auto-publishing descriptions**: DO NOT auto-publish generated descriptions without operator review. Always present for approval.

8. **Monolithic export**: DO NOT export the entire catalog when client asks for "прайс на свечи". Filter by requested category first.

9. **Phantom scripts**: DO NOT reference scripts that don't exist. If a script is needed but not yet created, mark it explicitly as TODO.

## Config Template

Create `config/product-catalog.json` in the capsule root:

```json
{
  "client_name": "{{CLIENT_NAME}}",
  "brand_voice_profile": "config/brand-voice.json",
  "categories_file": "config/categories.json",
  "db_path": "data/catalog.db",
  "monitored_channels": ["{{TG_CHANNEL_ID_1}}"],
  "intake_batch_size": 20,
  "dedup_enabled": true,
  "stock_stale_days": 30,
  "export_formats": ["pdf", "xlsx"],
  "description_auto_publish": false
}
```

`config/categories.json` example:

```json
{
  "categories": [
    {"id": "candles", "name_ru": "Свечи", "keywords": ["свеча", "воск", "ароматическая"]},
    {"id": "workshops", "name_ru": "Мастер-классы", "keywords": ["МК", "мастер-класс", "обучение"]},
    {"id": "decor", "name_ru": "Декор", "keywords": ["декор", "интерьер", "украшение"]}
  ]
}
```

Replace all `{{PLACEHOLDERS}}` with actual values during capsule deployment. No client-specific data lives in this skill file.

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
