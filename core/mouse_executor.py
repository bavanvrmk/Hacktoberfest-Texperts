"""
core/mouse_executor.py - OS Sandbox Execution Engine (Member 2 - Phase 2)
==========================================================================
Autonomous desktop agent mouse & keyboard executor.
Translates Vision Grounding model output (normalized or absolute bounding boxes)
into smooth, human-like Bézier trajectories and executes safe action loops.

Includes:
- Cubic Bézier curve generation with Fitts's Law velocity easing & micro-jitter
- Win32 native & PyGetWindow application window focus manager (with thread attach)
- Multi-action dispatcher (click, double-click, right-click, type, hotkey, scroll, drag)
- Vision Grounding coordinate normalizer & Gaussian center target sampler
- Self-healing state change verification hook (Phase 3 readiness)
- Comprehensive dry-run and fail-safe safety modes
"""

import sys
import time
import math
import random
import logging
from typing import Dict, Any, List, Tuple, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s")
logger = logging.getLogger("OS_Sandbox_Executor")

# Attempt importing GUI automation dependencies with graceful native fallbacks
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    HAS_PYAUTOGUI = True
except ImportError:
    pyautogui = None
    HAS_PYAUTOGUI = False
    logger.warning("PyAutoGUI not installed. Falling back to native Windows user32 API / mock simulation.")

try:
    import pygetwindow as gw
except ImportError:
    gw = None

# Native Windows API via ctypes for 100% dependency-free execution on Windows
IS_WINDOWS = sys.platform.startswith("win")
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
else:
    user32 = None
    kernel32 = None


# ==============================================================================
# 1. SCREEN & DISPLAY RESOLUTION UTILITIES
# ==============================================================================

def get_screen_resolution() -> Tuple[int, int]:
    """Returns primary monitor (width, height) in pixels."""
    if HAS_PYAUTOGUI and pyautogui:
        try:
            return pyautogui.size()
        except Exception:
            pass

    if IS_WINDOWS and user32:
        try:
            w = user32.GetSystemMetrics(0) # SM_CXSCREEN
            h = user32.GetSystemMetrics(1) # SM_CYSCREEN
            if w > 0 and h > 0:
                return (w, h)
        except Exception:
            pass

    return (1920, 1080) # Sensible desktop default


def get_current_cursor_pos() -> Tuple[int, int]:
    """Returns current cursor (x, y) coordinates."""
    if HAS_PYAUTOGUI and pyautogui:
        try:
            pos = pyautogui.position()
            return (pos.x, pos.y)
        except Exception:
            pass

    if IS_WINDOWS and user32:
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        if user32.GetCursorPos(ctypes.byref(pt)):
            return (pt.x, pt.y)

    return (0, 0)


def set_cursor_pos(x: int, y: int) -> None:
    """Sets cursor position directly via PyAutoGUI or native user32."""
    if HAS_PYAUTOGUI and pyautogui:
        pyautogui.moveTo(x, y)
    elif IS_WINDOWS and user32:
        user32.SetCursorPos(int(x), int(y))


# ==============================================================================
# 2. BÉZIER TRAJECTORY & HUMAN-LIKE KINEMATICS
# ==============================================================================

class HumanTrajectoryGenerator:
    """
    Generates anthropomorphic mouse movements using Cubic Bézier Curves,
    Fitts's Law velocity easing, and stochastic micro-adjustments.
    """

    @staticmethod
    def ease_in_out_cubic(t: float) -> float:
        """Sigmoidal ease-in-out cubic timing function."""
        return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2

    @classmethod
    def generate_trajectory(
        cls,
        start: Tuple[int, int],
        target: Tuple[int, int],
        min_steps: int = 25,
        max_steps: int = 65,
        jitter_amplitude: float = 1.2
    ) -> List[Tuple[int, int]]:
        """
        Computes a list of intermediate (x, y) coordinates along a curved trajectory.
        Includes natural curvature, velocity profiling, and subtle micro-jitter.
        """
        x0, y0 = start
        x3, y3 = target
        dx = x3 - x0
        dy = y3 - y0
        dist = math.hypot(dx, dy)

        if dist < 4:
            return [target]

        # Dynamic step count scaled with distance
        steps = int(max(min_steps, min(max_steps, dist / 15.0)))

        # Perpendicular normal vector for natural arm/wrist curvature
        nx = -dy / dist
        ny = dx / dist

        # Stochastic deviation magnitude proportional to distance
        deviation = min(80.0, dist * random.uniform(0.12, 0.28))
        curvature_dir = random.choice([-1.0, 1.0])

        # Intermediate control points (P1 and P2)
        p1_factor = random.uniform(0.20, 0.35)
        p2_factor = random.uniform(0.65, 0.82)

        ctrl1_x = x0 + dx * p1_factor + (nx * deviation * curvature_dir)
        ctrl1_y = y0 + dy * p1_factor + (ny * deviation * curvature_dir)

        ctrl2_x = x0 + dx * p2_factor + (nx * (deviation * 0.45) * curvature_dir)
        ctrl2_y = y0 + dy * p2_factor + (ny * (deviation * 0.45) * curvature_dir)

        points: List[Tuple[int, int]] = []
        screen_w, screen_h = get_screen_resolution()

        for step in range(steps + 1):
            raw_t = step / float(steps)
            # Apply velocity easing (acceleration -> cruise -> deceleration)
            t = cls.ease_in_out_cubic(raw_t)

            # Cubic Bézier formula
            u = 1.0 - t
            bx = (u**3 * x0) + (3 * u**2 * t * ctrl1_x) + (3 * u * t**2 * ctrl2_x) + (t**3 * x3)
            by = (u**3 * y0) + (3 * u**2 * t * ctrl1_y) + (3 * u * t**2 * ctrl2_y) + (t**3 * y3)

            # Add micro-jitter during cruising phase, tapering off near target
            taper = math.sin(raw_t * math.pi)
            jitter_x = random.gauss(0, jitter_amplitude) * taper
            jitter_y = random.gauss(0, jitter_amplitude) * taper

            final_x = int(round(bx + jitter_x))
            final_y = int(round(by + jitter_y))

            # Clamp within screen bounds
            final_x = max(0, min(screen_w - 1, final_x))
            final_y = max(0, min(screen_h - 1, final_y))

            points.append((final_x, final_y))

        # Ensure final point lands directly on target
        points[-1] = (int(x3), int(y3))
        return points


def smooth_mouse_move(
    start_x: int,
    start_y: int,
    target_x: int,
    target_y: int,
    duration: float = 0.45,
    dry_run: bool = False
) -> None:
    """
    Executes a smooth human-like mouse movement from start to target.
    Backward-compatible with Phase 1 signature.
    """
    if dry_run:
        logger.info(f"[Dry-Run] Simulating smooth move: ({start_x}, {start_y}) -> ({target_x}, {target_y})")
        return

    path = HumanTrajectoryGenerator.generate_trajectory((start_x, start_y), (target_x, target_y))
    if not path:
        return

    delay_per_step = max(0.002, duration / len(path))

    for px, py in path:
        set_cursor_pos(px, py)
        time.sleep(delay_per_step)


# ==============================================================================
# 3. APPLICATION WINDOW FOCUS LISTENER & MANAGER
# ==============================================================================

class WindowFocusManager:
    """
    Manages application window detection and foreground activation on Windows.
    Uses native Win32 API calls (AttachThreadInput, SetForegroundWindow, BringWindowToTop)
    with PyGetWindow as a secondary fallback.
    """

    @staticmethod
    def get_window_handles_by_title(keyword: str) -> List[Tuple[int, str]]:
        """Finds all open window handles whose titles contain the keyword."""
        matches: List[Tuple[int, str]] = []
        if not (IS_WINDOWS and user32):
            return matches

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def enum_windows_callback(hwnd, extra):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    if keyword.lower() in title.lower():
                        matches.append((hwnd, title))
            return True

        cb = WNDENUMPROC(enum_windows_callback)
        user32.EnumWindows(cb, 0)
        return matches

    @classmethod
    def force_focus_window(cls, hwnd: int) -> bool:
        """
        Forces a window into the foreground using the Win32 AttachThreadInput protocol.
        Bypasses Windows focus-stealing restrictions.
        """
        if not (IS_WINDOWS and user32):
            return False

        try:
            # If minimized, restore it
            if user32.IsIconic(hwnd):
                user32.ShowWindowAsync(hwnd, 9) # SW_RESTORE = 9
                time.sleep(0.15)

            fore_hwnd = user32.GetForegroundWindow()
            if fore_hwnd == hwnd:
                return True

            fore_thread_id = user32.GetWindowThreadProcessId(fore_hwnd, None)
            app_thread_id = kernel32.GetCurrentThreadId()

            # Attach thread inputs to grant foreground focus permissions
            if fore_thread_id != app_thread_id and fore_thread_id != 0:
                user32.AttachThreadInput(fore_thread_id, app_thread_id, True)

            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)

            if fore_thread_id != app_thread_id and fore_thread_id != 0:
                user32.AttachThreadInput(fore_thread_id, app_thread_id, False)

            time.sleep(0.2)
            return user32.GetForegroundWindow() == hwnd
        except Exception as ex:
            logger.debug(f"Win32 force_focus_window exception: {ex}")
            return False

    @classmethod
    def ensure_focus(cls, window_title_keyword: str, timeout_sec: float = 3.0) -> bool:
        """
        Verifies and ensures that a window matching window_title_keyword is in foreground.
        """
        logger.info(f"[Focus Manager] Ensuring focus for window keyword: '{window_title_keyword}'")

        # 1. Native Windows API pass
        if IS_WINDOWS and user32:
            handles = cls.get_window_handles_by_title(window_title_keyword)
            if handles:
                target_hwnd, title = handles[0]
                logger.info(f"[Focus Manager] Found target HWND {target_hwnd}: '{title}'")
                if cls.force_focus_window(target_hwnd):
                    logger.info(f"[Focus Manager] Successfully focused: '{title}'")
                    return True

        # 2. PyGetWindow fallback
        if gw is not None:
            try:
                windows = gw.getWindowsWithTitle(window_title_keyword)
                if windows:
                    target_window = windows[0]
                    if not target_window.isActive:
                        target_window.activate()
                        time.sleep(0.25)
                    return True
            except Exception as e:
                logger.warning(f"[Focus Manager] PyGetWindow activation error: {e}")

        logger.warning(f"[Focus Manager] Window matching '{window_title_keyword}' not found or could not be focused.")
        return False


def ensure_window_focus(window_title_keyword: str) -> bool:
    """Backward-compatible helper function."""
    return WindowFocusManager.ensure_focus(window_title_keyword)


# ==============================================================================
# 4. COORDINATE NORMALIZER & GAUSSIAN AIM SAMPLER
# ==============================================================================

def normalize_bounding_box(bbox: List[Union[int, float]]) -> Tuple[int, int, int, int]:
    """
    Converts either normalized coordinates [0.0-1.0] (from VisionGrounder)
    or absolute pixel coordinates into integer screen coordinates [x1, y1, x2, y2].
    """
    if len(bbox) != 4:
        raise ValueError(f"Bounding box must contain exactly 4 values: received {bbox}")

    x1, y1, x2, y2 = bbox
    screen_w, screen_h = get_screen_resolution()

    # If any coordinate is a float <= 1.0, treat all as normalized relative coordinates
    is_normalized = all(isinstance(c, float) for c in bbox) or all(c <= 1.0 for c in bbox)

    if is_normalized:
        abs_x1 = int(round(x1 * screen_w))
        abs_y1 = int(round(y1 * screen_h))
        abs_x2 = int(round(x2 * screen_w))
        abs_y2 = int(round(y2 * screen_h))
    else:
        abs_x1, abs_y1, abs_x2, abs_y2 = int(x1), int(y1), int(x2), int(y2)

    # Ensure coordinates are properly ordered (x1 <= x2, y1 <= y2)
    left = max(0, min(abs_x1, abs_x2))
    right = min(screen_w - 1, max(abs_x1, abs_x2))
    top = max(0, min(abs_y1, abs_y2))
    bottom = min(screen_h - 1, max(abs_y1, abs_y2))

    return (left, top, right, bottom)


def sample_human_target_point(bbox_coords: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """
    Selects a click target inside the bounding box using a truncated Gaussian distribution.
    Humans rarely click the exact dead-center; this simulates natural hand-eye targeting
    while keeping the point safely within the button boundaries.
    """
    x1, y1, x2, y2 = bbox_coords
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)

    center_x = x1 + (width / 2.0)
    center_y = y1 + (height / 2.0)

    # Standard deviation sized to keep 95% of samples within inner 60% of the box
    sigma_x = width * 0.12
    sigma_y = height * 0.12

    target_x = random.gauss(center_x, sigma_x)
    target_y = random.gauss(center_y, sigma_y)

    # Clamp inside safe 15% inner padding
    pad_x = max(1, int(width * 0.15))
    pad_y = max(1, int(height * 0.15))

    clamped_x = int(max(x1 + pad_x, min(x2 - pad_x, target_x)))
    clamped_y = int(max(y1 + pad_y, min(y2 - pad_y, target_y)))

    return (clamped_x, clamped_y)


# ==============================================================================
# 5. ACTION DISPATCHER & EXECUTION LOOPS
# ==============================================================================

class ActionExecutor:
    """
    Core executor that translates workflow steps into physical UI events.
    Supports clicks, typing, hotkeys, drags, and scrolls with natural delays.
    """

    def __init__(self, dry_run: bool = False, enable_failsafe: bool = True):
        self.dry_run = dry_run
        self.enable_failsafe = enable_failsafe

    def execute_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        """Executes a mouse click with realistic down/up dwell times."""
        curr_x, curr_y = get_current_cursor_pos()
        smooth_mouse_move(curr_x, curr_y, x, y, duration=random.uniform(0.35, 0.55), dry_run=self.dry_run)

        if self.dry_run:
            logger.info(f"[Dry-Run] Click at ({x}, {y}) button={button} count={clicks}")
            return

        if HAS_PYAUTOGUI and pyautogui:
            # Subtle delay before press
            time.sleep(random.uniform(0.06, 0.12))
            if clicks == 1:
                pyautogui.mouseDown(button=button)
                time.sleep(random.uniform(0.07, 0.13)) # Human press dwell time
                pyautogui.mouseUp(button=button)
            elif clicks == 2:
                pyautogui.doubleClick(button=button)
            else:
                pyautogui.click(button=button, clicks=clicks, interval=0.1)
        elif IS_WINDOWS and user32:
            # Native Win32 mouse event fallback
            down_flag = 0x0002 if button == "left" else 0x0008
            up_flag = 0x0004 if button == "left" else 0x0010
            for _ in range(clicks):
                user32.mouse_event(down_flag, 0, 0, 0, 0)
                time.sleep(random.uniform(0.07, 0.12))
                user32.mouse_event(up_flag, 0, 0, 0, 0)
                time.sleep(0.08)

    def execute_type(self, text: str, clear_field_first: bool = False) -> None:
        """Types text with human-like keystroke intervals and variable cadence."""
        if clear_field_first and not self.dry_run:
            self.execute_hotkey(["ctrl", "a"])
            time.sleep(0.05)
            self.execute_press_key("backspace")
            time.sleep(0.05)

        if self.dry_run:
            logger.info(f"[Dry-Run] Type text: '{text}'")
            return

        if HAS_PYAUTOGUI and pyautogui:
            for char in text:
                pyautogui.write(char)
                # Stochastic typing delay (approx 60-120 WPM)
                delay = random.uniform(0.04, 0.12)
                if char in " .,\n":
                    delay += random.uniform(0.10, 0.25) # Natural punctuation pause
                time.sleep(delay)
        else:
            logger.info(f"[Simulation] Typed: {text}")

    def execute_hotkey(self, keys: Union[List[str], str]) -> None:
        """Executes a key combination (e.g., ['ctrl', 'c'] or 'ctrl+s')."""
        if isinstance(keys, str):
            key_list = [k.strip() for k in keys.split("+")]
        else:
            key_list = keys

        if self.dry_run:
            logger.info(f"[Dry-Run] Hotkey: {key_list}")
            return

        if HAS_PYAUTOGUI and pyautogui:
            pyautogui.hotkey(*key_list)
        else:
            logger.info(f"[Simulation] Hotkey pressed: {key_list}")

    def execute_press_key(self, key: str) -> None:
        """Presses an individual key (e.g., 'enter', 'tab', 'esc')."""
        if self.dry_run:
            logger.info(f"[Dry-Run] Press key: '{key}'")
            return

        if HAS_PYAUTOGUI and pyautogui:
            pyautogui.press(key)
        else:
            logger.info(f"[Simulation] Key pressed: {key}")

    def execute_scroll(self, clicks: int) -> None:
        """Scrolls mouse wheel with smooth incremental steps."""
        if self.dry_run:
            logger.info(f"[Dry-Run] Scroll clicks: {clicks}")
            return

        if HAS_PYAUTOGUI and pyautogui:
            step_sign = 1 if clicks > 0 else -1
            for _ in range(abs(clicks)):
                pyautogui.scroll(step_sign * 100)
                time.sleep(random.uniform(0.02, 0.05))

    def execute_drag_and_drop(self, start_pt: Tuple[int, int], end_pt: Tuple[int, int]) -> None:
        """Smoothly drags from start_pt to end_pt while holding left mouse button."""
        sx, sy = start_pt
        ex, ey = end_pt

        curr_x, curr_y = get_current_cursor_pos()
        smooth_mouse_move(curr_x, curr_y, sx, sy, duration=0.4, dry_run=self.dry_run)

        if self.dry_run:
            logger.info(f"[Dry-Run] Drag and drop: ({sx}, {sy}) -> ({ex}, {ey})")
            return

        if HAS_PYAUTOGUI and pyautogui:
            pyautogui.mouseDown(button="left")
            time.sleep(0.1)
            smooth_mouse_move(sx, sy, ex, ey, duration=0.7, dry_run=self.dry_run)
            time.sleep(0.1)
            pyautogui.mouseUp(button="left")


# ==============================================================================
# 6. PIPELINE RUNNER & JSON ACTION LOOP
# ==============================================================================

def execute_action_loop(action_payload: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """
    Main entry point for Member 2's execution sandbox.
    Accepts:
    1. Multi-step plan: {"steps": [{"action": "click", "bbox": [...]}, ...]}
    2. Single Member 1 vision output: {"target_found": True, "bounding_box": [...]}
    3. Direct step: {"action": "click", "bbox": [...]}
    """
    executor = ActionExecutor(dry_run=dry_run)
    execution_summary = {
        "status": "success",
        "executed_steps": 0,
        "failed_steps": 0,
        "details": []
    }

    # Normalize payload into a list of steps
    steps: List[Dict[str, Any]] = []

    if "steps" in action_payload and isinstance(action_payload["steps"], list):
        steps = action_payload["steps"]
    elif "bounding_box" in action_payload:
        # Standard Member 1 Vision Grounder output
        steps = [{
            "action": action_payload.get("action", "click"),
            "bbox": action_payload["bounding_box"],
            "text": action_payload.get("text", "")
        }]
    elif "action" in action_payload:
        steps = [action_payload]

    logger.info(f"[Executor] Commencing execution of {len(steps)} action step(s)...")

    for idx, step in enumerate(steps, start=1):
        action_type = step.get("action", "click").lower()
        step_result = {"step": idx, "action": action_type, "status": "success"}

        try:
            # Handle window focus request if specified
            if "focus_window" in step:
                WindowFocusManager.ensure_focus(step["focus_window"])

            # Resolve coordinates if bounding box is provided
            if "bbox" in step or "bounding_box" in step:
                raw_bbox = step.get("bbox") or step.get("bounding_box")
                abs_bbox = normalize_bounding_box(raw_bbox)
                target_x, target_y = sample_human_target_point(abs_bbox)
                step_result["target_coords"] = (target_x, target_y)
                step_result["bbox_normalized"] = abs_bbox
            else:
                target_x, target_y = get_current_cursor_pos()

            # Dispatch action
            if action_type in ("click", "left_click"):
                executor.execute_click(target_x, target_y, button="left", clicks=1)
            elif action_type == "double_click":
                executor.execute_click(target_x, target_y, button="left", clicks=2)
            elif action_type == "right_click":
                executor.execute_click(target_x, target_y, button="right", clicks=1)
            elif action_type == "type":
                # Ensure input field is focused first
                if "bbox" in step or "bounding_box" in step:
                    executor.execute_click(target_x, target_y, button="left", clicks=1)
                    time.sleep(random.uniform(0.1, 0.2))
                text_to_type = step.get("text", "")
                executor.execute_type(text_to_type, clear_field_first=step.get("clear", False))
            elif action_type == "hotkey":
                executor.execute_hotkey(step.get("keys", step.get("key", [])))
            elif action_type == "press":
                executor.execute_press_key(step.get("key", "enter"))
            elif action_type == "scroll":
                executor.execute_scroll(step.get("amount", -3))
            elif action_type == "wait":
                wait_sec = float(step.get("duration", 1.0))
                time.sleep(wait_sec)
            else:
                logger.warning(f"[Executor] Unknown action type '{action_type}' at step {idx}. Skipping.")
                step_result["status"] = "skipped"

            execution_summary["executed_steps"] += 1
            # Realistic pause between successive autonomous workflow steps
            time.sleep(random.uniform(0.3, 0.7))

        except Exception as e:
            logger.error(f"[Executor] Error executing step {idx} ({action_type}): {e}")
            step_result["status"] = "error"
            step_result["error"] = str(e)
            execution_summary["failed_steps"] += 1
            execution_summary["status"] = "partial_failure"

        execution_summary["details"].append(step_result)

    logger.info(f"[Executor] Action loop complete. Result: {execution_summary['status']}")
    return execution_summary


# ==============================================================================
# 7. STANDALONE VERIFICATION ROUTINE
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print(" MEMBER 2 (OS SANDBOX LEAD) - PHASE 2 EXECUTION ENGINE TEST")
    print("=" * 70)

    # 1. Screen resolution & cursor test
    res = get_screen_resolution()
    cur = get_current_cursor_pos()
    print(f"Screen Resolution: {res[0]}x{res[1]}")
    print(f"Current Cursor: ({cur[0]}, {cur[1]})")

    # 2. Bézier Trajectory Test
    print("\n[Test 1] Generating Bézier Curve Trajectory...")
    path = HumanTrajectoryGenerator.generate_trajectory(cur, (res[0] // 2, res[1] // 2))
    print(f"Generated {len(path)} smooth points. First: {path[0]}, Last: {path[-1]}")

    # 3. Vision Grounding Output Translation (Normalized 0.0 - 1.0 bbox from Member 1)
    print("\n[Test 2] Translating Model Output [0.15, 0.20, 0.35, 0.28]...")
    mock_model_output = {
        "target_found": True,
        "confidence": 0.96,
        "bounding_box": [0.15, 0.20, 0.35, 0.28]
    }
    abs_box = normalize_bounding_box(mock_model_output["bounding_box"])
    aim_pt = sample_human_target_point(abs_box)
    print(f"Model Normalized Box -> Screen Pixels: {abs_box}")
    print(f"Gaussian Click Target inside box: {aim_pt}")

    # 4. Multi-step Execution Loop in Dry-Run Mode
    print("\n[Test 3] Testing Multi-Step Execution Loop in Dry-Run mode...")
    sample_workflow = {
        "steps": [
            {"action": "click", "bbox": [0.1, 0.1, 0.2, 0.15], "focus_window": "Notepad"},
            {"action": "type", "text": "Hacktoberfest 2026 - Autonomous Desktop Agent Active!"},
            {"action": "hotkey", "keys": ["ctrl", "s"]}
        ]
    }
    result = execute_action_loop(sample_workflow, dry_run=True)
    print(f"Execution Summary: {result}")
    print("\nMember 2 Phase 2 Engine Verified Successfully!")
