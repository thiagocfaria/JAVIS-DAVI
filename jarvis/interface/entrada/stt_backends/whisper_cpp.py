"""
Whisper.cpp STT Backend.

Adapter for pywhispercpp (CPU-optimized inference with GGML/GGUF models).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
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
    from pywhispercpp.model import Model as PyWhisperModel  # type: ignore
except ImportError:
    PyWhisperModel = None


def is_available() -> bool:
    """Check if pywhispercpp backend is available."""
    return PyWhisperModel is not None


class WhisperCppBackend(STTBackendBase):
    """
    STT backend using whisper.cpp via pywhispercpp.

    Optimized for CPU inference with 2-3x speedup over faster-whisper.
    """

    def __init__(
        self,
        model_size: str,
        device: str = "cpu",
        cpu_threads: int = 0,
        **kwargs: Any,
    ) -> None:
        """
        Initialize whisper.cpp backend.

        Args:
            model_size: Whisper model size ("tiny", "small", "base", etc.)
            device: Device to use (only "cpu" supported)
            cpu_threads: Number of CPU threads (0 = auto)
            **kwargs: Additional arguments
        """
        if PyWhisperModel is None:
            raise ImportError(
                "pywhispercpp not available. Install with: pip install pywhispercpp"
            )

        self._model_size = model_size
        self._device = device
        self._cpu_threads = cpu_threads if cpu_threads > 0 else os.cpu_count() or 4

        # Resolve models directory
        models_dir = self._resolve_models_dir()

        # Initialize pywhispercpp model
        self._model = PyWhisperModel(
            model=model_size,
            models_dir=models_dir,
            n_threads=self._cpu_threads,
            redirect_whispercpp_logs_to=False,
        )

    def _resolve_models_dir(self) -> str:
        """
        Resolve path to models directory.

        Returns:
            Path to models directory
        """
        cache_dir = Path.home() / ".cache" / "whisper"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return str(cache_dir)

    def _parse_result(self, segments: Any) -> Iterator[TranscriptionSegment]:
        """
        Parse pywhispercpp segments into TranscriptionSegment.

        Args:
            segments: List of Segment objects from pywhispercpp

        Yields:
            TranscriptionSegment instances
        """
        if not segments:
            return

        for seg in segments:
            # pywhispercpp Segment has: text, t0, t1
            text = getattr(seg, "text", str(seg)).strip()
            if not text:
                continue

            # t0/t1 are in milliseconds
            t0 = getattr(seg, "t0", 0) / 1000.0 if hasattr(seg, "t0") else 0.0
            t1 = getattr(seg, "t1", 0) / 1000.0 if hasattr(seg, "t1") else 0.0

            yield TranscriptionSegment(
                text=text,
                start=t0,
                end=t1,
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
        Transcribe audio using whisper.cpp.

        Args:
            audio: Audio data as numpy array (float32) or path to WAV file
            language: Language code (e.g., "pt", "en") or None for auto-detect
            beam_size: Beam search size
            temperature: Sampling temperature
            **kwargs: Additional transcription options

        Returns:
            Tuple of (segments_iterator, transcription_info)
        """
        # Prepare transcription parameters
        transcribe_kwargs: dict[str, Any] = {
            "n_processors": self._cpu_threads,
            "print_progress": False,
            "print_realtime": False,
        }

        # Add language if specified
        if language:
            transcribe_kwargs["language"] = language

        # Add decoding strategy: greedy for speed, beam_search for quality
        if beam_size > 1:
            transcribe_kwargs["beam_search"] = {"beam_size": beam_size, "patience": -1.0}
        else:
            # Use greedy decoding with best_of=1 for maximum speed
            transcribe_kwargs["greedy"] = {"best_of": 1}

        if temperature > 0:
            transcribe_kwargs["temperature"] = temperature

        # pywhispercpp.model.Model.transcribe accepts:
        # - str: path to audio file
        # - np.ndarray: float32 audio samples
        if isinstance(audio, str):
            # File path
            segments = self._model.transcribe(audio, **transcribe_kwargs)
        elif np is not None and hasattr(audio, "dtype"):
            # Numpy array - normalize to float32
            audio = self._array_to_samples(audio)
            segments = self._model.transcribe(audio, **transcribe_kwargs)
        else:
            raise ValueError(f"Unsupported audio type: {type(audio)}")

        # Parse result into segments list
        segments_list = list(self._parse_result(segments))

        # Create info
        info = TranscriptionInfo(
            language=language or "en",
            language_probability=1.0 if language else 0.0,
            duration=segments_list[-1].end if segments_list else 0.0,
        )

        return iter(segments_list), info

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "whisper_cpp"

    @property
    def model_name(self) -> str:
        """Return model identifier."""
        return self._model_size


def create_backend(
    model_size: str,
    device: str = "cpu",
    cpu_threads: int = 0,
    **kwargs: Any,
) -> WhisperCppBackend:
    """
    Factory function to create whisper.cpp backend.

    Args:
        model_size: Whisper model size
        device: Device to use (only "cpu" supported)
        cpu_threads: Number of CPU threads
        **kwargs: Additional arguments

    Returns:
        WhisperCppBackend instance
    """
    return WhisperCppBackend(
        model_size=model_size,
        device=device,
        cpu_threads=cpu_threads,
        **kwargs,
    )
