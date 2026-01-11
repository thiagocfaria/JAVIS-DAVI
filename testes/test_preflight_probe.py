from __future__ import annotations

import types

from jarvis.entrada import preflight


def _make_config(stt_mode: str = "local", tts_mode: str = "local"):
    return types.SimpleNamespace(stt_mode=stt_mode, tts_mode=tts_mode)


def test_check_stt_probe_warns_on_capture_failure(monkeypatch):
    monkeypatch.setenv("JARVIS_PREFLIGHT_PROBE", "1")
    monkeypatch.setattr(
        preflight,
        "check_stt_deps",
        lambda: {"sounddevice": True, "numpy": True, "faster_whisper": True, "scipy": True},
    )
    monkeypatch.setattr(preflight, "_probe_stt_capture", lambda seconds: (False, "default", 16000))
    result = preflight._check_stt(_make_config())
    assert result.status == "WARN"
    assert "captura falhou" in result.detail


def test_check_stt_probe_ok(monkeypatch):
    monkeypatch.setenv("JARVIS_PREFLIGHT_PROBE", "1")
    monkeypatch.setattr(
        preflight,
        "check_stt_deps",
        lambda: {"sounddevice": True, "numpy": True, "faster_whisper": True, "scipy": True},
    )
    monkeypatch.setattr(preflight, "_probe_stt_capture", lambda seconds: (True, "default", 16000))
    result = preflight._check_stt(_make_config())
    assert result.status == "OK"
    assert "captura ok" in result.detail


def test_check_tts_probe_warns_on_play_failure(monkeypatch):
    monkeypatch.setenv("JARVIS_PREFLIGHT_PROBE", "1")
    monkeypatch.setattr(
        preflight,
        "check_tts_deps",
        lambda: {"piper": False, "espeak-ng": True, "aplay": True},
    )
    monkeypatch.setattr(preflight, "_probe_tts_play", lambda config: False)
    result = preflight._check_tts(_make_config())
    assert result.status == "WARN"
    assert "falha ao tocar" in result.detail


def test_check_tts_probe_ok(monkeypatch):
    monkeypatch.setenv("JARVIS_PREFLIGHT_PROBE", "1")
    monkeypatch.setattr(
        preflight,
        "check_tts_deps",
        lambda: {"piper": False, "espeak-ng": True, "aplay": True},
    )
    monkeypatch.setattr(preflight, "_probe_tts_play", lambda config: True)
    result = preflight._check_tts(_make_config())
    assert result.status == "OK"
    assert "audio ok" in result.detail
