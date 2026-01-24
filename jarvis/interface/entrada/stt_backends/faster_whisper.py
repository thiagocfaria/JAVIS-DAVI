"""
Faster-Whisper STT Backend.

Adapter for the faster-whisper library (CTranslate2 backend).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]

from jarvis.interface.entrada.stt_backends.base import (
    STTBackendBase,
    TranscriptionInfo,
    TranscriptionSegment,
)

try:
    from faster_whisper import WhisperModel  # type: ignore
except ImportError:
    WhisperModel = None


def is_available() -> bool:
    """Check if faster-whisper backend is available."""
    return WhisperModel is not None


class FasterWhisperBackend(STTBackendBase):
    """
    STT backend using faster-whisper (CTranslate2).

    This is the default backend and provides good speed/quality balance
    on both CPU and GPU.
    """

    def __init__(
        self,
        model_size: str,
        device: str = "cpu",
        compute_type: str = "int8",
        cpu_threads: int = 0,
        num_workers: int = 1,
        **kwargs: Any,
    ) -> None:
        """
        Initialize faster-whisper backend.

        Args:
            model_size: Whisper model size ("tiny", "small", "base", etc.)
            device: Device to use ("cpu", "cuda", "auto")
            compute_type: Compute type ("int8", "int8_float16", "float16", etc.)
            cpu_threads: Number of CPU threads (0 = auto)
            num_workers: Number of parallel workers
            **kwargs: Additional arguments passed to WhisperModel
        """
        if WhisperModel is None:
            raise ImportError(
                "faster-whisper not available. Install with: pip install faster-whisper"
            )

        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type

        self._model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_threads,
            num_workers=num_workers,
            **kwargs,
        )

    def transcribe(
        self,
        audio: Any,
        language: str | None = None,
        beam_size: int = 5,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> tuple[Iterator[TranscriptionSegment], TranscriptionInfo]:
        """
        Transcribe audio using faster-whisper.

        Args:
            audio: Audio data as numpy array (float32) or path to WAV file
            language: Language code (e.g., "pt", "en") or None for auto-detect
            beam_size: Beam search size
            temperature: Sampling temperature
            **kwargs: Additional transcription options

        Returns:
            Tuple of (segments_iterator, transcription_info)
        """
        # Normalize audio to float32 if needed
        if np is not None and hasattr(audio, "dtype"):
            audio = self._array_to_samples(audio)

        # Call faster-whisper transcribe
        segments, info = self._model.transcribe(
            audio,
            language=language,
            beam_size=beam_size,
            temperature=temperature,
            **kwargs,
        )

        # Normalize outputs
        normalized_segments = self._normalize_segments(segments)
        normalized_info = self._normalize_info(info)

        return normalized_segments, normalized_info

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "faster_whisper"

    @property
    def model_name(self) -> str:
        """Return model identifier."""
        return self._model_size


def create_backend(
    model_size: str,
    device: str = "cpu",
    compute_type: str = "int8",
    cpu_threads: int = 0,
    num_workers: int = 1,
    **kwargs: Any,
) -> FasterWhisperBackend:
    """
    Factory function to create faster-whisper backend.

    Args:
        model_size: Whisper model size
        device: Device to use
        compute_type: Compute type
        cpu_threads: Number of CPU threads
        num_workers: Number of parallel workers
        **kwargs: Additional arguments

    Returns:
        FasterWhisperBackend instance
    """
    return FasterWhisperBackend(
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        cpu_threads=cpu_threads,
        num_workers=num_workers,
        **kwargs,
    )
