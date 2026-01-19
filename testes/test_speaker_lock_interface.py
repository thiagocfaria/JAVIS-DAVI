from jarvis.cerebro.config import load_config
from jarvis.interface.entrada import speaker_verify
from jarvis.interface.entrada.stt import SpeechToText


def test_speaker_lock_rejects_when_locked(monkeypatch) -> None:
    monkeypatch.setenv("JARVIS_SPK_VERIFY", "1")
    stt = SpeechToText(load_config())
    stt._speaker_locked = True

    monkeypatch.setattr(speaker_verify, "is_enabled", lambda: True)
    monkeypatch.setattr(speaker_verify, "is_available", lambda: True)
    monkeypatch.setattr(speaker_verify, "has_voiceprint", lambda: True)
    monkeypatch.setattr(
        speaker_verify, "verify_speaker", lambda _audio, _sr: (0.2, False)
    )

    audio = b"\x01\x00" * 16000
    assert stt._speaker_accepts(audio) is False


def test_speaker_lock_enrolls_first(monkeypatch) -> None:
    monkeypatch.setenv("JARVIS_SPK_VERIFY", "1")
    stt = SpeechToText(load_config())

    monkeypatch.setattr(speaker_verify, "is_enabled", lambda: True)
    monkeypatch.setattr(speaker_verify, "is_available", lambda: True)
    monkeypatch.setattr(speaker_verify, "has_voiceprint", lambda: False)
    monkeypatch.setattr(
        speaker_verify, "enroll_speaker", lambda _audio, _sr: [0.1, 0.2]
    )

    audio = b"\x01\x00" * 16000
    assert stt._speaker_accepts(audio) is True
    assert stt._speaker_locked is True
