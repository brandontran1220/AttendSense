"""Runtime configuration for the edge device."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "config.json"


@dataclass
class EdgeConfig:
    fog_host: str
    fog_port: int
    event_endpoint: str
    camera_id: str
    camera_index: int
    confidence_threshold: float
    rate_limit_seconds: int
    retry_interval_seconds: int
    demo_interval_seconds: int
    frame_resize_scale: float
    request_timeout_seconds: int
    show_preview: bool
    embeddings_path: str

    @property
    def fog_event_url(self) -> str:
        return f"http://{self.fog_host}:{self.fog_port}{self.event_endpoint}"

    @property
    def embeddings_file(self) -> Path:
        path = Path(self.embeddings_path)
        if not path.is_absolute():
            path = BASE_DIR / path
        return path


def load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> EdgeConfig:
    path = Path(config_path)
    if not path.is_absolute():
        path = BASE_DIR / path

    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    return EdgeConfig(
        fog_host=raw["fog_host"],
        fog_port=int(raw.get("fog_port", 5000)),
        event_endpoint=raw.get("event_endpoint", "/event"),
        camera_id=raw["camera_id"],
        camera_index=int(raw.get("camera_index", 0)),
        confidence_threshold=float(raw.get("confidence_threshold", 0.6)),
        rate_limit_seconds=int(raw.get("rate_limit_seconds", 30)),
        retry_interval_seconds=int(raw.get("retry_interval_seconds", 10)),
        demo_interval_seconds=int(raw.get("demo_interval_seconds", 15)),
        frame_resize_scale=float(raw.get("frame_resize_scale", 0.25)),
        request_timeout_seconds=int(raw.get("request_timeout_seconds", 3)),
        show_preview=bool(raw.get("show_preview", True)),
        embeddings_path=raw.get("embeddings_path", "data/known_faces.pkl"),
    )
