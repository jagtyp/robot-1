"""Shared eyelid drawing logic for all eye renderers."""

import math
from PIL import ImageDraw


class EyelidMixin:
    """Mixin providing eyelid drawing methods.

    Requires the using class to set:
        self._sclera_r: int  (sclera radius)
        SIZE: int            (image size, e.g. 240)
        CENTER: int          (image center, e.g. 120)
    """

    def _draw_eyelid_upper(self, draw: ImageDraw.ImageDraw, closure: float,
                           brow_angle: float, squint: float):
        total_closure = min(1.0, closure + squint * 0.3)
        if total_closure <= 0.01:
            return

        cx = self.CENTER
        r = self._sclera_r + 5
        drop = total_closure * self._sclera_r * 2.2

        points = []
        points.append((cx - r - 10, cx - r - 10))
        points.append((cx + r + 10, cx - r - 10))

        steps = 24
        for i in range(steps + 1):
            t = i / steps
            x = cx + r - t * 2 * r
            curve = math.sin(t * math.pi)
            floor = (total_closure ** 0.6) * 0.88
            curve = max(curve, floor)
            tilt = brow_angle * (t - 0.5) * 40
            y = (cx - r) + drop * curve + tilt
            points.append((x, y))

        draw.polygon(points, fill=(0, 0, 0))

    def _draw_eyelid_lower(self, draw: ImageDraw.ImageDraw, closure: float,
                           squint: float):
        total_closure = min(1.0, closure + squint * 0.15)
        if total_closure <= 0.01:
            return

        cx = self.CENTER
        r = self._sclera_r + 5
        rise = total_closure * self._sclera_r * 1.8

        points = []
        points.append((cx - r - 10, cx + r + 10))
        points.append((cx + r + 10, cx + r + 10))

        steps = 24
        for i in range(steps + 1):
            t = i / steps
            x = cx + r - t * 2 * r
            curve = math.sin(t * math.pi)
            floor = (total_closure ** 0.6) * 0.88
            curve = max(curve, floor)
            y = (cx + r) - rise * curve
            points.append((x, y))

        draw.polygon(points, fill=(0, 0, 0))
