"""
Main Orchestrator Module (Phase 3 System Pipeline Integration)
Unifies Member 1 (Vision Grounding via VisionGrounder & LLMClient), Member 2 (OS Sandbox & Self-Healing),
Member 3 (Spotlight UI, Toast & AR Overlay), and Member 4 (PII Redaction, DB Logger, ROI Dashboard).
"""

import time
import os
import sys
import threading

# Ensure workspace root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.event_bus import (
    event_bus,
    EVENT_TASK_START,
    EVENT_PROGRESS,
    EVENT_OVERLAY_DRAW,
    EVENT_ACTION_EXECUTED,
    EVENT_TASK_SUCCESS,
    EVENT_TASK_FAILED,
    EVENT_SELF_HEALING
)
from core.llm_client import LLMClient
from core.vision_grounding import VisionGrounder
from core.os_sandbox import OSSandbox
from core.windows_launcher import close_app, launch_app, open_file, press_keys, type_text
from core.workflow_manager import WorkflowManager
from src.architecture.database_logger import log_task_start, log_task_end
from src.architecture.pii_redaction import detect_and_blur_pii
from src.architecture.roi_calculator import calculate_financial_roi

class Orchestrator:
    def __init__(self):
        self.llm_client = LLMClient()
        self.grounder = VisionGrounder(client=self.llm_client)
        self.sandbox = OSSandbox()
        self.workflows = WorkflowManager()
        self._lock = threading.Lock()
        
        # Subscribe to task start event
        event_bus.subscribe(EVENT_TASK_START, self._on_task_start_event)

    def _on_task_start_event(self, data):
        command = data.get("command", "")
        if command:
            threading.Thread(target=self.run_pipeline, args=(command,), daemon=True).start()

    def run_pipeline(self, target_description: str):
        """
        Executes the complete 7-step autonomous automation pipeline.
        """
        with self._lock:
            print(f"\n=======================================================")
            print(f">> [Orchestrator] Starting workflow for: '{target_description}'")
            print(f"=======================================================")

            # Step 1: Database Task Initialization (Member 4)
            task_id, start_time = log_task_start(task_name=target_description)
            try:
                workflow_id, steps = self.workflows.save(target_description)
                plan = " → ".join(
                    f"{step['action'].replace('_', ' ')} {step.get('target', '')}".strip()
                    for step in steps
                )
                print(f"[Orchestrator] Workflow #{workflow_id}: {plan}")
                event_bus.emit(EVENT_PROGRESS, {
                    "step": f"Workflow #{workflow_id}: {plan}",
                    "progress": 0.1,
                })
                notes = self.workflows.execute(workflow_id, {
                    "launch_app": launch_app,
                    "open_file": open_file,
                    "close_app": close_app,
                    "type": type_text,
                    "hotkey": press_keys,
                    "click": self.ground_and_click,
                })
                self._finish_task(task_id, start_time, target_description, notes)

            except Exception as e:
                print(f"[ERROR] [Orchestrator] Pipeline error: {e}")
                log_task_end(task_id, start_time, cloud_cost_saved_usd=0.0, notes=f"Failed: {e}")
                event_bus.emit(EVENT_TASK_FAILED, {
                    "error": str(e)
                })

    def ground_and_click(self, description: str):
        """Find one on-screen element and click it. Fails when the model cannot see it."""
        raw_screenshot_path = "logs/raw_screenshot.png"
        self.sandbox.grab_screen(raw_screenshot_path)
        redacted_screenshot_path = "logs/redacted_screenshot.png"
        try:
            detect_and_blur_pii(raw_screenshot_path, redacted_screenshot_path)
        except Exception as exc:
            print(f"[Orchestrator] PII redaction note: {exc}, using raw screenshot.")
            redacted_screenshot_path = raw_screenshot_path

        grounding_data = self.grounder.find_element(redacted_screenshot_path, description)
        if not grounding_data.get("target_found"):
            raise RuntimeError(f"Could not find '{description}' on screen.")

        box = grounding_data["bounding_box"]
        screen_w = self.sandbox.monitor["width"]
        screen_h = self.sandbox.monitor["height"]
        x1 = int(box[0] * screen_w)
        y1 = int(box[1] * screen_h)
        x2 = int(box[2] * screen_w)
        y2 = int(box[3] * screen_h)
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        print(f"[Orchestrator] Element grounded at [{x1}, {y1}, {x2}, {y2}] Center: ({cx}, {cy})")
        event_bus.emit(EVENT_OVERLAY_DRAW, {
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "duration": 2.0, "color": "#38bdf8", "label": description,
        })
        time.sleep(0.4)
        event_bus.emit(EVENT_ACTION_EXECUTED, {"x": cx, "y": cy})
        self.sandbox.safe_move_and_click(cx, cy)
        return f"({cx}, {cy})"

    def _finish_task(self, task_id, start_time, target_description, notes):
        event_bus.emit(EVENT_PROGRESS, {
            "step": "6/6 Calculating ROI metrics & logging...",
            "progress": 0.95
        })
        cloud_saved = 0.01
        exec_duration_ms = log_task_end(
            task_id=task_id,
            start_time=start_time,
            cloud_cost_saved_usd=cloud_saved,
            notes=notes
        )
        roi_stats = calculate_financial_roi(num_requests=1, num_automated_tasks=1)
        roi_badge = f"Saved 3.0m | ${cloud_saved:.2f}"
        print(f"[SUCCESS] [Orchestrator] Workflow completed in {exec_duration_ms} ms. ROI: {roi_badge}")
        event_bus.emit(EVENT_TASK_SUCCESS, {
            "task_id": task_id,
            "summary": f"Completed: '{target_description}' ({exec_duration_ms}ms)",
            "roi_msg": roi_badge,
            "roi_stats": roi_stats
        })

# Global singleton orchestrator
orchestrator = Orchestrator()

if __name__ == "__main__":
    print("Testing Orchestrator end-to-end pipeline with VisionGrounder...")
    orchestrator.run_pipeline("Click the Save Changes button")
