#!/usr/bin/env python
import argparse
import subprocess

def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a subprocess command."""
    return subprocess.run(cmd, capture_output=True, text=True, check=False)

def notify(summary: str) -> None:
    """Send a simple desktop notification."""
    subprocess.run(["notify-send", "-a", "volumecontrol", summary])

def toggle_mute(source: bool) -> None:
    """Toggle mute for mic (source=True) or output (source=False)."""
    flag = "--default-source" if source else ""
    run_cmd(["pamixer", flag, "-t"])
    notify("Mic muted" if source else "Volume muted")

def change_volume(increase: bool, step: int = 5) -> None:
    """Increase or decrease volume by step %."""
    action = "-i" if increase else "-d"
    run_cmd(["pamixer", action, str(step)])
    vol = run_cmd(["pamixer", "--get-volume"]).stdout.strip()
    notify(f"Volume: {vol}%")

def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--mute-mic", action="store_true", help="Toggle mic mute")
    group.add_argument("--mute-vol", action="store_true", help="Toggle volume mute")
    group.add_argument("--inc", action="store_true", help="Increase volume")
    group.add_argument("--dec", action="store_true", help="Decrease volume")
    parser.add_argument("--step", type=int, default=5, help="Step percent for volume change")
    args = parser.parse_args()

    if args.mute_mic:
        toggle_mute(source=True)
    elif args.mute_vol:
        toggle_mute(source=False)
    elif args.inc:
        change_volume(increase=True, step=args.step)
    elif args.dec:
        change_volume(increase=False, step=args.step)

if __name__ == "__main__":
    main()
