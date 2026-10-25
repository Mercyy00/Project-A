"""
Project JARVIS - Native PyQt6 Desktop HUD Application (Mark LVI Authentic Edition).
Author: Rohit (Frontend & Desktop UI Specialist) & Aryan (Voice Specialist)

Provides a native high-performance PyQt6 desktop interface featuring:
- Mathematically animated Arc Reactor / Neural Core with vector geometry and blueprint grid
- Dynamic symmetrical Cyber Waveform Audio Visualizer (Mark LVI studio grade)
- Real-time audio amplitude and viseme reactivity
- Hardware telemetry gauges (CPU %, RAM %, Storage Drive %, Engine Latency)
- Live bi-directional chat / voice stream transcripts and tool execution steps
- Quick action command chips and direct text directive prompt
- Startup API Key Configuration modal window with clipboard paste support
- Global F4 hardware microphone mute toggle
"""

from __future__ import annotations

import asyncio
import math
import os
import re
import sys
import threading
import time
from typing import Any, Dict, List, Optional

import psutil
from PyQt6.QtCore import (
    QLineF, QObject, QPointF, QRectF, Qt, QThread, QTimer, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPen, QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSizePolicy, QTextEdit, QVBoxLayout, QWidget,
)

# Sci-fi aesthetic color palette
class HUDColors:
    BG = "#010811"
    PANEL = "#031120"
    PANEL_ALT = "#051a30"
    BORDER = "#0a3a5c"
    BORDER_GLOW = "#00e5ff"
    CYAN = "#00e5ff"
    CYAN_DIM = "#007a8a"
    GREEN = "#00ff88"
    AMBER = "#ffb300"
    RED = "#ff3366"
    TEXT_BRIGHT = "#e0f7fa"
    TEXT_DIM = "#548299"
    BAR_BG = "#061828"


def qcol(hex_str: str, alpha: int = 255) -> QColor:
    """Helper to convert hex string and alpha into QColor."""
    c = QColor(hex_str)
    c.setAlpha(alpha)
    return c


def save_api_key_to_env(api_key: str) -> bool:
    """Save the Gemini API key to .env file and update environment variables."""
    api_key = api_key.strip()
    if not api_key:
        return False
    os.environ["GEMINI_API_KEY"] = api_key
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, ".env")
    try:
        content = ""
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()

        pattern = r"^GEMINI_API_KEY=.*$"
        if re.search(pattern, content, flags=re.MULTILINE):
            new_content = re.sub(pattern, f"GEMINI_API_KEY={api_key}", content, flags=re.MULTILINE)
        else:
            new_content = f"GEMINI_API_KEY={api_key}\n" + content

        with open(env_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    except Exception as exc:
        print(f"[WARN] Failed to write API key to .env: {exc}", file=sys.stderr)
        return False


class ApiKeyDialog(QDialog):
    """Futuristic Sci-Fi Modal Dialog for entering or modifying GEMINI_API_KEY."""

    def __init__(self, current_key: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("JARVIS ACCESS KEY // AUTHENTICATION")
        self.setFixedSize(540, 310)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #020c18;
                border: 2px solid {HUDColors.CYAN};
                border-radius: 8px;
            }}
            QLabel {{
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(10)

        # Title
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title_lbl = QLabel("◈  JARVIS NEURAL ACCESS KEY CONFIGURATION")
        title_lbl.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {HUDColors.CYAN}; letter-spacing: 1px;")
        sub_lbl = QLabel("Enter your Google Gemini API key to initialize the neural full-duplex engine.")
        sub_lbl.setFont(QFont("Courier New", 8))
        sub_lbl.setStyleSheet(f"color: {HUDColors.TEXT_DIM};")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        layout.addLayout(title_box)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {HUDColors.BORDER};")
        layout.addWidget(sep)

        # Field Label
        field_lbl = QLabel("GEMINI API KEY (Format: AIzaSy...)")
        field_lbl.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        field_lbl.setStyleSheet(f"color: {HUDColors.CYAN_DIM};")
        layout.addWidget(field_lbl)

        # Input Row (QLineEdit + Paste + Show/Hide)
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Paste your AIza... key here")
        self.key_input.setFont(QFont("Courier New", 9))
        self.key_input.setFixedHeight(34)
        if current_key and not current_key.startswith("your_gemini"):
            self.key_input.setText(current_key)
        self.key_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #051627;
                color: #ffffff;
                border: 1px solid {HUDColors.BORDER};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {HUDColors.CYAN};
            }}
        """)
        input_row.addWidget(self.key_input, 1)

        paste_btn = QPushButton("📋 PASTE")
        paste_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        paste_btn.setFixedHeight(34)
        paste_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #08263f;
                color: {HUDColors.CYAN};
                border: 1px solid {HUDColors.BORDER};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: #0d385c;
                border: 1px solid {HUDColors.CYAN};
            }}
        """)
        paste_btn.clicked.connect(self._paste_clipboard)
        input_row.addWidget(paste_btn)

        self.toggle_eye_btn = QPushButton("👁 SHOW")
        self.toggle_eye_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.toggle_eye_btn.setFixedHeight(34)
        self.toggle_eye_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #08263f;
                color: {HUDColors.TEXT_DIM};
                border: 1px solid {HUDColors.BORDER};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                color: {HUDColors.TEXT_BRIGHT};
            }}
        """)
        self.toggle_eye_btn.clicked.connect(self._toggle_echo_mode)
        input_row.addWidget(self.toggle_eye_btn)

        layout.addLayout(input_row)

        # Help hint
        hint_lbl = QLabel("Need an API key? Get one free: https://aistudio.google.com")
        hint_lbl.setFont(QFont("Courier New", 8))
        hint_lbl.setStyleSheet(f"color: {HUDColors.TEXT_DIM};")
        layout.addWidget(hint_lbl)

        # Save checkbox
        self.save_check = QCheckBox("Save key to .env file for future sessions")
        self.save_check.setChecked(True)
        self.save_check.setFont(QFont("Courier New", 8))
        self.save_check.setStyleSheet(f"color: {HUDColors.CYAN};")
        layout.addWidget(self.save_check)

        layout.addStretch(1)

        # Bottom Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("CANCEL / SKIP")
        cancel_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        cancel_btn.setFixedHeight(34)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #041424;
                color: {HUDColors.TEXT_DIM};
                border: 1px solid {HUDColors.BORDER};
                border-radius: 4px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                color: {HUDColors.TEXT_BRIGHT};
                border: 1px solid {HUDColors.TEXT_DIM};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("◈ INITIALIZE NEURAL CORE")
        save_btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        save_btn.setFixedHeight(34)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #0b3d61;
                color: {HUDColors.CYAN};
                border: 1px solid {HUDColors.CYAN};
                border-radius: 4px;
                padding: 6px 20px;
            }}
            QPushButton:hover {{
                background-color: #125484;
                color: #ffffff;
            }}
        """)
        save_btn.clicked.connect(self._save_and_accept)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _paste_clipboard(self) -> None:
        """Paste text from system clipboard into input field."""
        clip = QApplication.clipboard().text().strip()
        if clip:
            self.key_input.setText(clip)

    def _toggle_echo_mode(self) -> None:
        """Toggle between password masked and visible text."""
        if self.key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_eye_btn.setText("🔒 HIDE")
        else:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_eye_btn.setText("👁 SHOW")

    def _save_and_accept(self) -> None:
        """Validate key, write to environment, and close dialog."""
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Invalid Key", "Please paste or enter a valid Gemini API key.")
            return

        if self.save_check.isChecked():
            save_api_key_to_env(key)
        else:
            os.environ["GEMINI_API_KEY"] = key

        self.accept()


class ArcReactorWidget(QWidget):
    """Native QPainter Arc Reactor / Neural Core animation widget with blueprint matrix."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.state: str = "LISTENING"  # "IDLE", "LISTENING", "SPEAKING", "THINKING", "MUTED"
        self.speaking: bool = False
        self.muted: bool = False
        self._live_amp: float = 0.05
        self._amp_disp: float = 0.05
        self._phase: float = 0.0

        # Animation timer (60 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step_animation)
        self._timer.start(16)

    def set_state(self, state: str) -> None:
        """Update core state (e.g., LISTENING, SPEAKING, THINKING, MUTED)."""
        self.state = state.upper()
        self.update()

    def set_amplitude(self, amp: float) -> None:
        """Set voice amplitude level [0.0, 1.0]."""
        self._live_amp = max(0.0, min(1.0, float(amp)))

    def _step_animation(self) -> None:
        """Advance animation frame."""
        rate = 0.04
        if self.state in ("THINKING", "PROCESSING"):
            rate = 0.12
        elif self.speaking:
            rate = 0.08

        self._phase += rate
        self._amp_disp += (self._live_amp - self._amp_disp) * 0.15
        self._live_amp = max(0.02, self._live_amp * 0.92)
        self.update()

    def paintEvent(self, _event: Any) -> None:
        """Render the animated Arc Reactor using vector geometry and sci-fi matrix."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), qcol(HUDColors.BG))

        w, h = float(self.width()), float(self.height())
        cx, cy = w / 2.0, h / 2.0
        r = min(w, h) * 0.44
        if r < 20:
            return

        amp = self._amp_disp
        t = self._phase

        # Colors based on state
        if self.muted:
            main_col, acc_col = qcol(HUDColors.RED), qcol(HUDColors.RED, 180)
        elif self.speaking:
            main_col, acc_col = qcol(HUDColors.CYAN), qcol(HUDColors.AMBER)
        elif self.state in ("THINKING", "PROCESSING"):
            main_col, acc_col = qcol(HUDColors.AMBER), qcol(HUDColors.CYAN)
        elif self.state == "LISTENING":
            main_col, acc_col = qcol(HUDColors.CYAN), qcol(HUDColors.GREEN)
        else:
            main_col, acc_col = qcol(HUDColors.CYAN), qcol(HUDColors.CYAN_DIM)

        # 0. Blueprint Grid Dots
        p.setPen(QPen(qcol(HUDColors.CYAN, 24), 1))
        step = 32
        for gx in range(0, int(w), step):
            for gy in range(0, int(h), step):
                p.drawPoint(gx, gy)

        # 1. Corner Framing Crosshairs (Blueprint Brackets)
        m, arm = 12.0, 16.0
        p.setPen(QPen(qcol(HUDColors.CYAN, 70), 1.2))
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            x = cx + sx * (w / 2.0 - m)
            y = cy + sy * (h / 2.0 - m)
            p.drawLine(QLineF(x, y, x - sx * arm, y))
            p.drawLine(QLineF(x, y, x, y - sy * arm))

        # 2. Canvas Crosshairs broken around core
        gap = r * 0.72
        p.setPen(QPen(qcol(HUDColors.CYAN, 35), 1))
        p.drawLine(QLineF(cx - w * 0.46, cy, cx - gap, cy))
        p.drawLine(QLineF(cx + gap, cy, cx + w * 0.46, cy))
        p.drawLine(QLineF(cx, cy - h * 0.46, cx, cy - gap))
        p.drawLine(QLineF(cx, cy + gap, cx, cy + h * 0.46))

        # 3. Cardinal Degree Markers
        p.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol(HUDColors.CYAN_DIM, 120), 1))
        p.drawText(QRectF(cx - 20, cy - r * 1.05 - 12, 40, 12), Qt.AlignmentFlag.AlignCenter, "000°")
        p.drawText(QRectF(cx + r * 1.05 + 4, cy - 6, 36, 12), Qt.AlignmentFlag.AlignLeft, "090°")
        p.drawText(QRectF(cx - 20, cy + r * 1.05 + 2, 40, 12), Qt.AlignmentFlag.AlignCenter, "180°")
        p.drawText(QRectF(cx - r * 1.05 - 40, cy - 6, 36, 12), Qt.AlignmentFlag.AlignRight, "270°")

        # 4. Background Radial Atmosphere Glow
        glow_rad = r * (0.65 + 0.3 * amp)
        glow = QRadialGradient(cx, cy, glow_rad)
        glow.setColorAt(0.0, qcol(acc_col.name(), int(160 + 90 * amp)))
        glow.setColorAt(0.45, qcol(main_col.name(), int(60 + 60 * amp)))
        glow.setColorAt(1.0, qcol(HUDColors.BG, 0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - glow_rad, cy - glow_rad, glow_rad * 2, glow_rad * 2))
        p.setBrush(Qt.BrushStyle.NoBrush)

        # 5. Concentric Rings
        for rr, alpha, width in ((1.0, 90, 1.0), (0.92, 140, 1.2), (0.75, 80, 1.0)):
            p.setPen(QPen(qcol(main_col.name(), alpha), width))
            rad = r * rr
            p.drawEllipse(QRectF(cx - rad, cy - rad, rad * 2, rad * 2))

        # 6. Rotating Tick Graduations (72 radial ticks)
        p.setPen(QPen(qcol(main_col.name(), 120), 1.2))
        lines: List[QLineF] = []
        for i in range(72):
            angle = math.radians(i * 5.0 + t * 4.0)
            ca, sa = math.cos(angle), math.sin(angle)
            len_ratio = 0.94 if i % 6 != 0 else 0.88
            lines.append(QLineF(
                cx + ca * r * len_ratio, cy + sa * r * len_ratio,
                cx + ca * r * 0.98, cy + sa * r * 0.98
            ))
        p.drawLines(lines)

        # 7. Sweeping Segmented Arcs
        arc_specs = [
            (0.85, 120, 2, +1.0, acc_col, 2.2),
            (0.70, 80, 3, -1.2, main_col, 1.5),
            (0.55, 160, 1, +1.5, acc_col, 1.8),
            (0.40, 60, 4, -1.8, main_col, 1.2),
        ]
        for rr, span, count, direction, col, width in arc_specs:
            p.setPen(QPen(col, width))
            rad = r * rr
            box = QRectF(cx - rad, cy - rad, rad * 2, rad * 2)
            base_deg = (t * direction * 25.0) % 360.0
            for k in range(count):
                p.drawArc(box, int((base_deg + k * (360.0 / count)) * 16), int(span * 16))

        # 8. Orbiting Electron Energy Nodes
        for node_i in range(4):
            node_ang = math.radians(node_i * 90.0 + t * 45.0)
            nx = cx + math.cos(node_ang) * (r * 0.92)
            ny = cy + math.sin(node_ang) * (r * 0.92)
            p.setBrush(QBrush(qcol(acc_col.name(), 220)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(nx, ny), 3.0 + 1.5 * amp, 3.0 + 1.5 * amp)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # 9. Core Center Disc & Pulse
        core_r = r * (0.24 + 0.08 * amp)
        p.setBrush(QBrush(qcol(main_col.name(), int(180 + 75 * amp))))
        p.setPen(QPen(qcol(acc_col.name()), 2.0))
        p.drawEllipse(QRectF(cx - core_r, cy - core_r, core_r * 2, core_r * 2))

        # 10. Center Typography ("J.A.R.V.I.S")
        f = QFont("Courier New", int(max(8, r * 0.09)), QFont.Weight.Bold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        p.setFont(f)
        p.setPen(QPen(qcol("#ffffff"), 1))
        p.drawText(QRectF(cx - core_r, cy - 10, core_r * 2, 20), Qt.AlignmentFlag.AlignCenter, "J.A.R.V.I.S")


class WaveformVisualizerWidget(QWidget):
    """Dynamic Sci-Fi Cyber Waveform Audio Visualizer (Mark LVI authentic styling)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(95)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.state: str = "LISTENING"
        self.speaking: bool = False
        self.muted: bool = False
        self._live_amp: float = 0.05
        self._amp_disp: float = 0.05
        self._phase: float = 0.0

        # Animation timer (60 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(16)

    def set_state(self, state: str) -> None:
        self.state = state.upper()
        self.update()

    def set_amplitude(self, amp: float) -> None:
        self._live_amp = max(0.0, min(1.0, float(amp)))

    def _step(self) -> None:
        rate = 0.06 if self.speaking else 0.03
        self._phase += rate
        self._amp_disp += (self._live_amp - self._amp_disp) * 0.18
        self._live_amp = max(0.02, self._live_amp * 0.90)
        self.update()

    def paintEvent(self, _event: Any) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), qcol(HUDColors.BG))

        w, h = float(self.width()), float(self.height())
        cx, cy = w / 2.0, h / 2.0 - 2.0

        amp = self._amp_disp
        t = self._phase

        # 1. Top status label
        p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        status_txt = "MUTED" if self.muted else ("SPEAKING" if self.speaking else (self.state if self.state != "IDLE" else "ONLINE"))
        col_main = HUDColors.RED if self.muted else (HUDColors.AMBER if self.speaking else HUDColors.CYAN)
        p.setPen(QPen(qcol(col_main), 1))
        p.drawText(QRectF(0, 2, w, 16), Qt.AlignmentFlag.AlignCenter, f"{status_txt} // FULL-DUPLEX AUDIO LINK")

        # 2. Subtitle
        p.setFont(QFont("Courier New", 7))
        p.setPen(QPen(qcol(HUDColors.TEXT_DIM), 1))
        p.drawText(QRectF(0, 18, w, 14), Qt.AlignmentFlag.AlignCenter, "GEMINI LIVE · CHARON · REAL-TIME STREAM")

        # 3. Waveform bars (Symmetrical envelope)
        N = 48
        bw = 6.0
        gap = 4.0
        total_span = N * (bw + gap) - gap
        wx0 = cx - total_span / 2.0
        mid = (N - 1) / 2.0

        for i in range(N):
            if self.muted:
                half_h = 2.0
                bar_col = qcol(HUDColors.RED, 160)
            else:
                env = (1.0 - abs(i - mid) / mid) ** 0.68
                wave1 = math.sin(t * 3.6 + i * 0.28)
                wave2 = math.cos(t * 2.1 - i * 0.19)
                shimmer = 0.6 + 0.4 * (wave1 * 0.7 + wave2 * 0.3)
                idle = 3.0 + 2.5 * math.sin(t * 1.6 + i * 0.45)
                live_h = idle + amp * 34.0 * env * shimmer
                half_h = max(2.0, min(36.0, live_h))

                if amp > 0.05:
                    bar_hex = HUDColors.AMBER if self.speaking else (HUDColors.GREEN if half_h > 18 else HUDColors.CYAN)
                    bar_col = qcol(bar_hex, int(180 + 75 * min(1.0, half_h / 24.0)))
                else:
                    bar_col = qcol(HUDColors.CYAN_DIM, int(90 + 50 * shimmer))

            bx = wx0 + i * (bw + gap)
            p.setBrush(QBrush(bar_col))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(bx, cy - half_h + 14, bw, half_h * 2.0), 2.0, 2.0)

        # 4. Bottom hint
        p.setFont(QFont("Courier New", 7))
        p.setPen(QPen(qcol(HUDColors.TEXT_DIM), 1))
        hint_text = "[MICROPHONE MUTED - PRESS F4 TO UNMUTE]" if self.muted else "[ACOUSTIC BARGE-IN ARMED · SPEAK FREELY ANYTIME · F4 TO MUTE]"
        p.drawText(QRectF(0, h - 16, w, 14), Qt.AlignmentFlag.AlignCenter, hint_text)


class MetricBarWidget(QWidget):
    """Gauge bar widget displaying a metric percentage and value."""

    def __init__(self, label: str, unit: str = "%", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._label: str = label
        self._unit: str = unit
        self._value: float = 0.0
        self._text: str = "--"
        self.setFixedHeight(34)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_value(self, value: float, display_text: str) -> None:
        """Update gauge reading."""
        self._value = max(0.0, min(100.0, float(value)))
        self._text = display_text
        self.update()

    def paintEvent(self, _event: Any) -> None:
        """Draw the metric bar."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())

        # Container
        p.setBrush(QBrush(qcol(HUDColors.PANEL)))
        p.setPen(QPen(qcol(HUDColors.BORDER), 1))
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 4, 4)

        # Bar background
        bar_h, bar_y = 4.0, h - 8.0
        bar_w = w - 16.0
        p.setBrush(QBrush(qcol(HUDColors.BAR_BG)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(8, bar_y, bar_w, bar_h), 2, 2)

        # Bar fill
        fill_w = (bar_w * self._value) / 100.0
        fill_col = qcol(HUDColors.CYAN)
        if self._value > 85.0:
            fill_col = qcol(HUDColors.RED)
        elif self._value > 65.0:
            fill_col = qcol(HUDColors.AMBER)

        if fill_w > 0:
            p.setBrush(QBrush(fill_col))
            p.drawRoundedRect(QRectF(8, bar_y, fill_w, bar_h), 2, 2)

        # Labels
        p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(HUDColors.TEXT_DIM), 1))
        p.drawText(QRectF(8, 4, 120, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._label)

        p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        p.setPen(QPen(fill_col, 1))
        p.drawText(QRectF(w - 90, 4, 82, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._text)


class VoiceThread(QThread):
    """Dedicated background worker thread for GeminiLiveEngine."""

    status_signal = pyqtSignal(dict)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._engine: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._is_active: bool = True

    def run(self) -> None:
        """Run asyncio loop for Gemini Live voice."""
        from voice.gemini_live import GeminiLiveEngine

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        def on_event(event: Dict[str, str]) -> None:
            self.status_signal.emit(event)

        try:
            self._engine = GeminiLiveEngine(event_callback=on_event)
            self._loop.run_until_complete(self._engine.run())
        except Exception as exc:
            self.status_signal.emit({
                "type": "voice_status", "status": "error", "message": str(exc),
            })
        finally:
            if self._loop and not self._loop.is_closed():
                self._loop.close()

    def set_muted(self, muted: bool) -> None:
        """Forward hardware capture mute request to active GeminiLiveEngine."""
        if self._engine:
            self._engine.set_muted(muted)

    def stop(self) -> None:
        """Terminate voice engine cleanly."""
        if self._engine:
            self._engine.stop()
        self.quit()
        self.wait(1500)


class JarvisNativeHUD(QMainWindow):
    """Main window for the Sci-Fi Native PyQt6 JARVIS Desktop Interface."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("JARVIS - SCI-FI DESKTOP NEURAL INTERFACE (MARK LVI)")
        self.resize(1120, 750)
        self.setMinimumSize(880, 580)
        self.setStyleSheet(f"background-color: {HUDColors.BG}; color: {HUDColors.TEXT_BRIGHT};")

        self.voice_thread: Optional[VoiceThread] = None
        self._is_muted: bool = False

        self._init_ui()
        self._init_telemetry_timer()
        self._start_voice_engine()

        # Prompt API key configuration dialog on startup as requested by the user
        QTimer.singleShot(150, self._check_startup_api_key)

    def _init_ui(self) -> None:
        """Construct the HUD window layout."""
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 12, 16, 16)
        root_layout.setSpacing(10)

        # 1. Top Header Bar
        header = QHBoxLayout()
        header.setSpacing(10)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        app_title = QLabel("PROJECT JARVIS // MARK LVI")
        app_title.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
        app_title.setStyleSheet(f"color: {HUDColors.CYAN}; letter-spacing: 2px;")
        sub_title = QLabel("SYSTEM KERNEL: FULL-DUPLEX LIVE STREAMING ENGINE")
        sub_title.setFont(QFont("Courier New", 8))
        sub_title.setStyleSheet(f"color: {HUDColors.TEXT_DIM};")
        title_box.addWidget(app_title)
        title_box.addWidget(sub_title)
        header.addLayout(title_box)

        header.addStretch(1)

        # API Key Config Button
        self.api_key_btn = QPushButton("🔑 API KEY")
        self.api_key_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.api_key_btn.setStyleSheet(
            f"background-color: #061f38; color: {HUDColors.CYAN}; "
            "padding: 5px 14px; border-radius: 12px; border: 1px solid #00e5ff; cursor: pointer;"
        )
        self.api_key_btn.clicked.connect(self.open_api_key_dialog)
        header.addWidget(self.api_key_btn)

        # Status pills
        self.status_pill = QLabel("● CONNECTING")
        self.status_pill.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.status_pill.setStyleSheet(
            f"background-color: #0b2238; color: {HUDColors.AMBER}; "
            "padding: 5px 12px; border-radius: 12px; border: 1px solid #14446b;"
        )
        header.addWidget(self.status_pill)

        self.voice_pill = QLabel("VOICE: CHARON")
        self.voice_pill.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.voice_pill.setStyleSheet(
            f"background-color: #081a2e; color: {HUDColors.CYAN}; "
            "padding: 5px 12px; border-radius: 12px; border: 1px solid #0a3a5c;"
        )
        header.addWidget(self.voice_pill)

        root_layout.addLayout(header)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {HUDColors.BORDER};")
        root_layout.addWidget(sep)

        # 2. Body Area (Left: Telemetry, Center: Arc Reactor + Waveform, Right: Stream Log)
        body = QHBoxLayout()
        body.setSpacing(14)

        # Left Column: Telemetry Gauges
        left_col = QVBoxLayout()
        left_col.setSpacing(8)
        telemetry_title = QLabel("[SYSTEM TELEMETRY]")
        telemetry_title.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        telemetry_title.setStyleSheet(f"color: {HUDColors.TEXT_DIM};")
        left_col.addWidget(telemetry_title)

        self.cpu_bar = MetricBarWidget("CPU USAGE", "%")
        self.ram_bar = MetricBarWidget("MEMORY USAGE", "%")
        self.lat_bar = MetricBarWidget("VOICE LATENCY", "ms")
        self.disk_bar = MetricBarWidget("STORAGE DRIVE", "%")
        left_col.addWidget(self.cpu_bar)
        left_col.addWidget(self.ram_bar)
        left_col.addWidget(self.lat_bar)
        left_col.addWidget(self.disk_bar)

        left_col.addSpacing(8)
        subsys_title = QLabel("[SUBSYSTEMS]")
        subsys_title.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        subsys_title.setStyleSheet(f"color: {HUDColors.TEXT_DIM};")
        left_col.addWidget(subsys_title)

        try:
            import sounddevice as sd
            in_dev_info = sd.query_devices(kind="input")
            in_dev_name = in_dev_info.get("name", "Default") if isinstance(in_dev_info, dict) else "Default"
            if len(in_dev_name) > 20:
                in_dev_name = in_dev_name[:18] + ".."
        except Exception:
            in_dev_name = "Default"

        self.subsys_box = QLabel(
            "• Gemini Live: ACTIVE\n"
            "• Echo Guard: ARMED\n"
            f"• Mic: {in_dev_name}\n"
            "• WhatsApp Tool: READY\n"
            "• System Tools: 24 OK"
        )
        self.subsys_box.setFont(QFont("Courier New", 8))
        self.subsys_box.setStyleSheet(
            f"background-color: {HUDColors.PANEL}; color: {HUDColors.TEXT_DIM}; "
            f"padding: 8px; border-radius: 4px; border: 1px solid {HUDColors.BORDER}; line-height: 1.4;"
        )
        left_col.addWidget(self.subsys_box)
        left_col.addStretch(1)

        body.addLayout(left_col, 26)

        # Center Column: Arc Reactor Core + Cyber Waveform Visualizer
        center_col = QVBoxLayout()
        center_col.setSpacing(6)
        self.reactor = ArcReactorWidget()
        center_col.addWidget(self.reactor, 1)

        self.waveform = WaveformVisualizerWidget()
        center_col.addWidget(self.waveform)
        body.addLayout(center_col, 42)

        # Right Column: Interaction Stream Log
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        log_title = QLabel("[ACTIVITY & CONVERSATION STREAM]")
        log_title.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        log_title.setStyleSheet(f"color: {HUDColors.TEXT_DIM};")
        right_col.addWidget(log_title)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFont(QFont("Segoe UI, Nirmala UI, Arial", 9))
        self.log_edit.setStyleSheet(
            f"background-color: {HUDColors.PANEL}; border: 1px solid {HUDColors.BORDER}; "
            f"color: {HUDColors.TEXT_BRIGHT}; border-radius: 4px; padding: 8px;"
        )
        right_col.addWidget(self.log_edit)

        body.addLayout(right_col, 32)
        root_layout.addLayout(body, 1)

        # 3. Quick Action Chips
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(8)

        chips = [
            ("🔑 Set API Key", "__apikey__"),
            ("Mute (F4)", "mute"),
            ("WhatsApp", "open whatsapp"),
            ("Search Aryan", "search contact Aryan in whatsapp"),
            ("Send Hello", "message them: hello how are you"),
            ("Status", "system status"),
            ("Clear Log", "__clear__"),
        ]
        for label, cmd in chips:
            btn = QPushButton(label)
            btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
            btn.setStyleSheet(
                f"background-color: {HUDColors.PANEL}; color: {HUDColors.CYAN}; "
                f"border: 1px solid {HUDColors.BORDER}; border-radius: 4px; padding: 4px 10px;"
            )
            btn.clicked.connect(lambda _checked, c=cmd: self._handle_chip_click(c))
            chips_layout.addWidget(btn)

        chips_layout.addStretch(1)
        root_layout.addLayout(chips_layout)

        # 4. Command Input Bar
        input_bar = QHBoxLayout()
        input_bar.setSpacing(8)

        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Type directive (e.g. 'search contact Aryan in whatsapp') or speak freely into mic...")
        self.cmd_input.setFont(QFont("Courier New", 9))
        self.cmd_input.setStyleSheet(
            f"background-color: {HUDColors.PANEL}; color: #ffffff; "
            f"border: 1px solid {HUDColors.BORDER}; border-radius: 4px; padding: 8px;"
        )
        self.cmd_input.returnPressed.connect(self._send_text_directive)
        input_bar.addWidget(self.cmd_input, 1)

        self.send_btn = QPushButton("EXECUTE")
        self.send_btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        self.send_btn.setStyleSheet(
            f"background-color: #0b3d61; color: {HUDColors.CYAN}; "
            "border: 1px solid #146096; border-radius: 4px; padding: 8px 18px;"
        )
        self.send_btn.clicked.connect(self._send_text_directive)
        input_bar.addWidget(self.send_btn)

        self.mic_btn = QPushButton("MIC: ACTIVE (F4)")
        self.mic_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.mic_btn.setStyleSheet(
            f"background-color: #0d3824; color: {HUDColors.GREEN}; "
            "border: 1px solid #186640; border-radius: 4px; padding: 8px 14px;"
        )
        self.mic_btn.clicked.connect(self._toggle_mic)
        input_bar.addWidget(self.mic_btn)

        root_layout.addLayout(input_bar)

    def _check_startup_api_key(self) -> None:
        """Prompt API key dialog on launch so the user can easily paste or review their key."""
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key or key.startswith("your_gemini") or os.getenv("PROMPT_KEY_ON_STARTUP", "1") == "1":
            self.open_api_key_dialog()

    def open_api_key_dialog(self) -> None:
        """Open the futuristic API key configuration modal."""
        current_key = os.getenv("GEMINI_API_KEY", "").strip()
        dlg = ApiKeyDialog(current_key=current_key, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_key = os.getenv("GEMINI_API_KEY", "").strip()
            self.append_log("SYS", f"Neural API Key verified: AIza...{new_key[-4:] if len(new_key) > 6 else '****'}", color=HUDColors.GREEN)
            # Re-initialize voice engine if needed
            if self.voice_thread is None or not self.voice_thread.isRunning():
                self._start_voice_engine()
            else:
                self.append_log("SYS", "Connecting to Gemini Live with updated neural key...", color=HUDColors.CYAN)
                self.voice_thread.stop()
                self._start_voice_engine()

    def _init_telemetry_timer(self) -> None:
        """Start periodic system telemetry sampling."""
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.timeout.connect(self._update_telemetry)
        self._telemetry_timer.start(1000)
        self._update_telemetry()

    def _update_telemetry(self) -> None:
        """Sample host hardware utilization."""
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent
            self.cpu_bar.set_value(cpu, f"{cpu:.1f}%")
            self.ram_bar.set_value(mem, f"{mem:.1f}%")
            self.lat_bar.set_value(12.0, "120ms")
            self.disk_bar.set_value(disk, f"{disk:.1f}%")
        except Exception:
            pass

    def _start_voice_engine(self) -> None:
        """Launch Gemini Live full-duplex voice thread."""
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key or key.startswith("your_gemini"):
            self.status_pill.setText("● NO KEY")
            self.status_pill.setStyleSheet(
                f"background-color: #380b18; color: {HUDColors.RED}; "
                "padding: 5px 12px; border-radius: 12px; border: 1px solid #661828;"
            )
            self.append_log("SYS", "Waiting for Gemini API Key. Click [🔑 API KEY] above to enter your key.", color=HUDColors.AMBER)
            return

        self.append_log("SYS", "Connecting to Gemini Live full-duplex neural engine...", color=HUDColors.CYAN)
        self.voice_thread = VoiceThread(self)
        self.voice_thread.status_signal.connect(self._handle_voice_event)
        self.voice_thread.start()

    def _handle_voice_event(self, event: Dict[str, str]) -> None:
        """Dispatch events from Gemini Live session to GUI."""
        ev_type = event.get("type", "")

        if ev_type == "voice_status":
            status = event.get("status", "")
            if status == "connected":
                self.status_pill.setText("● ONLINE")
                self.status_pill.setStyleSheet(
                    f"background-color: #0b3824; color: {HUDColors.GREEN}; "
                    "padding: 5px 12px; border-radius: 12px; border: 1px solid #186640;"
                )
                self.reactor.set_state("LISTENING")
                self.waveform.set_state("LISTENING")
                self.append_log("SYS", f"Live Session connected! Model: {event.get('model', 'gemini')}", color=HUDColors.GREEN)
            elif status == "connecting":
                self.status_pill.setText("● CONNECTING")
                self.status_pill.setStyleSheet(
                    f"background-color: #0b2238; color: {HUDColors.AMBER}; "
                    "padding: 5px 12px; border-radius: 12px; border: 1px solid #14446b;"
                )
                self.reactor.set_state("THINKING")
                self.waveform.set_state("CONNECTING")
            elif status == "error":
                self.status_pill.setText("● ERROR")
                self.status_pill.setStyleSheet(
                    f"background-color: #380b18; color: {HUDColors.RED}; "
                    "padding: 5px 12px; border-radius: 12px; border: 1px solid #661828;"
                )
                self.append_log("ERR", event.get("message", "Voice error"), color=HUDColors.RED)

        elif ev_type == "mic_amplitude":
            if not self._is_muted and not self.reactor.speaking:
                try:
                    amp = float(event.get("level", 0.0))
                    self.reactor.set_amplitude(amp)
                    self.waveform.set_amplitude(amp)
                except Exception:
                    pass

        elif ev_type == "voice_live_hearing":
            self.reactor.set_state("LISTENING")
            self.reactor.set_amplitude(0.40)
            self.waveform.set_state("LISTENING")
            self.waveform.set_amplitude(0.45)

        elif ev_type == "voice_live_speaking":
            self.reactor.speaking = True
            self.reactor.set_state("SPEAKING")
            self.reactor.set_amplitude(0.65)
            self.waveform.speaking = True
            self.waveform.set_state("SPEAKING")
            self.waveform.set_amplitude(0.70)

        elif ev_type == "voice_turn":
            speaker = event.get("speaker", "assistant")
            text = event.get("text", "")
            self.reactor.speaking = False
            self.reactor.set_state("LISTENING")
            self.waveform.speaking = False
            self.waveform.set_state("LISTENING")
            if speaker == "user":
                self.append_log("YOU", text, color=HUDColors.CYAN)
            else:
                self.append_log("JARVIS", text, color="#ffffff")

        elif ev_type == "tool_step":
            tool_text = event.get("text", "")
            self.reactor.set_state("THINKING")
            self.waveform.set_state("PROCESSING")
            self.append_log("TOOL", f"Executing: {tool_text}", color=HUDColors.AMBER)

    def _handle_chip_click(self, cmd: str) -> None:
        """Handle quick action button press."""
        if cmd == "__clear__":
            self.log_edit.clear()
            return
        elif cmd == "__apikey__":
            self.open_api_key_dialog()
            return
        self.cmd_input.setText(cmd)
        self._send_text_directive()

    def _send_text_directive(self) -> None:
        """Submit text command to brain."""
        text = self.cmd_input.text().strip()
        if not text:
            return
        self.cmd_input.clear()
        self.append_log("YOU", text, color=HUDColors.CYAN)

        # Direct mute/unmute command shortcuts
        low = text.lower()
        if low in ("mute", "mute mic", "mute microphone", "/mute"):
            self._set_muted(True)
            return
        elif low in ("unmute", "unmute mic", "unmute microphone", "/unmute"):
            self._set_muted(False)
            return

        self.reactor.set_state("THINKING")
        self.waveform.set_state("PROCESSING")

        threading.Thread(target=self._process_directive_async, args=(text,), daemon=True).start()

    def _process_directive_async(self, text: str) -> None:
        """Run text command through JarvisBrain in background thread."""
        try:
            from core.brain import JarvisBrain
            brain = JarvisBrain()
            res = brain.think(text)
            reply = res.response or "Directive completed."
            QTimer.singleShot(0, lambda: self._on_directive_result(reply, res.steps))
        except Exception as exc:
            err_msg = f"Failed to execute directive: {exc}"
            QTimer.singleShot(0, lambda: self.append_log("ERR", err_msg, color=HUDColors.RED))

    def _on_directive_result(self, reply: str, steps: List[str]) -> None:
        """Log brain reply on main GUI thread."""
        for step in steps:
            self.append_log("TOOL", step, color=HUDColors.AMBER)
        self.append_log("JARVIS", reply, color="#ffffff")
        self.reactor.set_state("LISTENING")
        self.waveform.set_state("LISTENING")

    def _toggle_mic(self) -> None:
        """Toggle microphone mute."""
        self._set_muted(not self._is_muted)

    def _set_muted(self, muted: bool) -> None:
        """Synchronize microphone mute state across UI and voice engine."""
        self._is_muted = bool(muted)
        self.reactor.muted = self._is_muted
        self.waveform.muted = self._is_muted
        if self.voice_thread:
            self.voice_thread.set_muted(self._is_muted)

        if self._is_muted:
            self.mic_btn.setText("MIC: MUTED (F4)")
            self.mic_btn.setStyleSheet(
                f"background-color: #380b18; color: {HUDColors.RED}; "
                "border: 1px solid #661828; border-radius: 4px; padding: 8px 14px;"
            )
            self.reactor.set_state("MUTED")
            self.waveform.set_state("MUTED")
            self.append_log("SYS", "Microphone MUTED (F4). Audio transmission stopped. JARVIS cannot hear you.", color=HUDColors.RED)
        else:
            self.mic_btn.setText("MIC: ACTIVE (F4)")
            self.mic_btn.setStyleSheet(
                f"background-color: #0d3824; color: {HUDColors.GREEN}; "
                "border: 1px solid #186640; border-radius: 4px; padding: 8px 14px;"
            )
            self.reactor.set_state("LISTENING")
            self.waveform.set_state("LISTENING")
            self.append_log("SYS", "Microphone ACTIVE. Listening to voice...", color=HUDColors.GREEN)

    def keyPressEvent(self, event: Any) -> None:
        """Handle keyboard shortcuts (F4 to toggle mute)."""
        if event.key() == Qt.Key.Key_F4:
            self._toggle_mic()
            event.accept()
        else:
            super().keyPressEvent(event)

    def append_log(self, sender: str, message: str, color: str = "#ffffff") -> None:
        """Format and append entry to interaction stream."""
        now = time.strftime("%H:%M:%S")
        html = f'<span style="color: #406080;">[{now}]</span> <b style="color: {color};">[{sender}]</b>: {message}<br>'
        self.log_edit.append(html)
        self.log_edit.verticalScrollBar().setValue(self.log_edit.verticalScrollBar().maximum())

    def closeEvent(self, event: Any) -> None:
        """Cleanly stop voice threads on window close."""
        if self.voice_thread:
            self.voice_thread.stop()
        event.accept()


def launch_pyqt_hud() -> None:
    """Launch the standalone native PyQt6 HUD application."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    window = JarvisNativeHUD()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch_pyqt_hud()
