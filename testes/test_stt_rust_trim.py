from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis.entrada.stt import SpeechToText


@pytest.fixture(autouse=True)
def patch_audio(monkeypatch):
    class DummySD:
        @staticmethod
        def rec(samples, samplerate=16000, channels=1, dtype="float32"):
            return DummyNP.zeros((samples, channels), dtype="float32")

        @staticmethod
        def wait():
            return

    class DummyNP:
        @staticmethod
        def array(data, dtype=None):
            return data
        @staticmethod
        def int16():
            return "int16"
        @staticmethod
        def zeros(shape, dtype=None):
            # shape is (samples, channels)
            samples, channels = shape
            return [[0.0 for _ in range(channels)] for _ in range(samples)]
        @staticmethod
        def float32():
            return "float32"

    monkeypatch.setattr("jarvis.entrada.stt.sd", DummySD())
    monkeypatch.setattr("jarvis.entrada.stt.np", DummyNP())
    monkeypatch.setattr("jarvis.entrada.stt.check_vad_available", lambda: False)
    monkeypatch.delenv("JARVIS_AUDIO_DEVICE", raising=False)
    monkeypatch.delenv("JARVIS_AUDIO_CAPTURE_SR", raising=False)


def test_trim_rust_blocks_silence(monkeypatch):
    called = {"trim": 0, "transcribe": 0}

    # Simula VAD retornando lista de frames (bytes)
    monkeypatch.setattr(
        "jarvis.entrada.stt.SpeechToText._record_fixed_duration",
        lambda self, seconds: ([b"\x00\x00", b"\x00\x00"], True),
    )

    class FakeJarvisAudio:
        @staticmethod
        def trim_until_silence(pcm, sample_rate, frame_ms, pre, post, silence):
            called["trim"] += 1
            return b"", False, {}

    monkeypatch.setattr("jarvis.entrada.stt.jarvis_audio", FakeJarvisAudio)
    cfg = SimpleNamespace(stt_mode="local", stt_model_size="tiny", stt_audio_trim_backend="rust")
    stt = SpeechToText(cfg)
    stt._transcribe_local = lambda audio: called.__setitem__("transcribe", called["transcribe"] + 1)  # type: ignore
    stt._record_fixed_duration = lambda seconds: (b"\x00\x00", True)  # type: ignore
    assert stt.transcribe_once(5) == ""
    assert called["trim"] == 1
    assert called["transcribe"] == 0


def test_trim_rust_allows_speech(monkeypatch):
    called = {"trim": 0, "transcribe": 0}

    monkeypatch.setattr(
        "jarvis.entrada.stt.SpeechToText._record_fixed_duration",
        lambda self, seconds: ([b"\x01\x02", b"\x03\x04"], True),
    )

    class FakeJarvisAudio:
        @staticmethod
        def trim_until_silence(pcm, sample_rate, frame_ms, pre, post, silence):
            called["trim"] += 1
            return b"\x01\x02", True, {}

    monkeypatch.setattr("jarvis.entrada.stt.jarvis_audio", FakeJarvisAudio)
    cfg = SimpleNamespace(stt_mode="local", stt_model_size="tiny", stt_audio_trim_backend="rust")
    stt = SpeechToText(cfg)
    stt._record_fixed_duration = lambda seconds: (b"\x00\x00", True)  # type: ignore

    def fake_transcribe(audio):
        called["transcribe"] += 1
        return "ok"

    stt._transcribe_local = fake_transcribe  # type: ignore
    assert stt.transcribe_once(5) == "ok"
    assert called["trim"] == 1
    assert called["transcribe"] == 1


def test_trim_rust_returns_list_of_ints(monkeypatch):
    captured = {"audio_type": None, "audio_value": None}

    monkeypatch.setattr(
        "jarvis.entrada.stt.SpeechToText._record_fixed_duration",
        lambda self, seconds: (b"\x00\x00", True),
    )

    class FakeJarvisAudio:
        @staticmethod
        def trim_until_silence(pcm, sample_rate, frame_ms, pre, post, silence):
            # Simula retorno incorreto como lista de int16
            return [1, 2, 3, 4], True, {}

    monkeypatch.setattr("jarvis.entrada.stt.jarvis_audio", FakeJarvisAudio)
    cfg = SimpleNamespace(stt_mode="local", stt_model_size="tiny", stt_audio_trim_backend="rust")
    stt = SpeechToText(cfg)

    def fake_transcribe(audio):
        captured["audio_type"] = type(audio)
        captured["audio_value"] = audio
        return "ok"

    stt._transcribe_local = fake_transcribe  # type: ignore
    assert stt.transcribe_once(5) == "ok"
    assert captured["audio_type"] is bytes
    assert captured["audio_value"] != b""


def test_trim_rust_returns_list_of_frames(monkeypatch):
    captured = {"audio_type": None, "len": None}

    monkeypatch.setattr(
        "jarvis.entrada.stt.SpeechToText._record_fixed_duration",
        lambda self, seconds: (b"\x00\x00", True),
    )

    class FakeJarvisAudio:
        @staticmethod
        def trim_until_silence(pcm, sample_rate, frame_ms, pre, post, silence):
            # Simula retorno como lista de frames bytes
            return [b"\x01\x02", b"\x03\x04"], True, {}

    monkeypatch.setattr("jarvis.entrada.stt.jarvis_audio", FakeJarvisAudio)
    cfg = SimpleNamespace(stt_mode="local", stt_model_size="tiny", stt_audio_trim_backend="rust")
    stt = SpeechToText(cfg)

    def fake_transcribe(audio):
        captured["audio_type"] = type(audio)
        captured["len"] = len(audio)
        return "ok"

    stt._transcribe_local = fake_transcribe  # type: ignore
    assert stt.transcribe_once(5) == "ok"
    assert captured["audio_type"] is bytes
    assert captured["len"] == 4
