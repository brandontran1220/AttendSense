"""Configuration for AttendSense fog manager."""

from __future__ import annotations

from pathlib import Path
import json


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "attendsense.db"
STUDENTS_PATH = BASE_DIR / "data" / "students.json"

SECRET_KEY = "attendsense_local_secret_key_change_me"
DASHBOARD_USERNAME = "admin"
DASHBOARD_PASSWORD = "attendsense123"
DEDUP_WINDOW_SECONDS = 30


def load_students() -> list[dict[str, str]]:
    if not STUDENTS_PATH.exists():
        return []
    with STUDENTS_PATH.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    students: list[dict[str, str]] = []
    for row in raw:
        person_id = str(row.get("person_id", "")).strip()
        if not person_id:
            continue
        students.append(
            {
                "person_id": person_id,
                "name": str(row.get("name", person_id)),
            }
        )
    return students
