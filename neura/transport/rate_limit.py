"""Fixed-window rate limiter for WebSocket message handling.

Per-capsule rate limiting with configurable window and max requests.
In-memory implementation — no external dependencies.
"""
import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_WINDOW_SEC = 60      # 1 minute window
DEFAULT_MAX_REQUESTS = 8     # max 8 messages per minute per capsule


@dataclass
class _Window:
    """Tracks requests within a time window."""
    start: float = 0.0
    count: int = 0


class RateLimiter:
    """Fixed-window rate limiter, keyed by capsule_id."""

    def __init__(
        self,
        window_sec: int = DEFAULT_WINDOW_SEC,
        max_requests: int = DEFAULT_MAX_REQUESTS,
    ):
        self._window_sec = window_sec
        self._max_requests = max_requests
        self._windows: dict[str, _Window] = {}

    def check(self, key: str) -> tuple[bool, float]:
        """Check if request is allowed.

        Returns:
            (allowed, wait_seconds)
            - (True, 0) if allowed
            - (False, N) if rate limited — wait N seconds
        """
        now = time.monotonic()
        window = self._windows.get(key)

        if window is None or now - window.start >= self._window_sec:
            # New window
            self._windows[key] = _Window(start=now, count=1)
            return True, 0.0

        if window.count < self._max_requests:
            window.count += 1
            return True, 0.0

        # Rate limited
        wait = self._window_sec - (now - window.start)
        return False, round(wait, 1)

    def cleanup(self) -> None:
        """Remove expired windows (call periodically)."""
        now = time.monotonic()
        expired = [
            k for k, w in self._windows.items()
            if now - w.start >= self._window_sec * 2
        ]
        for k in expired:
            del self._windows[k]
