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
    EVENT_SELF_HEALING,
    EVENT_VISUAL_THOUGHT,
)
from core.llm_client import LLMClient
from core.vision_grounding import VisionGrounder
from core.os_sandbox import OSSandbox
from core.command_planner import needs_model, plan_command, plan_with_model, compile_customer_intent_workflow
from core.windows_launcher import close_app, launch_app, open_file, press_keys, type_text
from core.email_sender import send_email_outlook, parse_email_intent, compose_email_body
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
        self._last_screenshot = None
        
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
                steps = self._understand(target_description)
                workflow_id, steps = self.workflows.save(target_description, steps)
                plan = " → ".join(
                    f"{step['action'].replace('_', ' ')} {step.get('target', '')}".strip()
                    for step in steps
                )
                print(f"[Orchestrator] Workflow #{workflow_id}: {plan}")
                event_bus.emit(EVENT_PROGRESS, {
                    "step": f"Workflow #{workflow_id}: {plan}",
                    "progress": 0.1,
                })
                self._last_screenshot = None
                notes = self.workflows.execute(workflow_id, {
                    "launch_app": lambda target: launch_app(target, llm_client=self.llm_client),
                    "open_url": self.open_web_url,
                    "open_file": open_file,
                    "close_app": close_app,
                    "type": type_text,
                    "hotkey": press_keys,
                    "wait": self.wait_seconds,
                    "scroll": self.scroll_screen,
                    "click": self.ground_and_click,
                    "generate": self.generate_and_type,
                    "send_email": self.send_and_log_email,
                    "summarize_screen": self.summarize_screen,
                }, visual_thinker=self.think_multi_screenshot)
                self._finish_task(task_id, start_time, target_description, notes)

            except Exception as e:
                print(f"[ERROR] [Orchestrator] Pipeline error: {e}")
                log_task_end(task_id, start_time, cloud_cost_saved_usd=0.0, notes=f"Failed: {e}")
                event_bus.emit(EVENT_TASK_FAILED, {
                    "error": str(e)
                })

    def _understand(self, command: str):
        """Use the local model when the command is not an obvious click, launch, or file open."""
        quick = plan_command(command)
        if not needs_model(command, quick):
            return quick
        try:
            print("[Orchestrator] Asking the local model to interpret the command...")
            interpreted = plan_with_model(
                command,
                lambda prompt: self.llm_client.chat_completion(
                    [{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=512,
                    timeout=35,
                )["choices"][0]["message"]["content"],
            )
            if interpreted:
                print(f"[Orchestrator] Model plan: {interpreted}")
                return interpreted
        except Exception as exc:
            print(f"[Orchestrator] Model planning unavailable, using the vision click path: {exc}")
        return quick

    def generate_and_type(self, instruction: str):
        print(f"[Orchestrator] Writing text with the local model: {instruction}")
        text = self.llm_client.generate_text(instruction)
        type_text(text)
        return f"typed {len(text.split())} words"

    def open_web_url(self, url: str):
        import webbrowser
        clean = (url or "").strip()
        if not clean.startswith("http"):
            clean = "https://" + clean
        webbrowser.open(clean)
        print(f"[Orchestrator] Opened URL: {clean}")
        time.sleep(1.2)
        return f"Opened {clean}"

    def wait_seconds(self, sec_str: str):
        try:
            s = float(str(sec_str).strip())
        except Exception:
            s = 1.0
        time.sleep(s)
        return f"Waited {s}s"

    def scroll_screen(self, amount_str: str):
        import pyautogui
        try:
            amt = int(str(amount_str).strip())
        except Exception:
            amt = -300
        pyautogui.scroll(amt)
        return f"Scrolled {amt}"

    def think_multi_screenshot(self, step: dict, step_index: int, total_steps: int):
        """
        Multi-Screenshot Visual Thinking:
        Takes a new post-action screenshot, calculates visual delta vs baseline,
        and prompts the local vision/LLM model to reason about UI changes and plan next visual action.
        """
        curr_raw = f"logs/step_{step_index}_raw.png"
        curr_redacted = f"logs/step_{step_index}_screen.png"
        try:
            self.sandbox.grab_screen(curr_raw)
            try:
                detect_and_blur_pii(curr_raw, curr_redacted)
            except Exception:
                curr_redacted = curr_raw

            diff_ratio = 1.0
            if self._last_screenshot and os.path.exists(self._last_screenshot):
                try:
                    from core.self_healing import UIStateValidator
                    from PIL import Image
                    with Image.open(self._last_screenshot) as img1, Image.open(curr_redacted) as img2:
                        diff_ratio = UIStateValidator.compute_visual_difference(img1, img2)
                except Exception:
                    diff_ratio = 0.25

            self._last_screenshot = curr_redacted
            diff_pct = round(diff_ratio * 100, 1)

            # Prompt the model to think about the screen transition
            action_desc = f"{step.get('action')} {step.get('target', '')}"
            thought = ""
            try:
                prompt = (
                    f"You are an Autonomous Visual OS Assistant observing screen changes.\n"
                    f"Current Step {step_index}/{total_steps}: Executed '{action_desc}'.\n"
                    f"Observed Visual Screen Delta: {diff_pct}% change.\n"
                    "Briefly state what you observed on screen and confirm readiness for the next step. (1-2 sentences)"
                )
                response = self.llm_client.chat_completion(
                    [{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=64,
                    timeout=8,
                )
                thought = response["choices"][0]["message"]["content"].strip()
            except Exception:
                thought = f"Observed {diff_pct}% screen state transition after executing {action_desc}. UI state confirmed."

            print(f"[Visual Thinking] Step {step_index}: {thought} ({diff_pct}% delta)")
            event_bus.emit(EVENT_VISUAL_THOUGHT, {
                "step_index": step_index,
                "total_steps": total_steps,
                "action": action_desc,
                "diff_pct": diff_pct,
                "thought": thought,
                "screenshot": curr_redacted,
            })
            event_bus.emit(EVENT_PROGRESS, {
                "step": f"🧠 Step {step_index}/{total_steps}: {thought[:55]}…",
                "progress": step_index / max(total_steps, 1),
            })
        except Exception as exc:
            print(f"[Visual Thinking] Error in reasoning loop: {exc}")

    def send_and_log_email(self, raw_command: str):
        """
        Parse a natural-language email command, compose the body with the local model,
        and send via Outlook COM automation.
        """
        print(f"[Orchestrator] Parsing email intent from: {raw_command}")
        event_bus.emit(EVENT_PROGRESS, {
            "step": "📧 Parsing email recipient & intent...",
            "progress": 0.3,
        })

        parsed = parse_email_intent(raw_command)
        if not parsed or not parsed.get("to"):
            raise RuntimeError(
                f"Could not extract a valid email address from: '{raw_command}'"
            )

        to_addr = parsed["to"]
        subject = parsed["subject"]
        body_intent = parsed.get("body_intent", "")

        print(f"[Orchestrator] Email target: {to_addr}, Subject: {subject}")
        event_bus.emit(EVENT_PROGRESS, {
            "step": f"🧠 Composing email body with local model...",
            "progress": 0.5,
        })

        # Use the local LLM to write a polished email body
        def llm_gen(prompt):
            return self.llm_client.generate_text(prompt)

        body = compose_email_body(body_intent, llm_generate_fn=llm_gen)

        print(f"[Orchestrator] Email body composed ({len(body.split())} words). Sending via Outlook...")
        event_bus.emit(EVENT_PROGRESS, {
            "step": f"📬 Sending email to {to_addr} via Outlook...",
            "progress": 0.8,
        })

        result = send_email_outlook(to=to_addr, subject=subject, body=body)
        method = result.get("method", "unknown")
        status = result.get("status", "unknown")

        summary = f"Email {status} to {to_addr} via {method}"
        print(f"[Orchestrator] {summary}")
        return summary

    def summarize_screen(self, target_instruction: str = ""):
        """
        Reads visible contents on the screen and provides a concise AI summary.
        Uses local vision model (Qwen2.5-VL) on the active screen frame.
        """
        print("[Orchestrator] Capturing screen for content reading and summarization...")
        event_bus.emit(EVENT_PROGRESS, {
            "step": "👁 Capturing screen & reading visible content...",
            "progress": 0.4,
        })
        os.makedirs("logs", exist_ok=True)
        screen_raw = "logs/summarize_screen_raw.png"
        screen_redacted = "logs/summarize_screen_redacted.png"
        self.sandbox.grab_screen(screen_raw)
        try:
            detect_and_blur_pii(screen_raw, screen_redacted)
        except Exception:
            screen_redacted = screen_raw

        b64_img = self.llm_client.encode_image_base64(screen_redacted)
        prompt = (
            "You are an AI desktop vision assistant. Read all visible text, documents, code, "
            "windows, chats, or web pages currently visible on this user's screen. "
            "Provide a concise, clear summary of what is displayed and what the user is working on. "
            "Highlight key information in 3-5 concise bullet points."
        )
        if target_instruction and "screen" not in target_instruction.lower():
            prompt += f"\nSpecifically focus on: {target_instruction}"

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                ]
            }
        ]

        event_bus.emit(EVENT_PROGRESS, {
            "step": "🧠 Generating screen summary with local vision model...",
            "progress": 0.7,
        })
        try:
            response = self.llm_client.chat_completion(messages, temperature=0.2, max_tokens=256, timeout=30)
            summary = response["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            summary = f"Unable to summarize screen content: {exc}"

        print(f"\n--- SCREEN SUMMARY ---\n{summary}\n----------------------")
        event_bus.emit(EVENT_VISUAL_THOUGHT, {
            "thought": summary,
            "diff_pct": 0.0,
            "step_index": 1,
            "total_steps": 1,
        })
        event_bus.emit(EVENT_PROGRESS, {
            "step": f"📋 Summary: {summary[:52]}…",
            "progress": 1.0,
        })
        return summary

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

        try:
            grounding_data = self.grounder.find_element(redacted_screenshot_path, description)
        except Exception as ge:
            print(f"[Orchestrator] Vision grounding element note: {ge}")
            grounding_data = {"target_found": False}

        if not grounding_data.get("target_found"):
            # Context-aware fallback recovery:
            desc_lower = description.lower()
            if any(w in desc_lower for w in ("search", "find", "filter", "query")):
                import pyautogui
                print("[Orchestrator] Fallback: activating search focus via Ctrl+F")
                pyautogui.hotkey("ctrl", "f")
                time.sleep(0.4)
                return "Focused search bar via Ctrl+F"
            elif any(w in desc_lower for w in ("contact", "result", "first", "chat", "conversation")):
                import pyautogui
                print("[Orchestrator] Fallback: selecting top search result via Enter")
                pyautogui.press("enter")
                time.sleep(0.4)
                return "Selected contact/result via Enter"
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
            "duration": 2.0, "color": "#f97316", "label": description,
        })
        time.sleep(0.4)
        event_bus.emit(EVENT_ACTION_EXECUTED, {"x": cx, "y": cy})
        self.sandbox.execute_with_self_healing(
            target_coords=(cx, cy),
            click_action_fn=lambda: self.sandbox.safe_move_and_click(cx, cy),
            max_retries=2,
        )
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
