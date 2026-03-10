"""
FIXED Utility functions with debug visualization.
"""

import cv2
import os
import numpy as np
from datetime import datetime
import config


def draw_detection_lines(frame):
    """Draw detection lines with zone highlight."""
    h, w = frame.shape[:2]
    y1 = config.DETECTION_LINE_Y1
    y2 = config.DETECTION_LINE_Y2

    # Highlight zone between lines
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, y1), (w, y2), (0, 255, 255), -1)
    cv2.addWeighted(overlay, 0.1, frame, 0.9, 0, frame)

    # Line 1 (green)
    cv2.line(frame, (0, y1), (w, y1), (0, 255, 0), 3)
    cv2.putText(frame, f"LINE 1 (Y={y1})", (10, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Line 2 (red)
    cv2.line(frame, (0, y2), (w, y2), (0, 0, 255), 3)
    cv2.putText(frame, f"LINE 2 (Y={y2})", (10, y2 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Distance label
    mid_y = (y1 + y2) // 2
    cv2.putText(frame, f"{config.REAL_DISTANCE_METERS}m zone",
                (w - 150, mid_y), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (0, 255, 255), 2)

    return frame


def draw_vehicle_info(frame, obj_id, bbox, speed, is_violation,
                       class_name="", centroid=None):
    """Draw bounding box with info."""
    x1, y1, x2, y2 = bbox

    if is_violation:
        color = (0, 0, 255)
        thickness = 3
    elif speed is not None:
        color = (0, 255, 0)
        thickness = 2
    else:
        color = (255, 255, 0)
        thickness = 2

    # Bounding box
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

    # Centroid dot
    if centroid is not None:
        cv2.circle(frame, (int(centroid[0]), int(centroid[1])),
                   5, (0, 0, 255), -1)

    # Label
    label = f"ID:{obj_id}"
    if class_name:
        label += f" {class_name}"
    if speed is not None:
        label += f" | {speed:.1f}km/h"
        if is_violation:
            label += " VIOLATION!"

    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 5, y1), color, -1)
    cv2.putText(frame, label, (x1 + 2, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

    return frame


def draw_dashboard(frame, stats):
    """Draw statistics dashboard."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (w - 320, 0), (w, 180), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    lines = [
        f"Speed Limit: {config.SPEED_LIMIT_KPH} km/h",
        f"Vehicles Tracked: {stats.get('tracked', 0)}",
        f"Violations: {stats.get('violations', 0)}",
        f"Total Fines: Rs.{stats.get('total_fines', 0):.0f}",
        f"FPS: {stats.get('fps', 0):.1f}",
        f"Frame: {stats.get('frame', 0)}",
    ]

    y = 22
    for line in lines:
        cv2.putText(frame, line, (w - 310, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        y += 26

    return frame


def save_vehicle_snapshot(frame, bbox, obj_id, output_dir="snapshots"):
    """Save cropped vehicle image."""
    os.makedirs(output_dir, exist_ok=True)
    x1, y1, x2, y2 = bbox

    h, w = frame.shape[:2]
    pad = 30
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w, x2 + pad)
    y2 = min(h, y2 + pad)

    crop = frame[y1:y2, x1:x2]

    if crop.size == 0:
        crop = frame  # fallback to full frame

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"vehicle_{obj_id}_{timestamp}.jpg"
    filepath = os.path.join(output_dir, filename)

    cv2.imwrite(filepath, crop)
    print(f"  [SNAPSHOT] Saved: {filepath}")
    return filepath, crop