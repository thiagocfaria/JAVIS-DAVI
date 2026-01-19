from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis.entrada.stt import SpeechToText
from jarvis.voz.adapters import stt_realtimestt

np = pytest.importorskip("numpy")


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


class _DummyRecorder:
    def __init__(self, text: str, audio) -> None:
        self._text = text
        self.last_transcription_bytes = audio
        self.on_realtime_transcription_update = None

    def text(self) -> str:
        if self.on_realtime_transcription_update:
            self.on_realtime_transcription_update("parcial")
        return self._text

    def abort(self) -> None:
        return None


def test_realtimestt_enabled_uses_backend(monkeypatch):
    monkeypatch.setenv("JARVIS_STT_STREAMING", "1")
    monkeypatch.setenv("JARVIS_REQUIRE_WAKE_WORD", "1")
    dummy = _DummyRecorder(
        "jarvis abrir navegador",
        np.zeros(16000, dtype=np.float32),
    )

    def fake_build_recorder(**kwargs):
        dummy.on_realtime_transcription_update = kwargs.get(
            "on_realtime_transcription_update"
        )
        return dummy

    monkeypatch.setattr(stt_realtimestt, "is_available", lambda: True)
    monkeypatch.setattr(stt_realtimestt, "build_recorder", fake_build_recorder)

    stt = _make_stt()

    def _fail(*args, **kwargs):
        raise AssertionError("fallback nao deveria rodar")

    monkeypatch.setattr(stt, "_record_until_silence", _fail)
    assert (
        stt.transcribe_with_vad(max_seconds=1, require_wake_word=True)
        == "abrir navegador"
    )


def test_realtimestt_falls_back_when_unavailable(monkeypatch):
    monkeypatch.setenv("JARVIS_STT_STREAMING", "1")
    monkeypatch.delenv("JARVIS_REQUIRE_WAKE_WORD", raising=False)
    monkeypatch.setattr(stt_realtimestt, "is_available", lambda: False)

    stt = _make_stt()
    monkeypatch.setattr(
        stt, "_record_until_silence", lambda *_: (b"\x01\x02" * 20000, True)
    )
    monkeypatch.setattr(stt, "_transcribe_audio_bytes", lambda *_a, **_k: "ok")

    assert stt.transcribe_with_vad(max_seconds=1) == "ok"


def test_realtimestt_reuses_recorder_when_enabled(monkeypatch):
    monkeypatch.setenv("JARVIS_STT_STREAMING", "1")
    monkeypatch.setenv("JARVIS_STT_STREAMING_REUSE_RECORDER", "1")
    dummy = _DummyRecorder(
        "jarvis abrir navegador",
        np.zeros(16000, dtype=np.float32),
    )
    calls = {"build": 0}

    def fake_build_recorder(**kwargs):
        calls["build"] += 1
        dummy.on_realtime_transcription_update = kwargs.get(
            "on_realtime_transcription_update"
        )
        return dummy

    monkeypatch.setattr(stt_realtimestt, "is_available", lambda: True)
    monkeypatch.setattr(stt_realtimestt, "build_recorder", fake_build_recorder)

    stt = _make_stt()
    assert stt.transcribe_with_vad(max_seconds=1) == "abrir navegador"
    assert stt.transcribe_with_vad(max_seconds=1) == "abrir navegador"
    assert calls["build"] == 1
