"""
╔═══════════════════════════════════════════════════════════╗
║   AI OVER-SPEEDING VEHICLE CHALLAN SYSTEM - FIXED        ║
╚═══════════════════════════════════════════════════════════╝
"""

import cv2
import time
import os
import sys
from datetime import datetime

import config
from vehicle_detector import VehicleDetector
from speed_estimator import SpeedEstimator
from plate_recognizer import PlateRecognizer
from challan_generator import ChallanGenerator
from database import ViolationDatabase
from utils import (
    draw_detection_lines,
    draw_vehicle_info,
    draw_dashboard,
    save_vehicle_snapshot
)


class SpeedChallanSystem:
    def __init__(self, video_source=None, use_yolo=True):
        print("=" * 60)
        print("  AI OVER-SPEEDING VEHICLE CHALLAN SYSTEM")
        print("=" * 60)

        self.video_source = video_source or config.VIDEO_SOURCE
        self.use_yolo = use_yolo

        # ── Check video source first ──
        self._check_video_source()

        # ── Initialize components ──
        self.detector = VehicleDetector(use_yolo=self.use_yolo)
        self.speed_estimator = SpeedEstimator()
        self.plate_recognizer = PlateRecognizer()
        self.challan_generator = ChallanGenerator()
        self.database = ViolationDatabase()

        self.processed_violations = set()
        self.total_violations = 0
        self.total_fines = 0.0
        self.frame_count = 0

    def _check_video_source(self):
        """Verify video source exists."""
        if isinstance(self.video_source, str) and not self.video_source.startswith(('rtsp', 'http')):
            if not os.path.exists(self.video_source):
                print(f"\n[ERROR] Video file not found: {self.video_source}")
                print("\nGenerating demo video automatically...")
                self._generate_demo()

    def _generate_demo(self):
        """Auto-generate demo video if none exists."""
        try:
            from demo_generator import generate_demo_video
            generate_demo_video(self.video_source)
        except ImportError:
            print("[ERROR] demo_generator.py not found!")
            print("Create the demo video file first.")
            sys.exit(1)

    def _auto_adjust_lines(self, frame_height):
        """
        Auto-adjust detection line positions based on video resolution.
        Lines should be in the middle portion of the frame.
        """
        # Place lines at 40% and 70% of frame height
        y1 = int(frame_height * 0.35)
        y2 = int(frame_height * 0.65)

        config.DETECTION_LINE_Y1 = y1
        config.DETECTION_LINE_Y2 = y2
        self.speed_estimator.set_lines(y1, y2)

        print(f"[AUTO] Detection lines adjusted: Y1={y1}, Y2={y2} "
              f"(frame height={frame_height})")

    def process_violation(self, frame, obj_id, vehicle_info,
                           class_name="Car"):
        """Process a speed violation - generate challan."""
        if obj_id in self.processed_violations:
            return

        self.processed_violations.add(obj_id)
        speed = vehicle_info['speed']
        bbox = vehicle_info['bbox']

        print(f"\n{'!'*60}")
        print(f"  🚨 VIOLATION DETECTED!")
        print(f"  Vehicle ID    : {obj_id}")
        print(f"  Speed         : {speed} km/h")
        print(f"  Speed Limit   : {config.SPEED_LIMIT_KPH} km/h")
        print(f"  Excess        : {speed - config.SPEED_LIMIT_KPH:.1f} km/h")
        print(f"{'!'*60}")

        # Step 1: Save snapshot
        snapshot_path, vehicle_crop = save_vehicle_snapshot(
            frame, bbox, obj_id
        )

        # Step 2: License plate recognition
        plate_number = "UNKNOWN"
        plate_conf = 0.0
        try:
            plate_number, plate_conf, _ = \
                self.plate_recognizer.recognize_plate(vehicle_crop)
        except Exception as e:
            print(f"  [WARN] Plate recognition failed: {e}")
            plate_number = f"UNREAD-{obj_id}"

        if not plate_number or plate_number in ["", "UNKNOWN", "UNREADABLE", "ERROR"]:
            plate_number = f"PLATE-{obj_id:04d}"

        print(f"  License Plate : {plate_number} (conf: {plate_conf})")

        # Step 3: Calculate fine
        fine_amount = self.challan_generator.calculate_fine(
            speed, config.SPEED_LIMIT_KPH
        )
        print(f"  Fine Amount   : ₹{fine_amount}")

        # Step 4: Store in database
        violation_id = self.database.add_violation(
            vehicle_id=obj_id,
            plate_number=plate_number,
            vehicle_type=class_name,
            detected_speed=speed,
            speed_limit=config.SPEED_LIMIT_KPH,
            fine_amount=fine_amount,
            location=config.CITY,
            snapshot_path=snapshot_path
        )

        # Step 5: Generate PDF Challan
        violation_data = {
            'violation_id': violation_id,
            'plate_number': plate_number,
            'vehicle_type': class_name,
            'detected_speed': speed,
            'speed_limit': config.SPEED_LIMIT_KPH,
            'fine_amount': fine_amount,
            'violation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'location': config.CITY
        }

        try:
            challan_path = self.challan_generator.generate(
                violation_data, snapshot_path
            )
            print(f"  📄 Challan PDF : {challan_path}")
        except Exception as e:
            challan_path = "GENERATION_FAILED"
            print(f"  [ERROR] Challan generation failed: {e}")

        self.total_violations += 1
        self.total_fines += fine_amount

        print(f"  ✅ Violation #{violation_id} processed!")
        print(f"{'!'*60}\n")
    
    def run(self):
        """Main processing loop."""

        
        cap = cv2.VideoCapture(self.video_source)

        if not cap.isOpened():
            print(f"[ERROR] Cannot open: {self.video_source}")
            sys.exit(1)

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"\n[VIDEO] {width}x{height} @ {fps:.0f} FPS, "
              f"{total_frames} frames")

        # ── FIX: Auto-adjust detection lines ──
        self._auto_adjust_lines(height)
        self.speed_estimator.fps = fps

        # Output video
        os.makedirs("output", exist_ok=True)
        out = cv2.VideoWriter(
            'output/annotated_output.mp4',
            cv2.VideoWriter_fourcc(*'mp4v'),
            fps, (width, height)
        )

        prev_time = time.time()
        skip_frames = 0  # Process every frame (set to 1-2 to skip)

        print(f"\n[INFO] Processing started...")
        print(f"[INFO] Press 'q' to quit, 'p' to pause\n")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("\n[INFO] End of video.")
                break

            self.frame_count += 1

            # Skip frames for performance (optional)
            if skip_frames > 0 and self.frame_count % (skip_frames + 1) != 0:
                continue

            display = frame.copy()

            # ─── Step 1: Detect vehicles ─────────────
            detections = self.detector.detect(frame)

            if config.DEBUG_MODE and self.frame_count % 60 == 0:
                print(f"  [DEBUG] Frame {self.frame_count}: "
                      f"{len(detections)} vehicles detected")

            # ─── Step 2: Track & estimate speed ──────
            bboxes = [d['bbox'] for d in detections]
            tracked = self.speed_estimator.update(bboxes)

            # ─── Step 3: Draw & check violations ────
            for obj_id, info in tracked.items():
                speed = info['speed']
                is_violation = info['is_violation']
                centroid = info['centroid']
                bbox = info['bbox']

                # Find class name
                class_name = "Vehicle"
                for det in detections:
                    dx1, dy1, dx2, dy2 = det['bbox']
                    bx1, by1, bx2, by2 = bbox
                    if abs(dx1-bx1) < 60 and abs(dy1-by1) < 60:
                        class_name = det['class_name']
                        break

                # Draw vehicle info
                draw_vehicle_info(
                    display, obj_id, bbox, speed,
                    is_violation, class_name, centroid
                )

                # ─── Process violation ───
                if is_violation and obj_id not in self.processed_violations:
                    self.process_violation(
                        frame, obj_id, info, class_name
                    )

            # ─── Step 4: Draw overlays ───────────────
            draw_detection_lines(display)

            # FPS calculation
            now = time.time()
            current_fps = 1.0 / (now - prev_time + 1e-9)
            prev_time = now

            stats = {
                'tracked': len(tracked),
                'violations': self.total_violations,
                'total_fines': self.total_fines,
                'fps': current_fps,
                'frame': self.frame_count
            }
            draw_dashboard(display, stats)

            # Progress bar
            if total_frames > 0:
                progress = self.frame_count / total_frames
                bar_w = width - 20
                cv2.rectangle(display, (10, height-20),
                             (10 + int(bar_w * progress), height-10),
                             (0, 255, 0), -1)
                cv2.rectangle(display, (10, height-20),
                             (10 + bar_w, height-10), (255, 255, 255), 1)

            # ─── Display ─────────────────────────────
            cv2.imshow("AI Speed Challan System", display)
            out.write(display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('p'):
                print("[PAUSED] Press any key...")
                cv2.waitKey(0)
            elif key == ord('d'):
                config.DEBUG_MODE = not config.DEBUG_MODE
                print(f"[DEBUG] Debug mode: {config.DEBUG_MODE}")

        # Cleanup
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        self._print_report()

    def _print_report(self):
        """Print final report."""
        stats = self.database.get_statistics()
        print(f"\n{'═'*60}")
        print("  📋 FINAL REPORT")
        print(f"{'═'*60}")
        print(f"  Frames Processed  : {self.frame_count}")
        print(f"  Total Violations  : {stats['total_violations']}")
        print(f"  Total Fines       : ₹{stats['total_fines']:.2f}")
        print(f"  Avg Speed (viol.) : {stats['avg_speed']:.1f} km/h")
        print(f"  Max Speed         : {stats['max_speed']:.1f} km/h")

        violations = self.database.get_all_violations()
        if violations:
            print(f"\n  {'ID':<4} {'Plate':<16} {'Speed':<10} "
                  f"{'Fine':<10} {'Challan'}")
            print(f"  {'─'*65}")
            for v in violations:
                print(f"  {v['id']:<4} {v['plate_number']:<16} "
                      f"{v['detected_speed']:<10} ₹{v['fine_amount']:<10.0f} "
                      f"{v.get('challan_path', 'N/A')}")

        print(f"\n  📁 Challans: {config.CHALLAN_OUTPUT_DIR}")
        print(f"  📁 Snapshots: snapshots/")
        print(f"  📁 Database: {config.DATABASE_PATH}")
        print(f"{'═'*60}\n")

        self.database.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="AI Speed Challan System"
    )
    parser.add_argument('--source', '-s', type=str, default=None)
    parser.add_argument('--speed-limit', '-l', type=int, default=None)
    parser.add_argument('--no-yolo', action='store_true',
                        help='Use contour detection instead of YOLO')
    parser.add_argument('--debug', action='store_true')

    args = parser.parse_args()

    if args.speed_limit:
        config.SPEED_LIMIT_KPH = args.speed_limit
    if args.debug:
        config.DEBUG_MODE = True

    source = args.source
    if source and source.isdigit():
        source = int(source)

    # ── KEY FIX: Use contour detection for demo videos ──
    use_yolo = not args.no_yolo

    system = SpeedChallanSystem(
        video_source=source,
        use_yolo=use_yolo
    )
    system.run()


if __name__ == "__main__":
    main()