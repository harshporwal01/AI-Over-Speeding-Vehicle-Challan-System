# AI-Over-Speeding-Vehicle-Challan-System
An AI-powered Traffic Enforcement System that automatically detects vehicles, estimates their speed, identifies over-speeding violations, recognizes license plates, and generates PDF challans according to the Indian Motor Vehicles Act (2019).

🧠 System Workflow

1️⃣ Vehicle detection from video frame

2️⃣ Vehicle tracking across frames

3️⃣ Speed estimation using distance between detection lines

4️⃣ Check if speed exceeds the configured limit

5️⃣ Capture vehicle snapshot

6️⃣ Extract license plate using OCR

7️⃣ Calculate fine based on Motor Vehicles Act 2019

8️⃣ Generate PDF challan

9️⃣ Store violation in SQLite database


🛠️ Technologies Used

Technology	Purpose

Python	Core programming language

OpenCV	Video processing

YOLOv8	Vehicle detection

EasyOCR	License plate recognition

NumPy	Numerical operations

SQLite	Database for violations

ReportLab	PDF challan generation

SciPy	Distance calculations

FilterPy	Tracking algorithms

⚙️ Installation

1️⃣ Clone the repository

git clone git clone https://github.com/yourusername/AI-Traffic-Challan-System.git

cd AI-Over-Speeding-Vehicle-Challan-System

2️⃣ Install dependencies

pip install -r requirements.txt

🧪 Demo Mode

If no video is available, the system automatically generates a demo traffic video using:

demo_generator.py

▶️ Running the Project

Run the system

python main.py

Run with custom video

python main.py --source traffic_video.mp4 --no-yolo
