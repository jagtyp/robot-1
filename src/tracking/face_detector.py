import cv2
import numpy as np


class FaceDetector:
    """OpenCV Haar Cascade face detection."""

    CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

    def __init__(self, scale_factor: float = 1.2, min_neighbors: int = 3,
                 min_face_size: tuple = (20, 20)):
        self._cascade = cv2.CascadeClassifier(self.CASCADE_PATH)
        if self._cascade.empty():
            raise RuntimeError(f"Failed to load cascade from {self.CASCADE_PATH}")
        self._scale_factor = scale_factor
        self._min_neighbors = min_neighbors
        self._min_face_size = min_face_size

    def detect(self, grey_frame: np.ndarray) -> list:
        """Detect faces in a grayscale frame.
        Returns list of (x, y, w, h) tuples."""
        faces = self._cascade.detectMultiScale(
            grey_frame,
            scaleFactor=self._scale_factor,
            minNeighbors=self._min_neighbors,
            minSize=self._min_face_size,
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        if len(faces) == 0:
            return []
        return [tuple(f) for f in faces]
