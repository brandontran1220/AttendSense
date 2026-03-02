"""Flask app for AttendSense fog manager."""

from __future__ import annotations

from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from config import (
    DASHBOARD_PASSWORD,
    DASHBOARD_USERNAME,
    DB_PATH,
    DEDUP_WINDOW_SECONDS,
    SECRET_KEY,
    load_students,
)
from db import AttendSenseDB
from policy import EventDeduplicator, validate_event_payload
from session_manager import SessionManager


app = Flask(__name__)
app.secret_key = SECRET_KEY

database = AttendSenseDB(DB_PATH)
database.init_db()
students = load_students()
session_manager = SessionManager(database=database, students=students)
deduplicator = EventDeduplicator(window_seconds=DEDUP_WINDOW_SECONDS)


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def build_dashboard_data() -> dict:
    active_session = session_manager.refresh_state()
    start_time = active_session["start_time"] if active_session else None
    end_time = active_session["end_time"] if active_session else None

    status_map: dict[str, bool] = {}
    if active_session:
        status_map = database.get_status_map(session_id=int(active_session["id"]))

    last_detection_map = database.get_last_detection_map(start_time=start_time, end_time=end_time)

    rows: list[dict] = []
    for student in students:
        person_id = student["person_id"]
        rows.append(
            {
                "person_id": person_id,
                "name": student["name"],
                "present": bool(status_map.get(person_id, False)),
                "last_detection": last_detection_map.get(person_id, "Never"),
            }
        )

    present_count = sum(1 for row in rows if row["present"])
    session_label = active_session["class_name"] if active_session else "No active session"

    return {
        "session": active_session,
        "session_name": session_label,
        "rows": rows,
        "present_count": present_count,
        "total_students": len(rows),
    }


def build_session_detail(session_row: dict) -> dict:
    session_id = int(session_row["id"])
    start_time = session_row["start_time"]
    end_time = session_row["end_time"]

    status_map = database.get_status_map(session_id=session_id)
    last_detection_map = database.get_last_detection_map(start_time=start_time, end_time=end_time)

    rows: list[dict] = []
    for student in students:
        person_id = student["person_id"]
        rows.append(
            {
                "person_id": person_id,
                "name": student["name"],
                "present": bool(status_map.get(person_id, False)),
                "last_detection": last_detection_map.get(person_id, "Never"),
            }
        )

    present_count = sum(1 for row in rows if row["present"])
    event_count = database.get_event_count_for_session(session_id=session_id)
    return {
        "session": session_row,
        "rows": rows,
        "present_count": present_count,
        "total_students": len(rows),
        "event_count": event_count,
    }


@app.route("/event", methods=["POST"])
def receive_event():
    ok, payload = validate_event_payload(request.get_json(silent=True))
    if not ok:
        return jsonify({"status": "error", "message": payload}), 400

    person_id = payload["person_id"]
    timestamp = payload["timestamp"]

    if not deduplicator.should_accept(person_id, payload["timestamp_dt"]):
        return jsonify({"status": "ignored", "reason": "duplicate_within_30_seconds"}), 200

    database.insert_event(
        person_id=person_id,
        timestamp=timestamp,
        confidence=payload["confidence"],
        camera_id=payload["camera_id"],
    )

    active_session = session_manager.get_session_for_timestamp(timestamp)
    if active_session:
        database.mark_present(session_id=int(active_session["id"]), person_id=person_id)

    return jsonify({"status": "accepted"}), 200


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == DASHBOARD_USERNAME and password == DASHBOARD_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        error = "Invalid credentials"
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET"])
@login_required
def dashboard():
    return render_template("dashboard.html", data=build_dashboard_data())


@app.route("/api/dashboard", methods=["GET"])
@login_required
def dashboard_api():
    return jsonify(build_dashboard_data())


@app.route("/sessions", methods=["GET"])
@login_required
def session_history():
    sessions = database.list_sessions(limit=100)
    selected_session = None

    if sessions:
        selected_id = request.args.get("session_id", "").strip()
        if selected_id:
            try:
                selected_session = database.get_session_by_id(int(selected_id))
            except ValueError:
                selected_session = None
        if not selected_session:
            selected_session = database.get_session_by_id(int(sessions[0]["id"]))

    detail = build_session_detail(selected_session) if selected_session else None

    return render_template(
        "past_sessions.html",
        sessions=sessions,
        selected_session_id=int(selected_session["id"]) if selected_session else None,
        detail=detail,
    )


@app.route("/session/start", methods=["POST"])
@login_required
def start_session():
    class_name = request.form.get("class_name", "").strip()
    if not class_name:
        return jsonify({"status": "error", "message": "class_name is required"}), 400

    session_manager.start_session(class_name=class_name)
    return redirect(url_for("dashboard"))


@app.route("/session/end", methods=["POST"])
@login_required
def end_session():
    session_manager.end_current_session()
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
