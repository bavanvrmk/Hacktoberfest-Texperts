"""
ui/spotlight.py — Phase 3 Premium Spotlight UI
Glassmorphism command bar wired to the Event Bus orchestrator.
Features: animated border glow, step-by-step status labels, shimmer progress bar.
"""

import customtkinter as ctk
import keyboard
import threading
import time
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from core.event_bus import (
        event_bus,
        EVENT_TASK_START,
        EVENT_PROGRESS,
        EVENT_TASK_SUCCESS,
        EVENT_TASK_FAILED,
    )
    HAS_EVENT_BUS = True
except ImportError:
    HAS_EVENT_BUS = False


# ─── Color Tokens ────────────────────────────────────────────────
BG_DEEP   = "#08101f"
BG_CARD   = "#0f1d33"
BG_ENTRY  = "#0d1a2e"
CYAN      = "#06b6d4"
BLUE_GLOW = "#3b82f6"
TEXT_DIM  = "#475569"
TEXT_MAIN = "#e2e8f0"
TEXT_CYAN = "#38bdf8"
GREEN     = "#10b981"
AMBER     = "#f59e0b"
RED       = "#ef4444"

STEPS = [
    "🔒 Redacting PII from screenshot…",
    "🧠 Grounding target with VisionModel…",
    "🎯 Projecting AR bounding box…",
    "🖱  Executing smooth click…",
    "📊 Calculating ROI & logging…",
    "✅ Done!",
]


class SpotlightUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ── Window chrome ─────────────────────────────────────────
        self.title("Shadow Automator")
        self.overrideredirect(True)
        self.attributes("-alpha", 0.97)
        self.attributes("-topmost", True)
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=BG_DEEP)

        W, H = 780, 80
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{int(sw/2 - W/2)}+{int(sh * 0.28)}")
        self._base_h = H
        self._W = W

        # ── Outer glow canvas ──────────────────────────────────────
        self.canvas = ctk.CTkCanvas(self, width=W, height=H, bg=BG_DEEP, highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # ── Glass card ────────────────────────────────────────────
        self.card = ctk.CTkFrame(
            self, fg_color=BG_CARD,
            corner_radius=18, border_width=1, border_color=BLUE_GLOW
        )
        self.card.place(x=6, y=6, relwidth=1, relheight=1, width=-12, height=-12)

        # ── Search row ────────────────────────────────────────────
        self.row = ctk.CTkFrame(self.card, fg_color="transparent")
        self.row.pack(fill="x", padx=12, pady=(10, 0))

        # Icon label
        self.icon_lbl = ctk.CTkLabel(
            self.row, text="⚡", font=("Segoe UI Emoji", 22),
            text_color=CYAN, width=30
        )
        self.icon_lbl.pack(side="left", padx=(4, 0))

        # Entry
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.row,
            textvariable=self.search_var,
            height=44,
            font=("Segoe UI", 20),
            placeholder_text="Ask Automator to click or type something…",
            placeholder_text_color=TEXT_DIM,
            border_width=0,
            corner_radius=12,
            fg_color=BG_ENTRY,
            text_color=TEXT_CYAN,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(8, 4))

        # Shortcut badge
        self.badge = ctk.CTkLabel(
            self.row, text="⌘ Space",
            font=("Segoe UI", 11), text_color=TEXT_DIM,
            fg_color="#1e293b", corner_radius=6, width=70, height=22
        )
        self.badge.pack(side="right", padx=(0, 4))

        # ── Thin shimmer bar ──────────────────────────────────────
        self.progress = ctk.CTkProgressBar(
            self.card, height=3,
            progress_color=CYAN, fg_color=BG_CARD,
            mode="indeterminate"
        )

        # ── Step label ────────────────────────────────────────────
        self.step_lbl = ctk.CTkLabel(
            self.card, text="",
            font=("Segoe UI", 12), text_color=TEXT_DIM
        )

        # ── State ─────────────────────────────────────────────────
        self.is_visible = True
        self.is_processing = False
        self._glow_angle = 0
        self._glow_job = None

        # ── Bindings ──────────────────────────────────────────────
        self.bind("<Escape>", lambda e: self.hide_spotlight())
        self.search_entry.bind("<Return>", self.on_execute)

        # ── Event bus subscriptions ───────────────────────────────
        if HAS_EVENT_BUS:
            event_bus.subscribe(EVENT_PROGRESS, self._on_progress)
            event_bus.subscribe(EVENT_TASK_SUCCESS, self._on_success)
            event_bus.subscribe(EVENT_TASK_FAILED, self._on_failure)

        self._start_idle_glow()

    # ── Idle border glow animation ─────────────────────────────────
    def _start_idle_glow(self):
        colors = [BLUE_GLOW, "#4f90ff", CYAN, "#4f90ff", BLUE_GLOW]
        def _cycle(i=0):
            if not self.is_processing and self.is_visible:
                try:
                    self.card.configure(border_color=colors[i % len(colors)])
                except Exception:
                    return
            self._glow_job = self.after(600, _cycle, i + 1)
        _cycle()

    # ── Execute ───────────────────────────────────────────────────
    def on_execute(self, event=None):
        query = self.search_var.get().strip()
        if not query or self.is_processing:
            return

        self.is_processing = True
        self._expand(True)
        self.search_entry.configure(state="disabled", text_color=TEXT_DIM)
        self.card.configure(border_color=CYAN, border_width=2)
        self._update_step(STEPS[0])

        if HAS_EVENT_BUS:
            threading.Thread(
                target=lambda: event_bus.emit(EVENT_TASK_START, {"command": query}),
                daemon=True
            ).start()
        else:
            threading.Thread(target=self._mock_run, args=(query,), daemon=True).start()

    def _mock_run(self, query):
        for i, step in enumerate(STEPS[:-1]):
            time.sleep(0.9)
            self.after(0, self._update_step, STEPS[i + 1])
        time.sleep(0.4)
        self.after(0, self._finish_success, query, "$1.26")

    # ── Event bus callbacks (thread-safe via .after) ───────────────
    def _on_progress(self, data):
        step_text = data.get("step", "")
        self.after(0, self._update_step, step_text)

    def _on_success(self, data):
        roi = data.get("roi_msg", "+$1.26")
        summary = data.get("summary", "Task complete")
        self.after(0, self._finish_success, summary, roi)

    def _on_failure(self, data):
        err = data.get("error", "Unknown error")
        self.after(0, self._finish_failure, err)

    # ── UI update helpers ─────────────────────────────────────────
    def _update_step(self, text):
        self.step_lbl.configure(text=f"  {text}", text_color=TEXT_CYAN)

    def _expand(self, show: bool):
        h = self._base_h + 34 if show else self._base_h
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{self._W}x{h}+{int(sw/2 - self._W/2)}+{int(sh * 0.28)}")
        if show:
            self.progress.pack(fill="x", padx=14, pady=(4, 0))
            self.progress.start()
            self.step_lbl.pack(anchor="w", padx=18, pady=(2, 6))
        else:
            self.progress.stop()
            self.progress.pack_forget()
            self.step_lbl.pack_forget()

    def _finish_success(self, summary, roi):
        self._expand(False)
        self.card.configure(border_color=GREEN, border_width=2)
        self.search_entry.configure(state="normal", text_color=TEXT_CYAN)
        self.search_var.set("")
        self.is_processing = False
        self.hide_spotlight()
        # Pop toast
        self.after(200, lambda: _show_ctk_toast(self, f"✅ Done — {roi} saved", GREEN))
        self.after(800, lambda: self.card.configure(border_color=BLUE_GLOW, border_width=1))

    def _finish_failure(self, error):
        self._expand(False)
        self.card.configure(border_color=RED, border_width=2)
        self.search_entry.configure(state="normal", text_color=RED)
        self.search_entry.delete(0, "end")
        self.is_processing = False
        self.after(800, lambda: self.card.configure(border_color=BLUE_GLOW, border_width=1))
        self.after(0, lambda: _show_ctk_toast(self, f"❌ Failed: {error[:40]}", RED))

    # ── Visibility ────────────────────────────────────────────────
    def toggle_spotlight(self):
        if self.is_visible:
            self.hide_spotlight()
        else:
            self.show_spotlight()

    def hide_spotlight(self):
        self.withdraw()
        self.is_visible = False

    def show_spotlight(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self.search_entry.focus()
        self.is_visible = True


# ─── Floating CTk toast helper ────────────────────────────────────
class _CtkToast(ctk.CTkToplevel):
    def __init__(self, parent, message, color):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)

        sw = self.winfo_screenwidth()
        W, H = 420, 58
        self.geometry(f"{W}x{H}+{int(sw/2 - W/2)}+30")

        frame = ctk.CTkFrame(self, fg_color="#0f1d33", corner_radius=14,
                              border_width=2, border_color=color)
        frame.pack(fill="both", expand=True, padx=2, pady=2)

        ctk.CTkLabel(
            frame, text=message,
            font=("Segoe UI", 15, "bold"), text_color="white"
        ).pack(expand=True)

        self._fade(0.0, 1)

    def _fade(self, a, direction):
        a = round(a + 0.08 * direction, 2)
        a = max(0.0, min(1.0, a))
        try:
            self.attributes("-alpha", a)
        except Exception:
            return
        if direction == 1 and a < 0.96:
            self.after(16, self._fade, a, 1)
        elif direction == 1:
            self.after(3200, self._fade, a, -1)
        elif a > 0.0:
            self.after(16, self._fade, a, -1)
        else:
            try:
                self.destroy()
            except Exception:
                pass


def _show_ctk_toast(parent, message, color=GREEN):
    _CtkToast(parent, message, color)


# ─── Entry point ─────────────────────────────────────────────────
def hotkey_listener(app):
    keyboard.add_hotkey("ctrl+space", app.toggle_spotlight)
    keyboard.wait()


if __name__ == "__main__":
    app = SpotlightUI()
    t = threading.Thread(target=hotkey_listener, args=(app,), daemon=True)
    t.start()
    app.mainloop()
