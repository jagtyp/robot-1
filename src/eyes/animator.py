import random
import time
from enum import Enum, auto

from src.eyes.eye_state import EyeState
from src.config import AnimationConfig
from src.utils.math_helpers import lerp, clamp


class Mode(Enum):
    TRACKING = auto()
    IDLE = auto()


class EyeAnimator:
    """State machine that produces animated EyeState pairs each frame."""

    def __init__(self, config: AnimationConfig):
        self._cfg = config
        self._mode = Mode.IDLE

        self._left = EyeState(is_left=True)
        self._right = EyeState(is_left=False)

        # Gaze
        self._current_gaze = (0.0, 0.0)
        self._target_gaze = (0.0, 0.0)

        # Idle behavior
        self._idle_target = (0.0, 0.0)
        self._idle_timer = 0.0
        self._idle_next = random.uniform(config.idle_interval_min, config.idle_interval_max)

        # Blink
        self._blink_timer = 0.0
        self._next_blink = random.uniform(config.blink_interval_min, config.blink_interval_max)
        self._blinking = False
        self._blink_progress = 0.0  # 0..1..0 over blink_duration

        # Track how long no face has been seen
        self._no_face_time = 0.0

    def update(self, dt: float, face_position: tuple | None) -> tuple[EyeState, EyeState]:
        """Update animation. face_position is (x, y) in -1..1 or None."""
        # Mode switching
        if face_position is not None:
            self._mode = Mode.TRACKING
            self._target_gaze = face_position
            self._no_face_time = 0.0
        else:
            self._no_face_time += dt
            if self._mode == Mode.TRACKING and self._no_face_time > 0.3:
                self._mode = Mode.IDLE
            if self._mode == Mode.IDLE:
                self._update_idle(dt)
                self._target_gaze = self._idle_target

        # Smooth pursuit toward target
        smoothing = self._cfg.pursuit_smoothing
        self._current_gaze = (
            lerp(self._current_gaze[0], self._target_gaze[0], smoothing),
            lerp(self._current_gaze[1], self._target_gaze[1], smoothing),
        )

        # Blink update
        self._update_blink(dt)

        # Compute eyelid value from blink
        blink_eyelid = self._blink_curve()

        # Apply to both eyes
        for eye in (self._left, self._right):
            eye.pupil_x = clamp(self._current_gaze[0], -1.0, 1.0)
            eye.pupil_y = clamp(self._current_gaze[1], -1.0, 1.0)
            eye.upper_eyelid = blink_eyelid
            eye.lower_eyelid = blink_eyelid * 0.4

        # Slight vergence (eyes converge toward close objects)
        vergence = 0.03
        self._left.pupil_x += vergence
        self._right.pupil_x -= vergence

        return (self._left, self._right)

    def _update_idle(self, dt: float):
        """Pick random gaze targets when idle."""
        self._idle_timer += dt
        if self._idle_timer >= self._idle_next:
            self._idle_target = (
                random.uniform(-self._cfg.idle_range_x, self._cfg.idle_range_x),
                random.uniform(-self._cfg.idle_range_y, self._cfg.idle_range_y),
            )
            self._idle_timer = 0.0
            self._idle_next = random.uniform(
                self._cfg.idle_interval_min, self._cfg.idle_interval_max
            )

    def _update_blink(self, dt: float):
        """Handle periodic blinking."""
        if self._blinking:
            self._blink_progress += dt / self._cfg.blink_duration
            if self._blink_progress >= 1.0:
                self._blink_progress = 0.0
                self._blinking = False
                self._next_blink = random.uniform(
                    self._cfg.blink_interval_min, self._cfg.blink_interval_max
                )
        else:
            self._blink_timer += dt
            if self._blink_timer >= self._next_blink:
                self._blinking = True
                self._blink_timer = 0.0
                self._blink_progress = 0.0

    def _blink_curve(self) -> float:
        """Returns eyelid closure 0..1 based on blink progress.
        Uses a triangle wave: ramps up to 1.0 at progress=0.5, then back to 0."""
        if not self._blinking:
            return 0.0
        p = self._blink_progress
        if p < 0.5:
            return p * 2.0   # 0 -> 1
        else:
            return (1.0 - p) * 2.0  # 1 -> 0
