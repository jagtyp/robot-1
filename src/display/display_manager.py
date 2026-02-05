import numpy as np
from PIL import Image

from src.display.gc9a01 import GC9A01


def _rgb888_to_rgb565(image: Image.Image) -> bytes:
    """Convert a 240x240 RGB PIL Image to RGB565 bytes (big-endian)."""
    arr = np.asarray(image, dtype=np.uint16)
    r = (arr[:, :, 0] >> 3) & 0x1F
    g = (arr[:, :, 1] >> 2) & 0x3F
    b = (arr[:, :, 2] >> 3) & 0x1F
    rgb565 = (r << 11) | (g << 5) | b
    return rgb565.astype(">u2").tobytes()


class DisplayManager:
    """Manages both eye displays."""

    def __init__(self, left: GC9A01, right: GC9A01):
        self._left = left
        self._right = right

    def update(self, left_image: Image.Image, right_image: Image.Image):
        """Convert PIL Images to RGB565 and send to both displays."""
        left_buf = _rgb888_to_rgb565(left_image)
        right_buf = _rgb888_to_rgb565(right_image)
        self._left.send_framebuffer(left_buf)
        self._right.send_framebuffer(right_buf)

    def clear(self):
        """Fill both displays with black."""
        self._left.fill(0x0000)
        self._right.fill(0x0000)

    def cleanup(self):
        """Shut down both displays."""
        self.clear()
        self._left.cleanup()
        self._right.cleanup()
