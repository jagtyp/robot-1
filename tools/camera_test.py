#!/usr/bin/env python3
"""Hardware test: captures frames and prints face detection results."""

import sys
import time
sys.path.insert(0, "/opt/robot-head")

from src.tracking.camera import Camera
from src.tracking.face_detector import FaceDetector


def main():
    print("Starting camera (160x120)...")
    cam = Camera(width=160, height=120)
    cam.start()
    time.sleep(1)  # Let camera warm up

    print("Loading face detector...")
    detector = FaceDetector(scale_factor=1.2, min_neighbors=3)

    print("Running detection loop (Ctrl+C to stop)\n")

    frame_count = 0
    start = time.monotonic()

    try:
        while True:
            grey = cam.capture_grey()
            faces = detector.detect(grey)
            frame_count += 1

            elapsed = time.monotonic() - start
            fps = frame_count / elapsed if elapsed > 0 else 0

            if faces:
                for i, (x, y, w, h) in enumerate(faces):
                    cx = (x + w / 2) / 160 * 2 - 1
                    cy = (y + h / 2) / 120 * 2 - 1
                    print(f"  Face {i}: pos=({x},{y}) size={w}x{h} "
                          f"normalized=({cx:.2f},{cy:.2f})  [{fps:.1f} FPS]")
            else:
                if frame_count % 10 == 0:
                    print(f"  No faces detected  [{fps:.1f} FPS]")

    except KeyboardInterrupt:
        print(f"\nTotal frames: {frame_count}, Avg FPS: {fps:.1f}")
    finally:
        cam.stop()
        print("Camera stopped")


if __name__ == "__main__":
    main()
