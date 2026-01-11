from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

try:
    import numpy as np  # type: ignore
except (ImportError, OSError):
    np = None

try:
    import torch  # type: ignore
except (ImportError, OSError):
    torch = None


def is_available() -> bool:
    return np is not None and torch is not None


def has_cached_model() -> bool:
    if torch is None:
        return False
    try:
        hub_dir = Path(torch.hub.get_dir())
    except Exception:
        return False
    if not hub_dir.exists():
        return False
    for entry in hub_dir.iterdir():
        if entry.is_dir() and entry.name.startswith("snakers4_silero-vad"):
            return True
    return False


def _extract_get_speech_timestamps(utils: Any) -> Callable[..., Any] | None:
    if isinstance(utils, dict):
        func = utils.get("get_speech_timestamps")
        if callable(func):
            return func
    if isinstance(utils, (list, tuple)):
        for item in utils:
            if callable(item) and getattr(item, "__name__", "") == "get_speech_timestamps":
                return item
    if callable(utils) and getattr(utils, "__name__", "") == "get_speech_timestamps":
        return utils
    return None


class SileroDeactivityDetector:
    def __init__(
        self,
        model: Any,
        get_speech_timestamps: Callable[..., Any],
        sensitivity: float,
        *,
        debug: bool = False,
    ) -> None:
        self._model = model
        self._get_speech_timestamps = get_speech_timestamps
        self._sensitivity = max(0.0, min(1.0, sensitivity))
        self._debug = debug

    def trim_on_deactivity(
        self,
        audio_i16: bytes,
        sample_rate: int,
        *,
        post_roll_ms: int = 0,
    ) -> tuple[bytes, bool | None]:
        if np is None or torch is None:
            return audio_i16, None
        if not audio_i16:
            return b"", False
        if sample_rate != 16000:
            if self._debug:
                print("[silero] sample_rate != 16000; ignorando deactivity")
            return audio_i16, None

        samples = np.frombuffer(audio_i16, dtype=np.int16).astype(np.float32)
        if samples.size == 0:
            return b"", False

        if hasattr(self._model, "reset_states"):
            try:
                self._model.reset_states()
            except Exception:
                pass

        audio_tensor = torch.from_numpy(samples / 32768.0)
        threshold = max(0.0, min(1.0, 1.0 - self._sensitivity))
        try:
            timestamps = self._get_speech_timestamps(
                audio_tensor, self._model, sampling_rate=sample_rate, threshold=threshold
            )
        except TypeError:
            try:
                timestamps = self._get_speech_timestamps(
                    audio_tensor, self._model, sampling_rate=sample_rate
                )
            except Exception as exc:
                if self._debug:
                    print(f"[silero] get_speech_timestamps falhou: {exc}")
                return audio_i16, None
        except Exception as exc:
            if self._debug:
                print(f"[silero] get_speech_timestamps falhou: {exc}")
            return audio_i16, None

        if not timestamps:
            return b"", False

        last = timestamps[-1]
        if isinstance(last, dict):
            end_idx = int(last.get("end", 0))
        elif isinstance(last, (list, tuple)) and len(last) >= 2:
            end_idx = int(last[1])
        else:
            end_idx = 0

        if end_idx <= 0:
            return b"", False

        pad = max(0, int((post_roll_ms / 1000.0) * sample_rate))
        end_idx = min(samples.size, end_idx + pad)
        if end_idx <= 0:
            return b"", False

        trimmed = samples[:end_idx].astype(np.int16).tobytes()
        return trimmed, True


def build_silero_deactivity_detector(
    *,
    sensitivity: float = 0.6,
    use_onnx: bool = False,
    auto_download: bool = False,
    debug: bool = False,
) -> SileroDeactivityDetector | None:
    if not is_available():
        return None
    if not auto_download and not has_cached_model():
        if debug:
            print("[silero] modelo nao encontrado no cache; auto_download=0")
        return None
    try:
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True,
            onnx=use_onnx,
        )
    except Exception as exc:
        if debug:
            print(f"[silero] falha ao carregar modelo: {exc}")
        return None
    get_speech_timestamps = _extract_get_speech_timestamps(utils)
    if get_speech_timestamps is None:
        if debug:
            print("[silero] utils sem get_speech_timestamps")
        return None
    return SileroDeactivityDetector(
        model,
        get_speech_timestamps,
        sensitivity,
        debug=debug,
    )
