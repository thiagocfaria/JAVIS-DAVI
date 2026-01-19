"""Compat: alias para o modulo VAD na nova interface."""

from __future__ import annotations

import sys as _sys
from importlib import import_module as _import_module
from typing import Any as _Any

_mod = _import_module("jarvis.interface.entrada.vad")

VADError = getattr(_mod, "VADError")
VoiceActivityDetector = getattr(_mod, "VoiceActivityDetector")
StreamingVAD = getattr(_mod, "StreamingVAD")
resolve_vad_aggressiveness = getattr(_mod, "resolve_vad_aggressiveness")
check_vad_available = getattr(_mod, "check_vad_available")
apply_aec_to_audio = getattr(_mod, "apply_aec_to_audio")
push_playback_reference = getattr(_mod, "push_playback_reference")
reset_playback_reference = getattr(_mod, "reset_playback_reference")

__all__ = [
    "VADError",
    "VoiceActivityDetector",
    "StreamingVAD",
    "resolve_vad_aggressiveness",
    "check_vad_available",
    "apply_aec_to_audio",
    "push_playback_reference",
    "reset_playback_reference",
]


def __getattr__(name: str) -> _Any:
    return getattr(_mod, name)


_sys.modules[__name__] = _mod
