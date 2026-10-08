import mss
import mss.tools
import pyautogui
from PIL import Image

# Enable PyAutoGUI fail-safe: moving mouse to any corner of the screen throws an exception
pyautogui.FAILSAFE = True
# Safety bounds for mouse movement to prevent runaway automation
pyautogui.PAUSE = 0.5 # Adds a half-second pause after every PyAutoGUI call

class OSSandbox:
    def __init__(self):
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1] # Primary monitor

    def grab_screen(self, output_path="screenshot.png"):
        """Grabs the full screen and saves it."""
        sct_img = self.sct.grab(self.monitor)
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=output_path)
        return output_path

    def grab_screen_crop(self, output_path, x, y, width, height):
        """Grabs a specific cropped region of the screen."""
        monitor_crop = {
            "top": self.monitor["top"] + y, 
            "left": self.monitor["left"] + x, 
            "width": width, 
            "height": height
        }
        sct_img = self.sct.grab(monitor_crop)
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=output_path)
        return output_path

    def normalize_coordinates(self, relative_x, relative_y):
        """
        Converts normalized coordinates (0.0 to 1.0) into absolute screen coordinates.
        """
        abs_x = int(relative_x * self.monitor["width"]) + self.monitor["left"]
        abs_y = int(relative_y * self.monitor["height"]) + self.monitor["top"]
        
        # Enforce safety bounds
        abs_x = max(self.monitor["left"], min(abs_x, self.monitor["left"] + self.monitor["width"] - 1))
        abs_y = max(self.monitor["top"], min(abs_y, self.monitor["top"] + self.monitor["height"] - 1))
        
        return abs_x, abs_y

    def safe_move_and_click(self, x, y):
        """
        Moves the mouse to coordinates safely and clicks.
        """
        # A simple check before moving, though PyAutoGUI failsafe handles extreme corners
        print(f"Executing safe click at ({x}, {y})")
        pyautogui.moveTo(x, y, duration=0.2, tween=pyautogui.easeInOutQuad)
        pyautogui.click()

if __name__ == "__main__":
    sandbox = OSSandbox()
    # Test screen grab
    print("Grabbing full screen...")
    sandbox.grab_screen("test_full_screen.png")
    
    # Test crop
    print("Grabbing crop...")
    sandbox.grab_screen_crop("test_crop.png", 0, 0, 800, 600)
    
    # Test normalization
    abs_x, abs_y = sandbox.normalize_coordinates(0.5, 0.5)
    print(f"Normalized Center of Screen: ({abs_x}, {abs_y})")
