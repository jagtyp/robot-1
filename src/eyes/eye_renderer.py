import math
from PIL import Image, ImageDraw

from src.eyes.eye_state import EyeState
from src.config import EyeConfig


class EyeRenderer:
    """Renders a single eye to a 240x240 PIL Image."""

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
        self._draw_eyelid_upper(state.upper_eyelid, state.brow_angle, state.squint)

        # 9. Lower eyelid
        self._draw_eyelid_lower(state.lower_eyelid, state.squint)

        return self._img

    def _circle(self, cx: float, cy: float, r: float, fill: tuple):
        self._draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=fill,
        )

    def _draw_eyelid_upper(self, closure: float, brow_angle: float, squint: float):
        """Draw the upper eyelid as a polygon covering from the top."""
        total_closure = min(1.0, closure + squint * 0.3)
        if total_closure <= 0.01:
            return

        cx = self.CENTER
        r = self._sclera_r + 5

        # Total descent of the eyelid edge
        drop = total_closure * self._sclera_r * 2.2

        # Build polygon: top rectangle + curved bottom edge
        points = []
        points.append((cx - r - 10, cx - r - 10))
        points.append((cx + r + 10, cx - r - 10))

        # Curved bottom edge (right to left)
        steps = 24
        for i in range(steps + 1):
            t = i / steps
            x = cx + r - t * 2 * r

            curve = math.sin(t * math.pi)
            # Floor ramps up with closure so the eyelid covers the full
            # circular sclera at the edges when fully closed.
            floor = (total_closure ** 0.6) * 0.88
            curve = max(curve, floor)

            tilt = brow_angle * (t - 0.5) * 40
            y = (cx - r) + drop * curve + tilt
            points.append((x, y))

        self._draw.polygon(points, fill=(0, 0, 0))

    def _draw_eyelid_lower(self, closure: float, squint: float):
        """Draw the lower eyelid from the bottom."""
        total_closure = min(1.0, closure + squint * 0.15)
        if total_closure <= 0.01:
            return

        cx = self.CENTER
        r = self._sclera_r + 5

        rise = total_closure * self._sclera_r * 1.8

        points = []
        points.append((cx - r - 10, cx + r + 10))
        points.append((cx + r + 10, cx + r + 10))

        # Curved top edge (right to left)
        steps = 24
        for i in range(steps + 1):
            t = i / steps
            x = cx + r - t * 2 * r
            curve = math.sin(t * math.pi)
            floor = (total_closure ** 0.6) * 0.88
            curve = max(curve, floor)
            y = (cx + r) - rise * curve
            points.append((x, y))

        self._draw.polygon(points, fill=(0, 0, 0))
