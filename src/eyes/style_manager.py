"""Thread-safe eye style registry and runtime switcher."""

import logging
import threading
from pathlib import Path

from src.config import EyeConfig
from src.eyes.eye_renderer import EyeRenderer
from src.eyes.sprite_renderer import SpriteEyeRenderer
from src.eyes.cartoon_renderer import CartoonEyeRenderer
from src.eyes.cartoon_moods import CARTOON_MOODS

log = logging.getLogger("robot-head")


class StyleManager:
    """Discovers available eye styles and manages the active renderer pair."""

    def __init__(self, config: EyeConfig):
        self._config = config
        self._lock = threading.Lock()
        self._styles: dict[str, dict] = {}
        self._active_id: str = "procedural"
        self._left: object = None
        self._right: object = None

        # Register the built-in procedural style
        self._styles["procedural"] = {
            "id": "procedural",
            "name": "Procedural (Red Iris)",
            "type": "procedural",
        }

        # Register cartoon style
        self._styles["cartoon"] = {
            "id": "cartoon",
            "name": "Cartoon Eyes",
            "type": "cartoon",
        }

        # Discover sprite styles from assets directory
        assets_dir = Path(config.assets_dir)
        if not assets_dir.is_absolute():
            # Resolve relative to project root
            project_root = Path(__file__).parent.parent.parent
            assets_dir = project_root / assets_dir

        if assets_dir.is_dir():
            for png in sorted(assets_dir.glob("*.png")):
                style_id = f"sprite_{png.stem}"
                name = png.stem.replace("_", " ").title()
                self._styles[style_id] = {
                    "id": style_id,
                    "name": name,
                    "type": "sprite",
                    "path": str(png),
                }
                log.info(f"Discovered sprite style: {name} ({png.name})")

        # Create initial renderers
        self._create_renderers(self._active_id)

    def _create_renderers(self, style_id: str):
        style = self._styles[style_id]
        if style["type"] == "procedural":
            self._left = EyeRenderer(self._config)
            self._right = EyeRenderer(self._config)
        elif style["type"] == "sprite":
            self._left = SpriteEyeRenderer(self._config, style["path"])
            self._right = SpriteEyeRenderer(self._config, style["path"])
        elif style["type"] == "cartoon":
            self._left = CartoonEyeRenderer(self._config, is_left=True)
            self._right = CartoonEyeRenderer(self._config, is_left=False)

    def get_styles(self) -> list[dict]:
        """Return list of all available styles with active flag."""
        with self._lock:
            result = []
            for style in self._styles.values():
                entry = {
                    "id": style["id"],
                    "name": style["name"],
                    "active": style["id"] == self._active_id,
                }
                result.append(entry)
            return result

    def get_active_id(self) -> str:
        with self._lock:
            return self._active_id

    def set_active_style(self, style_id: str) -> bool:
        """Switch to a different style. Returns True on success."""
        with self._lock:
            if style_id not in self._styles:
                return False
            if style_id == self._active_id:
                return True
            self._active_id = style_id
            self._create_renderers(style_id)
            log.info(f"Switched eye style to: {self._styles[style_id]['name']}")
            return True

    def get_renderers(self):
        """Return (left_renderer, right_renderer). Safe to call from render loop."""
        with self._lock:
            return self._left, self._right

    def get_cartoon_moods(self) -> list[dict] | None:
        """Return mood list with active flag, or None if not in cartoon mode."""
        with self._lock:
            if self._styles.get(self._active_id, {}).get("type") != "cartoon":
                return None
            active_mood = self._left.mood_id if self._left else "neutral"
            result = []
            for mood in CARTOON_MOODS.values():
                result.append({
                    "id": mood.id,
                    "name": mood.name,
                    "active": mood.id == active_mood,
                })
            return result

    def set_cartoon_mood(self, mood_id: str) -> bool:
        """Switch cartoon mood on both renderers. Returns True on success."""
        with self._lock:
            if self._styles.get(self._active_id, {}).get("type") != "cartoon":
                return False
            if mood_id not in CARTOON_MOODS:
                return False
            self._left.set_mood(mood_id)
            self._right.set_mood(mood_id)
            log.info(f"Switched cartoon mood to: {mood_id}")
            return True

    def get_cartoon_glow(self) -> bool | None:
        """Return glow state, or None if not in cartoon mode."""
        with self._lock:
            if self._styles.get(self._active_id, {}).get("type") != "cartoon":
                return None
            return self._left.glow_enabled

    def set_cartoon_glow(self, enabled: bool) -> bool:
        """Toggle glow on both cartoon renderers. Returns True on success."""
        with self._lock:
            if self._styles.get(self._active_id, {}).get("type") != "cartoon":
                return False
            self._left.glow_enabled = enabled
            self._right.glow_enabled = enabled
            log.info(f"Cartoon glow: {'on' if enabled else 'off'}")
            return True
