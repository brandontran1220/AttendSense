"""Demo mode to generate synthetic attendance events without a camera."""

from __future__ import annotations

from datetime import datetime, timezone
import random
import time

from event_sender import EventSender


def run_demo(sender: EventSender, person_ids: list[str], camera_id: str, interval_seconds: int = 15) -> None:
    candidates = person_ids or ["862392116", "862392117", "862392118"]
    while True:
        person_id = random.choice(candidates)
        event = {
            "person_id": person_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": round(random.uniform(0.72, 0.98), 4),
            "camera_id": camera_id,
        }
        sender.send_or_queue(event)
        print(f"[demo] sent simulated event for {person_id}")
        time.sleep(interval_seconds)
