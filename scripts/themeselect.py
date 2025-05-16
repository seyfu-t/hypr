#!/usr/bin/env python3
# themeselect.py

import os
import shutil
import json
import subprocess
import glob
import re

# --- Helpers ---------------------------------------------------------------

def run(cmd, **kwargs):
    return subprocess.run(cmd, shell=isinstance(cmd, str), **kwargs)

def get_conf_dir():
    return os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))

def load_hypr_options():
    """Fetch hyprland rounding (border radius)."""
    hyprctl = shutil.which("hyprctl")
    if not hyprctl: return 0
    try:
        out = run([hyprctl, "-j", "getoption", "decoration:rounding"],
                  capture_output=True, text=True).stdout
        return json.loads(out)["int"]
    except:
        return 0

def parse_hyde_conf():
    """Load hyde.conf KEY="VALUE" pairs into a dict."""
    cfg = {}
    path = os.path.join(get_conf_dir(), "hyde", "hyde.conf")
    if not os.path.isfile(path):
        return cfg
    with open(path) as f:
        for line in f:
            m = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)="(.+)"\s*$', line)
            if m:
                cfg[m.group(1)] = m.group(2)
    return cfg

def get_themes():
    """
    Scan $XDG_CONFIG_HOME/hyde/themes/* for theme dirs,
    ensure each has a wall.set symlink, and return two lists:
      thm_list: [theme_name, ...]
      thm_wall: [absolute-path-to-wall.set-target, ...]
    """
    conf = parse_hyde_conf()
    base = os.path.join(get_conf_dir(), "hyde", "themes")
    thm_list, thm_wall = [], []
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if not os.path.isdir(d):
            continue
        ws = os.path.join(d, "wall.set")
        # link the first image if missing
        if not os.path.islink(ws) or not os.path.exists(ws):
            # find first image
            imgs = []
            for ext in (".png", ".jpg", ".jpeg", ".gif"):
                imgs.extend(sorted(glob.glob(os.path.join(d, f"*{ext}"))))
            if imgs:
                try:
                    if os.path.exists(ws):
                        os.remove(ws)
                    os.symlink(imgs[0], ws)
                except OSError:
                    pass
        # collect
        if os.path.islink(ws):
            thm_list.append(name)
            thm_wall.append(os.readlink(ws))
    return thm_list, thm_wall

def sha1_hash(path):
    import hashlib
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def rofi_menu(lines, placeholder, scale_str, override_str, rofi_conf, select=None):
    menu = "\n".join(lines)
    args = [
        "rofi", "-dmenu",
        "-theme-str", f'entry {{ placeholder: "{placeholder}"; }}',
        "-theme-str", scale_str,
        "-theme-str", override_str,
        "-config", rofi_conf
    ]
    if select:
        args += ["-select", select]
    p = run(args, input=menu, capture_output=True, text=True)
    return p.stdout.strip()

def notify(theme):
    ico = os.path.expanduser("~/.config/dunst/icons/hyprdots.png")
    subprocess.run(["notify-send", "-a", "t1", "-i", ico, f" {theme}"])

# --- Main ------------------------------------------------------------------

def main():
    conf_dir = get_conf_dir()
    cfg = parse_hyde_conf()
    rofi_scale = cfg.get("rofiScale", "")
    rofi_scale = rofi_scale if rofi_scale.isdigit() else "10"
    r_scale = f'configuration {{font: "JetBrainsMono Nerd Font {rofi_scale}";}}'

    hypr_border = load_hypr_options()
    elem_border = hypr_border * 5
    icon_border = elem_border - 5

    # monitor geometry & scale
    j = run(["hyprctl", "-j", "monitors"], capture_output=True, text=True).stdout
    mon = next(filter(lambda m: m.get("focused"), json.loads(j)), {})
    width = mon.get("width", 0)
    scale = str(mon.get("scale", 1.0)).replace(".", "")
    try:
        mon_x_res = width * 100 // int(scale)
    except:
        mon_x_res = width

    # style override
    theme_select = cfg.get("themeSelect", "1")
    if theme_select == "2":
        elm_width = (20 + 12) * int(rofi_scale) * 2
        thmb_extn = "quad"
        override = (
            f"window{{width:100%;background-color:#00000003;}} "
            f"listview{{columns:{mon_x_res // elm_width};}} "
            f"element{{border-radius:{elem_border}px;background-color:@main-bg;}} "
            f"element-icon{{size:20em;border-radius:{icon_border}px 0 0 {icon_border}px;}}"
        )
    else:
        elm_width = (23 + 12 + 1) * int(rofi_scale) * 2
        thmb_extn = "sqre"
        override = (
            f"window{{width:100%;}} "
            f"listview{{columns:{mon_x_res // elm_width};}} "
            f"element{{border-radius:{elem_border}px;padding:0.5em;}} "
            f"element-icon{{size:23em;border-radius:{icon_border}px;}}"
        )

    # build menu
    thm_list, thm_wall = get_themes()
    cache_dir = os.path.expanduser("~/.cache/hyde/thumbs")
    os.makedirs(cache_dir, exist_ok=True)

    lines = []
    for name, wall in zip(thm_list, thm_wall):
        h = sha1_hash(wall)
        icon_path = os.path.join(cache_dir, f"{h}.{thmb_extn}")
        lines.append(f"{name}\x00icon\x1f{icon_path}")

    rofi_conf = os.path.join(conf_dir, "rofi", "selector.rasi")
    sel = rofi_menu(lines, "Select theme", r_scale, override, rofi_conf,
                    select=cfg.get("hydeTheme"))

    if sel:
        # call the Python port of themeswitch
        here = os.path.dirname(os.path.realpath(__file__))
        switcher = os.path.join(here, "themeswitch.py")
        subprocess.run([switcher, "-s", sel])
        notify(sel)

if __name__ == "__main__":
    main()
