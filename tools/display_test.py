#!/usr/bin/env python3
"""Hardware test: fills each display with solid colors to verify wiring."""

import sys
import time
sys.path.insert(0, "/opt/robot-head")

from src.hardware.gpio_map import GPIOMap
from src.display.gc9a01 import GC9A01


def rgb565(r, g, b):
    """Convert 8-bit RGB to RGB565."""
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


COLORS = [
    ("Red",     rgb565(255, 0, 0)),
    ("Green",   rgb565(0, 255, 0)),
    ("Blue",    rgb565(0, 0, 255)),
    ("White",   rgb565(255, 255, 255)),
    ("Black",   rgb565(0, 0, 0)),
]


def main():
    pins = GPIOMap()

    print("Initializing left display (CE0)...")
    left = GC9A01(0, 0, pins.LEFT_DC, pins.LEFT_RST, pins.LEFT_BL)
    left.init_display()

    print("Initializing right display (CE1)...")
    right = GC9A01(0, 1, pins.RIGHT_DC, pins.RIGHT_RST, pins.RIGHT_BL)
    right.init_display()

    print("Display test - cycling colors on both displays")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            for name, color in COLORS:
                print(f"  {name}...")
                left.fill(color)
                right.fill(color)
                time.sleep(1.5)
    except KeyboardInterrupt:
        print("\nCleaning up...")
        left.fill(0x0000)
        right.fill(0x0000)
        left.cleanup()
        right.cleanup()
        import RPi.GPIO as GPIO
        GPIO.cleanup()
        print("Done")


if __name__ == "__main__":
    main()
