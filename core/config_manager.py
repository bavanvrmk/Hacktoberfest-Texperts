"""
Configuration Manager for Shadow Automator.
Handles persistent user preferences, LLM server URLs, vision settings,
mouse speed, and theme configurations in config/settings.json.
"""

import os
import json

CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config"))
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "llama_server_url": "http://127.0.0.1:8080/v1",
    "vision_model_name": "Qwen2.5-VL-3B-Instruct (Q4_K_M)",
    "temperature": 0.1,
    "max_tokens": 256,
    "mouse_speed": 0.35,
    "action_delay": 0.3,
    "pii_redaction_enabled": True,
    "visual_thinking_enabled": True,
    "spotlight_theme": "neo_brutalist",
    "spotlight_hotkey": "ctrl+space",
    "auto_refresh_interval": 3000,
    "air_gapped_mode": True
}


def load_settings() -> dict:
    """Loads current settings from JSON file, merging with defaults."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        _write_file(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        settings = dict(DEFAULT_SETTINGS)
        settings.update(data)
        return settings
    except Exception as exc:
        print(f"[Config] Error loading settings ({exc}), using defaults.")
        return dict(DEFAULT_SETTINGS)


def _write_file(data: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_settings(new_settings: dict) -> dict:
    """Saves updated settings to config/settings.json."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    current = dict(DEFAULT_SETTINGS)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                current.update(json.load(f))
        except Exception:
            pass
    current.update(new_settings)
    _write_file(current)
    return current


def get_setting(key: str, default=None):
    """Retrieves a specific configuration value."""
    settings = load_settings()
    return settings.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))
