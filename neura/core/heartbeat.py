"""HeartbeatEngine — per-capsule periodic reminder tasks.

Each capsule can define heartbeat tasks in YAML config:

  heartbeat:
    - name: weekly_checkin
      message: "Привет! Как дела на этой неделе? Есть задачи?"
      schedule: "monday 10:00"    # day + time (MSK)
      enabled: true
    - name: daily_reminder
      message: "Напоминание: проверь задачи на сегодня"
      schedule: "daily 09:00"
      enabled: true

Schedule formats:
  - "daily HH:MM"       — every day at HH:MM MSK
  - "<weekday> HH:MM"   — weekly on that day (понедельник/monday/пн etc)
  - "every Nh"           — every N hours
  - "every Nm"           — every N minutes (min 30)

Messages are sent to the capsule owner via the bot.
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

HOMES_DIR = Path("/opt/neura-v2/homes")

MSK_OFFSET = timedelta(hours=3)

TZ_MAP = {
    "europe/moscow": 3, "msk": 3, "москва": 3,
    "asia/novosibirsk": 7, "nsk": 7, "новосибирск": 7,
    "asia/yekaterinburg": 5, "екатеринбург": 5,
    "asia/krasnoyarsk": 7, "красноярск": 7,
    "asia/almaty": 6, "алматы": 6,
    "europe/minsk": 3, "минск": 3,
    "europe/kiev": 2, "europe/kyiv": 2, "киев": 2,
    "utc": 0, "gmt": 0,
}

DAY_MAP = {
    "понедельник": 0, "пн": 0, "monday": 0, "mon": 0,
    "вторник": 1, "вт": 1, "tuesday": 1, "tue": 1,
    "среда": 2, "ср": 2, "wednesday": 2, "wed": 2,
    "четверг": 3, "чт": 3, "thursday": 3, "thu": 3,
    "пятница": 4, "пт": 4, "friday": 4, "fri": 4,
    "суббота": 5, "сб": 5, "saturday": 5, "sat": 5,
    "воскресенье": 6, "вс": 6, "sunday": 6, "sun": 6,
}


@dataclass
class HeartbeatTask:
    """A single periodic task for a capsule.

    task_type:
        "reminder" (default) — send message text to user via bot
        "task"               — run message as prompt through Claude engine,
                               send result to user
    """
    name: str
    message: str
    schedule: str
    capsule_id: str
    owner_telegram_id: int
    recipient_telegram_id: int | None = None  # Override: send to this ID instead of owner
    enabled: bool = True
    task_type: str = "reminder"  # "reminder" | "task"
    tz_offset_hours: int = 3     # Default MSK (UTC+3). Override per-task via timezone field.

    @property
    def target_telegram_id(self) -> int:
        """Actual recipient: explicit override or owner."""
        return self.recipient_telegram_id if self.recipient_telegram_id else self.owner_telegram_id


def _resolve_tz_offset(tz_str: str | None) -> int:
    """Resolve timezone string to UTC offset in hours. Default: 3 (MSK)."""
    if not tz_str:
        return 3
    return TZ_MAP.get(tz_str.lower().strip(), 3)


def parse_heartbeat_config(capsule_id: str, owner_telegram_id: int,
                           raw_list: list[dict]) -> list[HeartbeatTask]:
    """Parse heartbeat config from YAML into HeartbeatTask list."""
    tasks = []
    for item in raw_list:
        if not item.get("name") or not item.get("message"):
            logger.warning(f"Heartbeat task missing name/message in {capsule_id}")
            continue
        # Validate recipient_telegram_id type
        recipient_id = item.get("recipient_telegram_id")
        if recipient_id is not None:
            try:
                recipient_id = int(recipient_id)
            except (ValueError, TypeError):
                logger.warning(f"Heartbeat invalid recipient_telegram_id in {capsule_id}/{item['name']}")
                recipient_id = None
        tasks.append(HeartbeatTask(
            name=item["name"],
            message=item["message"],
            schedule=item.get("schedule", "daily 10:00"),
            capsule_id=capsule_id,
            owner_telegram_id=owner_telegram_id,
            recipient_telegram_id=recipient_id,
            enabled=item.get("enabled", True),
            task_type=item.get("type", "reminder"),
            tz_offset_hours=_resolve_tz_offset(item.get("timezone")),
        ))
    return tasks


def should_fire(task: HeartbeatTask, now_utc: datetime) -> bool:
    """Check if a heartbeat task should fire at the given UTC time.

    Uses task's timezone (default MSK) for schedule matching.
    Returns True if current hour:minute matches (within 15-min window).
    """
    if not task.enabled:
        return False

    local_offset = timedelta(hours=task.tz_offset_hours)
    local_now = now_utc + local_offset
    schedule = task.schedule.lower().strip()

    # "every Nh" or "every Nm"
    interval_match = re.match(r"every\s+(\d+)([hm])", schedule)
    if interval_match:
        # Interval-based: always return True (caller handles dedup)
        return True

    # Extract HH:MM
    time_match = re.search(r"(\d{1,2}):(\d{2})", schedule)
    if not time_match:
        return False
    target_h = int(time_match.group(1))
    target_m = int(time_match.group(2))

    # Check if current time is within 15-min window of target
    if local_now.hour != target_h:
        return False
    if abs(local_now.minute - target_m) > 15:
        return False

    # "daily HH:MM" or "ежедневно HH:MM"
    if schedule.startswith("daily") or schedule.startswith("ежедневно"):
        return True

    # "<weekday> HH:MM"
    for day_name, day_idx in DAY_MAP.items():
        if day_name in schedule:
            return local_now.weekday() == day_idx

    # Bare "HH:MM" without prefix → treat as daily (fix: silent no-fire bug)
    return True


def get_interval_seconds(task: HeartbeatTask) -> int:
    """Get interval in seconds for interval-based tasks. 0 = not interval."""
    schedule = task.schedule.lower().strip()
    m = re.match(r"every\s+(\d+)([hm])", schedule)
    if not m:
        return 0
    value = int(m.group(1))
    unit = m.group(2)
    if unit == "h":
        return value * 3600
    if unit == "m":
        return max(value, 30) * 60  # minimum 30 minutes
    return 0


class HeartbeatEngine:
    """Runs heartbeat tasks for all capsules.

    Checks every 15 minutes. Uses Redis for dedup (last fire time).
    Sends messages via Telegram bot.
    """

    CHECK_INTERVAL = 900  # 15 minutes

    def __init__(self, redis_client, send_callback, task_callback=None):
        """
        Args:
            redis_client: Redis async client for dedup state.
            send_callback: async fn(capsule_id, telegram_id, message) -> None
            task_callback: async fn(capsule_id, telegram_id, task_name, prompt) -> None
                           Runs prompt through engine and sends result.
        """
        self._redis = redis_client
        self._send = send_callback
        self._run_task = task_callback
        self._tasks: list[HeartbeatTask] = []
        self._loop_task: asyncio.Task | None = None

    def register_tasks(self, tasks: list[HeartbeatTask]) -> None:
        """Add heartbeat tasks (called per capsule during init)."""
        enabled = [t for t in tasks if t.enabled]
        self._tasks.extend(enabled)
        if enabled:
            logger.info(f"Heartbeat: registered {len(enabled)} task(s) "
                        f"for {enabled[0].capsule_id}")

    async def start(self) -> None:
        # Always start the loop — hot-reload picks up heartbeat.yaml from homes/
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info(f"HeartbeatEngine started ({len(self._tasks)} static task(s), "
                    f"hot-reload enabled)")

    async def stop(self) -> None:
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("HeartbeatEngine stopped")

    async def _run_loop(self) -> None:
        await asyncio.sleep(30)  # initial delay (short — fast user task pickup)
        while True:
            try:
                await self._check_all()
            except Exception as e:
                logger.error(f"HeartbeatEngine error: {e}", exc_info=True)
            await asyncio.sleep(self.CHECK_INTERVAL)

    async def _check_all(self) -> None:
        # Hot-reload: pick up user-managed heartbeat.yaml from capsule homes
        self._reload_user_tasks()

        now = datetime.now(timezone.utc)
        fired = 0

        for task in self._tasks:
            try:
                if not should_fire(task, now):
                    continue

                # Atomic dedup via Redis SETNX (prevents race condition on concurrent fires)
                dedup_key = f"neura:heartbeat:last:{task.capsule_id}:{task.name}"
                lock_key = f"neura:heartbeat:lock:{task.capsule_id}:{task.name}"

                try:
                    last_raw = await self._redis.get(dedup_key)
                except Exception as redis_err:
                    logger.warning(f"Heartbeat Redis read failed {task.capsule_id}/{task.name}: {redis_err}")
                    continue  # Skip task when Redis is down (safer than firing without dedup)

                interval = get_interval_seconds(task)
                if interval > 0:
                    # Interval-based: check elapsed time
                    if last_raw:
                        last_ts = float(last_raw)
                        if (now.timestamp() - last_ts) < interval:
                            continue
                else:
                    # Schedule-based: check same date (don't fire twice same day)
                    if last_raw:
                        last_date = datetime.fromtimestamp(
                            float(last_raw), tz=timezone.utc
                        ).date()
                        local_offset = timedelta(hours=task.tz_offset_hours)
                        local_today = (now + local_offset).date()
                        if last_date == local_today:
                            continue

                # Acquire lock atomically (SETNX) — prevents double-fire race
                try:
                    acquired = await self._redis.set(
                        lock_key, "1", nx=True, ex=900  # 15-min lock TTL
                    )
                    if not acquired:
                        continue  # Another cycle is already executing this task
                except Exception as redis_err:
                    logger.warning(f"Heartbeat Redis lock failed {task.capsule_id}/{task.name}: {redis_err}")
                    continue

                try:
                    # Fire!
                    if task.task_type == "task" and self._run_task:
                        await self._run_task(
                            task.capsule_id, task.target_telegram_id, task.name, task.message
                        )
                    else:
                        await self._send(
                            task.capsule_id, task.target_telegram_id, task.message
                        )
                    # Mark fired timestamp
                    try:
                        await self._redis.set(
                            dedup_key, str(now.timestamp()), ex=7 * 86400
                        )
                    except Exception:
                        pass  # Non-critical: worst case = fires again next cycle
                    fired += 1
                    logger.info(f"💓 Heartbeat fired: {task.capsule_id}/{task.name}")
                finally:
                    # Release lock
                    try:
                        await self._redis.delete(lock_key)
                    except Exception:
                        pass  # Lock will auto-expire via TTL

            except Exception as e:
                logger.warning(f"Heartbeat error {task.capsule_id}/{task.name}: {e}")

        if fired:
            logger.info(f"HeartbeatEngine: {fired} task(s) fired")

    def _reload_user_tasks(self) -> None:
        """Hot-reload heartbeat tasks from homes/<capsule>/heartbeat.yaml.

        Users can create/edit this file via the agent. Tasks are merged
        with static YAML config tasks. Dedup by (capsule_id, task_name).
        """
        try:
            import yaml
        except ImportError:
            return

        existing_keys = {(t.capsule_id, t.name) for t in self._tasks}
        new_count = 0

        for home in HOMES_DIR.iterdir():
            if not home.is_dir():
                continue
            hb_file = home / "heartbeat.yaml"
            if not hb_file.exists():
                continue

            capsule_id = home.name
            try:
                raw = yaml.safe_load(hb_file.read_text(encoding="utf-8"))
                if not isinstance(raw, list):
                    continue

                # Find owner telegram_id from existing tasks or config
                owner_id = 0
                for t in self._tasks:
                    if t.capsule_id == capsule_id:
                        owner_id = t.owner_telegram_id
                        break
                if not owner_id:
                    # Try loading from capsule config
                    cfg_path = Path(f"/opt/neura-v2/config/capsules/{capsule_id}.yaml")
                    if cfg_path.exists():
                        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
                        # telegram_id can be top-level or nested under owner
                        owner_id = cfg.get("telegram_id", 0)
                        if not owner_id:
                            owner_id = cfg.get("owner", {}).get("telegram_id", 0)
                    if not owner_id:
                        continue

                for item in raw:
                    name = item.get("name", "")
                    key = (capsule_id, name)
                    tz_offset = _resolve_tz_offset(item.get("timezone"))
                    if key in existing_keys:
                        # Update existing task (including enabled/disabled toggle)
                        for t in self._tasks:
                            if t.capsule_id == capsule_id and t.name == name:
                                t.message = item.get("message", t.message)
                                t.schedule = item.get("schedule", t.schedule)
                                t.enabled = item.get("enabled", True)
                                t.task_type = item.get("type", t.task_type)
                                t.tz_offset_hours = tz_offset
                                break
                    else:
                        # New task
                        task = HeartbeatTask(
                            name=name,
                            message=item.get("message", ""),
                            schedule=item.get("schedule", ""),
                            capsule_id=capsule_id,
                            owner_telegram_id=owner_id,
                            enabled=item.get("enabled", True),
                            task_type=item.get("type", "reminder"),
                            tz_offset_hours=tz_offset,
                        )
                        if task.name and task.message and task.schedule:
                            self._tasks.append(task)
                            existing_keys.add(key)
                            new_count += 1

            except Exception as e:
                logger.warning(f"Heartbeat hot-reload error for {capsule_id}: {e}")

        if new_count:
            logger.info(f"HeartbeatEngine: hot-reloaded {new_count} new user task(s)")
