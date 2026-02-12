"""Autonomous mood engine — drives mood changes based on environmental signals.

State machine:
    SLEEPING ─(bright 5s)─> WAKING ─(3s)─> IDLE
       ^                                      |
       |                   face appears ──> ENGAGED ─(60s face)─> BONDED
       |                                     ^ |                    |
       |                   face lost 5s ─────+ |    face lost ─> IDLE (sad 3s)
       |                                       |
       |                   120s no face ──> BORED ─(face)─> ENGAGED (excited)
       |                                       |
       +───── dark for 30s (from any) ────────+

Runs on the main thread at ~2 Hz via tick(). No extra threads.
"""

import logging
import random
import time

log = logging.getLogger("robot-head")

# States
SLEEPING = "SLEEPING"
WAKING = "WAKING"
IDLE = "IDLE"
ENGAGED = "ENGAGED"
BONDED = "BONDED"
BORED = "BORED"

# Personality event pool (brief mood flashes during IDLE)
_IDLE_PERSONALITY = ["surprised", "mischievous", "wink", "star", "tired"]

# Bored mood rotation
_BORED_MOODS = ["tired", "confused", "sleepy", "sad"]

# Bonded affection moods
_BONDED_AFFECTION = ["happy", "love", "wink", "celebrating"]


class MoodEngine:
    """Reads environment snapshots and drives style_manager.set_mood()."""

    def __init__(self, config, style_manager):
        self._cfg = config
        self._sm = style_manager

        # Current state
        self._state = IDLE
        self._state_entered = time.monotonic()

        # Enabled / manual override
        self._enabled = True
        self._manual_override_until = 0.0  # monotonic time

        # Brightness tracking for state transitions
        self._bright_since = 0.0  # time brightness exceeded wake threshold
        self._dark_since = 0.0    # time brightness dropped below sleep threshold

        # IDLE personality timer
        self._next_personality = time.monotonic() + random.uniform(8, 15)
        self._personality_revert_at = 0.0

        # BORED mood rotation
        self._bored_mood_idx = 0
        self._bored_next_switch = 0.0

        # BONDED affection timer
        self._next_bonded_affection = 0.0

        # WAKING phase timer
        self._waking_phase2_at = 0.0  # when to switch from tired -> neutral

        # Greeting mood revert timer
        self._greeting_revert_at = 0.0

        # Sad-on-leave revert timer
        self._sad_revert_at = 0.0

        # Previous face state for edge detection
        self._prev_face_present = False

        log.info("MoodEngine initialized (state=IDLE)")

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        log.info(f"MoodEngine {'enabled' if value else 'disabled'}")

    @property
    def state(self) -> str:
        return self._state

    def notify_manual_mood(self):
        """Called when user manually sets mood via web UI.
        Pauses auto-mood for the configured duration."""
        self._manual_override_until = time.monotonic() + self._cfg.manual_pause_secs
        log.info(f"Auto-mood paused for {self._cfg.manual_pause_secs}s (manual override)")

    def get_status(self) -> dict:
        """Return current status for the debug API."""
        now = time.monotonic()
        override_remaining = max(0, self._manual_override_until - now)
        return {
            "enabled": self._enabled,
            "state": self._state,
            "override_remaining": round(override_remaining, 1),
        }

    def tick(self, dt: float, env: dict):
        """Advance the state machine. Called from render loop at ~2 Hz.

        Args:
            dt: time since last tick
            env: snapshot from EnvironmentState.get_snapshot()
        """
        if not self._enabled:
            return

        now = env["time"]

        # Manual override active — skip automatic mood changes
        if now < self._manual_override_until:
            return

        brightness = env["brightness"]
        face_present = env["face_present"]
        face_continuous = env["face_continuous_secs"]
        face_lost_ago = env["face_lost_ago"]
        motion = env["motion_level"]

        # --- Global transition: dark -> SLEEPING (from any state) ---
        if brightness < self._cfg.sleep_brightness:
            if self._dark_since == 0:
                self._dark_since = now
            elif (now - self._dark_since) >= self._cfg.dark_to_sleep_secs and self._state != SLEEPING:
                self._transition(SLEEPING, now)
                self._set_mood("sleepy")
                return
        else:
            self._dark_since = 0

        # --- Track how long it's been bright ---
        if brightness >= self._cfg.wake_brightness:
            if self._bright_since == 0:
                self._bright_since = now
        else:
            self._bright_since = 0

        # Face edge detection
        face_appeared = face_present and not self._prev_face_present
        face_lost = not face_present and self._prev_face_present
        self._prev_face_present = face_present

        # --- State-specific logic ---
        if self._state == SLEEPING:
            self._tick_sleeping(now, face_appeared)

        elif self._state == WAKING:
            self._tick_waking(now)

        elif self._state == IDLE:
            self._tick_idle(now, face_appeared, face_lost_ago, motion)

        elif self._state == ENGAGED:
            self._tick_engaged(now, face_present, face_continuous, face_lost, face_lost_ago)

        elif self._state == BONDED:
            self._tick_bonded(now, face_present, face_lost)

        elif self._state == BORED:
            self._tick_bored(now, face_appeared)

    def _transition(self, new_state: str, now: float):
        log.info(f"MoodEngine: {self._state} -> {new_state}")
        self._state = new_state
        self._state_entered = now

    def _set_mood(self, mood_id: str):
        self._sm.set_mood(mood_id)

    # --- SLEEPING ---
    def _tick_sleeping(self, now, face_appeared):
        # Wake on bright light for 5s
        if self._bright_since > 0 and (now - self._bright_since) >= self._cfg.bright_to_wake_secs:
            self._start_waking(now)
            return
        # Wake on face appearing
        if face_appeared:
            self._start_waking(now)

    def _start_waking(self, now):
        self._transition(WAKING, now)
        self._set_mood("tired")
        self._waking_phase2_at = now + self._cfg.waking_duration / 2

    # --- WAKING ---
    def _tick_waking(self, now):
        # Phase 2: switch from tired to neutral halfway through
        if now >= self._waking_phase2_at and self._waking_phase2_at > 0:
            self._set_mood("neutral")
            self._waking_phase2_at = 0  # only once

        # Done waking
        if (now - self._state_entered) >= self._cfg.waking_duration:
            self._transition(IDLE, now)
            self._set_mood("neutral")
            self._next_personality = now + random.uniform(8, 15)

    # --- IDLE ---
    def _tick_idle(self, now, face_appeared, face_lost_ago, motion):
        # Revert sad-on-leave mood
        if self._sad_revert_at and now >= self._sad_revert_at:
            self._set_mood("neutral")
            self._sad_revert_at = 0

        # Revert personality flash
        if self._personality_revert_at and now >= self._personality_revert_at:
            self._set_mood("neutral")
            self._personality_revert_at = 0

        # Face appeared -> ENGAGED
        if face_appeared:
            self._transition(ENGAGED, now)
            self._set_mood("happy")
            self._greeting_revert_at = now + 3.0
            return

        # Motion surprise (only if not in a personality flash)
        if motion > self._cfg.motion_surprise_threshold and not self._personality_revert_at:
            self._set_mood("surprised")
            self._personality_revert_at = now + 2.0
            self._next_personality = now + random.uniform(8, 15)
            return

        # Long idle -> BORED
        time_in_state = now - self._state_entered
        if time_in_state >= self._cfg.idle_to_bored_secs:
            self._transition(BORED, now)
            self._bored_mood_idx = 0
            self._set_mood(_BORED_MOODS[0])
            self._bored_next_switch = now + self._cfg.bored_mood_cycle_secs
            return

        # Personality events (random rolls)
        if now >= self._next_personality and not self._personality_revert_at:
            mood = random.choice(_IDLE_PERSONALITY)
            self._set_mood(mood)
            self._personality_revert_at = now + random.uniform(2.0, 4.0)
            self._next_personality = now + random.uniform(
                self._cfg.personality_interval_min, self._cfg.personality_interval_max)

    # --- ENGAGED ---
    def _tick_engaged(self, now, face_present, face_continuous, face_lost, face_lost_ago):
        # Greeting revert
        if self._greeting_revert_at and now >= self._greeting_revert_at:
            self._set_mood("neutral")
            self._greeting_revert_at = 0

        # Long face -> BONDED
        if face_continuous >= self._cfg.engaged_to_bonded_secs:
            self._transition(BONDED, now)
            self._set_mood("neutral")
            self._next_bonded_affection = now + random.uniform(10, 20)
            return

        # Face lost -> back to IDLE with brief sadness
        if not face_present and face_lost_ago >= self._cfg.face_lost_to_idle_secs:
            self._transition(IDLE, now)
            self._set_mood("sad")
            self._sad_revert_at = now + 3.0
            self._next_personality = now + random.uniform(8, 15)

    # --- BONDED ---
    def _tick_bonded(self, now, face_present, face_lost):
        # Face lost -> IDLE with sadness
        if face_lost:
            self._transition(IDLE, now)
            self._set_mood("sad")
            self._sad_revert_at = now + 3.0
            self._next_personality = now + random.uniform(8, 15)
            return

        # Periodic affection moods
        if face_present and now >= self._next_bonded_affection:
            mood = random.choice(_BONDED_AFFECTION)
            self._set_mood(mood)
            # Revert to neutral after a brief flash
            self._greeting_revert_at = now + random.uniform(2.0, 4.0)
            self._next_bonded_affection = now + random.uniform(
                self._cfg.bonded_affection_interval_min,
                self._cfg.bonded_affection_interval_max)

    # --- BORED ---
    def _tick_bored(self, now, face_appeared):
        # Face appeared -> ENGAGED with excitement
        if face_appeared:
            self._transition(ENGAGED, now)
            self._set_mood("excited")
            self._greeting_revert_at = now + 3.0
            return

        # Cycle through bored moods
        if now >= self._bored_next_switch:
            self._bored_mood_idx = (self._bored_mood_idx + 1) % len(_BORED_MOODS)
            self._set_mood(_BORED_MOODS[self._bored_mood_idx])
            self._bored_next_switch = now + self._cfg.bored_mood_cycle_secs
