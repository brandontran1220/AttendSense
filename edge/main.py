import cv2
from camera import Camera

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