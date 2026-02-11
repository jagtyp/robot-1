"""Cartoon eye mood definitions — shape types and per-eye parameters for 12 moods."""

from dataclasses import dataclass, field
from enum import Enum


class ShapeType(Enum):
    ROUNDED_RECT = "rounded_rect"
    CIRCLE = "circle"
    ARC_UP = "arc_up"
    HEART = "heart"
    X_CROSS = "x_cross"
    CHEVRON = "chevron"
    LINE_ARC = "line_arc"


@dataclass
class CartoonEyeShape:
    """Parameters for one eye's shape within a mood."""
    shape: ShapeType = ShapeType.ROUNDED_RECT
    width: int = 90
    height: int = 140
    corner_radius: int = 40
    rotation: float = 0.0        # degrees, clockwise
    color: tuple = (0, 220, 255)  # cyan default
    y_offset: float = 0.0        # vertical shift from center
    gaze_range_x: float = 55.0
    gaze_range_y: float = 40.0
    blink_squash: float = 1.0    # 0 = blink disabled, 1 = normal
    line_width: int = 12         # for arc/line shapes
    chevron_direction: int = 1   # 1 = >, -1 = <


@dataclass
class CartoonMood:
    """A mood defines left and right eye shapes plus metadata."""
    id: str = "neutral"
    name: str = "Neutral"
    left: CartoonEyeShape = field(default_factory=CartoonEyeShape)
    right: CartoonEyeShape = field(default_factory=CartoonEyeShape)


# --- Default shape shortcuts ---

def _default_shape(**overrides) -> CartoonEyeShape:
    return CartoonEyeShape(**overrides)


# --- All 12 moods ---

CARTOON_MOODS: dict[str, CartoonMood] = {
    "neutral": CartoonMood(
        id="neutral",
        name="Neutral",
        left=_default_shape(width=90, height=140, corner_radius=40),
        right=_default_shape(width=90, height=140, corner_radius=40),
    ),
    "happy": CartoonMood(
        id="happy",
        name="Happy",
        left=_default_shape(
            shape=ShapeType.ARC_UP, width=130, height=90,
            line_width=16, blink_squash=0.3,
        ),
        right=_default_shape(
            shape=ShapeType.ARC_UP, width=130, height=90,
            line_width=16, blink_squash=0.3,
        ),
    ),
    "sad": CartoonMood(
        id="sad",
        name="Sad",
        left=_default_shape(
            width=110, height=100, corner_radius=35,
            rotation=18.0, y_offset=15.0,
        ),
        right=_default_shape(
            width=110, height=100, corner_radius=35,
            rotation=-18.0, y_offset=15.0,
        ),
    ),
    "angry": CartoonMood(
        id="angry",
        name="Angry",
        left=_default_shape(
            width=120, height=80, corner_radius=30,
            rotation=-25.0, y_offset=-5.0, color=(255, 50, 30),
        ),
        right=_default_shape(
            width=120, height=80, corner_radius=30,
            rotation=25.0, y_offset=-5.0, color=(255, 50, 30),
        ),
    ),
    "surprised": CartoonMood(
        id="surprised",
        name="Surprised",
        left=_default_shape(
            shape=ShapeType.CIRCLE, width=160, height=160,
        ),
        right=_default_shape(
            shape=ShapeType.CIRCLE, width=160, height=160,
        ),
    ),
    "tired": CartoonMood(
        id="tired",
        name="Tired",
        left=_default_shape(width=140, height=50, corner_radius=25, y_offset=18.0),
        right=_default_shape(width=140, height=50, corner_radius=25, y_offset=18.0),
    ),
    "love": CartoonMood(
        id="love",
        name="Love",
        left=_default_shape(
            shape=ShapeType.HEART, width=130, height=120,
            color=(255, 60, 120), blink_squash=0.5,
        ),
        right=_default_shape(
            shape=ShapeType.HEART, width=130, height=120,
            color=(255, 60, 120), blink_squash=0.5,
        ),
    ),
    "broken": CartoonMood(
        id="broken",
        name="Broken",
        left=_default_shape(
            shape=ShapeType.X_CROSS, width=100, height=100,
            line_width=16, blink_squash=0.0, gaze_range_x=0.0, gaze_range_y=0.0,
        ),
        right=_default_shape(
            shape=ShapeType.X_CROSS, width=100, height=100,
            line_width=16, blink_squash=0.0, gaze_range_x=0.0, gaze_range_y=0.0,
        ),
    ),
    "wink": CartoonMood(
        id="wink",
        name="Wink",
        left=_default_shape(width=90, height=140, corner_radius=40),
        right=_default_shape(
            shape=ShapeType.LINE_ARC, width=110, height=60,
            line_width=14, blink_squash=0.0,
        ),
    ),
    "sceptic": CartoonMood(
        id="sceptic",
        name="Sceptic",
        left=_default_shape(width=90, height=140, corner_radius=40),
        right=_default_shape(
            width=80, height=90, corner_radius=30,
            rotation=15.0, y_offset=18.0,
        ),
    ),
    "crazy": CartoonMood(
        id="crazy",
        name="Crazy",
        left=_default_shape(
            shape=ShapeType.CIRCLE, width=170, height=170,
        ),
        right=_default_shape(
            shape=ShapeType.CIRCLE, width=80, height=80,
        ),
    ),
    "denying": CartoonMood(
        id="denying",
        name="Denying",
        left=_default_shape(
            shape=ShapeType.CHEVRON, width=80, height=120,
            line_width=16, chevron_direction=1,
            blink_squash=0.0, gaze_range_x=0.0, gaze_range_y=0.0,
        ),
        right=_default_shape(
            shape=ShapeType.CHEVRON, width=80, height=120,
            line_width=16, chevron_direction=-1,
            blink_squash=0.0, gaze_range_x=0.0, gaze_range_y=0.0,
        ),
    ),
}
