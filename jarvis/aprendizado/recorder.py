"""
Demonstration recorder for learning by observation.

Records user actions (mouse, keyboard, screenshots) for later replay.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from pynput import keyboard, mouse  # type: ignore
    HAS_PYNPUT = True
except ImportError:
    mouse = None
    keyboard = None
    HAS_PYNPUT = False

try:
    from PIL import Image, ImageGrab  # type: ignore
except ImportError:
    Image = None
    ImageGrab = None


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class RecordedEvent:
    """A recorded user event."""
    event_type: str  # click, move, scroll, key_press, key_release, screenshot
    timestamp: float
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Recording:
    """A complete recording of a demonstration."""
    name: str
    start_time: float
    end_time: float
    events: list[RecordedEvent] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)  # Paths to screenshots
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "events": [
                {
                    "event_type": e.event_type,
                    "timestamp": e.timestamp,
                    "data": e.data,
                }
                for e in self.events
            ],
            "screenshots": self.screenshots,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Recording:
        """Create from dictionary."""
        events = [
            RecordedEvent(
                event_type=e["event_type"],
                timestamp=e["timestamp"],
                data=e.get("data", {}),
            )
            for e in data.get("events", [])
        ]
        return cls(
            name=data.get("name", ""),
            start_time=data.get("start_time", 0),
            end_time=data.get("end_time", 0),
            events=events,
            screenshots=data.get("screenshots", []),
            metadata=data.get("metadata", {}),
        )


# ============================================================================
# RECORDER
# ============================================================================

class DemonstrationRecorder:
    """
    Records user demonstrations for learning.
    
    Features:
    - Mouse click/move/scroll recording
    - Keyboard input recording
    - Periodic screenshot capture
    - Export to JSON for analysis
    """

    def __init__(
        self,
        screenshot_interval: float = 1.0,
        recordings_dir: Path | None = None,
    ) -> None:
        if not HAS_PYNPUT:
            raise RuntimeError("pynput not installed. Run: pip install pynput")

        self.screenshot_interval = screenshot_interval
        self.recordings_dir = recordings_dir or Path(tempfile.gettempdir()) / "jarvis_recordings"

        self._recording: Recording | None = None
        self._is_recording = False
        self._mouse_listener: Any | None = None
        self._keyboard_listener: Any | None = None
        self._screenshot_thread: threading.Thread | None = None
        self._last_screenshot_time = 0.0

    def start_recording(self, name: str) -> None:
        """Start recording a demonstration."""
        if self._is_recording:
            raise RuntimeError("Already recording")

        # Create recordings directory
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        # Initialize recording
        self._recording = Recording(
            name=name,
            start_time=time.time(),
            end_time=0,
        )
        self._is_recording = True

        # Start mouse listener
        self._mouse_listener = mouse.Listener(
            on_click=self._on_click,
            on_move=self._on_move,
            on_scroll=self._on_scroll,
        )
        self._mouse_listener.start()

        # Start keyboard listener
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._keyboard_listener.start()

        # Start screenshot thread
        self._screenshot_thread = threading.Thread(
            target=self._screenshot_loop,
            daemon=True,
        )
        self._screenshot_thread.start()

    def stop_recording(self) -> Recording:
        """Stop recording and return the recording."""
        if not self._is_recording or self._recording is None:
            raise RuntimeError("Not recording")

        self._is_recording = False
        self._recording.end_time = time.time()

        # Stop listeners
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None

        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None

        # Wait for screenshot thread
        if self._screenshot_thread:
            self._screenshot_thread.join(timeout=2)
            self._screenshot_thread = None

        recording = self._recording
        self._recording = None

        return recording

    def save_recording(self, recording: Recording, filename: str | None = None) -> Path:
        """Save recording to JSON file."""
        if filename is None:
            filename = f"{recording.name}_{int(recording.start_time)}.json"

        path = self.recordings_dir / filename

        with open(path, "w", encoding="utf-8") as f:
            json.dump(recording.to_dict(), f, ensure_ascii=False, indent=2)

        return path

    def load_recording(self, path: Path) -> Recording:
        """Load recording from JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return Recording.from_dict(data)

    def list_recordings(self) -> list[Path]:
        """List all saved recordings."""
        if not self.recordings_dir.exists():
            return []
        return list(self.recordings_dir.glob("*.json"))

    # ========================================================================
    # Event handlers
    # ========================================================================

    def _on_click(self, x: int, y: int, button: Any, pressed: bool) -> None:
        """Handle mouse click event."""
        if not self._is_recording or self._recording is None:
            return

        event = RecordedEvent(
            event_type="click" if pressed else "release",
            timestamp=time.time(),
            data={
                "x": x,
                "y": y,
                "button": str(button),
            },
        )
        self._recording.events.append(event)

        # Take screenshot on click
        self._take_screenshot_if_needed(force=True)

    def _on_move(self, x: int, y: int) -> None:
        """Handle mouse move event."""
        if not self._is_recording or self._recording is None:
            return

        # Only record significant moves (every 50px)
        if self._recording.events:
            last_event = self._recording.events[-1]
            if last_event.event_type == "move":
                last_x = last_event.data.get("x", 0)
                last_y = last_event.data.get("y", 0)
                if abs(x - last_x) < 50 and abs(y - last_y) < 50:
                    return

        event = RecordedEvent(
            event_type="move",
            timestamp=time.time(),
            data={"x": x, "y": y},
        )
        self._recording.events.append(event)

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """Handle mouse scroll event."""
        if not self._is_recording or self._recording is None:
            return

        event = RecordedEvent(
            event_type="scroll",
            timestamp=time.time(),
            data={
                "x": x,
                "y": y,
                "dx": dx,
                "dy": dy,
            },
        )
        self._recording.events.append(event)

    def _on_key_press(self, key: Any) -> None:
        """Handle key press event."""
        if not self._is_recording or self._recording is None:
            return

        try:
            key_str = key.char if hasattr(key, 'char') else str(key)
        except AttributeError:
            key_str = str(key)

        event = RecordedEvent(
            event_type="key_press",
            timestamp=time.time(),
            data={"key": key_str},
        )
        self._recording.events.append(event)

    def _on_key_release(self, key: Any) -> None:
        """Handle key release event."""
        if not self._is_recording or self._recording is None:
            return

        try:
            key_str = key.char if hasattr(key, 'char') else str(key)
        except AttributeError:
            key_str = str(key)

        event = RecordedEvent(
            event_type="key_release",
            timestamp=time.time(),
            data={"key": key_str},
        )
        self._recording.events.append(event)

    # ========================================================================
    # Screenshot handling
    # ========================================================================

    def _screenshot_loop(self) -> None:
        """Background thread for periodic screenshots."""
        while self._is_recording:
            self._take_screenshot_if_needed()
            time.sleep(0.1)  # Check frequently

    def _take_screenshot_if_needed(self, force: bool = False) -> None:
        """Take screenshot if enough time has passed."""
        if not self._is_recording or self._recording is None:
            return

        now = time.time()
        if not force and now - self._last_screenshot_time < self.screenshot_interval:
            return

        self._last_screenshot_time = now

        try:
            screenshot = self._take_screenshot()
            if screenshot:
                # Save screenshot
                filename = f"{self._recording.name}_{int(now * 1000)}.png"
                path = self.recordings_dir / filename
                screenshot.save(str(path))
                self._recording.screenshots.append(str(path))

                # Add event
                event = RecordedEvent(
                    event_type="screenshot",
                    timestamp=now,
                    data={"path": str(path)},
                )
                self._recording.events.append(event)
        except Exception:
            pass

    def _take_screenshot(self) -> Image.Image | None:
        """Take a screenshot."""
        if ImageGrab is None:
            return None

        try:
            return ImageGrab.grab()
        except Exception:
            return None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_recorder_deps() -> dict:
    """Check recorder dependencies."""
    return {
        "pynput": HAS_PYNPUT,
        "pillow": Image is not None,
        "imagegrab": ImageGrab is not None,
    }

