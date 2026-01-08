from __future__ import annotations

import os
import types

import pytest

from jarvis.entrada import shortcut as shortcut_module
from jarvis.entrada.shortcut import ChatShortcut


def test_parse_combo_defaults_key():
    shortcut = ChatShortcut(chat_command="echo")
    mods, key = shortcut._parse_combo("ctrl+shift")
    assert mods == {"ctrl", "shift"}
    assert key == "j"


def test_start_returns_false_without_pynput(monkeypatch):
    monkeypatch.setattr(shortcut_module, "HAS_PYNPUT", False)
    shortcut = ChatShortcut(chat_command="echo")
    assert shortcut.start() is False


def test_start_returns_false_on_wayland_without_x11(monkeypatch):
    monkeypatch.setattr(shortcut_module, "HAS_PYNPUT", True)
    monkeypatch.setenv("WAYLAND_DISPLAY", "1")
    monkeypatch.delenv("DISPLAY", raising=False)
    shortcut = ChatShortcut(chat_command="echo")
    assert shortcut.start() is False


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
