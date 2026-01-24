"""
STT Backend Abstraction Layer.

Provides pluggable STT backends for different inference engines.
"""

from jarvis.interface.entrada.stt_backends.base import (
    STTBackend,
    TranscriptionInfo,
    TranscriptionSegment,
)
from jarvis.interface.entrada.stt_backends.factory import create_backend

__all__ = [
    "STTBackend",
    "TranscriptionSegment",
    "TranscriptionInfo",
    "create_backend",
]
