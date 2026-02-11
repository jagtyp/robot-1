"""Persist runtime UI settings (style, mood, glow, fps overlay) across restarts."""

import json
import logging
from pathlib import Path

log = logging.getLogger("robot-head")

_STATE_FILE = "state.json"

# Keys
ACTIVE_STYLE = "active_style"
CARTOON_MOOD = "cartoon_mood"
CARTOON_GLOW = "cartoon_glow"
SHOW_FPS = "show_fps"


def _state_path() -> Path:
    """Return the state file path next to the running process's cwd."""
    return Path(_STATE_FILE)


def load_state() -> dict:
    """Load persisted state from disk. Returns empty dict if missing or corrupt."""
    path = _state_path()
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        log.info(f"Loaded persisted state: {data}")
        return data
    except (json.JSONDecodeError, OSError) as e:
        log.warning(f"Could not load state file: {e}")
        return {}


def save_state(style_manager, debug_state=None):
    """Snapshot current settings to disk."""
    data = {}

    if style_manager:
        data[ACTIVE_STYLE] = style_manager.get_active_id()

        moods = style_manager.get_cartoon_moods()
        if moods is not None:
            for m in moods:
                if m["active"]:
                    data[CARTOON_MOOD] = m["id"]
                    break

        glow = style_manager.get_cartoon_glow()
        if glow is not None:
            data[CARTOON_GLOW] = glow

    if debug_state is not None:
        data[SHOW_FPS] = debug_state.show_fps

    try:
        with open(_state_path(), "w") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        log.warning(f"Could not save state file: {e}")


def apply_state(state: dict, style_manager, debug_state=None):
    """Apply previously loaded state to the running system."""
    if not state:
        return

    # Restore active style
    style_id = state.get(ACTIVE_STYLE)
    if style_id:
        if style_manager.set_active_style(style_id):
            log.info(f"Restored style: {style_id}")

    # Restore cartoon mood (only applies if cartoon is now active)
    mood_id = state.get(CARTOON_MOOD)
    if mood_id:
        if style_manager.set_cartoon_mood(mood_id):
            log.info(f"Restored cartoon mood: {mood_id}")

    # Restore glow
    glow = state.get(CARTOON_GLOW)
    if glow is not None:
        style_manager.set_cartoon_glow(glow)

    # Restore FPS overlay
    if debug_state is not None:
        show_fps = state.get(SHOW_FPS)
        if show_fps is not None:
            debug_state.show_fps = show_fps
