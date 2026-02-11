"""Astro Bot-inspired eye renderer — blue LED eyes on dark screen with expressive moods."""

import math
import time
from PIL import Image, ImageDraw

from src.eyes.eye_state import EyeState
from src.config import EyeConfig


# Astro blue palette
ASTRO_BLUE = (0, 180, 255)
ASTRO_BRIGHT = (80, 220, 255)
ASTRO_DIM = (0, 80, 140)
HIGHLIGHT = (255, 255, 255)
SCREEN_BG = (5, 8, 15)

ASTRO_MOODS = {
    "neutral": {
        "id": "neutral", "name": "Neutral",
        "desc": "Default rounded oval eyes",
    },
    "happy": {
        "id": "happy", "name": "Happy",
        "desc": "Upward arc eyes (^_^)",
    },
    "excited": {
        "id": "excited", "name": "Excited",
        "desc": "Large round sparkling eyes",
    },
    "sad": {
        "id": "sad", "name": "Sad",
        "desc": "Drooping downturned eyes",
    },
    "angry": {
        "id": "angry", "name": "Angry",
        "desc": "Angled inward slanted eyes",
    },
    "surprised": {
        "id": "surprised", "name": "Surprised",
        "desc": "Wide open round eyes",
    },
    "love": {
        "id": "love", "name": "Love",
        "desc": "Heart-shaped eyes",
    },
    "star": {
        "id": "star", "name": "Star Eyes",
        "desc": "Star-shaped amazed eyes",
    },
    "dizzy": {
        "id": "dizzy", "name": "Dizzy",
        "desc": "Spiral dazed eyes",
    },
    "tired": {
        "id": "tired", "name": "Tired",
        "desc": "Half-closed droopy eyes",
    },
    "wink": {
        "id": "wink", "name": "Wink",
        "desc": "One eye winking",
    },
    "determined": {
        "id": "determined", "name": "Determined",
        "desc": "Narrowed focused eyes",
    },
    "worried": {
        "id": "worried", "name": "Worried",
        "desc": "Uneven anxious eyes",
    },
    "celebrating": {
        "id": "celebrating", "name": "Celebrating",
        "desc": "Sparkling party eyes",
    },
}


def _star_points(cx, cy, outer_r, inner_r, points=5, rotation=0):
    """Generate star polygon vertices."""
    result = []
    for i in range(points * 2):
        angle = math.radians(rotation + i * 180 / points - 90)
        r = outer_r if i % 2 == 0 else inner_r
        result.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return result


def _heart_points(cx, cy, w, h, n=40):
    """Generate heart shape as polygon points."""
    points = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) -
              2 * math.cos(3 * t) - math.cos(4 * t))
        points.append((cx + x * w / 34.0, cy + y * h / 34.0))
    return points


class AstroEyeRenderer:
    """Renders one Astro Bot-inspired LED eye with expressive mood shapes."""

    SIZE = 240
    CENTER = 120

    # Eye positioning — offset from center of display
    EYE_OFFSET_X = 0   # adjusted per mood
    GAZE_RANGE_X = 40
    GAZE_RANGE_Y = 30

    TRANSITION_DURATION = 0.2

    def __init__(self, config: EyeConfig, is_left: bool = True):
        self._config = config
        self._is_left = is_left
        self._img = Image.new("RGB", (self.SIZE, self.SIZE), SCREEN_BG)
        self._draw = ImageDraw.Draw(self._img)

        self._mood_id = "neutral"
        self._prev_mood_id = "neutral"
        self._transition_start = 0.0
        self._transitioning = False
        self.glow_enabled = False

    @property
    def mood_id(self):
        return self._mood_id

    def get_moods(self) -> list[dict]:
        return [{"id": m["id"], "name": m["name"]} for m in ASTRO_MOODS.values()]

    def set_mood(self, mood_id: str) -> bool:
        if mood_id not in ASTRO_MOODS:
            return False
        if mood_id == self._mood_id:
            return True
        self._prev_mood_id = self._mood_id
        self._mood_id = mood_id
        self._transition_start = time.monotonic()
        self._transitioning = True
        return True

    def render(self, state: EyeState) -> Image.Image:
        d = self._draw
        d.rectangle([0, 0, self.SIZE - 1, self.SIZE - 1], fill=SCREEN_BG)

        # Gaze offset
        cx = self.CENTER + state.pupil_x * self.GAZE_RANGE_X
        cy = self.CENTER + state.pupil_y * self.GAZE_RANGE_Y

        # Blink: scale_y controls vertical squash
        scale_y = 1.0 - state.upper_eyelid * 0.95
        if scale_y < 0.05:
            self._clip_circle(d)
            return self._img

        # Transition alpha
        if self._transitioning:
            elapsed = time.monotonic() - self._transition_start
            t = min(1.0, elapsed / self.TRANSITION_DURATION)
            if t >= 1.0:
                self._transitioning = False
        else:
            t = 1.0

        # Draw the current mood's eye shape
        self._draw_mood(d, self._mood_id, cx, cy, scale_y)

        # Clip to round display
        self._clip_circle(d)

        return self._img

    def _draw_mood(self, d, mood_id, cx, cy, scale_y):
        """Dispatch to the appropriate mood drawing method."""
        method = getattr(self, f"_draw_{mood_id}", None)
        if method:
            method(d, cx, cy, scale_y)
        else:
            self._draw_neutral(d, cx, cy, scale_y)

    # --- Mood renderers ---

    def _draw_neutral(self, d, cx, cy, scale_y):
        """Default: rounded oval eyes, slightly tilted inward."""
        w, h = 60, 80
        h = h * scale_y
        r = 25
        tilt = 8 if self._is_left else -8
        self._rounded_rect(d, cx, cy + tilt * 0.3, w, h, r, ASTRO_BLUE)
        self._highlight(d, cx - 10, cy - h * 0.25, 8, 5)

    def _draw_happy(self, d, cx, cy, scale_y):
        """Upward arc eyes — (^_^) style."""
        w = 70
        h = 50 * scale_y
        lw = 14
        bbox = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
        d.arc(bbox, start=200, end=340, fill=ASTRO_BLUE, width=lw)
        # Small sparkle
        sx = cx + (15 if self._is_left else -15)
        sy = cy - h * 0.4
        self._dot(d, sx, sy, 4, ASTRO_BRIGHT)

    def _draw_excited(self, d, cx, cy, scale_y):
        """Large round sparkling eyes."""
        r = 50 * scale_y
        self._circle(d, cx, cy, r, ASTRO_BLUE)
        # Big highlight
        self._highlight(d, cx - 15, cy - 15, 12, 8)
        # Small secondary highlight
        self._dot(d, cx + 12, cy + 10, 5, ASTRO_BRIGHT)
        # Sparkle crosses
        now = time.monotonic()
        sparkle_r = 58 + 5 * math.sin(now * 4)
        for i in range(4):
            angle = math.radians(now * 60 + i * 90)
            sx = cx + sparkle_r * math.cos(angle) * 0.7
            sy = cy + sparkle_r * math.sin(angle) * scale_y * 0.7
            self._dot(d, sx, sy, 3, ASTRO_BRIGHT)

    def _draw_sad(self, d, cx, cy, scale_y):
        """Drooping downturned eyes."""
        w, h = 60, 65
        h = h * scale_y
        r = 20
        # Tilt downward on outer edge
        tilt = -12 if self._is_left else 12
        # Draw main eye shape shifted down slightly
        self._rounded_rect(d, cx, cy + 8, w, h, r, ASTRO_DIM)
        # Droopy eyelid effect — dark arc at top
        lid_w = w + 10
        lid_h = 30
        lid_bbox = [cx - lid_w / 2, cy - 10, cx + lid_w / 2, cy + lid_h - 10]
        tilt_y = -6 if self._is_left else 6
        # Angled dark bar at top of eye
        pts = [
            (cx - w / 2 - 5, cy - h / 2 + 8 + tilt_y),
            (cx + w / 2 + 5, cy - h / 2 + 8 - tilt_y),
            (cx + w / 2 + 5, cy - h / 2 - 10 - tilt_y),
            (cx - w / 2 - 5, cy - h / 2 - 10 + tilt_y),
        ]
        d.polygon(pts, fill=SCREEN_BG)
        self._highlight(d, cx - 8, cy - 5, 6, 4)

    def _draw_angry(self, d, cx, cy, scale_y):
        """Angled inward slanted eyes — V shape brow."""
        w, h = 70, 55
        h = h * scale_y
        r = 18
        self._rounded_rect(d, cx, cy, w, h, r, ASTRO_BLUE)
        # Angry brow — thick dark triangle at top
        inward = -1 if self._is_left else 1
        pts = [
            (cx - w / 2 - 8, cy - h / 2 - 4 + 20 * inward),
            (cx + w / 2 + 8, cy - h / 2 - 4 - 20 * inward),
            (cx + w / 2 + 8, cy - h / 2 - 22 - 20 * inward),
            (cx - w / 2 - 8, cy - h / 2 - 22 + 20 * inward),
        ]
        d.polygon(pts, fill=SCREEN_BG)
        # Red tinge at edges
        self._highlight(d, cx - 8, cy - 5, 5, 3)

    def _draw_surprised(self, d, cx, cy, scale_y):
        """Wide open round eyes."""
        r = 55 * scale_y
        self._circle(d, cx, cy, r, ASTRO_BLUE)
        # Inner dark pupil
        pr = 20 * scale_y
        self._circle(d, cx, cy, pr, SCREEN_BG)
        # Bright ring
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  outline=ASTRO_BRIGHT, width=3)
        self._highlight(d, cx - 15, cy - 18, 10, 7)

    def _draw_love(self, d, cx, cy, scale_y):
        """Heart-shaped eyes."""
        w = 70
        h = 65 * scale_y
        points = _heart_points(cx, cy - 5, w, h)
        d.polygon(points, fill=(255, 60, 150))
        # Highlight
        self._highlight(d, cx - 12, cy - h * 0.3, 7, 5)

    def _draw_star(self, d, cx, cy, scale_y):
        """Star-shaped amazed eyes."""
        outer = 50 * scale_y
        inner = 22 * scale_y
        # Slowly rotate
        now = time.monotonic()
        rot = (now * 30) % 360
        points = _star_points(cx, cy, outer, inner, points=5, rotation=rot)
        d.polygon(points, fill=ASTRO_BRIGHT)
        # Center dot
        self._dot(d, cx, cy, 6 * scale_y, HIGHLIGHT)

    def _draw_dizzy(self, d, cx, cy, scale_y):
        """Spiral dazed eyes."""
        now = time.monotonic()
        rot_offset = now * 120  # degrees per second
        r_max = 40 * scale_y
        steps = 80
        for i in range(1, steps):
            t = i / steps
            r = r_max * t
            angle = math.radians(t * 720 + rot_offset)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle) * scale_y
            dot_size = 2 + t * 2
            alpha = t
            color = (
                int(ASTRO_BLUE[0] * alpha),
                int(ASTRO_BLUE[1] * alpha),
                int(ASTRO_BLUE[2] * alpha),
            )
            d.ellipse([x - dot_size, y - dot_size,
                       x + dot_size, y + dot_size], fill=color)

    def _draw_tired(self, d, cx, cy, scale_y):
        """Half-closed droopy eyes."""
        w, h = 70, 35
        h = h * scale_y
        r = 15
        # Flat, low eye
        self._rounded_rect(d, cx, cy + 15, w, h, r, ASTRO_DIM)
        self._highlight(d, cx - 10, cy + 8, 5, 3)

    def _draw_wink(self, d, cx, cy, scale_y):
        """One eye open, one winking arc."""
        if self._is_left:
            # Left eye: open normal
            w, h = 60, 80
            h = h * scale_y
            self._rounded_rect(d, cx, cy, w, h, 25, ASTRO_BLUE)
            self._highlight(d, cx - 10, cy - h * 0.25, 8, 5)
        else:
            # Right eye: winking arc
            w = 65
            h = 40 * scale_y
            lw = 14
            bbox = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
            d.arc(bbox, start=10, end=170, fill=ASTRO_BLUE, width=lw)

    def _draw_determined(self, d, cx, cy, scale_y):
        """Narrowed focused eyes."""
        w, h = 80, 40
        h = h * scale_y
        r = 15
        self._rounded_rect(d, cx, cy, w, h, r, ASTRO_BLUE)
        # Slight inward angle
        inward = -1 if self._is_left else 1
        pts = [
            (cx - w / 2 - 5, cy - h / 2 - 2 + 8 * inward),
            (cx + w / 2 + 5, cy - h / 2 - 2 - 8 * inward),
            (cx + w / 2 + 5, cy - h / 2 - 14 - 8 * inward),
            (cx - w / 2 - 5, cy - h / 2 - 14 + 8 * inward),
        ]
        d.polygon(pts, fill=SCREEN_BG)
        self._highlight(d, cx - 8, cy - 5, 6, 4)

    def _draw_worried(self, d, cx, cy, scale_y):
        """Uneven anxious eyes — one slightly higher."""
        w, h = 55, 70
        h = h * scale_y
        r = 22
        y_shift = -8 if self._is_left else 8
        self._rounded_rect(d, cx, cy + y_shift, w, h, r, ASTRO_BLUE)
        # Worried brow — slight upward angle on inner side
        inward = 1 if self._is_left else -1
        pts = [
            (cx - w / 2 - 5, cy + y_shift - h / 2 - 2 - 10 * inward),
            (cx + w / 2 + 5, cy + y_shift - h / 2 - 2 + 10 * inward),
            (cx + w / 2 + 5, cy + y_shift - h / 2 - 14 + 10 * inward),
            (cx - w / 2 - 5, cy + y_shift - h / 2 - 14 - 10 * inward),
        ]
        d.polygon(pts, fill=SCREEN_BG)
        self._highlight(d, cx - 8, cy + y_shift - h * 0.2, 6, 4)

    def _draw_celebrating(self, d, cx, cy, scale_y):
        """Sparkling party eyes with animated sparkles."""
        # Base: excited round eye
        r = 45 * scale_y
        self._circle(d, cx, cy, r, ASTRO_BLUE)
        self._highlight(d, cx - 12, cy - 12, 10, 7)

        # Animated sparkles around the eye
        now = time.monotonic()
        for i in range(6):
            angle = math.radians(now * 80 + i * 60)
            dist = 60 + 8 * math.sin(now * 3 + i)
            sx = cx + dist * math.cos(angle) * 0.8
            sy = cy + dist * math.sin(angle) * scale_y * 0.8
            # Draw tiny 4-pointed star
            sr = 4 + 2 * math.sin(now * 5 + i * 2)
            pts = _star_points(sx, sy, sr, sr * 0.3, points=4,
                               rotation=(now * 90 + i * 45) % 360)
            d.polygon(pts, fill=ASTRO_BRIGHT)

    # --- Drawing helpers ---

    def _rounded_rect(self, d, cx, cy, w, h, r, color):
        r = min(r, int(w) // 2, int(h) // 2)
        d.rounded_rectangle(
            [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2],
            radius=r, fill=color,
        )

    def _circle(self, d, cx, cy, r, color):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

    def _dot(self, d, cx, cy, r, color):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

    def _highlight(self, d, x, y, w, h):
        """Small white specular highlight — Astro Bot signature."""
        d.ellipse([x - w / 2, y - h / 2, x + w / 2, y + h / 2],
                  fill=HIGHLIGHT)

    def _clip_circle(self, d):
        """Black out corners outside the round display."""
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
            d.polygon(points, fill=SCREEN_BG)
