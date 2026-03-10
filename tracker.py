"""
FIXED Centroid Tracker with better line crossing detection.
"""

import numpy as np
from scipy.spatial import distance as dist
from collections import OrderedDict
import time


class CentroidTracker:
    def __init__(self, max_disappeared=80, max_distance=120):
        self.next_object_id = 0
        self.objects = OrderedDict()
        self.bboxes = OrderedDict()
        self.disappeared = OrderedDict()
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.timestamps = OrderedDict()
        self.line_status = OrderedDict()
        # FIX: Track frame numbers instead of wall-clock time
        self.frame_stamps = OrderedDict()

    def register(self, centroid, bbox):
        self.objects[self.next_object_id] = centroid
        self.bboxes[self.next_object_id] = bbox
        self.disappeared[self.next_object_id] = 0
        self.timestamps[self.next_object_id] = {}
        self.frame_stamps[self.next_object_id] = {}
        self.line_status[self.next_object_id] = set()
        self.next_object_id += 1

    def deregister(self, object_id):
        del self.objects[object_id]
        del self.bboxes[object_id]
        del self.disappeared[object_id]
        if object_id in self.timestamps:
            del self.timestamps[object_id]
        if object_id in self.frame_stamps:
            del self.frame_stamps[object_id]
        if object_id in self.line_status:
            del self.line_status[object_id]

    def record_line_crossing(self, object_id, line_id, frame_num):
        """Record when vehicle crosses a detection line."""
        if line_id not in self.line_status.get(object_id, set()):
            self.line_status[object_id].add(line_id)
            self.timestamps[object_id][line_id] = time.time()
            self.frame_stamps[object_id][line_id] = frame_num
            print(f"  [TRACKER] Vehicle {object_id} crossed LINE {line_id} "
                  f"at frame {frame_num}")

    def get_speed(self, object_id, real_distance_meters, fps=30):
        """
        Calculate speed using frame count (more reliable than wall clock).
        """
        ts = self.timestamps.get(object_id, {})
        fs = self.frame_stamps.get(object_id, {})

        if 1 in ts and 2 in ts:
            # Method 1: Use frame count (more accurate for video files)
            if 1 in fs and 2 in fs:
                frame_diff = abs(fs[2] - fs[1])
                if frame_diff > 0:
                    time_diff = frame_diff / fps
                    speed_mps = real_distance_meters / time_diff
                    speed_kph = speed_mps * 3.6
                    print(f"  [SPEED] Vehicle {object_id}: "
                          f"{frame_diff} frames, {time_diff:.2f}s, "
                          f"{speed_kph:.1f} km/h")
                    return round(speed_kph, 2)

            # Method 2: Fallback to wall clock
            time_diff = abs(ts[2] - ts[1])
            if time_diff > 0.01:
                speed_mps = real_distance_meters / time_diff
                speed_kph = speed_mps * 3.6
                return round(speed_kph, 2)

        return None

    def update(self, detections):
        if len(detections) == 0:
            for obj_id in list(self.disappeared.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    self.deregister(obj_id)
            return self.objects, self.bboxes

        input_centroids = np.zeros((len(detections), 2), dtype="int")
        input_bboxes = []
        for i, (x1, y1, x2, y2) in enumerate(detections):
            cx = int((x1 + x2) / 2.0)
            cy = int((y1 + y2) / 2.0)
            input_centroids[i] = (cx, cy)
            input_bboxes.append((x1, y1, x2, y2))

        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                self.register(input_centroids[i], input_bboxes[i])
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            D = dist.cdist(np.array(object_centroids), input_centroids)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows = set()
            used_cols = set()

            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                if D[row, col] > self.max_distance:
                    continue

                obj_id = object_ids[row]
                self.objects[obj_id] = input_centroids[col]
                self.bboxes[obj_id] = input_bboxes[col]
                self.disappeared[obj_id] = 0
                used_rows.add(row)
                used_cols.add(col)

            unused_rows = set(range(D.shape[0])) - used_rows
            unused_cols = set(range(D.shape[1])) - used_cols

            for row in unused_rows:
                obj_id = object_ids[row]
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    self.deregister(obj_id)

            for col in unused_cols:
                self.register(input_centroids[col], input_bboxes[col])

        return self.objects, self.bboxes