from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis.entrada import stt as stt_module
from jarvis.entrada.stt import SpeechToText


def _make_stt():
    cfg = SimpleNamespace(
        stt_mode="local",
        stt_model_size="tiny",
        stt_audio_trim_backend="none",
    )
    return SpeechToText(cfg)


def test_record_until_silence_bypasses_streaming_when_capture_sr_diff(monkeypatch):
    stt = _make_stt()
    called = {"stream": 0, "fixed": 0}

    class DummyStreaming:
        def record_until_silence(self, *args, **kwargs):
            called["stream"] += 1
            return b"bad"

    stt._streaming_vad = DummyStreaming()

    monkeypatch.setattr(stt, "_resolve_capture_config", lambda: (None, 44100, "dev"))

    def fake_fixed(seconds, **kwargs):
        called["fixed"] += 1
        return b"ok", True

    monkeypatch.setattr(stt, "_record_fixed_duration_compat", fake_fixed)

    audio_bytes, speech_detected = stt._record_until_silence(3)
    assert audio_bytes == b"ok"
    assert speech_detected is True
    assert called["stream"] == 0
    assert called["fixed"] == 1


def test_record_until_silence_uses_streaming_when_capture_sr_matches(monkeypatch):
    stt = _make_stt()
    called = {"stream": 0}

    class DummyStreaming:
        def record_until_silence(self, *args, **kwargs):
            called["stream"] += 1
            return (b"bytes", True)

    stt._streaming_vad = DummyStreaming()
    monkeypatch.setattr(stt, "_resolve_capture_config", lambda: (None, stt_module.SAMPLE_RATE, "dev"))

    audio_bytes, speech_detected = stt._record_until_silence(3)
    assert audio_bytes == b"bytes"
    assert speech_detected is True
    assert called["stream"] == 1


def test_record_audio_bypasses_streaming_when_capture_sr_diff(monkeypatch):
    stt = _make_stt()
    called = {"stream": 0, "fixed": 0}

    class DummyStreaming:
        def record_until_silence(self, *args, **kwargs):
            called["stream"] += 1
            return b"bad"

    stt._streaming_vad = DummyStreaming()
    monkeypatch.setattr(stt, "_resolve_capture_config", lambda: (None, 44100, "dev"))

    def fake_fixed(seconds, **kwargs):
        called["fixed"] += 1
        return b"ok", True

    monkeypatch.setattr(stt, "_record_fixed_duration_compat", fake_fixed)

    audio_bytes = stt._record_audio(3)
    assert audio_bytes == b"ok"
    assert called["stream"] == 0
    assert called["fixed"] == 1


def test_resolve_capture_config_uses_env_override(monkeypatch):
    stt = _make_stt()

    class DummySD:
        def query_devices(self, device, kind):
            return {"name": "mic", "default_samplerate": 48000}

    monkeypatch.setattr(stt_module, "sd", DummySD())
    monkeypatch.setattr(stt, "_audio_device", 3)
    monkeypatch.setattr(stt, "_capture_sr_override", 44100)

    device, capture_sr, name = stt._resolve_capture_config()
    assert device == 3
    assert capture_sr == 44100
    assert name == "mic"
