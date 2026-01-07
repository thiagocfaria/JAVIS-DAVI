"""
Speaker verification (optional).

Uses Resemblyzer to create a voiceprint and compare via cosine similarity.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    import numpy as np  # type: ignore
    from resemblyzer import VoiceEncoder  # type: ignore
except Exception:
    np = None
    VoiceEncoder = None


def _env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(key: str, default: float) -> float:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _debug_enabled() -> bool:
    return _env_bool("JARVIS_DEBUG", False)


def _debug(message: str) -> None:
    if _debug_enabled():
        print(f"[speaker_verify] {message}")


def is_enabled() -> bool:
    return _env_bool("JARVIS_SPK_VERIFY", False)


def is_available() -> bool:
    return VoiceEncoder is not None and np is not None


def _config_dir() -> Path:
    base = os.environ.get("JARVIS_CONFIG_DIR")
    if base:
        return Path(base)
    return Path.home() / ".config" / "jarvis"


def _voiceprint_path() -> Path:
    return _config_dir() / "voiceprint.json"


_encoder: VoiceEncoder | None = None


def _get_encoder() -> VoiceEncoder:
    global _encoder
    if _encoder is None:
        if VoiceEncoder is None:
            raise RuntimeError("Resemblyzer not available")
        _encoder = VoiceEncoder()
    return _encoder


def _pcm16_to_float(audio_bytes: bytes) -> Any:
    if np is None:
        raise RuntimeError("numpy not available")
    samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return samples
    return samples / 32768.0


def _cosine_similarity(a: Any, b: Any) -> float:
    if np is None:
        return 0.0
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _load_voiceprint() -> list[float] | None:
    path = _voiceprint_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    embedding = data.get("embedding") if isinstance(data, dict) else None
    if not isinstance(embedding, list) or not embedding:
        return None
    try:
        return [float(x) for x in embedding]
    except Exception:
        return None


def has_voiceprint() -> bool:
    return _load_voiceprint() is not None


def voiceprint_path() -> Path:
    return _voiceprint_path()


def _save_voiceprint(embedding: list[float]) -> None:
    path = _voiceprint_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"embedding": embedding}
    path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")


def enroll_speaker(audio_bytes: bytes) -> list[float] | None:
    """
    Create and persist a voiceprint from audio bytes.

    Returns the embedding list or None if unavailable.
    """
    if not is_available():
        _debug("resemblyzer unavailable; enrollment skipped")
        return None
    try:
        wav = _pcm16_to_float(audio_bytes)
        if wav.size == 0:
            return None
        encoder = _get_encoder()
        embedding = encoder.embed_utterance(wav)
        embedding_list = [float(x) for x in embedding.tolist()]
        _save_voiceprint(embedding_list)
        return embedding_list
    except Exception as exc:
        _debug(f"enroll failed: {exc}")
        return None


def verify_speaker(audio_bytes: bytes) -> tuple[float, bool]:
    """
    Verify if the audio matches the enrolled speaker.

    Returns (score, ok).
    """
    if not is_enabled():
        return 1.0, True
    if not is_available():
        _debug("resemblyzer unavailable; verification skipped")
        return 1.0, True
    voiceprint = _load_voiceprint()
    if not voiceprint:
        _debug("no voiceprint found; verification failed")
        return 0.0, False
    try:
        wav = _pcm16_to_float(audio_bytes)
        if wav.size == 0:
            return 0.0, False
        encoder = _get_encoder()
        embedding = encoder.embed_utterance(wav)
        reference = np.array(voiceprint, dtype=np.float32)
        score = _cosine_similarity(embedding, reference)
        threshold = _env_float("JARVIS_SPK_THRESHOLD", 0.75)
        return score, score >= threshold
    except Exception as exc:
        _debug(f"verify failed: {exc}")
        return 0.0, False
