"""API publica estavel para adapters de entrada da interface."""

from . import (
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
