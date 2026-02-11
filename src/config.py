from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class DisplayConfig:
    spi_speed_hz: int = 62_500_000
    fps_target: int = 30


@dataclass
class EyeConfig:
    iris_color: tuple = (200, 30, 20)
    sclera_radius: int = 110
    iris_radius: int = 65
    pupil_radius: int = 30
    pupil_max_offset: int = 45
    assets_dir: str = "assets/eyes"


@dataclass
class AnimationConfig:
    blink_interval_min: float = 2.0
    blink_interval_max: float = 6.0
    blink_duration: float = 0.2
    pursuit_smoothing: float = 0.15
    idle_interval_min: float = 1.5
    idle_interval_max: float = 4.0
    idle_range_x: float = 0.6
    idle_range_y: float = 0.3


@dataclass
class TrackingConfig:
    lores_width: int = 160
    lores_height: int = 120
    motion_history: int = 30
    motion_threshold: int = 25
    motion_min_area: int = 150
    smoothing: float = 0.3
    lost_timeout: float = 3.0


@dataclass
class DebugConfig:
    web_port: int = 8080


@dataclass
class Config:
    display: DisplayConfig = field(default_factory=DisplayConfig)
    eyes: EyeConfig = field(default_factory=EyeConfig)
    animation: AnimationConfig = field(default_factory=AnimationConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    debug: DebugConfig = field(default_factory=DebugConfig)
    log_level: str = "INFO"


def load_config(path: str = "config.yaml") -> Config:
    """Load config from YAML file, falling back to defaults for missing keys."""
    config = Config()
    config_path = Path(path)

    if not config_path.exists():
        return config

    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    if "display" in data:
        d = data["display"]
        config.display = DisplayConfig(
            spi_speed_hz=d.get("spi_speed_hz", config.display.spi_speed_hz),
            fps_target=d.get("fps_target", config.display.fps_target),
        )

    if "eyes" in data:
        e = data["eyes"]
        config.eyes = EyeConfig(
            iris_color=tuple(e.get("iris_color", list(config.eyes.iris_color))),
            sclera_radius=e.get("sclera_radius", config.eyes.sclera_radius),
            iris_radius=e.get("iris_radius", config.eyes.iris_radius),
            pupil_radius=e.get("pupil_radius", config.eyes.pupil_radius),
            pupil_max_offset=e.get("pupil_max_offset", config.eyes.pupil_max_offset),
        )

    if "animation" in data:
        a = data["animation"]
        config.animation = AnimationConfig(
            blink_interval_min=a.get("blink_interval_min", config.animation.blink_interval_min),
            blink_interval_max=a.get("blink_interval_max", config.animation.blink_interval_max),
            blink_duration=a.get("blink_duration", config.animation.blink_duration),
            pursuit_smoothing=a.get("pursuit_smoothing", config.animation.pursuit_smoothing),
            idle_interval_min=a.get("idle_interval_min", config.animation.idle_interval_min),
            idle_interval_max=a.get("idle_interval_max", config.animation.idle_interval_max),
            idle_range_x=a.get("idle_range_x", config.animation.idle_range_x),
            idle_range_y=a.get("idle_range_y", config.animation.idle_range_y),
        )

    if "tracking" in data:
        t = data["tracking"]
        config.tracking = TrackingConfig(
            lores_width=t.get("lores_width", config.tracking.lores_width),
            lores_height=t.get("lores_height", config.tracking.lores_height),
            motion_history=t.get("motion_history", config.tracking.motion_history),
            motion_threshold=t.get("motion_threshold", config.tracking.motion_threshold),
            motion_min_area=t.get("motion_min_area", config.tracking.motion_min_area),
            smoothing=t.get("smoothing", config.tracking.smoothing),
            lost_timeout=t.get("lost_timeout", config.tracking.lost_timeout),
        )

    if "debug" in data:
        config.debug = DebugConfig(
            web_port=data["debug"].get("web_port", config.debug.web_port),
        )

    if "logging" in data:
        config.log_level = data["logging"].get("level", config.log_level)

    return config
