from __future__ import annotations

from array import array
import types

from jarvis.entrada import stt as stt_module
from jarvis.cerebro.config import Config
from typing import cast


def _make_stt(monkeypatch):
    monkeypatch.setattr(stt_module, "check_vad_available", lambda: False)
    monkeypatch.setattr(stt_module, "jarvis_audio", None)
    monkeypatch.setattr(stt_module, "np", None)
    config = cast(
        Config,
        types.SimpleNamespace(
            stt_mode="local",
            stt_model_size="tiny",
            stt_audio_trim_backend="none",
        ),
    )
    stt = stt_module.SpeechToText(config)
    stt._vad = None
    return stt


def _pcm_bytes(samples: list[int]) -> bytes:
    buf = array("h", samples)
    return buf.tobytes()


def test_check_speech_present_fallback_silence(monkeypatch):
    monkeypatch.setenv("JARVIS_STT_MIN_PEAK", "300")
    stt = _make_stt(monkeypatch)
    silence = _pcm_bytes([0] * 320)
    assert stt.check_speech_present(silence) is False


def test_check_speech_present_fallback_signal(monkeypatch):
    monkeypatch.setenv("JARVIS_STT_MIN_PEAK", "300")
    stt = _make_stt(monkeypatch)
    signal = _pcm_bytes([0, 1000, -1000] * 200)
    assert stt.check_speech_present(signal) is True
