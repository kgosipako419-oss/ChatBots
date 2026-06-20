"""Windows UI Automation helpers — the same accessibility API screen readers use.

These let the assistant read and operate on real UI elements (buttons, links,
text fields) by name, rather than guessing pixel coordinates. All functions
degrade gracefully if the `uiautomation` package or an element is unavailable.
"""
from __future__ import annotations

from typing import Iterator, Optional

# Control types a user can interact with (click/focus).
INTERACTIVE = {
    "ButtonControl", "HyperlinkControl", "MenuItemControl", "ListItemControl",
    "TabItemControl", "CheckBoxControl", "RadioButtonControl", "EditControl",
    "ComboBoxControl", "SplitButtonControl", "TreeItemControl", "DocumentControl",
}


def _auto():
    import uiautomation as auto  # lazy: heavy COM import
    return auto


def available() -> bool:
    try:
        _auto()
        return True
    except Exception:
        return False


def foreground_window():
    """Return the foreground top-level window control, or None."""
    auto = _auto()
    try:
        ctrl = auto.GetForegroundControl()
        if ctrl:
            return ctrl
    except Exception:
        pass
    try:
        hwnd = auto.GetForegroundWindow()
        return auto.ControlFromHandle(hwnd)
    except Exception:
        return None


def focused_control():
    auto = _auto()
    try:
        return auto.GetFocusedControl()
    except Exception:
        return None


def iter_controls(root, max_count: int = 400, max_depth: int = 14) -> Iterator:
    """Yield descendant controls of `root`, breadth-limited for speed."""
    auto = _auto()
    count = 0
    walk = getattr(auto, "WalkControl", None)
    if walk is not None:
        try:
            for ctrl, _depth in walk(root, False, max_depth):
                yield ctrl
                count += 1
                if count >= max_count:
                    return
            return
        except Exception:
            pass
    # Manual BFS fallback.
    try:
        stack = list(root.GetChildren())
    except Exception:
        return
    while stack and count < max_count:
        ctrl = stack.pop(0)
        yield ctrl
        count += 1
        try:
            stack.extend(ctrl.GetChildren())
        except Exception:
            pass


def _name_of(ctrl) -> str:
    try:
        return (ctrl.Name or "").strip()
    except Exception:
        return ""


def _type_of(ctrl) -> str:
    try:
        return ctrl.ControlTypeName or ""
    except Exception:
        return ""


def list_interactive(limit: int = 30) -> list[tuple[str, str]]:
    """Return (name, type) for interactive elements in the foreground window."""
    win = foreground_window()
    if win is None:
        return []
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for ctrl in iter_controls(win):
        name = _name_of(ctrl)
        ctype = _type_of(ctrl)
        if not name or ctype not in INTERACTIVE:
            continue
        key = f"{name}|{ctype}"
        if key in seen:
            continue
        seen.add(key)
        out.append((name, ctype.replace("Control", "")))
        if len(out) >= limit:
            break
    return out


def find_by_name(name: str, interactive_only: bool = True):
    """Find the best-matching control in the foreground window by (partial) name."""
    win = foreground_window()
    if win is None:
        return None
    target = name.strip().lower()
    exact = None
    partial = None
    for ctrl in iter_controls(win):
        cname = _name_of(ctrl).lower()
        if not cname:
            continue
        if interactive_only and _type_of(ctrl) not in INTERACTIVE:
            continue
        if cname == target:
            exact = ctrl
            break
        if partial is None and target in cname:
            partial = ctrl
    return exact or partial


def invoke(ctrl) -> bool:
    """Activate a control (prefer the Invoke pattern; fall back to a real click)."""
    for getter in ("GetInvokePattern", "GetTogglePattern", "GetSelectionItemPattern"):
        try:
            pattern = getattr(ctrl, getter)()
            if pattern is not None:
                if hasattr(pattern, "Invoke"):
                    pattern.Invoke()
                elif hasattr(pattern, "Toggle"):
                    pattern.Toggle()
                elif hasattr(pattern, "Select"):
                    pattern.Select()
                return True
        except Exception:
            continue
    try:
        ctrl.Click(waitTime=0.05)
        return True
    except Exception:
        return False


def set_value(ctrl, text: str) -> bool:
    """Set a text field's value via the Value pattern, falling back to typing."""
    try:
        vp = ctrl.GetValuePattern()
        vp.SetValue(text)
        return True
    except Exception:
        pass
    try:
        ctrl.SetFocus()
        import pyautogui
        pyautogui.write(text, interval=0.01)
        return True
    except Exception:
        return False


def focus(ctrl) -> bool:
    try:
        ctrl.SetFocus()
        return True
    except Exception:
        return False


def window_title() -> Optional[str]:
    win = foreground_window()
    if win is None:
        return None
    return _name_of(win) or None
