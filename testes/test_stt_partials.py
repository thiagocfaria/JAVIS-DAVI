from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis.entrada.stt import SpeechToText


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


def test_transcribe_audio_bytes_emits_partials(monkeypatch):
    monkeypatch.setenv("JARVIS_STT_MIN_AUDIO_MS", "0")
    stt = _make_stt()
    stt._min_audio_ms = 0
    stt.check_speech_present = lambda _audio: True  # type: ignore[assignment]

    received: list[str] = []

    def on_partial(text: str) -> None:
        received.append(text)

    def fake_transcribe(audio_bytes, *, on_partial=None, realtime=False):
        assert on_partial is not None
        on_partial("ola")
        on_partial("ola mundo")
        return "ola mundo"

    monkeypatch.setattr(stt, "_transcribe_local", fake_transcribe)
    result = stt.transcribe_audio_bytes(b"\x01\x02", on_partial=on_partial)

    assert result == "ola mundo"
    assert received == ["ola", "ola mundo"]


def test_transcribe_audio_bytes_uses_realtime_model_when_configured(monkeypatch):
    monkeypatch.setenv("JARVIS_STT_MIN_AUDIO_MS", "0")
    monkeypatch.setenv("JARVIS_STT_REALTIME_MODEL", "tiny")
    stt = _make_stt()
    stt._min_audio_ms = 0
    stt.check_speech_present = lambda _audio: True  # type: ignore[assignment]

    seen: dict[str, bool] = {}

    def fake_transcribe(audio_bytes, *, on_partial=None, realtime=False):
        seen["realtime"] = bool(realtime)
        if on_partial:
            on_partial("ok")
        return "ok"

    monkeypatch.setattr(stt, "_transcribe_local", fake_transcribe)
    stt.transcribe_audio_bytes(b"\x01\x02", on_partial=lambda _t: None)
    assert seen["realtime"] is True


def test_transcribe_audio_bytes_defaults_to_local_model(monkeypatch):
    monkeypatch.setenv("JARVIS_STT_MIN_AUDIO_MS", "0")
    monkeypatch.setenv("JARVIS_STT_REALTIME_MODEL", "tiny")
    stt = _make_stt()
    stt._min_audio_ms = 0
    stt.check_speech_present = lambda _audio: True  # type: ignore[assignment]

    seen: dict[str, bool] = {}

    def fake_transcribe(audio_bytes, *, on_partial=None, realtime=False):
        seen["realtime"] = bool(realtime)
        return "ok"

    monkeypatch.setattr(stt, "_transcribe_local", fake_transcribe)
    stt.transcribe_audio_bytes(b"\x01\x02")
    assert seen["realtime"] is False
