"""
FIXED Vehicle Detector - works with both real AND demo videos.
"""

import cv2
import numpy as np
import config

# Try YOLO first
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("[WARNING] ultralytics not installed. Using basic detection.")


class VehicleDetector:
    """
    Detects vehicles using YOLOv8 (real videos) or
    contour detection (demo/synthetic videos).
    """

    def __init__(self, use_yolo=True):
        self.use_yolo = use_yolo and YOLO_AVAILABLE
        self.class_names = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}

        if self.use_yolo:
            print(f"[DETECTOR] Loading YOLO: {config.YOLO_MODEL}")
            self.model = YOLO(config.YOLO_MODEL)
        else:
            print("[DETECTOR] Using contour-based detection (for demo video)")
            self.model = None

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=True
        )

    def detect(self, frame):
        """Detect vehicles in frame."""
        if self.use_yolo:
            return self._detect_yolo(frame)
        else:
            return self._detect_contour(frame)

    def _detect_yolo(self, frame):
        """YOLO-based detection for real videos."""
        results = self.model(frame, verbose=False)[0]
        detections = []

        for box in results.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])

            if (class_id in config.VEHICLE_CLASSES and
                    confidence >= config.CONFIDENCE_THRESHOLD):
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append({
                    'bbox': (x1, y1, x2, y2),
                    'confidence': confidence,
                    'class_id': class_id,
                    'class_name': self.class_names.get(class_id, "Vehicle")
                })

        return detections

    def _detect_contour(self, frame):
        """
        Contour-based detection for demo/synthetic videos.
        This works when YOLO can't detect drawn shapes.
        """
        # Background subtraction
        fg_mask = self.bg_subtractor.apply(frame)

        # Remove shadows (shadows have value 127 in MOG2)
        _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)

        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        fg_mask = cv2.dilate(fg_mask, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by size (adjust based on your video)
            if area < 800:  # Too small
                continue
            if area > 50000:  # Too large
                continue

            x, y, w, h = cv2.boundingRect(contour)

            # Filter by aspect ratio
            aspect_ratio = w / float(h) if h > 0 else 0
            if aspect_ratio < 0.2 or aspect_ratio > 5.0:
                continue

            # Minimum dimensions
            if w < 30 or h < 30:
                continue

            detections.append({
                'bbox': (x, y, x + w, y + h),
                'confidence': 0.8,
                'class_id': 2,
                'class_name': 'Car'
            })

        return detections