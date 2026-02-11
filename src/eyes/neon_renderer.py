"""Neon ring eye renderer — glowing hollow ring with mood color variants."""

import math
import time
from PIL import Image, ImageDraw, ImageFilter, ImageChops

from src.eyes.eye_state import EyeState
from src.config import EyeConfig


NEON_MOODS = {
    "default": {
        "id": "default", "name": "Default",
        "color": (0, 255, 120), "pulse_speed": 2.0,
        "ring_width": 10, "ring_radius": 55,
    },
    "plasma": {
        "id": "plasma", "name": "Plasma",
        "color": (200, 0, 255), "pulse_speed": 3.0,
        "ring_width": 14, "ring_radius": 55,
    },
    "solar": {
        "id": "solar", "name": "Solar",
        "color": (255, 160, 0), "pulse_speed": 1.5,
        "ring_width": 12, "ring_radius": 60,
    },
    "ice": {
        "id": "ice", "name": "Ice",
        "color": (140, 200, 255), "pulse_speed": 1.0,
        "ring_width": 8, "ring_radius": 50,
    },
    "rage": {
        "id": "rage", "name": "Rage",
        "color": (255, 20, 0), "pulse_speed": 6.0,
        "ring_width": 16, "ring_radius": 65,
    },
    "calm": {
        "id": "calm", "name": "Calm",
        "color": (40, 100, 255), "pulse_speed": 0.5,
        "ring_width": 8, "ring_radius": 45,
    },
}


class NeonEyeRenderer:
    """Renders a glowing neon ring eye that follows gaze."""

    SIZE = 240
    CENTER = 120
    GLOW_RADIUS = 8

    def __init__(self, config: EyeConfig, is_left: bool = True):
        self._max_offset = config.pupil_max_offset
        self._is_left = is_left
        self._img = Image.new("RGB", (self.SIZE, self.SIZE), (0, 0, 0))
        self._ring_layer = Image.new("RGB", (self.SIZE, self.SIZE), (0, 0, 0))
        self._ring_draw = ImageDraw.Draw(self._ring_layer)
        self._draw = ImageDraw.Draw(self._img)
        self._mood_id = "default"
        self.glow_enabled = True  # glow on by default for neon

    @property
    def mood_id(self):
        return self._mood_id

    def get_moods(self) -> list[dict]:
        return [{"id": m["id"], "name": m["name"]} for m in NEON_MOODS.values()]

    def set_mood(self, mood_id: str) -> bool:
        if mood_id not in NEON_MOODS:
            return False
        self._mood_id = mood_id
        return True

    def render(self, state: EyeState) -> Image.Image:
        mood = NEON_MOODS[self._mood_id]
        color = mood["color"]
        pulse_speed = mood["pulse_speed"]
        ring_width = mood["ring_width"]
        ring_radius = mood["ring_radius"]
        dim_color = tuple(c // 3 for c in color)

        d = self._ring_draw
        d.rectangle([0, 0, self.SIZE - 1, self.SIZE - 1], fill=(0, 0, 0))

        cx = self.CENTER + state.pupil_x * self._max_offset
        cy = self.CENTER + state.pupil_y * self._max_offset

        # Blink: shrink ring vertically
        scale_y = 1.0 - state.upper_eyelid * 0.95
        if scale_y < 0.05:
            self._img.paste((0, 0, 0), (0, 0, self.SIZE, self.SIZE))
            return self._img

        # Pulse brightness
        now = time.monotonic()
        pulse = 0.7 + 0.3 * math.sin(now * pulse_speed * 2 * math.pi)
        live_color = tuple(int(c * pulse) for c in color)

        # Main ring
        rx = ring_radius
        ry = ring_radius * scale_y
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
                  outline=live_color, width=ring_width)

        # Inner dot
        dot_r = 6 * scale_y
        d.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
                  fill=live_color)

        # Orbital accent dots
        orbit_r = ring_radius + 18
        for i in range(3):
            angle = math.radians((now * 60 + i * 120) % 360)
            ox = cx + orbit_r * math.cos(angle)
            oy = cy + orbit_r * math.sin(angle) * scale_y
            dr = 3
            d.ellipse([ox - dr, oy - dr, ox + dr, oy + dr], fill=dim_color)

        # Apply glow if enabled
        if self.glow_enabled:
            glow = self._ring_layer.filter(
                ImageFilter.BoxBlur(radius=self.GLOW_RADIUS))
            self._img.paste(glow, (0, 0))
            self._img.paste(
                self._ring_layer, (0, 0),
                self._ring_layer.convert("L"),
            )
        else:
            self._img.paste(self._ring_layer, (0, 0))

        # Clip to round display
        self._clip_circle(self._draw)

        return self._img

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
            d.polygon(points, fill=(0, 0, 0))
