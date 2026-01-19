from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis.entrada.stt import SAMPLE_RATE, SpeechToText


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


def test_silero_deactivity_trims_audio(monkeypatch):
    stt = _make_stt()

    class DummySilero:
        def __init__(self) -> None:
            self.calls = 0

        def trim_on_deactivity(self, audio_bytes, sample_rate, post_roll_ms=0):
            self.calls += 1
            assert sample_rate == SAMPLE_RATE
            return b"trim", True

    dummy = DummySilero()
    stt._silero_detector = dummy  # type: ignore[assignment]
    stt._silero_deactivity_enabled = True
    stt._record_fixed_duration_compat = (  # type: ignore[assignment]
        lambda *args, **kwargs: (b"\x01\x02" * 10, True)
    )

    audio_bytes, speech_detected = stt._record_until_silence(1)
    assert dummy.calls == 1
    assert audio_bytes == b"trim"
    assert speech_detected is True


def test_silero_skipped_when_no_speech(monkeypatch):
    stt = _make_stt()

    class DummySilero:
        def __init__(self) -> None:
            self.calls = 0

        def trim_on_deactivity(self, audio_bytes, sample_rate, post_roll_ms=0):
            self.calls += 1
            return b"trim", True

    dummy = DummySilero()
    stt._silero_detector = dummy  # type: ignore[assignment]
    stt._silero_deactivity_enabled = True
    stt._record_fixed_duration_compat = (  # type: ignore[assignment]
        lambda *args, **kwargs: (b"\x01\x02", False)
    )

    audio_bytes, speech_detected = stt._record_until_silence(1)
    assert dummy.calls == 0
    assert audio_bytes == b"\x01\x02"
    assert speech_detected is False


def test_silero_deactivity_can_drop_audio(monkeypatch):
    stt = _make_stt()

    class DummySilero:
        def trim_on_deactivity(self, audio_bytes, sample_rate, post_roll_ms=0):
            return b"", False

    stt._silero_detector = DummySilero()  # type: ignore[assignment]
    stt._silero_deactivity_enabled = True
    stt._record_fixed_duration_compat = (  # type: ignore[assignment]
        lambda *args, **kwargs: (b"\x01\x02" * 10, True)
    )

    audio_bytes, speech_detected = stt._record_until_silence(1)
    assert audio_bytes == b""
    assert speech_detected is False
