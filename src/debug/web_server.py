"""Lightweight MJPEG debug stream showing camera feed with face detection overlay."""

import io
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import cv2
import numpy as np


class DebugState:
    """Shared state between the main app and the debug server."""

    def __init__(self):
        self.lock = threading.Lock()
        self.frame = None       # Latest camera frame (BGR numpy array)
        self.faces = []         # Latest face detections [(x,y,w,h), ...]
        self.gaze = (0.0, 0.0)  # Current eye gaze target
        self.fps_render = 0.0   # Rendering FPS
        self.fps_detect = 0.0   # Detection FPS
        self.face_detected = False

    def update_frame(self, grey_frame: np.ndarray, faces: list):
        with self.lock:
            # Convert grey to BGR for drawing
            self.frame = cv2.cvtColor(grey_frame, cv2.COLOR_GRAY2BGR)
            self.faces = list(faces)

    def update_stats(self, gaze, fps_render, fps_detect, face_detected):
        with self.lock:
            self.gaze = gaze
            self.fps_render = fps_render
            self.fps_detect = fps_detect
            self.face_detected = face_detected

    def get_jpeg(self) -> bytes | None:
        with self.lock:
            if self.frame is None:
                return None

            display = self.frame.copy()
            # Draw face rectangles
            for (x, y, w, h) in self.faces:
                cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Draw stats
            gx, gy = self.gaze
            cv2.putText(display, f"Gaze: ({gx:.2f}, {gy:.2f})",
                        (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            cv2.putText(display, f"Render: {self.fps_render:.0f} FPS",
                        (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            cv2.putText(display, f"Detect: {self.fps_detect:.0f} FPS",
                        (5, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            status = "TRACKING" if self.face_detected else "IDLE"
            cv2.putText(display, status,
                        (5, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                        (0, 255, 0) if self.face_detected else (0, 0, 255), 1)

            # Scale up for visibility
            display = cv2.resize(display, (480, 360))

            _, jpeg = cv2.imencode(".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, 70])
            return jpeg.tobytes()


_INDEX_HTML = b"""\
<html><head><title>Robot Head Debug</title>
<style>body{background:#111;color:#0f0;font-family:monospace;text-align:center}
img{border:2px solid #0f0;margin-top:20px}</style></head>
<body><h2>Robot Head - Debug Stream</h2>
<img src="/stream" /><br>
<p>Camera feed with face detection overlay</p>
</body></html>
"""


class DebugHandler(BaseHTTPRequestHandler):
    debug_state = None  # Set before starting server

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(_INDEX_HTML)
        elif self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type",
                             "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    jpeg = self.debug_state.get_jpeg()
                    if jpeg is not None:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(jpeg)}\r\n".encode())
                        self.wfile.write(b"\r\n")
                        self.wfile.write(jpeg)
                        self.wfile.write(b"\r\n")
                    time.sleep(0.1)  # ~10 FPS for the debug stream
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress request logging


def start_debug_server(debug_state: DebugState, port: int = 8080):
    """Start the debug web server in a daemon thread."""
    DebugHandler.debug_state = debug_state
    server = HTTPServer(("0.0.0.0", port), DebugHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
