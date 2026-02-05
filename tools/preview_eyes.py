#!/usr/bin/env python3
"""Renders eye images to PNG files for testing on a desktop (no Pi hardware needed)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import EyeConfig
from src.eyes.eye_state import EyeState
from src.eyes.eye_renderer import EyeRenderer


def main():
    config = EyeConfig(iris_color=(200, 30, 20))
    renderer = EyeRenderer(config)

    previews = {
        "center": EyeState(is_left=True),
        "look_left": EyeState(pupil_x=-0.7, pupil_y=0.0, is_left=True),
        "look_right": EyeState(pupil_x=0.7, pupil_y=0.0, is_left=True),
        "look_up": EyeState(pupil_x=0.0, pupil_y=-0.5, is_left=True),
        "blink_half": EyeState(upper_eyelid=0.5, lower_eyelid=0.2, is_left=True),
        "blink_full": EyeState(upper_eyelid=1.0, lower_eyelid=0.4, is_left=True),
        "angry": EyeState(brow_angle=-0.3, squint=0.2, pupil_scale=0.8, is_left=True),
        "surprised": EyeState(pupil_scale=1.4, is_left=True),
        "right_eye": EyeState(is_left=False),
    }

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview_output")
    os.makedirs(out_dir, exist_ok=True)

    for name, state in previews.items():
        img = renderer.render(state)
        path = os.path.join(out_dir, f"{name}.png")
        # Copy image since renderer reuses internal buffer
        img.copy().save(path)
        print(f"Saved {path}")

    print(f"\nAll previews saved to {out_dir}/")


if __name__ == "__main__":
    main()
