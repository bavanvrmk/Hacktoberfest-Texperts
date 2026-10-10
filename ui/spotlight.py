"""
ui/spotlight.py — Neo-Brutalist Autonomous Command Palette
Built for Hacktoberfest Hack Day — Coimbatore 2026.
Features:
- Authentic Neo-Brutalist design language matching the yellow & cream design system
- Heavy 3px solid black borders and high-contrast typography
- Smooth open and close sliding fade animations
- Themed status header with retro brutalist pills (replacing generic loading glowbar)
- Keyboard-first navigation (Up/Down arrow nav, Tab auto-fill, Enter execute, Esc close)
- Curated presets including WhatsApp 9-step automation, screen reading, and Outlook feedback
- Real-time search filtering & category pills
- Multi-stage execution telemetry drawer with stopwatch timer and visual thinking notes
"""

import sys
import os
import queue
import threading
import time
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


try:
    from core.config_manager import get_setting
except ImportError:
    def get_setting(key, default=None):
        return default


# ─── Multi-Theme Palettes ──────────────────────────────────────────
THEMES = {
    "neo_brutalist": {
        "name": "Neo-Brutalist Sunshine",
        "bg_canvas": "#FFFDF0",
        "bg_card": "#FFFDF5",
        "bg_entry": "#FFFFFF",
        "bg_row": "#FFFFFF",
        "bg_row_hover": "#FFF9E6",
        "bg_row_active": "#FFE600",
        "border_color": "#000000",
        "accent": "#FFE600",
        "accent_text": "#000000",
        "coral": "#FF5757",
        "mint": "#22C55E",
        "sky": "#38BDF8",
        "lavender": "#C084FC",
        "text_main": "#000000",
        "text_muted": "#444444",
        "text_dim": "#666666",
    },
    "retro_ivory": {
        "name": "Classic Retro Cream & Black",
        "bg_canvas": "#F5EFEB",
        "bg_card": "#FAF6F0",
        "bg_entry": "#FFFFFF",
        "bg_row": "#FFFFFF",
        "bg_row_hover": "#F0EAE1",
        "bg_row_active": "#E6B800",
        "border_color": "#292524",
        "accent": "#E6B800",
        "accent_text": "#1C1917",
        "coral": "#E0533C",
        "mint": "#16A34A",
        "sky": "#0284C7",
        "lavender": "#9333EA",
        "text_main": "#1C1917",
        "text_muted": "#57534E",
        "text_dim": "#78716C",
    },
    "dark_brutalist": {
        "name": "Dark Obsidian Brutalist",
        "bg_canvas": "#0D0E12",
        "bg_card": "#16181F",
        "bg_entry": "#1E212B",
        "bg_row": "#1A1D26",
        "bg_row_hover": "#252936",
        "bg_row_active": "#CCFF00",
        "border_color": "#CCFF00",
        "accent": "#CCFF00",
        "accent_text": "#000000",
        "coral": "#FF3366",
        "mint": "#00FFCC",
        "sky": "#38BDF8",
        "lavender": "#B55FE6",
        "text_main": "#F4F4F6",
        "text_muted": "#A0A5B5",
        "text_dim": "#717688",
    },
}

TRANSPARENT_KEY = "#000001"  # Chroma key for rounded frameless window on Windows
BORDER_WIDTH    = 3          # Heavy 3px brutalist border

# Default tokens fallback
BG_CANVAS       = THEMES["neo_brutalist"]["bg_canvas"]
BG_CARD         = THEMES["neo_brutalist"]["bg_card"]
BG_ENTRY        = THEMES["neo_brutalist"]["bg_entry"]
BG_ROW          = THEMES["neo_brutalist"]["bg_row"]
BG_ROW_HOVER    = THEMES["neo_brutalist"]["bg_row_hover"]
BG_ROW_ACTIVE   = THEMES["neo_brutalist"]["bg_row_active"]
BORDER_BLACK    = THEMES["neo_brutalist"]["border_color"]
YELLOW_ACCENT   = THEMES["neo_brutalist"]["accent"]
CORAL_ACCENT    = THEMES["neo_brutalist"]["coral"]
MINT_ACCENT     = THEMES["neo_brutalist"]["mint"]
SKY_ACCENT      = THEMES["neo_brutalist"]["sky"]
LAVENDER_ACCENT = THEMES["neo_brutalist"]["lavender"]
TEXT_MAIN       = THEMES["neo_brutalist"]["text_main"]
TEXT_MUTED      = THEMES["neo_brutalist"]["text_muted"]
TEXT_DIM        = THEMES["neo_brutalist"]["text_dim"]


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
        "badge_color": MINT_ACCENT,
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
        "badge_color": YELLOW_ACCENT,
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
        "badge_color": SKY_ACCENT,
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
        "badge_color": MINT_ACCENT,
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
        "badge_color": YELLOW_ACCENT,
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
        "badge_color": MINT_ACCENT,
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
        "badge_color": YELLOW_ACCENT,
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
        "badge_color": CORAL_ACCENT,
        "keywords": ["click", "vision", "grounding", "button", "save", "qwen"],
    },
    {
        "id": "system_taskmgr",
        "category": "SYSTEM",
        "icon": "⚡",
        "title": "Inspect Desktop Performance & VRAM",
        "command": "Launch Task Manager",
        "subtitle": "Win32 Sandbox Process Monitor",
        "badge": "System",
        "badge_color": LAVENDER_ACCENT,
        "keywords": ["task", "manager", "system", "vram", "performance", "sandbox"],
    },
]

SUGGESTION_CHIPS = [
    ("💬 WhatsApp Pranav", "open whatsapp and search for pranav cceb and send hi"),
    ("👁 Summarize Screen", "read contents on the screen and summarize"),
    ("📧 Outlook Evaluator", "Send an email using outlook to jp_vedaj@cb.amrita.edu about how good my hackathon demo was"),
    ("🐦 Twitter / X", "Open Twitter"),
    ("📊 Live ROI", "Open Chrome and navigate to http://127.0.0.1:8000"),
]

CATEGORY_TABS = [
    ("ALL", "All Presets"),
    ("APPS", "💬 Apps"),
    ("VISION", "👁 Vision AI"),
    ("EMAIL", "📧 Email"),
    ("TELEMETRY", "📊 ROI"),
    ("SYSTEM", "⚙ System"),
]


class SpotlightUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ── Window Chrome & Framing ──────────────────────────────
        self.title("Shadow Automator — Spotlight")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)

        if sys.platform.startswith("win"):
            try:
                self.attributes("-transparentcolor", TRANSPARENT_KEY)
            except Exception:
                pass
        self.configure(fg_color=TRANSPARENT_KEY)
        ctk.set_appearance_mode("light")

        self._W = 840
        self._H_EXPANDED = 510
        self._H_EXEC     = 260
        self._HUD_W      = 540
        self._HUD_H      = 64
        self._current_h  = self._H_EXPANDED

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self._pos_x = int(sw / 2 - self._W / 2)
        self._pos_y = int(sh * 0.20)
        self._hud_x = int(sw / 2 - self._HUD_W / 2)
        self._hud_y = 24
        self.is_in_hud_mode = False
        self.active_theme_key = "neo_brutalist"
        self.current_theme = THEMES["neo_brutalist"]
        self.geometry(f"{self._W}x{self._H_EXPANDED}+{self._pos_x}+{self._pos_y}")

        # ── Main Floating Neo-Brutalist Card ──────────────────────
        self.card = ctk.CTkFrame(
            self,
            fg_color=self.current_theme["bg_card"],
            corner_radius=22,
            border_width=BORDER_WIDTH,
            border_color=self.current_theme["border_color"],
        )
        self.card.pack(fill="both", expand=True, padx=6, pady=6)

        # ── Compact Running Popup HUD Container (Top of Screen) ──
        self.hud_container = ctk.CTkFrame(self.card, fg_color="transparent")

        self.hud_status_badge = ctk.CTkLabel(
            self.hud_container,
            text="⚡ RUNNING",
            font=("Segoe UI", 11, "bold"),
            text_color=self.current_theme["accent_text"],
            fg_color=self.current_theme["accent"],
            corner_radius=10,
            padx=10,
            pady=4,
        )
        self.hud_status_badge.pack(side="left", padx=(12, 10))

        self.hud_text_box = ctk.CTkFrame(self.hud_container, fg_color="transparent")
        self.hud_text_box.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.hud_task_title = ctk.CTkLabel(
            self.hud_text_box,
            text="Task: Executing routine…",
            font=("Segoe UI", 12, "bold"),
            text_color=self.current_theme["text_main"],
            anchor="w",
        )
        self.hud_task_title.pack(fill="x", pady=(2, 0))

        self.hud_task_step = ctk.CTkLabel(
            self.hud_text_box,
            text="🔒 Grounding action on screen…",
            font=("Segoe UI", 10, "bold"),
            text_color=self.current_theme["text_muted"],
            anchor="w",
        )
        self.hud_task_step.pack(fill="x", pady=(0, 2))

        self.hud_timer_lbl = ctk.CTkLabel(
            self.hud_container,
            text="⏱ 0.0s",
            font=("JetBrains Mono", 11, "bold"),
            text_color=self.current_theme["accent_text"],
            fg_color=self.current_theme["accent"],
            corner_radius=8,
            padx=8,
            pady=3,
        )
        self.hud_timer_lbl.pack(side="right", padx=(4, 6))

        self.hud_cancel_btn = ctk.CTkButton(
            self.hud_container,
            text="✕",
            width=28,
            height=28,
            corner_radius=14,
            font=("Segoe UI", 11, "bold"),
            fg_color="transparent",
            hover_color=self.current_theme["bg_row_hover"],
            text_color=self.current_theme["text_main"],
            border_width=1.5,
            border_color=self.current_theme["border_color"],
            command=self._cancel_running_task,
        )
        self.hud_cancel_btn.pack(side="right", padx=(2, 10))

        # ── Themed Neo-Brutalist Top Status Header ────────────────
        self.top_header = ctk.CTkFrame(self.card, fg_color="transparent", height=32)
        self.top_header.pack(fill="x", padx=20, pady=(12, 6))

        self.title_badge = ctk.CTkLabel(
            self.top_header,
            text="★ SHADOW SPOTLIGHT ★",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_MAIN,
        )
        self.title_badge.pack(side="left")

        self.status_pill = ctk.CTkLabel(
            self.top_header,
            text="⚡ SYSTEM READY",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT_MAIN,
            fg_color=YELLOW_ACCENT,
            corner_radius=8,
            padx=10,
            pady=2,
        )
        self.status_pill.pack(side="right")

        # ── Neo-Brutalist Search Capsule Bar ──────────────────────
        self.capsule_bar = ctk.CTkFrame(
            self.card,
            fg_color=BG_ENTRY,
            corner_radius=16,
            height=50,
            border_width=2,
            border_color=BORDER_BLACK,
        )
        self.capsule_bar.pack(fill="x", padx=16, pady=(2, 8))
        self.capsule_bar.pack_propagate(False)

        # Left (+) Action Menu Pill Button (From Reference Image)
        self.plus_btn = ctk.CTkButton(
            self.capsule_bar,
            text="+",
            width=34,
            height=34,
            corner_radius=17,
            font=("Segoe UI", 18, "bold"),
            fg_color=YELLOW_ACCENT,
            hover_color="#FACC15",
            text_color=TEXT_MAIN,
            border_width=2,
            border_color=BORDER_BLACK,
            command=self._on_plus_click,
        )
        self.plus_btn.pack(side="left", padx=(8, 8))

        # Center Search Entry Field
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.capsule_bar,
            textvariable=self.search_var,
            height=42,
            font=("Segoe UI", 15, "bold"),
            placeholder_text="Ask anything, describe task, or launch routine…",
            placeholder_text_color=TEXT_MUTED,
            border_width=0,
            fg_color="transparent",
            text_color=TEXT_MAIN,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # Clear Query Button (✕)
        self.clear_btn = ctk.CTkButton(
            self.capsule_bar,
            text="✕",
            width=26,
            height=26,
            corner_radius=13,
            font=("Segoe UI", 11, "bold"),
            fg_color="#F3F4F6",
            border_width=1,
            border_color=BORDER_BLACK,
            hover_color="#E5E7EB",
            text_color=TEXT_MAIN,
            command=self._clear_search,
        )

        # "🧠 Think" Toggle Button
        self.think_mode = True
        self.think_btn = ctk.CTkButton(
            self.capsule_bar,
            text="🧠 Think",
            width=76,
            height=32,
            corner_radius=12,
            font=("Segoe UI", 11, "bold"),
            fg_color=YELLOW_ACCENT,
            border_width=2,
            border_color=BORDER_BLACK,
            hover_color="#FACC15",
            text_color=TEXT_MAIN,
            command=self._toggle_think_mode,
        )
        self.think_btn.pack(side="right", padx=(4, 6))

        # Dispatch Beacon Button (⚡ Run)
        self.beacon_btn = ctk.CTkButton(
            self.capsule_bar,
            text="⚡",
            width=36,
            height=36,
            corner_radius=18,
            font=("Segoe UI Emoji", 14, "bold"),
            fg_color=YELLOW_ACCENT,
            border_width=2,
            border_color=BORDER_BLACK,
            hover_color="#FACC15",
            text_color=TEXT_MAIN,
            command=self.on_execute,
        )
        self.beacon_btn.pack(side="right", padx=(4, 8))

        # ── Browse View Container (Holds chips, filter pills, and suggestions) ──
        self.browse_container = ctk.CTkFrame(self.card, fg_color="transparent")
        self.browse_container.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Suggestion Chips Bar ──────────────────────────────────
        self.chips_frame = ctk.CTkFrame(self.browse_container, fg_color="transparent", height=32)
        self.chips_frame.pack(fill="x", padx=16, pady=(0, 8))

        for chip_label, chip_cmd in SUGGESTION_CHIPS:
            cbtn = ctk.CTkButton(
                self.chips_frame,
                text=chip_label,
                font=("Segoe UI", 11, "bold"),
                height=26,
                corner_radius=13,
                fg_color="#FFFFFF",
                border_width=1.5,
                border_color=BORDER_BLACK,
                hover_color=YELLOW_ACCENT,
                text_color=TEXT_MAIN,
                command=lambda cmd=chip_cmd: self._on_chip_click(cmd),
            )
            cbtn.pack(side="left", padx=(0, 6))

        # ── Category Filter Bar ────────────────────────────────────
        self.filter_bar = ctk.CTkFrame(self.browse_container, fg_color="transparent", height=30)
        self.filter_bar.pack(fill="x", padx=18, pady=(0, 8))

        self.active_category = "ALL"
        self._filter_buttons = {}
        for cat_key, cat_label in CATEGORY_TABS:
            btn = ctk.CTkButton(
                self.filter_bar,
                text=cat_label,
                font=("Segoe UI", 11, "bold"),
                height=24,
                corner_radius=12,
                fg_color=YELLOW_ACCENT if cat_key == "ALL" else "#FFFFFF",
                border_width=1.5,
                border_color=BORDER_BLACK,
                hover_color=YELLOW_ACCENT,
                text_color=TEXT_MAIN,
                command=lambda k=cat_key: self._set_category(k),
            )
            btn.pack(side="left", padx=(0, 6))
            self._filter_buttons[cat_key] = btn

        # ── Suggestions Container ─────────────────────────────────
        self.suggestions_frame = ctk.CTkFrame(self.browse_container, fg_color="transparent")
        self.suggestions_frame.pack(fill="both", expand=True, padx=16, pady=(2, 6))

        # ── Execution Telemetry Drawer (Hidden until running) ──────
        self.exec_drawer = ctk.CTkFrame(
            self.card,
            fg_color="#FFFFFF",
            corner_radius=16,
            border_width=2,
            border_color=BORDER_BLACK,
        )

        self.exec_header_row = ctk.CTkFrame(self.exec_drawer, fg_color="transparent")
        self.exec_header_row.pack(fill="x", padx=16, pady=(12, 4))

        self.exec_title_lbl = ctk.CTkLabel(
            self.exec_header_row,
            text="⚡ Executing Autonomous Routine…",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_MAIN,
        )
        self.exec_title_lbl.pack(side="left")

        self.exec_timer_lbl = ctk.CTkLabel(
            self.exec_header_row,
            text="⏱ 0.0s",
            font=("Segoe UI", 12, "bold"),
            fg_color=YELLOW_ACCENT,
            corner_radius=6,
            padx=8,
            pady=2,
            text_color=TEXT_MAIN,
        )
        self.exec_timer_lbl.pack(side="right")

        # Step progression text
        self.exec_step_lbl = ctk.CTkLabel(
            self.exec_drawer,
            text="🔒 Grounding action on screen…",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_MAIN,
            anchor="w",
        )
        self.exec_step_lbl.pack(fill="x", padx=18, pady=(4, 6))

        # Visual Agent Reasoning Box
        self.visual_thought_card = ctk.CTkFrame(
            self.exec_drawer,
            fg_color="#FFFDF0",
            corner_radius=10,
            border_width=1.5,
            border_color=BORDER_BLACK,
        )
        self.visual_thought_card.pack(fill="x", padx=16, pady=(4, 8))

        self.visual_thought_header = ctk.CTkFrame(self.visual_thought_card, fg_color="transparent")
        self.visual_thought_header.pack(fill="x", padx=12, pady=(6, 2))

        self.visual_thought_title = ctk.CTkLabel(
            self.visual_thought_header,
            text="🧠 Visual Observation & Grounding",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT_MAIN,
        )
        self.visual_thought_title.pack(side="left")

        self.visual_delta_badge = ctk.CTkLabel(
            self.visual_thought_header,
            text="Screen Delta: 0.0%",
            font=("Segoe UI", 10, "bold"),
            text_color="#000",
            fg_color=MINT_ACCENT,
            corner_radius=6,
            padx=6,
            pady=1,
        )
        self.visual_delta_badge.pack(side="right")

        self.visual_thought_lbl = ctk.CTkLabel(
            self.visual_thought_card,
            text="UI state verified. Preparing next coordinate injection…",
            font=("Segoe UI", 11),
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=760,
            justify="left",
        )
        self.visual_thought_lbl.pack(fill="x", padx=12, pady=(2, 8))

        # ── Bottom Shortcut Helper Bar ────────────────────────────
        self.footer = ctk.CTkFrame(self.card, fg_color="transparent", height=28)
        self.footer.pack(fill="x", side="bottom", padx=20, pady=(4, 10))

        lbl_nav = ctk.CTkLabel(
            self.footer,
            text="↑↓ Navigate   •   Tab Auto-fill   •   ↵ Run   •   Esc Close",
            font=("Segoe UI", 10, "bold"),
            text_color=TEXT_MUTED,
        )
        lbl_nav.pack(side="left")

        lbl_info = ctk.CTkLabel(
            self.footer,
            text="100% Offline Qwen2.5-VL • Zero Egress",
            font=("Segoe UI", 10, "bold"),
            text_color=TEXT_MAIN,
        )
        lbl_info.pack(side="right")

        # ── State Machine ─────────────────────────────────────────
        self.is_visible = False
        self.is_processing = False
        self.selected_index = 0
        self._row_widgets = []
        self._toggle_pending = False
        self._start_time = None
        self._timer_job = None
        self._is_animating = False

        # Event queue
        self._ui_events = queue.Queue()

        # Keyboard bindings
        self.search_entry.bind("<KeyRelease>", self._on_key_release)
        self.search_entry.bind("<Down>", self._on_key_down)
        self.search_entry.bind("<Up>", self._on_key_up)
        self.search_entry.bind("<Tab>", self._on_key_tab)
        self.search_entry.bind("<Return>", self._on_key_return)
        self.search_entry.bind("<Escape>", lambda e: self.hide_spotlight())

        # Bind event bus
        if HAS_EVENT_BUS:
            event_bus.subscribe(EVENT_PROGRESS, self._on_progress)
            event_bus.subscribe(EVENT_TASK_SUCCESS, self._on_success)
            event_bus.subscribe(EVENT_TASK_FAILED, self._on_failure)
            event_bus.subscribe(EVENT_VISUAL_THOUGHT, self._on_visual_thought)

        self._poll_toggle()
        self._reload_theme_from_settings()
        self.withdraw()

    # ── Theme Management ──────────────────────────────────────────
    def apply_theme(self, theme_key: str):
        if theme_key not in THEMES:
            theme_key = "neo_brutalist"
        self.active_theme_key = theme_key
        t = THEMES[theme_key]
        self.current_theme = t

        # Update card container
        self.card.configure(fg_color=t["bg_card"], border_color=t["border_color"])

        # Update top header
        self.title_badge.configure(text_color=t["text_main"])
        self.status_pill.configure(fg_color=t["accent"], text_color=t["accent_text"])

        # Update capsule search bar
        self.capsule_bar.configure(fg_color=t["bg_entry"], border_color=t["border_color"])
        self.plus_btn.configure(
            fg_color=t["accent"],
            text_color=t["accent_text"],
            border_color=t["border_color"],
            hover_color=t["bg_row_hover"],
        )
        self.search_entry.configure(
            text_color=t["text_main"],
            placeholder_text_color=t["text_muted"],
        )
        self.clear_btn.configure(
            fg_color=t["bg_card"],
            text_color=t["text_main"],
            border_color=t["border_color"],
        )
        self.think_btn.configure(
            fg_color=t["accent"] if self.think_mode else t["bg_entry"],
            text_color=t["accent_text"] if self.think_mode else t["text_muted"],
            border_color=t["border_color"],
        )
        self.beacon_btn.configure(
            fg_color=t["accent"],
            text_color=t["accent_text"],
            border_color=t["border_color"],
        )

        # Update chips
        for child in self.chips_frame.winfo_children():
            if isinstance(child, ctk.CTkButton):
                child.configure(
                    fg_color=t["bg_card"],
                    border_color=t["border_color"],
                    text_color=t["text_main"],
                    hover_color=t["accent"],
                )

        # Update category filters
        for key, btn in self._filter_buttons.items():
            is_active = (key == self.active_category)
            btn.configure(
                fg_color=t["accent"] if is_active else t["bg_card"],
                border_color=t["border_color"],
                text_color=t["accent_text"] if is_active else t["text_main"],
                hover_color=t["accent"],
            )

        # Update HUD popup widgets
        self.hud_container.configure(fg_color=t["bg_card"])
        self.hud_status_badge.configure(fg_color=t["accent"], text_color=t["accent_text"])
        self.hud_task_title.configure(text_color=t["text_main"])
        self.hud_task_step.configure(text_color=t["text_muted"])
        self.hud_timer_lbl.configure(fg_color=t["accent"], text_color=t["accent_text"])
        self.hud_cancel_btn.configure(
            fg_color=t["bg_card"],
            border_color=t["border_color"],
            text_color=t["text_main"],
            hover_color=t["bg_row_hover"],
        )

        # Update footer labels
        for child in self.footer.winfo_children():
            if isinstance(child, ctk.CTkLabel):
                child.configure(text_color=t["text_main"])

        # Update suggestions list
        self._update_suggestions()

    def _reload_theme_from_settings(self):
        try:
            from core.config_manager import get_setting
            theme_key = get_setting("spotlight_theme", "neo_brutalist")
            if theme_key != self.active_theme_key:
                self.apply_theme(theme_key)
        except Exception:
            pass

    # ── Category Filtering ─────────────────────────────────────────
    def _set_category(self, category_key: str):
        self.active_category = category_key
        t = self.current_theme
        for key, btn in self._filter_buttons.items():
            if key == category_key:
                btn.configure(
                    fg_color=t["accent"],
                    text_color=t["accent_text"],
                    border_color=t["border_color"],
                )
            else:
                btn.configure(
                    fg_color=t["bg_card"],
                    text_color=t["text_main"],
                    border_color=t["border_color"],
                )
        self._update_suggestions()

    def _on_plus_click(self):
        cats = [k for k, _ in CATEGORY_TABS]
        idx = (cats.index(self.active_category) + 1) % len(cats)
        self._set_category(cats[idx])

    def _toggle_think_mode(self):
        self.think_mode = not self.think_mode
        t = self.current_theme
        if self.think_mode:
            self.think_btn.configure(
                fg_color=t["accent"],
                text_color=t["accent_text"],
                border_color=t["border_color"],
            )
        else:
            self.think_btn.configure(
                fg_color=t["bg_entry"],
                text_color=t["text_muted"],
                border_color=t["border_color"],
            )

    def _on_chip_click(self, cmd: str):
        self.search_var.set(cmd)
        self._execute_command_text(cmd)

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

    # ── Suggestions Rendering ──────────────────────────────────────
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

        # Clear existing rows
        for w in self.suggestions_frame.winfo_children():
            w.destroy()
        self._row_widgets = []
        self.selected_index = 0

        if not filtered and query:
            # Custom command fallback item
            custom_item = {
                "id": "custom_run",
                "category": "CUSTOM",
                "icon": "⚡",
                "title": f"Execute Intent: \"{self.search_var.get().strip()}\"",
                "command": self.search_var.get().strip(),
                "subtitle": "Deconstruct customer prompt & run local automation pipeline",
                "badge": "Custom",
                "badge_color": self.current_theme["accent"],
            }
            filtered = [custom_item]

        t = self.current_theme
        for idx, item in enumerate(filtered[:5]):
            is_first = (idx == 0)
            row_frame = ctk.CTkFrame(
                self.suggestions_frame,
                fg_color=t["bg_row_active"] if is_first else t["bg_row"],
                corner_radius=12,
                height=52,
                border_width=2 if is_first else 1.5,
                border_color=t["border_color"],
            )
            row_frame.pack(fill="x", pady=2)
            row_frame.pack_propagate(False)

            # Left Icon
            icon_lbl = ctk.CTkLabel(
                row_frame,
                text=item["icon"],
                font=("Segoe UI Emoji", 16),
                width=34,
            )
            icon_lbl.pack(side="left", padx=(10, 6))

            # Texts block
            text_block = ctk.CTkFrame(row_frame, fg_color="transparent")
            text_block.pack(side="left", fill="both", expand=True, pady=6)

            title_lbl = ctk.CTkLabel(
                text_block,
                text=item["title"],
                font=("Segoe UI", 13, "bold"),
                text_color=t["accent_text"] if is_first else t["text_main"],
                anchor="w",
            )
            title_lbl.pack(fill="x")

            subtitle_lbl = ctk.CTkLabel(
                text_block,
                text=item["subtitle"],
                font=("Segoe UI", 11),
                text_color=t["text_muted"],
                anchor="w",
            )
            subtitle_lbl.pack(fill="x")

            # Right badge & run tag
            right_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            right_frame.pack(side="right", padx=(8, 12))

            badge_lbl = ctk.CTkLabel(
                right_frame,
                text=item.get("badge", "Action"),
                font=("Segoe UI", 10, "bold"),
                fg_color=item.get("badge_color", t["accent"]),
                text_color=t["accent_text"],
                corner_radius=6,
                padx=8,
                pady=1,
            )
            badge_lbl.pack(side="left", padx=(0, 8))

            run_lbl = ctk.CTkLabel(
                right_frame,
                text="↵ RUN",
                font=("Segoe UI", 11, "bold"),
                text_color=t["accent_text"] if is_first else t["text_main"],
            )
            run_lbl.pack(side="right")

            # Click binding
            for widget in (row_frame, icon_lbl, text_block, title_lbl, subtitle_lbl, right_frame, badge_lbl, run_lbl):
                widget.bind("<Button-1>", lambda e, c=item["command"]: self._execute_command_text(c))
                widget.bind("<Enter>", lambda e, i=idx: self._select_row(i))

            self._row_widgets.append({
                "row": row_frame,
                "title": title_lbl,
                "subtitle": subtitle_lbl,
                "run": run_lbl,
                "item": item,
            })

        self._resize_for_content(len(self._row_widgets))

    def _select_row(self, index: int):
        if not self._row_widgets:
            return
        t = self.current_theme
        self.selected_index = max(0, min(index, len(self._row_widgets) - 1))
        for idx, rw in enumerate(self._row_widgets):
            is_active = (idx == self.selected_index)
            rw["row"].configure(
                fg_color=t["bg_row_active"] if is_active else t["bg_row"],
                border_color=t["border_color"],
                border_width=2 if is_active else 1.5,
            )
            rw["title"].configure(text_color=t["accent_text"] if is_active else t["text_main"])
            rw["run"].configure(text_color=t["accent_text"] if is_active else t["text_main"])

    def _resize_for_content(self, row_count: int):
        header_h = 76
        chips_h = 36
        filter_h = 34
        footer_h = 38
        row_h = 58
        new_h = header_h + chips_h + filter_h + (row_count * row_h) + footer_h + 16
        self._resize_window(min(new_h, self._H_EXPANDED))

    def _resize_window(self, height: int):
        self._current_h = height
        sw = self.winfo_screenwidth()
        pos_x = int(sw / 2 - self._W / 2)
        self.geometry(f"{self._W}x{height}+{pos_x}+{self._pos_y}")

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

        if HAS_EVENT_BUS:
            threading.Thread(
                target=lambda: event_bus.emit(EVENT_TASK_START, {"command": command}),
                daemon=True,
            ).start()
        else:
            threading.Thread(target=self._mock_run, args=(command,), daemon=True).start()

    def _show_execution_view(self, command: str):
        t = self.current_theme
        disp_cmd = command if len(command) <= 42 else command[:39] + "…"

        self.is_in_hud_mode = True
        self.search_entry.configure(state="disabled")

        # Configure Running HUD widgets
        self.hud_task_title.configure(text=f"Task: {disp_cmd}", text_color=t["text_main"])
        self.hud_task_step.configure(text="🔒 Grounding action on screen…", text_color=t["text_muted"])
        self.hud_status_badge.configure(text="⚡ RUNNING", fg_color=t["accent"], text_color=t["accent_text"])
        self.hud_timer_lbl.configure(text="⏱ 0.0s", fg_color=t["accent"], text_color=t["accent_text"])

        # Also configure full exec drawer labels
        self.exec_title_lbl.configure(text=f"⚡ Executing: {disp_cmd}", text_color=t["text_main"])
        self.exec_step_lbl.configure(text="🔒 Grounding action on screen…", text_color=t["text_main"])
        self.status_pill.configure(text="🔥 EXECUTING ROUTINE", fg_color=t["accent"], text_color=t["accent_text"])

        # Hide full modal views
        self.top_header.pack_forget()
        self.capsule_bar.pack_forget()
        self.browse_container.pack_forget()
        self.footer.pack_forget()
        self.exec_drawer.pack_forget()

        # Mount HUD container inside card
        self.hud_container.pack(fill="both", expand=True, padx=4, pady=4)

        # Smooth conversion animation to small running popup at top of screen
        self._animate_geometry_transition(to_hud=True)

        self._tick_timer()

    def _cancel_running_task(self):
        self.is_processing = False
        t = self.current_theme
        self.hud_status_badge.configure(text="⏹ STOPPED", fg_color=t["coral"], text_color="#fff")
        self.hud_task_step.configure(text="Operation stopped by user.")
        self.after(500, self._restore_search_view)

    def _animate_geometry_transition(self, to_hud: bool, on_complete=None):
        """
        Smooth conversion animation between:
        - Center expanded modal: (self._W, self._H_EXPANDED, self._pos_x, self._pos_y)
        - Top running popup HUD: (self._HUD_W, self._HUD_H, self._hud_x, self._hud_y)
        """
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        target_w = self._HUD_W if to_hud else self._W
        target_h = self._HUD_H if to_hud else self._H_EXPANDED
        target_x = int(sw / 2 - target_w / 2)
        target_y = self._hud_y if to_hud else int(sh * 0.20)

        try:
            start_w = self.winfo_width()
            start_h = self.winfo_height()
            start_x = self.winfo_x()
            start_y = self.winfo_y()
        except Exception:
            start_w = self._W if to_hud else self._HUD_W
            start_h = self._H_EXPANDED if to_hud else self._HUD_H
            start_x = self._pos_x if to_hud else target_x
            start_y = self._pos_y if to_hud else target_y

        if start_w < 50 or start_h < 30:
            start_w = self._W if to_hud else self._HUD_W
            start_h = self._H_EXPANDED if to_hud else self._HUD_H
            start_x = self._pos_x if to_hud else target_x
            start_y = self._pos_y if to_hud else target_y

        frames = 10
        delay_ms = 12

        def _step(i=0):
            if i <= frames:
                t = i / frames
                # Cubic ease-out curve
                ease = 1.0 - (1.0 - t) ** 3
                cur_w = int(start_w + (target_w - start_w) * ease)
                cur_h = int(start_h + (target_h - start_h) * ease)
                cur_x = int(start_x + (target_x - start_x) * ease)
                cur_y = int(start_y + (target_y - start_y) * ease)
                try:
                    self.geometry(f"{cur_w}x{cur_h}+{cur_x}+{cur_y}")
                except Exception:
                    pass
                if i < frames:
                    self.after(delay_ms, lambda: _step(i + 1))
                else:
                    try:
                        self.geometry(f"{target_w}x{target_h}+{target_x}+{target_y}")
                    except Exception:
                        pass
                    if on_complete:
                        on_complete()

        _step(0)

    def _tick_timer(self):
        if not self.is_processing:
            return
        if self._start_time:
            elapsed = time.time() - self._start_time
            lbl_text = f"⏱ {elapsed:.1f}s"
            self.exec_timer_lbl.configure(text=lbl_text)
            self.hud_timer_lbl.configure(text=lbl_text)
        self._timer_job = self.after(100, self._tick_timer)

    def _mock_run(self, query):
        mock_steps = [
            "🔒 Grounding action on screen…",
            "🖱 Injecting sandboxed click action…",
            "📊 Verifying post-action visual state…",
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

    def _on_visual_thought(self, data):
        self._ui_events.put(("visual_thought", data))

    def _drain_ui_events(self):
        while True:
            try:
                kind, data = self._ui_events.get_nowait()
            except queue.Empty:
                return

            if kind == "step":
                self.exec_step_lbl.configure(text=data)
                self.hud_task_step.configure(text=str(data)[:55])
            elif kind == "visual_thought":
                thought = (data or {}).get("thought", "")
                diff_pct = (data or {}).get("diff_pct", 0.0)
                if thought:
                    self.visual_thought_lbl.configure(text=f"Thought: {thought}")
                    self.visual_delta_badge.configure(text=f"Delta: {diff_pct}%")
                    self.hud_task_step.configure(text=f"🧠 {thought[:48]}…")
            elif kind == "success":
                self._handle_pipeline_success(data)
            elif kind == "failure":
                self._handle_pipeline_failure(data)

    def _handle_pipeline_success(self, data):
        self.is_processing = False
        t = self.current_theme
        summary = data.get("summary", "Task finished")
        roi = data.get("roi", "Saved 3.0m | $0.01")

        self.exec_step_lbl.configure(text=f"✅ {summary}")
        self.status_pill.configure(text="✅ COMPLETED", fg_color=t["mint"], text_color="#000")

        # Update running popup HUD at top of screen
        self.hud_status_badge.configure(text="✅ DONE", fg_color=t["mint"], text_color="#000")
        self.hud_task_title.configure(text=f"✅ {summary[:38]}")
        self.hud_task_step.configure(text=f"🎉 {roi}")

        self.after(1800, self._restore_search_view)
        _show_ctk_toast(self, f"🎉 Routine Finished: {summary} • {roi}", color=t["mint"])

    def _handle_pipeline_failure(self, error_msg):
        self.is_processing = False
        t = self.current_theme
        self.exec_step_lbl.configure(text=f"❌ Failed: {error_msg}")
        self.status_pill.configure(text="❌ FAILED", fg_color=t["coral"], text_color="#fff")

        # Update running popup HUD at top of screen
        self.hud_status_badge.configure(text="❌ ERROR", fg_color=t["coral"], text_color="#fff")
        self.hud_task_title.configure(text="Automation Routine Error")
        self.hud_task_step.configure(text=str(error_msg)[:48])

        self.after(2200, self._restore_search_view)
        _show_ctk_toast(self, f"⚠ Automation Error: {error_msg}", color=t["coral"])

    def _restore_search_view(self):
        if not self.is_in_hud_mode:
            return
        self._animate_geometry_transition(to_hud=False, on_complete=self._finish_restore_search_view)

    def _finish_restore_search_view(self):
        self.is_in_hud_mode = False
        t = self.current_theme

        self.hud_container.pack_forget()
        self.exec_drawer.pack_forget()

        self.top_header.pack(fill="x", padx=20, pady=(12, 6))
        self.capsule_bar.pack(fill="x", padx=16, pady=(2, 8))
        self.footer.pack(fill="x", side="bottom", padx=20, pady=(4, 10))
        self.browse_container.pack(fill="both", expand=True, padx=0, pady=0)

        self.search_entry.configure(state="normal")
        self.status_pill.configure(text="⚡ SYSTEM READY", fg_color=t["accent"], text_color=t["accent_text"])
        self._update_suggestions()

    # ── Hotkey Poller & Toggle ─────────────────────────────────────
    def request_toggle(self):
        self._toggle_pending = True

    def _poll_toggle(self):
        try:
            if self._toggle_pending:
                self._toggle_pending = False
                self.toggle_spotlight()
            self._drain_ui_events()
        except Exception as exc:
            print(f">> [Hotkeys] Toggle failed: {exc}")
        try:
            self.after(40, self._poll_toggle)
        except Exception:
            pass

    def toggle_spotlight(self):
        if self.is_visible:
            self.hide_spotlight()
        else:
            self.show_spotlight()

    # ── Open & Close Animations ────────────────────────────────────
    def show_spotlight(self):
        """Smooth slide-in and opacity fade-in animation."""
        if self.is_visible or self._is_animating:
            return

        self._reload_theme_from_settings()

        if self.is_in_hud_mode:
            self.overrideredirect(True)
            self.deiconify()
            self.attributes("-topmost", True)
            self.attributes("-alpha", 0.98)
            self.lift()
            self.is_visible = True
            return

        self._is_animating = True
        self.overrideredirect(True)
        self.deiconify()
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)
        self.lift()

        # Start slightly higher for smooth slide down
        start_y = self._pos_y - 18
        self.geometry(f"{self._W}x{self._current_h}+{self._pos_x}+{start_y}")

        frames = 8
        delay_ms = 14

        def _step(i=0):
            if i <= frames:
                # Easing curve
                t = i / frames
                alpha = round(0.98 * t, 3)
                cur_y = int(start_y + (self._pos_y - start_y) * (1 - (1 - t) ** 2))
                try:
                    self.attributes("-alpha", alpha)
                    self.geometry(f"{self._W}x{self._current_h}+{self._pos_x}+{cur_y}")
                except Exception:
                    pass
                self.after(delay_ms, _step, i + 1)
            else:
                self.attributes("-alpha", 0.98)
                self.geometry(f"{self._W}x{self._current_h}+{self._pos_x}+{self._pos_y}")
                self.is_visible = True
                self._is_animating = False
                try:
                    self.focus_force()
                    self.search_entry.focus_set()
                except Exception:
                    pass
                self._update_suggestions()

        _step(0)

    def hide_spotlight(self):
        """Smooth slide-up and opacity fade-out animation."""
        if self.is_in_hud_mode:
            # Running HUD popup remains visible on top of screen while task is running
            return

        if not self.is_visible or self._is_animating:
            self.withdraw()
            self.is_visible = False
            return

        self._is_animating = True
        start_y = self._pos_y
        target_y = self._pos_y - 14

        frames = 7
        delay_ms = 12

        def _step(i=0):
            if i <= frames:
                t = i / frames
                alpha = round(0.98 * (1 - t), 3)
                cur_y = int(start_y + (target_y - start_y) * t)
                try:
                    self.attributes("-alpha", alpha)
                    self.geometry(f"{self._W}x{self._current_h}+{self._pos_x}+{cur_y}")
                except Exception:
                    pass
                self.after(delay_ms, _step, i + 1)
            else:
                self.withdraw()
                self.is_visible = False
                self._is_animating = False

        _step(0)


# ─── Floating Toast Notification Helper ───────────────────────────
class _CtkToast(ctk.CTkToplevel):
    def __init__(self, parent, message, color=YELLOW_ACCENT):
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
        W, H = 460, 56
        self.geometry(f"{W}x{H}+{int(sw/2 - W/2)}+26")

        frame = ctk.CTkFrame(
            self,
            fg_color=color,
            corner_radius=14,
            border_width=2.5,
            border_color=BORDER_BLACK,
        )
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(
            frame,
            text=message,
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_MAIN,
        ).pack(expand=True)

        self._fade(0.0, 1)

    def _fade(self, a, direction):
        a = round(a + 0.12 * direction, 2)
        a = max(0.0, min(1.0, a))
        try:
            self.attributes("-alpha", a)
        except Exception:
            return
        if direction == 1 and a < 0.98:
            self.after(16, self._fade, a, 1)
        elif direction == 1:
            self.after(3000, self._fade, a, -1)
        elif a > 0.0:
            self.after(16, self._fade, a, -1)
        else:
            try:
                self.destroy()
            except Exception:
                pass


def _show_ctk_toast(parent, message, color=YELLOW_ACCENT):
    _CtkToast(parent, message, color)


# ─── Global Hotkey Listener (Ctrl + Space) ────────────────────────
def hotkey_listener(app):
    """Global Ctrl+Space listener."""
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
