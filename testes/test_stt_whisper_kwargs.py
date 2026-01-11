from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis.entrada.stt import SpeechToText


@pytest.fixture(autouse=True)
def _patch_vad(monkeypatch):
    monkeypatch.setattr("jarvis.entrada.stt.check_vad_available", lambda: False)


def _make_stt():
    cfg = SimpleNamespace(
        stt_mode="local",
        stt_model_size="tiny",
        stt_audio_trim_backend="none",
    )
    return SpeechToText(cfg)


def test_whisper_kwargs_from_env(monkeypatch):
    monkeypatch.setenv("JARVIS_WHISPER_VAD_FILTER", "1")
    monkeypatch.setenv("JARVIS_STT_BEAM_SIZE", "5")
    monkeypatch.setenv("JARVIS_STT_BEST_OF", "2")
    monkeypatch.setenv("JARVIS_STT_TEMPERATURE", "0.2")
    monkeypatch.setenv("JARVIS_STT_INITIAL_PROMPT", "ola")
    monkeypatch.setenv("JARVIS_STT_SUPPRESS_TOKENS", "1,2, 3")

    stt = _make_stt()
    kwargs = stt._build_whisper_kwargs()

    assert kwargs["vad_filter"] is True
    assert kwargs["beam_size"] == 5
    assert kwargs["best_of"] == 2
    assert kwargs["temperature"] == 0.2
    assert kwargs["initial_prompt"] == "ola"
    assert kwargs["suppress_tokens"] == [1, 2, 3]


def test_whisper_kwargs_invalid_suppress_tokens(monkeypatch):
    monkeypatch.setenv("JARVIS_STT_SUPPRESS_TOKENS", "1, x")
    stt = _make_stt()
    kwargs = stt._build_whisper_kwargs()
    assert "suppress_tokens" not in kwargs
