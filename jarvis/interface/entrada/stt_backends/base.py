"""
STT Backend Base Classes and Protocol.

Defines the common interface for all STT backends.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, NamedTuple, Protocol, runtime_checkable

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]


class TranscriptionSegment(NamedTuple):
    """Single transcription segment from STT backend."""

    text: str
    start: float = 0.0
    end: float = 0.0
    id: int = 0
    seek: int = 0
    tokens: list[int] | None = None
    temperature: float = 0.0
    avg_logprob: float = 0.0
    compression_ratio: float = 0.0
    no_speech_prob: float = 0.0


class TranscriptionInfo(NamedTuple):
    """Metadata about the transcription."""

    language: str = "en"
    language_probability: float = 0.0
    duration: float = 0.0
    duration_after_vad: float = 0.0
    all_language_probs: list[tuple[str, float]] | None = None
    transcription_options: dict[str, Any] | None = None
    vad_options: dict[str, Any] | None = None


@runtime_checkable
class STTBackend(Protocol):
    """
    Protocol for STT backend implementations.

    All backends must implement this interface to be compatible
    with the STT service.
    """

    def transcribe(
        self,
        audio: Any,
        language: str | None = None,
        beam_size: int = 5,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> tuple[Iterator[TranscriptionSegment], TranscriptionInfo]:
        """
        Transcribe audio to text.

        Args:
            audio: Audio data as numpy array (float32) or path to WAV file
            language: Language code (e.g., "pt", "en") or None for auto-detect
            beam_size: Beam search size for decoding
            temperature: Sampling temperature
            **kwargs: Backend-specific options

        Returns:
            Tuple of (segments_iterator, transcription_info)
        """
        ...

    @property
    def backend_name(self) -> str:
        """
        Return backend identifier.

        Examples: "faster_whisper", "whisper_cpp", "ctranslate2"
        """
        ...

    @property
    def model_name(self) -> str:
        """
        Return model identifier.

        Examples: "tiny", "small", "base", "medium", "large-v3"
        """
        ...


class STTBackendBase:
    """
    Base class with common utilities for STT backends.

    Provides normalization helpers and common functionality.
    """

    def _normalize_segments(
        self, segments: Any
    ) -> Iterator[TranscriptionSegment]:
        """
        Normalize backend-specific segments to common format.

        Args:
            segments: Raw segments from backend

        Yields:
            TranscriptionSegment instances
        """
        for seg in segments:
            if isinstance(seg, TranscriptionSegment):
                yield seg
            elif hasattr(seg, "text"):
                # Convert object with attributes to TranscriptionSegment
                yield TranscriptionSegment(
                    text=seg.text,
                    start=getattr(seg, "start", 0.0),
                    end=getattr(seg, "end", 0.0),
                    id=getattr(seg, "id", 0),
                    seek=getattr(seg, "seek", 0),
                    tokens=getattr(seg, "tokens", None),
                    temperature=getattr(seg, "temperature", 0.0),
                    avg_logprob=getattr(seg, "avg_logprob", 0.0),
                    compression_ratio=getattr(seg, "compression_ratio", 0.0),
                    no_speech_prob=getattr(seg, "no_speech_prob", 0.0),
                )
            elif isinstance(seg, dict):
                # Convert dict to TranscriptionSegment
                yield TranscriptionSegment(
                    text=seg.get("text", ""),
                    start=seg.get("start", 0.0),
                    end=seg.get("end", 0.0),
                    id=seg.get("id", 0),
                    seek=seg.get("seek", 0),
                    tokens=seg.get("tokens"),
                    temperature=seg.get("temperature", 0.0),
                    avg_logprob=seg.get("avg_logprob", 0.0),
                    compression_ratio=seg.get("compression_ratio", 0.0),
                    no_speech_prob=seg.get("no_speech_prob", 0.0),
                )
            else:
                # Fallback: treat as string
                yield TranscriptionSegment(text=str(seg))

    def _normalize_info(self, info: Any) -> TranscriptionInfo:
        """
        Normalize backend-specific info to common format.

        Args:
            info: Raw transcription info from backend

        Returns:
            TranscriptionInfo instance
        """
        if isinstance(info, TranscriptionInfo):
            return info

        if hasattr(info, "language"):
            # Convert object with attributes
            return TranscriptionInfo(
                language=getattr(info, "language", "en"),
                language_probability=getattr(info, "language_probability", 0.0),
                duration=getattr(info, "duration", 0.0),
                duration_after_vad=getattr(info, "duration_after_vad", 0.0),
                all_language_probs=getattr(info, "all_language_probs", None),
                transcription_options=getattr(info, "transcription_options", None),
                vad_options=getattr(info, "vad_options", None),
            )

        if isinstance(info, dict):
            # Convert dict
            return TranscriptionInfo(
                language=info.get("language", "en"),
                language_probability=info.get("language_probability", 0.0),
                duration=info.get("duration", 0.0),
                duration_after_vad=info.get("duration_after_vad", 0.0),
                all_language_probs=info.get("all_language_probs"),
                transcription_options=info.get("transcription_options"),
                vad_options=info.get("vad_options"),
            )

        # Fallback: empty info
        return TranscriptionInfo()

    def _array_to_samples(self, audio: Any) -> Any:
        """
        Normalize audio array to float32 samples in [-1, 1].

        Args:
            audio: Audio array (any dtype)

        Returns:
            Float32 array in [-1, 1] range
        """
        if np is None:
            return audio

        if audio.dtype == np.float32:
            # Already float32, ensure range
            return np.clip(audio, -1.0, 1.0)

        if audio.dtype == np.int16:
            # Convert int16 to float32
            return (audio.astype(np.float32) / 32768.0).clip(-1.0, 1.0)

        if audio.dtype == np.int32:
            # Convert int32 to float32
            return (audio.astype(np.float32) / 2147483648.0).clip(-1.0, 1.0)

        # Fallback: assume already normalized
        return audio.astype(np.float32)
