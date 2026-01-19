from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis.entrada.stt import BYTES_PER_SAMPLE, SAMPLE_RATE, SpeechToText


@pytest.fixture(autouse=True)
def _patch_vad(monkeypatch):
    monkeypatch.setattr("jarvis.entrada.stt.check_vad_available", lambda: False)


def _make_stt() -> SpeechToText:
    cfg = SimpleNamespace(
        stt_mode="local",
        stt_model_size="tiny",
        stt_audio_trim_backend="none",
    )
    return SpeechToText(cfg)  # type: ignore[arg-type]


def test_early_transcribe_on_silence_allows_short(monkeypatch):
    monkeypatch.setenv("JARVIS_STT_EARLY_TRANSCRIBE_ON_SILENCE", "1")
    stt = _make_stt()
    stt._record_until_silence = lambda max_seconds: (b"\x01\x02", True)  # type: ignore[assignment]

    called = {"ok": False}

    def fake_transcribe(audio_bytes, **kwargs):
        called["ok"] = True
        assert kwargs.get("allow_short_audio") is True
        return "ok"

    monkeypatch.setattr(stt, "_transcribe_audio_bytes", fake_transcribe)
    assert stt.transcribe_with_vad(max_seconds=1) == "ok"
    assert called["ok"]


def test_short_audio_blocked_without_early(monkeypatch):
    monkeypatch.delenv("JARVIS_STT_EARLY_TRANSCRIBE_ON_SILENCE", raising=False)
    stt = _make_stt()
    stt._record_until_silence = lambda max_seconds: (b"\x01\x02", True)  # type: ignore[assignment]

    def fake_transcribe(*args, **kwargs):
        raise AssertionError("_transcribe_audio_bytes nao deveria rodar")

    monkeypatch.setattr(stt, "_transcribe_audio_bytes", fake_transcribe)
    assert stt.transcribe_with_vad(max_seconds=1) == ""


def test_record_until_silence_caps_buffer(monkeypatch):
    monkeypatch.setenv("JARVIS_STT_MAX_BUFFER_SECONDS", "0.01")
    stt = _make_stt()

    class DummyStreaming:
        def record_until_silence(self, **kwargs):
            return b"\x01\x02" * 1000

    stt._streaming_vad = DummyStreaming()
    monkeypatch.setattr(
        stt, "_resolve_capture_config", lambda: (None, SAMPLE_RATE, "dummy")
    )
    audio_bytes, _speech = stt._record_until_silence(2)
    expected = int(0.01 * SAMPLE_RATE * BYTES_PER_SAMPLE)
    assert len(audio_bytes) == expected


def test_transcribe_audio_bytes_calls_transcribe(monkeypatch):
    stt = _make_stt()
    seen = {"audio": b""}

    def fake_transcribe(audio_bytes, **kwargs):
        seen["audio"] = audio_bytes
        return "ok"

    monkeypatch.setattr(stt, "_transcribe_audio_bytes", fake_transcribe)
    assert stt.transcribe_audio_bytes(b"\x00\x01") == "ok"
    assert seen["audio"] == b"\x00\x01"
