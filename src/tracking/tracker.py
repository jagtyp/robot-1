from src.utils.math_helpers import lerp


class FaceTracker:
    """Smooths raw face detections into a stable normalized gaze target."""

    def __init__(self, smoothing: float = 0.3, lost_timeout: float = 0.5):
        self._smoothing = smoothing
        self._lost_timeout = lost_timeout
        self._last_detection_time = 0.0
        self._current = None  # (x, y) normalized or None
        self._raw = None

    def update(self, faces: list, frame_w: int, frame_h: int,
               timestamp: float) -> tuple | None:
        """Process detections. Returns normalized (x, y) in -1..1 or None."""
        if len(faces) > 0:
            # Pick largest face (closest person)
            biggest = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = biggest

            # Normalize center of face to -1..1
            cx = (x + w / 2) / frame_w * 2 - 1
            cy = (y + h / 2) / frame_h * 2 - 1

            # Mirror X (camera is mirrored relative to robot's perspective)
            cx = -cx

            self._raw = (cx, cy)
            self._last_detection_time = timestamp

        # Check timeout
        if timestamp - self._last_detection_time > self._lost_timeout:
            self._current = None
            return None

        if self._raw is None:
            return None

        # Exponential smoothing
        if self._current is None:
            self._current = self._raw
        else:
            self._current = (
                lerp(self._current[0], self._raw[0], self._smoothing),
                lerp(self._current[1], self._raw[1], self._smoothing),
            )

        return self._current
