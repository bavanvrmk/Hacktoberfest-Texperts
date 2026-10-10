"""
Resolve and run Windows actions: launch an installed app, open a real file, close a window.
"""

import ctypes
import os
import re
import subprocess
import time
from ctypes import wintypes

import pyautogui


_OPEN_VERB = re.compile(
    r"^(?:please\s+)?(?:open|launch|start|run|find|search(?:\s+for)?|locate)\s+(.+)$",
    re.IGNORECASE,
)
_FILE_TOKEN = re.compile(r"([A-Za-z0-9][\w .\-]*\.[A-Za-z0-9]{1,8})$")
import difflib
import webbrowser

_FILE_WORD = re.compile(r"\b(file|document|spreadsheet|pdf)\b", re.IGNORECASE)
_EXPLORER_APP = re.compile(r"\b(file\s+explorer|windows\s+explorer)\b", re.IGNORECASE)

_BUILTIN_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "windows explorer": "explorer.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "paint": "mspaint.exe",
    "snipping tool": "snippingtool.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
}

_APP_ALIASES = {
    "word": "Microsoft Word",
    "winword": "Microsoft Word",
    "excel": "Microsoft Excel",
    "spreadsheet": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "ppt": "Microsoft PowerPoint",
    "slides": "Microsoft PowerPoint",
    "outlook": "Outlook",
    "mail": "Outlook",
    "email": "Outlook",
    "code": "Visual Studio Code",
    "vscod": "Visual Studio Code",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "edge": "Microsoft Edge",
    "firefox": "Firefox",
    "brave": "Brave",
    "spotify": "Spotify",
    "music": "Spotify",
    "discord": "Discord",
    "slack": "Slack",
    "teams": "Microsoft Teams",
    "terminal": "Windows Terminal",
    "terminal prompt": "Windows Terminal",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "notes": "notepad.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "settings": "ms-settings:",
    "twitter": "Twitter",
    "x": "Twitter",
    "chatgpt": "ChatGPT",
    "whatsapp": "WhatsApp",
    "whats app": "WhatsApp",
    "watsapp": "WhatsApp",
}

_WEB_APP_URLS = {
    "twitter": "https://x.com",
    "x": "https://x.com",
    "chatgpt": "https://chatgpt.com",
    "github": "https://github.com",
    "youtube": "https://youtube.com",
    "reddit": "https://reddit.com",
    "gmail": "https://mail.google.com",
    "google": "https://google.com",
    "docs": "https://docs.google.com",
    "whatsapp": "https://web.whatsapp.com",
    "web whatsapp": "https://web.whatsapp.com",
}

_BROWSER_TITLES = ("brave", "chrome", "edge", "firefox", "opera")
_SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "AppData"}
_app_cache = {"at": 0.0, "apps": []}


def classify_command(command: str):
    """Return ("app", name), ("file", name), or None for a normal click command."""
    text = " ".join((command or "").strip().split())
    if not text:
        return None

    opened = _OPEN_VERB.match(text)
    body = opened.group(1).strip() if opened else text

    if _EXPLORER_APP.search(text) and not _FILE_TOKEN.search(body):
        return ("app", "File Explorer")

    file_match = _FILE_TOKEN.search(body)
    if file_match:
        return ("file", file_match.group(1).strip())

    if _FILE_WORD.search(text) and "explorer" not in text.lower():
        name = re.sub(r"\b(the|a|an|file|document|named|called)\b", " ", body, flags=re.IGNORECASE)
        name = " ".join(name.split())
        if name:
            return ("file", name)

    if opened:
        name = opened.group(1).strip(" .")
        name = re.sub(r"^(?:the|a|an)\s+", "", name, flags=re.IGNORECASE)
        name = re.sub(r"\s+(?:app|application)$", "", name, flags=re.IGNORECASE)
        if name:
            return ("app", name)
    return None


def resolve_app_with_ai(query: str, apps: list, llm_client=None):
    """
    Uses the local LLM model to resolve the user's intended app name
    against installed applications when direct matching fails.
    """
    if not query or not apps:
        return None
    try:
        from core.llm_client import LLMClient
        client = llm_client or LLMClient()
        app_names = [item[0] for item in apps[:60]]
        prompt = (
            f"The user wants to open or run: '{query}'.\n"
            f"Installed Windows applications list:\n"
            f"{', '.join(app_names)}\n\n"
            "Identify which application from the list best matches the user's intent, "
            "handling similar names, synonyms, or categories (e.g. 'browser' -> Chrome/Edge, "
            "'word' -> Microsoft Word, 'editor' -> Visual Studio Code).\n"
            "Return ONLY the exact matched name from the list. If none match, return 'NONE'."
        )
        response = client.chat_completion(
            [{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=32,
            timeout=10,
        )
        content = response["choices"][0]["message"]["content"].strip().strip('"').strip("'")
        if content and content.upper() != "NONE":
            for name, app_id in apps:
                if name.lower() == content.lower() or content.lower() in name.lower():
                    print(f"[Launcher] AI resolved '{query}' -> '{name}'")
                    return (name, app_id)
    except Exception as exc:
        print(f"[Launcher] AI app resolution note: {exc}")
    return None


def choose_app(query, apps, llm_client=None):
    """Pick the best (name, app_id) from Start Menu entries using direct, alias, fuzzy, and AI resolution."""
    needle = (query or "").strip().lower()
    if not needle:
        return None

    # 1. Alias lookup
    alias = _APP_ALIASES.get(needle)
    if alias:
        target = alias.lower()
        exact_alias = [item for item in apps if item[0].lower() == target]
        if exact_alias:
            return exact_alias[0]
        contains_alias = [item for item in apps if target in item[0].lower()]
        if contains_alias:
            return sorted(contains_alias, key=lambda item: len(item[0]))[0]

    # 2. Exact match
    exact = [item for item in apps if item[0].lower() == needle]
    if exact:
        return exact[0]

    # 3. Starts-with
    starts = [item for item in apps if item[0].lower().startswith(needle)]
    if starts:
        return sorted(starts, key=lambda item: len(item[0]))[0]

    # 4. Substring contains
    contains = [item for item in apps if needle in item[0].lower()]
    if contains:
        return sorted(contains, key=lambda item: len(item[0]))[0]

    # 5. Fuzzy match via difflib
    app_names_map = {item[0].lower(): item for item in apps}
    close = difflib.get_close_matches(needle, list(app_names_map.keys()), n=1, cutoff=0.55)
    if close:
        matched = app_names_map[close[0]]
        print(f"[Launcher] Fuzzy matched '{query}' -> '{matched[0]}'")
        return matched

    # 6. AI Model Semantic Search
    ai_match = resolve_app_with_ai(query, apps, llm_client=llm_client)
    if ai_match:
        return ai_match

    return None


def list_start_apps():
    """Return installed Start Menu apps as (display name, app id). Cached for one minute."""
    now = time.time()
    if _app_cache["apps"] and now - _app_cache["at"] < 60:
        return list(_app_cache["apps"])
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-StartApps | ForEach-Object { $_.Name + '|' + $_.AppID }",
        ],
        capture_output=True,
        text=True,
        timeout=25,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    apps = []
    for line in (completed.stdout or "").splitlines():
        if "|" not in line:
            continue
        name, app_id = line.split("|", 1)
        name, app_id = name.strip(), app_id.strip()
        if name and app_id:
            apps.append((name, app_id))
    _app_cache["apps"] = apps
    _app_cache["at"] = now
    return apps


def launch_app(app_name: str, llm_client=None) -> str:
    """Start an installed app or web app fallback using fuzzy and AI matching."""
    key = app_name.strip().lower()

    # Generic browser request -> Open default system browser without forcing Chrome
    if key in ("browser", "web browser", "the browser", "default browser", "internet browser"):
        webbrowser.open("https://google.com")
        print(f"[Launcher] Launched default system browser.")
        time.sleep(1.0)
        return "Default Browser"

    # Direct URL or website -> Open in default browser
    if key.startswith("http://") or key.startswith("https://") or (key.startswith("www.") and "." in key):
        url = key if key.startswith("http") else f"https://{key}"
        webbrowser.open(url)
        print(f"[Launcher] Opened website '{url}' via default system browser.")
        time.sleep(1.0)
        return f"Web: {url}"

    # Builtin win32 binaries
    builtin = _BUILTIN_APPS.get(key) or _BUILTIN_APPS.get(_APP_ALIASES.get(key, "").lower())
    if builtin:
        subprocess.Popen([builtin])
        print(f"[Launcher] Started built-in app '{app_name}' via {builtin}.")
        time.sleep(0.8)
        return builtin

    installed = list_start_apps()
    match = choose_app(app_name, installed, llm_client=llm_client)
    if match:
        name, app_id = match
        subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"])
        print(f"[Launcher] Launched '{name}' ({app_id}).")
        time.sleep(1.2)
        return name

    # Web App fallback for online services (e.g. Twitter, ChatGPT, YouTube)
    web_url = _WEB_APP_URLS.get(key)
    if not web_url:
        alias_key = _APP_ALIASES.get(key, "").lower()
        web_url = _WEB_APP_URLS.get(alias_key)
    if web_url:
        webbrowser.open(web_url)
        print(f"[Launcher] Launched online service '{app_name}' via {web_url}")
        time.sleep(1.2)
        return f"Web: {web_url}"

    raise RuntimeError(f"No installed app or online service matches '{app_name}'.")


def find_file(name: str, roots=None) -> str:
    """Resolve a file name to a real path. Searches the project, user folders, then the Windows index."""
    raw = (name or "").strip().strip('"')
    if not raw:
        raise RuntimeError("No file name was given.")
    if os.path.isfile(raw):
        return os.path.abspath(raw)

    search_roots = roots or _default_roots()
    found = _walk_for(raw, search_roots)
    if found:
        return found

    indexed = _search_index(raw)
    if indexed:
        return indexed
    raise RuntimeError(f"Could not find a file named '{raw}'.")


def open_file(name: str, roots=None) -> str:
    path = find_file(name, roots=roots)
    os.startfile(path)  # noqa: S606 - user asked the agent to open this file
    print(f"[Launcher] Opened file {path}")
    return path


def close_app(name: str) -> str:
    """Close visible windows whose title matches the app. 'browser' closes Brave, Chrome, Edge, or Firefox."""
    needle = name.strip().lower()
    titles = list(_BROWSER_TITLES) if needle in {"browser", "the browser", "web browser"} else [needle]
    closed = _close_windows(titles)
    if not closed:
        raise RuntimeError(f"No open window matched '{name}'.")
    print(f"[Launcher] Closed: {', '.join(closed)}")
    return ", ".join(closed)


def type_text(text: str):
    time.sleep(0.4)
    _paste(text)


def press_keys(spec: str):
    parts = [part.strip().lower() for part in re.split(r"\+| ", spec) if part.strip()]
    if not parts:
        raise RuntimeError("No key was given.")
    if len(parts) == 1:
        pyautogui.press(parts[0])
    else:
        pyautogui.hotkey(*parts)


def _paste(text: str):
    env = os.environ.copy()
    env["SHADOW_TEXT"] = text
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $env:SHADOW_TEXT"],
        env=env,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")


def _default_roots():
    home = os.path.expanduser("~")
    roots = [os.getcwd()]
    for folder in ("Desktop", "Documents", "Downloads"):
        path = os.path.join(home, folder)
        if os.path.isdir(path):
            roots.append(path)
    return roots


def _walk_for(name: str, roots):
    target = name.lower()
    has_ext = "." in os.path.basename(target)
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [item for item in dirnames if item not in _SKIP_DIRS]
            depth = os.path.relpath(dirpath, root).count(os.sep)
            if depth > 3:
                dirnames[:] = []
                continue
            for filename in filenames:
                current = filename.lower()
                if current == target or (not has_ext and os.path.splitext(current)[0] == target):
                    return os.path.join(dirpath, filename)
    return None


def _search_index(name: str):
    safe = name.replace("'", "''")
    column = "System.FileName" if "." in os.path.basename(safe) else "System.ItemNameDisplay"
    script = f"""
$conn = New-Object -ComObject ADODB.Connection
$conn.Open("Provider=Search.CollatorDSO;Extended Properties='Application=Windows';")
$rs = $conn.Execute("SELECT TOP 5 System.ItemPathDisplay FROM SystemIndex WHERE {column} = '{safe}'")
while (-not $rs.EOF) {{
  $rs.Fields.Item('System.ItemPathDisplay').Value
  $rs.MoveNext()
}}
$conn.Close()
"""
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=12,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        print(f"[Launcher] Windows index search skipped: {exc}")
        return None
    for line in (completed.stdout or "").splitlines():
        path = line.strip()
        if path and os.path.isfile(path):
            return path
    return None


def _close_windows(needles):
    user32 = ctypes.windll.user32
    closed = []

    def _callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value
        lowered = title.lower()
        if any(needle in lowered for needle in needles):
            user32.PostMessageW(hwnd, 0x0010, 0, 0)
            closed.append(title)
        return True

    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(_callback)
    user32.EnumWindows(enum_proc, 0)
    return closed
