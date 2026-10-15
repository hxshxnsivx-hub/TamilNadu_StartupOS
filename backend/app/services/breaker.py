"""Circuit breaker for the model provider (build spec 14.1).

Three failures within a minute open the breaker for five minutes: during that
time the conversation runs on the offline path straight away instead of
waiting on calls that are likely to fail. One success closes it again.
"""

from __future__ import annotations

import time
from collections import deque

from app.core.logging import get_logger

log = get_logger("breaker")


class Breaker:
    def __init__(
        self, name: str, threshold: int = 3, window_s: float = 60, cooldown_s: float = 300
    ) -> None:
        self.name = name
        self.threshold = threshold
        self.window_s = window_s
        self.cooldown_s = cooldown_s
        self.failures: deque[float] = deque()
        self.open_until = 0.0

    def allow(self, now: float | None = None) -> bool:
        return (now if now is not None else time.monotonic()) >= self.open_until

    def fail(self, reason: str = "", now: float | None = None) -> None:
        now = now if now is not None else time.monotonic()
        self.failures.append(now)
        while self.failures and now - self.failures[0] > self.window_s:
            self.failures.popleft()
        if len(self.failures) >= self.threshold and self.allow(now):
            self.open_until = now + self.cooldown_s
            log.warning("breaker.open", name=self.name, reason=reason, seconds=self.cooldown_s)

    def succeed(self) -> None:
        self.failures.clear()
        self.open_until = 0.0

    @property
    def state(self) -> str:
        return "closed" if self.allow() else "open"


model_breaker = Breaker("model")
