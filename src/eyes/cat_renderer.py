"""Cat/reptile eye renderer — vertical slit pupil with mood variants."""

import math
from PIL import Image, ImageDraw

from src.eyes.eye_state import EyeState
from src.eyes.eyelid_mixin import EyelidMixin
from src.config import EyeConfig


CAT_MOODS = {
    "normal": {
        "id": "normal", "name": "Normal",
        "iris": (180, 200, 30), "iris_outer": (100, 130, 10),
        "sclera": (200, 210, 50), "slit_width": 14,
    },
    "hunter": {
        "id": "hunter", "name": "Hunter",
        "iris": (220, 200, 10), "iris_outer": (140, 120, 0),
        "sclera": (210, 200, 40), "slit_width": 6,
    },
    "relaxed": {
        "id": "relaxed", "name": "Relaxed",
        "iris": (120, 200, 60), "iris_outer": (70, 130, 30),
        "sclera": (180, 210, 70), "slit_width": 30,
    },
    "angry": {
        "id": "angry", "name": "Angry",
        "iris": (240, 140, 10), "iris_outer": (160, 70, 0),
        "sclera": (220, 180, 40), "slit_width": 4,
    },
    "night": {
        "id": "night", "name": "Night Vision",
        "iris": (200, 190, 50), "iris_outer": (120, 110, 20),
        "sclera": (180, 180, 60), "slit_width": 45,
    },
    "hypnotic": {
        "id": "hypnotic", "name": "Hypnotic",
        "iris": (0, 255, 100), "iris_outer": (0, 160, 60),
        "sclera": (100, 220, 80), "slit_width": 10,
    },
}


class CatEyeRenderer(EyelidMixin):
    """Renders a cat/reptile eye with vertical slit pupil and mood variants."""

    SIZE = 240
    CENTER = 120
    SLIT_HEIGHT_RATIO = 1.7

    def __init__(self, config: EyeConfig, is_left: bool = True):
        self._sclera_r = config.sclera_radius
        self._iris_r = config.iris_radius
        self._pupil_r = config.pupil_radius
        self._max_offset = config.pupil_max_offset
        self._is_left = is_left
        self._img = Image.new("RGB", (self.SIZE, self.SIZE), (0, 0, 0))
        self._draw = ImageDraw.Draw(self._img)
        self._mood_id = "normal"

    @property
    def mood_id(self):
        return self._mood_id

    def get_moods(self) -> list[dict]:
        return [{"id": m["id"], "name": m["name"]} for m in CAT_MOODS.values()]

    def set_mood(self, mood_id: str) -> bool:
        if mood_id not in CAT_MOODS:
            return False
        self._mood_id = mood_id
        return True

    def render(self, state: EyeState) -> Image.Image:
        d = self._draw
        d.rectangle([0, 0, self.SIZE - 1, self.SIZE - 1], fill=(0, 0, 0))

        mood = CAT_MOODS[self._mood_id]
        iris_color = mood["iris"]
        iris_outer = mood["iris_outer"]
        sclera_color = mood["sclera"]
        slit_width = mood["slit_width"]

        # Sclera
        self._circle(d, self.CENTER, self.CENTER, self._sclera_r, sclera_color)

        # Pupil center position
        px = self.CENTER + state.pupil_x * self._max_offset
        py = self.CENTER + state.pupil_y * self._max_offset

        # Iris outer ring
        self._circle(d, px, py, self._iris_r, iris_outer)

        # Iris inner
        self._circle(d, px, py, self._iris_r - 5, iris_color)

        # Radial iris texture
        self._draw_iris_texture(d, px, py, self._iris_r - 5, iris_outer)

        # Vertical slit pupil
        effective_slit = slit_width * state.pupil_scale
        slit_h = self._iris_r * self.SLIT_HEIGHT_RATIO
        self._draw_slit(d, px, py, effective_slit, slit_h)

        # Specular highlight
        hx = px + (-10 if self._is_left else 10) - 3
        hy = py - 12
        self._circle(d, hx, hy, 6, (255, 255, 255))
        self._circle(d, hx + 12, hy + 16, 3, (220, 220, 200))

        # Eyelids
        self._draw_eyelid_upper(d, state.upper_eyelid,
                                state.brow_angle, state.squint)
        self._draw_eyelid_lower(d, state.lower_eyelid, state.squint)

        return self._img

    def _circle(self, d, cx, cy, r, fill):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)

    def _draw_slit(self, d, cx, cy, width, height):
        """Draw a vertical slit pupil using a pointed lens shape."""
        top = cy - height / 2
        bot = cy + height / 2
        hw = width / 2

        points = []
        steps = 20

        # Right curve (top to bottom)
        for i in range(steps + 1):
            t = i / steps
            y = top + t * (bot - top)
            normalized = (t - 0.5) * 2
            x_off = hw * (1 - normalized * normalized)
            points.append((cx + x_off, y))

        # Left curve (bottom to top)
        for i in range(steps + 1):
            t = 1.0 - i / steps
            y = top + t * (bot - top)
            normalized = (t - 0.5) * 2
            x_off = hw * (1 - normalized * normalized)
            points.append((cx - x_off, y))

        d.polygon(points, fill=(0, 0, 0))

    def _draw_iris_texture(self, d, cx, cy, r, line_color):
        """Draw subtle radial lines in the iris."""
        for i in range(16):
            angle = math.radians(i * 22.5)
            inner_r = r * 0.35
            outer_r = r * 0.9
            x1 = cx + inner_r * math.cos(angle)
            y1 = cy + inner_r * math.sin(angle)
            x2 = cx + outer_r * math.cos(angle)
            y2 = cy + outer_r * math.sin(angle)
            d.line([(x1, y1), (x2, y2)], fill=line_color, width=1)
