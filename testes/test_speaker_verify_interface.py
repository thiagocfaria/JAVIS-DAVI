from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

from jarvis.voz import speaker_verify as sv


def test_verify_speaker_disabled_returns_ok(monkeypatch):
    monkeypatch.setenv("JARVIS_SPK_VERIFY", "0")
    score, ok = sv.verify_speaker(b"\x00\x00")
    assert ok is True
    assert score == 1.0


def test_verify_speaker_enabled_without_voiceprint_fails(monkeypatch):
    monkeypatch.setenv("JARVIS_SPK_VERIFY", "1")
    monkeypatch.setattr(sv, "is_available", lambda: True)
    monkeypatch.setattr(sv, "_load_voiceprint", lambda: None)

    score, ok = sv.verify_speaker(b"\x00\x00")
    assert ok is False
    assert score == 0.0


def test_enroll_speaker_saves_voiceprint(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(sv, "is_available", lambda: True)

    class DummyWav:
        size = 1

    class DummyEmbedding:
        def tolist(self):
            return [0.1, 0.2]

    class DummyEncoder:
        def embed_utterance(self, wav):
            return DummyEmbedding()

    saved = {"embedding": None}

    monkeypatch.setattr(sv, "_pcm16_to_float", lambda audio: DummyWav())
    monkeypatch.setattr(sv, "_get_encoder", lambda: DummyEncoder())
    monkeypatch.setattr(sv, "_save_voiceprint", lambda emb: saved.__setitem__("embedding", emb))

    embedding = sv.enroll_speaker(b"\x00\x00")
    assert embedding == [0.1, 0.2]
    assert saved["embedding"] == [0.1, 0.2]


def test_verify_speaker_uses_threshold(monkeypatch):
    np = pytest.importorskip("numpy")

    monkeypatch.setenv("JARVIS_SPK_VERIFY", "1")
    monkeypatch.setenv("JARVIS_SPK_THRESHOLD", "0.75")
    monkeypatch.setattr(sv, "is_available", lambda: True)
    monkeypatch.setattr(sv, "_load_voiceprint", lambda: [0.1, 0.2])
    monkeypatch.setattr(sv, "_pcm16_to_float", lambda audio: types.SimpleNamespace(size=1))
    monkeypatch.setattr(sv, "_get_encoder", lambda: types.SimpleNamespace(embed_utterance=lambda wav: np.array([0.1, 0.2], dtype=np.float32)))
    monkeypatch.setattr(sv, "_cosine_similarity", lambda a, b: 0.8)
    monkeypatch.setattr(sv, "np", np)

    score, ok = sv.verify_speaker(b"\x00\x00")
    assert ok is True
    assert score == 0.8


def test_verify_speaker_resamples_when_sample_rate_diff(monkeypatch):
    monkeypatch.setenv("JARVIS_SPK_VERIFY", "1")
    monkeypatch.setenv("JARVIS_SPK_MIN_AUDIO_MS", "0")
    monkeypatch.setattr(sv, "is_available", lambda: True)
    monkeypatch.setattr(sv, "_load_voiceprint", lambda: [0.1, 0.2])

    dummy_wav = types.SimpleNamespace(size=1)
    monkeypatch.setattr(sv, "_pcm16_to_float", lambda audio: dummy_wav)

    called = {"args": None}

    def fake_resample(wav, source_sr, target_sr):
        called["args"] = (wav, source_sr, target_sr)
        return wav

    monkeypatch.setattr(sv, "_resample_float", fake_resample)
    monkeypatch.setattr(
        sv,
        "_get_encoder",
        lambda: types.SimpleNamespace(embed_utterance=lambda wav: "emb"),
    )
    monkeypatch.setattr(sv, "_cosine_similarity", lambda a, b: 0.9)
    monkeypatch.setattr(
        sv, "np", types.SimpleNamespace(array=lambda *args, **kwargs: "ref", float32="float32")
    )

    score, ok = sv.verify_speaker(b"\x00\x00", sample_rate=44100)
    assert called["args"] is not None
    assert called["args"][1] == 44100
    assert called["args"][2] == 16000
    assert ok is True
    assert score == 0.9


def test_verify_speaker_skips_short_audio(monkeypatch):
    monkeypatch.setenv("JARVIS_SPK_VERIFY", "1")
    monkeypatch.setenv("JARVIS_SPK_MIN_AUDIO_MS", "1000")
    monkeypatch.setattr(sv, "is_available", lambda: True)
    monkeypatch.setattr(sv, "_load_voiceprint", lambda: [0.1, 0.2])
    monkeypatch.setattr(sv, "_get_encoder", lambda: (_ for _ in ()).throw(RuntimeError("should not call")))

    score, ok = sv.verify_speaker(b"\x00\x00" * 100, sample_rate=16000)
    assert ok is True
    assert score == 1.0


def test_load_voiceprint_uses_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_CONFIG_DIR", str(tmp_path))
    path = tmp_path / "voiceprint.json"
    path.write_text(json.dumps({"embedding": [0.1, 0.2]}, ensure_ascii=True), encoding="utf-8")
    monkeypatch.setattr(sv, "_voiceprint_cache", None)
    monkeypatch.setattr(sv, "_voiceprint_mtime", None)

    original_read = Path.read_text
    calls = {"count": 0}

    def counted_read(self, *args, **kwargs):
        calls["count"] += 1
        return original_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counted_read)

    first = sv.load_voiceprint()
    second = sv.load_voiceprint()

    assert first == [0.1, 0.2]
    assert second == [0.1, 0.2]
    assert calls["count"] == 1
