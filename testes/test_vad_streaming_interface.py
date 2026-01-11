from __future__ import annotations

import types

import pytest

from jarvis.voz import vad as vad_module


def test_voice_activity_detector_frames_and_validation(monkeypatch):
    class DummyVad:
        def __init__(self, aggressiveness):
            self._aggressiveness = aggressiveness

        def is_speech(self, frame, sample_rate):
            return True

    monkeypatch.setattr(vad_module, "webrtcvad", types.SimpleNamespace(Vad=DummyVad))

    detector = vad_module.VoiceActivityDetector(
        aggressiveness=1,
        sample_rate=16000,
        frame_duration_ms=10,
    )
    frame = b"\x00" * detector.bytes_per_frame
    assert detector.is_speech(frame) is True

    frames = list(detector.frames_from_audio(frame * 2))
    assert len(frames) == 2

    with pytest.raises(vad_module.VADError):
        detector.is_speech(b"\x00")


def test_vad_aggressiveness_env_override(monkeypatch):
    class DummyVad:
        def __init__(self, aggressiveness):
            self.aggressiveness = aggressiveness

        def is_speech(self, frame, sample_rate):
            return True

    monkeypatch.setattr(vad_module, "webrtcvad", types.SimpleNamespace(Vad=DummyVad))
    monkeypatch.setenv("JARVIS_VAD_AGGRESSIVENESS", "0")

    detector = vad_module.VoiceActivityDetector()
    assert detector._vad.aggressiveness == 0


def test_vad_aggressiveness_env_clamp(monkeypatch):
    class DummyVad:
        def __init__(self, aggressiveness):
            self.aggressiveness = aggressiveness

        def is_speech(self, frame, sample_rate):
            return True

    monkeypatch.setattr(vad_module, "webrtcvad", types.SimpleNamespace(Vad=DummyVad))
    monkeypatch.setenv("JARVIS_VAD_AGGRESSIVENESS", "9")

    detector = vad_module.VoiceActivityDetector()
    assert detector._vad.aggressiveness == 3


def test_vad_preprocess_noise_gate(monkeypatch):
    np = pytest.importorskip("numpy")

    class DummyVad:
        def __init__(self, aggressiveness):
            self.last_frame = None

        def is_speech(self, frame, sample_rate):
            self.last_frame = frame
            return True

    monkeypatch.setattr(vad_module, "webrtcvad", types.SimpleNamespace(Vad=DummyVad))
    monkeypatch.setenv("JARVIS_VAD_PREPROCESS", "1")
    monkeypatch.setenv("JARVIS_AUDIO_NS_GATE_RMS", "0.5")

    detector = vad_module.VoiceActivityDetector()
    frame = (np.ones(detector.frame_size, dtype=np.int16) * 2).tobytes()
    detector.is_speech(frame)

    assert detector._vad.last_frame is not None
    assert set(detector._vad.last_frame) == {0}


def test_streaming_vad_record_fixed_duration_speech_detected(monkeypatch):
    np = pytest.importorskip("numpy")

    class DummyVAD:
        def __init__(self, *args, **kwargs):
            self.frame_size = 4
            self.frame_duration_ms = 20

        def frames_from_audio(self, audio_bytes):
            step = self.frame_size * 2
            for i in range(0, len(audio_bytes), step):
                yield audio_bytes[i : i + step]

        def is_speech(self, frame):
            return True

    class DummySD:
        def __init__(self):
            self.device_used = None

        def rec(
            self,
            total_samples,
            samplerate=16000,
            channels=1,
            dtype="float32",
            device=None,
        ):
            self.device_used = device
            return np.ones((total_samples, channels), dtype=np.float32)

        def wait(self):
            return None

    monkeypatch.setattr(vad_module, "VoiceActivityDetector", DummyVAD)
    dummy_sd = DummySD()
    monkeypatch.setattr(vad_module, "sd", dummy_sd)
    monkeypatch.setattr(vad_module, "np", np)

    vad = vad_module.StreamingVAD(sample_rate=16000)
    audio_bytes, speech_detected = vad.record_fixed_duration(seconds=1)

    assert isinstance(audio_bytes, bytes)
    assert audio_bytes
    assert speech_detected is True


def test_streaming_vad_record_fixed_duration_no_speech(monkeypatch):
    np = pytest.importorskip("numpy")

    class DummyVAD:
        def __init__(self, *args, **kwargs):
            self.frame_size = 4
            self.frame_duration_ms = 20

        def frames_from_audio(self, audio_bytes):
            step = self.frame_size * 2
            for i in range(0, len(audio_bytes), step):
                yield audio_bytes[i : i + step]

        def is_speech(self, frame):
            return False

    class DummySD:
        def __init__(self):
            self.device_used = None

        def rec(
            self,
            total_samples,
            samplerate=16000,
            channels=1,
            dtype="float32",
            device=None,
        ):
            self.device_used = device
            return np.ones((total_samples, channels), dtype=np.float32)

        def wait(self):
            return None

    monkeypatch.setattr(vad_module, "VoiceActivityDetector", DummyVAD)
    dummy_sd = DummySD()
    monkeypatch.setattr(vad_module, "sd", dummy_sd)
    monkeypatch.setattr(vad_module, "np", np)

    vad = vad_module.StreamingVAD(sample_rate=16000)
    audio_bytes, speech_detected = vad.record_fixed_duration(seconds=1)

    assert isinstance(audio_bytes, bytes)
    assert audio_bytes
    assert speech_detected is False


def test_streaming_vad_uses_device_in_record_fixed_duration(monkeypatch):
    np = pytest.importorskip("numpy")

    class DummyVAD:
        def __init__(self, *args, **kwargs):
            self.frame_size = 4
            self.frame_duration_ms = 20

        def frames_from_audio(self, audio_bytes):
            step = self.frame_size * 2
            for i in range(0, len(audio_bytes), step):
                yield audio_bytes[i : i + step]

        def is_speech(self, frame):
            return True

    class DummySD:
        def __init__(self):
            self.device_used = None

        def rec(
            self,
            total_samples,
            samplerate=16000,
            channels=1,
            dtype="float32",
            device=None,
        ):
            self.device_used = device
            return np.ones((total_samples, channels), dtype=np.float32)

        def wait(self):
            return None

    monkeypatch.setattr(vad_module, "VoiceActivityDetector", DummyVAD)
    dummy_sd = DummySD()
    monkeypatch.setattr(vad_module, "sd", dummy_sd)
    monkeypatch.setattr(vad_module, "np", np)

    vad = vad_module.StreamingVAD(sample_rate=16000, device=3)
    vad.record_fixed_duration(seconds=1)

    assert dummy_sd.device_used == 3
