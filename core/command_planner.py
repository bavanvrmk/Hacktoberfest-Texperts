"""
Turn a natural-language command into an ordered list of automation steps.
"""

import re

from core.windows_launcher import classify_command


_SPLIT = re.compile(r"\s+(?:and then|then)\s+|\s+and\s+", re.IGNORECASE)
_CLOSE = re.compile(r"^(?:please\s+)?(?:close|quit|exit)\s+(?:the\s+)?(.+)$", re.IGNORECASE)
_TYPE = re.compile(r"^(?:please\s+)?type\s+[\"']?(.*?)[\"']?$", re.IGNORECASE)
_HOTKEY = re.compile(r"^(?:please\s+)?(?:press|hit)\s+(.+)$", re.IGNORECASE)
_GOTO = re.compile(r"^(?:please\s+)?(?:go to|visit|browse|navigate to)\s+(.+)$", re.IGNORECASE)
_CLICK = re.compile(r"^(?:please\s+)?(?:click|tap|select)\s+(?:on\s+)?(?:the\s+)?(.+)$", re.IGNORECASE)
_PLAY = re.compile(r"^(?:please\s+)?play\s+(.+)$", re.IGNORECASE)
_RERUN = re.compile(r"^(?:please\s+)?(?:rerun|run workflow)\s+(.+)$", re.IGNORECASE)


def plan_command(command: str):
    """
    Return a list of steps: {"action": str, "target": str}.
    Actions: launch_app, open_file, close_app, type, hotkey, click, rerun.
    """
    text = " ".join((command or "").strip().split())
    if not text:
        return []

    rerun = _RERUN.match(text)
    if rerun:
        return [{"action": "rerun", "target": rerun.group(1).strip()}]

    steps = []
    for clause in _SPLIT.split(text):
        clause = clause.strip(" .")
        if not clause:
            continue
        steps.extend(_plan_clause(clause))
    return steps


def _plan_clause(clause: str):
    closed = _CLOSE.match(clause)
    if closed:
        return [{"action": "close_app", "target": closed.group(1).strip()}]

    typed = _TYPE.match(clause)
    if typed:
        return [{"action": "type", "target": typed.group(1).strip()}]

    hotkey = _HOTKEY.match(clause)
    if hotkey:
        return [{"action": "hotkey", "target": hotkey.group(1).strip()}]

    opened = _GOTO.match(clause)
    if opened:
        return [
            {"action": "type", "target": opened.group(1).strip()},
            {"action": "hotkey", "target": "enter"},
        ]

    played = _PLAY.match(clause)
    if played:
        return [{"action": "click", "target": played.group(1).strip()}]

    clicked = _CLICK.match(clause)
    if clicked:
        return [{"action": "click", "target": clicked.group(1).strip()}]

    intent = classify_command(clause)
    if intent:
        kind, target = intent
        action = "launch_app" if kind == "app" else "open_file"
        return [{"action": action, "target": target}]

    return [{"action": "click", "target": clause}]
