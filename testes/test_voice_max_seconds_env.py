from __future__ import annotations

import types
from pathlib import Path

import pytest

from jarvis.cerebro.orchestrator import Orchestrator
from jarvis.entrada.audio_utils import SAMPLE_RATE


def _set_env(monkeypatch: pytest.MonkeyPatch, key: str, value: str | None) -> None:
    if value is None:
        monkeypatch.delenv(key, raising=False)
    else:
        monkeypatch.setenv(key, value)


class _DummyFollowup:
    def should_require_wake_word(self, require_by_default: bool) -> bool:
        return require_by_default

    def on_command_accepted(self, accepted: bool) -> None:
        return None

    def reset(self) -> None:
        return None


class _DummyVerifier:
    def is_enabled(self) -> bool:
        return False

    def is_available(self) -> bool:
        return False


class _DummySTT:
    def __init__(self) -> None:
        self.last_max_seconds: int | None = None

    def requires_wake_word(self) -> bool:
        return True

    def transcribe_with_vad(self, max_seconds=5, return_audio=True, require_wake_word=True):
        self.last_max_seconds = max_seconds
        audio = b"\x01\x00" * SAMPLE_RATE
        return "ligar luz", audio, True


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [(None, 30), ("abc", 30), ("1", 3), ("999", 120)],
)
def test_voice_max_seconds_env(monkeypatch: pytest.MonkeyPatch, env_value, expected) -> None:
    _set_env(monkeypatch, "JARVIS_VOICE_MAX_SECONDS", env_value)

    stt = _DummySTT()
    fake = types.SimpleNamespace(
        stt=stt,
        _followup=_DummyFollowup(),
        _speaker_verifier=_DummyVerifier(),
        _debug=lambda message: None,
        _say=lambda message: None,
        handle_text=lambda text: ("ok", True),
    )

    Orchestrator.transcribe_and_handle(fake)  # type: ignore[misc]

    assert stt.last_max_seconds == expected


class _DummyEnrollVerifier:
    def is_available(self) -> bool:
        return True

    def enroll(self, audio_bytes: bytes, sample_rate: int):
        return [0.1]

    def voiceprint_path(self) -> Path:
        return Path("/tmp/voiceprint.json")


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [(None, 12), ("abc", 12), ("1", 5), ("999", 60)],
)
def test_voice_enroll_max_seconds_env(monkeypatch: pytest.MonkeyPatch, env_value, expected) -> None:
    _set_env(monkeypatch, "JARVIS_VOICE_ENROLL_MAX_SECONDS", env_value)

    stt = _DummySTT()
    fake = types.SimpleNamespace(
        stt=stt,
        _speaker_verifier=_DummyEnrollVerifier(),
        _debug=lambda message: None,
        _say=lambda message: None,
    )

    assert Orchestrator._handle_meta_command(fake, "cadastrar voz") is True  # type: ignore[misc]
    assert stt.last_max_seconds == expected
