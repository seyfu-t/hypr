#!/usr/bin/env python
"""Screenshot handler for various modes using grimblast and swappy."""
import os
import sys
import subprocess
from datetime import datetime

# Set directories
conf_dir = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
swpy_dir = os.path.join(conf_dir, "swappy")
save_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.getenv("XDG_PICTURES_DIR", os.path.expanduser("~/Pictures")), "Screenshots")

# Filename and temp path
save_file = datetime.now().strftime("%y%m%d_%Hh%Mm%Ss_screenshot.png")
temp_screenshot = "/tmp/screenshot.png"

# Ensure directories exist
os.makedirs(save_dir, exist_ok=True)
os.makedirs(swpy_dir, exist_ok=True)

# Write swappy config
with open(os.path.join(swpy_dir, "config"), "w") as f:
    f.write(f"[Default]\nsave_dir={save_dir}\nsave_filename_format={save_file}\n")

def print_error():
    print("""
    screenshot.py <action>
    ...valid actions are...
        p  : print all screens
        s  : snip current screen
        sf : snip current screen (frozen)
        m  : print focused monitor
    """, file=sys.stderr)
    sys.exit(1)

def run_grimblast(mode):
    try:
        if mode == "sf":
            subprocess.run(["grimblast", "--freeze", "copysave", "area", temp_screenshot], check=True)
        else:
            modes = {
                "p": ["screen"],
                "s": ["area"],
                "m": ["output"]
            }
            subprocess.run(["grimblast", "copysave"] + modes[mode] + [temp_screenshot], check=True)
        subprocess.run(["swappy", "-f", temp_screenshot], check=True)
    except subprocess.CalledProcessError:
        print("Failed to capture or edit screenshot.", file=sys.stderr)
        sys.exit(1)

def notify():
    screenshot_path = os.path.join(save_dir, save_file)
    if os.path.exists(screenshot_path):
        subprocess.run(["notify-send", "-a", "t1", "-i", screenshot_path, f"saved in {save_dir}"])

if len(sys.argv) < 2:
    print_error()

mode = sys.argv[1]
if mode not in ("p", "s", "sf", "m"):
    print_error()

run_grimblast(mode)

try:
    os.remove(temp_screenshot)
except FileNotFoundError:
    pass

notify()