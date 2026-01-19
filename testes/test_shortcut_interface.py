from __future__ import annotations

import os
import types


from jarvis.entrada import shortcut as shortcut_module
from jarvis.entrada.shortcut import ChatShortcut


def test_parse_combo_defaults_key():
    shortcut = ChatShortcut(chat_command="echo")
    mods, key = shortcut._parse_combo("ctrl+shift")
    assert mods == {"ctrl", "shift"}
    assert key == "j"


def test_shortcut_combo_uses_env_when_not_provided(monkeypatch):
    monkeypatch.setenv("JARVIS_CHAT_SHORTCUT_COMBO", "alt+k")
    shortcut = ChatShortcut(chat_command="echo", shortcut_combo=None)
    assert shortcut.shortcut_combo == "alt+k"
    mods, key = shortcut._parse_combo(shortcut.shortcut_combo)
    assert mods == {"alt"}
    assert key == "k"


def test_start_returns_false_without_pynput(monkeypatch):
    monkeypatch.setattr(shortcut_module, "HAS_PYNPUT", False)
    shortcut = ChatShortcut(chat_command="echo")
    assert shortcut.start() is False
    assert shortcut.last_error == "pynput_missing"


def test_start_uses_file_trigger_without_pynput(monkeypatch, tmp_path):
    monkeypatch.setattr(shortcut_module, "HAS_PYNPUT", False)
    trigger_path = tmp_path / "shortcut.trigger"
    monkeypatch.setenv("JARVIS_CHAT_SHORTCUT_FILE", str(trigger_path))
    monkeypatch.setenv("JARVIS_CHAT_SHORTCUT_FILE_POLL_MS", "9999")

    class DummyThread:
        def __init__(self, target=None, daemon=False):
            self._target = target
            self._daemon = daemon
            self._alive = False

        def start(self):
            self._alive = False

        def is_alive(self):
            return self._alive

    monkeypatch.setattr(shortcut_module.threading, "Thread", DummyThread)

    shortcut = ChatShortcut(chat_command="echo")
    calls = {"open": 0}
    shortcut._open_chat = lambda: calls.__setitem__("open", calls["open"] + 1)

    assert shortcut.start() is True
    assert shortcut.last_error == "pynput_missing"

    trigger_path.write_text("1", encoding="utf-8")
    shortcut._check_file_trigger()
    stat = trigger_path.stat()
    os.utime(trigger_path, (stat.st_atime + 1.0, stat.st_mtime + 1.0))
    shortcut._check_file_trigger()

    assert calls["open"] == 1


def test_start_returns_false_on_wayland_without_x11(monkeypatch):
    monkeypatch.setattr(shortcut_module, "HAS_PYNPUT", True)
    monkeypatch.setenv("WAYLAND_DISPLAY", "1")
    monkeypatch.delenv("DISPLAY", raising=False)
    shortcut = ChatShortcut(chat_command="echo")
    assert shortcut.start() is False
    assert shortcut.last_error == "wayland_no_x11"


def test_start_returns_true_with_dummy_listener(monkeypatch):
    class DummyListener:
        def __init__(self, on_press=None, on_release=None):
            self.running = False

        def start(self):
            self.running = True

    dummy_keyboard = types.SimpleNamespace(Listener=DummyListener)
    monkeypatch.setattr(shortcut_module, "HAS_PYNPUT", True)
    monkeypatch.setattr(shortcut_module, "keyboard", dummy_keyboard)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("DISPLAY", ":0")

    shortcut = ChatShortcut(chat_command="echo")
    assert shortcut.start() is True
    assert shortcut.last_error is None
    assert shortcut.is_running() is True


def test_open_chat_invokes_popen(monkeypatch):
    calls = []

    def fake_popen(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return object()

    monkeypatch.setattr(shortcut_module.subprocess, "Popen", fake_popen)

    shortcut = ChatShortcut(chat_command="echo hello")
    shortcut._open_chat()

    assert calls


def test_key_to_string_maps_modifiers():
    shortcut = ChatShortcut(chat_command="echo")

    class Key:
        name = "ctrl_l"
        char = None

    assert shortcut._key_to_string(Key()) == "ctrl"


def test_key_to_string_handles_char():
    shortcut = ChatShortcut(chat_command="echo")

    class Key:
        name = None
        char = "A"

    assert shortcut._key_to_string(Key()) == "a"
