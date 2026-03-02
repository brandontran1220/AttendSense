"""Validation and deduplication policy for incoming attendance events."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import threading
from typing import Any


def parse_iso_timestamp(raw: str) -> datetime:
    value = raw.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_event_payload(payload: Any) -> tuple[bool, dict | str]:
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object"

    required = ["person_id", "timestamp", "confidence", "camera_id"]
    for key in required:
        if key not in payload:
            return False, f"Missing required field: {key}"

    person_id = str(payload.get("person_id", "")).strip()
    camera_id = str(payload.get("camera_id", "")).strip()
    if not person_id:
        return False, "person_id cannot be empty"
    if not camera_id:
        return False, "camera_id cannot be empty"

    try:
        timestamp_dt = parse_iso_timestamp(str(payload.get("timestamp", "")))
    except ValueError:
        return False, "timestamp must be ISO-8601 formatted"

    try:
        confidence = float(payload.get("confidence"))
    except (TypeError, ValueError):
        return False, "confidence must be a number"

    if confidence < 0.0 or confidence > 1.0:
        return False, "confidence must be between 0.0 and 1.0"

    return (
        True,
        {
            "person_id": person_id,
            "timestamp": timestamp_dt.isoformat(timespec="seconds"),
            "confidence": round(confidence, 4),
            "camera_id": camera_id,
            "timestamp_dt": timestamp_dt,
        },
    )


class EventDeduplicator:
    def __init__(self, window_seconds: int = 30) -> None:
        self.window = timedelta(seconds=window_seconds)
        self._last_event_time: dict[str, datetime] = {}
        self._lock = threading.Lock()

    def should_accept(self, person_id: str, timestamp: datetime) -> bool:
        with self._lock:
            previous = self._last_event_time.get(person_id)
            if previous is None or timestamp - previous >= self.window:
                self._last_event_time[person_id] = timestamp
                return True
            return False
