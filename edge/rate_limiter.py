"""Person-level rate limiter for attendance events."""

from __future__ import annotations

from datetime import datetime, timedelta


class PersonRateLimiter:
    def __init__(self, window_seconds: int) -> None:
        self.window_seconds = window_seconds
        self._last_sent: dict[str, datetime] = {}

    def allow(self, person_id: str, now: datetime) -> bool:
        previous = self._last_sent.get(person_id)
        if previous is None:
            self._last_sent[person_id] = now
            return True

        if now - previous >= timedelta(seconds=self.window_seconds):
            self._last_sent[person_id] = now
            return True

        return False
