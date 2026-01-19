"""Compat: alias para o modulo audio_utils na nova interface."""

from __future__ import annotations

import sys as _sys
from importlib import import_module as _import_module
from typing import Any as _Any

_mod = _import_module("jarvis.interface.audio.audio_utils")

SAMPLE_RATE = getattr(_mod, "SAMPLE_RATE")
BYTES_PER_SAMPLE = getattr(_mod, "BYTES_PER_SAMPLE")
coerce_pcm_bytes = getattr(_mod, "coerce_pcm_bytes")

__all__ = ["SAMPLE_RATE", "BYTES_PER_SAMPLE", "coerce_pcm_bytes"]


def __getattr__(name: str) -> _Any:
    return getattr(_mod, name)


_sys.modules[__name__] = _mod
