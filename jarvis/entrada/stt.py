"""Compat: alias para o modulo STT na nova interface."""

from __future__ import annotations

import sys as _sys
from typing import Any as _Any

from jarvis.interface.entrada import stt as _mod
from jarvis.interface.entrada.stt import (
    STTError,
    SpeechToText,
    apply_wake_word_filter,
    check_stt_deps,
    resample_audio_float,
)

# Constantes e helpers usados em scripts/testes
from jarvis.interface.audio.audio_utils import BYTES_PER_SAMPLE, SAMPLE_RATE, coerce_pcm_bytes

sd = _mod.sd

__all__ = [
    "SpeechToText",
    "STTError",
    "apply_wake_word_filter",
    "resample_audio_float",
    "check_stt_deps",
    "SAMPLE_RATE",
    "BYTES_PER_SAMPLE",
    "coerce_pcm_bytes",
    "sd",
]


def __getattr__(name: str) -> _Any:
    return getattr(_mod, name)


_sys.modules[__name__] = _mod
