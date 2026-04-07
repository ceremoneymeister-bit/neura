"""ProactiveEngine — background task that checks skill triggers.

@arch scope=platform  affects=capsules_with_proactive
@arch depends=core.skills (SkillRegistry), PostgreSQL, Redis
@arch risk=MEDIUM  restart=neura-v2
@arch role=Evaluates proactive triggers every 30min. Logs + alerts + sends messages.
@arch note=Dedup: same skill max 1x per 6h. Schedule eval in MSK timezone.
@arch status=Phase 4 — triggers evaluate correctly, message delivery active.

Periodically evaluates proactive triggers for all enabled skills.
Trigger types: silence, threshold, schedule, event.
Actions: log to skill_usage, send alert to HQ, deliver message via capsule bot.
"""
import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 1800  # 30 minutes


class ProactiveEngine:
    """Background engine that evaluates proactive skill triggers."""

    def __init__(self, skill_registry, db_pool, redis_client,
                 alert_sender=None, metrics_collector=None,
                 capsules: dict | None = None,
                 interval: int = DEFAULT_INTERVAL):
        self._registry = skill_registry
        self._pool = db_pool
        self._redis = redis_client
        self._alert = alert_sender
        self._metrics = metrics_collector
        self._capsules = capsules or {}  # capsule_id -> Capsule (for message delivery)
        self._interval = interval
        self._task: asyncio.Task | None = None
        self._fired: dict[str, datetime] = {}  # skill_name -> last fired time (dedup)

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"ProactiveEngine started (interval={self._interval}s)")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ProactiveEngine stopped")

    async def _run_loop(self) -> None:
        await asyncio.sleep(60)  # initial delay — let system stabilize
        while True:
            try:
                await self._check_all_triggers()
            except Exception as e:
                logger.error(f"ProactiveEngine error: {e}", exc_info=True)
            await asyncio.sleep(self._interval)

    async def _check_all_triggers(self) -> None:
        """Evaluate all proactive skill triggers."""
        proactive_skills = self._registry.get_proactive_skills()
        if not proactive_skills:
            return

        now = datetime.now(timezone.utc)
        fired_count = 0

        for skill in proactive_skills:
            for trigger in skill.proactive_triggers:
                try:
                    should_fire = await self._evaluate_trigger(
                        skill.name, trigger, now
                    )
                    if should_fire:
                        # Dedup: don't fire same skill more than once per 6 hours
                        last = self._fired.get(skill.name)
                        if last and (now - last).total_seconds() < 21600:
                            continue

                        await self._fire_trigger(skill.name, trigger)
                        self._fired[skill.name] = now
                        fired_count += 1
                except Exception as e:
                    logger.warning(f"Trigger eval error for {skill.name}: {e}")

        if fired_count:
            logger.info(f"ProactiveEngine: {fired_count} trigger(s) fired")

    async def _evaluate_trigger(self, skill_name: str, trigger: dict,
                                now: datetime) -> bool:
        """Evaluate a single trigger. Returns True if should fire."""
        trigger_type = trigger.get("type", "")
        condition = trigger.get("condition", "")

        if trigger_type == "silence":
            return await self._eval_silence(skill_name, condition, now)
        elif trigger_type == "threshold":
            return await self._eval_threshold(condition)
        elif trigger_type == "schedule":
            return self._eval_schedule(condition, now)
        elif trigger_type == "event":
            # Events are fire-and-forget — checked by external triggers
            # Not evaluated in periodic loop
            return False
        return False

    async def _eval_silence(self, skill_name: str, condition: str,
                            now: datetime) -> bool:
        """Check if skill hasn't been used for N days."""
        # Parse "7 дней без контакта" or "14 days without demo"
        m = re.search(r"(\d+)\s*(?:дн|day)", condition)
        if not m:
            return False
        days = int(m.group(1))
        cutoff = now - timedelta(days=days)

        try:
            last_used = await self._pool.fetchval(
                """SELECT MAX(used_at) FROM skill_usage
                   WHERE skill_name = $1""",
                skill_name,
            )
            if last_used is None:
                # Never used — check diary for related activity
                last_diary = await self._pool.fetchval(
                    "SELECT MAX(created_at) FROM diary"
                )
                if last_diary and last_diary < cutoff:
                    return True
                return False
            return last_used < cutoff
        except Exception:
            return False

    async def _eval_threshold(self, condition: str) -> bool:
        """Check threshold conditions like 'errors_today > 5'."""
        # Parse "errors_today > 5" or "slots < 3"
        m = re.match(r"(\w+)\s*([><=!]+)\s*(\d+)", condition.strip().split(" в ")[0].strip())
        if not m:
            return False

        metric_name, operator, value = m.group(1), m.group(2), int(m.group(3))

        actual = await self._get_metric_value(metric_name)
        if actual is None:
            return False

        if operator == ">" and actual > value:
            return True
        if operator == ">=" and actual >= value:
            return True
        if operator == "<" and actual < value:
            return True
        if operator == "<=" and actual <= value:
            return True
        if operator == "==" and actual == value:
            return True
        return False

    async def _get_metric_value(self, metric_name: str) -> int | None:
        """Get current value of a metric."""
        try:
            if metric_name == "errors_today":
                # Count errors from all capsules today
                from datetime import date
                today = date.today().isoformat()
                total = 0
                capsule_ids = list(self._registry._skills.keys())  # approximate
                # Use Redis metrics
                for key in await self._redis.keys(f"neura:metrics:*:errors:{today}"):
                    val = await self._redis.get(key)
                    if val:
                        total += int(val)
                return total
            elif metric_name.startswith("slots"):
                # Cron guardian slots — read from file if available
                return None  # Not implemented yet
            elif metric_name.startswith("записей") or metric_name.startswith("bookings"):
                return None  # Future: booking count from external source
        except Exception:
            pass
        return None

    def _eval_schedule(self, condition: str, now: datetime) -> bool:
        """Check schedule conditions like 'понедельник 10:00' or 'ежедневно 08:00'."""
        # Moscow time
        msk = now + timedelta(hours=3)
        hour = msk.hour
        weekday = msk.weekday()  # 0=Mon

        condition_lower = condition.lower()

        # Daily schedule
        if "ежедневно" in condition_lower or "daily" in condition_lower:
            m = re.search(r"(\d{1,2}):(\d{2})", condition)
            if m:
                target_h = int(m.group(1))
                # Fire within 30-min window of target hour
                return hour == target_h
            return False

        # Weekly schedule
        day_map = {
            "понедельник": 0, "пн": 0, "monday": 0, "mon": 0,
            "вторник": 1, "вт": 1, "tuesday": 1, "tue": 1,
            "среда": 2, "ср": 2, "wednesday": 2, "wed": 2,
            "четверг": 3, "чт": 3, "thursday": 3, "thu": 3,
            "пятница": 4, "пт": 4, "friday": 4, "fri": 4,
            "суббота": 5, "сб": 5, "saturday": 5, "sat": 5,
            "воскресенье": 6, "вс": 6, "sunday": 6, "sun": 6,
        }

        for day_name, day_idx in day_map.items():
            if day_name in condition_lower:
                if weekday != day_idx:
                    return False
                m = re.search(r"(\d{1,2}):(\d{2})", condition)
                if m:
                    target_h = int(m.group(1))
                    return hour == target_h
                return True

        return False

    async def _fire_trigger(self, skill_name: str, trigger: dict) -> None:
        """Execute a triggered action."""
        action = trigger.get("action", "")
        trigger_type = trigger.get("type", "")
        condition = trigger.get("condition", "")

        logger.info(f"🔔 Proactive trigger fired: {skill_name} "
                     f"[{trigger_type}: {condition}] → {action}")

        # Record in skill_usage
        try:
            await self._pool.execute(
                """INSERT INTO skill_usage
                   (capsule_id, skill_name, success, user_intent, metadata)
                   VALUES ('system', $1, true, $2, $3)""",
                skill_name,
                f"proactive:{trigger_type}:{condition}",
                f'{{"trigger_type": "{trigger_type}", "action": "{action}"}}',
            )
        except Exception as e:
            logger.warning(f"Failed to record proactive trigger: {e}")

        # Send alert to HQ
        if self._alert:
            try:
                await self._alert.send(
                    f"🔔 Proactive: [{skill_name}] {action}\n"
                    f"Trigger: {trigger_type} — {condition}",
                    alert_type="PROACTIVE",
                    deduplicate=True,
                )
            except Exception as e:
                logger.warning(f"Failed to send proactive alert: {e}")

        # Deliver proactive message to capsule owner(s)
        await self._deliver_to_capsules(skill_name, action, trigger)

    async def _deliver_to_capsules(self, skill_name: str, action: str,
                                    trigger: dict) -> None:
        """Send proactive message to owners of capsules that have this skill.

        Finds capsules with proactive=true that include this skill,
        then sends a prompt via their Telegram bot to the owner.
        """
        if not self._capsules:
            return

        from telegram import Bot

        for cap_id, capsule in self._capsules.items():
            cfg = capsule.config
            # Skip capsules without proactive enabled in features
            if not cfg.features.get("proactive", False):
                continue
            # Check if this capsule has the skill
            if skill_name not in (cfg.skills or []):
                continue
            # Send to owner
            owner_id = cfg.owner_telegram_id
            if not owner_id:
                continue

            message = f"💡 {action}"
            try:
                bot = Bot(token=cfg.bot_token)
                await bot.send_message(chat_id=owner_id, text=message)
                logger.info(f"[{cap_id}] Proactive message sent to {owner_id}: {skill_name}")
            except Exception as e:
                logger.warning(f"[{cap_id}] Failed to send proactive message: {e}")
