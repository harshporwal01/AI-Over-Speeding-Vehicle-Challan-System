"""
Realistic Indian Traffic Fine Configuration
Based on Motor Vehicles (Amendment) Act, 2019
"""

# ──────────────────────────────────────────────
# SPEED LIMITS (Indian Standards)
# ──────────────────────────────────────────────

# Choose the zone type:
ZONE_TYPE = "city"  # Options: "city", "highway", "school", "residential"

SPEED_LIMITS = {
    "city": {
        "Car":        50,   # km/h
        "Motorcycle":  40,
        "Bus":        40,
        "Truck":      40,
        "default":    50
    },
    "highway": {
        "Car":        100,
        "Motorcycle":  80,
        "Bus":        80,
        "Truck":      60,
        "default":    80
    },
    "school": {
        "Car":        25,
        "Motorcycle":  25,
        "Bus":        25,
        "Truck":      25,
        "default":    25
    },
    "residential": {
        "Car":        30,
        "Motorcycle":  30,
        "Bus":        30,
        "Truck":      30,
        "default":    30
    }
}

# Default speed limit (used if zone not specified)
SPEED_LIMIT_KPH = SPEED_LIMITS[ZONE_TYPE]["default"]

# ──────────────────────────────────────────────
# FINE STRUCTURE (Motor Vehicles Act 2019)
# ──────────────────────────────────────────────

FINE_STRUCTURE = {
    "first_offence": {
        "light":    1000,   # 1-20 km/h over limit
        "moderate": 2000,   # 21-40 km/h over limit  
        "heavy":    4000,   # 41-60 km/h over limit
        "extreme":  10000,  # 60+ km/h over limit
    },
    "repeat_offence": {
        "light":    2000,
        "moderate": 4000,
        "heavy":    8000,
        "extreme":  20000,
    }
}

# Additional penalties
LICENSE_SUSPENSION_THRESHOLD = 40   # km/h over limit → license suspension warning
COURT_APPEARANCE_THRESHOLD = 60    # km/h over limit → must appear in court

# LMV (Light Motor Vehicle) specific
FINE_PER_KPH_OVER = 50
MINIMUM_FINE = 1000    # ₹1,000 minimum (as per 2019 Act)

# ──────────────────────────────────────────────
# OTHER CONFIG (same as before)
# ──────────────────────────────────────────────
FRAME_RATE = 30
PIXELS_PER_METER = 8.8

DETECTION_LINE_Y1 = 300
DETECTION_LINE_Y2 = 500
REAL_DISTANCE_METERS = 20

YOLO_MODEL = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.3
VEHICLE_CLASSES = [2, 3, 5, 7]

DATABASE_PATH = "violations.db"
CHALLAN_OUTPUT_DIR = "challans/"
AUTHORITY_NAME = "Traffic Police Department"
CITY = "New Delhi"

VIDEO_SOURCE = "traffic_video.mp4"
DEBUG_MODE = True