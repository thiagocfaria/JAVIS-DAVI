from __future__ import annotations

import types
from pathlib import Path

import pytest

import jarvis.cerebro.orchestrator as orch_module
from jarvis.entrada.audio_utils import SAMPLE_RATE
from jarvis.entrada.followup import FollowUpSession
from typing import cast, get_type_hints

from jarvis.voz.adapters.base import SampleRate, validate_audio_i16
from jarvis.voz.adapters import wakeword_openwakeword as oww
from jarvis.voz.adapters import wakeword_porcupine as ww
from jarvis.voz.adapters.wakeword_text import TextWakeWordDetector
from jarvis.voz.adapters.speaker_resemblyzer import ResemblyzerSpeakerVerifier
from jarvis.voz import speaker_verify


def test_orchestrator_does_not_import_speaker_verify():
    assert not hasattr(orch_module, "speaker_verify")


def test_transcribe_uses_speaker_verifier_adapter():
    class DummySTT:
        def requires_wake_word(self):
            return True

        def transcribe_with_vad(
            self, max_seconds=5, return_audio=True, require_wake_word=True
        ):
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

    orch_module.Orchestrator.transcribe_and_handle(cast(orch_module.Orchestrator, fake))

    assert verifier.called is True


def test_validate_audio_i16_rejects_invalid() -> None:
    assert validate_audio_i16(b"", 16000) == "empty_audio"
    assert validate_audio_i16(b"\x00", 16000) == "invalid_audio_length"
    assert validate_audio_i16(b"\x00\x00", 0) == "invalid_sample_rate"


def test_speaker_adapter_skips_invalid_audio(monkeypatch):
    verifier = ResemblyzerSpeakerVerifier()

    def _boom(*args, **kwargs):
        raise RuntimeError("should not be called")

    monkeypatch.setattr(speaker_verify, "verify_speaker", _boom)

    score, ok = verifier.verify_ok(b"\x00", 16000)
    assert score == 0.0
    assert ok is False

    assert verifier.verify(b"\x00", 16000) == 0.0


def test_adapter_sample_rate_type_hint() -> None:
    hints = get_type_hints(TextWakeWordDetector.detect)
    assert hints["sample_rate"] == SampleRate


def test_porcupine_detector_detects_keyword(monkeypatch):
    class DummyPorcupine:
        frame_length = 4

        def __init__(self) -> None:
            self.calls = 0

        def process(self, frame):
            self.calls += 1
            return 0 if self.calls == 2 else -1

        def delete(self) -> None:
            return None

    def fake_create(**kwargs):
        assert kwargs.get("access_key") == "abc"
        return DummyPorcupine()

    monkeypatch.setattr(ww, "pvporcupine", types.SimpleNamespace(create=fake_create))
    monkeypatch.setenv("JARVIS_PORCUPINE_ACCESS_KEY", "abc")

    detector = ww.build_porcupine_detector("jarvis")
    assert detector is not None
    audio = b"\x01\x00" * 8  # 8 samples -> 2 frames
    assert detector.detect(audio, 16000) is True


def test_porcupine_detector_rejects_invalid_audio(monkeypatch):
    class DummyPorcupine:
        frame_length = 4

        def process(self, frame):
            return -1

        def delete(self) -> None:
            return None

    monkeypatch.setattr(
        ww,
        "pvporcupine",
        types.SimpleNamespace(create=lambda **kwargs: DummyPorcupine()),
    )
    monkeypatch.setenv("JARVIS_PORCUPINE_ACCESS_KEY", "abc")

    detector = ww.build_porcupine_detector("jarvis")
    assert detector is not None
    assert detector.detect(b"\x00", 16000) is False
    assert detector.detect(b"\x00\x00" * 4, cast(SampleRate, 8000)) is False


def test_porcupine_detector_requires_access_key(monkeypatch):
    monkeypatch.setattr(
        ww, "pvporcupine", types.SimpleNamespace(create=lambda **kwargs: object())
    )
    monkeypatch.delenv("JARVIS_PORCUPINE_ACCESS_KEY", raising=False)

    assert ww.build_porcupine_detector("jarvis") is None


def test_openwakeword_detector_detects_keyword(monkeypatch):
    if oww.np is None:
        pytest.skip("numpy ausente")

    class DummyModel:
        def __init__(self, **kwargs) -> None:
            self.models = {"dummy": object()}
            self.prediction_buffer = {"dummy": [0.1]}

        def predict(self, pcm):
            self.prediction_buffer["dummy"] = [0.8]

    monkeypatch.setattr(oww, "Model", DummyModel)
    monkeypatch.setattr(
        oww,
        "openwakeword",
        types.SimpleNamespace(
            utils=types.SimpleNamespace(download_models=lambda: None)
        ),
    )

    detector = oww.build_openwakeword_detector(
        "jarvis", model_paths="dummy.onnx", auto_download=False
    )
    assert detector is not None
    audio = b"\x01\x00" * 8
    assert detector.detect(audio, 16000) is True


def test_openwakeword_detector_requires_models(monkeypatch):
    if oww.np is None:
        pytest.skip("numpy ausente")

    class DummyModel:
        def __init__(self, **kwargs) -> None:
            self.models = {}
            self.prediction_buffer = {}

        def predict(self, pcm):
            return None

    monkeypatch.setattr(oww, "Model", DummyModel)
    monkeypatch.setattr(
        oww,
        "openwakeword",
        types.SimpleNamespace(
            utils=types.SimpleNamespace(download_models=lambda: None)
        ),
    )

    detector = oww.build_openwakeword_detector(
        "jarvis", model_paths="dummy.onnx", auto_download=False
    )
    assert detector is None
