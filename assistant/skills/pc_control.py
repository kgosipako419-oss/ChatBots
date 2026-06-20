"""Skills for controlling the local Windows PC.

Each public action is registered as an LLM tool via the @tool decorator.
Heavy/OS-specific imports are guarded so the module still loads (with degraded
tools) if an optional dependency is missing.
"""
from __future__ import annotations

import datetime as _dt
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

import psutil

from ..brain.tools import tool
from ..config import PROJECT_ROOT

# ---- Optional dependencies (degrade gracefully if missing) -------------------
try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:  # pragma: no cover - depends on display/Pillow
    pyautogui = None

try:
    from pycaw.pycaw import AudioUtilities
    _HAS_PYCAW = True
except Exception:  # pragma: no cover - Windows-only
    _HAS_PYCAW = False


# ---- Application launching ---------------------------------------------------
# Friendly name -> what to launch. Generic names fall through to Windows `start`,
# which resolves apps via the App Paths registry and PATH.
APP_ALIASES: dict[str, str] = {
    "browser": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "file explorer": "explorer",
    "files": "explorer",
    "explorer": "explorer",
    "settings": "ms-settings:",
    "task manager": "taskmgr",
    "paint": "mspaint",
    "terminal": "wt",
    "command prompt": "cmd",
    "spotify": "spotify",
    "vscode": "code",
    "vs code": "code",
    "code": "code",
}

# Friendly name -> process executable for closing apps.
PROCESS_ALIASES: dict[str, str] = {
    "chrome": "chrome.exe",
    "browser": "chrome.exe",
    "edge": "msedge.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "notepad": "notepad.exe",
    "calculator": "calculatorapp.exe",
    "spotify": "spotify.exe",
    "vscode": "code.exe",
    "code": "code.exe",
    "terminal": "windowsterminal.exe",
}


@tool(
    "open_application",
    "Open or launch an application or program on the PC by name (e.g. chrome, notepad, spotify, calculator).",
    {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "App name to open"}},
        "required": ["name"],
    },
)
def open_application(name: str) -> str:
    key = name.strip().lower()
    target = APP_ALIASES.get(key, key)
    try:
        if target.endswith(":"):  # protocol like ms-settings:
            subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)
        else:
            subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)
        return f"Opened {name}."
    except Exception as exc:
        return f"Could not open {name}: {exc}"


@tool(
    "close_application",
    "Close or quit a running application by name.",
    {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "App name to close"}},
        "required": ["name"],
    },
)
def close_application(name: str) -> str:
    key = name.strip().lower()
    exe = PROCESS_ALIASES.get(key, key if key.endswith(".exe") else f"{key}.exe")
    killed = 0
    for proc in psutil.process_iter(["name"]):
        pname = (proc.info.get("name") or "").lower()
        if pname == exe.lower():
            try:
                proc.terminate()
                killed += 1
            except Exception:
                pass
    if killed:
        return f"Closed {name} ({killed} window{'s' if killed != 1 else ''})."
    return f"{name} doesn't appear to be running."


# ---- Volume ------------------------------------------------------------------
def _volume_interface():
    # Newer pycaw exposes the IAudioEndpointVolume interface directly on the device.
    return AudioUtilities.GetSpeakers().EndpointVolume


@tool(
    "set_volume",
    "Set the system master volume to a specific level from 0 to 100.",
    {
        "type": "object",
        "properties": {"level": {"type": "integer", "description": "Volume 0-100"}},
        "required": ["level"],
    },
)
def set_volume(level: int) -> str:
    level = max(0, min(100, int(level)))
    if not _HAS_PYCAW:
        return "Volume control needs the pycaw package (pip install pycaw)."
    try:
        vol = _volume_interface()
        vol.SetMute(0, None)
        vol.SetMasterVolumeLevelScalar(level / 100.0, None)
        return f"Volume set to {level} percent."
    except Exception as exc:
        return f"Could not set volume: {exc}"


@tool(
    "adjust_volume",
    "Change the system volume: 'up', 'down', 'mute', or 'unmute'.",
    {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["up", "down", "mute", "unmute"]},
        },
        "required": ["action"],
    },
)
def adjust_volume(action: str) -> str:
    action = action.strip().lower()
    if not _HAS_PYCAW:
        # Fall back to media keys if available.
        if pyautogui:
            key = {"up": "volumeup", "down": "volumedown", "mute": "volumemute",
                   "unmute": "volumemute"}.get(action)
            if key:
                pyautogui.press(key)
                return f"Volume {action}."
        return "Volume control needs the pycaw package."
    try:
        vol = _volume_interface()
        if action == "mute":
            vol.SetMute(1, None)
            return "Muted."
        if action == "unmute":
            vol.SetMute(0, None)
            return "Unmuted."
        current = vol.GetMasterVolumeLevelScalar()
        step = 0.1 if action == "up" else -0.1
        new = max(0.0, min(1.0, current + step))
        vol.SetMute(0, None)
        vol.SetMasterVolumeLevelScalar(new, None)
        return f"Volume {action} to {round(new * 100)} percent."
    except Exception as exc:
        return f"Could not adjust volume: {exc}"


# ---- Media keys --------------------------------------------------------------
@tool(
    "media_control",
    "Control media playback in the foreground player: play/pause, next, previous, or stop.",
    {
        "type": "object",
        "properties": {
            "action": {"type": "string",
                       "enum": ["play_pause", "next", "previous", "stop"]},
        },
        "required": ["action"],
    },
)
def media_control(action: str) -> str:
    if pyautogui is None:
        return "Media control needs the pyautogui package."
    keymap = {"play_pause": "playpause", "next": "nexttrack",
              "previous": "prevtrack", "stop": "stop"}
    key = keymap.get(action.strip().lower())
    if not key:
        return f"Unknown media action: {action}."
    pyautogui.press(key)
    return f"Media: {action.replace('_', ' ')}."


# ---- Screenshot --------------------------------------------------------------
@tool(
    "take_screenshot",
    "Capture a screenshot of the current screen and save it to the screenshots folder.",
    {"type": "object", "properties": {}},
)
def take_screenshot() -> str:
    if pyautogui is None:
        return "Screenshots need the pyautogui package."
    folder = PROJECT_ROOT / "screenshots"
    folder.mkdir(exist_ok=True)
    fname = folder / f"shot_{_dt.datetime.now():%Y%m%d_%H%M%S}.png"
    pyautogui.screenshot().save(fname)
    return f"Screenshot saved as {fname.name}."


# ---- System info -------------------------------------------------------------
@tool(
    "get_system_info",
    "Report system status: CPU usage, memory usage, disk space, and battery level.",
    {"type": "object", "properties": {}},
)
def get_system_info() -> str:
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(PROJECT_ROOT.anchor or "C:\\"))
    parts = [
        f"CPU at {cpu:.0f} percent",
        f"memory at {mem.percent:.0f} percent ({mem.used // 2**30} of {mem.total // 2**30} gigabytes)",
        f"disk {disk.percent:.0f} percent full ({disk.free // 2**30} gigabytes free)",
    ]
    battery = psutil.sensors_battery()
    if battery is not None:
        state = "charging" if battery.power_plugged else "on battery"
        parts.append(f"battery at {battery.percent:.0f} percent, {state}")
    return "; ".join(parts) + "."


# ---- Power -------------------------------------------------------------------
@tool(
    "power_action",
    "Perform a power action on the PC: 'lock', 'sleep', 'shutdown', or 'restart'.",
    {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["lock", "sleep", "shutdown", "restart"]},
        },
        "required": ["action"],
    },
    dangerous=True,
)
def power_action(action: str) -> str:
    action = action.strip().lower()
    try:
        if action == "lock":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
            return "Locked."
        if action == "sleep":
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)
            return "Going to sleep."
        if action == "shutdown":
            subprocess.run(["shutdown", "/s", "/t", "5"], check=False)
            return "Shutting down in 5 seconds. Say cancel shutdown to abort."
        if action == "restart":
            subprocess.run(["shutdown", "/r", "/t", "5"], check=False)
            return "Restarting in 5 seconds. Say cancel shutdown to abort."
        return f"Unknown power action: {action}."
    except Exception as exc:
        return f"Power action failed: {exc}"


@tool(
    "cancel_shutdown",
    "Cancel a pending shutdown or restart.",
    {"type": "object", "properties": {}},
)
def cancel_shutdown() -> str:
    subprocess.run(["shutdown", "/a"], check=False)
    return "Pending shutdown cancelled."


# ---- Web ---------------------------------------------------------------------
@tool(
    "open_website",
    "Open a website or URL in the default browser.",
    {
        "type": "object",
        "properties": {"url": {"type": "string", "description": "URL or domain to open"}},
        "required": ["url"],
    },
)
def open_website(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opening {url}."


@tool(
    "web_search",
    "Search the web for a query in the default browser.",
    {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "What to search for"}},
        "required": ["query"],
    },
)
def web_search(query: str) -> str:
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"Searching the web for {query}."


# ---- Keyboard ----------------------------------------------------------------
@tool(
    "type_text",
    "Type text into the currently focused window, as if typed on the keyboard.",
    {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to type"}},
        "required": ["text"],
    },
)
def type_text(text: str) -> str:
    if pyautogui is None:
        return "Typing needs the pyautogui package."
    pyautogui.write(text, interval=0.01)
    return "Typed the text."


# ---- Time --------------------------------------------------------------------
@tool(
    "get_datetime",
    "Get the current local date and time.",
    {"type": "object", "properties": {}},
)
def get_datetime() -> str:
    now = _dt.datetime.now()
    return now.strftime("It's %A, %B %d, %Y, %I:%M %p.")


# ---- Window management -------------------------------------------------------
@tool(
    "manage_windows",
    "Manage on-screen windows: 'show_desktop' (minimize all), 'switch' (alt-tab to "
    "next window), 'maximize', 'minimize', or 'close' the active window.",
    {
        "type": "object",
        "properties": {
            "action": {"type": "string",
                       "enum": ["show_desktop", "switch", "maximize", "minimize", "close"]},
        },
        "required": ["action"],
    },
)
def manage_windows(action: str) -> str:
    if pyautogui is None:
        return "Window management needs the pyautogui package."
    action = action.strip().lower()
    combos = {
        "show_desktop": ("win", "d"),
        "switch": ("alt", "tab"),
        "maximize": ("win", "up"),
        "minimize": ("win", "down"),
        "close": ("alt", "f4"),
    }
    combo = combos.get(action)
    if not combo:
        return f"Unknown window action: {action}."
    pyautogui.hotkey(*combo)
    return f"Done: {action.replace('_', ' ')}."


@tool(
    "list_open_windows",
    "List the titles of the currently open application windows.",
    {"type": "object", "properties": {}},
)
def list_open_windows() -> str:
    try:
        import pygetwindow as gw
    except Exception:
        return "Listing windows needs the pygetwindow package."
    titles = [t for t in gw.getAllTitles() if t.strip()]
    if not titles:
        return "No open windows found."
    return "Open windows: " + ", ".join(titles[:12]) + ("..." if len(titles) > 12 else "") + "."


@tool(
    "press_hotkey",
    "Press a keyboard shortcut. Provide keys to press together, e.g. ['ctrl','c'] to copy "
    "or ['ctrl','shift','t']. Valid keys include ctrl, alt, shift, win, and letters/numbers.",
    {
        "type": "object",
        "properties": {
            "keys": {"type": "array", "items": {"type": "string"},
                     "description": "Keys to press simultaneously"},
        },
        "required": ["keys"],
    },
)
def press_hotkey(keys: list) -> str:
    if pyautogui is None:
        return "Hotkeys need the pyautogui package."
    keys = [str(k).strip().lower() for k in keys if str(k).strip()]
    if not keys:
        return "No keys provided."
    pyautogui.hotkey(*keys)
    return f"Pressed {' + '.join(keys)}."
