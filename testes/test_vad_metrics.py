from __future__ import annotations

from jarvis.voz import vad as vad_module


def test_vad_metrics_logs_fixed(monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_VAD_METRICS", "1")

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

    class DummyArray:
        def __init__(self, total_samples: int, channels: int) -> None:
            self._size = total_samples * channels

        def flatten(self):
            return self

        def __mul__(self, _value):
            return self

        def astype(self, _dtype):
            return self

        def tobytes(self):
            return b"\x00\x01" * self._size

    class DummySD:
        def rec(
            self,
            total_samples,
            samplerate=16000,
            channels=1,
            dtype="float32",
            device=None,
        ):
            return DummyArray(total_samples, channels)

        def wait(self):
            return None

    dummy_np = type("DummyNP", (), {"int16": int})()

    monkeypatch.setattr(vad_module, "VoiceActivityDetector", DummyVAD)
    monkeypatch.setattr(vad_module, "sd", DummySD())
    monkeypatch.setattr(vad_module, "np", dummy_np)

    vad = vad_module.StreamingVAD(sample_rate=16000)
    vad.record_fixed_duration(seconds=1)

    out = capsys.readouterr().out
    assert "[vad-metrics] fixed" in out
    assert "frames=" in out
    assert "duration_ms=" in out
