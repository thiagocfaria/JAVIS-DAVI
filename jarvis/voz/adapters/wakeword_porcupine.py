from __future__ import annotations

import os
import sys
from array import array

from .base import SampleRate, validate_audio_i16

try:
    import pvporcupine  # type: ignore
except Exception:
    pvporcupine = None


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


def _clamp_sensitivity(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, value))


def is_available() -> bool:
    return pvporcupine is not None


class PorcupineWakeWordDetector:
    def __init__(self, porcupine) -> None:
        self._porcupine = porcupine
        self._frame_length = int(getattr(porcupine, "frame_length", 0))

    def detect(self, audio_i16: bytes, sample_rate: SampleRate) -> bool:
        error = validate_audio_i16(audio_i16, sample_rate)
        if error:
            return False
        if sample_rate != 16000:
            return False
        if self._frame_length <= 0:
            return False

        samples = array("h")
        samples.frombytes(audio_i16)
        if sys.byteorder != "little":
            samples.byteswap()

        limit = len(samples) - self._frame_length + 1
        if limit <= 0:
            return False
        for idx in range(0, limit, self._frame_length):
            frame = samples[idx : idx + self._frame_length]
            try:
                keyword_index = self._porcupine.process(frame)
            except Exception:
                return False
            if isinstance(keyword_index, int) and keyword_index >= 0:
                return True
        return False

    def close(self) -> None:
        try:
            self._porcupine.delete()
        except Exception:
            return


def build_porcupine_detector(
    wake_word: str,
    *,
    access_key: str | None = None,
    keyword_path: str | None = None,
    sensitivity: float | None = None,
    debug: bool = False,
) -> PorcupineWakeWordDetector | None:
    if pvporcupine is None:
        if debug:
            print("[wakeword] pvporcupine nao esta disponivel")
        return None

    access_key = access_key or _env_str("JARVIS_PORCUPINE_ACCESS_KEY")
    if not access_key:
        if debug:
            print("[wakeword] access key ausente para pvporcupine")
        return None

    keyword_path = keyword_path or _env_str("JARVIS_PORCUPINE_KEYWORD_PATH")
    sensitivity = _clamp_sensitivity(
        sensitivity if sensitivity is not None else _env_float("JARVIS_PORCUPINE_SENSITIVITY")
    )
    wake_word = (wake_word or "").strip() or "jarvis"

    kwargs: dict[str, object] = {"access_key": access_key}
    if keyword_path:
        kwargs["keyword_paths"] = [keyword_path]
    else:
        kwargs["keywords"] = [wake_word]
    if sensitivity is not None:
        kwargs["sensitivities"] = [sensitivity]

    try:
        porcupine = pvporcupine.create(**kwargs)
    except Exception as exc:
        if debug:
            print(f"[wakeword] falha ao iniciar porcupine: {exc}")
        return None

    return PorcupineWakeWordDetector(porcupine)
