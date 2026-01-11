from __future__ import annotations

import math
import wave
from pathlib import Path

import pytest

from scripts import bench_interface


def _write_wav(path: Path, samplerate: int, samples: "list[int]") -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(samplerate)
        data = b"".join(int(s).to_bytes(2, "little", signed=True) for s in samples)
        handle.writeframes(data)


def test_load_audio_requires_16k_without_resample(tmp_path: Path) -> None:
    samples = [0] * 441
    audio_path = tmp_path / "audio_44k.wav"
    _write_wav(audio_path, 44100, samples)

    with pytest.raises(ValueError):
        bench_interface._load_audio(audio_path, 16000, resample=False)


def test_load_audio_resamples_to_16k(tmp_path: Path) -> None:
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")

    source_sr = 44100
    duration_s = 0.1
    t = np.arange(int(source_sr * duration_s)) / source_sr
    signal = (np.sin(2 * math.pi * 440.0 * t) * 1000).astype(np.int16)
    audio_path = tmp_path / "audio_44k.wav"
    _write_wav(audio_path, source_sr, signal.tolist())

    frames, samplerate, channels = bench_interface._load_audio(
        audio_path, 16000, resample=True
    )

    assert samplerate == 16000
    assert channels == 1
    expected_len = int(duration_s * 16000) * 2
    assert abs(len(frames) - expected_len) <= 4


def test_measure_includes_psutil_metrics_when_available(monkeypatch):
    class DummyMem:
        rss = 123
        vms = 456

    class DummyProc:
        def __init__(self):
            self.calls = 0

        def cpu_percent(self, interval=None):
            self.calls += 1
            return 12.5

        def memory_info(self):
            return DummyMem()

    class DummyPsutil:
        def Process(self):
            return DummyProc()

    monkeypatch.setattr(bench_interface, "psutil", DummyPsutil())
    result = bench_interface._measure(lambda: None, repeat=1)
    assert result["psutil_available"] is True
    assert result["psutil_cpu_percent"] == 12.5
    assert result["psutil_rss_bytes"] == 123
    assert result["psutil_vms_bytes"] == 456


def test_measure_skips_psutil_when_missing(monkeypatch):
    monkeypatch.setattr(bench_interface, "psutil", None)
    result = bench_interface._measure(lambda: None, repeat=1)
    assert "psutil_available" not in result


def test_measure_includes_gpu_metrics_when_available(monkeypatch):
    monkeypatch.setattr(bench_interface.shutil, "which", lambda name: "/bin/nvidia-smi")

    class DummyResult:
        stdout = "35, 120, 4096\n"

    def fake_run(*args, **kwargs):
        return DummyResult()

    monkeypatch.setattr(bench_interface.subprocess, "run", fake_run)

    result = bench_interface._measure(lambda: None, repeat=1, enable_gpu=True)
    assert result["gpu_available"] is True
    assert result["gpu_util_percent"] == 35
    assert result["gpu_mem_used_mb"] == 120
    assert result["gpu_mem_total_mb"] == 4096


def test_measure_marks_gpu_unavailable(monkeypatch):
    monkeypatch.setattr(bench_interface.shutil, "which", lambda name: None)
    result = bench_interface._measure(lambda: None, repeat=1, enable_gpu=True)
    assert result["gpu_available"] is False
