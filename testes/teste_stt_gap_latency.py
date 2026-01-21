from __future__ import annotations

import pytest

from jarvis.entrada.stt import SpeechToText


class _DummyConfig:
    stt_model_size = "tiny"
    stt_audio_trim_backend = "none"


@pytest.fixture()
def stt(monkeypatch):
    monkeypatch.setattr("jarvis.entrada.stt.check_vad_available", lambda: False)
    return SpeechToText(_DummyConfig())  # type: ignore[arg-type]


def test_transcribe_once_respects_min_gap(monkeypatch, stt) -> None:
    stt._min_gap_seconds = 1.0
    stt._last_record_end_ts = 100.0

    called = {"record": 0}

    def fake_record(seconds: int) -> bytes:
        called["record"] += 1
        return b"\x01\x02" * 50

    stt._record_audio = fake_record  # type: ignore[assignment]
    stt._transcribe_audio_bytes = lambda *_args, **_kwargs: "ok"  # type: ignore[assignment]

    monkeypatch.setattr("jarvis.entrada.stt.time.monotonic", lambda: 100.5)
    assert stt.transcribe_once(1) == ""
    assert called["record"] == 0

    monkeypatch.setattr("jarvis.entrada.stt.time.monotonic", lambda: 101.5)
    assert stt.transcribe_once(1) == "ok"
    assert called["record"] == 1


def test_transcribe_once_latency_limit(monkeypatch, stt) -> None:
    stt._allowed_latency_ms = 50.0
    stt._record_audio = lambda _seconds: b"\x01\x02" * 10  # type: ignore[assignment]
    stt._transcribe_audio_bytes = lambda *_args, **_kwargs: "ok"  # type: ignore[assignment]

    times = iter([0.0, 0.01, 0.02, 0.12])
    monkeypatch.setattr("jarvis.entrada.stt.time.perf_counter", lambda: next(times))

    assert stt.transcribe_once(1) == ""


def test_normalize_audio_increases_peak(monkeypatch) -> None:
    np = pytest.importorskip("numpy")
    monkeypatch.setattr("jarvis.entrada.stt.check_vad_available", lambda: False)

    stt = SpeechToText(_DummyConfig())  # type: ignore[arg-type]
    stt._normalize_audio = True
    stt._normalize_target = 0.9
    stt._normalize_max_gain = 10.0

    samples = np.array([1000, -1000], dtype=np.int16)
    out = stt._maybe_normalize_for_stt(samples.tobytes())
    out_samples = np.frombuffer(out, dtype=np.int16)

    assert np.max(np.abs(out_samples)) > np.max(np.abs(samples))
