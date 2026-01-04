"""
Global keyboard shortcut handler for opening chat UI.

This module registers a global keyboard shortcut (default: Ctrl+Shift+J)
that opens the chat UI when pressed.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

try:
    from pynput import keyboard  # type: ignore
    HAS_PYNPUT = True
except ImportError:
    keyboard = None
    HAS_PYNPUT = False


class ChatShortcut:
    """Global keyboard shortcut to open chat UI."""

    def __init__(
        self,
        chat_command: str | None = None,
        shortcut_combo: str = "ctrl+shift+j",
    ) -> None:
        """
        Initialize chat shortcut handler.

        Args:
            chat_command: Command to run when shortcut is pressed.
                          Defaults to opening chat UI via Python module.
            shortcut_combo: Keyboard shortcut combo (default: ctrl+shift+j)
        """
        self.chat_command = chat_command or self._default_chat_command()
        self.shortcut_combo = shortcut_combo.lower()
        self._listener: keyboard.Listener | None = None
        self._running = False
        self._pressed_keys: set = set()

    def _default_chat_command(self) -> str:
        """Get default command to open chat UI."""
        python = sys.executable
        module = "jarvis.entrada.chat_ui"
        return f"{python} -m {module}"

    def _parse_combo(self, combo: str) -> tuple[set[str], str]:
        """
        Parse shortcut combo into modifiers and key.

        Returns:
            Tuple of (modifiers_set, final_key)
        """
        parts = [p.strip() for p in combo.split("+")]
        modifiers = {"ctrl", "alt", "shift", "super", "cmd"}
        mods = set()
        final_key = None

        for part in parts:
            if part.lower() in modifiers:
                mods.add(part.lower())
            else:
                final_key = part.lower()

        if not final_key:
            final_key = "j"  # Default key

        return mods, final_key

    def _key_to_string(self, key) -> str:
        """Convert pynput key to string."""
        if hasattr(key, "char") and key.char:
            return key.char.lower()
        if hasattr(key, "name"):
            name = key.name.lower()
            # Map special keys
            key_map = {
                "ctrl_l": "ctrl",
                "ctrl_r": "ctrl",
                "alt_l": "alt",
                "alt_r": "alt",
                "shift_l": "shift",
                "shift_r": "shift",
                "cmd": "super",
                "cmd_l": "super",
                "cmd_r": "super",
            }
            return key_map.get(name, name)
        return ""

    def _on_press(self, key) -> None:
        """Handle key press event."""
        try:
            key_str = self._key_to_string(key)
            if key_str:
                self._pressed_keys.add(key_str)

            # Check if shortcut matches
            mods, final_key = self._parse_combo(self.shortcut_combo)
            pressed_mods = {k for k in self._pressed_keys if k in {"ctrl", "alt", "shift", "super"}}

            if pressed_mods == mods and key_str == final_key:
                self._open_chat()
        except Exception:
            pass  # Ignore errors in key handling

    def _on_release(self, key) -> None:
        """Handle key release event."""
        try:
            key_str = self._key_to_string(key)
            if key_str in self._pressed_keys:
                self._pressed_keys.discard(key_str)
        except Exception:
            pass

    def _open_chat(self) -> None:
        """Open chat UI by running the chat command."""
        try:
            # Run in background to avoid blocking
            if os.name == "nt":  # Windows
                subprocess.Popen(
                    self.chat_command,
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:  # Linux/Mac
                subprocess.Popen(
                    self.chat_command.split(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
        except Exception:
            pass  # Ignore errors when opening chat

    def start(self) -> bool:
        """
        Start listening for keyboard shortcut.

        Returns:
            True if started successfully, False otherwise
        """
        if not HAS_PYNPUT:
            return False

        if self._running:
            return True

        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()
            self._running = True
            return True
        except Exception:
            return False

    def stop(self) -> None:
        """Stop listening for keyboard shortcut."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        self._running = False
        self._pressed_keys.clear()

    def is_running(self) -> bool:
        """Check if shortcut listener is running."""
        return self._running and self._listener is not None and self._listener.running


def check_shortcut_deps() -> dict:
    """Check if dependencies for global shortcuts are available."""
    return {
        "pynput": HAS_PYNPUT,
    }



