#!/usr/bin/env python3
"""Robot Head - Main entry point and orchestrator."""

import argparse
import logging
import signal
import sys
import threading
import time

from src.config import load_config
from src.state import load_state, apply_state
from src.environment import EnvironmentState
from src.mood_engine import MoodEngine
from src.hardware.gpio_map import GPIOMap
from src.display.gc9a01 import GC9A01
from src.display.display_manager import DisplayManager
from src.eyes.style_manager import StyleManager
from src.eyes.animator import EyeAnimator
from src.tracking.camera import Camera
from src.tracking.motion_detector import MotionDetector
from src.tracking.tracker import FaceTracker
from PIL import ImageDraw, ImageFont

log = logging.getLogger("robot-head")


class RobotHead:
    def __init__(self, config_path: str = "config.yaml", debug: bool = False):
        self.config = load_config(config_path)
        self._debug = debug
        self._running = False

        # Environment state (replaces simple face_position/lock)
        self._env_state = EnvironmentState(
            brightness_tau=self.config.mood_engine.brightness_tau,
        )

        # Debug state (only used if --debug)
        self._debug_state = None
        self._detect_fps = 0.0
        self._render_fps = 0.0

    def start(self):
        self._running = True

        # Set up logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
        )

        # Initialize displays
        pins = GPIOMap()
        log.info("Initializing left display (CE0)...")
        left_disp = GC9A01(0, 0, pins.LEFT_DC, pins.LEFT_RST, pins.LEFT_BL,
                           self.config.display.spi_speed_hz)
        left_disp.init_display()

        log.info("Initializing right display (CE1)...")
        right_disp = GC9A01(0, 1, pins.RIGHT_DC, pins.RIGHT_RST, pins.RIGHT_BL,
                            self.config.display.spi_speed_hz)
        right_disp.init_display()

        display_mgr = DisplayManager(left_disp, right_disp)
        log.info("Displays initialized")

        # Eye style manager and animator
        style_mgr = StyleManager(self.config.eyes)
        animator = EyeAnimator(self.config.animation)

        # Mood engine
        mood_engine = MoodEngine(self.config.mood_engine, style_mgr)

        # Start debug server if requested
        if self._debug:
            from src.debug.web_server import DebugState, start_debug_server
            self._debug_state = DebugState()
            self._debug_state.style_manager = style_mgr
            self._debug_state.mood_engine = mood_engine
            start_debug_server(self._debug_state, self.config.debug.web_port)
            log.info(f"Debug server at http://0.0.0.0:{self.config.debug.web_port}")

        # Restore persisted UI state (style, mood, glow, fps overlay, auto-mood)
        saved = load_state()
        apply_state(saved, style_mgr, self._debug_state, mood_engine)

        # Start tracking thread
        tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        tracking_thread.start()
        log.info("Tracking thread started")

        # Main render loop
        target_fps = self.config.display.fps_target
        frame_time = 1.0 / target_fps
        last_time = time.monotonic()
        frame_count = 0
        fps_timer = time.monotonic()
        mood_timer = time.monotonic()
        mood_tick_interval = 0.5  # ~2 Hz

        log.info(f"Entering render loop at {target_fps} FPS target")

        try:
            while self._running:
                now = time.monotonic()
                dt = now - last_time
                last_time = now

                # Read face position from environment state
                face_pos = self._env_state.face_position

                # Tick mood engine at ~2 Hz
                if now - mood_timer >= mood_tick_interval:
                    mood_dt = now - mood_timer
                    mood_timer = now
                    env_snap = self._env_state.get_snapshot()
                    mood_engine.tick(mood_dt, env_snap)

                # Animate
                left_state, right_state = animator.update(dt, face_pos)

                # Render both eyes (get current renderers from style manager)
                renderer_left, renderer_right = style_mgr.get_renderers()
                left_img = renderer_left.render(left_state)
                right_img = renderer_right.render(right_state)

                # FPS overlay on right eye
                if self._debug_state and self._debug_state.show_fps:
                    fps_draw = ImageDraw.Draw(right_img)
                    fps_text = f"{self._render_fps:.0f}"
                    fps_draw.text((120, 210), fps_text, fill=(255, 255, 255),
                                  anchor="mb")

                # Push to displays
                display_mgr.update(left_img, right_img)

                # FPS counting
                frame_count += 1
                if now - fps_timer >= 1.0:
                    self._render_fps = frame_count / (now - fps_timer)
                    frame_count = 0
                    fps_timer = now
                    if self._debug and self._debug_state:
                        self._debug_state.update_stats(
                            gaze=(left_state.pupil_x, left_state.pupil_y),
                            fps_render=self._render_fps,
                            fps_detect=self._detect_fps,
                            face_detected=face_pos is not None,
                        )

                # Frame rate limiting
                elapsed = time.monotonic() - now
                sleep_time = frame_time - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            log.info("Interrupted")
        finally:
            self._running = False
            log.info("Shutting down displays...")
            display_mgr.cleanup()
            import RPi.GPIO as GPIO
            GPIO.cleanup()
            log.info("Done")

    def _tracking_loop(self):
        """Background thread: camera capture + face detection."""
        camera = Camera(
            width=self.config.tracking.lores_width,
            height=self.config.tracking.lores_height,
        )
        detector = MotionDetector(
            history=self.config.tracking.motion_history,
            threshold=self.config.tracking.motion_threshold,
            min_area=self.config.tracking.motion_min_area,
        )
        tracker = FaceTracker(
            smoothing=self.config.tracking.smoothing,
            lost_timeout=self.config.tracking.lost_timeout,
        )

        camera.start()
        log.info("Camera started")

        frame_count = 0
        fps_timer = time.monotonic()

        try:
            while self._running:
                grey = camera.capture_grey()
                faces = detector.detect(grey)
                position = tracker.update(
                    faces,
                    self.config.tracking.lores_width,
                    self.config.tracking.lores_height,
                    time.monotonic(),
                )

                self._env_state.update_from_tracking(
                    grey, faces, position,
                    self.config.tracking.lores_width,
                    self.config.tracking.lores_height,
                )

                # Update debug state
                if self._debug and self._debug_state:
                    self._debug_state.update_frame(grey, faces)

                # FPS counting
                frame_count += 1
                now = time.monotonic()
                if now - fps_timer >= 1.0:
                    self._detect_fps = frame_count / (now - fps_timer)
                    frame_count = 0
                    fps_timer = now

        except Exception as e:
            log.error(f"Tracking thread error: {e}", exc_info=True)
        finally:
            camera.stop()
            log.info("Camera stopped")

    def stop(self):
        self._running = False


def main():
    parser = argparse.ArgumentParser(description="Robot Head")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug web server")
    args = parser.parse_args()

    head = RobotHead(config_path=args.config, debug=args.debug)

    # Handle SIGTERM gracefully (for systemd)
    signal.signal(signal.SIGTERM, lambda *_: head.stop())

    head.start()


if __name__ == "__main__":
    main()
