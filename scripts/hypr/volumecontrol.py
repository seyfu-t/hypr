#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import shutil
import tempfile
import base64

def run_cmd(cmd, capture_output=True, text=True, check=False, input=None, shell=False):
    """Run a subprocess command and return CompletedProcess."""
    return subprocess.run(cmd, capture_output=capture_output, text=text,
                          check=check, input=input, shell=shell)

def get_conf_dir():
    """Return XDG config directory (default ~/.config)."""
    return os.environ.get("XDG_CONFIG_HOME",
                          os.path.expanduser("~/.config"))

def notify_send(summary, body="", icon=None, urgency="normal"):
    """Send a desktop notification."""
    args = ["notify-send", "-a", "volumecontrol", "-r", "91190", "-t", "800"]
    if icon:
        args += ["-i", icon]
    if urgency:
        args += ["-u", urgency]
    args += [summary, body]
    subprocess.run(args)

def has_swayosd():
    """Check if swayosd-client & server are available."""
    client = shutil.which("swayosd-client")
    server = run_cmd(["pgrep", "-x", "swayosd-server"], capture_output=True)
    return bool(client and server.stdout.strip())

USE_SWAYOSD = has_swayosd()

def rofi_menu(lines, config_path, placeholder="Select…"):
    """
    Show a simple rofi dmenu and return the chosen line.
    Uses the given rofi config file.
    """
    menu = "\n".join(lines)
    p = run_cmd([
        "rofi", "-dmenu",
        "-theme-str", f'entry {{ placeholder: "{placeholder}"; }}',
        "-config", config_path
    ], input=menu)
    return p.stdout.strip()

def print_usage():
    usage = """
Usage: volumecontrol.py -[i|o|p <player>] [-s | -t] <action> [step]

Devices:
  -i                Input (microphone)
  -o                Output (speaker)
  -p PLAYER         Player application (e.g. spotify)

Other:
  -s                Select output device via menu
  -t                Toggle to next output device

Actions:
  i                 Increase volume
  d                 Decrease volume
  m                 Toggle mute

Step (optional):
  Integer percent (default: 5)
"""
    print(usage, file=sys.stderr)
    sys.exit(1)

def get_default_sink_name():
    out = run_cmd(["pamixer", "--get-default-sink"], text=True).stdout
    parts = out.strip().split('"')
    return parts[-2] if len(parts) >= 2 else out.strip()

def get_default_source_name():
    out = run_cmd(["pamixer", "--list-sources"], text=True).stdout
    # last quoted field
    parts = out.strip().split('"')
    return parts[-2] if len(parts) >= 2 else out.strip()

def list_sinks():
    """Return sorted list of available sink descriptions."""
    out = run_cmd("pactl list sinks", text=True, shell=True).stdout.splitlines()
    descs = []
    for line in out:
        if line.strip().startswith("Description:"):
            _, val = line.split(":", 1)
            descs.append(val.strip())
    return sorted(set(descs))

def select_output(selection=None):
    """
    If selection is provided, set it as default sink.
    Otherwise return the list of descriptions.
    """
    config = os.path.join(get_conf_dir(), "rofi", "notification.rasi")
    if selection:
        # replicate: pactl list sinks | grep -C2 -F "Description: {selection}" \
        #           | grep Name | cut -d: -f2 | xargs
        cmd = (
            "pactl list sinks | "
            f"grep -C2 -F 'Description: {selection}' | "
            "grep Name | cut -d: -f2 | xargs"
        )
        device = run_cmd(cmd, shell=True).stdout.strip()
        if device:
            res = run_cmd(["pactl", "set-default-sink", device])
            if res.returncode == 0:
                notify_send(f"Activated: {selection}")
            else:
                notify_send(f"Error activating {selection}", urgency="critical")
        return
    else:
        return list_sinks()

def toggle_output():
    """Cycle through sinks and switch to the next one."""
    default = get_default_sink_name()
    sinks = select_output()
    if not sinks:
        return
    try:
        idx = sinks.index(default)
    except ValueError:
        idx = 0
    next_idx = (idx + 1) % len(sinks)
    select_output(sinks[next_idx])

def compute_notify_bar(volume):
    """Build a progress bar of dots for the notification."""
    count = max(0, min(20, volume // 15))  # limit to ~20 dots
    return "." * count

def notify_volume(level, nsink):
    """Notify current volume level."""
    angle = ((level + 2) // 5) * 5
    ico = os.path.join(get_conf_dir(), "dunst", "icons", "vol",
                       f"vol-{angle}.svg")
    bar = compute_notify_bar(level)
    notify_send(f"{level}{bar}", nsink, icon=ico)

def notify_mute(srce, nsink):
    """Notify mute/unmute status."""
    mute = run_cmd(["pamixer", srce, "--get-mute"], text=True).stdout.strip()
    dvce = "mic" if srce == "--default-source" else "speaker"
    icon_name = "muted" if mute == "true" else "unmuted"
    ico = os.path.join(get_conf_dir(), "dunst", "icons", "vol",
                       f"{icon_name}-{dvce}.svg")
    action = "muted" if mute == "true" else "unmuted"
    notify_send(action, nsink, icon=ico)

def change_volume(action, step, device, srce, nsink):
    """
    Change volume up/down for pamixer or playerctl.
    action: 'i' or 'd'
    step: integer percent
    """
    delta = "+" if action == "i" else "-"
    mode_flag = "--output-volume"
    if srce == "--default-source":
        mode_flag = "--input-volume"

    if device == "pamixer":
        if USE_SWAYOSD:
            subprocess.run(["swayosd-client",
                            mode_flag, f"{delta}{step}"])
            return
        run_cmd(["pamixer", srce, f"-{action}", str(step)], check=True)
        level = int(run_cmd(
            ["pamixer", srce, "--get-volume"], text=True).stdout.strip())
        notify_volume(level, nsink)

    elif device == "playerctl":
        # build e.g. "0.05+" or "0.10-"
        frac = step / 100.0
        expr = f"{frac}{delta}"
        run_cmd(["playerctl", "--player", srce, "volume", expr], check=True)
        out = run_cmd(["playerctl", "--player", srce, "volume"],
                      text=True).stdout.strip()
        level = round(float(out) * 100)
        notify_volume(level, nsink)

def toggle_mute_action(device, srce, nsink):
    """Toggle mute for pamixer or playerctl."""
    if device == "pamixer":
        if USE_SWAYOSD:
            subprocess.run(["swayosd-client",
                            "--output-volume" if srce != "--default-source" else "--input-volume",
                            "mute-toggle"])
            return
        run_cmd(["pamixer", srce, "-t"], check=True)
        notify_mute(srce, nsink)

    elif device == "playerctl":
        # remember last volume in temp file
        key = srce or "all"
        vol_file = os.path.join(tempfile.gettempdir(),
                                f"volumecontrol_last_{key}")
        out = run_cmd(["playerctl", "--player", srce, "volume"],
                      text=True).stdout.strip()
        current = float(out)
        if current > 0:
            # store and mute
            with open(vol_file, "w") as f:
                f.write(f"{current:.2f}")
            run_cmd(["playerctl", "--player", srce, "volume", "0"], check=True)
        else:
            # restore
            if os.path.exists(vol_file):
                with open(vol_file) as f:
                    last = f.read().strip()
                run_cmd(["playerctl", "--player", srce, "volume", last],
                        check=True)
            else:
                run_cmd(["playerctl", "--player", srce, "volume", "0.5"],
                        check=True)
        notify_mute(srce, nsink)

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-i", action="store_true")
    parser.add_argument("-o", action="store_true")
    parser.add_argument("-p", metavar="PLAYER", nargs="?", const="", type=str)
    parser.add_argument("-s", action="store_true")
    parser.add_argument("-t", action="store_true")
    parser.add_argument("action", nargs="?", choices=["i", "d", "m"])
    parser.add_argument("step", nargs="?", type=int, default=5)
    args = parser.parse_args()

    conf_dir = get_conf_dir()
    rofi_conf = os.path.join(conf_dir, "rofi", "notification.rasi")

    # Handle select/toggle output early
    if args.s:
        choices = select_output()
        if choices:
            choice = rofi_menu(choices, rofi_conf, placeholder="Select sink")
            if choice:
                select_output(choice)
        return
    if args.t:
        toggle_output()
        return

    # Determine device
    device = srce = nsink = None
    if args.i:
        device = "pamixer"
        srce = "--default-source"
        nsink = get_default_source_name()
    elif args.o:
        device = "pamixer"
        srce = ""
        nsink = get_default_sink_name()
    elif args.p is not None:
        device = "playerctl"
        srce = args.p
        nsink = args.p
    else:
        print_usage()

    if not args.action:
        print_usage()

    if args.action in ("i", "d"):
        change_volume(args.action, args.step, device, srce, nsink)
    elif args.action == "m":
        toggle_mute_action(device, srce, nsink)
    else:
        print_usage()

if __name__ == "__main__":
    main()
