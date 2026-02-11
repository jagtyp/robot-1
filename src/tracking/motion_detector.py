import cv2
import numpy as np


class MotionDetector:
    """Detects moving objects using background subtraction."""

    def __init__(self, history: int = 30, threshold: int = 25,
                 min_area: int = 150, blur_size: int = 5):
        self._bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=threshold,
            detectShadows=False,
        )
        self._min_area = min_area
        self._blur_size = blur_size

    def detect(self, grey_frame: np.ndarray) -> list:
        """Detect moving regions in a grayscale frame.
        Returns list of (x, y, w, h) tuples."""
        blurred = cv2.GaussianBlur(grey_frame, (self._blur_size, self._blur_size), 0)

        # Apply background subtraction
        fg_mask = self._bg_sub.apply(blurred)

        # Clean up noise with morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.dilate(fg_mask, kernel, iterations=2)

        # Find contours of moving regions
        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        results = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self._min_area:
                results.append(cv2.boundingRect(contour))

        return results
