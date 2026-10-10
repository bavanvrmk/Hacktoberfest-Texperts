"""
Turn a natural-language command into an ordered list of automation steps.
"""

import json
import re

from core.windows_launcher import classify_command


_SPLIT = re.compile(r"\s+(?:and then|then)\s+|\s+and\s+", re.IGNORECASE)
_CLOSE = re.compile(r"^(?:please\s+)?(?:close|quit|exit)\s+(?:the\s+)?(.+)$", re.IGNORECASE)
_TYPE = re.compile(r"^(?:please\s+)?type\s+[\"']?(.*?)[\"']?$", re.IGNORECASE)
_WRITE = re.compile(r"^(?:please\s+)?(?:write|writa|compose|draft)\s+(.+)$", re.IGNORECASE)
_CREATE_TEXT = re.compile(r"create\s+(?:a\s+)?(?:new\s+)?text\s+file", re.IGNORECASE)
_UI_TARGET = re.compile(r"\b(tab|button|menu|icon|checkbox)\b", re.IGNORECASE)
_HOTKEY = re.compile(r"^(?:please\s+)?(?:press|hit)\s+(.+)$", re.IGNORECASE)
_GOTO = re.compile(r"^(?:please\s+)?(?:go to|visit|browse|navigate to)\s+(.+)$", re.IGNORECASE)
_CLICK = re.compile(r"^(?:please\s+)?(?:click|tap|select)\s+(?:on\s+)?(?:the\s+)?(.+)$", re.IGNORECASE)
_PLAY = re.compile(r"^(?:please\s+)?play\s+(.+)$", re.IGNORECASE)
_RERUN = re.compile(r"^(?:please\s+)?(?:rerun|run workflow)\s+(.+)$", re.IGNORECASE)
_SEND_EMAIL = re.compile(
    r"^(?:please\s+)?(?:send|compose|draft|write)\s+(?:an?\s+)?(?:email|mail|message)\s+"
    r"(?:using\s+(?:outlook|gmail|mail)\s+)?"
    r"(?:to\s+)?(\S+@\S+\.\S+)\s*(.*?)$",
    re.IGNORECASE,
)
_EMAIL_ADDR = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_APP_ALIASES = {
    "vscode": "Visual Studio Code",
    "vscoed": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "whatsapp": "WhatsApp",
    "whats app": "WhatsApp",
    "watsapp": "WhatsApp",
}
_ALLOWED = {
    "launch_app", "open_url", "open_file", "close_app",
    "click", "type", "hotkey", "wait", "scroll",
    "generate", "rerun", "send_email", "verify_visual",
    "summarize_screen"
}


def plan_command(command: str):
    """
    Return a list of steps: {"action": str, "target": str}.
    Actions: launch_app, open_file, close_app, type, hotkey, click, rerun, summarize_screen.
    """
    text = " ".join((command or "").strip().split())
    if not text:
        return []

    rerun = _RERUN.match(text)
    if rerun:
        return [{"action": "rerun", "target": rerun.group(1).strip()}]

    # Direct screen summarization intent
    if any(k in text.lower() for k in ("summarize screen", "read screen", "summarize contents on screen", "read contents on the screen", "what is on screen", "what's on screen", "screen summary")):
        return [{"action": "summarize_screen", "target": text, "description": "Read visible screen contents and provide AI summary"}]

    # Email commands should NOT be split on "and" — the full sentence is the intent
    email = _SEND_EMAIL.match(text)
    if email:
        return [{"action": "send_email", "target": text}]

    # Also catch any command containing an email address + "send/email/mail"
    if _EMAIL_ADDR.search(text) and re.search(r"\b(?:send|email|mail|message)\b", text, re.IGNORECASE):
        return [{"action": "send_email", "target": text}]

    alias = _APP_ALIASES.get(text.lower())
    if alias:
        return [{"action": "launch_app", "target": alias}]

    steps = []
    for clause in _SPLIT.split(text):
        clause = clause.strip(" .")
        if not clause:
            continue
        steps.extend(_plan_clause(clause))
    return steps


def needs_model(command: str, steps) -> bool:
    """
    True whenever the user's input expresses a workflow, conversation,
    multi-step goal, or complex intent that requires model reasoning.
    """
    text = " ".join((command or "").strip().split())
    if not text:
        return False
    words = text.split()

    # Fast path ONLY for single, atomic, unambiguous system commands
    # e.g., "calc", "notepad", "launch task manager", "close chrome", "ctrl+c"
    if len(words) <= 3 and len(steps) == 1 and steps[0]["action"] in ("launch_app", "open_file", "close_app", "hotkey", "rerun"):
        if not any(w in text.lower() for w in ("and", "then", "search", "send", "type", "summarize", "read", "chat", "msg", "click", "find")):
            return False

    # Any natural language goal or multi-step command MUST be processed semantically by the model
    return True


def compile_customer_intent_workflow(command: str, complete_fn) -> list:
    """
    Compiles ANY customer intent into an executable structured JSON workflow
    using the local LLM model without taking conversational text literally.
    """
    prompt = (
        "You are an Autonomous Desktop Automation Agent compiler.\n"
        f"Customer Request: \"{command}\"\n\n"
        "Deconstruct this customer intent into an ordered, executable JSON list of steps.\n"
        "Allowed action types:\n"
        "- launch_app: target is app name (e.g. 'WhatsApp', 'Notepad')\n"
        "- open_url: target is a full URL or web address to open in default browser (e.g. 'http://127.0.0.1:8000', 'https://google.com')\n"
        "- click: target is description of UI element to locate visually and click (e.g. 'Search bar', 'Send button')\n"
        "- type: target is short string to type (e.g. 'pranav cceb', 'hi')\n"
        "- generate: target is the topic/subject to compose rich factual text/report/notes for (e.g. 'Comprehensive factual details, background, and summary of the Jantar Mantar protest'). Use 'generate' whenever the user wants information, research, or notes written into an app!\n"
        "- hotkey: target is keyboard shortcut (e.g. 'enter', 'ctrl+f', 'esc')\n"
        "- wait: target is seconds to wait for UI rendering (e.g. '2.0', '1.0')\n"
        "- summarize_screen: target is what to read and summarize on the visible screen\n"
        "- send_email: target is the full email instruction\n"
        "- close_app: target is app name to close\n\n"
        "Guidelines:\n"
        "1. For messaging apps (WhatsApp, Slack): launch_app -> wait 2.0s -> click search bar -> type contact name -> hotkey enter -> wait 1.0s -> type message -> hotkey enter.\n"
        "   CRITICAL: In WhatsApp, pressing Enter after typing the contact name opens the chat and directly focuses the message compose field. NEVER click 'Contact' or 'Contact button' after pressing enter.\n"
        "2. For opening websites or web services: action MUST be 'open_url' with the target URL. NEVER launch Chrome unless the user explicitly demanded 'Google Chrome' by name. Websites must open in the user's default browser.\n"
        "3. For researching, fetching details, or writing notes in Notepad/documents: launch_app -> wait 1.5s -> generate (with full factual topic description). NEVER use placeholder brackets like '[summarized content from search results]'. Use 'generate' so the model writes real content.\n"
        "4. For screen reading/summarization: action is 'summarize_screen'.\n"
        "5. Output strictly valid JSON only with no markdown backticks:\n"
        "{\"workflow_name\": \"...\", \"steps\": [{\"action\": \"...\", \"target\": \"...\", \"description\": \"...\"}]}"
    )
    try:
        raw = complete_fn(prompt)
        # Clean any markdown code fences if model returned them
        clean = re.sub(r"```json\s*", "", raw or "")
        clean = re.sub(r"```\s*$", "", clean)
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            steps = []
            for item in data.get("steps") or []:
                action = str(item.get("action", "")).strip()
                target = str(item.get("target", "")).strip()
                desc = str(item.get("description", f"{action} {target}")).strip()
                if action in _ALLOWED and target:
                    steps.append({"action": action, "target": target, "description": desc})
            if steps:
                # Post-processing sanitization:
                # 1. Drop redundant "click Contact" steps that occur after "hotkey enter" in messaging workflows.
                # 2. Prevent launching Chrome when user intended to open a website in default browser.
                sanitized = []
                saw_enter_chat = False
                for step in steps:
                    act = step.get("action")
                    tgt = str(step.get("target", "")).strip()
                    tgt_lower = tgt.lower()

                    if act == "hotkey" and tgt_lower == "enter":
                        saw_enter_chat = True
                        sanitized.append(step)
                        continue

                    if saw_enter_chat and act == "click" and any(k in tgt_lower for k in ("contact", "contact button", "chat item", "conversation")):
                        print(f"[Planner] Stripping redundant post-enter click on contact: {tgt}")
                        continue

                    if act == "type":
                        saw_enter_chat = False

                    sanitized.append(step)
                return sanitized
    except Exception as exc:
        print(f"[Planner] compile_customer_intent_workflow error: {exc}")

    # Fallback smart heuristics for conversational intents
    cmd_lower = command.lower()
    if "whatsapp" in cmd_lower and any(w in cmd_lower for w in ("search", "send", "msg", "message", "hi", "hello")):
        # Extract contact and message
        m_contact = re.search(r"search for\s+(.+?)(?:\s+(?:and\s+)?send|\s*$)", command, re.IGNORECASE)
        m_msg = re.search(r"send\s+(?:message\s+)?[\"']?([^\"'\n]+)[\"']?$", command, re.IGNORECASE)
        contact = m_contact.group(1).strip() if m_contact else "search query"
        msg = m_msg.group(1).strip() if m_msg else "hi"
        return [
            {"action": "launch_app", "target": "WhatsApp", "description": "Launch WhatsApp application"},
            {"action": "wait", "target": "2.0", "description": "Wait for WhatsApp to load"},
            {"action": "click", "target": "Search bar", "description": "Click search bar to find contact"},
            {"action": "type", "target": contact, "description": f"Type contact name '{contact}'"},
            {"action": "hotkey", "target": "enter", "description": "Open conversation with contact"},
            {"action": "wait", "target": "1.0", "description": "Wait for chat to open"},
            {"action": "type", "target": msg, "description": f"Type message '{msg}'"},
            {"action": "hotkey", "target": "enter", "description": "Send message"}
        ]
    elif any(k in cmd_lower for k in ("summarize screen", "read screen", "read contents on the screen")):
        return [{"action": "summarize_screen", "target": command, "description": "Read screen and generate AI summary"}]
    elif any(k in cmd_lower for k in ("notepad", "notes", "text file", "document")) and any(w in cmd_lower for w in ("fetch", "give", "write", "search", "details", "info", "information", "protest", "report")):
        # Extract topic cleanly
        topic = command
        topic = re.sub(r"^(?:fetch|get|gather|search for|find|give|write|provide)\s+(?:me\s+)?(?:the\s+)?(?:details|info|information|notes|summary|report)\s+(?:of|about|on|regarding)?\s*", "", topic, flags=re.IGNORECASE)
        topic = re.sub(r"\s*(?:and\s+)?(?:give|write|put|save)\s+(?:it\s+)?(?:in|to|into)\s+(?:a\s+)?(?:notepad|text|notes|doc|file)(?:\s+file)?.*$", "", topic, flags=re.IGNORECASE)
        topic = re.sub(r"\s*(?:in|to|into)\s+(?:a\s+)?(?:notepad|text|notes|doc|file)(?:\s+file)?.*$", "", topic, flags=re.IGNORECASE)
        topic = topic.strip(" .:-\"'\t\r\n")
        if not topic or len(topic) < 3:
            topic = "the requested topic and protest developments"
        return [
            {"action": "launch_app", "target": "Notepad", "description": "Launch Notepad application"},
            {"action": "wait", "target": "1.5", "description": "Wait for Notepad to load"},
            {"action": "generate", "target": f"Comprehensive factual details, background, and summary regarding {topic}", "description": f"Generate factual details on {topic}"}
        ]

    return plan_command(command)


def plan_with_model(command: str, complete):
    """Ask the local model for workflow steps. complete(prompt) returns text."""
    return compile_customer_intent_workflow(command, complete)


def _plan_clause(clause: str):
    if _CREATE_TEXT.search(clause):
        return [{"action": "launch_app", "target": "Notepad"}]

    written = _WRITE.match(clause)
    if written:
        return [{"action": "generate", "target": written.group(1).strip()}]

    closed = _CLOSE.match(clause)
    if closed:
        target = closed.group(1).strip()
        if _UI_TARGET.search(clause):
            return [{"action": "click", "target": f"the close control for the {target}"}]
        return [{"action": "close_app", "target": target}]

    typed = _TYPE.match(clause)
    if typed:
        return [{"action": "type", "target": typed.group(1).strip()}]

    hotkey = _HOTKEY.match(clause)
    if hotkey:
        return [{"action": "hotkey", "target": hotkey.group(1).strip()}]

    # Direct URL or website navigation: open in default browser
    url_match = re.search(r"^(?:open|navigate to|browse to|go to|visit|browse)?\s*(https?://\S+|www\.\S+|[\w-]+\.(?:com|org|net|edu|io|ai|gov|in|local|app|dev)(?:/\S*)?)$", clause, re.IGNORECASE)
    if url_match:
        target_url = url_match.group(1).strip()
        return [{"action": "open_url", "target": target_url, "description": f"Open {target_url} in default browser"}]

    opened = _GOTO.match(clause)
    if opened:
        target = opened.group(1).strip()
        if re.search(r"https?://|\.com|\.org|\.net|\.edu|\.io|\.ai|\.gov|\.in|127\.0\.0\.1|localhost", target, re.IGNORECASE):
            return [{"action": "open_url", "target": target, "description": f"Open {target} in default browser"}]
        return [
            {"action": "type", "target": target},
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
