"""
ui/spotlight.py — Luxury Black, Gray & Orange Autonomous Command Palette
Built for Hacktoberfest Hack Day — Coimbatore 2026.
Features:
- True rounded floating window with zero rectangular edge artifacts (-transparentcolor)
- High-quality animated sweeping Orange Glowbar beam with sine-eased gradient pulse
- Professionally graded Black, Zinc-Gray, and Electric Orange (#f97316) design system
- Keyboard-first navigation (Up/Down arrow nav, Tab auto-fill, Enter execute, Esc close)
- Curated presets including Outlook COM automation for evaluator demos
- Real-time search filtering & category pills
- Multi-stage execution telemetry drawer with stopwatch timer and orange shimmer bar
- Floating HUD toast with live ROI savings badge
"""

import sys
import os
import queue
import threading
import time
import math
import customtkinter as ctk
import keyboard

# Ensure workspace root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from core.event_bus import (
        event_bus,
        EVENT_TASK_START,
        EVENT_PROGRESS,
        EVENT_TASK_SUCCESS,
        EVENT_TASK_FAILED,
        EVENT_VISUAL_THOUGHT,
    )
    HAS_EVENT_BUS = True
except ImportError:
    HAS_EVENT_BUS = False


# ─── Design Tokens: Professionally Graded Black, Gray & Orange ───
TRANSPARENT_KEY = "#000001"  # Chroma key for true rounded frameless window on Windows

BG_CANVAS       = "#09090b"  # Deep obsidian black (Zinc 950)
BG_CARD         = "#121215"  # Luxury dark graphite card surface
BG_ENTRY        = "#18181b"  # Refined zinc-900 input field
BG_ROW          = "#161619"  # Elevated charcoal item row
BG_ROW_HOVER    = "#222228"  # Warm charcoal hover
BG_ROW_ACTIVE   = "#2a2725"  # Active selection with warm dark amber tint

BORDER_IDLE     = "#27272a"  # Subtle zinc-800 border
BORDER_ORANGE   = "#f97316"  # Electric Sunset Orange
BORDER_HOT      = "#ea580c"  # Deep burnished orange

ORANGE_HOT      = "#ea580c"  # Deep fiery orange
ORANGE_MAIN     = "#f97316"  # Electric Orange primary accent
ORANGE_GLOW     = "#fb923c"  # Luminous orange beam
ORANGE_SOFT     = "#fdba74"  # Highlight flare
ORANGE_PALE     = "#fed7aa"  # Core white-hot beam center
ORANGE_BADGE_BG = "#381708"  # Subtle warm dark badge background
ORANGE_BADGE_BD = "#7c2d12"  # Muted orange badge border

TEXT_PRIMARY    = "#fafafa"  # Pure crisp white (100% contrast)
TEXT_SECONDARY  = "#d4d4d8"  # Clean neutral gray (Zinc 300)
TEXT_MUTED      = "#71717a"  # Refined zinc muted (Zinc 500)
TEXT_DIM        = "#52525b"  # Deep zinc faint (Zinc 600)
TEXT_ORANGE     = "#fb923c"  # Luminous orange text


# ─── Curated Actions & Automation Presets ─────────────────────────
DEFAULT_ACTIONS = [
    {
        "id": "whatsapp_msg",
        "category": "APPS",
        "icon": "💬",
        "title": "WhatsApp: Send Message to Contact",
        "command": "open whatsapp and search for pranav cceb and send hi",
        "subtitle": "Search contact 'pranav cceb' & dispatch message via WhatsApp",
        "badge": "WhatsApp",
        "badge_color": "#25d366",
        "keywords": ["whatsapp", "pranav", "chat", "message", "send", "hi", "social"],
    },
    {
        "id": "screen_summary",
        "category": "VISION",
        "icon": "👁",
        "title": "Read & Summarize Screen Contents",
        "command": "read contents on the screen and summarize",
        "subtitle": "Local Qwen2.5-VL Vision reads active windows & documents",
        "badge": "Vision AI",
        "badge_color": ORANGE_MAIN,
        "keywords": ["summarize", "read", "screen", "summary", "vision", "contents", "ocr"],
    },
    {
        "id": "open_twitter",
        "category": "APPS",
        "icon": "🐦",
        "title": "Open Twitter / X",
        "command": "Open Twitter",
        "subtitle": "Launches installed Twitter app or opens x.com",
        "badge": "Social App",
        "badge_color": "#38bdf8",
        "keywords": ["twitter", "x", "social", "tweet", "feed"],
    },
    {
        "id": "open_chatgpt",
        "category": "APPS",
        "icon": "🤖",
        "title": "Ask ChatGPT",
        "command": "Open ChatGPT",
        "subtitle": "Launches ChatGPT or opens chatgpt.com",
        "badge": "AI Engine",
        "badge_color": "#10b981",
        "keywords": ["chatgpt", "openai", "gpt", "ask", "ai", "search"],
    },
    {
        "id": "email_hackathon_demo",
        "category": "EMAIL",
        "icon": "📧",
        "title": "Send Email via Outlook to Evaluator",
        "command": "Send an email using outlook to jp_vedaj@cb.amrita.edu about how good my hackathon demo was",
        "subtitle": "To: jp_vedaj@cb.amrita.edu · Topic: Hackathon Demo Feedback",
        "badge": "Outlook COM",
        "badge_color": ORANGE_MAIN,
        "keywords": ["email", "outlook", "jp_vedaj", "demo", "amrita", "send", "mail", "hackathon"],
    },
    {
        "id": "roi_dashboard",
        "category": "TELEMETRY",
        "icon": "📊",
        "title": "Launch Live ROI & Financial Engine",
        "command": "Open Chrome and navigate to http://127.0.0.1:8000",
        "subtitle": "Real-time Telemetry, PII Audit Logs & Cost Metrics",
        "badge": "Browser",
        "badge_color": ORANGE_GLOW,
        "keywords": ["roi", "dashboard", "telemetry", "chrome", "cost", "metrics", "financial"],
    },
    {
        "id": "notepad_notes",
        "category": "APPS",
        "icon": "📝",
        "title": "Draft Presentation Notes in Notepad",
        "command": "Launch Notepad and type hackathon notes for jury evaluation",
        "subtitle": "Process Spawning & Sandboxed Keystroke Injection",
        "badge": "Windows App",
        "badge_color": "#f59e0b",
        "keywords": ["notepad", "notes", "type", "presentation", "jury", "app"],
    },
    {
        "id": "vision_click",
        "category": "VISION",
        "icon": "🖱",
        "title": "Autonomous Vision Grounding Click",
        "command": "Click the Save Changes button",
        "subtitle": "Local Qwen2.5-VL Object Detection & AR Projection",
        "badge": "Vision AI",
        "badge_color": ORANGE_HOT,
        "keywords": ["click", "vision", "grounding", "button", "save", "qwen"],
    },
    {
        "id": "system_taskmgr",
        "category": "SYSTEM",
        "icon": "⚡",
        "title": "Inspect Desktop Performance & VRAM",
        "command": "Launch Task Manager",
        "subtitle": "Win32 Sandbox Process Monitor",
        "badge": "Win32 Driver",
        "badge_color": "#a1a1aa",
        "keywords": ["task", "manager", "system", "vram", "performance", "sandbox"],
    },
    {
        "id": "email_quick",
        "category": "EMAIL",
        "icon": "📨",
        "title": "Send Quick Email Notification",
        "command": "Send an email using outlook to team@hackathon.org about presentation schedule",
        "subtitle": "Direct Dispatch via Outlook COM Automation",
        "badge": "Outlook COM",
        "badge_color": ORANGE_MAIN,
        "keywords": ["email", "team", "presentation", "schedule", "mail"],
    },
]

# Apple Assistant Quick Suggestion Chips (Inspired by Siri & Google Assistant)
SUGGESTION_CHIPS = [
    ("💬 WhatsApp", "open whatsapp and search for pranav cceb and send hi"),
    ("👁 Summarize", "read contents on the screen and summarize"),
    ("🐦 Twitter", "Open Twitter"),
    ("🤖 ChatGPT", "Open ChatGPT"),
    ("📧 Send Email", "Send an email using outlook to jp_vedaj@cb.amrita.edu about how good my hackathon demo was"),
    ("📝 Notes", "Launch Notepad and type hackathon notes for jury evaluation"),
    ("🌐 Chrome", "Open Chrome and search for Hacktoberfest 2026"),
]

CATEGORY_TABS = [
    ("ALL", "⚡ All"),
    ("EMAIL", "📧 Email"),
    ("APPS", "💻 Apps"),
    ("VISION", "🖱 Vision"),
    ("TELEMETRY", "📊 ROI"),
    ("SYSTEM", "⚙ System"),
]


class SpotlightUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ── Window Chrome & True-Rounded Framing ──────────────────
        self.title("Shadow Automator — Spotlight")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.98)

        # Make root window 100% transparent so only the rounded card displays (no rectangle edges)
        if sys.platform.startswith("win"):
            try:
                self.attributes("-transparentcolor", TRANSPARENT_KEY)
            except Exception:
                pass
        self.configure(fg_color=TRANSPARENT_KEY)
        ctk.set_appearance_mode("dark")

        self._W = 840
        self._H_EXPANDED = 496
        self._H_COMPACT  = 84
        self._H_EXEC     = 250

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self._pos_x = int(sw / 2 - self._W / 2)
        self._pos_y = int(sh * 0.22)
        self.geometry(f"{self._W}x{self._H_EXPANDED}+{self._pos_x}+{self._pos_y}")

        # ── Main Floating Rounded Glass Card (Apple Squircle Aesthetics) ──
        self.card = ctk.CTkFrame(
            self,
            fg_color=BG_CARD,
            corner_radius=28,
            border_width=2,
            border_color=BORDER_ORANGE,
        )
        self.card.pack(fill="both", expand=True, padx=6, pady=6)

        # ── High-Quality Animated Orange Glowbar (Top Edge) ────────
        self.glowbar_canvas = ctk.CTkCanvas(
            self.card,
            height=4,
            bg=BG_CARD,
            highlightthickness=0,
        )
        self.glowbar_canvas.pack(fill="x", padx=26, pady=(10, 2))

        # ── Apple Capsule Search Bar (Inspired by ChatGPT macOS / Apple Intelligence) ──
        self.capsule_bar = ctk.CTkFrame(
            self.card,
            fg_color="#18181c",
            corner_radius=24,
            height=48,
            border_width=1,
            border_color="#27272a",
        )
        self.capsule_bar.pack(fill="x", padx=16, pady=(4, 6))
        self.capsule_bar.pack_propagate(False)

        # Left (+) Action Menu Pill Button
        self.plus_btn = ctk.CTkButton(
            self.capsule_bar,
            text="+",
            width=32,
            height=32,
            corner_radius=16,
            font=("Segoe UI", 16, "bold"),
            fg_color="#222228",
            hover_color="#2c2c34",
            text_color="#e4e4e7",
            command=self._on_plus_click,
        )
        self.plus_btn.pack(side="left", padx=(8, 8))

        # Center Search Entry Field
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.capsule_bar,
            textvariable=self.search_var,
            height=40,
            font=("Segoe UI", 15),
            placeholder_text="Ask anything, describe task, or launch app…",
            placeholder_text_color=TEXT_MUTED,
            border_width=0,
            fg_color="transparent",
            text_color=TEXT_PRIMARY,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # Clear Query Button (✕)
        self.clear_btn = ctk.CTkButton(
            self.capsule_bar,
            text="✕",
            width=24,
            height=24,
            font=("Segoe UI", 11, "bold"),
            fg_color="transparent",
            hover_color="#222228",
            text_color=TEXT_MUTED,
            command=self._clear_search,
        )

        # "🧠 Think" Toggle Button (Image 1 reference)
        self.think_mode = True
        self.think_btn = ctk.CTkButton(
            self.capsule_bar,
            text="🧠 Think",
            width=76,
            height=30,
            corner_radius=15,
            font=("Segoe UI", 11, "bold"),
            fg_color=ORANGE_BADGE_BG,
            border_width=1,
            border_color=ORANGE_HOT,
            hover_color="#451a08",
            text_color=ORANGE_PALE,
            command=self._toggle_think_mode,
        )
        self.think_btn.pack(side="right", padx=(4, 6))

        # Microphone Icon Button (Image 1 reference)
        self.mic_btn = ctk.CTkButton(
            self.capsule_bar,
            text="🎙",
            width=30,
            height=30,
            corner_radius=15,
            font=("Segoe UI Emoji", 13),
            fg_color="transparent",
            hover_color="#222228",
            text_color=TEXT_SECONDARY,
            command=lambda: self.search_entry.focus_set(),
        )
        self.mic_btn.pack(side="right", padx=(2, 2))

        # Dispatch Beacon Button (Image 1 reference)
        self.beacon_btn = ctk.CTkButton(
            self.capsule_bar,
            text="⚡",
            width=34,
            height=34,
            corner_radius=17,
            font=("Segoe UI Emoji", 13),
            fg_color=ORANGE_MAIN,
            hover_color=ORANGE_HOT,
            text_color="#ffffff",
            command=self.on_execute,
        )
        self.beacon_btn.pack(side="right", padx=(4, 8))

        # ── Apple Assistant Suggestion Chips Bar (Image 2 reference) ──
        self.chips_frame = ctk.CTkFrame(self.card, fg_color="transparent", height=32)
        self.chips_frame.pack(fill="x", padx=16, pady=(0, 6))

        for chip_label, chip_cmd in SUGGESTION_CHIPS:
            cbtn = ctk.CTkButton(
                self.chips_frame,
                text=chip_label,
                font=("Segoe UI", 11, "bold"),
                height=26,
                corner_radius=13,
                fg_color="#18181c",
                border_width=1,
                border_color="#27272a",
                hover_color="#222228",
                text_color=TEXT_SECONDARY,
                command=lambda cmd=chip_cmd: self._on_chip_click(cmd),
            )
            cbtn.pack(side="left", padx=(0, 6))

        # ── Category Filter Bar ────────────────────────────────────
        self.filter_bar = ctk.CTkFrame(self.card, fg_color="transparent", height=30)
        self.filter_bar.pack(fill="x", padx=18, pady=(0, 6))

        self.active_category = "ALL"
        self._filter_buttons = {}
        for cat_key, cat_label in CATEGORY_TABS:
            btn = ctk.CTkButton(
                self.filter_bar,
                text=cat_label,
                font=("Segoe UI", 11, "bold" if cat_key == "ALL" else "normal"),
                height=24,
                corner_radius=12,
                fg_color=ORANGE_BADGE_BG if cat_key == "ALL" else "transparent",
                border_width=1 if cat_key == "ALL" else 0,
                border_color=ORANGE_HOT if cat_key == "ALL" else BORDER_IDLE,
                hover_color="#222228",
                text_color=ORANGE_GLOW if cat_key == "ALL" else TEXT_MUTED,
                command=lambda k=cat_key: self._set_category(k),
            )
            btn.pack(side="left", padx=(0, 6))
            self._filter_buttons[cat_key] = btn

        # ── Suggestions Frame (Dynamic List Container) ─────────────
        self.suggestions_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.suggestions_frame.pack(fill="both", expand=True, padx=16, pady=(2, 6))

        # ── Execution Telemetry Drawer (Hidden until running) ──────
        self.exec_drawer = ctk.CTkFrame(
            self.card,
            fg_color="#0e0e11",
            corner_radius=16,
            border_width=1,
            border_color=ORANGE_HOT,
        )

        self.exec_header_row = ctk.CTkFrame(self.exec_drawer, fg_color="transparent")
        self.exec_header_row.pack(fill="x", padx=16, pady=(10, 4))

        self.exec_title_lbl = ctk.CTkLabel(
            self.exec_header_row,
            text="⚡ Executing Autonomous Pipeline…",
            font=("Segoe UI", 14, "bold"),
            text_color=ORANGE_GLOW,
        )
        self.exec_title_lbl.pack(side="left")

        self.exec_timer_lbl = ctk.CTkLabel(
            self.exec_header_row,
            text="⏱ 0.0s",
            font=("JetBrains Mono", 12),
            text_color=TEXT_MUTED,
        )
        self.exec_timer_lbl.pack(side="right")

        # Shimmer progress bar in vibrant orange
        self.progress_bar = ctk.CTkProgressBar(
            self.exec_drawer,
            height=4,
            progress_color=ORANGE_MAIN,
            fg_color="#1f1f23",
            mode="indeterminate",
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(4, 6))

        # Step progression text
        self.exec_step_lbl = ctk.CTkLabel(
            self.exec_drawer,
            text="🔒 Redacting PII from screenshot…",
            font=("Segoe UI", 12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        )
        self.exec_step_lbl.pack(fill="x", padx=18, pady=(0, 4))

        # ── Multi-Screenshot Visual Agent Reasoning Box ────────────
        self.visual_thought_card = ctk.CTkFrame(
            self.exec_drawer,
            fg_color="#121216",
            corner_radius=10,
            border_width=1,
            border_color="#27272a",
        )
        self.visual_thought_card.pack(fill="x", padx=16, pady=(4, 6))

        self.visual_thought_header = ctk.CTkFrame(self.visual_thought_card, fg_color="transparent")
        self.visual_thought_header.pack(fill="x", padx=12, pady=(6, 2))

        self.visual_thought_title = ctk.CTkLabel(
            self.visual_thought_header,
            text="🧠 Multi-Screenshot Visual Thinking",
            font=("Segoe UI", 11, "bold"),
            text_color=ORANGE_GLOW,
        )
        self.visual_thought_title.pack(side="left")

        self.visual_delta_badge = ctk.CTkLabel(
            self.visual_thought_header,
            text="Screen Delta: 0.0%",
            font=("JetBrains Mono", 10, "bold"),
            text_color="#34d399",
            fg_color="#064e3b",
            corner_radius=6,
            padx=6,
            pady=1,
        )
        self.visual_delta_badge.pack(side="right")

        self.visual_thought_lbl = ctk.CTkLabel(
            self.visual_thought_card,
            text="Observing visual screen transitions and reasoning next UI action...",
            font=("Segoe UI", 11),
            text_color=TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=760,
        )
        self.visual_thought_lbl.pack(fill="x", padx=12, pady=(2, 8))

        # Security Trust Pill
        self.trust_pill = ctk.CTkLabel(
            self.exec_drawer,
            text="🔒 Zero Cloud Egress · Local Qwen2.5-VL & Win32 Sandbox",
            font=("Segoe UI", 10),
            text_color="#10b981",
            anchor="w",
        )
        self.trust_pill.pack(fill="x", padx=18, pady=(0, 10))

        # ── Bottom Shortcut Tips Footer ────────────────────────────
        self.footer = ctk.CTkFrame(self.card, fg_color="#0a0a0d", corner_radius=10, height=28)
        self.footer.pack(fill="x", padx=16, pady=(0, 12))

        self.footer_shortcuts = ctk.CTkLabel(
            self.footer,
            text="↑↓ Navigate   •   ↵ Run   •   Tab Auto-fill   •   Esc Close",
            font=("Segoe UI", 11),
            text_color=TEXT_MUTED,
        )
        self.footer_shortcuts.pack(side="left", padx=12, pady=4)

        self.footer_engine = ctk.CTkLabel(
            self.footer,
            text="● Qwen2.5-VL · Local COM Engine",
            font=("Segoe UI", 11, "bold"),
            text_color=ORANGE_MAIN,
        )
        self.footer_engine.pack(side="right", padx=12, pady=4)

        # ── State Machine & Selection ──────────────────────────────
        self.is_visible = True
        self.is_processing = False
        self.selected_index = 0
        self._current_matches = []
        self._row_widgets = []
        self._start_time = None
        self._timer_job = None
        self._glow_job = None
        self._beam_job = None
        self._beam_step = 0
        self._toggle_pending = False
        self._toggle_lock = threading.Lock()
        self._ui_events = queue.Queue()

        # ── Bindings ───────────────────────────────────────────────
        self.bind("<Escape>", lambda e: self.hide_spotlight())
        self.search_entry.bind("<KeyRelease>", self._on_key_release)
        self.search_entry.bind("<Down>", self._on_key_down)
        self.search_entry.bind("<Up>", self._on_key_up)
        self.search_entry.bind("<Tab>", self._on_key_tab)
        self.search_entry.bind("<Return>", self._on_key_return)

        # ── Event Bus Subscriptions ────────────────────────────────
        if HAS_EVENT_BUS:
            event_bus.subscribe(EVENT_PROGRESS, self._on_progress)
            event_bus.subscribe(EVENT_TASK_SUCCESS, self._on_success)
            event_bus.subscribe(EVENT_TASK_FAILED, self._on_failure)
            event_bus.subscribe(EVENT_VISUAL_THOUGHT, self._on_visual_thought)

        # ── Populate Initial Actions & Start Animated Glowbar ─────
        self._update_suggestions()
        self._start_orange_glowbar()
        self._poll_toggle()

    # ── High-Quality Animated Orange Glowbar Beam ──────────────────
    def _start_orange_glowbar(self):
        """
        Sweeps an organic luminous orange light beam back and forth across the glowbar
        with smooth sine easing, complemented by breathing card border pulse.
        """
        w = max(400, self._W - 60)

        def _tick():
            if not self.is_visible:
                self._beam_job = self.after(100, _tick)
                return

            if getattr(self, "_in_burst", False):
                self._beam_job = self.after(25, _tick)
                return

            try:
                self._beam_step = (self._beam_step + 1) % 360
                rad = math.radians(self._beam_step * 2.2)

                # Sine-wave position of the beam center
                center_x = (math.sin(rad) * 0.5 + 0.5) * w
                beam_width = 150 if not self.is_processing else 240

                self.glowbar_canvas.delete("all")

                # Base ambient orange line
                base_color = "#33180d" if not self.is_processing else "#451a08"
                self.glowbar_canvas.create_line(0, 2, w, 2, fill=base_color, width=1)

                # Outer diffuse glow
                x1 = max(0, center_x - beam_width / 2)
                x2 = min(w, center_x + beam_width / 2)
                self.glowbar_canvas.create_line(x1, 2, x2, 2, fill=ORANGE_HOT, width=2)

                # Middle bright glow
                mx1 = max(0, center_x - beam_width / 4)
                mx2 = min(w, center_x + beam_width / 4)
                self.glowbar_canvas.create_line(mx1, 2, mx2, 2, fill=ORANGE_MAIN, width=3)

                # Core white-hot flare
                cx1 = max(0, center_x - 16)
                cx2 = min(w, center_x + 16)
                self.glowbar_canvas.create_line(cx1, 2, cx2, 2, fill=ORANGE_PALE, width=3)

                # Card border breathing glow: smooth cycle through luxury orange shades
                if not self.is_processing:
                    border_colors = [BORDER_ORANGE, ORANGE_HOT, "#c2410c", ORANGE_HOT, BORDER_ORANGE, ORANGE_GLOW]
                    color_idx = int((self._beam_step / 15) % len(border_colors))
                    self.card.configure(border_color=border_colors[color_idx])
                else:
                    pulse_idx = int((self._beam_step / 6) % 2)
                    self.card.configure(border_color=ORANGE_MAIN if pulse_idx == 0 else ORANGE_PALE)

            except Exception:
                pass

            delay = 25 if self.is_processing else 35
            self._beam_job = self.after(delay, _tick)

        _tick()

    def _flash_activation_pulse(self):
        """Intense cinematic orange glowbar shockwave when Spotlight is summoned."""
        w = max(400, self._W - 60)
        cx = w / 2
        self._in_burst = True

        # Card border flash sequence
        flashes = [ORANGE_PALE, ORANGE_SOFT, ORANGE_GLOW, ORANGE_MAIN, ORANGE_HOT, BORDER_ORANGE]
        def _card_step(i=0):
            if i < len(flashes):
                try:
                    self.card.configure(border_color=flashes[i], border_width=2)
                except Exception:
                    return
                self.after(35, _card_step, i + 1)
        _card_step()

        # Canvas expansion shockwave
        burst_steps = 10
        def _burst_step(step=0):
            if not self.is_visible:
                self._in_burst = False
                return
            if step >= burst_steps:
                self._in_burst = False
                return
            progress = (step + 1) / burst_steps
            spread = progress * (w / 2)
            alpha_glow = ORANGE_PALE if step < 3 else (ORANGE_GLOW if step < 6 else ORANGE_HOT)
            try:
                self.glowbar_canvas.delete("all")
                # Base track
                self.glowbar_canvas.create_line(0, 2, w, 2, fill="#33180d", width=1)
                # Expanding glow beam
                self.glowbar_canvas.create_line(cx - spread, 2, cx + spread, 2, fill=alpha_glow, width=3)
                # Intense white-hot center core
                core_spread = spread * 0.4
                self.glowbar_canvas.create_line(cx - core_spread, 2, cx + core_spread, 2, fill="#ffffff" if step < 4 else ORANGE_PALE, width=3)
            except Exception:
                pass
            self.after(22, _burst_step, step + 1)
        _burst_step()

    # ── Apple Interactive Actions & Visual Thinking ───────────────
    def _toggle_think_mode(self):
        self.think_mode = not self.think_mode
        if self.think_mode:
            self.think_btn.configure(
                fg_color=ORANGE_BADGE_BG,
                border_width=1,
                border_color=ORANGE_HOT,
                text_color=ORANGE_PALE,
            )
        else:
            self.think_btn.configure(
                fg_color="#222228",
                border_width=0,
                text_color=TEXT_MUTED,
            )

    def _on_plus_click(self):
        cats = [k for k, _ in CATEGORY_TABS]
        idx = (cats.index(self.active_category) + 1) % len(cats)
        self._set_category(cats[idx])

    def _on_chip_click(self, cmd: str):
        self.search_var.set(cmd)
        self._execute_command_text(cmd)

    def _on_visual_thought(self, data):
        self._ui_events.put(("visual_thought", data))

    def _update_visual_thought(self, data):
        thought = (data or {}).get("thought", "")
        diff_pct = (data or {}).get("diff_pct", 0.0)
        step_idx = (data or {}).get("step_index", 1)
        tot_steps = (data or {}).get("total_steps", 1)
        if thought:
            self.visual_thought_lbl.configure(text=f"Thought: {thought}")
            self.visual_delta_badge.configure(text=f"Delta: {diff_pct}% (t{step_idx-1}➔t{step_idx})")

    # ── Category Filtering ─────────────────────────────────────────
    def _set_category(self, category_key: str):
        self.active_category = category_key
        for key, btn in self._filter_buttons.items():
            if key == category_key:
                btn.configure(
                    fg_color=ORANGE_BADGE_BG,
                    border_width=1,
                    border_color=ORANGE_HOT,
                    font=("Segoe UI", 11, "bold"),
                    text_color=ORANGE_GLOW,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    border_width=0,
                    font=("Segoe UI", 11, "normal"),
                    text_color=TEXT_MUTED,
                )
        self._update_suggestions()

    # ── Search & Filter Logic ──────────────────────────────────────
    def _clear_search(self):
        self.search_var.set("")
        self.clear_btn.pack_forget()
        self.search_entry.focus_set()
        self._update_suggestions()

    def _on_key_release(self, event):
        if event.keysym in ("Up", "Down", "Tab", "Return", "Escape"):
            return

        query = self.search_var.get().strip()
        if query:
            if not self.clear_btn.winfo_ismapped():
                self.clear_btn.pack(side="right", padx=(0, 6), before=self.think_btn)
        else:
            if self.clear_btn.winfo_ismapped():
                self.clear_btn.pack_forget()

        self._update_suggestions()

    def _update_suggestions(self):
        query = self.search_var.get().strip().lower()
        cat = self.active_category

        filtered = []
        for item in DEFAULT_ACTIONS:
            if cat != "ALL" and item["category"] != cat:
                continue
            if query:
                text_match = (
                    query in item["title"].lower()
                    or query in item["command"].lower()
                    or query in item["subtitle"].lower()
                    or any(query in kw for kw in item.get("keywords", []))
                )
                if not text_match:
                    continue
            filtered.append(item)

        self._current_matches = filtered
        self.selected_index = 0 if filtered else -1
        self._render_suggestion_rows()

    # ── Render Suggestion Rows (Black, Gray & Orange) ──────────────
    def _render_suggestion_rows(self):
        for w in self.suggestions_frame.winfo_children():
            w.destroy()
        self._row_widgets = []

        if not self._current_matches:
            empty_frame = ctk.CTkFrame(self.suggestions_frame, fg_color="#111114", corner_radius=10)
            empty_frame.pack(fill="x", pady=6)
            q = self.search_var.get().strip()
            msg = f"↵ Run Custom Automation: '{q}'" if q else "No matching routine. Type any plain-text automation command."
            lbl = ctk.CTkLabel(
                empty_frame,
                text=msg,
                font=("Segoe UI", 13, "bold" if q else "normal"),
                text_color=ORANGE_GLOW if q else TEXT_MUTED,
            )
            lbl.pack(pady=14, padx=16, anchor="w")
            self._resize_for_content(1)
            return

        for idx, item in enumerate(self._current_matches[:5]):
            is_active = (idx == self.selected_index)
            row = ctk.CTkFrame(
                self.suggestions_frame,
                fg_color=BG_ROW_ACTIVE if is_active else BG_ROW,
                corner_radius=10,
                border_width=1 if is_active else 0,
                border_color=BORDER_ORANGE if is_active else BG_ROW,
                height=52,
            )
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            # Left Icon Chip in warm charcoal
            icon_box = ctk.CTkFrame(
                row,
                width=34,
                height=34,
                corner_radius=8,
                fg_color=ORANGE_BADGE_BG if is_active else "#1f1f23",
            )
            icon_box.pack(side="left", padx=(10, 10), pady=9)
            icon_box.pack_propagate(False)

            icon_lbl = ctk.CTkLabel(
                icon_box,
                text=item["icon"],
                font=("Segoe UI Emoji", 15),
            )
            icon_lbl.place(relx=0.5, rely=0.5, anchor="center")

            # Center Title & Subtitle Info
            text_box = ctk.CTkFrame(row, fg_color="transparent")
            text_box.pack(side="left", fill="both", expand=True, pady=6)

            title_lbl = ctk.CTkLabel(
                text_box,
                text=item["title"],
                font=("Segoe UI", 13, "bold"),
                text_color=TEXT_PRIMARY,
                anchor="w",
            )
            title_lbl.pack(fill="x")

            subtitle_lbl = ctk.CTkLabel(
                text_box,
                text=item["subtitle"],
                font=("Segoe UI", 11),
                text_color=TEXT_MUTED if not is_active else ORANGE_GLOW,
                anchor="w",
            )
            subtitle_lbl.pack(fill="x")

            # Right Badges (Category Pill + Run Action)
            badges_box = ctk.CTkFrame(row, fg_color="transparent")
            badges_box.pack(side="right", padx=(6, 12))

            cat_badge = ctk.CTkLabel(
                badges_box,
                text=item.get("badge", item["category"]),
                font=("Segoe UI", 10, "bold"),
                text_color=item.get("badge_color", ORANGE_MAIN),
                fg_color=ORANGE_BADGE_BG,
                corner_radius=6,
                width=72,
                height=22,
            )
            cat_badge.pack(side="left", padx=(0, 6))

            run_lbl = ctk.CTkLabel(
                badges_box,
                text="↵ Run",
                font=("Segoe UI", 11, "bold"),
                text_color=ORANGE_MAIN if is_active else TEXT_DIM,
            )
            run_lbl.pack(side="right")

            def _make_select(i=idx):
                self._select_row(i)

            def _make_exec(cmd=item["command"]):
                self._execute_command_text(cmd)

            for widget in (row, icon_box, icon_lbl, text_box, title_lbl, subtitle_lbl, badges_box, cat_badge, run_lbl):
                widget.bind("<Enter>", lambda e, i=idx: self._select_row(i))
                widget.bind("<Button-1>", lambda e, cmd=item["command"]: self._execute_command_text(cmd))

            self._row_widgets.append({
                "row": row,
                "title": title_lbl,
                "subtitle": subtitle_lbl,
                "run": run_lbl,
                "item": item,
            })

        self._resize_for_content(len(self._row_widgets))

    def _select_row(self, index: int):
        if not self._row_widgets:
            return
        self.selected_index = max(0, min(index, len(self._row_widgets) - 1))
        for idx, rw in enumerate(self._row_widgets):
            is_active = (idx == self.selected_index)
            rw["row"].configure(
                fg_color=BG_ROW_ACTIVE if is_active else BG_ROW,
                border_width=1 if is_active else 0,
                border_color=BORDER_ORANGE if is_active else BG_ROW,
            )
            rw["subtitle"].configure(text_color=ORANGE_GLOW if is_active else TEXT_MUTED)
            rw["run"].configure(text_color=ORANGE_MAIN if is_active else TEXT_DIM)

    def _resize_for_content(self, row_count: int):
        header_h = 70
        chips_h = 36
        filter_h = 32
        footer_h = 38
        row_h = 56
        new_h = header_h + chips_h + filter_h + (row_count * row_h) + footer_h + 16
        self._resize_window(min(new_h, self._H_EXPANDED))

    def _resize_window(self, height: int):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        pos_x = int(sw / 2 - self._W / 2)
        pos_y = int(sh * 0.22)
        self.geometry(f"{self._W}x{height}+{pos_x}+{pos_y}")

    # ── Keyboard Navigation Handlers ───────────────────────────────
    def _on_key_down(self, event):
        if not self._row_widgets:
            return "break"
        new_idx = (self.selected_index + 1) % len(self._row_widgets)
        self._select_row(new_idx)
        return "break"

    def _on_key_up(self, event):
        if not self._row_widgets:
            return "break"
        new_idx = (self.selected_index - 1) % len(self._row_widgets)
        self._select_row(new_idx)
        return "break"

    def _on_key_tab(self, event):
        if 0 <= self.selected_index < len(self._row_widgets):
            chosen = self._row_widgets[self.selected_index]["item"]["command"]
            self.search_var.set(chosen)
            self.search_entry.icursor("end")
            if not self.clear_btn.winfo_ismapped():
                self.clear_btn.pack(side="right", padx=(0, 6), before=self.think_btn)
            self._update_suggestions()
        return "break"

    def _on_key_return(self, event):
        self.on_execute()
        return "break"

    # ── Execution Pipeline Dispatch ────────────────────────────────
    def on_execute(self):
        typed = self.search_var.get().strip()

        if 0 <= self.selected_index < len(self._row_widgets):
            command = self._row_widgets[self.selected_index]["item"]["command"]
            if typed and not any(typed.lower() in self._row_widgets[self.selected_index]["item"][k].lower() for k in ("command", "title", "subtitle")):
                command = typed
        elif typed:
            command = typed
        else:
            return

        self._execute_command_text(command)

    def _execute_command_text(self, command: str):
        if self.is_processing or not command:
            return

        self.is_processing = True
        self._start_time = time.time()

        self._show_execution_view(command)

        is_vision = any(w in command.lower() for w in ("click", "ground", "save changes", "find on screen"))
        if is_vision:
            self.hide_spotlight()
            try:
                self.update()
            except Exception:
                pass

        if HAS_EVENT_BUS:
            threading.Thread(
                target=lambda: event_bus.emit(EVENT_TASK_START, {"command": command}),
                daemon=True,
            ).start()
        else:
            threading.Thread(target=self._mock_run, args=(command,), daemon=True).start()

    def _show_execution_view(self, command: str):
        if hasattr(self, "chips_frame"):
            self.chips_frame.pack_forget()
        self.filter_bar.pack_forget()
        self.suggestions_frame.pack_forget()
        self.footer.pack_forget()

        disp_cmd = command if len(command) <= 52 else command[:49] + "…"
        self.exec_title_lbl.configure(text=f"⚡ Executing: {disp_cmd}")
        self.exec_step_lbl.configure(text="🔒 Redacting PII from screenshot…")

        self.exec_drawer.pack(fill="both", expand=True, padx=16, pady=(6, 12))
        self.progress_bar.start()

        self._resize_window(self._H_EXEC)
        self.card.configure(border_color=ORANGE_MAIN, border_width=2)
        self.search_entry.configure(state="disabled")

        self._tick_timer()

    def _tick_timer(self):
        if not self.is_processing:
            return
        if self._start_time:
            elapsed = time.time() - self._start_time
            self.exec_timer_lbl.configure(text=f"⏱ {elapsed:.1f}s")
        self._timer_job = self.after(100, self._tick_timer)

    def _mock_run(self, query):
        mock_steps = [
            "🔒 Redacting PII from screenshot…",
            "🧠 Grounding target with VisionModel…",
            "🎯 Projecting AR bounding box…",
            "🖱 Executing smooth action…",
            "📧 Composing & dispatching email via Outlook COM…",
            "📊 Calculating ROI & logging…",
        ]
        for step in mock_steps:
            time.sleep(0.7)
            self._ui_events.put(("step", step))
        time.sleep(0.4)
        self._ui_events.put(("success", {"summary": query, "roi_msg": "Saved 3.0m | $0.01"}))

    # ── Event Bus Callbacks (Thread-Safe Queue) ─────────────────────
    def _on_progress(self, data):
        step_text = (data or {}).get("step", "")
        self._ui_events.put(("step", step_text))

    def _on_success(self, data):
        data = data or {}
        self._ui_events.put(("success", {
            "summary": data.get("summary", "Task complete"),
            "roi": data.get("roi_msg", "Saved 3.0m | $0.01"),
        }))

    def _on_failure(self, data):
        self._ui_events.put(("failure", (data or {}).get("error", "Unknown error")))

    def _drain_ui_events(self):
        while True:
            try:
                kind, data = self._ui_events.get_nowait()
            except queue.Empty:
                return
            if kind == "step":
                self._update_step(data)
            elif kind == "visual_thought":
                self._update_visual_thought(data)
            elif kind == "success":
                self._finish_success(data.get("summary", ""), data.get("roi", ""))
            elif kind == "failure":
                self._finish_failure(data)

    def _update_step(self, text):
        if text:
            self.exec_step_lbl.configure(text=f"● {text}")

    def _finish_success(self, summary, roi):
        self.progress_bar.stop()
        self.is_processing = False
        if self._timer_job:
            self.after_cancel(self._timer_job)

        self.card.configure(border_color="#10b981", border_width=2)
        self.search_entry.configure(state="normal")
        self.search_var.set("")
        if self.clear_btn.winfo_ismapped():
            self.clear_btn.pack_forget()

        self.exec_drawer.pack_forget()
        if hasattr(self, "chips_frame"):
            self.chips_frame.pack(fill="x", padx=16, pady=(0, 6))
        self.filter_bar.pack(fill="x", padx=18, pady=(2, 6))
        self.suggestions_frame.pack(fill="both", expand=True, padx=16, pady=(2, 6))
        self.footer.pack(fill="x", padx=16, pady=(0, 12))
        self._update_suggestions()

        self.hide_spotlight()

        # Pop floating HUD toast in Black & Orange
        self.after(200, lambda: _show_ctk_toast(self, f"✅ Done — {roi}", ORANGE_MAIN))
        self.after(1200, lambda: self.card.configure(border_color=BORDER_ORANGE, border_width=2))

    def _finish_failure(self, error):
        self.progress_bar.stop()
        self.is_processing = False
        if self._timer_job:
            self.after_cancel(self._timer_job)

        self.card.configure(border_color="#ef4444", border_width=2)
        self.search_entry.configure(state="normal")

        self.exec_drawer.pack_forget()
        if hasattr(self, "chips_frame"):
            self.chips_frame.pack(fill="x", padx=16, pady=(0, 6))
        self.filter_bar.pack(fill="x", padx=18, pady=(2, 6))
        self.suggestions_frame.pack(fill="both", expand=True, padx=16, pady=(2, 6))
        self.footer.pack(fill="x", padx=16, pady=(0, 12))
        self._update_suggestions()

        self.after(0, lambda: _show_ctk_toast(self, f"❌ Failed: {error[:42]}", "#ef4444"))
        self.after(1200, lambda: self.card.configure(border_color=BORDER_ORANGE, border_width=2))

    # ── Visibility & Hotkey Toggling ───────────────────────────────
    def request_toggle(self):
        with self._toggle_lock:
            self._toggle_pending = True

    def _poll_toggle(self):
        try:
            with self._toggle_lock:
                pending = self._toggle_pending
                self._toggle_pending = False
            if pending:
                self.toggle_spotlight()
            self._drain_ui_events()
        except Exception as exc:
            print(f">> [Hotkeys] Toggle failed: {exc}")
        try:
            self.after(45, self._poll_toggle)
        except Exception:
            pass

    def toggle_spotlight(self):
        if self.is_visible:
            self.hide_spotlight()
        else:
            self.show_spotlight()

    def hide_spotlight(self):
        self.withdraw()
        self.is_visible = False

    def show_spotlight(self):
        if sys.platform.startswith("win"):
            try:
                self.attributes("-transparentcolor", TRANSPARENT_KEY)
            except Exception:
                pass
        self.overrideredirect(True)
        self.deiconify()
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.98)
        self.lift()
        try:
            self.focus_force()
            self.search_entry.focus_set()
        except Exception:
            pass
        self.is_visible = True
        self._update_suggestions()
        self._flash_activation_pulse()


# ─── Floating HUD Toast Notification Helper (Black, Gray & Orange) ───
class _CtkToast(ctk.CTkToplevel):
    def __init__(self, parent, message, color):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)

        if sys.platform.startswith("win"):
            try:
                self.attributes("-transparentcolor", TRANSPARENT_KEY)
            except Exception:
                pass
        self.configure(fg_color=TRANSPARENT_KEY)

        sw = self.winfo_screenwidth()
        W, H = 450, 60
        self.geometry(f"{W}x{H}+{int(sw/2 - W/2)}+28")

        frame = ctk.CTkFrame(
            self,
            fg_color="#121215",
            corner_radius=16,
            border_width=2,
            border_color=color,
        )
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(
            frame,
            text=message,
            font=("Segoe UI", 14, "bold"),
            text_color="#fafafa",
        ).pack(expand=True)

        self._fade(0.0, 1)

    def _fade(self, a, direction):
        a = round(a + 0.1 * direction, 2)
        a = max(0.0, min(1.0, a))
        try:
            self.attributes("-alpha", a)
        except Exception:
            return
        if direction == 1 and a < 0.98:
            self.after(16, self._fade, a, 1)
        elif direction == 1:
            self.after(3400, self._fade, a, -1)
        elif a > 0.0:
            self.after(16, self._fade, a, -1)
        else:
            try:
                self.destroy()
            except Exception:
                pass


def _show_ctk_toast(parent, message, color=ORANGE_MAIN):
    _CtkToast(parent, message, color)


# ─── Global Hotkey Listener (Ctrl + Space) ────────────────────────
def hotkey_listener(app):
    """Global Ctrl+Space. Runs off the Tk thread and signals toggle request."""
    if _listen_win32_hotkey(app):
        return
    keyboard.add_hotkey("ctrl+space", app.request_toggle, suppress=False)
    print(">> [Hotkeys] Ctrl+Space hooked via keyboard listener.")
    keyboard.wait()


def _listen_win32_hotkey(app):
    if not sys.platform.startswith("win"):
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    MOD_CONTROL = 0x0002
    MOD_NOREPEAT = 0x4000
    VK_SPACE = 0x20
    WM_HOTKEY = 0x0312
    HOTKEY_ID = 1

    if not user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_NOREPEAT, VK_SPACE):
        err = ctypes.get_last_error()
        print(f">> [Hotkeys] RegisterHotKey failed (error {err}). Falling back to keyboard hook.")
        return False

    print(">> [Hotkeys] Ctrl+Space registered.")

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wParam", wintypes.WPARAM),
            ("lParam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt", POINT),
        ]

    msg = MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                app.request_toggle()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    finally:
        user32.UnregisterHotKey(None, HOTKEY_ID)
    return True


if __name__ == "__main__":
    app = SpotlightUI()
    t = threading.Thread(target=hotkey_listener, args=(app,), daemon=True)
    t.start()
    app.mainloop()
