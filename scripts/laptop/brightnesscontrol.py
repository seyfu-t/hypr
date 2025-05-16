#!/usr/bin/env python
"""Adjust screen brightness and send notifications via notify-send."""
import os
import sys
import re
import subprocess

def is_running():
    script = os.path.basename(sys.argv[0])
    if int(subprocess.check_output(["pgrep", "-cf", script]).strip()) > 1:
        print("An instance of the script is already running...", file=sys.stderr)
        sys.exit(1)

def get_brightness():
    out = subprocess.check_output(["brightnessctl", "-m"], text=True)
    m = re.search(r"(\d+)%", out)
    return int(m.group(1)) if m else 0

def send_notification():
    brightness = get_brightness()
    info = subprocess.check_output(["brightnessctl", "info"], text=True)
    name_match = re.search(r"Device '([^']+)'", info)
    name = name_match.group(1) if name_match else ''
    angle = ((brightness + 2) // 5) * 5
    ico = os.path.expanduser(f"~/.config/dunst/icons/vol/vol-{angle}.svg")
    bar = '.' * (brightness // 15)
    subprocess.run([
        "notify-send", "-a", "brightness", "-r", "91190", "-t", "800", "-i", ico,
        f"{brightness}{bar}", name
    ])

def error():
    name = os.path.basename(sys.argv[0])
    print(f"Usage: {name} <i|d> [step] [-q]\n"
          "   i: increase brightness\n"
          "   d: decrease brightness\n"
          "   -q: quiet (no notification)",
          file=sys.stderr)
    sys.exit(1)

def main():
    is_running()
    notify = True
    action = None
    step = 5

    for arg in sys.argv[1:]:
        if arg in ('i', '-i'):
            if action: error()
            action = 'increase'
        elif arg in ('d', '-d'):
            if action: error()
            action = 'decrease'
        elif arg == '-q':
            notify = False
        elif re.fullmatch(r'\d+', arg):
            step = int(arg)
        else:
            error()

    if not action:
        error()

    current = get_brightness()
    if action == 'increase':
        if current < 10:
            step = 1
        subprocess.run(['brightnessctl', 'set', f'+{step}%'])
    else:  # decrease
        if current <= 10:
            step = 1
        if current <= 1:
            subprocess.run(['brightnessctl', 'set', f'{step}%'])
        else:
            subprocess.run(['brightnessctl', 'set', f'{step}%-'])

    if notify:
        send_notification()

if __name__ == '__main__':
    main()
