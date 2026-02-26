import sqlite3
from datetime import datetime, timedelta

DB_NAME = "attendsense.db"

DEDUP_SECONDS = 30

def process_event(person_id, name, timestamp, confidence, camera_id):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    # Check for existing attendance status
    cursor.execute("""
        SELECT last_seen FROM attendance_status WHERE person_id=?
    """, (person_id,))
    existing = cursor.fetchone()

    if existing:
        last_seen_str = existing[0]
        last_seen = datetime.fromisoformat(last_seen_str)
        current_time = datetime.fromisoformat(timestamp)

        # deduplication: if the same person is seen again within DEDUP_SECONDS, ignore it
        if current_time - last_seen < timedelta(seconds=DEDUP_SECONDS):
            conn.close()
            return  # Ignore duplicate within time window

    # Insert event log
    cursor.execute("""
        INSERT INTO attendance_events
        (person_id, name, timestamp, confidence, camera_id, received_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (person_id, name, timestamp, confidence, camera_id, now))

    # Update or insert attendance status
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