"""
Detector leve de emocao/tonalidade para audio de voz.

Backend padrao: heuristicas simples (CPU-first).
Backend opcional: SpeechBrain (quando instalado).
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, TYPE_CHECKING, TypeAlias

try:
    import numpy as np  # type: ignore
except Exception:
    np = None

if TYPE_CHECKING:
    import numpy as _np

    NDArrayFloat: TypeAlias = _np.ndarray
else:
    NDArrayFloat: TypeAlias = Any


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


def _env_str(key: str, default: str) -> str:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.strip()


def _log_op(event: str, payload: dict[str, Any]) -> None:
    if not _env_bool("JARVIS_EMOTION_LOG", False):
        return
    log_path = Path("/home/u/Documentos/Jarvis/storage/logs/log_ops.jsonl")
    record = {
        "event": event,
        "ts_ms": int(time.time() * 1000),
        "payload": payload,
    }
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    except Exception:
        pass


def _heuristic_emotion(samples: NDArrayFloat, sample_rate: int) -> dict[str, Any]:
    if np is None:
        return {"label": "neutro", "confidence": 0.0, "backend": "heuristic"}
    if samples.size == 0:
        return {"label": "neutro", "confidence": 0.0, "backend": "heuristic"}
    assert np is not None
    samples = samples.astype(np.float32, copy=False)
    samples /= 32768.0
    rms = float(np.sqrt(np.mean(samples**2)) + 1e-8)
    zcr = float(np.mean(np.abs(np.diff(np.sign(samples))))) if samples.size > 1 else 0.0

    pitch_hz = 0.0
    if sample_rate > 0 and samples.size > sample_rate // 4:
        window = samples[: min(samples.size, sample_rate)]
        corr = np.correlate(window, window, mode="full")[len(window) - 1 :]
        corr[: int(sample_rate / 300)] = 0
        peak = int(np.argmax(corr))
        if peak > 0:
            pitch_hz = float(sample_rate / peak)

    if rms < 0.02:
        label = "neutro"
        confidence = 0.5
    elif rms < 0.04 and pitch_hz < 140:
        label = "triste"
        confidence = 0.55
    elif rms > 0.08 and zcr > 0.1:
        label = "agitado"
        confidence = 0.6
    elif pitch_hz > 180 and rms > 0.04:
        label = "feliz"
        confidence = 0.55
    else:
        label = "calmo"
        confidence = 0.5

    return {
        "label": label,
        "confidence": confidence,
        "backend": "heuristic",
        "metrics": {"rms": rms, "zcr": zcr, "pitch_hz": pitch_hz},
    }


def detect_emotion(audio_bytes: bytes, sample_rate: int) -> dict[str, Any] | None:
    if not _env_bool("JARVIS_EMOTION_ENABLED", True):
        return None
    if np is None or not audio_bytes:
        return None
    assert np is not None
    min_ms = max(0.0, _env_float("JARVIS_EMOTION_MIN_MS", 800.0))
    if sample_rate > 0 and (len(audio_bytes) / 2.0) < (sample_rate * min_ms / 1000.0):
        return None
    samples = np.frombuffer(audio_bytes, dtype=np.int16)
    backend = _env_str("JARVIS_EMOTION_BACKEND", "heuristic").lower()
    if backend != "heuristic":
        return None
    result = _heuristic_emotion(samples, sample_rate)
    _log_op("emotion_detected", result)
    return result


def detect_emotion_async(
    audio_bytes: bytes,
    sample_rate: int,
    callback,
) -> None:
    def _runner() -> None:
        result = detect_emotion(audio_bytes, sample_rate)
        if result is not None:
            try:
                callback(result)
            except Exception:
                return

    threading.Thread(target=_runner, daemon=True).start()
