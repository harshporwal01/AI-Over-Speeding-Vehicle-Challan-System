"""
Realistic Challan Generator with Indian Traffic Fine Rules.
"""

import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import config


class ChallanGenerator:
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or config.CHALLAN_OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        self.styles.add(ParagraphStyle(
            name='ChallanTitle',
            parent=self.styles['Title'],
            fontSize=18,
            textColor=colors.HexColor('#CC0000'),
            alignment=TA_CENTER,
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            name='ChallanSubtitle',
            parent=self.styles['Normal'],
            fontSize=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#333333'),
            spaceAfter=10
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#003366'),
            spaceBefore=10,
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            name='WarningText',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#CC0000'),
            alignment=TA_CENTER,
            spaceBefore=8
        ))

    def get_speed_limit_for_vehicle(self, vehicle_type):
        """
        Get speed limit based on vehicle type and zone.
        """
        zone = config.ZONE_TYPE
        limits = config.SPEED_LIMITS.get(zone, config.SPEED_LIMITS["city"])
        return limits.get(vehicle_type, limits["default"])

    def get_violation_severity(self, excess_speed):
        """
        Classify violation severity.
        
        Returns:
            severity: str
            description: str
        """
        if excess_speed <= 20:
            return "light", "Minor Over-Speeding"
        elif excess_speed <= 40:
            return "moderate", "Moderate Over-Speeding"
        elif excess_speed <= 60:
            return "heavy", "Heavy Over-Speeding"
        else:
            return "extreme", "Extreme/Dangerous Over-Speeding"

    def calculate_fine(self, detected_speed, speed_limit,
                        vehicle_type="Car", is_repeat=False):
        """
        Calculate fine based on Indian Motor Vehicles Act 2019.
        
        Fine Structure:
        ┌────────────────┬───────────────┬────────────────┐
        │ Excess Speed   │ First Offence │ Repeat Offence │
        ├────────────────┼───────────────┼────────────────┤
        │  1-20 km/h     │ ₹1,000        │ ₹2,000         │
        │ 21-40 km/h     │ ₹2,000        │ ₹4,000         │
        │ 41-60 km/h     │ ₹4,000        │ ₹8,000         │
        │ 60+  km/h      │ ₹10,000       │ ₹20,000        │
        └────────────────┴───────────────┴────────────────┘
        """
        excess_speed = detected_speed - speed_limit

        if excess_speed <= 0:
            return 0

        # Get severity
        severity, _ = self.get_violation_severity(excess_speed)

        # Get fine from structure
        offence_type = "repeat_offence" if is_repeat else "first_offence"
        base_fine = config.FINE_STRUCTURE[offence_type][severity]

        # Additional per-km/h charge for heavy violations
        if excess_speed > 20:
            additional = (excess_speed - 20) * config.FINE_PER_KPH_OVER
            base_fine += additional

        # Heavy vehicle surcharge (buses, trucks)
        if vehicle_type in ["Bus", "Truck"]:
            base_fine = int(base_fine * 1.5)

        # Ensure minimum fine
        fine = max(config.MINIMUM_FINE, base_fine)

        return round(fine, 2)

    def generate(self, violation_data, snapshot_path=None):
        """Generate PDF challan."""
        challan_id = violation_data.get('violation_id',
                                         datetime.now().strftime('%Y%m%d%H%M%S'))
        filename = f"CHALLAN_{challan_id}.pdf"
        filepath = os.path.join(self.output_dir, filename)

        doc = SimpleDocTemplate(
            filepath, pagesize=A4,
            rightMargin=30, leftMargin=30,
            topMargin=25, bottomMargin=25
        )

        elements = []
        detected_speed = violation_data.get('detected_speed', 0)
        speed_limit = violation_data.get('speed_limit', config.SPEED_LIMIT_KPH)
        excess = round(detected_speed - speed_limit, 1)
        fine_amount = violation_data.get('fine_amount', 0)
        severity, severity_desc = self.get_violation_severity(excess)
        vehicle_type = violation_data.get('vehicle_type', 'Car')
        plate = violation_data.get('plate_number', 'UNKNOWN')
        violation_time = violation_data.get('violation_time',
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        deadline = (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')

        # ── Header ──
        elements.append(Paragraph(
            "⚠ E-CHALLAN - TRAFFIC VIOLATION NOTICE ⚠",
            self.styles['ChallanTitle']
        ))
        elements.append(Paragraph(
            f"{config.AUTHORITY_NAME}<br/>"
            f"{config.CITY} | Motor Vehicles Act, 2019 - Section 183",
            self.styles['ChallanSubtitle']
        ))
        elements.append(Spacer(1, 4))

        # ── Challan Info ──
        elements.append(Paragraph(
            "📋 Challan Information", self.styles['SectionHeader']
        ))
        info = [
            ['Challan No.', f'E-TRF-{challan_id:06d}' if isinstance(challan_id, int)
             else f'E-TRF-{challan_id}'],
            ['Date & Time', violation_time],
            ['Location', violation_data.get('location', config.CITY)],
            ['Zone Type', config.ZONE_TYPE.upper()],
            ['Violation', f'OVER SPEEDING ({severity_desc})'],
            ['Section', 'MV Act 2019 - Section 183'],
        ]
        elements.append(self._make_table(info))
        elements.append(Spacer(1, 6))

        # ── Vehicle Info ──
        elements.append(Paragraph(
            "🚗 Vehicle Details", self.styles['SectionHeader']
        ))
        veh_info = [
            ['Registration No.', plate],
            ['Vehicle Type', vehicle_type],
            ['Speed Limit (for this vehicle)', f'{speed_limit} km/h'],
        ]
        elements.append(self._make_table(veh_info))
        elements.append(Spacer(1, 6))

        # ── Speed Details ──
        elements.append(Paragraph(
            "🏎 Speed Violation Details", self.styles['SectionHeader']
        ))
        speed_info = [
            ['Posted Speed Limit', f'{speed_limit} km/h'],
            ['Your Detected Speed', f'{detected_speed} km/h'],
            ['Over the Limit by', f'{excess} km/h'],
            ['Severity', severity_desc.upper()],
        ]
        t = self._make_table(speed_info)
        # Highlight speed in red
        t.setStyle(TableStyle([
            ('TEXTCOLOR', (1, 1), (1, 1), colors.red),
            ('TEXTCOLOR', (1, 2), (1, 2), colors.red),
            ('FONTNAME', (1, 1), (1, 2), 'Helvetica-Bold'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 6))

        # ── Fine Breakdown ──
        elements.append(Paragraph(
            "💰 Fine Details", self.styles['SectionHeader']
        ))

        # Build fine breakdown
        fine_rows = [
            ['Description', 'Amount'],
            [f'Base fine ({severity_desc})',
             f'₹{config.FINE_STRUCTURE["first_offence"][severity]:,}'],
        ]
        if excess > 20:
            additional = (excess - 20) * config.FINE_PER_KPH_OVER
            fine_rows.append(
                [f'Additional charge ({excess-20:.0f} km/h × '
                 f'₹{config.FINE_PER_KPH_OVER})',
                 f'₹{additional:,.0f}']
            )
        if vehicle_type in ["Bus", "Truck"]:
            fine_rows.append(
                ['Heavy vehicle surcharge (50%)',
                 f'₹{fine_amount * 0.33:,.0f}']
            )
        fine_rows.append(['', ''])
        fine_rows.append(['TOTAL FINE AMOUNT', f'₹{fine_amount:,.2f}'])
        fine_rows.append(['Payment Deadline', deadline])
        fine_rows.append(['Status', 'UNPAID'])

        ft = Table(fine_rows, colWidths=[300, 200])
        ft.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -3), (-1, -3), colors.HexColor('#FFEEEE')),
            ('FONTNAME', (0, -3), (-1, -3), 'Helvetica-Bold'),
            ('FONTSIZE', (1, -3), (1, -3), 14),
            ('TEXTCOLOR', (1, -3), (1, -3), colors.HexColor('#CC0000')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(ft)
        elements.append(Spacer(1, 8))

        # ── Additional Penalties Warning ──
        if excess >= config.LICENSE_SUSPENSION_THRESHOLD:
            elements.append(Paragraph(
                f"⚠ WARNING: Your speed exceeded the limit by {excess:.0f} km/h. "
                f"This may result in LICENSE SUSPENSION as per Section 19 "
                f"of the Motor Vehicles Act.",
                self.styles['WarningText']
            ))

        if excess >= config.COURT_APPEARANCE_THRESHOLD:
            elements.append(Paragraph(
                "🔴 COURT APPEARANCE REQUIRED: Due to extreme over-speeding, "
                "you are required to appear before the Traffic Court.",
                self.styles['WarningText']
            ))

        elements.append(Spacer(1, 6))

        # ── Snapshot ──
        if snapshot_path and os.path.exists(snapshot_path):
            elements.append(Paragraph(
                "📸 Evidence", self.styles['SectionHeader']
            ))
            try:
                img = RLImage(snapshot_path, width=3.5*inch, height=2.5*inch)
                elements.append(img)
            except Exception:
                pass
            elements.append(Spacer(1, 6))

        # ── Payment Info ──
        elements.append(Paragraph(
            "💳 Payment Options", self.styles['SectionHeader']
        ))
        payment_info = [
            "1. Online: https://echallan.parivahan.gov.in",
            "2. Nearest Traffic Police Station",
            "3. Designated Bank Branches",
            f"4. Payment Deadline: {deadline}",
            "",
            "Late payment penalty: ₹500 per week after deadline"
        ]
        for line in payment_info:
            elements.append(Paragraph(line, self.styles['Normal']))

        elements.append(Spacer(1, 10))

        # ── Disclaimer ──
        elements.append(Paragraph(
            "This is a computer-generated e-Challan. "
            "For disputes, contact the Traffic Police Department within 30 days. "
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ParagraphStyle('Footer', parent=self.styles['Normal'],
                          fontSize=7, textColor=colors.grey,
                          alignment=TA_CENTER)
        ))

        doc.build(elements)
        print(f"  [CHALLAN] PDF saved: {filepath}")
        return filepath

    def _make_table(self, data, col_widths=None):
        """Helper to create a styled table."""
        if col_widths is None:
            col_widths = [200, 300]
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8E8E8')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        return t