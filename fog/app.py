from flask import Flask, request, jsonify, render_template
from db import init_db
from dedupe import process_event
import sqlite3

app = Flask(__name__)

init_db()

@app.route("/event", methods=["POST"])
def receive_event():
    data = request.json

    person_id = data["person_id"]
    name = data["name"]
    timestamp = data["timestamp"]
    confidence = data["confidence"]
    camera_id = data["camera_id"]

    process_event(person_id, name, timestamp, confidence, camera_id)

    return jsonify({"status": "received"}), 200


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/attendance")
def get_attendance():
    conn = sqlite3.connect("attendsense.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM attendance_status WHERE present=1")
    rows = cursor.fetchall()

    conn.close()

    return jsonify([dict(row) for row in rows])

@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    data = request.json

    device_id = data["device_id"]
    fps = data.get("fps", 0)
    camera_ok = data.get("camera_ok", 1)

    from datetime import datetime
    now = datetime.utcnow().isoformat()

    conn = sqlite3.connect("attendsense.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO device_status
        (device_id, last_heartbeat, fps, camera_ok)
        VALUES (?, ?, ?, ?)
    """, (device_id, now, fps, camera_ok))

    conn.commit()
    conn.close()

    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)