"""
ui/toast.py — Phase 3 Premium Toast Notification System (PyQt5)
Renders HUD-style floating toasts with drop shadow, color-coded borders,
animated fade-in/out, stacking, and a live ROI badge.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel,
    QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QFont

# ─── Color Palette ────────────────────────────────────────────────
PALETTES = {
    "success": {
        "border":   "#10b981",
        "bg":       "#121215",
        "title":    "#34d399",
        "badge_bg": "#064e3b",
        "badge_fg": "#6ee7b7",
        "icon":     "✓",
    },
    "healing": {
        "border":   "#f97316",
        "bg":       "#121215",
        "title":    "#fb923c",
        "badge_bg": "#431407",
        "badge_fg": "#fed7aa",
        "icon":     "⚡",
    },
    "info": {
        "border":   "#f97316",
        "bg":       "#121215",
        "title":    "#fb923c",
        "badge_bg": "#431407",
        "badge_fg": "#fed7aa",
        "icon":     "⚡",
    },
    "error": {
        "border":   "#ef4444",
        "bg":       "#121215",
        "title":    "#f87171",
        "badge_bg": "#450a0a",
        "badge_fg": "#fca5a5",
        "icon":     "✕",
    },
}

TOAST_W = 390
TOAST_H = 112
TOAST_GAP = 14
TOAST_MARGIN_X = 22
TOAST_MARGIN_BOTTOM = 55


# ─── Toast Widget ─────────────────────────────────────────────────
class ToastWidget(QWidget):
    closed = pyqtSignal(object)

    def __init__(self, title: str, message: str,
                 toast_type: str = "success",
                 duration: float = 4.0,
                 badge: str = None,
                 slot_y: int = 0,
                 parent=None):
        super().__init__(parent)

        theme = PALETTES.get(toast_type, PALETTES["info"])

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(TOAST_W, TOAST_H)

        # Position bottom-right, stacked
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - TOAST_W - TOAST_MARGIN_X
        y = screen.height() - TOAST_MARGIN_BOTTOM - TOAST_H - slot_y
        self.move(x, y)

        # ── Card ──────────────────────────────────────────────────
        card = QWidget(self)
        card.setObjectName("card")
        card.setFixedSize(TOAST_W, TOAST_H)
        card.setStyleSheet(f"""
            #card {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {theme['bg']},
                    stop:1 #18181b
                );
                border: 1.5px solid {theme['border']};
                border-radius: 14px;
            }}
        """)

        # Drop shadow (glow effect)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(theme["border"]))
        shadow.setOffset(0, 0)
        card.setGraphicsEffect(shadow)

        # ── Layout ────────────────────────────────────────────────
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 10)
        layout.setSpacing(5)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(8)

        icon = QLabel(f"{theme['icon']}")
        icon.setFont(QFont("Segoe UI Emoji", 16))
        icon.setStyleSheet(f"color: {theme['title']}; background: transparent;")
        header.addWidget(icon)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {theme['title']}; background: transparent;")
        header.addWidget(title_lbl)
        header.addStretch()

        if badge:
            badge_lbl = QLabel(f"  {badge}  ")
            badge_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
            badge_lbl.setStyleSheet(f"""
                background: {theme['badge_bg']};
                color: {theme['badge_fg']};
                border-radius: 6px;
                padding: 2px 6px;
            """)
            header.addWidget(badge_lbl)

        layout.addLayout(header)

        # Message
        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont("Segoe UI", 11))
        msg_lbl.setStyleSheet("color: #d4d4d8; background: transparent;")
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)

        # Slim progress timer bar
        self.timer_bar = QProgressBar()
        self.timer_bar.setRange(0, 100)
        self.timer_bar.setValue(100)
        self.timer_bar.setTextVisible(False)
        self.timer_bar.setFixedHeight(3)
        self.timer_bar.setStyleSheet(f"""
            QProgressBar {{
                background: #27272a;
                border-radius: 2px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: {theme['border']};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.timer_bar)

        # ── Fade-in animation ─────────────────────────────────────
        self.setWindowOpacity(0.0)
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(280)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.show()
        self._anim.start()

        # ── Timer bar countdown ───────────────────────────────────
        self._ticks = 0
        self._max_ticks = int(duration * 20)
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(50)

        # ── Auto dismiss ──────────────────────────────────────────
        QTimer.singleShot(int(duration * 1000), self._fade_out)

    def _tick(self):
        self._ticks += 1
        val = max(0, 100 - int(self._ticks / self._max_ticks * 100))
        self.timer_bar.setValue(val)

    def _fade_out(self):
        self._tick_timer.stop()
        self._anim2 = QPropertyAnimation(self, b"windowOpacity")
        self._anim2.setDuration(350)
        self._anim2.setStartValue(1.0)
        self._anim2.setEndValue(0.0)
        self._anim2.setEasingCurve(QEasingCurve.InCubic)
        self._anim2.finished.connect(self._on_closed)
        self._anim2.start()

    def _on_closed(self):
        self.closed.emit(self)
        self.close()


# ─── Toast Manager (stacking) ─────────────────────────────────────
class ToastManager(QObject):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        super(ToastManager, self).__init__()
        self._queue: list[ToastWidget] = []

    def show(self, title, message, toast_type="success", duration=4.0, badge=None):
        slot = len(self._queue) * (TOAST_H + TOAST_GAP)
        t = ToastWidget(title, message, toast_type, duration, badge, slot_y=slot)
        t.closed.connect(self._remove)
        self._queue.append(t)

    def _remove(self, toast):
        if toast in self._queue:
            self._queue.remove(toast)
        # Restack remaining toasts
        for i, t in enumerate(self._queue):
            screen = QApplication.primaryScreen().geometry()
            x = screen.width() - TOAST_W - TOAST_MARGIN_X
            y = screen.height() - TOAST_MARGIN_BOTTOM - TOAST_H - i * (TOAST_H + TOAST_GAP)
            t.move(x, y)


# ─── Public helpers ───────────────────────────────────────────────
_manager: ToastManager = None

def _get_manager():
    global _manager
    if _manager is None:
        _manager = ToastManager()
    return _manager

def show_toast(title, message, toast_type="success", duration=4.0, badge=None):
    """Thread-safe public API — call from anywhere."""
    app = QApplication.instance()
    if app:
        _get_manager().show(title, message, toast_type, duration, badge)
    else:
        print(f"[{toast_type.upper()}] {title}: {message}")


# ─── Demo ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)

    show_toast(
        "Task Complete",
        "Automated invoice entry into ERP successfully.",
        "success", duration=5.0, badge="Saved $12.40"
    )
    QTimer.singleShot(1200, lambda: show_toast(
        "Self-Healing Triggered",
        "Submit button moved. Re-grounding via VisionModel…",
        "healing", duration=5.0
    ))
    QTimer.singleShot(2400, lambda: show_toast(
        "Connecting Pipeline",
        "Spotlight → Orchestrator → OSSandbox event bus active.",
        "info", duration=5.0
    ))
    QTimer.singleShot(8000, app.quit)
    sys.exit(app.exec_())
