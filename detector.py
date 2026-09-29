"""Timing-only burst detector. Never stores or prints characters."""
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional


@dataclass(frozen=True)
class Alert:
    elapsed_seconds: float
    key_count: int
    keys_per_second: float


class BurstDetector:
    """Flag sustained fast key presses in a sliding time window.

    Each press contributes only a timestamp. This is a heuristic, not an
    injected-input classifier. A burst can be caused by macros or automation.
    """

    def __init__(self, window_seconds: float = 0.75, min_keys: int = 12,
                 min_rate: float = 18.0, cooldown_seconds: float = 3.0):
        if window_seconds <= 0 or min_keys < 2 or min_rate <= 0 or cooldown_seconds < 0:
            raise ValueError("window and rate must be positive, min_keys >= 2, cooldown >= 0")
        self.window_seconds = window_seconds
        self.min_keys = min_keys
        self.min_rate = min_rate
        self.cooldown_seconds = cooldown_seconds
        self._times: Deque[float] = deque()
        self._last_alert = float("-inf")
        self._last_time = float("-inf")

    def observe(self, timestamp: float) -> Optional[Alert]:
        if timestamp < self._last_time:
            raise ValueError("timestamps must be nondecreasing")
        self._last_time = timestamp
        self._times.append(timestamp)
        while self._times and timestamp - self._times[0] > self.window_seconds:
            self._times.popleft()
        if len(self._times) < self.min_keys:
            return None
        elapsed = timestamp - self._times[0]
        # Span must be nonzero: a batch delivered at one instant tells us
        # nothing reliable about the actual pace of typing.
        if elapsed <= 0 or timestamp - self._last_alert < self.cooldown_seconds:
            return None
        rate = (len(self._times) - 1) / elapsed
        if rate < self.min_rate:
            return None
        self._last_alert = timestamp
        return Alert(elapsed, len(self._times), rate)
