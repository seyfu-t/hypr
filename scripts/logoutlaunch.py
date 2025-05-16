#!/usr/bin/env python3
import os, sys, subprocess, json, re, tempfile, shutil, glob, hashlib

def run(cmd, **kw):
    return subprocess.run(cmd, shell=isinstance(cmd, str), **kw)

def which(prog):
    return shutil.which(prog)

def get_conf_dir():
    return os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))

def get_cache_dir():
    return os.path.expanduser("~/.cache/hyde")

def parse_env_file(path):
    """Parse VAR="VALUE" lines into a dict (strips quotes)."""
    d = {}
    if not os.path.isfile(path):
        return d
    with open(path) as f:
        for L in f:
            L = L.strip()
            if not L or L.startswith("#") or "=" not in L:
                continue
            k,v = L.split("=",1)
            v = v.strip().strip('"').strip("'")
            d[k] = v
    return d

def envsubst(template, mapping):
    """Replace ${VAR} and $VAR in template from mapping."""
    pat = re.compile(r"\$\{(\w+)\}|\$(\w+)")
    def repl(m):
        key = m.group(1) or m.group(2)
        return mapping.get(key, m.group(0))
    return pat.sub(repl, template)

def get_hypr_border():
    hypr = which("hyprctl")
    if not hypr: return 0
    out = run([hypr, "-j", "getoption", "decoration:rounding"],
              capture_output=True, text=True).stdout
    try:
        return int(json.loads(out)["int"])
    except:
        return 0

def get_focused_monitor():
    hypr = which("hyprctl")
    if not hypr: return {}
    out = run([hypr, "-j", "monitors"], capture_output=True, text=True).stdout
    for m in json.loads(out):
        if m.get("focused"):
            return m
    return {}

def get_themes_list(hyde_conf_dir):
    base = os.path.join(hyde_conf_dir, "themes")
    if not os.path.isdir(base):
        return []
    return sorted([d for d in os.listdir(base) if os.path.isdir(os.path.join(base,d))])

def main():
    # 1) toggle off existing wlogout
    if run("pgrep -x wlogout", capture_output=True, text=True).stdout.strip():
        run("pkill -x wlogout", shell=True)
        sys.exit(0)

    # 2) minimal globalcontrol.sh
    conf_dir     = get_conf_dir()
    hyde_conf_dir= os.path.join(conf_dir, "hyde")
    cache_dir    = get_cache_dir()
    # read hyde.conf
    cfg = parse_env_file(os.path.join(hyde_conf_dir, "hyde.conf"))
    # sane default
    enableWallDcol = int(cfg.get("enableWallDcol","0")) if cfg.get("enableWallDcol","").isdigit() else 0
    # pick or detect theme
    hyde_theme = cfg.get("hydeTheme")
    themes = get_themes_list(hyde_conf_dir)
    if not hyde_theme or hyde_theme not in themes:
        hyde_theme = themes[0] if themes else ""
    hyde_theme_dir = os.path.join(hyde_conf_dir, "themes", hyde_theme)

    # 3) read style arg
    style = sys.argv[1] if len(sys.argv)>1 else "1"
    layout = os.path.join(conf_dir, "wlogout", f"layout_{style}")
    tpl    = os.path.join(conf_dir, "wlogout", f"style_{style}.css")
    if not (os.path.isfile(layout) and os.path.isfile(tpl)):
        style = "1"
        layout = os.path.join(conf_dir, "wlogout", "layout_1")
        tpl    = os.path.join(conf_dir, "wlogout", "style_1.css")

    # 4) monitor geometry & scale
    mon = get_focused_monitor()
    x_mon = mon.get("width",0)
    y_mon = mon.get("height",0)
    scale = str(mon.get("scale",1.0)).replace(".","")
    hypr_scale = int(scale) if scale.isdigit() else 1

    # 5) compute all the CSS vars
    env = {}
    border = get_hypr_border()
    if style == "1":
        wl_cols = 6
        env["mgn"] = str(y_mon * 28 // hypr_scale)
        env["hvr"] = str(y_mon * 23 // hypr_scale)
    else:
        wl_cols = 2
        env["x_mgn"] = str(x_mon * 35 // hypr_scale)
        env["y_mgn"] = str(y_mon * 25 // hypr_scale)
        env["x_hvr"] = str(x_mon * 32 // hypr_scale)
        env["y_hvr"] = str(y_mon * 20 // hypr_scale)

    env["fntSize"]   = str(y_mon * 2 // 100)
    env.update(parse_env_file(os.path.join(cache_dir, "wall.dcol")))

    # 6) color‐scheme / dcol_mode
    dcol = ""
    if enableWallDcol == 0:
        # try hypr.theme
        theme_file = os.path.join(hyde_theme_dir, "hypr.theme")
        cs = ""
        if os.path.isfile(theme_file):
            txt = open(theme_file).read()
            m = re.search(r'^\s*\$COLOR[-_]SCHEME\s*=\s*(.+)$', txt, flags=re.M)
            if m:
                cs = m.group(1).strip().strip('"').strip("'")
            else:
                m2 = re.search(
                  r"gsettings set org\.gnome\.desktop\.interface color-scheme '([^']+)'",
                  txt)
                if m2:
                    cs = m2.group(1)
        if not cs:
            cs = run(
              ["gsettings","get","org.gnome.desktop.interface","color-scheme"],
              capture_output=True, text=True
            ).stdout.strip().strip("'")
        if "dark" in cs.lower():   dcol="dark"
        if "light" in cs.lower():  dcol="light"
        env.update(parse_env_file(os.path.join(hyde_theme_dir, "theme.dcol")))
    env["dcol_mode"] = dcol
    env["BtnCol"]    = "white" if dcol=="dark" else "black"
    env["active_rad"]= str(border * 5)
    env["button_rad"]= str(border * 8)

    # 7) substitute CSS & write temp file
    css_txt = open(tpl).read()
    full_map = {**os.environ, **env}
    out_css = envsubst(css_txt, full_map)

    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".css", mode="w")
    tf.write(out_css); tf.flush(); tf.close()

    # 8) finally launch wlogout with the same flags
    run([
        "wlogout",
        "-b", str(wl_cols),
        "-c", "0","-r","0","-m","0",
        "--layout", layout,
        "--css", tf.name,
        "--protocol", "layer-shell"
    ])

if __name__ == "__main__":
    main()
