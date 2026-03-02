"""Session-state orchestration for fog manager."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from db import AttendSenseDB


class SessionManager:
    def __init__(self, database: AttendSenseDB, students: list[dict[str, str]]) -> None:
        self.database = database
        self.students = students
        self.current_session = self.database.get_active_session()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def refresh_state(self) -> Optional[dict]:
        self.current_session = self.database.get_active_session()
        return self.current_session

    def start_session(self, class_name: str, end_time: str | None = None) -> dict:
        existing = self.refresh_state()
        if existing:
            self.database.end_session(session_id=int(existing["id"]), end_time=self._now_iso())

        start_time = self._now_iso()
        session_id = self.database.create_session(class_name=class_name, start_time=start_time, end_time=end_time)
        person_ids = [student["person_id"] for student in self.students]
        self.database.ensure_status_rows(session_id=session_id, person_ids=person_ids)
        self.current_session = self.database.get_session_by_id(session_id)
        return self.current_session

    def end_current_session(self) -> Optional[dict]:
        current = self.refresh_state()
        if not current:
            return None
        end_time = self._now_iso()
        self.database.end_session(session_id=int(current["id"]), end_time=end_time)
        self.current_session = self.database.get_session_by_id(int(current["id"]))
        return self.current_session

    def get_session_for_timestamp(self, timestamp: str) -> Optional[dict]:
        return self.database.get_session_for_timestamp(timestamp)
