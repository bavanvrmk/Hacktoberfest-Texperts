"""
Demo Showcase Script (Phase 4 Live Video Recording & Verification)
Simulates end-to-end multi-step autonomous workflows with AR overlays,
click animations, self-healing recovery, and real-time ROI tracking for the demo video.
"""

import sys
import os
import time
import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# Ensure workspace root in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.event_bus import event_bus, EVENT_PROGRESS, EVENT_OVERLAY_DRAW, EVENT_ACTION_EXECUTED, EVENT_TASK_SUCCESS, EVENT_SELF_HEALING
from ui.overlay import AROverlay
from ui.toast import ToastManager, show_toast
from src.architecture.database_logger import init_db, log_task_start, log_task_end
from src.architecture.roi_calculator import calculate_financial_roi

def run_automated_showcase():
    """Runs a simulated multi-stage demo showcasing all features for the recording."""
    time.sleep(1.5)
    print("\n=======================================================")
    print("🎬 [Demo Showcase] Starting Live Recording Sequence")
    print("=======================================================")

    init_db()

    # Workflow 1: Invoice Processing & Form Automation
    task_name = "Extract Invoice Data & Save to Tracker"
    task_id, start_time = log_task_start(task_name)
    show_toast("Workflow Initiated", f"Executing: '{task_name}'", "info", duration=2.5)
    
    time.sleep(1.2)
    print(">> Step 1: Grounding Invoice Input Field...")
    event_bus.emit(EVENT_OVERLAY_DRAW, {
        "x1": 340, "y1": 240, "x2": 620, "y2": 290,
        "duration": 2.5, "color": "#38bdf8", "label": "Invoice Number Field"
    })
    
    time.sleep(1.0)
    print(">> Step 2: Executing Smooth Click...")
    event_bus.emit(EVENT_ACTION_EXECUTED, {"x": 480, "y": 265})
    
    time.sleep(1.5)
    print(">> Step 3: Grounding Submit Button...")
    event_bus.emit(EVENT_OVERLAY_DRAW, {
        "x1": 550, "y1": 420, "x2": 720, "y2": 470,
        "duration": 2.5, "color": "#10b981", "label": "Submit & Save Button"
    })
    
    time.sleep(0.8)
    event_bus.emit(EVENT_ACTION_EXECUTED, {"x": 635, "y": 445})

    time.sleep(1.0)
    exec_time = log_task_end(task_id, start_time, cloud_cost_saved_usd=0.01, notes="Demo Step 1 Successful")
    show_toast("Step Complete", "Extracted invoice #INV-2026-889. Saved to CSV.", "success", duration=3.0, badge="Saved $0.01 | 3.0m")

    # Workflow 2: Self-Healing Trigger Demonstration
    time.sleep(3.5)
    print("\n>> Demonstrating Self-Healing Loop: Target Element Moved...")
    heal_task = "Auto-Repair: Recover Moved Export Button"
    h_task_id, h_start = log_task_start(heal_task)
    
    # Original target location (failed click)
    event_bus.emit(EVENT_OVERLAY_DRAW, {
        "x1": 200, "y1": 500, "x2": 380, "y2": 550,
        "duration": 2.0, "color": "#ef4444", "label": "Unresponsive Target (Moved)"
    })
    time.sleep(0.8)
    event_bus.emit(EVENT_ACTION_EXECUTED, {"x": 290, "y": 525})
    
    time.sleep(1.2)
    print(">> UI State Unchanged -> Triggering Self-Healing Loop...")
    event_bus.emit(EVENT_SELF_HEALING, {
        "message": "UI state unresponsive. Re-cropping ROI and recalculating target coordinates..."
    })

    time.sleep(1.5)
    # Self-Healing recovered target location
    event_bus.emit(EVENT_OVERLAY_DRAW, {
        "x1": 750, "y1": 320, "x2": 950, "y2": 375,
        "duration": 3.0, "color": "#f59e0b", "label": "Self-Healing Repaired Element"
    })
    time.sleep(0.9)
    event_bus.emit(EVENT_ACTION_EXECUTED, {"x": 850, "y": 348})
    
    time.sleep(1.2)
    h_exec = log_task_end(h_task_id, h_start, cloud_cost_saved_usd=0.02, notes="Self-Healing Recovery Passed")
    show_toast("Self-Healing Success", "Recovered moved UI element. Workflow completed.", "success", duration=3.5, badge="⚡ Repaired")

    time.sleep(3.5)
    print("\n=======================================================")
    print("🎉 [Demo Showcase] Showcase sequence finished!")
    print("=======================================================")

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    ToastManager()

    overlay = AROverlay()

    def pump_tk():
        try:
            overlay.update()
        except Exception:
            pass

    tk_timer = QTimer()
    tk_timer.timeout.connect(pump_tk)
    tk_timer.start(16)

    # Launch demo in background worker thread
    demo_thread = threading.Thread(target=run_automated_showcase, daemon=True)
    demo_thread.start()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
