"""
Improved demo video generator with cars that YOLO can better detect,
OR that work with contour-based detection.
"""

import cv2
import numpy as np
import random


def generate_demo_video(output_path="traffic_video.mp4",
                         duration_sec=30, fps=30):
    
    width, height = 800, 600
    total_frames = duration_sec * fps

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    vehicles = []
    spawn_interval = fps  # Every 1 second

    lanes = [150, 300, 500, 650]

    print(f"[DEMO] Generating {duration_sec}s video...")

    # Background (static road)
    road_bg = np.zeros((height, width, 3), dtype=np.uint8)
    road_bg[:] = (50, 50, 50)
    
    # Road markings
    cv2.line(road_bg, (100, 0), (100, height), (0, 180, 255), 3)
    cv2.line(road_bg, (700, 0), (700, height), (0, 180, 255), 3)
    
    for y in range(0, height, 50):
        cv2.line(road_bg, (400, y), (400, y+25), (255, 255, 255), 2)

    for i in range(total_frames):
        frame = road_bg.copy()

        # Spawn vehicles
        if i % spawn_interval == 0:
            lane = random.choice(lanes)
            car_w = random.randint(50, 80)
            car_h = random.randint(60, 100)

            # Mix of slow and fast vehicles
            if random.random() < 0.4:
                # FAST vehicle (will trigger violation)
                speed = random.uniform(8, 15)
            else:
                # Normal vehicle
                speed = random.uniform(2, 5)

            color = [random.randint(100, 255) for _ in range(3)]
            plate = (f"{random.choice(['DL','MH','KA','UP'])}"
                     f"{random.randint(10,99)}"
                     f"{chr(random.randint(65,90))}"
                     f"{chr(random.randint(65,90))}"
                     f"{random.randint(1000,9999)}")

            vehicles.append({
                'x': lane - car_w // 2,
                'y': -car_h - random.randint(0, 50),
                'w': car_w,
                'h': car_h,
                'speed': speed,
                'color': tuple(color),
                'plate': plate
            })

        # Update and draw
        active = []
        for v in vehicles:
            v['y'] += v['speed']

            if v['y'] > height + 50:
                continue

            active.append(v)
            x, y = int(v['x']), int(v['y'])
            w, h = v['w'], v['h']

            if y + h < 0:
                continue

            # Draw car (filled rectangle)
            cv2.rectangle(frame, (x, y), (x+w, y+h), v['color'], -1)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (20, 20, 20), 2)

            # Windshield
            cv2.rectangle(frame, (x+5, y+3),
                         (x+w-5, y+h//3), (180, 200, 230), -1)

            # License plate
            pw, ph = w-16, 14
            px, py = x+8, y+h-18
            cv2.rectangle(frame, (px, py), (px+pw, py+ph),
                         (255, 255, 255), -1)
            cv2.putText(frame, v['plate'][:8], (px+2, py+11),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)

            # Speed label
            spd = v['speed'] * 6  # Visual speed indicator
            col = (0, 0, 255) if spd > 40 else (0, 200, 0)
            cv2.putText(frame, f"{spd:.0f}km/h", (x, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, col, 1)

        vehicles = active

        # Detection lines
        line_y1 = int(height * 0.35)
        line_y2 = int(height * 0.65)
        cv2.line(frame, (100, line_y1), (700, line_y1), (0, 255, 0), 2)
        cv2.line(frame, (100, line_y2), (700, line_y2), (0, 0, 255), 2)
        
        cv2.putText(frame, f"LINE 1 (Y={line_y1})", (105, line_y1-5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        cv2.putText(frame, f"LINE 2 (Y={line_y2})", (105, line_y2-5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        # Frame info
        cv2.putText(frame,
                   f"DEMO | Frame {i}/{total_frames} | "
                   f"Vehicles: {len(active)}",
                   (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                   0.5, (255, 255, 255), 1)

        writer.write(frame)

    writer.release()
    print(f"✅ Video saved: {output_path}")
    print(f"   Frames: {total_frames}, Duration: {duration_sec}s")
    print(f"\n   Run with:")
    print(f"   python main.py --source {output_path} --no-yolo")


if __name__ == "__main__":
    generate_demo_video()
