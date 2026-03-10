"""
FIXED Speed Estimator - better line crossing detection.
"""

import time
import config
from tracker import CentroidTracker


class SpeedEstimator:
    def __init__(self):
        self.tracker = CentroidTracker(max_disappeared=80, max_distance=120)
        self.line_y1 = config.DETECTION_LINE_Y1
        self.line_y2 = config.DETECTION_LINE_Y2
        self.real_distance = config.REAL_DISTANCE_METERS
        self.speed_limit = config.SPEED_LIMIT_KPH

        self.vehicle_speeds = {}
        self.violations = {}
        self.speed_computed = set()
        self.prev_centroids = {}
        self.frame_number = 0
        self.fps = config.FRAME_RATE

    def set_lines(self, y1, y2):
        """Update detection line positions."""
        self.line_y1 = y1
        self.line_y2 = y2
        print(f"[SPEED] Detection lines set: Y1={y1}, Y2={y2}")

    def update(self, detections_bboxes):
        self.frame_number += 1
        objects, bboxes = self.tracker.update(detections_bboxes)
        results = {}

        for obj_id in objects:
            centroid = objects[obj_id]
            bbox = bboxes[obj_id]
            cy = centroid[1]

            prev_cy = self.prev_centroids.get(obj_id, None)

            if prev_cy is not None:
                # ─── FIX: Better line crossing detection ───
                # Check if centroid crossed LINE 1 (in either direction)
                crossed_line1 = (
                    (prev_cy < self.line_y1 and cy >= self.line_y1) or
                    (prev_cy > self.line_y1 and cy <= self.line_y1) or
                    abs(cy - self.line_y1) < 10  # Within 10px of line
                )

                crossed_line2 = (
                    (prev_cy < self.line_y2 and cy >= self.line_y2) or
                    (prev_cy > self.line_y2 and cy <= self.line_y2) or
                    abs(cy - self.line_y2) < 10
                )

                # ─── FIX: Also check if centroid is IN the zone ───
                if 1 not in self.tracker.line_status.get(obj_id, set()):
                    if crossed_line1 or (prev_cy <= self.line_y1 <= cy):
                        self.tracker.record_line_crossing(
                            obj_id, 1, self.frame_number
                        )

                if 2 not in self.tracker.line_status.get(obj_id, set()):
                    if crossed_line2 or (prev_cy <= self.line_y2 <= cy):
                        self.tracker.record_line_crossing(
                            obj_id, 2, self.frame_number
                        )

            self.prev_centroids[obj_id] = cy

            # Compute speed
            speed = None
            is_violation = False

            if obj_id not in self.speed_computed:
                speed = self.tracker.get_speed(
                    obj_id, self.real_distance, self.fps
                )
                if speed is not None:
                    self.vehicle_speeds[obj_id] = speed
                    self.speed_computed.add(obj_id)
                    if speed > self.speed_limit:
                        is_violation = True
                        self.violations[obj_id] = True
                        print(f"\n  🚨 VIOLATION! Vehicle {obj_id}: "
                              f"{speed} km/h > {self.speed_limit} km/h")
                    else:
                        self.violations[obj_id] = False
                        print(f"  ✅ Vehicle {obj_id}: "
                              f"{speed} km/h (within limit)")

            if obj_id in self.vehicle_speeds:
                speed = self.vehicle_speeds[obj_id]
                is_violation = self.violations.get(obj_id, False)

            results[obj_id] = {
                'centroid': centroid,
                'bbox': bbox,
                'speed': speed,
                'is_violation': is_violation
            }

        return results