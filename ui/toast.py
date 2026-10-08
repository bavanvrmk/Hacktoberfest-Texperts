"""
Toast Notification Module (Member 3 UI/UX Deliverable - PyQt5)
Renders sleek, floating dark-mode HUD toast notifications with auto-fade.
"""

import sys
import os
import time
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QFont

class ToastSignals(QObject):
    show_toast = pyqtSignal(str, str, str, float, str)

class ToastWidget(QWidget):
    def __init__(self, title: str, message: str, toast_type: str = "success", duration: float = 3.5, badge: str = None, parent=None):
        super().__init__(parent)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        
        # Color palettes
        palettes = {
            "success": {"border": "#10b981", "bg": "#0f172a", "title": "#34d399", "badge_bg": "#064e3b", "badge_fg": "#6ee7b7", "icon": "✓"},
            "healing": {"border": "#f59e0b", "bg": "#18181b", "title": "#fbbf24", "badge_bg": "#78350f", "badge_fg": "#fde68a", "icon": "⚡"},
            "info":    {"border": "#38bdf8", "bg": "#0f172a", "title": "#60a5fa", "badge_bg": "#1e3a8a", "badge_fg": "#93c5fd", "icon": "ℹ"},
            "error":   {"border": "#ef4444", "bg": "#1c1917", "title": "#f87171", "badge_bg": "#7f1d1d", "badge_fg": "#fca5a5", "icon": "✕"},
        }
        theme = palettes.get(toast_type, palettes["info"])
        
        # Container
        container = QWidget(self)
        container.setObjectName("Container")
        container.setStyleSheet(f"""
            #Container {{
                background-color: {theme['bg']};
                border: 2px solid {theme['border']};
                border-radius: 12px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(theme['border']))
        shadow.setOffset(0, 0)
        container.setGraphicsEffect(shadow)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(container)
        
        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(14, 12, 14, 12)
        inner_layout.setSpacing(6)
        
        # Header Row
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        title_lbl = QLabel(f"{theme['icon']}  {title}", container)
        title_lbl.setStyleSheet(f"color: {theme['title']}; font-weight: bold; font-size: 13px; font-family: 'Segoe UI';")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        
        if badge:
            badge_lbl = QLabel(f" {badge} ", container)
            badge_lbl.setStyleSheet(f"background-color: {theme['badge_bg']}; color: {theme['badge_fg']}; border-radius: 4px; font-weight: bold; font-size: 11px; padding: 2px 6px;")
            header_layout.addWidget(badge_lbl)
            
        inner_layout.addLayout(header_layout)
        
        # Message
        msg_lbl = QLabel(message, container)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #e2e8f0; font-size: 12px; font-family: 'Segoe UI';")
        inner_layout.addWidget(msg_lbl)
        
        # Fixed size & Bottom-Right positioning
        self.resize(360, 100)
        self._reposition()
        
        # Auto-dismiss timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)
        self.timer.start(int(duration * 1000))

    def _reposition(self):
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            x = geom.width() - self.width() - 20
            y = geom.height() - self.height() - 50
            self.move(x, y)

# Helper singleton for thread-safe toast invocations
class ToastManager(QObject):
    _instance = None
    
    def __init__(self):
        super().__init__()
        self.signals = ToastSignals()
        self.signals.show_toast.connect(self._create_toast)
        self._active_toasts = []

    def _create_toast(self, title, message, toast_type, duration, badge):
        toast = ToastWidget(title, message, toast_type, duration, badge)
        toast.show()
        self._active_toasts.append(toast)
        QTimer.singleShot(int((duration + 0.5) * 1000), lambda: self._cleanup(toast))

    def _cleanup(self, toast):
        if toast in self._active_toasts:
            self._active_toasts.remove(toast)

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = ToastManager()
        return cls._instance

def show_toast(title: str, message: str, toast_type: str = "success", duration: float = 3.5, badge: str = None):
    """Global helper to display a toast."""
    app = QApplication.instance()
    if app:
        mgr = ToastManager.instance()
        mgr.signals.show_toast.emit(title, message, toast_type, duration, badge or "")
    else:
        print(f"[{toast_type.upper()}] {title}: {message} {f'({badge})' if badge else ''}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    show_toast("Task Complete", "Successfully automated invoice entry into CSV.", "success", duration=3.0, badge="Saved $12.40")
    QTimer.singleShot(1500, lambda: show_toast("Self-Healing Triggered", "Target UI element moved. Re-cropping ROI...", "healing", duration=3.0))
    QTimer.singleShot(5000, app.quit)
    sys.exit(app.exec_())
