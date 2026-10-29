"""
Global keyboard shortcut handler for opening chat UI.

This module registers a global keyboard shortcut (default: Ctrl+Shift+J)
that opens the chat UI when pressed.

Implementation notes:
- Uses `pynput`.
- On Linux Wayland, global hotkeys are often blocked. If Wayland is detected
  without XWayland, we disable the shortcut and suggest setting the hotkey in
  the desktop environment.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time

try:
    from pynput import keyboard  # type: ignore

    HAS_PYNPUT = True
except ImportError:
    keyboard = None
    HAS_PYNPUT = False


def _is_wayland() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY"))


def _has_x11() -> bool:
    # On Wayland with XWayland, DISPLAY is often set.
    return bool(os.environ.get("DISPLAY"))


class ChatShortcut:
    """Global keyboard shortcut to open chat UI."""

    def __init__(
        self,
        chat_command: str | list[str] | None = None,
        shortcut_combo: str = "ctrl+shift+j",
        cooldown_s: float = 0.6,
    ) -> None:
        """
        Initialize chat shortcut handler.

        Args:
            chat_command: Command to run when shortcut is pressed.
                          Defaults to opening chat UI via Python module.
            shortcut_combo: Keyboard shortcut combo (default: ctrl+shift+j)
            cooldown_s: Debounce window to avoid repeated triggers by key repeat.
        """
        self.chat_command = chat_command or self._default_chat_command()
        self.shortcut_combo = shortcut_combo.lower()
        self.cooldown_s = max(0.0, float(cooldown_s))

        self._listener: keyboard.Listener | None = None
        self._running = False
        self._pressed_keys: set[str] = set()

        self._combo_mods, self._combo_key = self._parse_combo(self.shortcut_combo)
        self._last_fire_ts = 0.0
        self._armed = True  # re-arm after releasing modifiers

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
        parts = [p.strip() for p in combo.split("+") if p.strip()]
        modifiers = {"ctrl", "alt", "shift", "super", "cmd"}
        mods: set[str] = set()
        final_key: str | None = None

        for part in parts:
            p = part.lower()
            if p in modifiers:
                mods.add("super" if p == "cmd" else p)
            else:
                final_key = p

        if not final_key:
            final_key = "j"

        return mods, final_key

    def _key_to_string(self, key) -> str:
        """Convert pynput key to string."""
        if hasattr(key, "char") and key.char:
            return str(key.char).lower()
        if hasattr(key, "name"):
            name = str(key.name).lower()
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
                "super_l": "super",
                "super_r": "super",
            }
            return key_map.get(name, name)
        return ""

    def _mods_down(self) -> set[str]:
        return {k for k in self._pressed_keys if k in {"ctrl", "alt", "shift", "super"}}

    def _on_press(self, key) -> None:
        """Handle key press event."""
        try:
            key_str = self._key_to_string(key)
            if key_str:
                self._pressed_keys.add(key_str)

            pressed_mods = self._mods_down()

            # Re-arm after all modifiers released (prevents repeats while holding keys)
            if not pressed_mods:
                self._armed = True

            if not self._armed:
                return

            # Match: all required modifiers must be down AND final key pressed
            if pressed_mods == self._combo_mods and key_str == self._combo_key:
                now = time.monotonic()
                if (now - self._last_fire_ts) >= self.cooldown_s:
                    self._last_fire_ts = now
                    self._armed = False
                    self._open_chat()
        except Exception:
            pass

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
            cmd = self.chat_command

            # Normalize: allow either "str" or "list[str]"
            if isinstance(cmd, str):
                # Use shlex for proper quoting in Linux/macOS
                cmd_list = shlex.split(cmd) if os.name != "nt" else cmd
            else:
                cmd_list = cmd

            if os.name == "nt":
                # CREATE_NO_WINDOW is Windows-specific and may not be in type stubs
                create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                subprocess.Popen(cmd_list, shell=True, creationflags=create_no_window)  # type: ignore[arg-type]
            else:
                subprocess.Popen(
                    cmd_list,  # type: ignore[arg-type]
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
        except Exception:
            pass

    def start(self) -> bool:
        """
        Start listening for keyboard shortcut.

        Returns:
            True if started successfully, False otherwise
        """
        if not HAS_PYNPUT:
            return False

        # On Wayland without XWayland, pynput usually can't grab global hotkeys.
        if sys.platform.startswith("linux") and _is_wayland() and not _has_x11():
            return False

        if self._running:
            return True

        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press, on_release=self._on_release
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
        "wayland": _is_wayland(),
        "x11": _has_x11(),
    }
