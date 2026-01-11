from __future__ import annotations

import builtins
import sys
import types

import pytest

from jarvis.entrada import preflight


def _make_config(tts_mode: str = "local"):
    return types.SimpleNamespace(tts_mode=tts_mode)


def test_check_chat_ui_warns_when_tkinter_missing(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "tkinter":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = preflight._check_chat_ui()
    assert result.status == "WARN"


def test_check_chat_ui_ok_when_tkinter_present(monkeypatch):
    monkeypatch.setitem(sys.modules, "tkinter", types.SimpleNamespace())
    result = preflight._check_chat_ui()
    assert result.status == "OK"


def test_check_chat_shortcut_warns_without_pynput(monkeypatch):
    monkeypatch.setattr(preflight, "check_shortcut_deps", lambda: {"pynput": False})
    result = preflight._check_chat_shortcut()
    assert result.status == "WARN"


def test_check_chat_shortcut_ok_with_file_trigger(monkeypatch):
    monkeypatch.setattr(
        preflight,
        "check_shortcut_deps",
        lambda: {"pynput": False, "file_trigger": True},
    )
    result = preflight._check_chat_shortcut()
    assert result.status == "OK"


def test_check_chat_shortcut_warns_on_wayland_without_x11(monkeypatch):
    monkeypatch.setattr(
        preflight,
        "check_shortcut_deps",
        lambda: {"pynput": True, "wayland": True, "x11": False},
    )
    result = preflight._check_chat_shortcut()
    assert result.status == "WARN"


def test_check_chat_shortcut_ok(monkeypatch):
    monkeypatch.setattr(
        preflight,
        "check_shortcut_deps",
        lambda: {"pynput": True, "wayland": False, "x11": True},
    )
    result = preflight._check_chat_shortcut()
    assert result.status == "OK"


def test_check_tts_warns_when_piper_missing_model(monkeypatch):
    monkeypatch.setattr(
        preflight,
        "check_tts_deps",
        lambda: {"piper": True, "espeak-ng": False, "aplay": True},
    )

    class DummyTTS:
        def __init__(self, config):
            self.config = config

        def _find_piper_model(self):
            return None

    monkeypatch.setattr(preflight, "TextToSpeech", DummyTTS)
    result = preflight._check_tts(_make_config())
    assert result.status == "WARN"
    assert "piper" in result.detail


def test_check_tts_warns_when_piper_missing_model_but_espeak_ok(monkeypatch):
    monkeypatch.setattr(
        preflight,
        "check_tts_deps",
        lambda: {"piper": True, "espeak-ng": True, "aplay": True},
    )

    class DummyTTS:
        def __init__(self, config):
            self.config = config

        def _find_piper_model(self):
            return None

    monkeypatch.setattr(preflight, "TextToSpeech", DummyTTS)
    result = preflight._check_tts(_make_config())
    assert result.status == "WARN"
    assert "espeak" in result.detail


def test_check_wake_word_audio_warns_when_porcupine_missing(monkeypatch):
    monkeypatch.setenv("JARVIS_WAKE_WORD_AUDIO", "1")
    monkeypatch.setenv("JARVIS_WAKE_WORD_AUDIO_BACKEND", "porcupine")
    monkeypatch.setattr(
        preflight, "wakeword_porcupine", types.SimpleNamespace(is_available=lambda: False)
    )
    result = preflight._check_wake_word_audio()
    assert result is not None
    assert result.status == "WARN"


def test_check_wake_word_audio_warns_when_openwakeword_missing(monkeypatch):
    monkeypatch.setenv("JARVIS_WAKE_WORD_AUDIO", "1")
    monkeypatch.setenv("JARVIS_WAKE_WORD_AUDIO_BACKEND", "openwakeword")
    monkeypatch.setattr(
        preflight,
        "wakeword_openwakeword",
        types.SimpleNamespace(is_available=lambda: False),
    )
    result = preflight._check_wake_word_audio()
    assert result is not None
    assert result.status == "WARN"


def test_check_wake_word_audio_warns_when_openwakeword_no_models(monkeypatch):
    monkeypatch.setenv("JARVIS_WAKE_WORD_AUDIO", "1")
    monkeypatch.setenv("JARVIS_WAKE_WORD_AUDIO_BACKEND", "openwakeword")
    monkeypatch.delenv("JARVIS_OPENWAKEWORD_MODEL_PATHS", raising=False)
    monkeypatch.setattr(
        preflight,
        "wakeword_openwakeword",
        types.SimpleNamespace(is_available=lambda: True),
    )
    result = preflight._check_wake_word_audio()
    assert result is not None
    assert result.status == "WARN"


def test_check_wake_word_audio_ok_with_openwakeword_models(monkeypatch):
    monkeypatch.setenv("JARVIS_WAKE_WORD_AUDIO", "1")
    monkeypatch.setenv("JARVIS_WAKE_WORD_AUDIO_BACKEND", "openwakeword")
    monkeypatch.setenv("JARVIS_OPENWAKEWORD_MODEL_PATHS", "model1.onnx")
    monkeypatch.setattr(
        preflight,
        "wakeword_openwakeword",
        types.SimpleNamespace(is_available=lambda: True),
    )
    result = preflight._check_wake_word_audio()
    assert result is not None
    assert result.status == "OK"
