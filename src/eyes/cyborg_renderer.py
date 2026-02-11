"""Cyborg targeting reticle eye renderer with mood variants."""

import math
import time
from PIL import Image, ImageDraw

from src.eyes.eye_state import EyeState
from src.config import EyeConfig


CYBORG_MOODS = {
    "normal": {
        "id": "normal", "name": "Normal",
        "primary": (0, 200, 255), "dim": (0, 80, 120),
        "accent": (255, 60, 30), "scan_speed": 90,
    },
    "alert": {
        "id": "alert", "name": "Alert",
        "primary": (255, 40, 20), "dim": (120, 20, 10),
        "accent": (255, 200, 0), "scan_speed": 200,
    },
    "scanning": {
        "id": "scanning", "name": "Scanning",
        "primary": (0, 255, 80), "dim": (0, 100, 40),
        "accent": (200, 255, 200), "scan_speed": 45,
    },
    "locked": {
        "id": "locked", "name": "Locked On",
        "primary": (255, 160, 0), "dim": (120, 70, 0),
        "accent": (255, 50, 0), "scan_speed": 300,
    },
    "stealth": {
        "id": "stealth", "name": "Stealth",
        "primary": (30, 60, 120), "dim": (15, 30, 60),
        "accent": (60, 80, 160), "scan_speed": 30,
    },
    "malfunction": {
        "id": "malfunction", "name": "Malfunction",
        "primary": (255, 0, 255), "dim": (80, 0, 80),
        "accent": (255, 255, 0), "scan_speed": 500,
    },
}


class CyborgEyeRenderer:
    """Renders a targeting reticle eye with crosshairs, rings, and scan line."""

    SIZE = 240
    CENTER = 120
    BG = (0, 0, 0)

    def __init__(self, config: EyeConfig, is_left: bool = True):
        self._max_offset = config.pupil_max_offset
        self._is_left = is_left
        self._img = Image.new("RGB", (self.SIZE, self.SIZE), self.BG)
        self._draw = ImageDraw.Draw(self._img)
        self._mood_id = "normal"
        self.glow_enabled = False

    @property
    def mood_id(self):
        return self._mood_id

    def get_moods(self) -> list[dict]:
        return [{"id": m["id"], "name": m["name"]} for m in CYBORG_MOODS.values()]

    def set_mood(self, mood_id: str) -> bool:
        if mood_id not in CYBORG_MOODS:
            return False
        self._mood_id = mood_id
        return True

    def render(self, state: EyeState) -> Image.Image:
        d = self._draw
        d.rectangle([0, 0, self.SIZE - 1, self.SIZE - 1], fill=self.BG)

        mood = CYBORG_MOODS[self._mood_id]
        primary = mood["primary"]
        dim = mood["dim"]
        accent = mood["accent"]
        scan_speed = mood["scan_speed"]

        cx = self.CENTER + state.pupil_x * self._max_offset
        cy = self.CENTER + state.pupil_y * self._max_offset

        # Apply blink by squashing vertically
        scale_y = 1.0 - state.upper_eyelid * 0.95
        if scale_y < 0.05:
            return self._img

        # Malfunction jitter
        if self._mood_id == "malfunction":
            now = time.monotonic()
            jx = math.sin(now * 47) * 5
            jy = math.cos(now * 31) * 4
            cx += jx
            cy += jy

        # Outer ring
        self._ellipse(d, cx, cy, 95, 95 * scale_y, dim, width=2)

        # Middle ring
        self._ellipse(d, cx, cy, 65, 65 * scale_y, primary, width=2)

        # Inner ring
        self._ellipse(d, cx, cy, 30, 30 * scale_y, primary, width=1)

        # Crosshairs
        gap = 12
        line_len = 100
        d.line([(cx - line_len, cy), (cx - gap, cy)], fill=primary, width=1)
        d.line([(cx + gap, cy), (cx + line_len, cy)], fill=primary, width=1)
        if scale_y > 0.3:
            v_gap = gap * scale_y
            v_len = line_len * scale_y
            d.line([(cx, cy - v_len), (cx, cy - v_gap)], fill=primary, width=1)
            d.line([(cx, cy + v_gap), (cx, cy + v_len)], fill=primary, width=1)

        # Center dot
        dot_r = 4 * scale_y
        d.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
                  fill=accent)

        # Tick marks on outer ring
        self._draw_ticks(d, cx, cy, 95, scale_y, dim)

        # Rotating scan line
        now = time.monotonic()
        angle = (now * scan_speed) % 360
        rad = math.radians(angle)
        scan_r = 85
        sx = cx + scan_r * math.cos(rad)
        sy = cy + scan_r * math.sin(rad) * scale_y
        d.line([(cx, cy), (sx, sy)], fill=primary, width=1)

        # Clip to circular display area
        self._clip_circle(d)

        return self._img

    def _ellipse(self, d, cx, cy, rx, ry, color, width=1):
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
                  outline=color, width=width)

    def _draw_ticks(self, d, cx, cy, r, scale_y, color):
        for i in range(12):
            angle = math.radians(i * 30)
            inner = r - 8
            outer = r
            x1 = cx + inner * math.cos(angle)
            y1 = cy + inner * math.sin(angle) * scale_y
            x2 = cx + outer * math.cos(angle)
            y2 = cy + outer * math.sin(angle) * scale_y
            d.line([(x1, y1), (x2, y2)], fill=color, width=1)

    def _clip_circle(self, d):
        r = 118
        cx = cy = self.CENTER
        steps = 60
        for corner_x, corner_y, start_a, end_a in [
            (0, 0, 180, 270),
            (self.SIZE, 0, 270, 360),
            (self.SIZE, self.SIZE, 0, 90),
            (0, self.SIZE, 90, 180),
        ]:
            points = [(corner_x, corner_y)]
            for i in range(steps + 1):
                a = math.radians(start_a + (end_a - start_a) * i / steps)
                points.append((cx + r * math.cos(a), cy + r * math.sin(a)))
            d.polygon(points, fill=self.BG)
