#!/usr/bin/env python3
import os
import sys
import json
import base64
import subprocess
from shutil import which

def run_cmd(cmd, capture_output=True, text=True, input=None):
    """Helper to run a subprocess command."""
    return subprocess.run(cmd, capture_output=capture_output, text=text, input=input)

def get_conf_dir():
    return os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))

def load_hypr_options():
    """Fetch hyprland rounding (border radius) and border size."""
    hyprctl = which("hyprctl")
    if not hyprctl:
        return 0, 0
    try:
        r = run_cmd([hyprctl, "-j", "getoption", "decoration:rounding"])
        rounding = json.loads(r.stdout)["int"]
        r = run_cmd([hyprctl, "-j", "getoption", "general:border_size"])
        border   = json.loads(r.stdout)["int"]
        return rounding, border
    except Exception:
        return 0, 0

def get_cursor_and_monitor():
    """Compute cursor and focused-monitor geometry, adjusted for scale & offset."""
    hyprctl = which("hyprctl")
    if not hyprctl:
        return (0,0), (0,0,1,0,0), [0,0,0,0]
    # cursor pos
    r = run_cmd([hyprctl, "cursorpos", "-j"])
    cp = json.loads(r.stdout)
    cur_x, cur_y = cp["x"], cp["y"]
    # monitors
    r = run_cmd([hyprctl, "-j", "monitors"])
    mon = next(filter(lambda m: m.get("focused"), json.loads(r.stdout)), None)
    if not mon:
        return (cur_x, cur_y), (0,0,1,0,0), [0,0,0,0]
    w, h, scale, offx, offy = mon["width"], mon["height"], mon["scale"], mon["x"], mon["y"]
    reserved = mon.get("reserved", [0,0,0,0])
    # normalize
    scale_i = int(str(scale).replace(".", ""))
    w_pct = w * 100 // scale_i
    h_pct = h * 100 // scale_i
    cur_x -= offx
    cur_y -= offy
    return (cur_x, cur_y), (w_pct, h_pct, scale_i, offx, offy), reserved

def compute_rofi_override(cur, mon, reserved, border, width):
    cur_x, cur_y = cur
    w_pct, h_pct, scale_i, _, _ = mon

    # Reconstruct RAW pixel size from scaled values (scale_i comes from removing the decimal)
    raw_w = w_pct * scale_i // 100
    raw_h = h_pct * scale_i // 100

    # Hyprland reserved order → [left, top, right, bottom]
    left, top, right, bottom = reserved

    # Horizontal: east if on right half, else west
    if cur_x >= raw_w // 2:
        x_pos = "east"
        x_off = -(raw_w - cur_x - right)
    else:
        x_pos = "west"
        x_off = cur_x - left

    # Vertical: south if on bottom half (box appears above), else north
    if cur_y >= raw_h // 2:
        y_pos = "south"
        y_off = -(raw_h - cur_y - bottom)
    else:
        y_pos = "north"
        y_off = cur_y - top

    wind_border = border * 3 // 2
    elem_border = 5 if border == 0 else border

    return (
        f"window{{location:{x_pos} {y_pos};"
        f"anchor:{x_pos} {y_pos};"
        f"x-offset:{x_off}px;"
        f"y-offset:{y_off}px;"
        f"border:{width}px;"
        f"border-radius:{wind_border}px;}} "
        f"wallbox{{border-radius:{elem_border}px;}} "
        f"element{{border-radius:{elem_border}px;}}"
    )

def rofi_menu(lines, placeholder, rofi_scale, rofi_override, rofi_conf):
    """Show a rofi dmenu with given lines; return the chosen line."""
    menu = "\n".join(lines)
    args = [
        "rofi", "-dmenu",
        "-theme-str", f"entry {{ placeholder: \"{placeholder}\"; }}",
        "-theme-str", rofi_scale,
        "-theme-str", rofi_override,
        "-config", rofi_conf
    ]
    p = run_cmd(args, input=menu)
    return p.stdout.strip()

def notify(msg):
    subprocess.run(["notify-send", msg])

def copy_to_clipboard(text):
    subprocess.run(["wl-copy"], input=text, text=True)

def main():
    # paths & defaults
    conf_dir       = get_conf_dir()
    rofi_conf      = os.path.join(conf_dir, "rofi", "clipboard.rasi")
    fav_file       = os.path.expanduser("~/.cliphist_favorites")
    try:
        scale_env   = int(os.environ.get("rofiScale", ""))
    except Exception:
        scale_env   = 10
    rofi_scale     = f'configuration {{font: "JetBrainsMono Nerd Font {scale_env}";}}'
    # hyprland vars
    hypr_border, hypr_width = load_hypr_options()
    # geometry
    (cur_x, cur_y), mon, reserved = get_cursor_and_monitor()
    rofi_override = compute_rofi_override((cur_x,cur_y), mon, reserved, hypr_border, hypr_width)

    # choose main action
    if len(sys.argv) == 1:
        actions = ["History", "Delete", "View Favorites", "Manage Favorites", "Clear History"]
        main_action = rofi_menu(actions, "Choose action", rofi_scale, rofi_override, rofi_conf)
    else:
        main_action = "History"

    if main_action == "History":
        history = subprocess.check_output(["cliphist", "list"], text=True).splitlines()
        sel = rofi_menu(history, "History…", rofi_scale, rofi_override, rofi_conf)
        if sel:
            decoded = subprocess.check_output(["cliphist", "decode"], input=sel, text=True)
            copy_to_clipboard(decoded)
            notify("Copied to clipboard.")
    elif main_action == "Delete":
        history = subprocess.check_output(["cliphist", "list"], text=True).splitlines()
        sel = rofi_menu(history, "Delete…", rofi_scale, rofi_override, rofi_conf)
        if sel:
            subprocess.run(["cliphist", "delete"], input=sel, text=True)
            notify("Deleted.")
    elif main_action == "View Favorites":
        if os.path.isfile(fav_file) and os.path.getsize(fav_file) > 0:
            with open(fav_file, "r") as f:
                encoded = [line.strip() for line in f if line.strip()]
            decoded = [base64.b64decode(x).decode().replace("\n", " ") for x in encoded]
            sel = rofi_menu(decoded, "View Favorites", rofi_scale, rofi_override, rofi_conf)
            if sel:
                idx = decoded.index(sel)
                full = base64.b64decode(encoded[idx]).decode()
                copy_to_clipboard(full)
                notify("Copied to clipboard.")
        else:
            notify("No favorites.")
    elif main_action == "Manage Favorites":
        opts = ["Add to Favorites", "Delete from Favorites", "Clear All Favorites"]
        sub = rofi_menu(opts, "Manage Favorites", rofi_scale, rofi_override, rofi_conf)
        if sub == "Add to Favorites":
            history = subprocess.check_output(["cliphist", "list"], text=True).splitlines()
            sel = rofi_menu(history, "Add to Favorites…", rofi_scale, rofi_override, rofi_conf)
            if sel:
                full = subprocess.check_output(["cliphist", "decode"], input=sel, text=True)
                enc  = base64.b64encode(full.encode()).decode()
                os.makedirs(os.path.dirname(fav_file), exist_ok=True)
                existing = []
                if os.path.isfile(fav_file):
                    with open(fav_file) as f:
                        existing = [l.strip() for l in f]
                if enc in existing:
                    notify("Item is already in favorites.")
                else:
                    with open(fav_file, "a") as f:
                        f.write(enc + "\n")
                    notify("Added to favorites.")
        elif sub == "Delete from Favorites":
            if os.path.isfile(fav_file) and os.path.getsize(fav_file) > 0:
                with open(fav_file) as f:
                    encoded = [l.strip() for l in f if l.strip()]
                decoded = [base64.b64decode(x).decode().replace("\n", " ") for x in encoded]
                sel = rofi_menu(decoded, "Remove from Favorites…", rofi_scale, rofi_override, rofi_conf)
                if sel:
                    idx = decoded.index(sel)
                    to_remove = encoded[idx]
                    remaining = [x for x in encoded if x != to_remove]
                    with open(fav_file, "w") as f:
                        f.write("\n".join(remaining) + ("\n" if remaining else ""))
                    notify("Item removed from favorites.")
            else:
                notify("No favorites to remove.")
        elif sub == "Clear All Favorites":
            if os.path.isfile(fav_file) and os.path.getsize(fav_file) > 0:
                confirm = rofi_menu(["Yes", "No"], "Clear All Favorites?", rofi_scale, rofi_override, rofi_conf)
                if confirm == "Yes":
                    open(fav_file, "w").close()
                    notify("All favorites have been deleted.")
            else:
                notify("No favorites to delete.")
        else:
            sys.exit(1)
    elif main_action == "Clear History":
        confirm = rofi_menu(["Yes", "No"], "Clear Clipboard History?", rofi_scale, rofi_override, rofi_conf)
        if confirm == "Yes":
            subprocess.run(["cliphist", "wipe"])
            notify("Clipboard history cleared.")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
