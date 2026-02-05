import numpy as np
from picamera2 import Picamera2


class Camera:
    """Wraps picamera2 for headless face-tracking capture."""

    def __init__(self, width: int = 160, height: int = 120):
        self._width = width
        self._height = height
        self._picam2 = Picamera2()
        config = self._picam2.create_still_configuration(
            main={"size": (640, 480)},
            lores={"size": (width, height), "format": "YUV420"},
            buffer_count=2,
        )
        self._picam2.configure(config)

    def start(self):
        self._picam2.start()

    def capture_grey(self) -> np.ndarray:
        """Capture a grayscale frame from the lores stream.
        The Y plane of YUV420 is already grayscale - zero conversion cost."""
        arr = self._picam2.capture_array("lores")
        return arr[:self._height, :self._width]

    def capture_rgb(self) -> np.ndarray:
        """Capture a full RGB frame from the main stream (for debug)."""
        return self._picam2.capture_array("main")

    def stop(self):
        self._picam2.stop()
        self._picam2.close()
