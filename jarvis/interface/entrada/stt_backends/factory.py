"""
STT Backend Factory.

Automatic backend selection with fallback chain.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

from jarvis.interface.entrada.stt_backends.base import STTBackend


def detect_gpu_available() -> bool:
    """
    Detect if NVIDIA GPU is available.

    Returns:
        True if nvidia-smi reports available GPU
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        return result.returncode == 0 and "GPU" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def select_backend_name(device: str = "cpu") -> str:
    """
    Auto-select best backend based on environment.

    Selection priority:
    1. JARVIS_STT_BACKEND env var (explicit override)
    2. Auto-detect:
       - GPU available → "ctranslate2" (faster-whisper GPU)
       - CPU → "whisper_cpp" (CPU-optimized)
    3. Fallback: "faster_whisper"

    Args:
        device: Device hint ("cpu", "cuda", "auto")

    Returns:
        Backend name string
    """
    # Priority 1: Explicit override
    env_backend = os.environ.get("JARVIS_STT_BACKEND", "").strip().lower()
    if env_backend:
        return env_backend

    # Priority 2: Auto-detect
    if device == "cuda" or (device == "auto" and detect_gpu_available()):
        # GPU available: use ctranslate2 (faster-whisper GPU backend)
        return "ctranslate2"

    # CPU: prefer whisper_cpp if available
    # Check if whisper_cpp is importable
    try:
        import whispercpp  # noqa: F401

        return "whisper_cpp"
    except ImportError:
        pass

    # Priority 3: Fallback to faster_whisper
    return "faster_whisper"


def create_backend(
    model_size: str,
    device: str = "cpu",
    compute_type: str = "int8",
    cpu_threads: int = 0,
    num_workers: int = 1,
    backend_name: str | None = None,
    **kwargs: Any,
) -> STTBackend:
    """
    Create STT backend with automatic selection and fallback.

    Fallback chain:
    - whisper_cpp → faster_whisper
    - ctranslate2 → faster_whisper → whisper_cpp

    Args:
        model_size: Whisper model size ("tiny", "small", etc.)
        device: Device to use ("cpu", "cuda", "auto")
        compute_type: Compute type ("int8", "int8_float16", etc.)
        cpu_threads: Number of CPU threads (0 = auto)
        num_workers: Number of parallel workers
        backend_name: Explicit backend name or None for auto-select
        **kwargs: Additional backend-specific arguments

    Returns:
        STTBackend instance

    Raises:
        ImportError: If no backend is available
    """
    # Auto-select backend if not specified
    if backend_name is None:
        backend_name = select_backend_name(device)

    # Normalize backend name
    backend_name = backend_name.lower().strip()

    # Map ctranslate2 to faster_whisper (same implementation)
    if backend_name == "ctranslate2":
        backend_name = "faster_whisper"

    # Try requested backend
    if backend_name == "whisper_cpp":
        try:
            from jarvis.interface.entrada.stt_backends import whisper_cpp

            if whisper_cpp.is_available():
                return whisper_cpp.create_backend(
                    model_size=model_size,
                    device=device,
                    cpu_threads=cpu_threads,
                    **kwargs,
                )
        except ImportError:
            pass

        # Fallback: whisper_cpp → faster_whisper
        backend_name = "faster_whisper"

    if backend_name == "faster_whisper":
        try:
            from jarvis.interface.entrada.stt_backends import faster_whisper

            if faster_whisper.is_available():
                return faster_whisper.create_backend(
                    model_size=model_size,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=cpu_threads,
                    num_workers=num_workers,
                    **kwargs,
                )
        except ImportError:
            pass

        # Fallback: faster_whisper → whisper_cpp
        try:
            from jarvis.interface.entrada.stt_backends import whisper_cpp

            if whisper_cpp.is_available():
                return whisper_cpp.create_backend(
                    model_size=model_size,
                    device=device,
                    cpu_threads=cpu_threads,
                    **kwargs,
                )
        except ImportError:
            pass

    # No backend available
    raise ImportError(
        f"STT backend '{backend_name}' not available. "
        "Install faster-whisper or whispercpp:\n"
        "  pip install faster-whisper\n"
        "  pip install whispercpp"
    )
