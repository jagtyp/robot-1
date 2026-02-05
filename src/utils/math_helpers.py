def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation from a to b by factor t (0.0-1.0)."""
    return a + (b - a) * t


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min_val and max_val."""
    return max(min_val, min(max_val, value))
