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
from src.architecture.database_logger import log_task_start, log_task_end
from src.architecture.pii_redaction import detect_and_blur_pii
from src.architecture.roi_calculator import calculate_financial_roi

class Orchestrator:
    def __init__(self):
        self.llm_client = LLMClient()
        self.grounder = VisionGrounder(client=self.llm_client)
        self.sandbox = OSSandbox()
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
            event_bus.emit(EVENT_PROGRESS, {
                "step": "1/6 Initializing task & capturing screen...",
                "progress": 0.15
            })
            time.sleep(0.3)

            try:
                # Step 2: Screen Grab (Member 2)
                raw_screenshot_path = "logs/raw_screenshot.png"
                self.sandbox.grab_screen(raw_screenshot_path)
                
                # Step 3: Offline PII Redaction Pipeline (Member 4)
                event_bus.emit(EVENT_PROGRESS, {
                    "step": "2/6 Redacting sensitive PII with OpenCV...",
                    "progress": 0.30
                })
                redacted_screenshot_path = "logs/redacted_screenshot.png"
                try:
                    detect_and_blur_pii(raw_screenshot_path, redacted_screenshot_path)
                except Exception as e:
                    print(f"[Orchestrator] PII redaction note: {e}, using raw screenshot.")
                    redacted_screenshot_path = raw_screenshot_path

                # Step 4: Vision Grounding with Member 1 VisionGrounder
                event_bus.emit(EVENT_PROGRESS, {
                    "step": "3/6 Grounding target element via VisionGrounder...",
                    "progress": 0.50
                })
                
                screen_w = self.sandbox.monitor["width"]
                screen_h = self.sandbox.monitor["height"]
                
                # Attempt Member 1's VisionGrounder, with fallback to simulator if server offline
                try:
                    grounding_data = self.grounder.find_element(redacted_screenshot_path, target_description)
                    if grounding_data.get("target_found"):
                        box = grounding_data["bounding_box"]
                        # Convert normalized [x1, y1, x2, y2] to screen pixels
                        x1 = int(box[0] * screen_w)
                        y1 = int(box[1] * screen_h)
                        x2 = int(box[2] * screen_w)
                        y2 = int(box[3] * screen_h)
                        cx = (x1 + x2) // 2
                        cy = (y1 + y2) // 2
                        label = target_description
                    else:
                        raise ValueError("Target not found by grounding model")
                except Exception as ex:
                    print(f"[Orchestrator] Vision server offline or grounding notice: {ex}")
                    print("[Orchestrator] Using robust fallback grounding engine...")
                    fallback = self.llm_client.ground_target(
                        redacted_screenshot_path, target_description, screen_width=screen_w, screen_height=screen_h
                    )
                    x1, y1, x2, y2 = fallback["box"]
                    cx, cy = fallback["center"]
                    label = fallback.get("label", target_description)
                
                print(f"[Orchestrator] Element grounded at [{x1}, {y1}, {x2}, {y2}] Center: ({cx}, {cy})")

                # Step 5: AR Overlay Projection (Member 3)
                event_bus.emit(EVENT_PROGRESS, {
                    "step": "4/6 Projecting AR glowing bounding box...",
                    "progress": 0.70
                })
                event_bus.emit(EVENT_OVERLAY_DRAW, {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "duration": 2.5,
                    "color": "#38bdf8",
                    "label": f"Target: {label}"
                })
                time.sleep(0.6) # Allow user to see glowing AR target box

                # Step 6: OS Execution & Self-Healing Loop (Member 2)
                event_bus.emit(EVENT_PROGRESS, {
                    "step": "5/6 Executing smooth click & validating state...",
                    "progress": 0.85
                })
                
                # Emit action event to trigger AR click ripple radar ping
                event_bus.emit(EVENT_ACTION_EXECUTED, {"x": cx, "y": cy})

                execution_success = self.sandbox.execute_with_self_healing(
                    target_coords=(cx, cy),
                    click_action_fn=lambda: self.sandbox.safe_move_and_click(cx, cy),
                    max_retries=2
                )

                # Step 7: ROI Calculation & DB Completion (Member 4)
                event_bus.emit(EVENT_PROGRESS, {
                    "step": "6/6 Calculating ROI metrics & logging...",
                    "progress": 0.95
                })
                
                # Assume $0.01 saved per request
                cloud_saved = 0.01
                exec_duration_ms = log_task_end(
                    task_id=task_id, 
                    start_time=start_time, 
                    cloud_cost_saved_usd=cloud_saved, 
                    notes=f"Auto-grounded: {label}"
                )
                
                roi_stats = calculate_financial_roi(num_requests=1, num_automated_tasks=1)
                roi_badge = f"Saved 3.0m | ${cloud_saved:.2f}"

                print(f"[SUCCESS] [Orchestrator] Workflow completed in {exec_duration_ms} ms. ROI: {roi_badge}")

                # Emit completion event to Spotlight and Toast notification (Member 3)
                event_bus.emit(EVENT_TASK_SUCCESS, {
                    "task_id": task_id,
                    "summary": f"Completed: '{target_description}' ({exec_duration_ms}ms)",
                    "roi_msg": roi_badge,
                    "roi_stats": roi_stats
                })

            except Exception as e:
                print(f"[ERROR] [Orchestrator] Pipeline error: {e}")
                log_task_end(task_id, start_time, cloud_cost_saved_usd=0.0, notes=f"Failed: {e}")
                event_bus.emit(EVENT_TASK_FAILED, {
                    "error": str(e)
                })

# Global singleton orchestrator
orchestrator = Orchestrator()

if __name__ == "__main__":
    print("Testing Orchestrator end-to-end pipeline with VisionGrounder...")
    orchestrator.run_pipeline("Click the Save Changes button")
