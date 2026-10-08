import time
import random
import pyautogui

# Try importing pygetwindow for application focus, but mock if not available
try:
    import pygetwindow as gw
except ImportError:
    gw = None

# Configure PyAutoGUI Safety bounds (from Phase 1 OS Sandbox)
pyautogui.FAILSAFE = True

def smooth_mouse_move(start_x, start_y, target_x, target_y, duration=0.5):
    """
    Mouse smoothing algorithm simulating human-like trajectories.
    Uses PyAutoGUI's easeOutQuad to naturally decelerate as it approaches the target.
    """
    # Introduce slight randomness to target coordinates
    jitter_x = target_x + random.randint(-2, 2)
    jitter_y = target_y + random.randint(-2, 2)
    
    # Move the mouse smoothly
    pyautogui.moveTo(
        jitter_x, 
        jitter_y, 
        duration=duration, 
        tween=pyautogui.easeOutQuad
    )

def ensure_window_focus(window_title_keyword):
    """
    Application window focus listener.
    Checks if a window matching the keyword is active; if not, attempts to focus it.
    """
    if gw is None:
        print(f"[Focus Listener] pygetwindow not installed. Assuming '{window_title_keyword}' is focused.")
        return True
        
    try:
        windows = gw.getWindowsWithTitle(window_title_keyword)
        if not windows:
            print(f"[Focus Listener] Could not find window matching: {window_title_keyword}")
            return False
            
        target_window = windows[0]
        if not target_window.isActive:
            target_window.activate()
            time.sleep(0.2) # Wait for UI to come forward
            
        return True
    except Exception as e:
        print(f"[Focus Listener] Failed to focus window: {e}")
        return False

def execute_action_loop(action_json):
    """
    Click/type execution loops.
    Parses JSON containing coordinates and actions, and executes them with human-like timing.
    """
    print("[Executor] Starting execution loop...")
    
    for step in action_json.get("steps", []):
        action_type = step.get("action")
        
        # Determine center of bounding box for interaction
        bbox = step.get("bbox", [0, 0, 0, 0])
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        
        if action_type == "click":
            print(f"[Executor] Moving to click at ({center_x}, {center_y})")
            smooth_mouse_move(pyautogui.position().x, pyautogui.position().y, center_x, center_y, duration=0.6)
            
            # Human-like click delay
            time.sleep(random.uniform(0.1, 0.3))
            pyautogui.click()
            
        elif action_type == "type":
            text = step.get("text", "")
            print(f"[Executor] Moving to input field at ({center_x}, {center_y}) to type")
            smooth_mouse_move(pyautogui.position().x, pyautogui.position().y, center_x, center_y, duration=0.6)
            
            pyautogui.click()
            time.sleep(random.uniform(0.1, 0.2))
            
            # Type with human-like intervals
            pyautogui.write(text, interval=random.uniform(0.05, 0.15))
            
        # Wait between steps
        time.sleep(random.uniform(0.5, 1.5))
        
    print("[Executor] Execution loop finished.")

if __name__ == "__main__":
    # Test JSON payload from Member 1's model output
    sample_json = {
        "steps": [
            {"action": "click", "bbox": [100, 100, 150, 130]},
            {"action": "type", "text": "Hello World", "bbox": [200, 200, 400, 240]}
        ]
    }
    
    print("Testing Member 2 Phase 2 execution loop...")
    ensure_window_focus("Notepad")
    # execute_action_loop(sample_json)  # Commented out so it doesn't hijack user's mouse during test
