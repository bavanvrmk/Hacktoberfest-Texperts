"""
Shadow Automator — Main Entrypoint (Phase 3 Complete Integration)
Integrates Spotlight UI (Member 3), AR Overlay (Member 3), Toast Notifications (Member 3),
Orchestrator (Phase 3 Integration), OS Sandbox (Member 2), Vision Grounding (Member 1),
and Database/ROI Engine (Member 4).
"""

import sys
import os
import threading
import argparse
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# Ensure workspace root in path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.event_bus import event_bus
from core.orchestrator import orchestrator
from ui.spotlight import SpotlightUI, hotkey_listener
from ui.overlay import AROverlay
from ui.toast import ToastManager
from src.architecture.database_logger import init_db

def start_dashboard():
    """Runs FastAPI Live ROI Dashboard server."""
    import uvicorn
    from src.architecture.roi_dashboard import app
    print(">> [Dashboard] Starting Live ROI Telemetry Dashboard on http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

def main():
    parser = argparse.ArgumentParser(description="Shadow Automator - Local Autonomous Desktop Automation")
    parser.add_argument("--dashboard", action="store_true", help="Launch the Live ROI & Compliance Web Dashboard alongside desktop UI")
    args = parser.parse_args()

    print("==================================================================")
    print(">> Shadow Automator -- Autonomous Local AI Desktop Agent")
    print(">> Phase 3: System Pipeline Integration & Self-Healing ACTIVE")
    print("==================================================================")
    
    # 1. Initialize SQLite schema
    init_db()

    # 2. Launch Live ROI Web Dashboard if requested
    if args.dashboard:
        dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
        dashboard_thread.start()

    # 3. Create Qt Application
    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)

    # 4. Initialize Toast Manager singleton
    ToastManager()

    # 5. Initialize Spotlight UI (CustomTkinter) as the root Tk window
    spotlight = SpotlightUI()
    spotlight.show_spotlight()

    # 6. Initialize AR Fullscreen Overlay (Tkinter Toplevel attached to spotlight root)
    overlay = AROverlay(master=spotlight)

    # 6.5 Pump Tkinter events using PyQt5 timer (single root update drives all toplevels)
    def pump_tk():
        try:
            spotlight.update()
        except Exception:
            pass
        
    tk_timer = QTimer()
    tk_timer.timeout.connect(pump_tk)
    tk_timer.start(16)

    # 7. Start Global Hotkey Listener (Ctrl + Space)
    hotkey_thread = threading.Thread(target=hotkey_listener, args=(spotlight,), daemon=True)
    hotkey_thread.start()

    print(">> [Hotkeys] Press [Ctrl + Space] anywhere on desktop to toggle Spotlight.")
    print(">> [Hotkeys] Press [Esc] to dismiss Spotlight.")
    print(">> [Ready] Listening for automation workflows...")
    print("==================================================================")

    # Run PyQt5 Event Loop
    sys.exit(qt_app.exec_())

if __name__ == "__main__":
    main()
