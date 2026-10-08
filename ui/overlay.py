"""
AR Overlay Module (Member 3 UI/UX Deliverable - Phase 4 Visual Polish)
Transparent canvas drawing engine that renders pulsating glowing bounding boxes,
sci-fi HUD reticles, corner brackets, and ripple click pings over target desktop elements.
"""

import sys
import os
import time
import math
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush, QRadialGradient

# Ensure root workspace is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.event_bus import event_bus, EVENT_OVERLAY_DRAW, EVENT_ACTION_EXECUTED

class OverlaySignals(QObject):
    draw_requested = pyqtSignal(dict)
    ping_requested = pyqtSignal(int, int)

class AROverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Frameless, transparent, always-on-top, click-through overlay
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        
        # Cover the primary screen
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
            
        self.active_boxes = [] # List of {'box': [x1, y1, x2, y2], 'color': str, 'label': str, 'expires': float, ...}
        self.active_pings = [] # List of {'cx': int, 'cy': int, 'created': float, 'duration': float}

        self.signals = OverlaySignals()
        self.signals.draw_requested.connect(self._on_draw_signal)
        self.signals.ping_requested.connect(self._on_ping_signal)
        
        # High refresh rate render loop (60 FPS for smooth animations)
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self._animation_tick)
        self.render_timer.start(16) # ~60 FPS

        self._subscribe_events()

    def _subscribe_events(self):
        """Listen to overlay draw and action execution events from EventBus."""
        event_bus.subscribe(EVENT_OVERLAY_DRAW, lambda data: self.signals.draw_requested.emit(data))
        event_bus.subscribe(EVENT_ACTION_EXECUTED, lambda data: self.signals.ping_requested.emit(data.get("x", 0), data.get("y", 0)))

    def _on_draw_signal(self, data):
        if not data:
            return
        x1 = data.get("x1", 0)
        y1 = data.get("y1", 0)
        x2 = data.get("x2", 0)
        y2 = data.get("y2", 0)
        duration = data.get("duration", 2.8)
        color = data.get("color", "#38bdf8")
        label = data.get("label", "Target UI")

        self.draw_glowing_box(x1, y1, x2, y2, duration, color, label)

    def _on_ping_signal(self, x, y):
        self.trigger_click_ping(x, y)

    def draw_glowing_box(self, x1, y1, x2, y2, duration=2.8, color="#38bdf8", label="Target UI"):
        """Adds a glowing HUD bounding box with corner brackets and breathing glow."""
        self.active_boxes.append({
            "box": (int(x1), int(y1), int(x2), int(y2)),
            "color": color,
            "label": label,
            "expires": time.time() + duration,
            "created": time.time(),
            "duration": duration
        })
        self.update()

    def trigger_click_ping(self, cx: int, cy: int, duration: float = 0.6):
        """Triggers an expanding radar ripple effect at the click coordinate."""
        self.active_pings.append({
            "cx": cx,
            "cy": cy,
            "created": time.time(),
            "duration": duration
        })
        self.update()

    def _animation_tick(self):
        now = time.time()
        initial_box_count = len(self.active_boxes)
        initial_ping_count = len(self.active_pings)
        
        # Cleanup expired items
        self.active_boxes = [b for b in self.active_boxes if b["expires"] > now]
        self.active_pings = [p for p in self.active_pings if (now - p["created"]) < p["duration"]]
        
        # Repaint if items are active or just removed
        if len(self.active_boxes) > 0 or len(self.active_pings) > 0 or initial_box_count > 0 or initial_ping_count > 0:
            self.update()

    def paintEvent(self, event):
        """Paints high-precision glowing AR bounding boxes on transparent canvas."""
        if not self.active_boxes and not self.active_pings:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        now = time.time()

        # 1. Paint Click Pings (Expanding Ripple)
        for p in self.active_pings:
            elapsed = now - p["created"]
            progress = min(1.0, elapsed / p["duration"])
            radius = int(progress * 48)
            alpha = int((1.0 - progress) * 220)
            
            ping_pen = QPen(QColor(56, 189, 248, alpha), 2)
            painter.setPen(ping_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPoint(p["cx"], p["cy"]), radius, radius)
            painter.drawEllipse(QPoint(p["cx"], p["cy"]), max(2, radius // 2), max(2, radius // 2))

        # 2. Paint Glowing Bounding Boxes
        for b in self.active_boxes:
            x1, y1, x2, y2 = b["box"]
            w = max(10, x2 - x1)
            h = max(10, y2 - y1)
            color_hex = b["color"]
            label = b["label"]

            # Sine wave pulsing factor for smooth breathing glow
            elapsed = now - b["created"]
            pulse = 0.85 + 0.15 * math.sin(elapsed * 8.0) # 8 rad/s pulsation
            
            time_left = max(0.0, b["expires"] - now)
            alpha_factor = min(1.0, time_left / 0.4) if time_left < 0.4 else 1.0
            overall_alpha = pulse * alpha_factor

            qcolor = QColor(color_hex)
            
            # --- Tier 1: Soft Neon Bloom Halos ---
            for offset, width, alpha_val in [(10, 5, 25), (6, 4, 60), (3, 2, 130)]:
                halo_color = QColor(qcolor.red(), qcolor.green(), qcolor.blue(), int(alpha_val * overall_alpha))
                pen = QPen(halo_color, width)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(x1 - offset, y1 - offset, w + offset*2, h + offset*2, 8, 8)

            # --- Tier 2: Translucent Tint Fill ---
            fill_color = QColor(qcolor.red(), qcolor.green(), qcolor.blue(), int(20 * overall_alpha))
            painter.setBrush(QBrush(fill_color))
            painter.setPen(QPen(QColor(255, 255, 255, int(180 * overall_alpha)), 1, Qt.DashLine))
            painter.drawRoundedRect(x1, y1, w, h, 6, 6)

            # --- Tier 3: Sci-Fi Corner Reticle Brackets ---
            bracket_len = min(16, min(w, h) // 3)
            bracket_pen = QPen(QColor(255, 255, 255, int(240 * overall_alpha)), 3)
            painter.setPen(bracket_pen)
            
            # Top-Left ⌜
            painter.drawLine(x1, y1, x1 + bracket_len, y1)
            painter.drawLine(x1, y1, x1, y1 + bracket_len)
            # Top-Right ⌝
            painter.drawLine(x2, y1, x2 - bracket_len, y1)
            painter.drawLine(x2, y1, x2, y1 + bracket_len)
            # Bottom-Left ⌞
            painter.drawLine(x1, y2, x1 + bracket_len, y2)
            painter.drawLine(x1, y2, x1, y2 - bracket_len)
            # Bottom-Right ⌟
            painter.drawLine(x2, y2, x2 - bracket_len, y2)
            painter.drawLine(x2, y2, x2, y2 - bracket_len)

            # --- Tier 4: Center Crosshair Target ---
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            ch_pen = QPen(QColor(qcolor.red(), qcolor.green(), qcolor.blue(), int(200 * overall_alpha)), 1)
            painter.setPen(ch_pen)
            painter.drawLine(cx - 5, cy, cx + 5, cy)
            painter.drawLine(cx, cy - 5, cx, cy + 5)

            # --- Tier 5: Floating HUD Badge ---
            if label:
                badge_text = f"🎯 {label}"
                font = QFont("Segoe UI", 9, QFont.Bold)
                painter.setFont(font)
                
                badge_w = len(badge_text) * 8 + 16
                badge_h = 24
                badge_x = x1
                badge_y = max(6, y1 - badge_h - 6)

                # Badge Card
                painter.setPen(QPen(qcolor, 1))
                painter.setBrush(QBrush(QColor(15, 23, 42, int(230 * overall_alpha))))
                painter.drawRoundedRect(badge_x, badge_y, badge_w, badge_h, 5, 5)

                # Badge Label
                painter.setPen(QColor(255, 255, 255, int(255 * overall_alpha)))
                painter.drawText(QRect(badge_x + 8, badge_y + 1, badge_w - 8, badge_h - 2), Qt.AlignLeft | Qt.AlignVCenter, badge_text)

        painter.end()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = AROverlay()
    overlay.show()
    
    # Visual Demonstration
    QTimer.singleShot(800, lambda: overlay.draw_glowing_box(320, 220, 580, 290, duration=3.5, color="#10b981", label="Save Changes Button"))
    QTimer.singleShot(1800, lambda: overlay.trigger_click_ping(450, 255, duration=0.8))
    QTimer.singleShot(2600, lambda: overlay.draw_glowing_box(680, 420, 940, 480, duration=3.0, color="#f59e0b", label="Self-Healing Recovery Box"))
    QTimer.singleShot(6000, app.quit)
    
    sys.exit(app.exec_())
