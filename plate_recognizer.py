"""
License Plate Detection and Recognition.
Uses EasyOCR for text extraction from the plate region.
"""

import cv2
import numpy as np

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("[WARNING] EasyOCR not installed. Plate recognition disabled.")


class PlateRecognizer:
    """
    Detects and reads license plates from vehicle crops.

    Pipeline:
    1. Convert to grayscale
    2. Apply bilateral filter + edge detection
    3. Find rectangular contours (potential plates)
    4. Crop plate region
    5. Apply OCR using EasyOCR
    """

    def __init__(self, languages=None):
        if languages is None:
            languages = ['en']

        if EASYOCR_AVAILABLE:
            print("[INFO] Initializing EasyOCR reader...")
            self.reader = easyocr.Reader(languages, gpu=True)
        else:
            self.reader = None

    def preprocess_plate(self, plate_img):
        """
        Preprocess the plate image for better OCR results.
        """
        # Resize for consistency
        plate_img = cv2.resize(plate_img, None, fx=2, fy=2,
                                interpolation=cv2.INTER_CUBIC)

        # Convert to grayscale
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)

        # Denoise
        gray = cv2.bilateralFilter(gray, 11, 17, 17)

        # Adaptive threshold
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        return thresh

    def detect_plate_region(self, vehicle_img):
        """
        Detect the license plate region in a vehicle crop.

        Returns:
            plate_crop (numpy array) or None
            plate_coords (x, y, w, h) or None
        """
        gray = cv2.cvtColor(vehicle_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 13, 15, 15)

        # Edge detection
        edged = cv2.Canny(gray, 30, 200)

        # Find contours
        contours, _ = cv2.findContours(
            edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:15]

        plate_contour = None
        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.018 * peri, True)

            # License plates are roughly rectangular (4 corners)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / float(h)

                # Filter by aspect ratio (plates are wider than tall)
                if 2.0 <= aspect_ratio <= 6.0 and w > 60:
                    plate_contour = approx
                    plate_crop = vehicle_img[y:y + h, x:x + w]
                    return plate_crop, (x, y, w, h)

        # Fallback: use bottom portion of vehicle (plates usually at bottom)
        h, w = vehicle_img.shape[:2]
        bottom_region = vehicle_img[int(h * 0.5):, :]
        if bottom_region.size > 0:
            return bottom_region, (0, int(h * 0.5), w, int(h * 0.5))

        return None, None

    def recognize_plate(self, vehicle_img):
        """
        Full pipeline: detect plate region + OCR.

        Args:
            vehicle_img: Cropped vehicle image (BGR)

        Returns:
            plate_text: str (recognized plate number)
            confidence: float
            plate_crop: numpy array (cropped plate image)
        """
        if self.reader is None:
            return "OCR_UNAVAILABLE", 0.0, None

        if vehicle_img is None or vehicle_img.size == 0:
            return "UNKNOWN", 0.0, None

        # Step 1: Detect plate region
        plate_crop, plate_coords = self.detect_plate_region(vehicle_img)

        if plate_crop is None or plate_crop.size == 0:
            # Try OCR on entire vehicle image
            plate_crop = vehicle_img

        # Step 2: Preprocess
        processed = self.preprocess_plate(plate_crop)

        # Step 3: OCR
        try:
            results = self.reader.readtext(processed)

            if not results:
                # Try on original plate crop
                results = self.reader.readtext(plate_crop)

            if results:
                # Combine all detected text
                texts = []
                total_conf = 0
                for (bbox, text, conf) in results:
                    cleaned = self._clean_plate_text(text)
                    if cleaned:
                        texts.append(cleaned)
                        total_conf += conf

                if texts:
                    plate_text = " ".join(texts)
                    avg_conf = total_conf / len(texts)
                    return plate_text, round(avg_conf, 2), plate_crop

            return "UNREADABLE", 0.0, plate_crop

        except Exception as e:
            print(f"[ERROR] OCR failed: {e}")
            return "ERROR", 0.0, plate_crop

    def _clean_plate_text(self, text):
        """Clean and validate plate text."""
        # Remove special characters, keep alphanumeric and spaces
        cleaned = ''.join(c for c in text if c.isalnum() or c == ' ')
        cleaned = cleaned.strip().upper()

        # Filter out very short results (noise)
        if len(cleaned) < 2:
            return ""

        return cleaned