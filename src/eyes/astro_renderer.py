"""Astro Bot-inspired eye renderer — blue LED dot-matrix eyes with glow on dark screen."""

import math
import time
from PIL import Image, ImageDraw, ImageFilter

from src.eyes.eye_state import EyeState
from src.config import EyeConfig


# Astro blue palette — rich saturated blue like the real thing
ASTRO_BLUE = (20, 100, 255)
ASTRO_BRIGHT = (60, 160, 255)
ASTRO_DIM = (10, 50, 160)
SCREEN_BG = (2, 3, 8)

# LED dot matrix settings
DOT_SPACING = 6      # pixels between dot centers
DOT_RADIUS = 2.0     # radius of each LED dot
GLOW_RADIUS = 10     # blur radius for the glow effect

ASTRO_MOODS = {
    "neutral": {"id": "neutral", "name": "Neutral"},
    "happy": {"id": "happy", "name": "Happy"},
    "excited": {"id": "excited", "name": "Excited"},
    "sad": {"id": "sad", "name": "Sad"},
    "angry": {"id": "angry", "name": "Angry"},
    "surprised": {"id": "surprised", "name": "Surprised"},
    "love": {"id": "love", "name": "Love"},
    "star": {"id": "star", "name": "Star Eyes"},
    "dizzy": {"id": "dizzy", "name": "Dizzy"},
    "tired": {"id": "tired", "name": "Tired"},
    "wink": {"id": "wink", "name": "Wink"},
    "determined": {"id": "determined", "name": "Determined"},
    "worried": {"id": "worried", "name": "Worried"},
    "celebrating": {"id": "celebrating", "name": "Celebrating"},
    "scared": {"id": "scared", "name": "Scared"},
    "crying": {"id": "crying", "name": "Crying"},
    "laughing": {"id": "laughing", "name": "Laughing"},
    "x_eyes": {"id": "x_eyes", "name": "Stunned"},
    "confused": {"id": "confused", "name": "Confused"},
    "sleepy": {"id": "sleepy", "name": "Sleepy"},
    "mischievous": {"id": "mischievous", "name": "Mischievous"},
}


def _star_points(cx, cy, outer_r, inner_r, points=5, rotation=0):
    result = []
    for i in range(points * 2):
        angle = math.radians(rotation + i * 180 / points - 90)
        r = outer_r if i % 2 == 0 else inner_r
        result.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return result


def _heart_contains(px, py, cx, cy, w, h):
    """Check if point (px, py) is inside a heart shape centered at (cx, cy)."""
    # Normalize to parametric heart space (-17..17)
    nx = (px - cx) / w * 34.0
    ny = -(py - cy) / h * 34.0  # flip y
    # Heart implicit: (x^2 + y^2 - 1)^3 - x^2 * y^3 < 0
    # Simplified heart test
    nx2 = (nx / 16.0)
    ny2 = (ny + 2) / 17.0
    val = (nx2 * nx2 + ny2 * ny2 - 1)
    val = val * val * val - nx2 * nx2 * ny2 * ny2 * ny2
    return val < 0


class AstroEyeRenderer:
    """Renders one Astro Bot-inspired LED dot-matrix eye with glow."""

    SIZE = 240
    CENTER = 120

    GAZE_RANGE_X = 35
    GAZE_RANGE_Y = 25

    def __init__(self, config: EyeConfig, is_left: bool = True):
        self._config = config
        self._is_left = is_left

        # Shape layer: draw shapes here, then sample for dot mask
        self._shape = Image.new("RGB", (self.SIZE, self.SIZE), SCREEN_BG)
        self._shape_draw = ImageDraw.Draw(self._shape)

        # Dot layer: LED dots drawn here
        self._dots = Image.new("RGB", (self.SIZE, self.SIZE), SCREEN_BG)
        self._dots_draw = ImageDraw.Draw(self._dots)

        # Final composited image
        self._img = Image.new("RGB", (self.SIZE, self.SIZE), SCREEN_BG)

        self._mood_id = "neutral"
        self.glow_enabled = True  # glow always on — it's the Astro look

        # Pre-compute dot grid positions
        self._dot_grid = []
        for y in range(0, self.SIZE, DOT_SPACING):
            for x in range(0, self.SIZE, DOT_SPACING):
                self._dot_grid.append((x + DOT_SPACING // 2,
                                       y + DOT_SPACING // 2))

    @property
    def mood_id(self):
        return self._mood_id

    def get_moods(self) -> list[dict]:
        return [{"id": m["id"], "name": m["name"]} for m in ASTRO_MOODS.values()]

    def set_mood(self, mood_id: str) -> bool:
        if mood_id not in ASTRO_MOODS:
            return False
        self._mood_id = mood_id
        return True

    def render(self, state: EyeState) -> Image.Image:
        sd = self._shape_draw
        dd = self._dots_draw

        # Clear both layers
        sd.rectangle([0, 0, self.SIZE - 1, self.SIZE - 1], fill=SCREEN_BG)
        dd.rectangle([0, 0, self.SIZE - 1, self.SIZE - 1], fill=SCREEN_BG)

        # Gaze offset
        cx = self.CENTER + state.pupil_x * self.GAZE_RANGE_X
        cy = self.CENTER + state.pupil_y * self.GAZE_RANGE_Y

        # Blink
        scale_y = 1.0 - state.upper_eyelid * 0.95
        if scale_y < 0.05:
            self._img.paste(SCREEN_BG, (0, 0, self.SIZE, self.SIZE))
            self._clip_circle_img()
            return self._img

        # Draw the shape onto the shape layer (solid fill)
        self._draw_mood(sd, self._mood_id, cx, cy, scale_y)

        # Sample the shape layer to create LED dot pattern
        shape_data = self._shape.load()
        r = DOT_RADIUS
        for gx, gy in self._dot_grid:
            # Sample the shape layer at this grid position
            sx = min(max(int(gx), 0), self.SIZE - 1)
            sy = min(max(int(gy), 0), self.SIZE - 1)
            pixel = shape_data[sx, sy]
            # If the pixel is not background, draw a dot
            if pixel[0] > 10 or pixel[1] > 10 or pixel[2] > 10:
                dd.ellipse([gx - r, gy - r, gx + r, gy + r], fill=pixel)

        # Composite: glow (blurred dots) + sharp dots on top
        glow = self._dots.filter(ImageFilter.GaussianBlur(radius=GLOW_RADIUS))
        self._img.paste(glow, (0, 0))
        # Paste dots on top using their luminance as mask
        self._img.paste(self._dots, (0, 0), self._dots.convert("L"))

        # Clip to round display
        self._clip_circle_img()

        return self._img

    def _draw_mood(self, d, mood_id, cx, cy, scale_y):
        method = getattr(self, f"_draw_{mood_id}", None)
        if method:
            method(d, cx, cy, scale_y)
        else:
            self._draw_neutral(d, cx, cy, scale_y)

    # --- Mood renderers (draw solid shapes on shape layer) ---

    def _draw_neutral(self, d, cx, cy, scale_y):
        """Soft tapered oval — wider at top, narrower at bottom."""
        w_top, w_bot = 65, 50
        h = 90 * scale_y
        self._tapered_oval(d, cx, cy, w_top, w_bot, h, ASTRO_BLUE)

    def _draw_happy(self, d, cx, cy, scale_y):
        """Upward arc eyes — squinted happy (^_^)."""
        w_top, w_bot = 70, 55
        h = 50 * scale_y
        self._tapered_oval(d, cx, cy + 5, w_top, w_bot, h, ASTRO_BLUE)
        # Cut out top portion to create arc effect
        cut_h = h * 0.5
        d.rectangle([cx - w_top, cy + 5 - h / 2,
                     cx + w_top, cy + 5 - h / 2 + cut_h], fill=SCREEN_BG)

    def _draw_excited(self, d, cx, cy, scale_y):
        """Large round eyes."""
        r = 55 * scale_y
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ASTRO_BRIGHT)

    def _draw_sad(self, d, cx, cy, scale_y):
        """Drooping eyes — angled down on outer edge."""
        w_top, w_bot = 60, 50
        h = 70 * scale_y
        self._tapered_oval(d, cx, cy + 10, w_top, w_bot, h, ASTRO_DIM)
        # Angled eyelid cut at top
        tilt = -15 if self._is_left else 15
        pts = [
            (cx - w_top - 5, cy + 10 - h / 2 + 10 + tilt),
            (cx + w_top + 5, cy + 10 - h / 2 + 10 - tilt),
            (cx + w_top + 5, cy + 10 - h / 2 - 15),
            (cx - w_top - 5, cy + 10 - h / 2 - 15),
        ]
        d.polygon(pts, fill=SCREEN_BG)

    def _draw_angry(self, d, cx, cy, scale_y):
        """Angled inward — V brow cut."""
        w_top, w_bot = 70, 55
        h = 60 * scale_y
        self._tapered_oval(d, cx, cy, w_top, w_bot, h, ASTRO_BLUE)
        # V-shaped brow cut
        inward = -1 if self._is_left else 1
        pts = [
            (cx - w_top - 5, cy - h / 2 + 5 + 25 * inward),
            (cx + w_top + 5, cy - h / 2 + 5 - 25 * inward),
            (cx + w_top + 5, cy - h / 2 - 20),
            (cx - w_top - 5, cy - h / 2 - 20),
        ]
        d.polygon(pts, fill=SCREEN_BG)

    def _draw_surprised(self, d, cx, cy, scale_y):
        """Wide open round eyes."""
        r = 60 * scale_y
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ASTRO_BRIGHT)
        # Dark inner pupil
        pr = 22 * scale_y
        d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=SCREEN_BG)

    def _draw_love(self, d, cx, cy, scale_y):
        """Heart-shaped eyes — blue like the reference."""
        w, h = 75, 70 * scale_y
        # Draw heart using parametric polygon
        points = []
        n = 50
        for i in range(n):
            t = 2 * math.pi * i / n
            x = 16 * math.sin(t) ** 3
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t) -
                  2 * math.cos(3 * t) - math.cos(4 * t))
            points.append((cx + x * w / 34.0, cy + y * h / 34.0))
        d.polygon(points, fill=ASTRO_BLUE)

    def _draw_star(self, d, cx, cy, scale_y):
        """Star-shaped eyes — slowly rotating."""
        now = time.monotonic()
        rot = (now * 30) % 360
        outer = 55 * scale_y
        inner = 25 * scale_y
        pts = _star_points(cx, cy, outer, inner, points=5, rotation=rot)
        d.polygon(pts, fill=ASTRO_BRIGHT)

    def _draw_dizzy(self, d, cx, cy, scale_y):
        """Spiral dazed eyes."""
        now = time.monotonic()
        rot = now * 120
        r_max = 45 * scale_y
        # Draw spiral as thick arc segments
        steps = 100
        for i in range(1, steps):
            t = i / steps
            r = r_max * t
            angle = math.radians(t * 720 + rot)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            dot_r = 2 + t * 2.5
            brightness = t
            color = (
                int(ASTRO_BLUE[0] * brightness),
                int(ASTRO_BLUE[1] * brightness),
                int(ASTRO_BLUE[2] * brightness),
            )
            d.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=color)

    def _draw_tired(self, d, cx, cy, scale_y):
        """Half-closed flat eyes."""
        w_top, w_bot = 70, 55
        h = 30 * scale_y
        self._tapered_oval(d, cx, cy + 18, w_top, w_bot, h, ASTRO_DIM)

    def _draw_wink(self, d, cx, cy, scale_y):
        """Left eye normal, right eye winking arc."""
        if self._is_left:
            w_top, w_bot = 65, 50
            h = 90 * scale_y
            self._tapered_oval(d, cx, cy, w_top, w_bot, h, ASTRO_BLUE)
        else:
            # Winking arc — thick curved line
            w = 65
            h = 40 * scale_y
            lw = 16
            bbox = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
            d.arc(bbox, start=10, end=170, fill=ASTRO_BLUE, width=lw)

    def _draw_determined(self, d, cx, cy, scale_y):
        """Narrowed focused eyes with slight inward angle."""
        w_top, w_bot = 80, 65
        h = 40 * scale_y
        self._tapered_oval(d, cx, cy, w_top, w_bot, h, ASTRO_BLUE)
        inward = -1 if self._is_left else 1
        pts = [
            (cx - w_top - 5, cy - h / 2 + 3 + 10 * inward),
            (cx + w_top + 5, cy - h / 2 + 3 - 10 * inward),
            (cx + w_top + 5, cy - h / 2 - 15),
            (cx - w_top - 5, cy - h / 2 - 15),
        ]
        d.polygon(pts, fill=SCREEN_BG)

    def _draw_worried(self, d, cx, cy, scale_y):
        """Uneven eyes — one higher, with upward inner brow."""
        w_top, w_bot = 55, 45
        h = 75 * scale_y
        y_shift = -10 if self._is_left else 10
        self._tapered_oval(d, cx, cy + y_shift, w_top, w_bot, h, ASTRO_BLUE)
        inward = 1 if self._is_left else -1
        pts = [
            (cx - w_top - 5, cy + y_shift - h / 2 + 5 - 12 * inward),
            (cx + w_top + 5, cy + y_shift - h / 2 + 5 + 12 * inward),
            (cx + w_top + 5, cy + y_shift - h / 2 - 15),
            (cx - w_top - 5, cy + y_shift - h / 2 - 15),
        ]
        d.polygon(pts, fill=SCREEN_BG)

    def _draw_celebrating(self, d, cx, cy, scale_y):
        """Round eyes with animated sparkle ring."""
        r = 50 * scale_y
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ASTRO_BLUE)
        # Sparkle ring
        now = time.monotonic()
        for i in range(6):
            angle = math.radians(now * 80 + i * 60)
            dist = 65
            sx = cx + dist * math.cos(angle)
            sy = cy + dist * math.sin(angle) * scale_y
            sr = 5 + 3 * math.sin(now * 5 + i * 2)
            pts = _star_points(sx, sy, sr, sr * 0.3, points=4,
                               rotation=(now * 90 + i * 45) % 360)
            d.polygon(pts, fill=ASTRO_BRIGHT)

    def _draw_scared(self, d, cx, cy, scale_y):
        """Small shrunk eyes with tiny pupils — trembling."""
        now = time.monotonic()
        tremble_x = math.sin(now * 25) * 3
        tremble_y = math.cos(now * 30) * 2
        ex = cx + tremble_x
        ey = cy + tremble_y
        # Small round eye
        r = 40 * scale_y
        d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=ASTRO_BRIGHT)
        # Tiny pupil (fear = constricted)
        pr = 12 * scale_y
        d.ellipse([ex - pr, ey - pr, ex + pr, ey + pr], fill=SCREEN_BG)

    def _draw_crying(self, d, cx, cy, scale_y):
        """Sad droopy eyes with animated tear streams."""
        # Sad eye shape
        w_top, w_bot = 55, 45
        h = 60 * scale_y
        self._tapered_oval(d, cx, cy + 5, w_top, w_bot, h, ASTRO_DIM)
        # Angled sad brow
        tilt = -12 if self._is_left else 12
        pts = [
            (cx - w_top - 5, cy + 5 - h / 2 + 8 + tilt),
            (cx + w_top + 5, cy + 5 - h / 2 + 8 - tilt),
            (cx + w_top + 5, cy + 5 - h / 2 - 15),
            (cx - w_top - 5, cy + 5 - h / 2 - 15),
        ]
        d.polygon(pts, fill=SCREEN_BG)
        # Animated tear drops falling from bottom of eye
        now = time.monotonic()
        tear_x = cx + (10 if self._is_left else -10)
        for i in range(3):
            phase = (now * 2.5 + i * 0.7) % 2.0
            if phase < 1.5:
                tear_y = cy + 5 + h / 2 + phase * 50
                tear_r = 5 - phase * 2.5
                if tear_r > 0:
                    d.ellipse([tear_x - tear_r, tear_y - tear_r,
                               tear_x + tear_r, tear_y + tear_r],
                              fill=ASTRO_BRIGHT)

    def _draw_laughing(self, d, cx, cy, scale_y):
        """Tightly squinted XD eyes — upside-down U arcs."""
        w = 60
        h = 50 * scale_y
        lw = 18
        # Upside-down U shape (bottom arc)
        bbox = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
        d.arc(bbox, start=190, end=350, fill=ASTRO_BRIGHT, width=lw)

    def _draw_x_eyes(self, d, cx, cy, scale_y):
        """X-shaped stunned/KO eyes."""
        size = 45 * scale_y
        lw = 14
        d.line([(cx - size, cy - size), (cx + size, cy + size)],
               fill=ASTRO_DIM, width=lw)
        d.line([(cx + size, cy - size), (cx - size, cy + size)],
               fill=ASTRO_DIM, width=lw)

    def _draw_confused(self, d, cx, cy, scale_y):
        """Asymmetric eyes — one big, one small, with tilted brow."""
        if self._is_left:
            # Bigger eye, raised
            r = 50 * scale_y
            d.ellipse([cx - r, cy - 8 - r, cx + r, cy - 8 + r],
                      fill=ASTRO_BLUE)
        else:
            # Smaller squinting eye
            w_top, w_bot = 50, 40
            h = 35 * scale_y
            self._tapered_oval(d, cx, cy + 8, w_top, w_bot, h, ASTRO_BLUE)
            # Tilted brow
            pts = [
                (cx - w_top - 5, cy + 8 - h / 2 - 2),
                (cx + w_top + 5, cy + 8 - h / 2 + 12),
                (cx + w_top + 5, cy + 8 - h / 2 - 15),
                (cx - w_top - 5, cy + 8 - h / 2 - 15),
            ]
            d.polygon(pts, fill=SCREEN_BG)

    def _draw_sleepy(self, d, cx, cy, scale_y):
        """Barely-open slit eyes with floating Z letters."""
        # Thin slit eye
        w = 55
        h = 12 * scale_y
        lw = 14
        bbox = [cx - w / 2, cy + 10 - h, cx + w / 2, cy + 10 + h]
        d.arc(bbox, start=200, end=340, fill=ASTRO_DIM, width=lw)
        # Animated Z letters floating up
        now = time.monotonic()
        for i in range(3):
            phase = (now * 0.8 + i * 1.2) % 3.0
            zx = cx + 30 + i * 15
            zy = cy - 20 - phase * 30
            z_size = 6 + i * 3
            alpha = max(0.0, 1.0 - phase / 3.0)
            z_color = (
                int(ASTRO_BLUE[0] * alpha),
                int(ASTRO_BLUE[1] * alpha),
                int(ASTRO_BLUE[2] * alpha),
            )
            if z_color[2] > 15:
                # Draw Z shape
                d.line([(zx - z_size, zy - z_size),
                        (zx + z_size, zy - z_size)],
                       fill=z_color, width=3)
                d.line([(zx + z_size, zy - z_size),
                        (zx - z_size, zy + z_size)],
                       fill=z_color, width=3)
                d.line([(zx - z_size, zy + z_size),
                        (zx + z_size, zy + z_size)],
                       fill=z_color, width=3)

    def _draw_mischievous(self, d, cx, cy, scale_y):
        """Sly asymmetric look — one eye normal, one narrowed smugly."""
        if self._is_left:
            # Normal-ish eye but slightly narrowed at top
            w_top, w_bot = 60, 50
            h = 70 * scale_y
            self._tapered_oval(d, cx, cy, w_top, w_bot, h, ASTRO_BLUE)
            # Slight smug brow angle
            pts = [
                (cx - w_top - 5, cy - h / 2 + 8),
                (cx + w_top + 5, cy - h / 2 + 2),
                (cx + w_top + 5, cy - h / 2 - 15),
                (cx - w_top - 5, cy - h / 2 - 15),
            ]
            d.polygon(pts, fill=SCREEN_BG)
        else:
            # Narrowed sly eye
            w = 65
            h = 35 * scale_y
            lw = 16
            bbox = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
            d.arc(bbox, start=195, end=345, fill=ASTRO_BLUE, width=lw)

    # --- Shape helpers ---

    def _tapered_oval(self, d, cx, cy, w_top, w_bot, h, color):
        """Draw a soft tapered oval — wider at top, narrower at bottom.
        This is the signature Astro Bot eye shape."""
        points = []
        steps = 40
        half_h = h / 2
        for i in range(steps + 1):
            t = i / steps  # 0..1, top to bottom
            y = cy - half_h + t * h
            # Interpolate width from top to bottom
            w = w_top + (w_bot - w_top) * t
            # Use sine for smooth rounding
            angle = t * math.pi
            roundness = math.sin(angle)
            x_offset = (w / 2) * roundness
            points.append((cx + x_offset, y))
        # Return back on the left side
        for i in range(steps, -1, -1):
            t = i / steps
            y = cy - half_h + t * h
            w = w_top + (w_bot - w_top) * t
            angle = t * math.pi
            roundness = math.sin(angle)
            x_offset = (w / 2) * roundness
            points.append((cx - x_offset, y))
        d.polygon(points, fill=color)

    def _clip_circle_img(self):
        """Black out corners outside the round display on the final image."""
        d = ImageDraw.Draw(self._img)
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
