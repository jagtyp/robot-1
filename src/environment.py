"""Thread-safe environmental signal buffer for the mood engine.

Replaces the simple face_position/lock pattern in main.py with a richer
signal set: brightness, motion level, face presence events, and smoothed
face position for the animator.
"""

import threading
import time
import logging

import numpy as np

log = logging.getLogger("robot-head")


class EnvironmentState:
    """Collects signals from the tracking thread and exposes snapshots
    for the mood engine (main thread).  All public methods are thread-safe."""

    def __init__(self, brightness_tau: float = 1.0):
        self._lock = threading.Lock()

        # Face tracking (for animator backward compat)
        self._face_position = None        # (x, y) normalized or None

        # Brightness (exponentially smoothed)
        self._brightness = 50.0           # initial "daylight" guess
        self._brightness_tau = brightness_tau

        # Motion level (0..1 normalized area)
        self._motion_level = 0.0

        # Face event tracking
        self._face_present = False
        self._face_appeared_at = 0.0      # monotonic time of last appearance
        self._face_lost_at = 0.0          # monotonic time face was lost
        self._face_continuous_secs = 0.0  # how long current face has been tracked

        self._last_update = time.monotonic()

    def update_from_tracking(self, grey: np.ndarray, faces: list,
                             position, w: int, h: int):
        """Called from tracking thread each detection cycle.

        Args:
            grey: greyscale frame (numpy uint8 array)
            faces: list of (x, y, w, h) face bounding boxes
            position: normalized (x, y) face position or None
            w, h: frame dimensions for motion normalization
        """
        now = time.monotonic()

        # Compute raw brightness from the Y-plane
        raw_brightness = float(np.mean(grey))

        # Compute motion level from face bounding boxes area
        motion = 0.0
        if faces:
            total_area = sum(fw * fh for (_, _, fw, fh) in faces)
            frame_area = max(w * h, 1)
            motion = min(total_area / frame_area, 1.0)

        with self._lock:
            dt = now - self._last_update
            self._last_update = now

            # Exponential smoothing on brightness
            if dt > 0:
                alpha = min(1.0, dt / self._brightness_tau)
                self._brightness += alpha * (raw_brightness - self._brightness)

            # Motion level (instant, no smoothing needed for mood engine)
            self._motion_level = motion

            # Face presence edge detection
            was_present = self._face_present
            is_present = position is not None

            if is_present and not was_present:
                # Face just appeared
                self._face_appeared_at = now
                self._face_continuous_secs = 0.0
            elif is_present and was_present:
                # Face still present
                self._face_continuous_secs = now - self._face_appeared_at
            elif not is_present and was_present:
                # Face just lost
                self._face_lost_at = now
                self._face_continuous_secs = 0.0

            self._face_present = is_present
            self._face_position = position

    @property
    def face_position(self):
        """Backward-compatible accessor for animator. Returns (x,y) or None."""
        with self._lock:
            return self._face_position

    def get_snapshot(self) -> dict:
        """Return a snapshot of all environmental signals for the mood engine.

        Called from the main/render thread at ~2 Hz.
        """
        now = time.monotonic()
        with self._lock:
            face_lost_ago = (now - self._face_lost_at) if self._face_lost_at > 0 else 999.0
            return {
                "brightness": self._brightness,
                "motion_level": self._motion_level,
                "face_present": self._face_present,
                "face_continuous_secs": self._face_continuous_secs,
                "face_lost_ago": face_lost_ago,
                "time": now,
            }
