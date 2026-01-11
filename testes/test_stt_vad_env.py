from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis.entrada.stt import SpeechToText


class _DummyVAD:
    def __init__(self, *args, **kwargs) -> None:
        return None


def test_streaming_vad_uses_env(monkeypatch) -> None:
    captured = {}

    class DummyStreaming:
        def __init__(self, *args, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setenv("JARVIS_VAD_SILENCE_MS", "500")
    monkeypatch.setenv("JARVIS_VAD_PRE_ROLL_MS", "250")
    monkeypatch.setenv("JARVIS_VAD_POST_ROLL_MS", "150")
    monkeypatch.setenv("JARVIS_VAD_MAX_SECONDS", "12")
    monkeypatch.setenv("JARVIS_VAD_AGGRESSIVENESS", "3")
    monkeypatch.delenv("JARVIS_AUDIO_DEVICE", raising=False)
    monkeypatch.delenv("JARVIS_AUDIO_CAPTURE_SR", raising=False)

    monkeypatch.setattr("jarvis.entrada.stt.check_vad_available", lambda: True)
    monkeypatch.setattr("jarvis.entrada.stt.VADRecorder", None)
    monkeypatch.setattr("jarvis.voz.vad.VoiceActivityDetector", _DummyVAD)
    monkeypatch.setattr("jarvis.voz.vad.StreamingVAD", DummyStreaming)

    cfg = SimpleNamespace(
        stt_mode="local",
        stt_model_size="tiny",
        stt_audio_trim_backend="none",
    )
    SpeechToText(cfg)

    assert captured["silence_duration_ms"] == 500
    assert captured["pre_roll_ms"] == 250
    assert captured["post_roll_ms"] == 150
    assert captured["max_duration_s"] == 12
    assert captured["device"] is None
