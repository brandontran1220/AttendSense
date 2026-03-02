"""Enrollment mode: capture multiple embeddings per person without persisting image frames."""

from __future__ import annotations

from pathlib import Path
import pickle
import time
from typing import Dict, List

import cv2
import face_recognition

from camera_handler import CameraHandler


def _load_existing(embeddings_file: Path) -> Dict[str, List[List[float]]]:
    if not embeddings_file.exists():
        return {}
    with embeddings_file.open("rb") as handle:
        return pickle.load(handle)


def enroll_person(
    person_id: str,
    samples_required: int,
    embeddings_file: Path,
    camera_index: int,
    show_preview: bool,
) -> int:
    embeddings_file.parent.mkdir(parents=True, exist_ok=True)
    database = _load_existing(embeddings_file)

    camera = CameraHandler(camera_index=camera_index, show_preview=show_preview)
    camera.open()

    captured: list[list[float]] = []
    last_capture_time = 0.0

    try:
        while len(captured) < samples_required:
            frame = camera.read()
            if frame is None:
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb, model="hog")
            encodings = face_recognition.face_encodings(rgb, locations)

            now = time.time()
            if len(encodings) == 1 and now - last_capture_time >= 0.5:
                captured.append(encodings[0].tolist())
                last_capture_time = now

            status = f"Enrolling {person_id}: {len(captured)}/{samples_required} (press q to exit)"
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 200, 30), 2)
            camera.show(frame, window_name="AttendSense Enrollment")

            if show_preview and camera.should_quit():
                break
    finally:
        camera.release()

    if captured:
        database.setdefault(person_id, [])
        database[person_id].extend(captured)
        with embeddings_file.open("wb") as handle:
            pickle.dump(database, handle)

    return len(captured)
