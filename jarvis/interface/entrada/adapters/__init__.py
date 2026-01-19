"""Compat: reexporta adapters de voz para a nova interface."""

from jarvis.voz.adapters import (  # noqa: F401
    base,
    speaker_resemblyzer,
    stt_realtimestt,
    vad_silero,
    wakeword_openwakeword,
    wakeword_porcupine,
    wakeword_text,
)

__all__ = [
    "base",
    "speaker_resemblyzer",
    "stt_realtimestt",
    "vad_silero",
    "wakeword_openwakeword",
    "wakeword_porcupine",
    "wakeword_text",
]
