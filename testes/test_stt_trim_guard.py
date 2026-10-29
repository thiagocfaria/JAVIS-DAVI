from __future__ import annotations

from testes.test_stt_flow import _make_stt


def test_trim_with_rust_none_does_not_crash(monkeypatch, tmp_path) -> None:
    stt = _make_stt(tmp_path)
    stt._require_wake_word = False
    stt._normalize_audio = False
    stt._min_audio_ms = 0

    monkeypatch.setattr(stt, "_trim_with_rust", lambda audio, force=False: None)
    monkeypatch.setattr(stt, "_transcribe_local", lambda audio: "Oi")
    monkeypatch.setattr(stt, "check_speech_present", lambda audio: True)

    result = stt._transcribe_audio_bytes(b"\x01\x02" * 200)
    assert result == "Oi"
