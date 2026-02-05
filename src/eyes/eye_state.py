from dataclasses import dataclass


@dataclass
class EyeState:
    """Complete state of one eye for a single frame."""

    # Pupil position: 0.0 = center, -1.0..1.0 range
    pupil_x: float = 0.0
    pupil_y: float = 0.0

    # Eyelid closure: 0.0 = open, 1.0 = fully closed
    upper_eyelid: float = 0.0
    lower_eyelid: float = 0.0

    # Pupil dilation multiplier (1.0 = normal)
    pupil_scale: float = 1.0

    # Expression modifiers
    brow_angle: float = 0.0   # negative = angry, positive = surprised
    squint: float = 0.0       # 0.0 = none, 1.0 = full squint

    # Which eye (affects highlight position)
    is_left: bool = True
