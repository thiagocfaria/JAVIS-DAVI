from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class STTBackendCapabilities:
    backend_id: str
    supports_sync: bool
    supports_streaming: bool
    supports_partials: bool
    cpu_first: bool
    experimental: bool


class STTBackendContract(Protocol):
    def backend_id(self) -> str: ...

    def capabilities(self) -> STTBackendCapabilities: ...

    def estimate_memory_cost_bytes(self) -> int | None: ...

    def warmup(self) -> None: ...

    def transcribe_sync(
        self,
        audio_bytes: bytes,
        *,
        require_wake_word: bool | None,
        skip_speech_check: bool,
        on_partial: Callable[[str], None] | None,
    ) -> str: ...

    def transcribe_stream(
        self,
        *,
        max_seconds: int,
        on_partial: Callable[[str], None] | None,
    ) -> tuple[str, bytes] | None: ...

    def get_last_metrics(self) -> dict[str, float | int | str | None]: ...


class WhisperCPUBackend:
    def __init__(
        self,
        *,
        transcribe_fn: Callable[..., str],
        warmup_fn: Callable[[], None],
        model_size: str,
    ) -> None:
        self._transcribe_fn = transcribe_fn
        self._warmup_fn = warmup_fn
        self._model_size = model_size
        self._last_metrics: dict[str, float | int | str | None] = {}

    def backend_id(self) -> str:
        return "whisper_cpu"

    def capabilities(self) -> STTBackendCapabilities:
        return STTBackendCapabilities(
            backend_id=self.backend_id(),
            supports_sync=True,
            supports_streaming=False,
            supports_partials=True,
            cpu_first=True,
            experimental=False,
        )

    def estimate_memory_cost_bytes(self) -> int | None:
        # Heuristica para footprint do modelo em RAM (ordem de grandeza)
        table = {
            "tiny": 240 * 1024 * 1024,
            "tiny.en": 240 * 1024 * 1024,
            "base": 450 * 1024 * 1024,
            "small": 1100 * 1024 * 1024,
            "medium": 2800 * 1024 * 1024,
            "large": 5200 * 1024 * 1024,
            "large-v2": 5200 * 1024 * 1024,
            "large-v3": 6200 * 1024 * 1024,
        }
        return table.get((self._model_size or "").strip().lower())

    def warmup(self) -> None:
        self._warmup_fn()

    def transcribe_sync(
        self,
        audio_bytes: bytes,
        *,
        require_wake_word: bool | None,
        skip_speech_check: bool,
        on_partial: Callable[[str], None] | None,
    ) -> str:
        start = time.perf_counter()
        text = self._transcribe_fn(
            audio_bytes,
            require_wake_word=require_wake_word,
            skip_speech_check=skip_speech_check,
            on_partial=on_partial,
        )
        elapsed = (time.perf_counter() - start) * 1000.0
        self._last_metrics = {
            "backend": self.backend_id(),
            "endpoint_ms": None,
            "stt_ms": elapsed,
            "partials_enabled": bool(on_partial),
        }
        return text

    def transcribe_stream(
        self,
        *,
        max_seconds: int,
        on_partial: Callable[[str], None] | None,
    ) -> tuple[str, bytes] | None:
        return None

    def get_last_metrics(self) -> dict[str, float | int | str | None]:
        return dict(self._last_metrics)


class RealtimeSTTExperimentalBackend:
    def __init__(
        self,
        *,
        model_size: str,
        language: str | None,
        debug_enabled: bool,
    ) -> None:
        self._model_size = model_size
        self._language = language or ""
        self._debug_enabled = debug_enabled
        self._last_metrics: dict[str, float | int | str | None] = {}

    def backend_id(self) -> str:
        return "realtimestt_experimental"

    def capabilities(self) -> STTBackendCapabilities:
        return STTBackendCapabilities(
            backend_id=self.backend_id(),
            supports_sync=False,
            supports_streaming=True,
            supports_partials=True,
            cpu_first=False,
            experimental=True,
        )

    def estimate_memory_cost_bytes(self) -> int | None:
        return 320 * 1024 * 1024

    def warmup(self) -> None:
        # Warmup opcional para baixar variancia de primeira chamada
        self._last_metrics = {"backend": self.backend_id(), "warmed": True}

    def transcribe_sync(
        self,
        audio_bytes: bytes,
        *,
        require_wake_word: bool | None,
        skip_speech_check: bool,
        on_partial: Callable[[str], None] | None,
    ) -> str:
        return ""

    def transcribe_stream(
        self,
        *,
        max_seconds: int,
        on_partial: Callable[[str], None] | None,
    ) -> tuple[str, bytes] | None:
        from jarvis.interface.entrada.adapters import stt_realtimestt

        if not stt_realtimestt.is_available():
            return None

        start = time.perf_counter()
        recorder = stt_realtimestt.build_recorder(
            model=self._model_size,
            language=self._language,
            device="cpu",
            use_microphone=True,
            spinner=False,
            enable_realtime_transcription=bool(on_partial),
            use_main_model_for_realtime=True,
            realtime_model_type=self._model_size,
            init_realtime_after_seconds=0.0,
            on_realtime_transcription_update=on_partial,
            wake_words="",
            silero_sensitivity=0.0,
            silero_deactivity_detection=False,
            allowed_latency_limit=100000,
            debug_mode=self._debug_enabled,
        )
        try:
            text = str(recorder.text() or "")
            audio = getattr(recorder, "last_transcription_bytes", b"")
            if isinstance(audio, bytes):
                audio_bytes = audio
            elif isinstance(audio, (bytearray, memoryview)):
                audio_bytes = bytes(audio)
            else:
                audio_bytes = b""
        finally:
            for method in ("shutdown", "close", "abort", "stop"):
                if hasattr(recorder, method):
                    try:
                        getattr(recorder, method)()
                    except Exception:
                        pass
        elapsed = (time.perf_counter() - start) * 1000.0
        self._last_metrics = {
            "backend": self.backend_id(),
            "endpoint_ms": elapsed,
            "stt_ms": 0.0,
            "partials_enabled": bool(on_partial),
            "stream_max_seconds": max_seconds,
        }
        return text, audio_bytes

    def get_last_metrics(self) -> dict[str, float | int | str | None]:
        return dict(self._last_metrics)


def resolve_default_backend() -> str:
    configured = (os.environ.get("JARVIS_STT_BACKEND") or "").strip().lower()
    if configured in {"whisper_cpu", "cpu", "default", "whisper"}:
        return "whisper_cpu"
    if configured in {"realtimestt_experimental", "experimental", "realtime"}:
        return "realtimestt_experimental"
    return "whisper_cpu"
