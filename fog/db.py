import sqlite3
from datetime import datetime

DB_NAME = "attendsense.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Table 1: attendance_events
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id TEXT NOT NULL,
        name TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        confidence REAL,
        camera_id TEXT,
        received_at TEXT NOT NULL
    )
    """)

    # Table 2: attendance_status
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance_status (
        person_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL,
        present INTEGER NOT NULL
    )
    """)

    # Table 3: device_status
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS device_status (
        device_id TEXT PRIMARY KEY,
        last_heartbeat TEXT NOT NULL,
        fps REAL,
        camera_ok INTEGER
    )
    """)

    conn.commit()
    conn.close()

    print("Database initialized successfully.")