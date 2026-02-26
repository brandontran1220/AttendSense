import cv2
import numpy as np
from typing import Optional

class Camera:
    def __init__(
        self,
        device_index: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        use_v4l2: bool = True,
        show_preview: bool = True,
    ):
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self.use_v4l2 = use_v4l2
        self.show_preview = show_preview
        self.cap: Optional[cv2.VideoCapture] = None
        
    def open(self) -> bool:
        if self.use_v4l2:
            self.cap = cv2.VideoCapture(self.device_index, cv2.CAP_V4L2)
        else:
            self.cap = cv2.VideoCapture(self.device_index)

        # Fallback if first attempt fails
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.device_index)

        if self.cap is None or not self.cap.isOpened():
            print("[camera] ERROR: Could not open camera.")
            return False

        # Best-effort settings (some cameras ignore these)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        # Optional: smaller internal buffer can reduce lag on some webcams
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

        print(f"[camera] Opened camera index {self.device_index}")
        print(f"[camera] Resolution: {actual_w}x{actual_h} @ {actual_fps:.1f} FPS")
        return True
    
    def read(self):
        if self.cap is None or not self.cap.isOpened():
            return False, None

        ok, frame = self.cap.read()
        if not ok:
            return False, None
        return True, frame
    
    def _letterbox_to_window(self, frame, win_w, win_h):
        # Resize frame to fit within (win_w, win_h) while maintaining aspect ratio, and add black borders if needed.
        h, w = frame.shape[:2]
        if win_w <= 0 or win_h <= 0:
            return frame

        scale = min(win_w / w, win_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        canvas = np.zeros((win_h, win_w, 3), dtype=np.uint8)
        x = (win_w - new_w) // 2
        y = (win_h - new_h) // 2
        canvas[y:y+new_h, x:x+new_w] = resized
        return canvas
    
    def show(self, frame, window_name: str = "Jetson Camera"):
        if not self.show_preview:
            return
        
        if not getattr(self, '_window_initialized', False) or getattr(self, '_last_window_name', '') != window_name:
            self._window_initialized = window_name
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            self._window_initialized = True
        
        try:
            _, _, win_w, win_h = cv2.getWindowImageRect(window_name)
            frame_to_show = self._letterbox_to_window(frame, win_w, win_h)
            
        except cv2.error:
            # Fallback if getWindowImageRect isn't available on some builds
            frame_to_show = frame
            
        # Overlay: "Press 'q' to quit"
        text = "Press 'q' to quit"
        x, y = 20, 40
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        font_thickness = 2
        
        (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, font_thickness)
        
        # Draw background rectangle for better visibility
        cv2.rectangle(frame, (x - 10, y - text_height - 10), (x + text_width + 10, y + 10), (0, 0, 0), -1)
        cv2.putText(frame, text, (x, y), font, font_scale, (255, 255, 255), font_thickness)
        
        cv2.imshow(window_name, frame)

    def key_pressed(self, delay_ms: int = 1) -> int:
        #Return last key pressed from OpenCV window.
        return cv2.waitKeyEx(delay_ms)

    def release(self):
        # Release camera and close windows.
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.show_preview:
            cv2.destroyAllWindows()
        print("[camera] Camera released.")
# Quick standalone test
if __name__ == "__main__":
    cam = Camera(width=640, height=480, fps=30, use_v4l2=True, show_preview=True)

    if not cam.open():
        raise SystemExit(1)

    print("[camera] Press 'q' to quit.")
    try:
        while True:
            ok, frame = cam.read()
            if not ok:
                print("[camera] WARNING: Failed to read frame.")
                break

            cam.show(frame, window_name="Jetson Camera")

            key = cam.key_pressed(1) & 0xFF  # Mask to get ASCII value
            
            if key == ord('q') or key == ord('Q'):
                print("[camera] 'q' pressed. Exiting.")
                break

            if cv2.getWindowProperty("Jetson Camera", cv2.WND_PROP_VISIBLE) < 1:
                print("[camera] Window closed (X clicked).")
                break

    finally:
        cam.release()