"""7-phase onboarding flow for new capsule users.

Transport-agnostic business logic. Telegram handlers delegate here.
State stored in Redis via OnboardingState.

Phases:
  0 — First Contact (welcome + start/skip)
  1 — Self-Diagnosis (capabilities card)
  2 — Interview (questions + Claude parsing)
  3 — Profile Confirmation (show + confirm/edit)
  4 — Integration Checklist (select from catalog)
  5 — Step-by-step Setup (auto + manual integrations)
  6 — Verification + Complete

Ported from v1: neura-capsule/bot/handlers/onboarding.py (767 LOC).
"""
import asyncio
import json
import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from neura.core.capsule import Capsule
from neura.core.engine import ClaudeEngine, EngineConfig
from neura.core.memory import MemoryStore
from neura.provisioning.onboarding_state import OnboardingState
from neura.provisioning.userbot_connect import UserbotConnector

logger = logging.getLogger(__name__)

# Lightweight config for interview parsing (fast + cheap)
PARSE_ENGINE_CONFIG = EngineConfig(
    model="haiku",
    effort="low",
    allowed_tools=[],
    timeout=30,
)

CATALOG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "integration_catalog.json"

# ── Interview Questions ────────────────────────────────────────

INTERVIEW_GROUPS = [
    {
        "title": "\U0001f464 Расскажите о себе",
        "questions": [
            "1. Как вас зовут и чем занимаетесь?",
            "2. Какие задачи хотите делегировать AI?",
        ],
        "fields": ["name", "business"],
    },
    {
        "title": "\U0001f3af Что для вас важно",
        "questions": [
            "3. Какая самая срочная задача прямо сейчас?",
            "4. Есть ли что-то, что AI НЕ должен делать?",
        ],
        "fields": ["urgent_needs", "boundaries"],
    },
]


# ── Catalog Loader ─────────────────────────────────────────────

_catalog_cache: dict | None = None


def _load_catalog() -> dict:
    global _catalog_cache
    if _catalog_cache is not None:
        return _catalog_cache
    if CATALOG_PATH.exists():
        try:
            _catalog_cache = json.loads(CATALOG_PATH.read_text())
            return _catalog_cache
        except Exception as e:
            logger.error(f"Failed to load integration catalog: {e}")
    _catalog_cache = {"integrations": {}, "profiles": {}}
    return _catalog_cache


def _match_profile_type(profile: dict) -> str:
    """Determine best matching profile type from catalog."""
    catalog = _load_catalog()
    profiles = catalog.get("profiles", {})
    business = str(profile.get("business", "")).lower()
    combined = business

    best_match = "default"
    best_score = 0
    for ptype, pdata in profiles.items():
        if ptype == "default":
            continue
        tags = pdata.get("tags", [])
        score = sum(1 for tag in tags if tag.lower() in combined)
        if score > best_score:
            best_score = score
            best_match = ptype
    return best_match


def _get_manual_integrations(state: dict) -> list[dict]:
    """Get list of selected manual (non-auto) integrations."""
    catalog = _load_catalog()
    selected = state.get("integrations", {}).get("selected", [])
    integrations = catalog.get("integrations", {})
    result = []
    for key in selected:
        if key in integrations and not integrations[key].get("auto_setup", False):
            entry = integrations[key].copy()
            entry["key"] = key
            result.append(entry)
    result.sort(key=lambda x: x.get("estimated_minutes", 999))
    return result


def _get_current_manual(state: dict) -> dict | None:
    """Get the current manual integration being set up."""
    manual = _get_manual_integrations(state)
    completed = set(state.get("integrations", {}).get("completed", []))
    deferred = set(state.get("integrations", {}).get("deferred", []))
    done = completed | deferred
    for intg in manual:
        if intg["key"] not in done:
            return intg
    return None


# ── Onboarding Manager ─────────────────────────────────────────

class OnboardingManager:
    """Manages the 7-phase onboarding flow."""

    def __init__(self, state_store: OnboardingState, engine: ClaudeEngine,
                 memory: MemoryStore):
        self._state = state_store
        self._engine = engine
        self._memory = memory
        # Active userbot connectors: {(capsule_id, user_id): UserbotConnector}
        self._connectors: dict[tuple[str, int], UserbotConnector] = {}
        # Background QR wait tasks: {(capsule_id, user_id): asyncio.Task}
        self._qr_tasks: dict[tuple[str, int], asyncio.Task] = {}

    async def _cleanup_user_session(self, cap_id: str, user_id: int) -> None:
        """Cancel QR background task, cleanup connector, remove temp QR files."""
        key = (cap_id, user_id)
        # Cancel background QR task
        task = self._qr_tasks.pop(key, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        # Cleanup QR temp files from state
        try:
            state = await self._state.get(cap_id, user_id)
            if state:
                qr_path = state.get("userbot_qr_path")
                if qr_path:
                    import os
                    try:
                        os.unlink(qr_path)
                    except OSError:
                        pass
        except Exception:
            pass
        # Cleanup connector
        connector = self._connectors.pop(key, None)
        if connector:
            await connector.cleanup()

    async def cleanup_all(self) -> None:
        """Cleanup all active connectors and tasks (called on service stop)."""
        for key in list(self._qr_tasks):
            task = self._qr_tasks.pop(key, None)
            if task and not task.done():
                task.cancel()
        for key in list(self._connectors):
            connector = self._connectors.pop(key, None)
            if connector:
                try:
                    await connector.cleanup()
                except Exception:
                    pass

    # ── Entry Point ────────────────────────────────────────────

    async def should_onboard(self, capsule: Capsule, user_id: int) -> bool:
        """Check if this user should see onboarding."""
        # Capsule must have onboarding enabled
        onb_cfg = capsule.config.trial  # reuse trial dict for now, or check features
        # Check features dict for onboarding flag
        if not capsule.config.features.get("onboarding", False):
            return False
        # Already completed?
        if await self._state.has_completed(capsule.config.id, user_id):
            return False
        return True

    async def handle_start(self, capsule: Capsule, user_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
        """Handle /start — return (text, keyboard) for welcome or resume."""
        cap_id = capsule.config.id
        # Cleanup any active QR session / connector from previous attempt
        await self._cleanup_user_session(cap_id, user_id)
        state = await self._state.get(cap_id, user_id)

        if state and state.get("completed_at"):
            # Already done — personalized welcome
            user_name = state.get("profile", {}).get("name", "").split()[0]
            capsule_name = capsule.config.name
            if user_name:
                return (f"Привет, {user_name}! Я — {capsule_name}. Чем помогу?", None)
            return (f"Привет! Я — {capsule_name}. Чем помогу?", None)

        if state and state.get("phase", 0) >= 6:
            # Phase 6+ reached = auto-complete, don't trap user in resume loop
            await self._state.mark_completed(cap_id, user_id)
            user_name = state.get("profile", {}).get("name", "").split()[0]
            capsule_name = capsule.config.name
            if user_name:
                return (f"Привет, {user_name}! Я — {capsule_name}. Чем помогу?", None)
            return (f"Привет! Я — {capsule_name}. Чем помогу?", None)

        if state and state.get("phase", 0) > 0:
            # Resume earlier phases
            return self._resume_message(state)

        # New user — init state
        await self._state.init(cap_id, user_id)
        text = (
            f"\U0001f44b Привет! Я AI-ассистент {capsule.config.name}.\n\n"
            "Давайте настроим меня под вас — это займёт пару минут.\n"
            "Я покажу свои возможности, познакомлюсь с вами "
            "и подключу нужные инструменты.\n\n"
            "Готовы начать?"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("\u25b6\ufe0f Начать настройку", callback_data="onb:start")],
            [InlineKeyboardButton("\u23ed Пропустить", callback_data="onb:skip")],
        ])
        return text, keyboard

    def _resume_message(self, state: dict) -> tuple[str, InlineKeyboardMarkup]:
        phase = state.get("phase", 0)
        names = {
            1: "диагностику", 2: "знакомство", 3: "подтверждение профиля",
            4: "выбор интеграций", 5: "подключение", 6: "проверку",
        }
        name = names.get(phase, "настройку")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"\u25b6\ufe0f Продолжить {name}",
                                  callback_data=f"onb:resume:{phase}")],
            [InlineKeyboardButton("\U0001f504 Начать заново", callback_data="onb:restart")],
            [InlineKeyboardButton("\u23ed Пропустить", callback_data="onb:skip")],
        ])
        return f"У вас есть незавершённая настройка (фаза: {name}).\nПродолжить?", keyboard

    # ── Callback Router ────────────────────────────────────────

    async def handle_callback(self, capsule: Capsule, user_id: int,
                              data: str) -> tuple[str, InlineKeyboardMarkup | None, str]:
        """Route callback query. Returns (text, keyboard, action).

        action: "edit" (edit current message), "reply" (send new message), "answer" (just answer callback)
        """
        cap_id = capsule.config.id

        # Phase 0: Start
        if data == "onb:start":
            state = await self._state.get(cap_id, user_id)
            if not state:
                state = await self._state.init(cap_id, user_id)
            return await self._phase1_diagnosis(cap_id, user_id, state)

        if data == "onb:skip":
            await self._state.mark_completed(cap_id, user_id)
            text = (
                f"\U0001f44b Готово! Я AI-ассистент {capsule.config.name}.\n\n"
                "\U0001f4cb Команды:\n/start — перезапуск\n\n"
                "\U0001f4ac Просто напишите сообщение!"
            )
            return text, None, "edit"

        if data == "onb:restart":
            await self._cleanup_user_session(cap_id, user_id)
            await self._state.delete(cap_id, user_id)
            state = await self._state.init(cap_id, user_id)
            return await self._phase1_diagnosis(cap_id, user_id, state)

        if data.startswith("onb:resume:"):
            phase = int(data.split(":")[2])
            state = await self._state.get(cap_id, user_id)
            if not state:
                state = await self._state.init(cap_id, user_id)
            return await self._route_to_phase(cap_id, user_id, state, phase)

        # Phase 1 → 2
        if data == "onb:phase2":
            state = await self._state.get(cap_id, user_id)
            if not state:
                return "Ошибка состояния. Отправьте /start", None, "edit"
            return await self._phase2_send_questions(cap_id, user_id, state, 0)

        # Phase 3: confirm / edit
        if data == "onb:confirm":
            state = await self._state.get(cap_id, user_id)
            if not state:
                return "Ошибка. Отправьте /start", None, "edit"
            await self._save_profile(cap_id, user_id, state)
            return await self._phase4_show_checklist(cap_id, user_id, state)

        if data == "onb:edit":
            state = await self._state.get(cap_id, user_id)
            if state:
                state["phase"] = 2
                state["sub_step"] = 0
                await self._state.set(cap_id, user_id, state)
            return ("\u270f\ufe0f Давайте уточним. Ответьте одним сообщением на вопросы ниже.",
                    None, "reply")

        # Phase 4: toggles
        if data.startswith("onb:toggle:"):
            key = data.split(":")[2]
            state = await self._state.get(cap_id, user_id)
            if not state:
                return "Ошибка", None, "answer"
            return self._toggle_integration(state, cap_id, user_id, key)

        if data == "onb:integrations_confirm":
            state = await self._state.get(cap_id, user_id)
            if not state:
                return "Ошибка", None, "edit"
            selected = state.get("integrations", {}).get("selected", [])
            if not selected:
                return "\u26a0\ufe0f Выберите хотя бы одну интеграцию!", None, "answer"
            return await self._phase5_start_setup(cap_id, user_id, state)

        # Phase 5: userbot connection
        if data == "onb:userbot_qr":
            state = await self._state.get(cap_id, user_id)
            if not state:
                return "Ошибка", None, "answer"
            return await self._start_qr_flow(cap_id, user_id, state, capsule)

        if data == "onb:userbot_phone":
            state = await self._state.get(cap_id, user_id)
            if not state:
                return "Ошибка", None, "answer"
            return await self._start_phone_flow(cap_id, user_id, state, capsule)

        if data == "onb:userbot_qr_refresh":
            connector = self._connectors.get((cap_id, user_id))
            if connector:
                result = await connector.recreate_qr()
                if result.get("ok"):
                    state = await self._state.get(cap_id, user_id)
                    if state:
                        state["userbot_qr_path"] = result["qr_path"]
                        await self._state.set(cap_id, user_id, state)
                    return "", None, "qr_refresh"
            return "Ошибка. Начните заново.", None, "reply"

        if data == "onb:userbot_cancel":
            # Cancel QR background task + cleanup connector
            await self._cleanup_user_session(cap_id, user_id)
            state = await self._state.get(cap_id, user_id)
            if state:
                state["userbot_step"] = None
                state["integrations"]["deferred"].append("telegram_userbot")
                state["current_integration_idx"] = state.get("current_integration_idx", 0) + 1
                await self._state.set(cap_id, user_id, state)
            current = _get_current_manual(state) if state else None
            if current:
                text, kb = self._format_integration_instruction(state)
                return text, kb, "reply"
            return await self._phase6_verification(cap_id, user_id, state)

        # Phase 5: integration actions
        if data.startswith("onb:int_"):
            parts = data.split(":")
            action = parts[1].replace("int_", "")  # done, defer, skip
            key = parts[2]
            state = await self._state.get(cap_id, user_id)
            if not state:
                return "Ошибка", None, "answer"
            return await self._handle_integration_action(cap_id, user_id, state, action, key)

        # Phase 6: complete
        if data == "onb:complete":
            await self._state.mark_completed(cap_id, user_id)
            state = await self._state.get(cap_id, user_id)
            profile = state.get("profile", {}) if state else {}
            business = profile.get("business", "")
            if business:
                wow = f"\U0001f4a1 Попробуйте прямо сейчас:\n«Составь план на неделю для {business}»"
            else:
                wow = "\U0001f4a1 Попробуйте прямо сейчас — задайте любой рабочий вопрос!"
            text = (
                f"\u2728 {capsule.config.name} готов к работе!\n\n"
                f"{wow}\n\n"
                "Напишите текст, отправьте голосовое или документ — я помогу."
            )
            return text, None, "reply"

        return "", None, "answer"

    # ── Text Handler (during onboarding) ───────────────────────

    async def handle_text(self, capsule: Capsule, user_id: int,
                          text: str) -> tuple[str, InlineKeyboardMarkup | None] | None:
        """Handle text input during onboarding. Returns (text, keyboard) or None if not in onboarding.

        Intercepts during:
        - Phases 2-3: interview answers
        - Phase 5 with userbot sub-flow: phone, code, 2fa
        """
        cap_id = capsule.config.id
        state = await self._state.get(cap_id, user_id)
        if not state or state.get("completed_at"):
            return None

        phase = state.get("phase", 0)

        # Phases 2-3: interview — intercept text
        if phase in (2, 3):
            return await self._handle_interview_answer(cap_id, user_id, state, text, capsule)

        # Phase 5: userbot connection sub-flow
        if phase == 5:
            userbot_step = state.get("userbot_step")
            if userbot_step in ("phone", "code", "2fa"):
                return await self._handle_userbot_input(cap_id, user_id, state, text, capsule)

        # Phase 6: auto-complete on any text, let it through to normal handler
        if phase >= 6:
            await self._state.mark_completed(cap_id, user_id)
            return None

        # Phases 0, 1, 4: buttons expected — give hint
        if phase in (0, 1, 4):
            return "\U0001f446 Используйте кнопки выше для продолжения настройки.", None

        return None

    # ── Phase 1: Self-Diagnosis ────────────────────────────────

    async def _phase1_diagnosis(self, cap_id: str, user_id: int,
                                state: dict) -> tuple[str, InlineKeyboardMarkup, str]:
        """Show capabilities card."""
        state["phase"] = 1
        await self._state.set(cap_id, user_id, state)

        caps = [
            "\U0001f4ac Текстовые сообщения — задавайте любые вопросы",
            "\U0001f3a4 Голосовые — говорите, я пойму",
            "\U0001f4c4 Документы — PDF, Word, таблицы — проанализирую",
            "\U0001f4f7 Фото — анализ изображений и скриншотов",
            "\U0001f4dd Длинные ответы — статьи, планы, отчёты",
            "\U0001f9e0 Память — запоминаю контекст и учусь у вас",
        ]
        capabilities = "\n".join(caps)

        text = (
            "\u2728 Вот что я умею:\n"
            "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"
            "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
            f"{capabilities}\n"
            "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"
            "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
            "Теперь давайте познакомимся, чтобы я работал именно под вас."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("\u25b6\ufe0f Далее \u2192 Знакомство",
                                  callback_data="onb:phase2")],
        ])
        return text, keyboard, "edit"

    # ── Phase 2: Interview ─────────────────────────────────────

    async def _phase2_send_questions(self, cap_id: str, user_id: int,
                                     state: dict, sub_step: int
                                     ) -> tuple[str, InlineKeyboardMarkup | None, str]:
        """Send interview question group."""
        if sub_step >= len(INTERVIEW_GROUPS):
            return await self._phase3_show_profile(cap_id, user_id, state)

        state["phase"] = 2
        state["sub_step"] = sub_step
        await self._state.set(cap_id, user_id, state)

        group = INTERVIEW_GROUPS[sub_step]
        questions = "\n".join(group["questions"])
        text = (
            f"{group['title']}\n"
            f"(вопросы {sub_step + 1}/{len(INTERVIEW_GROUPS)})\n\n"
            f"{questions}\n\n"
            "\U0001f4ac Ответьте одним сообщением на все вопросы."
        )
        return text, None, "reply"

    async def _handle_interview_answer(self, cap_id: str, user_id: int,
                                       state: dict, text: str,
                                       capsule: Capsule
                                       ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Parse interview answer with Claude (haiku) and advance."""
        sub_step = state.get("sub_step", 0)
        if sub_step >= len(INTERVIEW_GROUPS):
            sub_step = 0

        group = INTERVIEW_GROUPS[sub_step]
        fields = group["fields"]
        questions = "\n".join(group["questions"])

        # Parse with haiku (fast + cheap)
        parse_prompt = (
            f"Извлеки из текста ответы на вопросы.\n\n"
            f"Вопросы:\n{questions}\n\n"
            f"Текст:\n{text}\n\n"
            f"Верни ТОЛЬКО JSON с полями: {json.dumps(fields, ensure_ascii=False)}\n"
            f"Для списков — массив строк. Для текста — строку. Нет данных — null.\n"
            f"Верни ТОЛЬКО JSON."
        )

        parsed = {}
        try:
            result = await self._engine.execute(parse_prompt, PARSE_ENGINE_CONFIG)
            if result.success:
                json_str = result.text.strip()
                # Extract JSON from possible markdown wrapping
                if "```" in json_str:
                    for part in json_str.split("```"):
                        cleaned = part.strip()
                        if cleaned.startswith("json"):
                            cleaned = cleaned[4:].strip()
                        if cleaned.startswith("{"):
                            json_str = cleaned
                            break
                parsed = json.loads(json_str)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Interview parse error: {e}")

        # Fallback: raw text
        if not parsed:
            for field in fields:
                parsed[field] = text if field in ("business", "name") else [text]

        # Update profile
        profile = state.get("profile", {})
        for field in fields:
            if field in parsed and parsed[field] is not None:
                profile[field] = parsed[field]
        state["profile"] = profile
        state["sub_step"] = sub_step + 1
        await self._state.set(cap_id, user_id, state)

        if sub_step + 1 < len(INTERVIEW_GROUPS):
            # Next group
            group2 = INTERVIEW_GROUPS[sub_step + 1]
            questions2 = "\n".join(group2["questions"])
            reply = (
                "\u2705 Принято! Следующая группа вопросов:\n\n"
                f"{group2['title']}\n"
                f"(вопросы {sub_step + 2}/{len(INTERVIEW_GROUPS)})\n\n"
                f"{questions2}\n\n"
                "\U0001f4ac Ответьте одним сообщением."
            )
            return reply, None
        else:
            # All done → show profile
            text_out, kb, _ = await self._phase3_show_profile(cap_id, user_id, state)
            return f"\u2705 Отлично! Вот что я узнал о вас:\n\n{text_out}", kb

    # ── Phase 3: Profile Confirmation ──────────────────────────

    async def _phase3_show_profile(self, cap_id: str, user_id: int,
                                   state: dict) -> tuple[str, InlineKeyboardMarkup, str]:
        """Show collected profile for confirmation."""
        state["phase"] = 3
        await self._state.set(cap_id, user_id, state)

        profile = state.get("profile", {})

        def _fmt(val):
            if val is None:
                return "\u2014"
            if isinstance(val, list):
                return ", ".join(str(v) for v in val) if val else "\u2014"
            return str(val)

        text = (
            "\U0001f4cb Ваш профиль:\n"
            "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"
            "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
            f"\U0001f464 Имя: {_fmt(profile.get('name'))}\n"
            f"\U0001f4bc Занятие: {_fmt(profile.get('business'))}\n"
            f"\u26a1 Срочная задача: {_fmt(profile.get('urgent_needs'))}\n"
            f"\u26d4 Границы: {_fmt(profile.get('boundaries'))}\n"
            "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"
            "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("\u2705 Всё верно", callback_data="onb:confirm"),
                InlineKeyboardButton("\u270f\ufe0f Исправить", callback_data="onb:edit"),
            ],
        ])
        return text, keyboard, "reply"

    async def _save_profile(self, cap_id: str, user_id: int, state: dict) -> None:
        """Save confirmed profile to PostgreSQL memory."""
        profile = state.get("profile", {})
        state["profile_confirmed"] = True
        await self._state.set(cap_id, user_id, state)

        # Save to memory table
        profile_text = "Профиль владельца (из онбординга):\n"
        for key, label in [("name", "Имя"), ("business", "Занятие"),
                           ("urgent_needs", "Срочные задачи"), ("boundaries", "Границы")]:
            val = profile.get(key)
            if val is not None:
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val) if val else "\u2014"
                profile_text += f"- {label}: {val}\n"

        try:
            # Delete previous onboarding profiles (prevent duplicates)
            if hasattr(self._memory, '_pool') and self._memory._pool:
                await self._memory._pool.execute(
                    "DELETE FROM memory WHERE capsule_id = $1 AND source = 'onboarding'",
                    cap_id,
                )
            await self._memory.add_memory(cap_id, profile_text, source="onboarding")
        except Exception as e:
            logger.error(f"Failed to save onboarding profile: {e}")

    # ── Phase 4: Integration Checklist ─────────────────────────

    async def _phase4_show_checklist(self, cap_id: str, user_id: int,
                                     state: dict) -> tuple[str, InlineKeyboardMarkup, str]:
        """Show integration checklist."""
        state["phase"] = 4
        catalog = _load_catalog()
        integrations = catalog.get("integrations", {})

        # Pre-select: auto_setup integrations + telegram_userbot (always recommended)
        auto_keys = [k for k, v in integrations.items() if v.get("auto_setup")]
        if "telegram_userbot" in integrations and "telegram_userbot" not in auto_keys:
            auto_keys.append("telegram_userbot")
        state["integrations"]["selected"] = auto_keys
        await self._state.set(cap_id, user_id, state)

        profile_type = _match_profile_type(state.get("profile", {}))
        profile_labels = {
            "psychologist": "психолога", "manufacturer": "производства",
            "coach": "обучения", "content_creator": "контент-мейкера",
            "beauty": "бьюти-сферы", "therapist": "медицины",
            "designer": "дизайнера", "default": "вашего профиля",
        }
        label = profile_labels.get(profile_type, "вашего профиля")

        text = (
            f"\U0001f50c Интеграции для {label}:\n\n"
            "Отметьте нужные галочкой.\n"
            "Предвыбранные (\u2611) — работают автоматически."
        )
        keyboard = self._build_checklist_keyboard(state)
        return text, keyboard, "reply"

    def _build_checklist_keyboard(self, state: dict) -> InlineKeyboardMarkup:
        """Build toggleable integration checklist."""
        catalog = _load_catalog()
        integrations = catalog.get("integrations", {})
        selected = set(state.get("integrations", {}).get("selected", []))

        profile_type = _match_profile_type(state.get("profile", {}))
        profile_config = catalog.get("profiles", {}).get(profile_type, {})
        hidden = set(profile_config.get("hidden", []))

        difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
        sorted_keys = sorted(
            [k for k in integrations if k not in hidden],
            key=lambda k: (difficulty_order.get(integrations[k].get("difficulty", "hard"), 3),
                           integrations[k].get("estimated_minutes", 99)),
        )

        rows = []
        for key in sorted_keys:
            intg = integrations[key]
            check = "\u2611" if key in selected else "\u2610"
            minutes = intg.get("estimated_minutes", "?")
            label = f"{check} {intg['icon']} {intg['name']} (~{minutes} мин)"
            rows.append([InlineKeyboardButton(label, callback_data=f"onb:toggle:{key}")])

        rows.append([InlineKeyboardButton("\u2705 Подтвердить выбор",
                                          callback_data="onb:integrations_confirm")])
        return InlineKeyboardMarkup(rows)

    def _toggle_integration(self, state: dict, cap_id: str, user_id: int,
                            key: str) -> tuple[str, InlineKeyboardMarkup | None, str]:
        """Toggle integration selection. Returns answer text + updated keyboard."""
        selected = state.get("integrations", {}).get("selected", [])
        if key in selected:
            selected.remove(key)
        else:
            selected.append(key)
        state["integrations"]["selected"] = selected

        # Need to save state asynchronously — caller handles it
        # We return a marker for the caller
        catalog = _load_catalog()
        name = catalog.get("integrations", {}).get(key, {}).get("name", key)
        check = "\u2611" if key in selected else "\u2610"

        keyboard = self._build_checklist_keyboard(state)
        return f"{check} {name}", keyboard, "toggle"

    # ── Phase 5: Step-by-step Setup ────────────────────────────

    async def _phase5_start_setup(self, cap_id: str, user_id: int,
                                  state: dict) -> tuple[str, InlineKeyboardMarkup | None, str]:
        """Begin step-by-step integration setup."""
        state["phase"] = 5
        state["current_integration_idx"] = 0
        catalog = _load_catalog()
        integrations = catalog.get("integrations", {})

        selected = state.get("integrations", {}).get("selected", [])
        auto_completed = [k for k in selected if integrations.get(k, {}).get("auto_setup")]
        state["integrations"]["completed"] = auto_completed
        await self._state.set(cap_id, user_id, state)

        parts = []
        if auto_completed:
            names = [f"{integrations[k]['icon']} {integrations[k]['name']}" for k in auto_completed]
            parts.append("\u2705 Автоматически подключено:\n" + "\n".join(f"  \u2022 {n}" for n in names))

        manual = _get_manual_integrations(state)
        if not manual:
            parts.append("\nВсе интеграции подключены!")
            text, kb, action = await self._phase6_verification(cap_id, user_id, state)
            return "\n".join(parts) + "\n\n" + text, kb, action

        intg_text, intg_kb = self._format_integration_instruction(state)
        parts.append(intg_text)
        return "\n\n".join(parts), intg_kb, "reply"

    def _format_integration_instruction(self, state: dict) -> tuple[str, InlineKeyboardMarkup]:
        """Format instruction for current manual integration."""
        current = _get_current_manual(state)
        if not current:
            return "Все интеграции настроены!", InlineKeyboardMarkup([])

        key = current["key"]
        manual = _get_manual_integrations(state)
        completed = set(state.get("integrations", {}).get("completed", []))
        deferred = set(state.get("integrations", {}).get("deferred", []))
        done_count = len([m for m in manual if m["key"] in (completed | deferred)])
        total = len(manual)

        # Special handling: Telegram Userbot — QR + phone code
        if key == "telegram_userbot":
            text = (
                f"\U0001f50c Интеграция {done_count + 1}/{total}: \u2709\ufe0f Telegram Userbot\n\n"
                "Подключу ваш Telegram — смогу читать каналы, "
                "пересылать сообщения и отвечать от вашего имени.\n\n"
                "Выберите способ подключения:"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("\U0001f4f2 QR-код (рекомендуется)",
                                      callback_data="onb:userbot_qr")],
                [InlineKeyboardButton("\U0001f4f1 По номеру телефона",
                                      callback_data="onb:userbot_phone")],
                [
                    InlineKeyboardButton("\u23ed Позже", callback_data=f"onb:int_defer:{key}"),
                    InlineKeyboardButton("\u274c Пропустить", callback_data=f"onb:int_skip:{key}"),
                ],
            ])
            return text, keyboard

        # Default: show steps from catalog
        steps = current.get("setup_steps", [])
        steps_text = "\n".join(
            f"  {'📌' if s.get('type') == 'action' else 'ℹ️'} {s['text']}"
            for s in steps
        )

        text = (
            f"\U0001f50c Интеграция {done_count + 1}/{total}: {current['icon']} {current['name']}\n\n"
            f"\U0001f4cb Инструкция:\n{steps_text}\n\n"
            f"\u23f1 ~{current.get('estimated_minutes', '?')} минут"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("\u2705 Готово", callback_data=f"onb:int_done:{key}"),
                InlineKeyboardButton("\u23ed Позже", callback_data=f"onb:int_defer:{key}"),
                InlineKeyboardButton("\u274c Пропустить", callback_data=f"onb:int_skip:{key}"),
            ],
        ])
        return text, keyboard

    # ── Userbot Connection Sub-flow ────────────────────────────

    # ── QR Flow ─────────────────────────────────────────────────

    async def _start_qr_flow(self, cap_id: str, user_id: int,
                             state: dict, capsule: Capsule
                             ) -> tuple[str, InlineKeyboardMarkup | None, str]:
        """Start QR code login. Returns text + QR image path."""
        home = capsule.config.home_dir or f"/tmp/neura-homes/{cap_id}"
        connector = UserbotConnector(home, cap_id)
        self._connectors[(cap_id, user_id)] = connector

        result = await connector.request_qr()
        if result.get("error"):
            state["userbot_step"] = None
            await self._state.set(cap_id, user_id, state)
            return f"\u274c {result['error']}", InlineKeyboardMarkup([
                [InlineKeyboardButton("\U0001f504 Попробовать снова",
                                      callback_data="onb:userbot_qr")],
            ]), "reply"

        state["userbot_step"] = "qr_waiting"
        state["userbot_qr_path"] = result["qr_path"]
        await self._state.set(cap_id, user_id, state)

        text = (
            "\U0001f4f2 Сканируйте QR-код для подключения Telegram:\n\n"
            "1\ufe0f\u20e3 Откройте Telegram на телефоне\n"
            "2\ufe0f\u20e3 Настройки \u2192 Устройства \u2192 Привязать устройство\n"
            "3\ufe0f\u20e3 Наведите камеру на QR-код\n\n"
            "\u23f3 QR действует 2 минуты"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("\U0001f504 Обновить QR", callback_data="onb:userbot_qr_refresh")],
            [InlineKeyboardButton("\u274c Отмена", callback_data="onb:userbot_cancel")],
        ])
        # "qr_send" action = caller must send QR image + text
        return text, keyboard, "qr_send"

    async def start_qr_background_wait(self, cap_id: str, user_id: int,
                                       capsule: Capsule, bot, chat_id: int):
        """Background task: wait for QR scan, then notify user."""
        connector = self._connectors.get((cap_id, user_id))
        if not connector:
            return

        result = await connector.wait_for_qr_scan(timeout=120)

        if result.get("ok"):
            # Success!
            state = await self._state.get(cap_id, user_id)
            if state:
                text_msg, _ = await self._userbot_success(cap_id, user_id, state, result)
                await bot.send_message(chat_id, text_msg)
            return

        if result.get("2fa"):
            state = await self._state.get(cap_id, user_id)
            if state:
                state["userbot_step"] = "2fa"
                await self._state.set(cap_id, user_id, state)
            await bot.send_message(
                chat_id,
                "\U0001f510 QR отсканирован! У вас включена 2FA.\n\nВведите пароль:",
            )
            return

        if result.get("expired"):
            # Try to recreate QR
            if connector:
                new_qr = await connector.recreate_qr()
                if new_qr.get("ok"):
                    state = await self._state.get(cap_id, user_id)
                    if state:
                        state["userbot_qr_path"] = new_qr["qr_path"]
                        await self._state.set(cap_id, user_id, state)
                    await bot.send_message(chat_id, "\u23f3 QR обновлён. Сканируйте заново:")
                    with open(new_qr["qr_path"], "rb") as f:
                        await bot.send_photo(chat_id, f)
                    # Restart wait (tracked for cleanup)
                    task = asyncio.create_task(
                        self.start_qr_background_wait(cap_id, user_id, capsule, bot, chat_id)
                    )
                    self._qr_tasks[(cap_id, user_id)] = task
                    return

            await bot.send_message(chat_id, "\u274c QR истёк. Нажмите /start чтобы попробовать снова.")

    # ── Phone Code Flow ────────────────────────────────────────

    async def _start_phone_flow(self, cap_id: str, user_id: int,
                                state: dict, capsule: Capsule
                                ) -> tuple[str, InlineKeyboardMarkup | None, str]:
        """Start phone code login."""
        state["userbot_step"] = "phone"
        await self._state.set(cap_id, user_id, state)

        text = (
            "\U0001f4f1 Подключение по номеру телефона\n\n"
            "Отправьте номер, привязанный к вашему Telegram.\n"
            "Формат: +79991234567"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("\u274c Отмена", callback_data="onb:userbot_cancel")],
        ])
        return text, keyboard, "reply"

    async def _handle_userbot_input(self, cap_id: str, user_id: int,
                                    state: dict, text: str, capsule: Capsule
                                    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Handle phone/code/2fa text input during userbot connection."""
        step = state.get("userbot_step", "")
        connector_key = (cap_id, user_id)

        if step == "phone":
            phone = text.strip().replace(" ", "").replace("-", "")
            if not phone.startswith("+"):
                return "\u26a0\ufe0f Номер должен начинаться с + (например +79991234567)", None

            home = capsule.config.home_dir or f"/tmp/neura-homes/{cap_id}"
            connector = UserbotConnector(home, cap_id)
            self._connectors[connector_key] = connector

            result = await connector.request_code(phone)
            if result.get("error"):
                state["userbot_step"] = None
                await self._state.set(cap_id, user_id, state)
                return f"\u274c {result['error']}", InlineKeyboardMarkup([
                    [InlineKeyboardButton("\U0001f504 Попробовать снова",
                                          callback_data="onb:userbot_phone")],
                    [InlineKeyboardButton("\U0001f4f2 Попробовать QR",
                                          callback_data="onb:userbot_qr")],
                ])

            state["userbot_step"] = "code"
            # Store phone on connector (NOT in Redis — PII protection)
            connector._user_phone = phone
            await self._state.set(cap_id, user_id, state)

            return (
                f"\u2705 Код отправлен на {phone[:5]}***\n\n"
                "\U0001f511 Введите 5-значный код из приложения Telegram.\n"
                "(Не из уведомления о входе, а из отдельного сообщения от «Telegram»)"
            ), InlineKeyboardMarkup([
                [InlineKeyboardButton("\u274c Отмена", callback_data="onb:userbot_cancel")],
            ])

        elif step == "code":
            code = text.strip().replace(" ", "").replace("-", "")
            connector = self._connectors.get(connector_key)

            if not connector:
                state["userbot_step"] = None
                await self._state.set(cap_id, user_id, state)
                return "\u26a0\ufe0f Сессия потеряна. Начните заново.", InlineKeyboardMarkup([
                    [InlineKeyboardButton("\U0001f504 Заново", callback_data="onb:userbot_phone")],
                ])

            # Phone stored on connector, not in Redis (PII protection)
            phone = getattr(connector, '_user_phone', '')
            if not phone:
                state["userbot_step"] = None
                await self._state.set(cap_id, user_id, state)
                return "\u26a0\ufe0f Номер утерян. Начните заново.", InlineKeyboardMarkup([
                    [InlineKeyboardButton("\U0001f504 Заново", callback_data="onb:userbot_phone")],
                ])

            result = await connector.sign_in_code(phone, code)

            if result.get("error"):
                return f"\u274c {result['error']}", InlineKeyboardMarkup([
                    [InlineKeyboardButton("\u274c Отмена", callback_data="onb:userbot_cancel")],
                ])

            if result.get("2fa"):
                state["userbot_step"] = "2fa"
                await self._state.set(cap_id, user_id, state)
                return (
                    "\U0001f510 Двухфакторная авторизация.\n\nВведите пароль 2FA:"
                ), InlineKeyboardMarkup([
                    [InlineKeyboardButton("\u274c Отмена", callback_data="onb:userbot_cancel")],
                ])

            return await self._userbot_success(cap_id, user_id, state, result)

        elif step == "2fa":
            connector = self._connectors.get(connector_key)
            if not connector:
                state["userbot_step"] = None
                await self._state.set(cap_id, user_id, state)
                return "\u26a0\ufe0f Сессия потеряна.", InlineKeyboardMarkup([
                    [InlineKeyboardButton("\U0001f504 Заново", callback_data="onb:userbot_qr")],
                ])

            result = await connector.sign_in_2fa(text.strip())
            if result.get("error"):
                return f"\u274c {result['error']}", InlineKeyboardMarkup([
                    [InlineKeyboardButton("\u274c Отмена", callback_data="onb:userbot_cancel")],
                ])

            return await self._userbot_success(cap_id, user_id, state, result)

        return None

    async def _userbot_success(self, cap_id: str, user_id: int,
                               state: dict, result: dict
                               ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Userbot connected successfully."""
        connector_key = (cap_id, user_id)
        self._connectors.pop(connector_key, None)

        name = result.get("name", "")
        uid = result.get("user_id", "")
        state["userbot_step"] = None
        state["integrations"]["completed"].append("telegram_userbot")
        state["current_integration_idx"] = state.get("current_integration_idx", 0) + 1
        await self._state.set(cap_id, user_id, state)

        text = (
            f"\u2705 Telegram подключён!\n"
            f"\U0001f464 {name} (ID: {uid})\n\n"
            "Теперь агент может читать каналы и отправлять сообщения от вашего имени."
        )

        # Check if more integrations
        current = _get_current_manual(state)
        if current:
            next_text, next_kb = self._format_integration_instruction(state)
            return f"{text}\n\n{next_text}", next_kb
        else:
            # Move to phase 6
            return text, InlineKeyboardMarkup([
                [InlineKeyboardButton("\u25b6\ufe0f Далее", callback_data="onb:int_done:_finish")],
            ])

    async def _handle_integration_action(self, cap_id: str, user_id: int,
                                         state: dict, action: str, key: str
                                         ) -> tuple[str, InlineKeyboardMarkup | None, str]:
        """Handle done/defer/skip for an integration."""
        catalog = _load_catalog()
        name = catalog.get("integrations", {}).get(key, {}).get("name", key)

        if action == "done":
            state["integrations"]["completed"].append(key)
            answer = f"\u2705 {name} подключён!"
        elif action in ("defer", "skip"):
            state["integrations"]["deferred"].append(key)
            answer = f"\u23ed {name} отложен" if action == "defer" else f"\u274c {name} пропущен"

        state["current_integration_idx"] = state.get("current_integration_idx", 0) + 1
        await self._state.set(cap_id, user_id, state)

        current = _get_current_manual(state)
        if current:
            text, kb = self._format_integration_instruction(state)
            return text, kb, "reply"
        else:
            return await self._phase6_verification(cap_id, user_id, state)

    # ── Phase 6: Verification ──────────────────────────────────

    async def _phase6_verification(self, cap_id: str, user_id: int,
                                   state: dict) -> tuple[str, InlineKeyboardMarkup, str]:
        """Show final status. Auto-marks as completed."""
        state["phase"] = 6
        await self._state.set(cap_id, user_id, state)
        # Auto-complete: phase 6 = onboarding done, button is just UX
        await self._state.mark_completed(cap_id, user_id)

        catalog = _load_catalog()
        integrations = catalog.get("integrations", {})
        completed = state.get("integrations", {}).get("completed", [])
        deferred = state.get("integrations", {}).get("deferred", [])

        lines = ["\U0001f3c1 Онбординг завершён!\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"]
        for key in completed:
            intg = integrations.get(key, {})
            lines.append(f"\u2705 {intg.get('icon', '')} {intg.get('name', key)}")
        for key in deferred:
            intg = integrations.get(key, {})
            lines.append(f"\u23f8 {intg.get('icon', '')} {intg.get('name', key)} (отложено)")
        lines.append("\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501")

        profile = state.get("profile", {})
        business = profile.get("business", "")
        if business:
            lines.append(f"\n\U0001f4a1 Попробуйте: «Найди последние тренды в {business}»")
        else:
            lines.append("\n\U0001f4a1 Попробуйте задать любой вопрос!")

        text = "\n".join(lines)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("\U0001f680 Начать работу", callback_data="onb:complete")],
        ])
        return text, keyboard, "reply"

    # ── Route Helper ───────────────────────────────────────────

    async def _route_to_phase(self, cap_id: str, user_id: int,
                              state: dict, phase: int) -> tuple[str, InlineKeyboardMarkup | None, str]:
        """Route to a specific phase (for resume)."""
        if phase == 1:
            return await self._phase1_diagnosis(cap_id, user_id, state)
        elif phase == 2:
            return await self._phase2_send_questions(cap_id, user_id, state, state.get("sub_step", 0))
        elif phase == 3:
            return await self._phase3_show_profile(cap_id, user_id, state)
        elif phase == 4:
            return await self._phase4_show_checklist(cap_id, user_id, state)
        elif phase == 5:
            text, kb = self._format_integration_instruction(state)
            return text, kb, "reply"
        elif phase == 6:
            return await self._phase6_verification(cap_id, user_id, state)
        return "Отправьте /start для начала.", None, "reply"
