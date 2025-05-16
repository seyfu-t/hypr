#!/usr/bin/env python3
# themeswitch.py

import os
import sys
import argparse
import subprocess
import shutil
import re

# --- Helpers ---------------------------------------------------------------

def run(cmd, **kwargs):
    return subprocess.run(cmd, shell=isinstance(cmd, str), **kwargs)

def get_conf_dir():
    return os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))

def parse_hyde_conf():
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

def write_hyde_conf(var, val):
    path = os.path.join(get_conf_dir(), "hyde", "hyde.conf")
    lines = []
    if os.path.isfile(path):
        with open(path) as f:
            for L in f:
                if not L.startswith(f"{var}="):
                    lines.append(L)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    lines.append(f'{var}="{val}"\n')
    with open(path, "w") as f:
        f.writelines(lines)

def get_themes():
    base = os.path.join(get_conf_dir(), "hyde", "themes")
    themes = [d for d in sorted(os.listdir(base))
              if os.path.isdir(os.path.join(base, d))]
    return themes

def replace_in_file(path, key, new_line):
    """Replace first line starting with key= with new_line, in-place."""
    if not os.path.isfile(path):
        return
    out = []
    with open(path) as f:
        for L in f:
            if L.startswith(key):
                out.append(new_line + "\n")
            else:
                out.append(L)
    with open(path, "w") as f:
        f.writelines(out)

# --- Main ------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("-n", action="store_true")
    p.add_argument("-p", action="store_true")
    p.add_argument("-s", metavar="THEME", help="Select this theme")
    args = p.parse_args()

    cfg = parse_hyde_conf()
    current = cfg.get("hydeTheme")
    if not current:
        print("ERROR: unable to detect current theme", file=sys.stderr)
        sys.exit(1)

    themes = get_themes()
    if args.n:
        idx = themes.index(current)
        new = themes[(idx + 1) % len(themes)]
    elif args.p:
        idx = themes.index(current)
        new = themes[(idx - 1) % len(themes)]
    elif args.s:
        new = args.s
    else:
        print("Usage: themeswitch.py -n | -p | -s THEME", file=sys.stderr)
        sys.exit(1)

    if new not in themes:
        new = current

    # update hyde.conf
    write_hyde_conf("hydeTheme", new)
    print(f':: applying theme :: "{new}"')

    # disable Hypr autoreload if running
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        run(["hyprctl", "keyword", "misc:disable_autoreload", "1", "-q"], check=False)

    # regenerate Hypr config
    hypr_src = os.path.join(get_conf_dir(), "hyde", "themes", new, "hypr.theme")
    hypr_dst = os.path.join(get_conf_dir(), "hypr", "themes", "theme.conf")
    os.makedirs(os.path.dirname(hypr_dst), exist_ok=True)
    with open(hypr_src) as src, open(hypr_dst, "w") as dst:
        next(src)  # skip first line
        dst.writelines(src.readlines())

    # parse GTK & icon themes from hypr.theme
    text = open(hypr_src).read()
    m = re.search(r'^\s*\$GTK[-_]THEME\s*=\s*(.+)$', text, flags=re.M)
    if m:
        gtk_theme = m.group(1).strip().strip('"').strip("'")
    else:
        m = re.search(r"gsettings set org\.gnome\.desktop\.interface gtk-theme '([^']+)'", text)
        gtk_theme = m.group(1) if m else None

    m = re.search(r'^\s*\$ICON[-_]THEME\s*=\s*(.+)$', text, flags=re.M)
    if m:
        icon_theme = m.group(1).strip().strip('"').strip("'")
    else:
        m = re.search(r"gsettings set org\.gnome\.desktop\.interface icon-theme '([^']+)'", text)
        icon_theme = m.group(1) if m else gtk_theme

    # update Qt config
    for sub in ("qt5ct", "qt6ct"):
        path = os.path.join(get_conf_dir(), sub, f"{sub}.conf")
        replace_in_file(path, "icon_theme=", f"icon_theme={icon_theme}")
    replace_in_file(os.path.join(get_conf_dir(), "kdeglobals"),
                    "Theme=", f"Theme={icon_theme}")

    # update GTK3
    gtk3 = os.path.join(get_conf_dir(), "gtk-3.0", "settings.ini")
    replace_in_file(gtk3, "gtk-theme-name=", f"gtk-theme-name={gtk_theme}")
    replace_in_file(gtk3, "gtk-icon-theme-name=", f"gtk-icon-theme-name={icon_theme}")

    # update GTK4 (Arch only: always use ~/.themes)
    gtk4_conf = os.path.join(get_conf_dir(), "gtk-4.0")
    target = os.path.expanduser(f"~/.themes/{gtk_theme}/gtk-4.0")
    if os.path.islink(gtk4_conf) or os.path.isdir(gtk4_conf):
        os.remove(gtk4_conf)
    os.symlink(target, gtk4_conf)

    # flatpak overrides
    if shutil.which("flatpak"):
        # load enableWallDcol flag
        ewd = int(cfg.get("enableWallDcol", "0"))
        theme_env = "Wallbash-Gtk" if ewd else gtk_theme
        run(f"flatpak --user override --env=GTK_THEME={theme_env}", shell=True)
        run(f"flatpak --user override --env=ICON_THEME={icon_theme}", shell=True)

    # call swwwallpaper.sh to update wallpaper
    here = os.path.dirname(os.path.realpath(__file__))
    wall = os.path.join(get_conf_dir(), "hyde", "themes", new, "wall.set")
    if os.path.islink(wall):
        real = os.readlink(wall)
        run([os.path.join(here, "swwwallpaper.sh"), "-s", real], check=False)

if __name__ == "__main__":
    main()
