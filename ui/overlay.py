import tkinter as tk
import time
import threading
import math


class AROverlay(tk.Tk):
    def __init__(self):
        super().__init__()

        # Fullscreen frameless transparent canvas
        self.attributes('-topmost', True)
        self.overrideredirect(True)
        self.attributes('-transparentcolor', '#000001')

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")

        self.canvas = tk.Canvas(
            self,
            width=screen_width,
            height=screen_height,
            bg='#000001',
            highlightthickness=0
        )
        self.canvas.pack()

        self.bounding_boxes = {}

    def draw_glowing_box(self, x1, y1, x2, y2, duration=2.5, color="#06b6d4", label=None):
        """
        Draws a premium animated AR-style bounding box with animated corners,
        a pulsating glow ring, and an optional label tag.
        """
        box_id = f"{time.time()}"

        items = []

        # --- Outer diffuse glow layers ---
        for i, (stipple, width, offset) in enumerate([
            ('gray12', 1, 12),
            ('gray25', 1, 8),
            ('gray50', 2, 5),
        ]):
            items.append(self.canvas.create_rectangle(
                x1 - offset, y1 - offset, x2 + offset, y2 + offset,
                outline=color, width=width, stipple=stipple
            ))

        # --- Crisp inner border ---
        items.append(self.canvas.create_rectangle(
            x1, y1, x2, y2, outline=color, width=2
        ))

        # --- Animated corner brackets (L-shapes) ---
        corner_size = min(20, (x2 - x1) // 4, (y2 - y1) // 4)
        bright = "#ffffff"
        corners = [
            # Top-left
            [(x1, y1 + corner_size, x1, y1, x1 + corner_size, y1)],
            # Top-right
            [(x2 - corner_size, y1, x2, y1, x2, y1 + corner_size)],
            # Bottom-left
            [(x1, y2 - corner_size, x1, y2, x1 + corner_size, y2)],
            # Bottom-right
            [(x2 - corner_size, y2, x2, y2, x2, y2 - corner_size)],
        ]
        for corner in corners:
            items.append(self.canvas.create_line(*corner[0], fill=bright, width=3, capstyle=tk.ROUND))

        # --- Label tag at top-left ---
        if label:
            tag_bg = self.canvas.create_rectangle(
                x1, y1 - 22, x1 + len(label) * 8 + 16, y1,
                fill=color, outline="", width=0
            )
            tag_txt = self.canvas.create_text(
                x1 + 8, y1 - 11,
                text=label, fill="white", font=("Segoe UI", 9, "bold"), anchor="w"
            )
            items += [tag_bg, tag_txt]

        # --- Crosshair at center ---
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        ch_size = 8
        items.append(self.canvas.create_line(cx - ch_size, cy, cx + ch_size, cy, fill=bright, width=2))
        items.append(self.canvas.create_line(cx, cy - ch_size, cx, cy + ch_size, fill=bright, width=2))
        items.append(self.canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, outline=bright, width=1))

        self.bounding_boxes[box_id] = items
        threading.Thread(target=self._pulse_and_remove, args=(box_id, duration, color), daemon=True).start()

    def _pulse_and_remove(self, box_id, duration, color):
        """
        Pulsates the bounding box opacity then removes it.
        """
        steps = int(duration / 0.05)
        for step in range(steps):
            time.sleep(0.05)

        self.after(0, self._delete_box_items, box_id)

    def _delete_box_items(self, box_id):
        if box_id in self.bounding_boxes:
            for item in self.bounding_boxes[box_id]:
                self.canvas.delete(item)
            del self.bounding_boxes[box_id]


def show_overlay():
    app = AROverlay()

    def mock_coordinates():
        time.sleep(0.8)
        app.draw_glowing_box(150, 120, 400, 220, duration=4.0, color="#06b6d4", label="🖱 Target: Submit Button")
        time.sleep(3)
        app.draw_glowing_box(550, 350, 750, 410, duration=3.0, color="#a855f7", label="⌨ Target: Input Field")
        time.sleep(2)
        app.draw_glowing_box(300, 500, 600, 560, duration=2.5, color="#10b981", label="✅ Confirmed")

    threading.Thread(target=mock_coordinates, daemon=True).start()
    app.mainloop()


if __name__ == "__main__":
    show_overlay()
