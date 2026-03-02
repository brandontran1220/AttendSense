"""Face embedding loading and recognition utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pickle
from typing import Dict, List

import cv2
import face_recognition
import numpy as np


@dataclass
class Recognition:
    person_id: str
    confidence: float
    top: int
    right: int
    bottom: int
    left: int


class FaceRecognizer:
    def __init__(
        self,
        embeddings_file: Path,
        confidence_threshold: float,
        frame_resize_scale: float = 0.25,
    ) -> None:
        self.embeddings_file = embeddings_file
        self.confidence_threshold = confidence_threshold
        self.frame_resize_scale = frame_resize_scale
        self.known_encodings, self.known_labels = self._load_known_faces(embeddings_file)

    @staticmethod
    def _load_known_faces(embeddings_file: Path):
        if not embeddings_file.exists():
            return [], []

        with embeddings_file.open("rb") as handle:
            data: Dict[str, List[List[float]]] = pickle.load(handle)

        encodings: list[np.ndarray] = []
        labels: list[str] = []

        for person_id, vectors in data.items():
            for vector in vectors:
                encodings.append(np.array(vector, dtype=np.float64))
                labels.append(person_id)

        return encodings, labels

    def has_known_faces(self) -> bool:
        return len(self.known_encodings) > 0

    def detect_and_match(self, frame) -> list[Recognition]:
        small_frame = cv2.resize(frame, (0, 0), fx=self.frame_resize_scale, fy=self.frame_resize_scale)
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        locations = face_recognition.face_locations(rgb_small, model="hog")
        encodings = face_recognition.face_encodings(rgb_small, locations)

        results: list[Recognition] = []
        scale = int(round(1 / self.frame_resize_scale))

        for (top, right, bottom, left), encoding in zip(locations, encodings):
            person_id, confidence = self._match_encoding(encoding)
            results.append(
                Recognition(
                    person_id=person_id,
                    confidence=confidence,
                    top=top * scale,
                    right=right * scale,
                    bottom=bottom * scale,
                    left=left * scale,
                )
            )

        return results

    def _match_encoding(self, encoding: np.ndarray) -> tuple[str, float]:
        if not self.known_encodings:
            return "unknown", 0.0

        distances = face_recognition.face_distance(self.known_encodings, encoding)
        best_idx = int(np.argmin(distances))
        distance = float(distances[best_idx])
        confidence = max(0.0, min(1.0, 1.0 - distance))

        if confidence >= self.confidence_threshold:
            return self.known_labels[best_idx], confidence
        return "unknown", confidence


def draw_recognition_overlays(frame, recognitions: list[Recognition]) -> None:
    for rec in recognitions:
        if rec.person_id == "unknown":
            color = (0, 0, 255)
            label = f"Unknown ({rec.confidence:.2f})"
        else:
            color = (0, 200, 0)
            label = f"{rec.person_id} ({rec.confidence:.2f})"

        cv2.rectangle(frame, (rec.left, rec.top), (rec.right, rec.bottom), color, 2)
        cv2.putText(
            frame,
            label,
            (rec.left, max(15, rec.top - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )
