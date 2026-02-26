import sqlite3
from datetime import datetime

DB_NAME = "attendsense.db"

def process_event(person_id, name, timestamp, confidence, camera_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    # Insert event log
    cursor.execute("""
        INSERT INTO attendance_events
        (person_id, name, timestamp, confidence, camera_id, received_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (person_id, name, timestamp, confidence, camera_id, now))

    # Check if already present
    cursor.execute("""
        SELECT * FROM attendance_status WHERE person_id=?
    """, (person_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE attendance_status
            SET last_seen=?, present=1
            WHERE person_id=?
        """, (timestamp, person_id))
    else:
        cursor.execute("""
            INSERT INTO attendance_status
            (person_id, name, first_seen, last_seen, present)
            VALUES (?, ?, ?, ?, 1)
        """, (person_id, name, timestamp, timestamp))

    conn.commit()
    conn.close()