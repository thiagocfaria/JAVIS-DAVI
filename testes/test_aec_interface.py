from __future__ import annotations

import pytest

from jarvis.voz import vad as vad_module


def test_aec_disabled_passthrough(monkeypatch):
    monkeypatch.delenv("JARVIS_AEC_BACKEND", raising=False)
    vad_module.reset_playback_reference()
    data = b"\x01\x02" * 100
    assert vad_module.apply_aec_to_audio(data, 16000, frame_ms=30) == data


def test_simple_aec_reduces_echo(monkeypatch):
    np = pytest.importorskip("numpy")
    monkeypatch.setenv("JARVIS_AEC_BACKEND", "simple")
    vad_module.reset_playback_reference()

    frame_ms = 20
    frame_samples = int(16000 * frame_ms / 1000)
    near = (np.ones(frame_samples, dtype=np.int16) * 1000).tobytes()
    assert vad_module.push_playback_reference(near, 16000) is True

    out = vad_module.apply_aec_to_audio(near, 16000, frame_ms=frame_ms)
    in_energy = float(abs(np.frombuffer(near, dtype=np.int16)).mean())
    out_energy = float(abs(np.frombuffer(out, dtype=np.int16)).mean())
    assert out_energy < in_energy
