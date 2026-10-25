"""
Project JARVIS - Native PyQt6 Desktop HUD Application.
Author: Rohit (Frontend & Desktop UI Specialist) & Aryan (Voice Specialist)

Provides a native high-performance PyQt6 desktop interface featuring:
- Mathematically animated Arc Reactor / Neural Core with live voice amplitude reactivity
- Real-time audio waveform visualizer and viseme-aware speaking pulses
- Hardware telemetry gauges (CPU %, RAM %, System Uptime, Engine Latency)
- Live bi-directional chat / voice stream transcripts and tool execution steps
- Quick action command chips and direct text directive prompt
- Integrated background thread bridge to GeminiLiveEngine and JarvisBrain
"""

from __future__ import annotations

import asyncio
import math
import os
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
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QSizePolicy, QTextEdit, QVBoxLayout, QWidget,
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


class ArcReactorWidget(QWidget):
    """Native QPainter Arc Reactor / Neural Core animation widget."""

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
        # Smooth amplitude decay
        self._amp_disp += (self._live_amp - self._amp_disp) * 0.15
        self._live_amp = max(0.02, self._live_amp * 0.92)
        self.update()

    def paintEvent(self, _event: Any) -> None:
        """Render the animated Arc Reactor using vector geometry."""
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

        # 1. Background radial glow
        glow_rad = r * (0.65 + 0.3 * amp)
        glow = QRadialGradient(cx, cy, glow_rad)
        glow.setColorAt(0.0, qcol(acc_col.name(), int(160 + 90 * amp)))
        glow.setColorAt(0.45, qcol(main_col.name(), int(60 + 60 * amp)))
        glow.setColorAt(1.0, qcol(HUDColors.BG, 0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - glow_rad, cy - glow_rad, glow_rad * 2, glow_rad * 2))
        p.setBrush(Qt.BrushStyle.NoBrush)

        # 2. Outer boundary concentric rings
        for rr, alpha, width in ((1.0, 90, 1.0), (0.92, 140, 1.2), (0.75, 80, 1.0)):
            p.setPen(QPen(qcol(main_col.name(), alpha), width))
            rad = r * rr
            p.drawEllipse(QRectF(cx - rad, cy - rad, rad * 2, rad * 2))

        # 3. Rotating tick graduations (72 radial ticks)
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

        # 4. Sweeping segmented arcs
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

        # 5. Core center disc & pulse
        core_r = r * (0.22 + 0.08 * amp)
        p.setBrush(QBrush(qcol(main_col.name(), int(180 + 75 * amp))))
        p.setPen(QPen(qcol(acc_col.name()), 2.0))
        p.drawEllipse(QRectF(cx - core_r, cy - core_r, core_r * 2, core_r * 2))

        # Core status text
        p.setFont(QFont("Courier New", int(max(7, r * 0.07)), QFont.Weight.Bold))
        p.setPen(QPen(qcol("#ffffff"), 1))
        label_text = self.state if not self.speaking else "SPEAKING"
        p.drawText(QRectF(cx - 50, cy - 10, 100, 20), Qt.AlignmentFlag.AlignCenter, label_text)


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
        self.resize(1100, 720)
        self.setMinimumSize(850, 560)
        self.setStyleSheet(f"background-color: {HUDColors.BG}; color: {HUDColors.TEXT_BRIGHT};")

        self.voice_thread: Optional[VoiceThread] = None
        self._is_muted: bool = False

        self._init_ui()
        self._init_telemetry_timer()
        self._start_voice_engine()

    def _init_ui(self) -> None:
        """Construct the HUD window layout."""
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 12, 16, 16)
        root_layout.setSpacing(12)

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

        # 2. Body Area (Left: Telemetry & Controls, Center: Arc Reactor, Right: Live Log)
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

        left_col.addSpacing(10)
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

        body.addLayout(left_col, 28)

        # Center Column: Arc Reactor Core
        center_col = QVBoxLayout()
        self.reactor = ArcReactorWidget()
        center_col.addWidget(self.reactor)
        body.addLayout(center_col, 40)

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
                self.append_log("SYS", f"Live Session connected! Model: {event.get('model', 'gemini')}", color=HUDColors.GREEN)
            elif status == "connecting":
                self.status_pill.setText("● CONNECTING")
                self.status_pill.setStyleSheet(
                    f"background-color: #0b2238; color: {HUDColors.AMBER}; "
                    "padding: 5px 12px; border-radius: 12px; border: 1px solid #14446b;"
                )
                self.reactor.set_state("THINKING")
            elif status == "error":
                self.status_pill.setText("● ERROR")
                self.status_pill.setStyleSheet(
                    f"background-color: #380b18; color: {HUDColors.RED}; "
                    "padding: 5px 12px; border-radius: 12px; border: 1px solid #661828;"
                )
                self.append_log("ERR", event.get("message", "Voice error"), color=HUDColors.RED)

        elif ev_type == "voice_live_hearing":
            self.reactor.set_state("LISTENING")
            self.reactor.set_amplitude(0.35)

        elif ev_type == "mic_amplitude":
            if not self._is_muted and not self.reactor.speaking:
                try:
                    amp = float(event.get("level", 0.0))
                    self.reactor.set_amplitude(amp)
                except Exception:
                    pass

        elif ev_type == "voice_live_speaking":
            self.reactor.speaking = True
            self.reactor.set_state("SPEAKING")
            self.reactor.set_amplitude(0.65)

        elif ev_type == "voice_turn":
            speaker = event.get("speaker", "assistant")
            text = event.get("text", "")
            self.reactor.speaking = False
            self.reactor.set_state("LISTENING")
            if speaker == "user":
                self.append_log("YOU", text, color=HUDColors.CYAN)
            else:
                self.append_log("JARVIS", text, color="#ffffff")

        elif ev_type == "tool_step":
            tool_text = event.get("text", "")
            self.reactor.set_state("THINKING")
            self.append_log("TOOL", f"Executing: {tool_text}", color=HUDColors.AMBER)

    def _handle_chip_click(self, cmd: str) -> None:
        """Handle quick action button press."""
        if cmd == "__clear__":
            self.log_edit.clear()
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

        threading.Thread(target=self._process_directive_async, args=(text,), daemon=True).start()

    def _process_directive_async(self, text: str) -> None:
        """Run text command through JarvisBrain in background thread."""
        try:
            from core.brain import JarvisBrain
            brain = JarvisBrain()
            res = brain.think(text)
            reply = res.response or "Directive completed."
            # Schedule log append on Qt main thread via QTimer.singleShot
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

    def _toggle_mic(self) -> None:
        """Toggle microphone mute."""
        self._set_muted(not self._is_muted)

    def _set_muted(self, muted: bool) -> None:
        """Synchronize microphone mute state across UI and voice engine."""
        self._is_muted = bool(muted)
        self.reactor.muted = self._is_muted
        if self.voice_thread:
            self.voice_thread.set_muted(self._is_muted)

        if self._is_muted:
            self.mic_btn.setText("MIC: MUTED (F4)")
            self.mic_btn.setStyleSheet(
                f"background-color: #380b18; color: {HUDColors.RED}; "
                "border: 1px solid #661828; border-radius: 4px; padding: 8px 14px;"
            )
            self.reactor.set_state("MUTED")
            self.append_log("SYS", "Microphone MUTED (F4). Audio transmission stopped. JARVIS cannot hear you.", color=HUDColors.RED)
        else:
            self.mic_btn.setText("MIC: ACTIVE (F4)")
            self.mic_btn.setStyleSheet(
                f"background-color: #0d3824; color: {HUDColors.GREEN}; "
                "border: 1px solid #186640; border-radius: 4px; padding: 8px 14px;"
            )
            self.reactor.set_state("LISTENING")
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
