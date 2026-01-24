"""
Whisper.cpp STT Backend.

Adapter for whispercpp (CPU-optimized inference with GGML/GGUF models).
"""

from __future__ import annotations

import os
import tempfile
import wave
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
    import whispercpp  # type: ignore
except ImportError:
    whispercpp = None


def is_available() -> bool:
    """Check if whispercpp backend is available."""
    return whispercpp is not None


class WhisperCppBackend(STTBackendBase):
    """
    STT backend using whisper.cpp (GGML/GGUF quantized models).

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
        if whispercpp is None:
            raise ImportError(
                "whispercpp not available. Install with: pip install whispercpp"
            )

        self._model_size = model_size
        self._device = device
        self._cpu_threads = cpu_threads if cpu_threads > 0 else os.cpu_count() or 4

        # Resolve model path
        model_path = self._resolve_model_path(model_size)

        # Initialize whispercpp model
        self._model = whispercpp.Whisper.from_pretrained(
            model_path,
            n_threads=self._cpu_threads,
        )

    def _resolve_model_path(self, model_size: str) -> str:
        """
        Resolve path to GGUF model file.

        Search order:
        1. ~/.cache/whisper/ggml-{model_size}-q5_k_s.bin
        2. ~/.cache/whisper/ggml-{model_size}.bin
        3. Auto-download via whispercpp

        Args:
            model_size: Model size string

        Returns:
            Path to model file
        """
        cache_dir = Path.home() / ".cache" / "whisper"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Try Q5_K_S quantized model (best speed/quality)
        q5_path = cache_dir / f"ggml-{model_size}-q5_k_s.bin"
        if q5_path.exists():
            return str(q5_path)

        # Try base quantized model
        base_path = cache_dir / f"ggml-{model_size}.bin"
        if base_path.exists():
            return str(base_path)

        # Fallback: use model name, let whispercpp handle download
        # whispercpp will download to its default cache
        return model_size

    def _array_to_wav(self, audio: Any, sample_rate: int = 16000) -> str:
        """
        Convert numpy array to temporary WAV file.

        Args:
            audio: Float32 audio samples in [-1, 1]
            sample_rate: Sample rate in Hz

        Returns:
            Path to temporary WAV file
        """
        if np is None:
            raise ImportError("numpy required for audio conversion")

        # Convert float32 to int16
        if audio.dtype != np.int16:
            audio_int16 = (audio * 32767.0).astype(np.int16)
        else:
            audio_int16 = audio

        # Create temporary WAV file
        fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="whisper_cpp_")
        os.close(fd)

        # Write WAV
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())

        return wav_path

    def _parse_result(self, result: Any) -> Iterator[TranscriptionSegment]:
        """
        Parse whispercpp result into TranscriptionSegment.

        Args:
            result: Raw result from whispercpp

        Yields:
            TranscriptionSegment instances
        """
        # whispercpp returns a list of dicts with "text", "start", "end"
        # or a single string
        if isinstance(result, str):
            # Single string result
            yield TranscriptionSegment(text=result.strip())
            return

        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict):
                    yield TranscriptionSegment(
                        text=item.get("text", "").strip(),
                        start=item.get("start", 0.0),
                        end=item.get("end", 0.0),
                    )
                elif isinstance(item, str):
                    yield TranscriptionSegment(text=item.strip())
                elif hasattr(item, "text"):
                    yield TranscriptionSegment(
                        text=item.text.strip(),
                        start=getattr(item, "start", 0.0),
                        end=getattr(item, "end", 0.0),
                    )
            return

        # Fallback: try to extract text attribute
        if hasattr(result, "text"):
            yield TranscriptionSegment(text=result.text.strip())
        else:
            yield TranscriptionSegment(text=str(result).strip())

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
            beam_size: Beam search size (may not be supported)
            temperature: Sampling temperature (may not be supported)
            **kwargs: Additional transcription options

        Returns:
            Tuple of (segments_iterator, transcription_info)
        """
        # Convert numpy array to WAV if needed
        temp_wav = None
        if np is not None and hasattr(audio, "dtype"):
            audio = self._array_to_samples(audio)
            temp_wav = self._array_to_wav(audio)
            audio_path = temp_wav
        else:
            audio_path = audio

        try:
            # Prepare transcription params
            transcribe_params = {}
            if language:
                transcribe_params["language"] = language

            # Call whispercpp transcribe
            # Note: whispercpp API may vary, adjust as needed
            result = self._model.transcribe(audio_path, **transcribe_params)

            # Parse result into segments
            segments = list(self._parse_result(result))

            # Create info (limited metadata from whisper.cpp)
            info = TranscriptionInfo(
                language=language or "en",
                language_probability=1.0 if language else 0.0,
                duration=segments[-1].end if segments else 0.0,
            )

            return iter(segments), info

        finally:
            # Clean up temporary WAV
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.unlink(temp_wav)
                except Exception:
                    pass

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
