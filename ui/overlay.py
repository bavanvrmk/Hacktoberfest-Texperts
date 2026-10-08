import tkinter as tk
import time
import threading

class AROverlay(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Make the window cover the whole screen and transparent
        self.attributes('-alpha', 0.9) 
        self.attributes('-topmost', True)
        self.attributes('-transparentcolor', 'black') # Black will be fully transparent
        self.overrideredirect(True)
        
        # Get screen size
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # Transparent Canvas
        self.canvas = tk.Canvas(self, width=screen_width, height=screen_height, bg='black', highlightthickness=0)
        self.canvas.pack()
        
        self.bounding_boxes = {} # Store active bounding box IDs

    def draw_glowing_box(self, x1, y1, x2, y2, duration=2.0, color="#00ffff"):
        """
        Draws a temporary glowing bounding box at the specified coordinates.
        """
        # Outer glow (thicker, less alpha but tkinter doesn't support alpha on lines easily so we use multiple lines)
        glow3 = self.canvas.create_rectangle(x1-6, y1-6, x2+6, y2+6, outline=color, width=1, stipple='gray50')
        glow2 = self.canvas.create_rectangle(x1-4, y1-4, x2+4, y2+4, outline=color, width=2, stipple='gray50')
        glow1 = self.canvas.create_rectangle(x1-2, y1-2, x2+2, y2+2, outline=color, width=3)
        core = self.canvas.create_rectangle(x1, y1, x2, y2, outline="white", width=2)
        
        box_id = f"{time.time()}"
        self.bounding_boxes[box_id] = [glow3, glow2, glow1, core]
        
        # Schedule cleanup
        threading.Thread(target=self._animate_and_remove, args=(box_id, duration), daemon=True).start()
        
    def _animate_and_remove(self, box_id, duration):
        """
        Animation loop for the glowing box, fades/cleans up after duration.
        """
        steps = 20
        sleep_time = duration / steps
        
        # Simple pulsating animation loop
        for step in range(steps):
            time.sleep(sleep_time)
            
        # Cleanup
        if box_id in self.bounding_boxes:
            # We use after() to safely update Tkinter UI from a background thread
            self.after(0, self._delete_box_items, box_id)

    def _delete_box_items(self, box_id):
        if box_id in self.bounding_boxes:
            for item in self.bounding_boxes[box_id]:
                self.canvas.delete(item)
            del self.bounding_boxes[box_id]

def show_overlay():
    app = AROverlay()
    
    # Mocking coordinates arriving for demonstration
    def mock_coordinates():
        time.sleep(1)
        print("[Overlay] Drawing target box at (100, 100) -> (300, 200)")
        app.draw_glowing_box(100, 100, 300, 200, duration=3.0, color="#32cd32") # lime green glow
        
        time.sleep(4)
        print("[Overlay] Drawing target box at (500, 400) -> (600, 450)")
        app.draw_glowing_box(500, 400, 600, 450, duration=2.0, color="#ff00ff") # magenta glow
        
    threading.Thread(target=mock_coordinates, daemon=True).start()
    
    app.mainloop()

if __name__ == "__main__":
    show_overlay()
