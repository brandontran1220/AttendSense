"""AttendSense edge runtime entry point."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import logging

from camera_handler import CameraHandler
from config import load_config
from demo_mode import run_demo
from enrollment import enroll_person
from event_sender import EventSender
from rate_limiter import PersonRateLimiter
from recognition import FaceRecognizer, draw_recognition_overlays


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AttendSense edge runtime")
    parser.add_argument("--config", default="config/config.json", help="Path to edge config JSON")

    subparsers = parser.add_subparsers(dest="mode", required=True)

    run_parser = subparsers.add_parser("run", help="Run live camera recognition")
    run_parser.add_argument("--no-preview", action="store_true", help="Disable OpenCV preview window")

    enroll_parser = subparsers.add_parser("enroll", help="Capture face embeddings for one person")
    enroll_parser.add_argument("--person-id", required=True, help="Person ID to enroll")
    enroll_parser.add_argument("--samples", type=int, default=8, help="Number of embeddings to capture")
    enroll_parser.add_argument("--no-preview", action="store_true", help="Disable OpenCV preview window")

    subparsers.add_parser("demo", help="Run synthetic event sender without camera")

    return parser


def run_live(config_path: str, no_preview: bool) -> None:
    cfg = load_config(config_path)
    show_preview = cfg.show_preview and not no_preview

    recognizer = FaceRecognizer(
        embeddings_file=cfg.embeddings_file,
        confidence_threshold=cfg.confidence_threshold,
        frame_resize_scale=cfg.frame_resize_scale,
    )
    if not recognizer.has_known_faces():
        raise RuntimeError(
            f"No enrolled faces found at {cfg.embeddings_file}. Run enroll mode before live mode."
        )

    rate_limiter = PersonRateLimiter(window_seconds=cfg.rate_limit_seconds)
    sender = EventSender(
        event_url=cfg.fog_event_url,
        timeout_seconds=cfg.request_timeout_seconds,
        retry_interval_seconds=cfg.retry_interval_seconds,
    )

    camera = CameraHandler(camera_index=cfg.camera_index, show_preview=show_preview)
    camera.open()
    sender.start()

    print("[edge] live mode started. Press 'q' to quit.")

    try:
        while True:
            frame = camera.read()
            if frame is None:
                continue

            recognitions = recognizer.detect_and_match(frame)
            now = datetime.now(timezone.utc)

            for rec in recognitions:
                if rec.person_id == "unknown":
                    continue

                if not rate_limiter.allow(rec.person_id, now):
                    continue

                event = {
                    "person_id": rec.person_id,
                    "timestamp": now.isoformat(),
                    "confidence": round(rec.confidence, 4),
                    "camera_id": cfg.camera_id,
                }
                sender.send_or_queue(event)

            draw_recognition_overlays(frame, recognitions)
            camera.show(frame)
            if show_preview and camera.should_quit():
                break
    finally:
        sender.stop()
        camera.release()


def run_enrollment(config_path: str, person_id: str, samples: int, no_preview: bool) -> None:
    cfg = load_config(config_path)
    show_preview = cfg.show_preview and not no_preview

    captured = enroll_person(
        person_id=person_id,
        samples_required=samples,
        embeddings_file=cfg.embeddings_file,
        camera_index=cfg.camera_index,
        show_preview=show_preview,
    )
    print(f"[edge] enrollment completed. person_id={person_id} captured={captured}")


def run_demo_mode(config_path: str) -> None:
    cfg = load_config(config_path)
    recognizer = FaceRecognizer(
        embeddings_file=cfg.embeddings_file,
        confidence_threshold=cfg.confidence_threshold,
        frame_resize_scale=cfg.frame_resize_scale,
    )

    sender = EventSender(
        event_url=cfg.fog_event_url,
        timeout_seconds=cfg.request_timeout_seconds,
        retry_interval_seconds=cfg.retry_interval_seconds,
    )

    try:
        sender.start()
        known_people = sorted(set(recognizer.known_labels))
        run_demo(
            sender=sender,
            person_ids=known_people,
            camera_id=cfg.camera_id,
            interval_seconds=cfg.demo_interval_seconds,
        )
    finally:
        sender.stop()


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.mode == "run":
        run_live(config_path=args.config, no_preview=args.no_preview)
    elif args.mode == "enroll":
        run_enrollment(
            config_path=args.config,
            person_id=args.person_id,
            samples=args.samples,
            no_preview=args.no_preview,
        )
    elif args.mode == "demo":
        run_demo_mode(config_path=args.config)


if __name__ == "__main__":
    main()
