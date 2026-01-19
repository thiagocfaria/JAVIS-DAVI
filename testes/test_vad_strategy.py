from __future__ import annotations

from jarvis.entrada import stt as stt_module
from testes.test_stt_flow import _make_stt


def _disable_webrtc_deps(monkeypatch) -> None:
    monkeypatch.setattr(stt_module, "check_vad_available", lambda: False)
    monkeypatch.setattr(stt_module, "VADRecorder", None)
    monkeypatch.setattr(stt_module, "StreamingVAD", None)


def test_vad_strategy_webrtc_disables_other_vads(monkeypatch, tmp_path) -> None:
    _disable_webrtc_deps(monkeypatch)
    monkeypatch.setenv("JARVIS_VAD_STRATEGY", "webrtc")
    monkeypatch.setenv("JARVIS_SILERO_DEACTIVITY", "1")
    monkeypatch.setenv("JARVIS_WHISPER_VAD_FILTER", "1")

    stt = _make_stt(tmp_path)

    assert stt._webrtc_vad_enabled is True
    assert stt._silero_deactivity_enabled is False
    assert stt._whisper_vad_filter is False


def test_vad_strategy_silero_disables_webrtc(monkeypatch, tmp_path) -> None:
    _disable_webrtc_deps(monkeypatch)
    monkeypatch.setenv("JARVIS_VAD_STRATEGY", "silero")
    monkeypatch.delenv("JARVIS_SILERO_DEACTIVITY", raising=False)
    monkeypatch.setenv("JARVIS_WHISPER_VAD_FILTER", "1")

    stt = _make_stt(tmp_path)

    assert stt._webrtc_vad_enabled is False
    assert stt._silero_deactivity_enabled is True
    assert stt._whisper_vad_filter is False


def test_vad_strategy_realtimestt_disables_other_vads(monkeypatch, tmp_path) -> None:
    _disable_webrtc_deps(monkeypatch)
    monkeypatch.setenv("JARVIS_VAD_STRATEGY", "realtimestt")
    monkeypatch.setenv("JARVIS_SILERO_DEACTIVITY", "1")
    monkeypatch.setenv("JARVIS_WHISPER_VAD_FILTER", "1")

    stt = _make_stt(tmp_path)

    assert stt._webrtc_vad_enabled is False
    assert stt._silero_deactivity_enabled is False
    assert stt._whisper_vad_filter is False
    assert stt._stt_streaming_enabled is True
