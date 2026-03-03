"""SQLite storage access for AttendSense fog manager."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Optional


class AttendSenseDB:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._connect() as conn:
            self._ensure_expected_schema(conn)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    camera_id TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    person_id TEXT NOT NULL,
                    present INTEGER NOT NULL DEFAULT 0 CHECK (present IN (0, 1)),
                    UNIQUE(session_id, person_id),
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )
            conn.commit()

    def _ensure_expected_schema(self, conn: sqlite3.Connection) -> None:
        expected = {
            "sessions": {"id", "class_name", "start_time", "end_time"},
            "attendance_events": {"id", "person_id", "timestamp", "confidence", "camera_id"},
            "attendance_status": {"id", "session_id", "person_id", "present"},
        }
        for table, cols in expected.items():
            existing_cols = self._get_table_columns(conn, table)
            if existing_cols and existing_cols != cols:
                conn.execute(f"DROP TABLE IF EXISTS {table}")

    @staticmethod
    def _get_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if not rows:
            return set()
        return {row["name"] for row in rows}

    def create_session(self, class_name: str, start_time: str, end_time: Optional[str] = None) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (class_name, start_time, end_time)
                VALUES (?, ?, ?)
                """,
                (class_name, start_time, end_time),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def end_session(self, session_id: int, end_time: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE sessions SET end_time = ? WHERE id = ?", (end_time, session_id))
            conn.commit()

    def get_session_by_id(self, session_id: int) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            return dict(row) if row else None

    def get_session_for_timestamp(self, timestamp: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM sessions
                WHERE start_time <= ?
                  AND (end_time IS NULL OR end_time >= ?)
                ORDER BY start_time DESC
                LIMIT 1
                """,
                (timestamp, timestamp),
            ).fetchone()
            return dict(row) if row else None

    def get_active_session(self) -> Optional[dict]:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return self.get_session_for_timestamp(now)

    def list_sessions(self, limit: int = 50, allowed_person_ids: Optional[list[str]] = None) -> list[dict]:
        with self._connect() as conn:
            if allowed_person_ids is None:
                rows = conn.execute(
                    """
                    SELECT
                        s.id,
                        s.class_name,
                        s.start_time,
                        s.end_time,
                        COALESCE(SUM(CASE WHEN st.present = 1 THEN 1 ELSE 0 END), 0) AS present_count,
                        COUNT(st.person_id) AS total_students
                    FROM sessions s
                    LEFT JOIN attendance_status st
                      ON st.session_id = s.id
                    GROUP BY s.id, s.class_name, s.start_time, s.end_time
                    ORDER BY s.start_time DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                return [dict(row) for row in rows]

            if not allowed_person_ids:
                rows = conn.execute(
                    """
                    SELECT
                        s.id,
                        s.class_name,
                        s.start_time,
                        s.end_time,
                        0 AS present_count,
                        0 AS total_students
                    FROM sessions s
                    ORDER BY s.start_time DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                return [dict(row) for row in rows]

            placeholders = ", ".join("?" for _ in allowed_person_ids)
            rows = conn.execute(
                f"""
                SELECT
                    s.id,
                    s.class_name,
                    s.start_time,
                    s.end_time,
                    COALESCE(SUM(CASE WHEN st.present = 1 THEN 1 ELSE 0 END), 0) AS present_count,
                    ? AS total_students
                FROM sessions s
                LEFT JOIN attendance_status st
                  ON st.session_id = s.id
                 AND st.person_id IN ({placeholders})
                GROUP BY s.id, s.class_name, s.start_time, s.end_time
                ORDER BY s.start_time DESC
                LIMIT ?
                """,
                (len(allowed_person_ids), *allowed_person_ids, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def insert_event(self, person_id: str, timestamp: str, confidence: float, camera_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO attendance_events (person_id, timestamp, confidence, camera_id)
                VALUES (?, ?, ?, ?)
                """,
                (person_id, timestamp, confidence, camera_id),
            )
            conn.commit()

    def ensure_status_rows(self, session_id: int, person_ids: list[str]) -> None:
        with self._connect() as conn:
            for person_id in person_ids:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO attendance_status (session_id, person_id, present)
                    VALUES (?, ?, 0)
                    """,
                    (session_id, person_id),
                )
            conn.commit()

    def mark_present(self, session_id: int, person_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO attendance_status (session_id, person_id, present)
                VALUES (?, ?, 1)
                ON CONFLICT(session_id, person_id)
                DO UPDATE SET present = 1
                """,
                (session_id, person_id),
            )
            conn.commit()

    def get_status_map(self, session_id: int) -> dict[str, bool]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT person_id, present FROM attendance_status WHERE session_id = ?",
                (session_id,),
            ).fetchall()
            return {row["person_id"]: bool(row["present"]) for row in rows}

    def get_last_detection_map(self, start_time: Optional[str], end_time: Optional[str]) -> dict[str, str]:
        where_parts = []
        params: list[str] = []

        if start_time:
            where_parts.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            where_parts.append("timestamp <= ?")
            params.append(end_time)

        where_clause = ""
        if where_parts:
            where_clause = "WHERE " + " AND ".join(where_parts)

        query = (
            "SELECT person_id, MAX(timestamp) AS last_detection "
            "FROM attendance_events "
            f"{where_clause} "
            "GROUP BY person_id"
        )

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return {row["person_id"]: row["last_detection"] for row in rows if row["last_detection"]}

    def get_event_count_for_session(self, session_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS event_count
                FROM attendance_events e
                JOIN sessions s ON s.id = ?
                WHERE e.timestamp >= s.start_time
                  AND (s.end_time IS NULL OR e.timestamp <= s.end_time)
                """,
                (session_id,),
            ).fetchone()
            if not row:
                return 0
            return int(row["event_count"])

    def delete_session(self, session_id: int) -> bool:
        session_row = self.get_session_by_id(session_id)
        if not session_row:
            return False

        start_time = session_row["start_time"]
        end_time = session_row["end_time"]

        with self._connect() as conn:
            conn.execute("DELETE FROM attendance_status WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            if end_time:
                conn.execute(
                    """
                    DELETE FROM attendance_events
                    WHERE timestamp >= ? AND timestamp <= ?
                    """,
                    (start_time, end_time),
                )
            conn.commit()
        return True
