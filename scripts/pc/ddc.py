#!/usr/bin/env python
"""Set DDC input source for all connected monitors using ddcutil."""
import re
import subprocess
import sys

def get_ddc_buses():
    try:
        output = subprocess.check_output(["ddcutil", "detect"], text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running ddcutil detect: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract all /dev/i2c-X buses
    buses = re.findall(r"I2C bus:\s+/dev/i2c-(\d+)", output)
    return sorted(set(buses))

def set_ddc_input(bus: str, value: str):
    try:
        subprocess.run(["ddcutil", "--bus", bus, "setvcp", "10", value], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to set DDC input on bus {bus}: {e}", file=sys.stderr)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input>", file=sys.stderr)
        sys.exit(1)

    input_value = sys.argv[1]
    buses = get_ddc_buses()

    if not buses:
        print("No DDC-capable displays found.", file=sys.stderr)
        sys.exit(1)

    for bus in buses:
        set_ddc_input(bus, input_value)

    print(f"DDC input set to '{input_value}' for all detected monitors.")

if __name__ == "__main__":
    main()
