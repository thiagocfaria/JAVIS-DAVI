from __future__ import annotations

import types
from pathlib import Path

from jarvis.cerebro.orchestrator import Orchestrator
from jarvis.entrada.audio_utils import SAMPLE_RATE
from jarvis.entrada.followup import FollowUpSession
from jarvis.entrada.stt import apply_wake_word_filter


def test_followup_allows_without_wake_word_within_window() -> None:
    session = FollowUpSession(followup_seconds=20, max_commands=2)
    now = 100.0

    assert session.should_require_wake_word(True, now=now) is True

    session.on_command_accepted(True, now=now)
    require = session.should_require_wake_word(True, now=now + 5)
    assert require is False
    assert (
        apply_wake_word_filter("abrir navegador", wake_word="jarvis", require=require)
        == "abrir navegador"
    )


def test_followup_expires_and_requires_wake_word() -> None:
    session = FollowUpSession(followup_seconds=10, max_commands=2)
    now = 200.0

    session.on_command_accepted(True, now=now)
    require = session.should_require_wake_word(True, now=now + 11)
    assert require is True
    assert (
        apply_wake_word_filter("abrir navegador", wake_word="jarvis", require=require)
        == ""
    )


def test_followup_resets_on_speaker_verify_failure() -> None:
    class DummySTT:
        def requires_wake_word(self) -> bool:
            return True

        def transcribe_with_vad(
            self,
            max_seconds: int = 5,
            return_audio: bool = True,
            require_wake_word: bool = True,
        ) -> tuple[str, bytes, bool]:
            audio = b"\x01\x00" * SAMPLE_RATE
            return "ligar luz", audio, True

    session = FollowUpSession(followup_seconds=20, max_commands=2)
    session.renew(now=0.0)
    handled: list[str] = []
    messages: list[str] = []

    class DummyVerifier:
        def is_enabled(self) -> bool:
            return True

        def is_available(self) -> bool:
            return True

        def voiceprint_path(self) -> Path:
            return Path("/tmp/voiceprint.json")

        def load_voiceprint(self, path: str) -> dict[str, list[float]]:
            return {"embedding": [0.1]}

        def verify_ok(self, audio_bytes: bytes, sample_rate: int) -> tuple[float, bool]:
            return 0.1, False

    def _handle(text: str) -> tuple[str, bool]:
        handled.append(text)
        return "ok", True

    def _debug(message: str) -> None:
        pass

    def _say(message: str) -> None:
        messages.append(message)

    fake = types.SimpleNamespace(
        stt=DummySTT(),
        _followup=session,
        _speaker_verifier=DummyVerifier(),
        _debug=_debug,
        _say=_say,
        handle_text=_handle,
    )

    Orchestrator.transcribe_and_handle(fake)  # type: ignore[misc]

    assert handled == []
    assert session.followup_until == 0.0


def test_followup_resets_when_command_fails() -> None:
    class DummySTT:
        def requires_wake_word(self) -> bool:
            return True

        def transcribe_with_vad(
            self,
            max_seconds: int = 5,
            return_audio: bool = True,
            require_wake_word: bool = True,
        ) -> tuple[str, bytes, bool]:
            audio = b"\x01\x00" * SAMPLE_RATE
            return "ligar luz", audio, True

    session = FollowUpSession(followup_seconds=20, max_commands=2)
    session.renew(now=0.0)

    class DummyVerifier:
        def is_enabled(self) -> bool:
            return False

    def _debug(message: str) -> None:
        pass

    def _say(message: str) -> None:
        pass

    def _handle_text(text: str) -> tuple[str, bool]:
        return ("approval_denied", False)

    fake = types.SimpleNamespace(
        stt=DummySTT(),
        _followup=session,
        _speaker_verifier=DummyVerifier(),
        _debug=_debug,
        _say=_say,
        handle_text=_handle_text,
    )

    Orchestrator.transcribe_and_handle(fake)  # type: ignore[misc]

    assert session.followup_until == 0.0


def test_followup_resets_after_max_commands() -> None:
    session = FollowUpSession(followup_seconds=20, max_commands=2)
    now = 10.0

    session.on_command_accepted(True, now=now)
    assert session.should_require_wake_word(True, now=now + 1) is False

    session.on_command_accepted(True, now=now + 2)
    assert session.should_require_wake_word(True, now=now + 3) is True
