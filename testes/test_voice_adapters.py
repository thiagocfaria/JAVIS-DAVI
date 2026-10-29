from __future__ import annotations

import types
from pathlib import Path

import jarvis.cerebro.orchestrator as orch_module
from jarvis.entrada.audio_utils import SAMPLE_RATE
from jarvis.entrada.followup import FollowUpSession


def test_orchestrator_does_not_import_speaker_verify():
    assert not hasattr(orch_module, "speaker_verify")


def test_transcribe_uses_speaker_verifier_adapter():
    class DummySTT:
        def requires_wake_word(self):
            return True

        def transcribe_with_vad(self, max_seconds=5, return_audio=True, require_wake_word=True):
            audio = b"\x01\x00" * SAMPLE_RATE
            return "ligar luz", audio, True

    class DummyVerifier:
        def __init__(self) -> None:
            self.called = False

        def is_enabled(self) -> bool:
            return True

        def is_available(self) -> bool:
            return True

        def voiceprint_path(self) -> Path:
            return Path("/tmp/voiceprint.json")

        def load_voiceprint(self, path: str):
            return {"embedding": [0.1]}

        def verify_ok(self, audio_bytes: bytes, sample_rate: int):
            self.called = True
            return 0.9, True

    verifier = DummyVerifier()
    session = FollowUpSession(followup_seconds=20)

    fake = types.SimpleNamespace(
        stt=DummySTT(),
        _followup=session,
        _speaker_verifier=verifier,
        _debug=lambda message: None,
        _say=lambda message: None,
        handle_text=lambda text: ("ok", True),
    )

    orch_module.Orchestrator.transcribe_and_handle(fake)

    assert verifier.called is True
