from __future__ import annotations

import math

import pytest

np = pytest.importorskip("numpy")

from jarvis.entrada.stt import resample_audio_float


def test_resample_audio_float_length():
    source_sr = 44100
    target_sr = 16000
    duration_s = 0.5
    t = np.arange(int(source_sr * duration_s)) / source_sr
    signal = np.sin(2 * math.pi * 440.0 * t).astype(np.float32)

    resampled = resample_audio_float(signal, source_sr, target_sr)

    expected_len = int(duration_s * target_sr)
    assert abs(len(resampled) - expected_len) <= 2
