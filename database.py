"""
SQLite database for storing traffic violations.
"""

import sqlite3
import os
from datetime import datetime
import config


class ViolationDatabase:
    """Manages the violations database."""

    def __init__(self, db_path=None):
        self.db_path = db_path or config.DATABASE_PATH
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()
        print(f"[INFO] Database initialized: {self.db_path}")

    def _create_tables(self):
        """Create violations table if not exists."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                plate_number TEXT,
                vehicle_type TEXT,
                detected_speed REAL,
                speed_limit REAL,
                fine_amount REAL,
                violation_time TEXT,
                location TEXT,
                challan_path TEXT,
                snapshot_path TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def add_violation(self, vehicle_id, plate_number, vehicle_type,
                      detected_speed, speed_limit, fine_amount,
                      location="", challan_path="", snapshot_path=""):
        """Insert a new violation record."""
        cursor = self.conn.cursor()
        violation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute('''
            INSERT INTO violations
            (vehicle_id, plate_number, vehicle_type, detected_speed,
             speed_limit, fine_amount, violation_time, location,
             challan_path, snapshot_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            vehicle_id, plate_number, vehicle_type, detected_speed,
            speed_limit, fine_amount, violation_time, location,
            challan_path, snapshot_path
        ))
        self.conn.commit()
        violation_id = cursor.lastrowid
        print(f"[DB] Violation #{violation_id} recorded: "
              f"{plate_number} @ {detected_speed} km/h")
        return violation_id

    def get_all_violations(self):
        """Retrieve all violations."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM violations ORDER BY created_at DESC")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def get_violation_by_id(self, violation_id):
        """Retrieve a specific violation."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM violations WHERE id = ?", (violation_id,))
        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        return dict(zip(columns, row)) if row else None

    def get_violations_by_plate(self, plate_number):
        """Find violations for a specific plate."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM violations WHERE plate_number LIKE ?",
            (f"%{plate_number}%",)
        )
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def update_status(self, violation_id, status):
        """Update violation status (PENDING/PAID/DISPUTED)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE violations SET status = ? WHERE id = ?",
            (status, violation_id)
        )
        self.conn.commit()

    def get_statistics(self):
        """Get violation statistics."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM violations")
        total = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM violations WHERE status='PENDING'"
        )
        pending = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(fine_amount) FROM violations")
        total_fines = cursor.fetchone()[0] or 0

        cursor.execute("SELECT AVG(detected_speed) FROM violations")
        avg_speed = cursor.fetchone()[0] or 0

        cursor.execute("SELECT MAX(detected_speed) FROM violations")
        max_speed = cursor.fetchone()[0] or 0

        return {
            'total_violations': total,
            'pending': pending,
            'total_fines': round(total_fines, 2),
            'avg_speed': round(avg_speed, 2),
            'max_speed': round(max_speed, 2)
        }

    def close(self):
        """Close database connection."""
        self.conn.close()