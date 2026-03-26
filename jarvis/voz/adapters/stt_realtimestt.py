from __future__ import annotations

from pathlib import Path
import importlib
import sys
from typing import Any, Callable

from jarvis.interface.entrada.stt_backend import STTBackendCapabilities

_cached_module: Any | None = None
_cached_cls: type | None = None
_cached_error: str | None = None


def _load_module() -> Any | None:
    global _cached_module, _cached_error
    if _cached_module is not None:
        return _cached_module
    if _cached_error is not None:
        return None

    try:
        module = importlib.import_module("RealtimeSTT")
        _cached_module = module
        return module
    except Exception as exc:
        last_error: Exception | None = exc

    vendor_root = Path(__file__).resolve().parents[2] / "third_party" / "realtimestt"
    if (vendor_root / "RealtimeSTT").exists():
        sys.path.insert(0, str(vendor_root))
        try:
            module = importlib.import_module("RealtimeSTT")
            _cached_module = module
            return module
        except Exception as exc:
            last_error = exc
        finally:
            try:
                sys.path.remove(str(vendor_root))
            except ValueError:
                pass

    local_root = (
        Path(__file__).resolve().parents[2] / "REPOSITORIOS_CLONAR" / "realtimestt"
    )
    if (local_root / "RealtimeSTT").exists():
        sys.path.insert(0, str(local_root))
        try:
            module = importlib.import_module("RealtimeSTT")
            _cached_module = module
            return module
        except Exception as exc:
            last_error = exc
        finally:
            try:
                sys.path.remove(str(local_root))
            except ValueError:
                pass

    _cached_error = str(last_error) if last_error else "RealtimeSTT nao disponivel"
    return None


def get_recorder_class() -> type | None:
    global _cached_cls
    if _cached_cls is not None:
        return _cached_cls
    module = _load_module()
    if module is None:
        return None
    recorder_cls = getattr(module, "AudioToTextRecorder", None)
    if isinstance(recorder_cls, type):
        _cached_cls = recorder_cls
        return recorder_cls
    _cached_error = "AudioToTextRecorder nao encontrado"
    return None


def is_available() -> bool:
    return get_recorder_class() is not None


def last_error() -> str | None:
    return _cached_error


def build_recorder(**kwargs: Any) -> Any:
    recorder_cls = get_recorder_class()
    if recorder_cls is None:
        raise RuntimeError(_cached_error or "RealtimeSTT nao disponivel")
    return recorder_cls(**kwargs)


def set_partial_callback(recorder: Any, callback: Callable[[str], None] | None) -> None:
    if recorder is None:
        return
    if hasattr(recorder, "on_realtime_transcription_update"):
        try:
            recorder.on_realtime_transcription_update = callback
        except Exception:
            return


def capabilities() -> STTBackendCapabilities:
    return STTBackendCapabilities(
        backend_id="realtimestt_experimental",
        supports_sync=False,
        supports_streaming=True,
        supports_partials=True,
        cpu_first=False,
        experimental=True,
    )


def estimate_memory_cost_bytes() -> int:
    return 320 * 1024 * 1024


def warmup() -> bool:
    """Disponibilidade simples para uniformizar contrato de backend."""
    return is_available()
