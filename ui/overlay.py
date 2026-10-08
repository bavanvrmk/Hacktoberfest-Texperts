"""
AR Overlay Module (Member 3 UI/UX Deliverable - PyQt5)
Transparent canvas drawing engine that renders glowing bounding boxes over target UI buttons,
subscribing to EventBus coordinates and running non-blocking overlay animations.
"""

import sys
import os
import time
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush

# Ensure root workspace is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.event_bus import event_bus, EVENT_OVERLAY_DRAW

class OverlaySignals(QObject):
    draw_requested = pyqtSignal(dict)

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
            
        self.active_boxes = [] # List of {'box': [x1, y1, x2, y2], 'color': str, 'label': str, 'expires': float}

        self.signals = OverlaySignals()
        self.signals.draw_requested.connect(self._on_draw_signal)
        
        # Periodic repaint timer for cleaning up expired boxes
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.timeout.connect(self._check_expirations)
        self.cleanup_timer.start(50) # 20 FPS refresh

        self._subscribe_events()

    def _subscribe_events(self):
        """Listen to overlay draw events from the EventBus."""
        event_bus.subscribe(EVENT_OVERLAY_DRAW, lambda data: self.signals.draw_requested.emit(data))

    def _on_draw_signal(self, data):
        if not data:
            return
        x1 = data.get("x1", 0)
        y1 = data.get("y1", 0)
        x2 = data.get("x2", 0)
        y2 = data.get("y2", 0)
        duration = data.get("duration", 2.5)
        color = data.get("color", "#38bdf8")
        label = data.get("label", "Target UI")

        self.draw_glowing_box(x1, y1, x2, y2, duration, color, label)

    def draw_glowing_box(self, x1, y1, x2, y2, duration=2.5, color="#38bdf8", label="Target UI"):
        """Adds a glowing bounding box to the active render queue."""
        self.active_boxes.append({
            "box": (int(x1), int(y1), int(x2), int(y2)),
            "color": color,
            "label": label,
            "expires": time.time() + duration,
            "created": time.time(),
            "duration": duration
        })
        self.update()

    def _check_expirations(self):
        now = time.time()
        initial_count = len(self.active_boxes)
        self.active_boxes = [b for b in self.active_boxes if b["expires"] > now]
        if len(self.active_boxes) > 0 or initial_count > 0:
            self.update()

    def paintEvent(self, event):
        """Paints high-precision glowing AR bounding boxes on transparent canvas."""
        if not self.active_boxes:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        now = time.time()
        for b in self.active_boxes:
            x1, y1, x2, y2 = b["box"]
            w = max(10, x2 - x1)
            h = max(10, y2 - y1)
            color_hex = b["color"]
            label = b["label"]

            # Compute fade out factor
            time_left = max(0.0, b["expires"] - now)
            alpha_factor = min(1.0, time_left / 0.5) if time_left < 0.5 else 1.0

            qcolor = QColor(color_hex)
            
            # 1. Outer Glow (Soft Halo)
            for offset, width, alpha in [(8, 4, 30), (4, 3, 70), (2, 2, 140)]:
                halo_color = QColor(qcolor.red(), qcolor.green(), qcolor.blue(), int(alpha * alpha_factor))
                pen = QPen(halo_color, width)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(x1 - offset, y1 - offset, w + offset*2, h + offset*2, 6, 6)

            # 2. Crisp Core Border
            core_color = QColor(255, 255, 255, int(230 * alpha_factor))
            painter.setPen(QPen(core_color, 2))
            painter.drawRoundedRect(x1, y1, w, h, 4, 4)

            # 3. HUD Target Label Badge
            if label:
                badge_text = f"🎯 {label}"
                font = QFont("Segoe UI", 9, QFont.Bold)
                painter.setFont(font)
                
                # Badge background
                badge_w = len(badge_text) * 8 + 16
                badge_h = 22
                badge_x = x1
                badge_y = max(4, y1 - badge_h - 4)

                painter.setPen(QPen(qcolor, 1))
                painter.setBrush(QBrush(QColor(15, 23, 42, int(220 * alpha_factor))))
                painter.drawRoundedRect(badge_x, badge_y, badge_w, badge_h, 4, 4)

                # Badge text
                painter.setPen(QColor(qcolor.red(), qcolor.green(), qcolor.blue(), int(255 * alpha_factor)))
                painter.drawText(QRect(badge_x + 6, badge_y + 2, badge_w - 6, badge_h - 2), Qt.AlignLeft | Qt.AlignVCenter, badge_text)

        painter.end()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = AROverlay()
    overlay.show()
    
    # Demonstration test
    QTimer.singleShot(1000, lambda: overlay.draw_glowing_box(300, 250, 550, 320, duration=3.0, color="#10b981", label="Save Button"))
    QTimer.singleShot(2500, lambda: overlay.draw_glowing_box(700, 400, 950, 460, duration=3.0, color="#f59e0b", label="Self-Healing Target"))
    QTimer.singleShot(6000, app.quit)
    
    sys.exit(app.exec_())
