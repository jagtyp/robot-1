#!/usr/bin/env python3
"""Preprocess raw eye asset images into clean 350x350 sprites on black backgrounds."""

from pathlib import Path
from PIL import Image

ASSETS_DIR = Path(__file__).parent.parent / "assets"
OUTPUT_DIR = ASSETS_DIR / "eyes"
TARGET_SIZE = 350

# Map raw filenames to clean output names
FILE_MAP = {
    "png-transparent-eye-iris-robotic-vision-vista-eyeball-bionic-eye-sphere-optical.png": "robotic_eyeball.png",
    "images.jpg": "camera_lens.png",
    "transparent-eyelashes-1711070942673.webp": "cyber_eye.png",
    "human-eye-robotic-art-robotics-png-favpng-5WR1tDQtAfAQkKLCg332pvGsE.jpg": "bloodshot.png",
}


def process_image(src_path: Path, dst_path: Path):
    img = Image.open(src_path).convert("RGBA")

    # Composite onto black background
    black = Image.new("RGBA", img.size, (0, 0, 0, 255))
    composited = Image.alpha_composite(black, img).convert("RGB")

    # Center-crop to square
    w, h = composited.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    cropped = composited.crop((left, top, left + side, top + side))

    # Resize to target
    resized = cropped.resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)

    resized.save(dst_path)
    print(f"  {src_path.name} -> {dst_path.name} ({TARGET_SIZE}x{TARGET_SIZE})")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Processing eye sprites to {OUTPUT_DIR}/")

    for raw_name, clean_name in FILE_MAP.items():
        src = ASSETS_DIR / raw_name
        dst = OUTPUT_DIR / clean_name
        if not src.exists():
            print(f"  WARNING: {raw_name} not found, skipping")
            continue
        process_image(src, dst)

    print("Done!")


if __name__ == "__main__":
    main()
