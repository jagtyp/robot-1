"""Lightweight MJPEG debug stream showing camera feed with motion detection overlay."""

import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import cv2
import numpy as np

from src.state import save_state


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


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
        self.style_manager = None  # Set by main.py if available
        self.show_fps = False     # FPS overlay on right eye display

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
<style>
body { background:#111; color:#0f0; font-family:monospace; text-align:center; margin:0; padding:20px; }
h2 { margin-bottom: 10px; }
img.stream { border:2px solid #0f0; margin-top:10px; }
.section { margin-top: 20px; }
.styles-grid {
    display: flex; flex-wrap: wrap; justify-content: center; gap: 12px;
    margin-top: 12px; padding: 0 20px;
}
.style-card {
    background: #1a1a1a; border: 2px solid #333; border-radius: 8px;
    padding: 14px 20px; cursor: pointer; min-width: 140px;
    transition: border-color 0.2s, background 0.2s;
}
.style-card:hover { border-color: #0f0; background: #222; }
.style-card.active { border-color: #0f0; background: #0a2a0a; }
.style-card .name { font-size: 14px; color: #eee; }
.style-card .type { font-size: 11px; color: #666; margin-top: 4px; }
#status-msg { color: #0f0; margin-top: 8px; min-height: 18px; font-size: 12px; }
#mood-msg { color: #0f0; margin-top: 8px; min-height: 18px; font-size: 12px; }
.toggle-row {
    display: flex; justify-content: center; align-items: center; gap: 10px;
    margin-top: 12px;
}
.toggle-row label { color: #eee; font-size: 14px; cursor: pointer; }
.toggle-row input[type=checkbox] { width: 18px; height: 18px; cursor: pointer; accent-color: #0f0; }
</style></head>
<body>
<h2>Robot Head - Debug</h2>
<img class="stream" src="/stream" /><br>
<p>Camera feed with face detection overlay</p>

<div class="section">
<h3>Eye Style</h3>
<div id="styles-grid" class="styles-grid"></div>
<div class="toggle-row" style="margin-top:14px">
    <input type="checkbox" id="fps-toggle" onchange="toggleFps(this.checked)">
    <label for="fps-toggle">FPS overlay on right eye</label>
</div>
<div id="status-msg"></div>
</div>

<div id="moods-section" class="section" style="display:none">
<h3>Cartoon Mood</h3>
<div id="moods-grid" class="styles-grid"></div>
<div class="toggle-row">
    <input type="checkbox" id="glow-toggle" onchange="toggleGlow(this.checked)">
    <label for="glow-toggle">Glow effect (slower)</label>
</div>
<div id="mood-msg"></div>
</div>

<script>
function loadStyles() {
    fetch('/api/styles')
        .then(r => r.json())
        .then(styles => {
            const grid = document.getElementById('styles-grid');
            grid.innerHTML = '';
            styles.forEach(s => {
                const card = document.createElement('div');
                card.className = 'style-card' + (s.active ? ' active' : '');
                card.innerHTML = '<div class="name">' + s.name + '</div>' +
                    '<div class="type">' + s.id + '</div>';
                card.onclick = () => setStyle(s.id);
                grid.appendChild(card);
            });
            loadMoods();
        })
        .catch(() => {
            document.getElementById('styles-grid').innerHTML =
                '<div style="color:#f00">Failed to load styles</div>';
        });
}

function setStyle(id) {
    const msg = document.getElementById('status-msg');
    msg.textContent = 'Switching...';
    fetch('/api/styles/active', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: id})
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            msg.textContent = 'Switched to ' + id;
            loadStyles();
        } else {
            msg.textContent = 'Error: ' + (data.error || 'unknown');
            msg.style.color = '#f00';
        }
        setTimeout(() => { msg.textContent = ''; msg.style.color = '#0f0'; }, 2000);
    })
    .catch(() => {
        msg.textContent = 'Request failed';
        msg.style.color = '#f00';
    });
}

function loadMoods() {
    fetch('/api/moods')
        .then(r => r.json())
        .then(data => {
            const section = document.getElementById('moods-section');
            const grid = document.getElementById('moods-grid');
            if (!data.moods) {
                section.style.display = 'none';
                return;
            }
            section.style.display = '';
            grid.innerHTML = '';
            data.moods.forEach(m => {
                const card = document.createElement('div');
                card.className = 'style-card' + (m.active ? ' active' : '');
                card.innerHTML = '<div class="name">' + m.name + '</div>' +
                    '<div class="type">' + m.id + '</div>';
                card.onclick = () => setMood(m.id);
                grid.appendChild(card);
            });
            if (data.glow !== undefined) {
                document.getElementById('glow-toggle').checked = data.glow;
            }
        })
        .catch(() => {
            document.getElementById('moods-section').style.display = 'none';
        });
}

function toggleGlow(enabled) {
    fetch('/api/cartoon/glow', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({enabled: enabled})
    })
    .then(r => r.json())
    .then(data => {
        const msg = document.getElementById('mood-msg');
        if (data.ok) {
            msg.textContent = 'Glow ' + (enabled ? 'on' : 'off');
        } else {
            msg.textContent = 'Error: ' + (data.error || 'unknown');
            msg.style.color = '#f00';
        }
        setTimeout(() => { msg.textContent = ''; msg.style.color = '#0f0'; }, 2000);
    });
}

function setMood(id) {
    const msg = document.getElementById('mood-msg');
    msg.textContent = 'Switching mood...';
    fetch('/api/moods/active', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: id})
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            msg.textContent = 'Mood: ' + id;
            loadMoods();
        } else {
            msg.textContent = 'Error: ' + (data.error || 'unknown');
            msg.style.color = '#f00';
        }
        setTimeout(() => { msg.textContent = ''; msg.style.color = '#0f0'; }, 2000);
    })
    .catch(() => {
        msg.textContent = 'Request failed';
        msg.style.color = '#f00';
    });
}

function loadFpsState() {
    fetch('/api/fps-overlay')
        .then(r => r.json())
        .then(data => {
            document.getElementById('fps-toggle').checked = !!data.enabled;
        });
}

function toggleFps(enabled) {
    fetch('/api/fps-overlay', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({enabled: enabled})
    })
    .then(r => r.json())
    .then(data => {
        const msg = document.getElementById('status-msg');
        if (data.ok) {
            msg.textContent = 'FPS overlay ' + (enabled ? 'on' : 'off');
        } else {
            msg.textContent = 'Error';
            msg.style.color = '#f00';
        }
        setTimeout(() => { msg.textContent = ''; msg.style.color = '#0f0'; }, 2000);
    });
}

loadStyles();
loadFpsState();
</script>
</body></html>
"""


class DebugHandler(BaseHTTPRequestHandler):
    debug_state = None  # Set before starting server

    def do_GET(self):
        if self.path == "/":
            self._send_html(_INDEX_HTML)
        elif self.path == "/stream":
            self._send_stream()
        elif self.path == "/api/styles":
            self._send_json_styles()
        elif self.path == "/api/moods":
            self._send_json_moods()
        elif self.path == "/api/cartoon/glow":
            self._send_json_glow()
        elif self.path == "/api/fps-overlay":
            self._send_json_fps_overlay()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/styles/active":
            self._handle_set_style()
        elif self.path == "/api/moods/active":
            self._handle_set_mood()
        elif self.path == "/api/cartoon/glow":
            self._handle_set_glow()
        elif self.path == "/api/fps-overlay":
            self._handle_set_fps_overlay()
        else:
            self.send_response(404)
            self.end_headers()

    def _send_html(self, content: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_stream(self):
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

    def _send_json_styles(self):
        sm = self.debug_state.style_manager
        if sm is None:
            self._send_json([], 200)
            return
        self._send_json(sm.get_styles())

    def _handle_set_style(self):
        sm = self.debug_state.style_manager
        if sm is None:
            self._send_json({"ok": False, "error": "no style manager"}, 500)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            style_id = body.get("id", "")
        except (json.JSONDecodeError, ValueError):
            self._send_json({"ok": False, "error": "invalid JSON"}, 400)
            return

        if sm.set_active_style(style_id):
            save_state(sm, self.debug_state)
            self._send_json({"ok": True})
        else:
            self._send_json({"ok": False, "error": f"unknown style: {style_id}"}, 400)

    def _send_json_moods(self):
        sm = self.debug_state.style_manager
        if sm is None:
            self._send_json({"moods": None})
            return
        moods = sm.get_cartoon_moods()
        glow = sm.get_cartoon_glow()
        self._send_json({"moods": moods, "glow": glow})

    def _handle_set_mood(self):
        sm = self.debug_state.style_manager
        if sm is None:
            self._send_json({"ok": False, "error": "no style manager"}, 500)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            mood_id = body.get("id", "")
        except (json.JSONDecodeError, ValueError):
            self._send_json({"ok": False, "error": "invalid JSON"}, 400)
            return

        if sm.set_cartoon_mood(mood_id):
            save_state(sm, self.debug_state)
            self._send_json({"ok": True})
        else:
            self._send_json({"ok": False, "error": f"unknown mood: {mood_id}"}, 400)

    def _send_json_glow(self):
        sm = self.debug_state.style_manager
        if sm is None:
            self._send_json({"glow": None})
            return
        glow = sm.get_cartoon_glow()
        self._send_json({"glow": glow})

    def _handle_set_glow(self):
        sm = self.debug_state.style_manager
        if sm is None:
            self._send_json({"ok": False, "error": "no style manager"}, 500)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            enabled = bool(body.get("enabled", False))
        except (json.JSONDecodeError, ValueError):
            self._send_json({"ok": False, "error": "invalid JSON"}, 400)
            return

        if sm.set_cartoon_glow(enabled):
            save_state(sm, self.debug_state)
            self._send_json({"ok": True})
        else:
            self._send_json({"ok": False, "error": "not in cartoon mode"}, 400)

    def _send_json_fps_overlay(self):
        self._send_json({"enabled": self.debug_state.show_fps})

    def _handle_set_fps_overlay(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            enabled = bool(body.get("enabled", False))
        except (json.JSONDecodeError, ValueError):
            self._send_json({"ok": False, "error": "invalid JSON"}, 400)
            return
        self.debug_state.show_fps = enabled
        save_state(self.debug_state.style_manager, self.debug_state)
        self._send_json({"ok": True})

    def log_message(self, format, *args):
        pass  # Suppress request logging


def start_debug_server(debug_state: DebugState, port: int = 8080):
    """Start the debug web server in a daemon thread."""
    DebugHandler.debug_state = debug_state
    server = ThreadingHTTPServer(("0.0.0.0", port), DebugHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
