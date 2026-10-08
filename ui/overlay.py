import sys
import os
import queue
import tkinter as tk
import time
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from core.event_bus import event_bus, EVENT_OVERLAY_DRAW, EVENT_ACTION_EXECUTED
    HAS_EVENT_BUS = True
except ImportError:
    HAS_EVENT_BUS = False


class AROverlay(tk.Toplevel):
    def __init__(self, master=None):
        # Do not assign self._root — that name is a Tk method (Misc._root).
        owner = master
        if owner is None:
            owner = tk.Tk()
            owner.withdraw()
        super().__init__(owner)
        self._owner = owner

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
        self._ui_events = queue.Queue()
        self._make_click_through()
        self._bind_events()
        self._poll_events()

    def _make_click_through(self):
        """Let mouse events pass through the transparent fullscreen canvas."""
        if not sys.platform.startswith("win"):
            return
        try:
            import ctypes
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            )
        except Exception as exc:
            print(f"[Overlay] click-through setup skipped: {exc}")

    def _bind_events(self):
        if not HAS_EVENT_BUS:
            return
        event_bus.subscribe(EVENT_OVERLAY_DRAW, self._on_overlay_draw)
        event_bus.subscribe(EVENT_ACTION_EXECUTED, self._on_action_executed)

    def _on_overlay_draw(self, data):
        if data:
            self._ui_events.put(("draw", data))

    def _on_action_executed(self, data):
        if data:
            self._ui_events.put(("ping", data))

    def _poll_events(self):
        while True:
            try:
                kind, data = self._ui_events.get_nowait()
            except queue.Empty:
                break
            try:
                if kind == "draw":
                    self.draw_glowing_box(
                        data.get("x1", 0),
                        data.get("y1", 0),
                        data.get("x2", 0),
                        data.get("y2", 0),
                        duration=data.get("duration", 2.5),
                        color=data.get("color", "#06b6d4"),
                        label=data.get("label"),
                    )
                elif kind == "ping":
                    self.draw_click_ping(data.get("x", 0), data.get("y", 0))
                elif kind == "delete":
                    self._delete_box_items(data)
            except Exception as exc:
                print(f"[Overlay] draw failed: {exc}")
        try:
            self.after(50, self._poll_events)
        except Exception:
            pass

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

    def draw_click_ping(self, x, y, color="#38bdf8"):
        """Brief ring at the click point so action events are visible on the overlay."""
        x, y = int(x), int(y)
        items = []
        for radius in (10, 22, 36):
            items.append(self.canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                outline=color, width=2
            ))
        box_id = f"ping-{time.time()}"
        self.bounding_boxes[box_id] = items
        threading.Thread(target=self._pulse_and_remove, args=(box_id, 0.8, color), daemon=True).start()

    def _pulse_and_remove(self, box_id, duration, color):
        """
        Pulsates the bounding box opacity then removes it.
        """
        steps = int(duration / 0.05)
        for step in range(steps):
            time.sleep(0.05)

        self._ui_events.put(("delete", box_id))

    def _delete_box_items(self, box_id):
        if box_id in self.bounding_boxes:
            for item in self.bounding_boxes[box_id]:
                self.canvas.delete(item)
            del self.bounding_boxes[box_id]


def show_overlay():
    app = AROverlay()

    def mock_coordinates():
        time.sleep(0.8)
        app._ui_events.put(("draw", {"x1": 150, "y1": 120, "x2": 400, "y2": 220, "duration": 4.0, "color": "#06b6d4", "label": "Target: Submit Button"}))
        time.sleep(3)
        app._ui_events.put(("draw", {"x1": 550, "y1": 350, "x2": 750, "y2": 410, "duration": 3.0, "color": "#a855f7", "label": "Target: Input Field"}))
        time.sleep(2)
        app._ui_events.put(("draw", {"x1": 300, "y1": 500, "x2": 600, "y2": 560, "duration": 2.5, "color": "#10b981", "label": "Confirmed"}))

    threading.Thread(target=mock_coordinates, daemon=True).start()
    app.mainloop()


if __name__ == "__main__":
    show_overlay()
