"""Sprite-based eye renderer: loads a pre-made eye image and shifts it for gaze."""

from pathlib import Path
from PIL import Image, ImageDraw

from src.eyes.eye_state import EyeState
from src.eyes.eyelid_mixin import EyelidMixin
from src.config import EyeConfig


class SpriteEyeRenderer(EyelidMixin):
    """Renders an eye by cropping a shifted region from a sprite image."""

    SIZE = 240
    CENTER = 120
    SPRITE_SIZE = 350

    def __init__(self, config: EyeConfig, sprite_path: str):
        self._sclera_r = config.sclera_radius
        self._max_offset = 55

        # Load and prepare the sprite
        self._sprite = Image.open(sprite_path).convert("RGB")
        if self._sprite.size != (self.SPRITE_SIZE, self.SPRITE_SIZE):
            self._sprite = self._sprite.resize(
                (self.SPRITE_SIZE, self.SPRITE_SIZE), Image.LANCZOS
            )

        # Pre-compute circular mask (white circle on black)
        self._mask = Image.new("L", (self.SIZE, self.SIZE), 0)
        mask_draw = ImageDraw.Draw(self._mask)
        mask_draw.ellipse(
            [self.CENTER - self._sclera_r, self.CENTER - self._sclera_r,
             self.CENTER + self._sclera_r, self.CENTER + self._sclera_r],
            fill=255,
        )

        # Pre-allocate output image
        self._img = Image.new("RGB", (self.SIZE, self.SIZE), (0, 0, 0))
        self._draw = ImageDraw.Draw(self._img)

        # Center of sprite where crop origin starts
        self._sprite_center = self.SPRITE_SIZE // 2

    def render(self, state: EyeState) -> Image.Image:
        # Compute crop offset based on gaze
        offset_x = int(-state.pupil_x * self._max_offset)
        offset_y = int(-state.pupil_y * self._max_offset)

        # Crop region centered on sprite_center + offset
        half = self.SIZE // 2
        cx = self._sprite_center + offset_x
        cy = self._sprite_center + offset_y

        left = cx - half
        top = cy - half

        # Crop the 240x240 region from the sprite
        cropped = self._sprite.crop((left, top, left + self.SIZE, top + self.SIZE))

        # Clear to black, paste cropped sprite through circular mask
        self._img.paste((0, 0, 0), (0, 0, self.SIZE, self.SIZE))
        self._img.paste(cropped, (0, 0), self._mask)

        # Draw eyelids on top
        self._draw_eyelid_upper(self._draw, state.upper_eyelid,
                                state.brow_angle, state.squint)
        self._draw_eyelid_lower(self._draw, state.lower_eyelid, state.squint)

        return self._img
