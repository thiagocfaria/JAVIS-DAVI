from __future__ import annotations

import types

from jarvis.entrada import stt as stt_module
from jarvis.entrada.stt import SpeechToText


def _make_config():
    return types.SimpleNamespace(  # type: ignore[return-value]
        stt_model_size="tiny",
        stt_mode="local",
        stt_audio_trim_backend="none",
    )


def test_transcribe_with_vad_logs_metrics(monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_STT_METRICS", "1")
    monkeypatch.setattr(stt_module, "check_vad_available", lambda: False)

    stt = SpeechToText(_make_config())  # type: ignore[arg-type]
    monkeypatch.setattr(
        stt,
        "_record_until_silence",
        lambda max_seconds: (b"\x00\x01" * 20, True),
    )
    monkeypatch.setattr(stt, "_transcribe_audio_bytes", lambda *args, **kwargs: "ok")

    stt.transcribe_with_vad(max_seconds=1)

    out = capsys.readouterr().out
    assert "[stt-metrics] with_vad" in out
    assert "record_ms=" in out
    assert "transcribe_ms=" in out


def test_transcribe_once_logs_metrics(monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_STT_METRICS", "1")
    monkeypatch.setattr(stt_module, "check_vad_available", lambda: False)

    stt = SpeechToText(_make_config())  # type: ignore[arg-type]
    monkeypatch.setattr(stt, "_record_audio", lambda seconds: b"\x00\x01" * 10)
    monkeypatch.setattr(stt, "_transcribe_audio_bytes", lambda *args, **kwargs: "ok")

    stt.transcribe_once(seconds=1)

    out = capsys.readouterr().out
    assert "[stt-metrics] once" in out
    assert "record_ms=" in out
    assert "transcribe_ms=" in out
