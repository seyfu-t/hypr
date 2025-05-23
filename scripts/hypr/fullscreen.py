#!/usr/bin/env python
from typing import Optional
import subprocess
import json

WHITELISTED_APPS = {"firefox", "chromium", "floorp"}

def get_active_window_info() -> Optional[dict]:
    try:
        output = subprocess.check_output(["hyprctl", "activewindow", "-j"], text=True)
        return json.loads(output)
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return None

def is_whitelisted(app_class: str) -> bool:
    lowered = app_class.lower()
    return any(app in lowered for app in WHITELISTED_APPS)

def toggle_fullscreen() -> None:
    info = get_active_window_info()
    if info is None:
        return

    app_class = info.get("class", "")
    fullscreen_state = info.get("fullscreen")

    if is_whitelisted(app_class):
        new_state = 0 if fullscreen_state != 0 else 2
        subprocess.run(["hyprctl", "dispatch", "fullscreenstate", f"{new_state} 0"])
    else:
        subprocess.run(["hyprctl", "dispatch", "fullscreen"])

if __name__ == "__main__":
    toggle_fullscreen()
