#!/usr/bin/env python
"""
This script toggles window floating and pinning states based on the focused window.
"""
import json
import subprocess
import sys

def get_clients():
    """Fetch the list of clients from hyprctl as JSON."""
    try:
        output = subprocess.check_output(["hyprctl", "-j", "clients"], text=True)
        return json.loads(output)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching clients: {e}", file=sys.stderr)
        sys.exit(1)

def get_focused_client(clients):
    """Return the client dict where focusHistoryID == 0."""
    for client in clients:
        if client.get("focusHistoryID") == 0:
            return client
    return None

def dispatch(action, target="active"):
    """Run a hyprctl dispatch command."""
    try:
        subprocess.run(["hyprctl", "dispatch", action, target], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error dispatching {action}: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    clients = get_clients()
    focused = get_focused_client(clients)
    if not focused:
        print("No focused window found.", file=sys.stderr)
        sys.exit(1)

    floating = bool(focused.get("floating"))
    pinned = bool(focused.get("pinned"))

    # Enable float if neither floating nor pinned
    if not floating and not pinned:
        dispatch("togglefloating")

    # Toggle pin state
    dispatch("pin")

    # Re-fetch to get updated state
    clients = get_clients()
    focused = get_focused_client(clients)
    if not focused:
        print("No focused window found after pinning.", file=sys.stderr)
        sys.exit(1)

    floating = bool(focused.get("floating"))
    pinned = bool(focused.get("pinned"))

    # Disable float if it's floating but not pinned
    if floating and not pinned:
        dispatch("togglefloating")

if __name__ == "__main__":
    main()
