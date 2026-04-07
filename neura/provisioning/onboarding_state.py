"""Onboarding state machine — Redis-backed per-user onboarding progress.

Keys: onb:{capsule_id}:{user_id} → JSON state
TTL: 7 days (abandoned onboardings expire automatically).
Completed onboardings stored permanently (TTL removed on completion).

Ported from v1: neura-capsule/bot/engine/onboarding_state.py (file-based → Redis).
"""
import json
import logging
from datetime import datetime, timezone, timedelta

import redis.asyncio

logger = logging.getLogger(__name__)

KEY_PREFIX = "neura:onb"
ACTIVE_TTL = 7 * 24 * 3600  # 7 days for in-progress onboarding
COMPLETED_TTL = 90 * 24 * 3600  # 90 days for completed (cleanup)


def _key(capsule_id: str, user_id: int) -> str:
    return f"{KEY_PREFIX}:{capsule_id}:{user_id}"


def _new_state(channel: str = "telegram") -> dict:
    """Create blank onboarding state for a new user."""
    return {
        "phase": 0,
        "sub_step": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "channel": channel,
        "diagnosis": {},
        "profile": {
            "name": None,
            "business": None,
            "urgent_needs": [],
            "boundaries": [],
        },
        "profile_confirmed": False,
        "integrations": {
            "selected": [],
            "completed": [],
            "failed": [],
            "deferred": [],
        },
        "current_integration_idx": 0,
    }


class OnboardingState:
    """Redis-backed onboarding state machine."""

    def __init__(self, redis_client: redis.asyncio.Redis):
        self._r = redis_client

    async def get(self, capsule_id: str, user_id: int) -> dict | None:
        """Get onboarding state. Returns None if not started."""
        raw = await self._r.get(_key(capsule_id, user_id))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Corrupt onboarding state for {capsule_id}:{user_id}")
            return None

    async def set(self, capsule_id: str, user_id: int, state: dict) -> None:
        """Save onboarding state."""
        key = _key(capsule_id, user_id)
        ttl = COMPLETED_TTL if state.get("completed_at") else ACTIVE_TTL
        await self._r.set(key, json.dumps(state, ensure_ascii=False, default=str), ex=ttl)

    async def init(self, capsule_id: str, user_id: int, channel: str = "telegram") -> dict:
        """Initialize onboarding for a new user. Returns the new state."""
        state = _new_state(channel)
        await self.set(capsule_id, user_id, state)
        return state

    async def is_active(self, capsule_id: str, user_id: int) -> bool:
        """Check if user has an active (not completed) onboarding."""
        state = await self.get(capsule_id, user_id)
        if state is None:
            return False
        return state.get("completed_at") is None

    async def mark_completed(self, capsule_id: str, user_id: int) -> None:
        """Mark onboarding as completed."""
        state = await self.get(capsule_id, user_id)
        if state:
            state["completed_at"] = datetime.now(timezone.utc).isoformat()
            await self.set(capsule_id, user_id, state)

    async def update_phase(self, capsule_id: str, user_id: int,
                           phase: int, sub_step: int = 0) -> None:
        """Update phase and sub_step."""
        state = await self.get(capsule_id, user_id)
        if state:
            state["phase"] = phase
            state["sub_step"] = sub_step
            await self.set(capsule_id, user_id, state)

    async def has_completed(self, capsule_id: str, user_id: int) -> bool:
        """Check if user has ever completed onboarding (even if expired)."""
        state = await self.get(capsule_id, user_id)
        if state is None:
            return False
        return state.get("completed_at") is not None

    async def delete(self, capsule_id: str, user_id: int) -> None:
        """Delete onboarding state (for restart)."""
        await self._r.delete(_key(capsule_id, user_id))
