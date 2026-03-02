"""HTTP event sender with retry queue for intermittent local network outages."""

from __future__ import annotations

from collections import deque
import logging
import threading
import time
from typing import Dict

import requests


logger = logging.getLogger(__name__)


class EventSender:
    def __init__(self, event_url: str, timeout_seconds: int = 3, retry_interval_seconds: int = 10) -> None:
        self.event_url = event_url
        self.timeout_seconds = timeout_seconds
        self.retry_interval_seconds = retry_interval_seconds
        self._queue: deque[Dict] = deque()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._retry_thread = threading.Thread(target=self._retry_loop, daemon=True)

    def start(self) -> None:
        self._retry_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._retry_thread.join(timeout=self.retry_interval_seconds + 1)

    def send_or_queue(self, event: Dict) -> None:
        if self._send_once(event):
            return
        with self._lock:
            self._queue.append(event)
            queued = len(self._queue)
        logger.warning("Event queued due to network/server issue. queue_size=%d", queued)

    def _send_once(self, event: Dict) -> bool:
        try:
            response = requests.post(self.event_url, json=event, timeout=self.timeout_seconds)
            if response.status_code == 200:
                logger.info("Event sent successfully for person_id=%s", event.get("person_id"))
                return True
            logger.warning("Event send failed with status=%d body=%s", response.status_code, response.text)
            return False
        except requests.RequestException as exc:
            logger.warning("Network error sending event: %s", exc)
            return False

    def _retry_loop(self) -> None:
        while not self._stop_event.is_set():
            self._stop_event.wait(self.retry_interval_seconds)
            if self._stop_event.is_set():
                break
            self._flush_queue()

    def _flush_queue(self) -> None:
        while True:
            with self._lock:
                if not self._queue:
                    return
                event = self._queue[0]

            if not self._send_once(event):
                return

            with self._lock:
                self._queue.popleft()

            time.sleep(0.05)
