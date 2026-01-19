"""Compat: alias para o modulo speaker_verify na nova interface."""

from __future__ import annotations

import sys as _sys
from importlib import import_module as _import_module
from typing import Any as _Any

_mod = _import_module("jarvis.interface.entrada.speaker_verify")

is_enabled = getattr(_mod, "is_enabled")
is_available = getattr(_mod, "is_available")
has_voiceprint = getattr(_mod, "has_voiceprint")
voiceprint_path = getattr(_mod, "voiceprint_path")
load_voiceprint = getattr(_mod, "load_voiceprint")
enroll_speaker = getattr(_mod, "enroll_speaker")
verify_speaker = getattr(_mod, "verify_speaker")
_save_voiceprint = getattr(_mod, "_save_voiceprint")

__all__ = [
    "is_enabled",
    "is_available",
    "has_voiceprint",
    "voiceprint_path",
    "load_voiceprint",
    "enroll_speaker",
    "verify_speaker",
    "_save_voiceprint",
]


def __getattr__(name: str) -> _Any:
    return getattr(_mod, name)


_sys.modules[__name__] = _mod
