"""OpenCV camera abstraction used by edge runtime and enrollment."""

from __future__ import annotations

import cv2


class CameraHandler:
    def __init__(self, camera_index: int = 0, show_preview: bool = True) -> None:
        self.camera_index = camera_index
        self.show_preview = show_preview
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        self._capture = cv2.VideoCapture(self.camera_index)
        if not self._capture.isOpened():
            raise RuntimeError(f"Unable to open camera index {self.camera_index}")

    def read(self):
        if self._capture is None:
            raise RuntimeError("Camera has not been opened")
        ok, frame = self._capture.read()
        if not ok:
            return None
        return frame

    def show(self, frame, window_name: str = "AttendSense Edge") -> None:
        if self.show_preview:
            cv2.imshow(window_name, frame)

    def should_quit(self) -> bool:
        return (cv2.waitKey(1) & 0xFF) == ord("q")

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        if self.show_preview:
            cv2.destroyAllWindows()
