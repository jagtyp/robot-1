import math
from PIL import Image, ImageDraw

from src.eyes.eye_state import EyeState
from src.eyes.eyelid_mixin import EyelidMixin
from src.config import EyeConfig


class ProceduralEyeRenderer(EyelidMixin):
    """Renders a single eye procedurally to a 240x240 PIL Image."""

    SIZE = 240
    CENTER = 120

    def __init__(self, config: EyeConfig):
        self._iris_color = tuple(config.iris_color)
        self._sclera_r = config.sclera_radius
        self._iris_r = config.iris_radius
        self._pupil_r = config.pupil_radius
        self._max_offset = config.pupil_max_offset
        # Darker shade of iris for the outer ring
        self._iris_outer = tuple(max(0, c - 40) for c in self._iris_color)
        # Pre-allocate image and draw context (reused every frame)
        self._img = Image.new("RGB", (self.SIZE, self.SIZE), (0, 0, 0))
        self._draw = ImageDraw.Draw(self._img)

    def render(self, state: EyeState) -> Image.Image:
        """Render eye from state. Returns the internal image (do not modify)."""
        d = self._draw

        # 1. Clear to black
        d.rectangle([0, 0, self.SIZE - 1, self.SIZE - 1], fill=(0, 0, 0))

        # 2. Sclera (white of the eye)
        self._circle(self.CENTER, self.CENTER, self._sclera_r, (235, 235, 235))

        # 3. Pupil center position
        px = self.CENTER + state.pupil_x * self._max_offset
        py = self.CENTER + state.pupil_y * self._max_offset

        # 4. Iris outer ring (darker border)
        self._circle(px, py, self._iris_r, self._iris_outer)

        # 5. Iris inner (main color)
        self._circle(px, py, self._iris_r - 6, self._iris_color)

        # 6. Pupil (black)
        pr = self._pupil_r * state.pupil_scale
        self._circle(px, py, pr, (0, 0, 0))

        # 7. Specular highlight (small white dot)
        hx = px + (-12 if state.is_left else 12) - 5
        hy = py - 14
        self._circle(hx, hy, 7, (255, 255, 255))
        # Smaller secondary highlight
        self._circle(hx + 14, hy + 18, 3, (200, 200, 200))

        # 8. Upper eyelid
        self._draw_eyelid_upper(self._draw, state.upper_eyelid,
                                state.brow_angle, state.squint)

        # 9. Lower eyelid
        self._draw_eyelid_lower(self._draw, state.lower_eyelid, state.squint)

        return self._img

    def _circle(self, cx: float, cy: float, r: float, fill: tuple):
        self._draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=fill,
        )


# Backward-compatible alias
EyeRenderer = ProceduralEyeRenderer
