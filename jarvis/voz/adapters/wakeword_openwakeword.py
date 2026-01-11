from __future__ import annotations

import os

from .base import SampleRate, validate_audio_i16

try:
    import numpy as np  # type: ignore
except Exception:
    np = None

try:
    from openwakeword.model import Model  # type: ignore
    import openwakeword  # type: ignore
except Exception:
    Model = None
    openwakeword = None


def _env_str(key: str) -> str | None:
    value = os.environ.get(key)
    if value is None or value == "":
        return None
    return value.strip()


def _env_float(key: str) -> float | None:
    value = os.environ.get(key)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _env_bool(key: str) -> bool:
    value = os.environ.get(key)
    if value is None or value == "":
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _clamp_sensitivity(value: float | None, default: float = 0.5) -> float:
    if value is None:
        return default
    return max(0.0, min(1.0, value))


def is_available() -> bool:
    return Model is not None and openwakeword is not None and np is not None


class OpenWakeWordDetector:
    def __init__(self, model, sensitivity: float) -> None:
        self._model = model
        self._sensitivity = sensitivity

    def detect(self, audio_i16: bytes, sample_rate: SampleRate) -> bool:
        error = validate_audio_i16(audio_i16, sample_rate)
        if error:
            return False
        if sample_rate != 16000 or np is None:
            return False
        samples = np.frombuffer(audio_i16, dtype=np.int16)
        if samples.size == 0:
            return False
        try:
            self._model.predict(samples)
        except Exception:
            return False
        prediction_buffer = getattr(self._model, "prediction_buffer", None)
        if not prediction_buffer:
            return False
        for scores in prediction_buffer.values():
            try:
                last_score = list(scores)[-1]
            except Exception:
                continue
            if isinstance(last_score, (int, float)) and last_score >= self._sensitivity:
                return True
        return False


def build_openwakeword_detector(
    wake_word: str,
    *,
    model_paths: str | None = None,
    inference_framework: str | None = None,
    sensitivity: float | None = None,
    auto_download: bool | None = None,
    debug: bool = False,
) -> OpenWakeWordDetector | None:
    if Model is None or openwakeword is None or np is None:
        if debug:
            print("[wakeword] openwakeword nao esta disponivel")
        return None

    model_paths = model_paths or _env_str("JARVIS_OPENWAKEWORD_MODEL_PATHS")
    inference_framework = (
        inference_framework
        or _env_str("JARVIS_OPENWAKEWORD_INFERENCE_FRAMEWORK")
        or "onnx"
    )
    sensitivity = _clamp_sensitivity(
        sensitivity if sensitivity is not None else _env_float("JARVIS_OPENWAKEWORD_SENSITIVITY")
    )
    if auto_download is None:
        auto_download = _env_bool("JARVIS_OPENWAKEWORD_AUTO_DOWNLOAD")

    if auto_download or model_paths:
        try:
            openwakeword.utils.download_models()
        except Exception as exc:
            if debug:
                print(f"[wakeword] falha ao baixar modelos openwakeword: {exc}")
            if not model_paths:
                return None

    try:
        if model_paths:
            paths = [p.strip() for p in model_paths.split(",") if p.strip()]
            model = Model(
                wakeword_models=paths,
                inference_framework=inference_framework,
            )
        else:
            model = Model(inference_framework=inference_framework)
    except Exception as exc:
        if debug:
            print(f"[wakeword] falha ao iniciar openwakeword: {exc}")
        return None

    if not getattr(model, "models", None):
        if debug:
            print("[wakeword] openwakeword sem modelos carregados")
        return None

    _ = wake_word  # wake_word define o modelo usado; serve apenas como referencia
    return OpenWakeWordDetector(model, sensitivity)
