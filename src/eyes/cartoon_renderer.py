"""Cartoon eye renderer — procedurally draws geometric shapes with mood transitions."""

import math
import time
from PIL import Image, ImageDraw, ImageFilter, ImageChops

from src.eyes.eye_state import EyeState
from src.eyes.cartoon_moods import (
    ShapeType, CartoonEyeShape, CartoonMood, CARTOON_MOODS,
)
from src.config import EyeConfig


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_color(a, b, t):
    return tuple(int(_lerp(a[i], b[i], t)) for i in range(3))


def _ease_in_out(t):
    """Smooth ease-in-out (cubic)."""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - (-2 * t + 2) ** 3 / 2


def _rotated_rounded_rect(cx, cy, w, h, r, angle_deg):
    """Build a polygon approximating a rounded rectangle, then rotate it.

    Traces the perimeter clockwise: top-right -> bottom-right -> bottom-left -> top-left.
    Returns list of (x, y) tuples.
    """
    # Clamp corner radius
    r = min(r, w // 2, h // 2)
    hw, hh = w / 2.0, h / 2.0

    # Corners in clockwise order with correct arc angle ranges
    points = []
    corners = [
        (hw - r, -hh + r, 270, 360),   # top-right
        (hw - r,  hh - r,   0,  90),   # bottom-right
        (-hw + r, hh - r,  90, 180),   # bottom-left
        (-hw + r, -hh + r, 180, 270),  # top-left
    ]
    n_arc = 7
    for corner_cx, corner_cy, start_a, end_a in corners:
        for i in range(n_arc + 1):
            a = math.radians(start_a + (end_a - start_a) * i / n_arc)
            px = corner_cx + r * math.cos(a)
            py = corner_cy + r * math.sin(a)
            points.append((px, py))

    # Rotate all points
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    rotated = []
    for px, py in points:
        rx = px * cos_a - py * sin_a + cx
        ry = px * sin_a + py * cos_a + cy
        rotated.append((rx, ry))

    return rotated


def _heart_points(cx, cy, w, h, n=40):
    """Generate heart shape as polygon points."""
    points = []
    for i in range(n):
        t = 2 * math.pi * i / n
        # Parametric heart
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        # Scale to desired size (parametric heart goes roughly -17..17 x, -17..15 y)
        points.append((
            cx + x * w / 34.0,
            cy + y * h / 34.0,
        ))
    return points


class CartoonEyeRenderer:
    """Renders one cartoon eye with mood-based shapes and smooth transitions."""

    SIZE = 240
    CENTER = 120
    TRANSITION_DURATION = 0.25  # seconds

    GLOW_RADIUS = 6
    GLOW_BOOST = 1.5

    def __init__(self, config: EyeConfig, is_left: bool):
        self._config = config
        self._is_left = is_left
        self.glow_enabled = False

        # Pre-allocate images
        self._img = Image.new("RGB", (self.SIZE, self.SIZE), (0, 0, 0))
        self._shape_layer = Image.new("RGB", (self.SIZE, self.SIZE), (0, 0, 0))
        self._shape_draw = ImageDraw.Draw(self._shape_layer)
        self._direct_draw = ImageDraw.Draw(self._img)

        # Mood state
        self._current_mood_id = "neutral"
        self._target_mood_id = "neutral"
        self._transition_start = 0.0
        self._transitioning = False

    @property
    def mood_id(self):
        return self._target_mood_id

    def get_moods(self) -> list[dict]:
        """Return list of available moods."""
        return [{"id": m.id, "name": m.name} for m in CARTOON_MOODS.values()]

    def set_mood(self, mood_id: str) -> bool:
        """Start transitioning to a new mood. Returns True on success."""
        if mood_id not in CARTOON_MOODS:
            return False
        if mood_id == self._target_mood_id:
            return True
        self._target_mood_id = mood_id
        self._transition_start = time.monotonic()
        self._transitioning = True
        return True

    def _get_eye_shape(self, mood_id: str) -> CartoonEyeShape:
        mood = CARTOON_MOODS[mood_id]
        return mood.left if self._is_left else mood.right

    def render(self, state: EyeState) -> Image.Image:
        now = time.monotonic()

        # Compute transition progress
        if self._transitioning:
            elapsed = now - self._transition_start
            t = min(1.0, elapsed / self.TRANSITION_DURATION)
            t = _ease_in_out(t)
            if t >= 1.0:
                self._current_mood_id = self._target_mood_id
                self._transitioning = False
                t = 1.0
        else:
            t = 1.0

        # Get shape params
        current_shape = self._get_eye_shape(self._current_mood_id)
        target_shape = self._get_eye_shape(self._target_mood_id)

        if self._transitioning:
            width = _lerp(current_shape.width, target_shape.width, t)
            height = _lerp(current_shape.height, target_shape.height, t)
            corner_radius = _lerp(current_shape.corner_radius, target_shape.corner_radius, t)
            rotation = _lerp(current_shape.rotation, target_shape.rotation, t)
            color = _lerp_color(current_shape.color, target_shape.color, t)
            y_offset = _lerp(current_shape.y_offset, target_shape.y_offset, t)
            gaze_range_x = _lerp(current_shape.gaze_range_x, target_shape.gaze_range_x, t)
            gaze_range_y = _lerp(current_shape.gaze_range_y, target_shape.gaze_range_y, t)
            blink_squash = _lerp(current_shape.blink_squash, target_shape.blink_squash, t)
            line_width = int(_lerp(current_shape.line_width, target_shape.line_width, t))
            chevron_dir = target_shape.chevron_direction
            shape_type = current_shape.shape if t < 0.5 else target_shape.shape
        else:
            shape = target_shape
            width = shape.width
            height = shape.height
            corner_radius = shape.corner_radius
            rotation = shape.rotation
            color = shape.color
            y_offset = shape.y_offset
            gaze_range_x = shape.gaze_range_x
            gaze_range_y = shape.gaze_range_y
            blink_squash = shape.blink_squash
            line_width = shape.line_width
            chevron_dir = shape.chevron_direction
            shape_type = shape.shape

        # Apply blink squash
        effective_height = height * (1.0 - state.upper_eyelid * blink_squash)
        effective_height = max(2, effective_height)

        # Compute gaze offset
        cx = self.CENTER + state.pupil_x * gaze_range_x
        cy = self.CENTER + state.pupil_y * gaze_range_y + y_offset

        if self.glow_enabled:
            # Draw onto separate layer, then blur + composite for glow
            self._shape_draw.rectangle(
                [0, 0, self.SIZE - 1, self.SIZE - 1], fill=(0, 0, 0))
            self._draw_shape(
                self._shape_draw, shape_type, cx, cy, width, effective_height,
                corner_radius, rotation, color, line_width, chevron_dir,
            )

            glow = self._shape_layer.filter(
                ImageFilter.BoxBlur(radius=self.GLOW_RADIUS))
            if self.GLOW_BOOST > 1.0:
                boost_val = int(255 * (self.GLOW_BOOST - 1.0))
                extra = ImageChops.multiply(
                    glow,
                    Image.new("RGB", glow.size, (boost_val,) * 3),
                )
                glow = ImageChops.add(glow, extra)

            self._img.paste(glow, (0, 0))
            self._img.paste(
                self._shape_layer, (0, 0),
                self._shape_layer.convert("L"),
            )
        else:
            # Fast path: draw directly, no blur
            self._direct_draw.rectangle(
                [0, 0, self.SIZE - 1, self.SIZE - 1], fill=(0, 0, 0))
            self._draw_shape(
                self._direct_draw, shape_type, cx, cy, width, effective_height,
                corner_radius, rotation, color, line_width, chevron_dir,
            )

        return self._img

    def _draw_shape(self, d, shape_type, cx, cy, w, h, r, rotation, color,
                    line_width, chevron_dir):
        w = int(w)
        h = int(h)
        r = int(r)

        if shape_type == ShapeType.ROUNDED_RECT:
            self._draw_rounded_rect(d, cx, cy, w, h, r, rotation, color)

        elif shape_type == ShapeType.CIRCLE:
            d.ellipse(
                [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2],
                fill=color,
            )

        elif shape_type == ShapeType.ARC_UP:
            self._draw_arc_up(d, cx, cy, w, h, color, line_width)

        elif shape_type == ShapeType.HEART:
            self._draw_heart(d, cx, cy, w, h, color)

        elif shape_type == ShapeType.X_CROSS:
            self._draw_x_cross(d, cx, cy, w, h, color, line_width)

        elif shape_type == ShapeType.CHEVRON:
            self._draw_chevron(d, cx, cy, w, h, color, line_width, chevron_dir)

        elif shape_type == ShapeType.LINE_ARC:
            self._draw_line_arc(d, cx, cy, w, h, color, line_width)

    def _draw_rounded_rect(self, d, cx, cy, w, h, r, rotation, color):
        if abs(rotation) < 0.5:
            # No rotation needed — use Pillow's native rounded_rectangle
            r = min(r, w // 2, h // 2)
            d.rounded_rectangle(
                [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2],
                radius=r,
                fill=color,
            )
        else:
            # Rotated — use polygon approximation
            points = _rotated_rounded_rect(cx, cy, w, h, r, rotation)
            d.polygon(points, fill=color)

    def _draw_arc_up(self, d, cx, cy, w, h, color, line_width):
        """Draw a happy arc (^) using a thick arc from 200° to 340°."""
        bbox = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
        d.arc(bbox, start=200, end=340, fill=color, width=line_width)

    def _draw_heart(self, d, cx, cy, w, h, color):
        points = _heart_points(cx, cy, w, h)
        d.polygon(points, fill=color)

    def _draw_x_cross(self, d, cx, cy, w, h, color, line_width):
        hw, hh = w / 2, h / 2
        d.line([(cx - hw, cy - hh), (cx + hw, cy + hh)],
               fill=color, width=line_width)
        d.line([(cx + hw, cy - hh), (cx - hw, cy + hh)],
               fill=color, width=line_width)

    def _draw_chevron(self, d, cx, cy, w, h, color, line_width, direction):
        """Draw a chevron (> or <). direction=1 for >, -1 for <."""
        hw, hh = w / 2, h / 2
        tip_x = cx + hw * direction
        d.line(
            [(cx - hw * direction, cy - hh), (tip_x, cy)],
            fill=color, width=line_width, joint="curve",
        )
        d.line(
            [(tip_x, cy), (cx - hw * direction, cy + hh)],
            fill=color, width=line_width, joint="curve",
        )

    def _draw_line_arc(self, d, cx, cy, w, h, color, line_width):
        """Draw a closed-eye arc (wink). A thick arc spanning 0° to 180°."""
        bbox = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
        d.arc(bbox, start=0, end=180, fill=color, width=line_width)
