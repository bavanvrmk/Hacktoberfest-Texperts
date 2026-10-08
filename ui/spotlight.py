"""
Spotlight UI Module (Member 3 UI/UX Deliverable - Phase 4 Visual Polish)
Transparent, hotkey-activated ('Ctrl + Space') Spotlight HUD with real-time execution telemetry,
quick workflow suggestions chips, and reactive event-bus integration.
"""

import sys
import os
import threading

try:
    from pynput import keyboard as pynput_keyboard
except ImportError:
    pynput_keyboard = None

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLineEdit, QProgressBar, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QFont, QCursor

# Ensure root workspace is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.event_bus import (
    event_bus, 
    EVENT_TASK_START, 
    EVENT_PROGRESS, 
    EVENT_TASK_SUCCESS, 
    EVENT_TASK_FAILED, 
    EVENT_SELF_HEALING
)
from ui.toast import show_toast

class SpotlightSignals(QObject):
    toggle_requested = pyqtSignal()
    progress_updated = pyqtSignal(str, float)
    task_succeeded = pyqtSignal(str, str)
    task_failed = pyqtSignal(str)
    self_healing_triggered = pyqtSignal(str)

class SpotlightUI(QWidget):
    def __init__(self, orchestrator_callback=None, parent=None):
        super().__init__(parent)
        
        self.orchestrator_callback = orchestrator_callback
        self.is_executing = False

        # Window properties
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.collapsed_height = 106
        self.expanded_height = 148
        self.window_width = 640
        
        self._init_ui()
        self._setup_signals()
        self._subscribe_event_bus()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        
        # Central Container Card
        self.card = QWidget(self)
        self.card.setObjectName("SpotlightCard")
        self.card.setStyleSheet("""
            #SpotlightCard {
                background-color: #0b0f19;
                border: 2px solid #38bdf8;
                border-radius: 16px;
            }
        """)
        
        # Neon Drop Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(56, 189, 248, 140))
        shadow.setOffset(0, 4)
        self.card.setGraphicsEffect(shadow)
        
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(16, 12, 16, 14)
        self.card_layout.setSpacing(10)
        
        # Top Row: Icon + Input
        input_row = QHBoxLayout()
        input_row.setSpacing(12)
        
        self.icon_lbl = QLabel("⚡", self.card)
        self.icon_lbl.setStyleSheet("font-size: 22px; color: #38bdf8;")
        input_row.addWidget(self.icon_lbl)
        
        self.search_entry = QLineEdit(self.card)
        self.search_entry.setPlaceholderText("Enter automation workflow or describe UI element to click...")
        self.search_entry.setStyleSheet("""
            QLineEdit {
                background-color: #161f30;
                color: #f8fafc;
                font-size: 14px;
                font-family: 'Segoe UI';
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 7px 14px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
                background-color: #1a2438;
            }
        """)
        self.search_entry.returnPressed.connect(self.on_execute)
        input_row.addWidget(self.search_entry)
        
        self.card_layout.addLayout(input_row)

        # Action Chips / Suggestion Pills
        self.chips_row = QHBoxLayout()
        self.chips_row.setSpacing(8)
        
        suggestions = [
            ("📄 Invoice to CSV", "Extract invoice numbers and log to CSV"),
            ("💾 Save Changes", "Click the Save Changes button"),
            ("🔒 Blur PII & Submit", "Redact sensitive data and submit form")
        ]
        
        for label, cmd in suggestions:
            btn = QPushButton(label, self.card)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(30, 41, 59, 0.7);
                    color: #94a3b8;
                    font-size: 11px;
                    font-family: 'Segoe UI';
                    border: 1px solid rgba(51, 65, 85, 0.6);
                    border-radius: 6px;
                    padding: 3px 8px;
                }
                QPushButton:hover {
                    background-color: rgba(56, 189, 248, 0.15);
                    color: #38bdf8;
                    border: 1px solid #38bdf8;
                }
            """)
            btn.clicked.connect(lambda checked, c=cmd: self._trigger_chip(c))
            self.chips_row.addWidget(btn)
            
        self.chips_row.addStretch()
        self.card_layout.addLayout(self.chips_row)
        
        # Bottom Progress Row (Hidden by default)
        self.progress_container = QWidget(self.card)
        prog_layout = QVBoxLayout(self.progress_container)
        prog_layout.setContentsMargins(0, 2, 0, 0)
        prog_layout.setSpacing(5)
        
        self.status_lbl = QLabel("Ready", self.progress_container)
        self.status_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: 'Segoe UI';")
        prog_layout.addWidget(self.status_lbl)
        
        self.progress_bar = QProgressBar(self.progress_container)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:0.5 #38bdf8, stop:1 #10b981);
                border-radius: 3px;
            }
        """)
        prog_layout.addWidget(self.progress_bar)
        
        self.card_layout.addWidget(self.progress_container)
        self.progress_container.hide()
        
        self.main_layout.addWidget(self.card)
        
        self.resize(self.window_width, self.collapsed_height)
        self._reposition()

    def _trigger_chip(self, cmd_text: str):
        if not self.is_executing:
            self.search_entry.setText(cmd_text)
            self.on_execute()

    def _reposition(self):
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            x = (geom.width() - self.width()) // 2
            y = geom.height() // 4
            self.move(x, y)

    def _setup_signals(self):
        self.signals = SpotlightSignals()
        self.signals.toggle_requested.connect(self.toggle_spotlight)
        self.signals.progress_updated.connect(self._on_progress_update)
        self.signals.task_succeeded.connect(self._on_task_success)
        self.signals.task_failed.connect(self._on_task_failed)
        self.signals.self_healing_triggered.connect(self._on_self_healing)

    def _subscribe_event_bus(self):
        event_bus.subscribe(EVENT_PROGRESS, lambda d: self.signals.progress_updated.emit(d.get("step", ""), float(d.get("progress", 0.0))))
        event_bus.subscribe(EVENT_TASK_SUCCESS, lambda d: self.signals.task_succeeded.emit(d.get("summary", "Task Completed"), d.get("roi_msg", "")))
        event_bus.subscribe(EVENT_TASK_FAILED, lambda d: self.signals.task_failed.emit(d.get("error", "Failed")))
        event_bus.subscribe(EVENT_SELF_HEALING, lambda d: self.signals.self_healing_triggered.emit(d.get("message", "Healing...")))

    def on_execute(self):
        query = self.search_entry.text().strip()
        if not query or self.is_executing:
            return

        self.is_executing = True
        self.search_entry.setEnabled(False)
        
        # Expand UI
        self.progress_container.show()
        self.resize(self.window_width, self.expanded_height)
        self.status_lbl.setText(f"🚀 Initiating: '{query}'...")
        self.status_lbl.setStyleSheet("color: #60a5fa; font-size: 11px;")
        self.progress_bar.setValue(10)
        
        # Dispatch event
        event_bus.emit(EVENT_TASK_START, {"command": query})

        if self.orchestrator_callback:
            threading.Thread(target=self.orchestrator_callback, args=(query,), daemon=True).start()

        self.search_entry.clear()

    def _on_progress_update(self, step_text: str, progress_val: float):
        self.status_lbl.setText(step_text)
        self.progress_bar.setValue(int(progress_val * 100))

    def _on_self_healing(self, msg: str):
        self.status_lbl.setText(f"⚡ {msg}")
        self.status_lbl.setStyleSheet("color: #fbbf24; font-size: 11px; font-weight: bold;")
        show_toast("Self-Healing Active", msg, toast_type="healing", duration=3.0)

    def _on_task_success(self, summary: str, roi_msg: str):
        self.status_lbl.setText(f"✓ {summary}")
        self.status_lbl.setStyleSheet("color: #34d399; font-size: 11px; font-weight: bold;")
        self.progress_bar.setValue(100)
        show_toast("Task Executed", summary, toast_type="success", duration=4.0, badge=roi_msg)
        
        QTimer.singleShot(1800, self._collapse_and_hide)

    def _on_task_failed(self, err_msg: str):
        self.status_lbl.setText(f"✕ Error: {err_msg}")
        self.status_lbl.setStyleSheet("color: #f87171; font-size: 11px;")
        show_toast("Task Failed", err_msg, toast_type="error", duration=4.0)
        
        QTimer.singleShot(2500, self._collapse_and_hide)

    def _collapse_and_hide(self):
        self.progress_container.hide()
        self.resize(self.window_width, self.collapsed_height)
        self.hide()
        self.is_executing = False
        self.search_entry.setEnabled(True)
        self.status_lbl.setText("Ready")
        self.progress_bar.setValue(0)

    def toggle_spotlight(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
            self.search_entry.setFocus()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

def start_hotkey_listener(app_signals: SpotlightSignals):
    """Listens for Ctrl + Space globally and triggers Qt signal safely."""
    if pynput_keyboard:
        try:
            hotkeys = {
                '<ctrl>+<space>': lambda: app_signals.toggle_requested.emit()
            }
            with pynput_keyboard.GlobalHotKeys(hotkeys) as h:
                h.join()
        except Exception as e:
            print(f"[Hotkey Listener Warning] pynput listener: {e}")
    else:
        print("[Hotkey Listener] pynput not installed. Global hotkey disabled.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    spotlight = SpotlightUI()
    spotlight.show()
    
    listener_thread = threading.Thread(target=start_hotkey_listener, args=(spotlight.signals,), daemon=True)
    listener_thread.start()
    
    sys.exit(app.exec_())
