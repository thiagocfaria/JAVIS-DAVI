"""
Speaker verification (optional).

Uses Resemblyzer to create a voiceprint and compare via cosine similarity.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, TYPE_CHECKING

try:
    import numpy as np  # type: ignore
except Exception:
    np = None

if TYPE_CHECKING:
    from resemblyzer import VoiceEncoder as ResemblyzerVoiceEncoder
else:
    ResemblyzerVoiceEncoder = Any

try:
    from resemblyzer import VoiceEncoder  # type: ignore
except Exception:
    VoiceEncoder = None

try:
    from scipy.signal import resample_poly  # type: ignore
except Exception:
    resample_poly = None

try:
    from cryptography.fernet import Fernet  # type: ignore
except Exception:
    Fernet = None


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


def _voiceprint_passphrase() -> str:
    return os.environ.get("JARVIS_SPK_VOICEPRINT_PASSPHRASE", "").strip()


def _build_fernet(passphrase: str):
    if not passphrase or Fernet is None:
        return None
    key = hashlib.sha256(passphrase.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def _encrypt_payload(
    payload: Mapping[str, object], passphrase: str
) -> dict[str, object] | None:
    fernet = _build_fernet(passphrase)
    if fernet is None:
        return None
    try:
        raw = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        token = fernet.encrypt(raw)
        return {"encrypted": True, "ciphertext": token.decode("utf-8")}
    except Exception as exc:
        _debug(f"encrypt failed: {exc}")
        return None


def _decrypt_payload(
    data: dict[str, object], passphrase: str
) -> dict[str, object] | None:
    fernet = _build_fernet(passphrase)
    if fernet is None:
        return None
    ciphertext = data.get("ciphertext")
    if not isinstance(ciphertext, str) or not ciphertext:
        return None
    try:
        raw = fernet.decrypt(ciphertext.encode("utf-8"))
        parsed = json.loads(raw.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else None
    except Exception as exc:
        _debug(f"decrypt failed: {exc}")
        return None


_encoder: Any | None = None
_voiceprint_cache: list[float] | None = None
_voiceprint_mtime: float | None = None
_TARGET_SAMPLE_RATE = 16000


def _get_encoder() -> Any:
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


def _resample_float(audio: Any, source_sr: int, target_sr: int) -> Any:
    if source_sr == target_sr:
        return audio
    if resample_poly is None or np is None:
        _debug("resample unavailable; using original sample rate")
        return audio
    ratio = Fraction(target_sr, source_sr).limit_denominator(1000)
    try:
        resampled = resample_poly(audio, ratio.numerator, ratio.denominator)
        return resampled.astype(np.float32, copy=False)
    except Exception as exc:
        _debug(f"resample failed: {exc}")
        return audio


def _prepare_audio(audio_bytes: bytes, sample_rate: int) -> Any:
    wav = _pcm16_to_float(audio_bytes)
    if getattr(wav, "size", 0) == 0:
        return wav
    if sample_rate != _TARGET_SAMPLE_RATE:
        wav = _resample_float(wav, sample_rate, _TARGET_SAMPLE_RATE)
    return wav


def _cosine_similarity(a: Any, b: Any) -> float:
    if np is None:
        return 0.0
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _load_voiceprint() -> list[float] | None:
    global _voiceprint_cache, _voiceprint_mtime
    path = _voiceprint_path()
    if not path.exists():
        _voiceprint_cache = None
        _voiceprint_mtime = None
        return None
    mtime: float | None
    try:
        mtime = path.stat().st_mtime
    except Exception:
        mtime = None
    if _voiceprint_cache is not None and _voiceprint_mtime == mtime:
        return _voiceprint_cache
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(data, dict) and data.get("encrypted"):
        passphrase = _voiceprint_passphrase()
        if not passphrase:
            _debug("voiceprint encrypted but passphrase missing")
            return None
        decrypted = _decrypt_payload(data, passphrase)
        if not decrypted:
            _debug("voiceprint decrypt failed")
            return None
        data = decrypted
    embedding = data.get("embedding") if isinstance(data, dict) else None
    if not isinstance(embedding, list) or not embedding:
        return None
    try:
        _voiceprint_cache = [float(x) for x in embedding]
        _voiceprint_mtime = mtime
        return _voiceprint_cache
    except Exception:
        return None


def has_voiceprint() -> bool:
    return _load_voiceprint() is not None


def voiceprint_path() -> Path:
    return _voiceprint_path()


def _save_voiceprint(embedding: list[float]) -> bool:
    global _voiceprint_cache, _voiceprint_mtime
    path = _voiceprint_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {"embedding": embedding}
    passphrase = _voiceprint_passphrase()
    if passphrase:
        encrypted = _encrypt_payload(payload, passphrase)
        if encrypted is None:
            _debug("voiceprint encryption unavailable; not saving")
            return False
        payload = encrypted
    path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    _voiceprint_cache = embedding
    try:
        _voiceprint_mtime = path.stat().st_mtime
    except Exception:
        _voiceprint_mtime = None
    return True


def load_voiceprint() -> list[float] | None:
    return _load_voiceprint()


def enroll_speaker(
    audio_bytes: bytes, sample_rate: int = _TARGET_SAMPLE_RATE
) -> list[float] | None:
    """
    Create and persist a voiceprint from audio bytes.

    Returns the embedding list or None if unavailable.
    """
    if not is_available():
        _debug("resemblyzer unavailable; enrollment skipped")
        return None
    try:
        wav = _prepare_audio(audio_bytes, sample_rate)
        if wav.size == 0:
            return None
        encoder = _get_encoder()
        embedding = encoder.embed_utterance(wav)
        embedding_list = [float(x) for x in embedding.tolist()]
        if not _save_voiceprint(embedding_list):
            return None
        return embedding_list
    except Exception as exc:
        _debug(f"enroll failed: {exc}")
        return None


def verify_speaker(
    audio_bytes: bytes, sample_rate: int = _TARGET_SAMPLE_RATE
) -> tuple[float, bool]:
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
    min_ms = _env_float("JARVIS_SPK_MIN_AUDIO_MS", 1000.0)
    if min_ms > 0 and sample_rate > 0:
        duration_ms = (len(audio_bytes) / 2.0) / float(sample_rate) * 1000.0
        if duration_ms < min_ms:
            _debug("audio curto; verificacao falhou (abaixo do minimo)")
            return 0.0, False
    try:
        wav = _prepare_audio(audio_bytes, sample_rate)
        if wav.size == 0:
            return 0.0, False
        encoder = _get_encoder()
        embedding = encoder.embed_utterance(wav)
        if np is None:
            _debug("numpy not available; verification skipped")
            return 1.0, True
        assert np is not None
        reference = np.array(voiceprint, dtype=np.float32)
        score = _cosine_similarity(embedding, reference)
        threshold = _env_float("JARVIS_SPK_THRESHOLD", 0.75)
        return score, score >= threshold
    except Exception as exc:
        _debug(f"verify failed: {exc}")
        return 0.0, False
