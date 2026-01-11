"""
Speech-to-Text module (local only).

Uses faster-whisper locally, with optional VAD and wake word filtering.
"""

from __future__ import annotations

import os
import re
import tempfile
import time
import wave
from array import array
from fractions import Fraction
from typing import Any, Callable, Literal, overload

from ..cerebro.config import Config
from .audio_utils import BYTES_PER_SAMPLE, SAMPLE_RATE, coerce_pcm_bytes

try:
    import numpy as np  # type: ignore
except (ImportError, OSError):
    np = None

sd = None


def _ensure_sounddevice() -> Any:
    global sd
    if sd is not None:
        return sd
    try:
        import sounddevice as _sd  # type: ignore
    except (ImportError, OSError):
        sd = None
        return None
    sd = _sd
    return sd

try:
    from scipy.signal import resample_poly  # type: ignore
except Exception:
    resample_poly = None

try:
    from faster_whisper import WhisperModel  # type: ignore
except ImportError:
    WhisperModel = None

try:
    from ..voz.vad import (
        StreamingVAD,
        VoiceActivityDetector,
        apply_aec_to_audio,
        check_vad_available,
        resolve_vad_aggressiveness,
    )
except Exception:
    # When import fails, assign None - mypy will treat as Any in type context
    StreamingVAD = None  # type: ignore[assignment, misc]
    VoiceActivityDetector = None  # type: ignore[assignment, misc]
    apply_aec_to_audio = None  # type: ignore[assignment, misc]
    resolve_vad_aggressiveness = None  # type: ignore[assignment, misc]

    def check_vad_available() -> bool:
        return False


try:
    from ..voz.vad import AudioRecorder as VADRecorder  # type: ignore
except Exception:
    VADRecorder = None

try:
    import jarvis_audio  # type: ignore
except Exception:
    jarvis_audio = None


class STTError(Exception):
    """Speech-to-Text error."""


def _env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int) -> int:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_float_optional(key: str) -> float | None:
    value = os.environ.get(key)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _env_int_optional(key: str) -> int | None:
    value = os.environ.get(key)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _env_str_optional(key: str) -> str | None:
    value = os.environ.get(key)
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned == "":
        return None
    if cleaned.lower() in {"none", "null"}:
        return None
    return cleaned


def _peak_amplitude(pcm_bytes: bytes) -> int:
    if np is not None:
        try:
            samples = np.frombuffer(pcm_bytes, dtype=np.int16)
            if samples.size == 0:
                return 0
            return int(np.max(np.abs(samples)))
        except Exception:
            return 0
    try:
        samples = array("h")
        samples.frombytes(pcm_bytes)
        if not samples:
            return 0
        return max(abs(sample) for sample in samples)
    except Exception:
        return 0


def resample_audio_float(
    audio: "np.ndarray",
    capture_sr: int,
    target_sr: int = SAMPLE_RATE,
) -> "np.ndarray":
    if capture_sr == target_sr:
        return audio
    if resample_poly is None:
        raise STTError("scipy is required for resampling; install scipy")
    ratio = Fraction(target_sr, capture_sr).limit_denominator(1000)
    return resample_poly(audio, ratio.numerator, ratio.denominator)


def apply_wake_word_filter(
    text: str,
    *,
    wake_word: str | None = None,
    require: bool | None = None,
) -> str:
    """
    Enforce optional wake word at the start of the text.

    If required and missing, returns empty string.
    If present as a whole word, strips the wake word and optional separators (, : or space).
    """
    if not text:
        return ""
    cleaned = text.strip()
    if not cleaned:
        return ""

    if require is None:
        require = _env_bool("JARVIS_REQUIRE_WAKE_WORD", False)
    wake = (
        wake_word
        if wake_word is not None
        else os.environ.get("JARVIS_WAKE_WORD", "jarvis")
    ).strip()
    if not wake:
        return cleaned if not require else ""

    match = re.match(
        rf"^\s*{re.escape(wake)}\b(?P<rest>.*)$", cleaned, flags=re.IGNORECASE
    )
    if not match:
        return "" if require else cleaned

    rest = match.group("rest")
    rest = rest.lstrip(" ,:\t").strip()
    return rest


class SpeechToText:
    """
    Speech-to-Text with local-only architecture.

    Modes:
    - "local": Use local faster-whisper
    - "auto": Alias to local (self-hosted only)
    - "none": STT disabled
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._local_model: WhisperModel | None = None
        self._realtime_model: WhisperModel | None = None
        self._vad: VoiceActivityDetector | None = None
        self._streaming_vad: Any | None = None

        self._debug_enabled = _env_bool("JARVIS_DEBUG", False)
        self._metrics_enabled = _env_bool("JARVIS_STT_METRICS", False)
        self._require_wake_word = _env_bool("JARVIS_REQUIRE_WAKE_WORD", False)
        self._wake_word = os.environ.get("JARVIS_WAKE_WORD", "jarvis").strip()
        self._wake_word_audio_enabled = _env_bool("JARVIS_WAKE_WORD_AUDIO", False)
        self._wake_word_audio_backend = (
            _env_str_optional("JARVIS_WAKE_WORD_AUDIO_BACKEND") or "pvporcupine"
        ).strip().lower()
        self._wake_word_detector = None
        self._min_audio_ms = max(0, _env_int("JARVIS_STT_MIN_AUDIO_MS", 300))
        self._min_audio_seconds = max(0.0, _env_float("JARVIS_MIN_AUDIO_SECONDS", 1.2))
        self._early_transcribe_on_silence = _env_bool(
            "JARVIS_STT_EARLY_TRANSCRIBE_ON_SILENCE", False
        )
        self._max_buffer_seconds = max(
            0.0, _env_float("JARVIS_STT_MAX_BUFFER_SECONDS", 0.0)
        )
        self._audio_device = _env_int_optional("JARVIS_AUDIO_DEVICE")
        self._capture_sr_override = _env_int_optional("JARVIS_AUDIO_CAPTURE_SR")
        self._whisper_vad_filter = _env_bool("JARVIS_WHISPER_VAD_FILTER", False)
        self._whisper_beam_size = _env_int_optional("JARVIS_STT_BEAM_SIZE")
        self._whisper_best_of = _env_int_optional("JARVIS_STT_BEST_OF")
        self._whisper_temperature = _env_float_optional("JARVIS_STT_TEMPERATURE")
        self._whisper_initial_prompt = _env_str_optional("JARVIS_STT_INITIAL_PROMPT")
        self._whisper_suppress_tokens = _env_str_optional(
            "JARVIS_STT_SUPPRESS_TOKENS"
        )
        self._warmup_enabled = _env_bool("JARVIS_STT_WARMUP", False)
        self._warmup_seconds = max(
            0.0, _env_float("JARVIS_STT_WARMUP_SECONDS", 0.5)
        )
        self._warmup_done = False
        self._min_gap_seconds = max(
            0.0, _env_float("JARVIS_STT_MIN_GAP_SECONDS", 0.0)
        )
        self._allowed_latency_ms = max(
            0.0, _env_float("JARVIS_STT_ALLOWED_LATENCY_MS", 0.0)
        )
        self._normalize_audio = _env_bool("JARVIS_STT_NORMALIZE_AUDIO", False)
        self._normalize_target = min(
            1.0, max(0.1, _env_float("JARVIS_STT_NORMALIZE_TARGET", 0.98))
        )
        self._normalize_max_gain = max(
            1.0, _env_float("JARVIS_STT_NORMALIZE_MAX_GAIN", 4.0)
        )
        self._vad_silence_ms = max(0, _env_int("JARVIS_VAD_SILENCE_MS", 800))
        self._vad_pre_roll_ms = max(0, _env_int("JARVIS_VAD_PRE_ROLL_MS", 200))
        self._vad_post_roll_ms = max(0, _env_int("JARVIS_VAD_POST_ROLL_MS", 200))
        self._vad_max_seconds = max(1, _env_int("JARVIS_VAD_MAX_SECONDS", 30))
        self._last_record_end_ts = 0.0
        self._silero_deactivity_enabled = _env_bool(
            "JARVIS_SILERO_DEACTIVITY", False
        )
        self._silero_sensitivity = min(
            1.0, max(0.0, _env_float("JARVIS_SILERO_SENSITIVITY", 0.6))
        )
        self._silero_use_onnx = _env_bool("JARVIS_SILERO_USE_ONNX", False)
        self._silero_auto_download = _env_bool("JARVIS_SILERO_AUTO_DOWNLOAD", False)
        self._silero_detector = None

        model_size = getattr(config, "stt_model_size", None) or os.environ.get(
            "JARVIS_STT_MODEL", "small"
        )
        self._model_size = str(model_size)
        self._realtime_model_size = _env_str_optional("JARVIS_STT_REALTIME_MODEL")

        language = os.environ.get("JARVIS_STT_LANGUAGE", "pt").strip()
        if language.lower() in {"auto", "none", ""}:
            self._language = None
        else:
            self._language = language

        if check_vad_available():
            try:
                from ..voz.vad import StreamingVAD, VoiceActivityDetector

                vad_aggr = (
                    resolve_vad_aggressiveness(2)
                    if callable(resolve_vad_aggressiveness)
                    else 2
                )
                self._vad = VoiceActivityDetector(aggressiveness=vad_aggr)
                if VADRecorder is not None:
                    try:
                        self._streaming_vad = VADRecorder(
                            aggressiveness=vad_aggr,
                            silence_duration_ms=self._vad_silence_ms,
                            max_duration_s=self._vad_max_seconds,
                            pre_roll_ms=self._vad_pre_roll_ms,
                            post_roll_ms=self._vad_post_roll_ms,
                            device=self._audio_device,
                        )
                    except TypeError:
                        try:
                            self._streaming_vad = VADRecorder(
                                aggressiveness=vad_aggr,
                                device=self._audio_device,
                            )
                        except TypeError:
                            self._streaming_vad = VADRecorder(aggressiveness=vad_aggr)
                else:
                    self._streaming_vad = StreamingVAD(
                        aggressiveness=vad_aggr,
                        silence_duration_ms=self._vad_silence_ms,
                        max_duration_s=self._vad_max_seconds,
                        pre_roll_ms=self._vad_pre_roll_ms,
                        post_roll_ms=self._vad_post_roll_ms,
                        device=self._audio_device,
                    )
            except Exception as exc:
                self._debug(f"vad init failed: {exc}")

        if self._wake_word_audio_enabled:
            try:
                backend = self._wake_word_audio_backend
                if backend in {"oww", "openwakeword", "openwakewords"}:
                    from ..voz.adapters.wakeword_openwakeword import (
                        build_openwakeword_detector,
                    )

                    self._wake_word_detector = build_openwakeword_detector(
                        self._wake_word,
                        debug=self._debug_enabled,
                    )
                else:
                    if backend not in {"pvporcupine", "porcupine", "pvp"}:
                        self._debug(
                            f"wake word backend desconhecido: {backend}, usando pvporcupine"
                        )
                    from ..voz.adapters.wakeword_porcupine import (
                        build_porcupine_detector,
                    )

                    self._wake_word_detector = build_porcupine_detector(
                        self._wake_word,
                        debug=self._debug_enabled,
                    )
            except Exception as exc:
                self._debug(f"wake word audio init failed: {exc}")

        if self._silero_deactivity_enabled:
            try:
                from ..voz.adapters.vad_silero import (
                    build_silero_deactivity_detector,
                )

                self._silero_detector = build_silero_deactivity_detector(
                    sensitivity=self._silero_sensitivity,
                    use_onnx=self._silero_use_onnx,
                    auto_download=self._silero_auto_download,
                    debug=self._debug_enabled,
                )
                if self._silero_detector is None:
                    self._debug("silero deactivity indisponivel")
            except Exception as exc:
                self._debug(f"silero deactivity init failed: {exc}")

    def _debug(self, message: str) -> None:
        if self._debug_enabled:
            print(f"[stt] {message}")

    def _log_metrics(self, label: str, **values: object) -> None:
        if not self._metrics_enabled:
            return
        parts = [f"{key}={value}" for key, value in values.items()]
        print(f"[stt-metrics] {label} " + " ".join(parts))

    def _should_skip_for_gap(self) -> bool:
        if self._min_gap_seconds <= 0:
            return False
        last = self._last_record_end_ts
        if last <= 0:
            return False
        elapsed = time.monotonic() - last
        if elapsed < self._min_gap_seconds:
            self._log_metrics("min_gap_skip", elapsed_ms=int(elapsed * 1000.0))
            return True
        return False

    def _mark_record_end(self) -> None:
        if self._min_gap_seconds > 0:
            self._last_record_end_ts = time.monotonic()

    def _maybe_normalize_for_stt(self, pcm_bytes: bytes) -> bytes:
        if not self._normalize_audio or np is None:
            return pcm_bytes
        if not pcm_bytes:
            return pcm_bytes
        try:
            samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
        except Exception as exc:
            self._debug(f"normalize failed: {exc}")
            return pcm_bytes
        peak = float(np.max(np.abs(samples))) if samples.size else 0.0
        if peak <= 0:
            return pcm_bytes
        target_peak = float(self._normalize_target * 32767.0)
        gain = target_peak / peak
        if self._normalize_max_gain > 0:
            gain = min(gain, self._normalize_max_gain)
        samples = np.clip(samples * gain, -32768, 32767)
        return samples.astype(np.int16).tobytes()

    def _parse_suppress_tokens(self, value: str | None) -> list[int] | None:
        if not value:
            return None
        tokens: list[int] = []
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                tokens.append(int(part))
            except ValueError:
                self._debug("suppress_tokens invalido; ignorando")
                return None
        return tokens or None

    def _build_whisper_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if self._language:
            kwargs["language"] = self._language
        if self._whisper_vad_filter:
            kwargs["vad_filter"] = True
        if self._whisper_beam_size is not None and self._whisper_beam_size > 0:
            kwargs["beam_size"] = self._whisper_beam_size
        if self._whisper_best_of is not None and self._whisper_best_of > 0:
            kwargs["best_of"] = self._whisper_best_of
        if self._whisper_temperature is not None and self._whisper_temperature >= 0:
            kwargs["temperature"] = self._whisper_temperature
        if self._whisper_initial_prompt:
            kwargs["initial_prompt"] = self._whisper_initial_prompt
        suppress_tokens = self._parse_suppress_tokens(self._whisper_suppress_tokens)
        if suppress_tokens is not None:
            kwargs["suppress_tokens"] = suppress_tokens
        return kwargs

    def _maybe_warmup_model(self) -> None:
        if not self._warmup_enabled or self._warmup_done:
            return
        if np is None or self._local_model is None:
            return
        if self._warmup_seconds <= 0:
            return
        try:
            samples = np.zeros(
                int(self._warmup_seconds * SAMPLE_RATE), dtype=np.float32
            )
            list(self._local_model.transcribe(samples))
            self._warmup_done = True
        except Exception as exc:
            self._debug(f"warmup failed: {exc}")

    def _get_whisper_model(self, *, realtime: bool) -> WhisperModel:
        if WhisperModel is None:
            raise STTError("Missing faster-whisper. Run: pip install faster-whisper")
        if realtime and self._realtime_model_size:
            if self._realtime_model is None:
                self._realtime_model = WhisperModel(
                    self._realtime_model_size,
                    device="cpu",
                    compute_type="int8",
                )
            return self._realtime_model
        if self._local_model is None:
            self._local_model = WhisperModel(
                self._model_size,
                device="cpu",
                compute_type="int8",
            )
        return self._local_model
    def _debug_capture(
        self,
        device: int | None,
        device_name: str,
        capture_sr: int,
        target_sr: int,
        resampled: bool,
    ) -> None:
        if not self._debug_enabled:
            return
        device_label = (
            f"{device} ({device_name})" if device is not None else f"default ({device_name})"
        )
        print(
            f"[stt] audio capture device={device_label} capture_sr={capture_sr} "
            f"target_sr={target_sr} resampled={'yes' if resampled else 'no'}"
        )

    def _resolve_capture_config(self) -> tuple[int | None, int, str]:
        device = self._audio_device
        sd_module = _ensure_sounddevice()
        if sd_module is None:
            return device, SAMPLE_RATE, "unknown"
        try:
            info = sd_module.query_devices(device, "input")
        except Exception as exc:
            self._debug(f"audio device query failed: {exc}")
            info = {}
        name = str(info.get("name") or device or "default")
        capture_sr = self._capture_sr_override
        if capture_sr is None:
            default_sr = info.get("default_samplerate")
            capture_sr = int(default_sr) if default_sr else SAMPLE_RATE
        return device, int(capture_sr), name

    def _record_fixed_duration_compat(
        self,
        seconds: int,
        *,
        capture_sr: int,
        device: int | None,
        device_name: str,
    ) -> tuple[bytes, bool]:
        try:
            return self._record_fixed_duration(
                seconds,
                capture_sr=capture_sr,
                device=device,
                device_name=device_name,
            )
        except TypeError:
            return self._record_fixed_duration(seconds)

    def _min_audio_bytes(self) -> int:
        if self._min_audio_ms <= 0:
            return 0
        return int((self._min_audio_ms / 1000.0) * SAMPLE_RATE * BYTES_PER_SAMPLE)

    def _max_buffer_bytes(self) -> int:
        if self._max_buffer_seconds <= 0:
            return 0
        return int(self._max_buffer_seconds * SAMPLE_RATE * BYTES_PER_SAMPLE)

    def _cap_audio_bytes(self, audio_bytes: bytes) -> bytes:
        max_bytes = self._max_buffer_bytes()
        if max_bytes and len(audio_bytes) > max_bytes:
            self._debug(
                f"audio capped to {max_bytes} bytes (from {len(audio_bytes)})"
            )
            return audio_bytes[:max_bytes]
        return audio_bytes

    def _maybe_apply_silero_deactivity(
        self, audio_bytes: bytes, speech_detected: bool | None
    ) -> tuple[bytes, bool | None]:
        if not self._silero_deactivity_enabled or self._silero_detector is None:
            return audio_bytes, speech_detected
        if speech_detected is False:
            return audio_bytes, speech_detected
        if not audio_bytes:
            return audio_bytes, speech_detected
        try:
            trimmed, silero_speech = self._silero_detector.trim_on_deactivity(
                audio_bytes,
                SAMPLE_RATE,
                post_roll_ms=self._vad_post_roll_ms,
            )
        except Exception as exc:
            self._debug(f"silero deactivity failed: {exc}")
            return audio_bytes, speech_detected
        if silero_speech is False:
            return b"", False
        if silero_speech is True and trimmed:
            return trimmed, True if speech_detected is None else speech_detected
        if silero_speech is True:
            return trimmed, True if speech_detected is None else speech_detected
        return audio_bytes, speech_detected

    def requires_wake_word(self) -> bool:
        return self._require_wake_word

    def transcribe_once(
        self, seconds: int = 5, *, require_wake_word: bool | None = None
    ) -> str:
        """
        Record audio and transcribe to text.

        Args:
            seconds: Duration to record (if not using VAD)

        Returns:
            Transcribed text or empty string.
        """
        mode = getattr(self.config, "stt_mode", "local")
        if mode == "none":
            return ""
        if self._should_skip_for_gap():
            return ""

        try:
            start_record = time.perf_counter()
            audio_bytes = self._record_audio(seconds)
            record_ms = (time.perf_counter() - start_record) * 1000.0
        except Exception as exc:
            self._debug(f"record failed: {exc}")
            return ""
        finally:
            self._mark_record_end()

        start_transcribe = time.perf_counter()
        result = self._transcribe_audio_bytes(
            audio_bytes, require_wake_word=require_wake_word
        )
        transcribe_ms = (time.perf_counter() - start_transcribe) * 1000.0
        self._log_metrics(
            "once",
            record_ms=int(record_ms),
            transcribe_ms=int(transcribe_ms),
            bytes=len(audio_bytes),
        )
        if self._allowed_latency_ms and transcribe_ms > self._allowed_latency_ms:
            self._debug(
                f"transcribe_once latency {transcribe_ms:.1f}ms acima do limite"
            )
            return ""
        # transcribe_once always returns str (not tuple)
        if isinstance(result, tuple):
            return result[0]
        return result

    @overload
    def transcribe_with_vad(
        self,
        max_seconds: int = 30,
        *,
        return_audio: Literal[True],
        require_wake_word: bool | None = None,
        on_partial: Callable[[str], None] | None = None,
    ) -> tuple[str, bytes, bool | None]: ...

    @overload
    def transcribe_with_vad(
        self,
        max_seconds: int = 30,
        *,
        return_audio: Literal[False] = False,
        require_wake_word: bool | None = None,
        on_partial: Callable[[str], None] | None = None,
    ) -> str: ...

    def transcribe_with_vad(
        self,
        max_seconds: int = 30,
        *,
        return_audio: bool = False,
        require_wake_word: bool | None = None,
        on_partial: Callable[[str], None] | None = None,
    ) -> str | tuple[str, bytes, bool | None]:
        """
        Record audio using VAD (Voice Activity Detection) and transcribe.

        Stops recording when speech ends instead of fixed duration.
        If on_partial is provided, it receives incremental text during decoding.
        """
        mode = getattr(self.config, "stt_mode", "local")
        if mode == "none":
            return ("", b"", None) if return_audio else ""
        if self._should_skip_for_gap():
            return ("", b"", None) if return_audio else ""

        start_record = time.perf_counter()
        audio_bytes, speech_detected = self._record_until_silence(max_seconds)
        record_ms = (time.perf_counter() - start_record) * 1000.0
        self._mark_record_end()
        if not audio_bytes:
            self._log_metrics(
                "with_vad",
                record_ms=int(record_ms),
                transcribe_ms=0,
                bytes=0,
                speech=speech_detected,
            )
            return ("", b"", speech_detected) if return_audio else ""
        if speech_detected is False:
            self._log_metrics(
                "with_vad",
                record_ms=int(record_ms),
                transcribe_ms=0,
                bytes=len(audio_bytes),
                speech=speech_detected,
            )
            return ("", b"", speech_detected) if return_audio else ""
        allow_short_audio = (
            self._early_transcribe_on_silence and speech_detected is True
        )
        if (
            self._min_audio_bytes()
            and len(audio_bytes) < self._min_audio_bytes()
            and not allow_short_audio
        ):
            self._log_metrics(
                "with_vad",
                record_ms=int(record_ms),
                transcribe_ms=0,
                bytes=len(audio_bytes),
                speech=speech_detected,
            )
            return (
                ("", coerce_pcm_bytes(audio_bytes), speech_detected)
                if return_audio
                else ""
            )

        require = (
            self._require_wake_word if require_wake_word is None else require_wake_word
        )
        text_require_wake = require
        if (
            require
            and self._wake_word_audio_enabled
            and self._wake_word_detector is not None
        ):
            try:
                detected = self._wake_word_detector.detect(audio_bytes, SAMPLE_RATE)
            except Exception as exc:
                self._debug(f"wake word audio detect failed: {exc}")
                detected = None
            if detected is False:
                self._log_metrics(
                    "with_vad",
                    record_ms=int(record_ms),
                    transcribe_ms=0,
                    bytes=len(audio_bytes),
                    speech=speech_detected,
                )
                return ("", audio_bytes, speech_detected) if return_audio else ""
            if detected is True:
                text_require_wake = False

        # If VAD is unavailable or failed, optionally try Rust trim to detect speech.
        if speech_detected is None and not self._vad and jarvis_audio is not None:
            audio_bytes, rust_speech = self._trim_with_rust(audio_bytes, force=True)
            if rust_speech is False:
                self._log_metrics(
                    "with_vad",
                    record_ms=int(record_ms),
                    transcribe_ms=0,
                    bytes=len(audio_bytes),
                    speech=rust_speech,
                )
                return ("", b"", rust_speech) if return_audio else ""
            allow_short = bool(rust_speech) if rust_speech is not None else False
            start_transcribe = time.perf_counter()
            result = self._transcribe_audio_bytes(
                audio_bytes,
                skip_rust_trim=True,
                allow_short_audio=allow_short,
                require_wake_word=text_require_wake,
                return_audio=return_audio,
                skip_speech_check=bool(rust_speech),
                on_partial=on_partial,
            )
            transcribe_ms = (time.perf_counter() - start_transcribe) * 1000.0
            self._log_metrics(
                "with_vad",
                record_ms=int(record_ms),
                transcribe_ms=int(transcribe_ms),
                bytes=len(audio_bytes),
                speech=rust_speech,
            )
            if self._allowed_latency_ms and transcribe_ms > self._allowed_latency_ms:
                self._debug(
                    f"transcribe_with_vad latency {transcribe_ms:.1f}ms acima do limite"
                )
                return ("", audio_bytes, rust_speech) if return_audio else ""
            if return_audio:
                text, final_bytes = result  # type: ignore[misc]
                return text, final_bytes, rust_speech
            return result  # type: ignore[return-value]

        start_transcribe = time.perf_counter()
        result = self._transcribe_audio_bytes(
            audio_bytes,
            require_wake_word=text_require_wake,
            return_audio=return_audio,
            allow_short_audio=allow_short_audio,
            skip_speech_check=bool(speech_detected),
            on_partial=on_partial,
        )
        transcribe_ms = (time.perf_counter() - start_transcribe) * 1000.0
        self._log_metrics(
            "with_vad",
            record_ms=int(record_ms),
            transcribe_ms=int(transcribe_ms),
            bytes=len(audio_bytes),
            speech=speech_detected,
        )
        if self._allowed_latency_ms and transcribe_ms > self._allowed_latency_ms:
            self._debug(
                f"transcribe_with_vad latency {transcribe_ms:.1f}ms acima do limite"
            )
            return ("", audio_bytes, speech_detected) if return_audio else ""
        if return_audio:
            text, final_bytes = result  # type: ignore[misc]
            return text, final_bytes, speech_detected
        return result  # type: ignore[return-value]

    def _record_until_silence(self, max_seconds: int) -> tuple[bytes, bool | None]:
        device, capture_sr, device_name = self._resolve_capture_config()
        use_streaming = (
            self._streaming_vad is not None
            and capture_sr == SAMPLE_RATE
            and device is None
        )
        if not use_streaming:
            audio_bytes, speech_detected = self._record_fixed_duration_compat(
                max_seconds,
                capture_sr=capture_sr,
                device=device,
                device_name=device_name,
            )
            audio_bytes = self._cap_audio_bytes(audio_bytes)
            audio_bytes, speech_detected = self._maybe_apply_silero_deactivity(
                audio_bytes, speech_detected
            )
            return audio_bytes, speech_detected

        try:
            try:
                result = self._streaming_vad.record_until_silence(
                    max_seconds=max_seconds,
                    return_speech_flag=True,
                    empty_if_no_speech=True,
                )
            except TypeError:
                result = self._streaming_vad.record_until_silence(
                    max_seconds=max_seconds
                )
            audio_bytes, speech_detected = self._split_record_result(result)
            audio_bytes = self._cap_audio_bytes(audio_bytes)
            audio_bytes, speech_detected = self._maybe_apply_silero_deactivity(
                audio_bytes, speech_detected
            )
            self._debug_capture(device, device_name, capture_sr, SAMPLE_RATE, False)
            return audio_bytes, speech_detected
        except Exception as exc:
            self._debug(f"record_until_silence failed: {exc}")
            audio_bytes, speech_detected = self._record_fixed_duration_compat(
                max_seconds,
                capture_sr=capture_sr,
                device=device,
                device_name=device_name,
            )
            audio_bytes = self._cap_audio_bytes(audio_bytes)
            audio_bytes, speech_detected = self._maybe_apply_silero_deactivity(
                audio_bytes, speech_detected
            )
            return audio_bytes, speech_detected

    def _split_record_result(self, result: Any) -> tuple[bytes, bool | None]:
        speech_detected: bool | None = None
        audio = result
        if isinstance(result, tuple) and len(result) >= 2:
            audio = result[0]
            speech_detected = bool(result[1])
        try:
            audio_bytes = coerce_pcm_bytes(audio)
        except Exception as exc:
            self._debug(f"audio coerce failed: {exc}")
            return b"", speech_detected
        return audio_bytes, speech_detected

    def _record_audio(self, seconds: int) -> bytes:
        """
        Record audio from microphone.

        Uses VAD if available to stop when speech ends.
        """
        device, capture_sr, device_name = self._resolve_capture_config()
        use_streaming = (
            self._streaming_vad is not None
            and capture_sr == SAMPLE_RATE
            and device is None
        )
        if use_streaming:
            try:
                result = self._streaming_vad.record_until_silence(max_seconds=seconds)
                audio = result
                if (
                    isinstance(result, tuple)
                    and len(result) >= 2
                    and isinstance(result[1], (bool, int))
                ):
                    audio = result[0]

                if audio is None:
                    audio_bytes = b""
                elif isinstance(audio, (bytes, bytearray, memoryview)):
                    audio_bytes = bytes(audio)
                elif isinstance(audio, (list, tuple)) and all(
                    isinstance(item, (bytes, bytearray, memoryview)) for item in audio
                ):
                    audio_bytes = b"".join(bytes(item) for item in audio)
                else:
                    audio_bytes = audio

                try:
                    audio_bytes = coerce_pcm_bytes(audio_bytes)
                except Exception as exc:
                    self._debug(f"audio coerce failed: {exc}")
                    audio_bytes = b""
                audio_bytes = self._cap_audio_bytes(audio_bytes)

                self._debug_capture(device, device_name, capture_sr, SAMPLE_RATE, False)
                min_bytes = int(
                    self._min_audio_seconds * SAMPLE_RATE * BYTES_PER_SAMPLE
                )
                if min_bytes <= 0 or len(audio_bytes) >= min_bytes:
                    return audio_bytes
            except Exception as exc:
                self._debug(f"streaming vad record failed: {exc}")

        sd_module = _ensure_sounddevice()
        if sd_module is None or np is None:
            self._debug("missing sounddevice/numpy")
            return b""

        audio_bytes, _speech = self._record_fixed_duration_compat(
            seconds,
            capture_sr=capture_sr,
            device=device,
            device_name=device_name,
        )
        return self._cap_audio_bytes(audio_bytes)

    def transcribe_audio_bytes(
        self,
        audio_bytes: Any,
        *,
        require_wake_word: bool | None = None,
        return_audio: bool = False,
        speech_detected: bool | None = None,
        on_partial: Callable[[str], None] | None = None,
    ) -> str | tuple[str, bytes]:
        """
        Transcribe audio bytes without touching the microphone.

        If on_partial is provided, it receives incremental text during decoding.
        """
        if not audio_bytes:
            return ("", b"") if return_audio else ""
        allow_short_audio = (
            self._early_transcribe_on_silence and speech_detected is True
        )
        return self._transcribe_audio_bytes(
            audio_bytes,
            require_wake_word=require_wake_word,
            return_audio=return_audio,
            allow_short_audio=allow_short_audio,
            skip_speech_check=bool(speech_detected),
            on_partial=on_partial,
        )

    def _record_fixed_duration(
        self,
        seconds: int,
        *,
        capture_sr: int | None = None,
        device: int | None = None,
        device_name: str | None = None,
    ) -> tuple[bytes, bool]:
        if capture_sr is None or device_name is None:
            device, capture_sr, device_name = self._resolve_capture_config()

        use_streaming = (
            self._streaming_vad is not None
            and capture_sr == SAMPLE_RATE
            and device is None
        )
        if use_streaming and hasattr(self._streaming_vad, "record_fixed_duration"):
            try:
                audio_bytes, speech_detected = (
                    self._streaming_vad.record_fixed_duration(seconds)
                )
                self._debug_capture(device, device_name, capture_sr, SAMPLE_RATE, False)
                return coerce_pcm_bytes(audio_bytes), bool(speech_detected)
            except Exception as exc:
                self._debug(f"record_fixed_duration failed: {exc}")

        sd_module = _ensure_sounddevice()
        if sd_module is None or np is None:
            return b"", False

        samplerate = int(capture_sr)
        audio = sd_module.rec(
            int(seconds * samplerate),
            samplerate=samplerate,
            channels=1,
            dtype="float32",
            device=device,
        )
        sd_module.wait()

        mono = audio.flatten()
        if samplerate != SAMPLE_RATE:
            try:
                mono = resample_audio_float(mono, samplerate, SAMPLE_RATE).astype(
                    np.float32
                )
            except Exception as exc:
                self._debug(f"resample failed: {exc}")
                return b"", False

        int16_data = (mono * 32767).astype(np.int16)
        audio_bytes = int16_data.tobytes()
        if apply_aec_to_audio is not None:
            try:
                audio_bytes = apply_aec_to_audio(
                    audio_bytes, SAMPLE_RATE, frame_ms=30
                )
            except Exception as exc:
                self._debug(f"aec failed: {exc}")
        self._debug_capture(
            device,
            device_name,
            samplerate,
            SAMPLE_RATE,
            samplerate != SAMPLE_RATE,
        )
        speech_detected = self.check_speech_present(audio_bytes)
        return audio_bytes, speech_detected

    def _transcribe_audio_bytes(
        self,
        audio_bytes: Any,
        *,
        skip_rust_trim: bool = False,
        allow_short_audio: bool = False,
        require_wake_word: bool | None = None,
        return_audio: bool = False,
        skip_speech_check: bool = False,
        on_partial: Callable[[str], None] | None = None,
    ) -> str | tuple[str, bytes]:
        try:
            pcm_bytes = coerce_pcm_bytes(audio_bytes)
        except Exception as exc:
            self._debug(f"invalid audio payload: {exc}")
            return ("", b"") if return_audio else ""

        if not pcm_bytes:
            return ("", b"") if return_audio else ""

        rust_speech: bool | None = None
        if not skip_rust_trim:
            pcm_bytes, rust_speech = self._trim_with_rust(pcm_bytes, force=False)
            if rust_speech is False:
                return ("", b"") if return_audio else ""
            if rust_speech is True:
                allow_short_audio = True
                skip_speech_check = True

        min_bytes = self._min_audio_bytes()
        if min_bytes and len(pcm_bytes) < min_bytes and not allow_short_audio:
            return ("", pcm_bytes) if return_audio else ""

        if not skip_speech_check and not self.check_speech_present(pcm_bytes):
            return ("", pcm_bytes) if return_audio else ""

        pcm_bytes = self._maybe_normalize_for_stt(pcm_bytes)
        use_realtime_model = bool(self._realtime_model_size) and on_partial is not None
        try:
            if on_partial is not None or use_realtime_model:
                text = self._transcribe_local(
                    pcm_bytes,
                    on_partial=on_partial,
                    realtime=use_realtime_model,
                )
            else:
                text = self._transcribe_local(pcm_bytes)
        except Exception as exc:
            self._debug(f"transcribe failed: {exc}")
            return ("", pcm_bytes) if return_audio else ""

        text = text.strip()
        if not text:
            return ("", pcm_bytes) if return_audio else ""

        require = (
            self._require_wake_word if require_wake_word is None else require_wake_word
        )
        filtered = apply_wake_word_filter(
            text,
            wake_word=self._wake_word,
            require=require,
        )
        filtered_text = filtered.strip()
        if return_audio:
            return filtered_text, pcm_bytes
        return filtered_text

    def _trim_with_rust(
        self, audio_bytes: bytes, *, force: bool
    ) -> tuple[bytes, bool | None]:
        if jarvis_audio is None or not hasattr(jarvis_audio, "trim_until_silence"):
            return audio_bytes, None

        backend = getattr(self.config, "stt_audio_trim_backend", "")
        use_rust = str(backend).lower() == "rust"
        if not (use_rust or force):
            return audio_bytes, None

        try:
            trimmed, speech_detected, _stats = jarvis_audio.trim_until_silence(
                audio_bytes,
                SAMPLE_RATE,
                20,
                200,
                200,
                300,
            )
            trimmed_bytes = coerce_pcm_bytes(trimmed)
            return trimmed_bytes, bool(speech_detected)
        except Exception as exc:
            self._debug(f"rust trim failed: {exc}")
            return audio_bytes, None

    def _transcribe_local(
        self,
        audio_bytes: bytes,
        *,
        on_partial: Callable[[str], None] | None = None,
        realtime: bool = False,
    ) -> str:
        """
        Transcribe audio using local faster-whisper.
        """
        model = self._get_whisper_model(realtime=realtime)
        if model is self._local_model:
            self._maybe_warmup_model()

        kwargs = self._build_whisper_kwargs()
        last_partial = ""

        def emit_partial(partial: str) -> None:
            nonlocal last_partial
            if on_partial is None:
                return
            cleaned = partial.strip()
            if not cleaned or cleaned == last_partial:
                return
            last_partial = cleaned
            try:
                on_partial(cleaned)
            except Exception as exc:
                self._debug(f"on_partial failed: {exc}")

        if np is not None:
            try:
                samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
                if samples.size:
                    samples /= 32768.0
                segments, _info = model.transcribe(samples, **kwargs)
                parts: list[str] = []
                for seg in segments:
                    chunk = seg.text.strip()
                    if not chunk:
                        continue
                    parts.append(chunk)
                    emit_partial(" ".join(parts))
                return " ".join(parts).strip()
            except Exception as exc:
                self._debug(f"whisper in-memory failed: {exc}")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
            self._write_wav(wav_path, audio_bytes, SAMPLE_RATE)

        try:
            segments, _info = model.transcribe(wav_path, **kwargs)
            parts: list[str] = []
            for seg in segments:
                chunk = seg.text.strip()
                if not chunk:
                    continue
                parts.append(chunk)
                emit_partial(" ".join(parts))
            return " ".join(parts).strip()
        finally:
            try:
                os.unlink(wav_path)
            except Exception:
                pass

    def _write_wav(self, path: str, audio_bytes: Any, samplerate: int) -> None:
        """Write audio bytes to WAV file."""
        data = coerce_pcm_bytes(audio_bytes)
        with wave.open(path, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)  # 16-bit
            handle.setframerate(samplerate)
            handle.writeframes(data)

    def check_speech_present(self, audio_bytes: Any) -> bool:
        """
        Check if audio contains speech.

        Uses VAD if available, otherwise optional Rust check.
        """
        try:
            pcm_bytes = coerce_pcm_bytes(audio_bytes)
        except Exception:
            return False
        if not pcm_bytes:
            return False

        if self._vad is None:
            if jarvis_audio is not None and hasattr(
                jarvis_audio, "check_speech_present"
            ):
                try:
                    return bool(
                        jarvis_audio.check_speech_present(pcm_bytes, SAMPLE_RATE, 20)
                    )
                except Exception as exc:
                    self._debug(f"rust speech check failed: {exc}")
                    return False
            min_peak = _env_int("JARVIS_STT_MIN_PEAK", 300)
            return _peak_amplitude(pcm_bytes) >= max(0, min_peak)

        speech_frames = 0
        total_frames = 0

        for frame in self._vad.frames_from_audio(pcm_bytes):
            if self._vad.is_speech(frame):
                speech_frames += 1
            total_frames += 1

        return (speech_frames / total_frames) > 0.1 if total_frames > 0 else False


def check_stt_deps() -> dict:
    """Check STT dependencies."""
    sd_module = _ensure_sounddevice()
    return {
        "sounddevice": sd_module is not None,
        "numpy": np is not None,
        "scipy": resample_poly is not None,
        "faster_whisper": WhisperModel is not None,
        "webrtcvad": check_vad_available() if callable(check_vad_available) else False,
    }


def _write_wav(path: str, audio: Any, samplerate: int) -> None:
    """Legacy function for backwards compatibility."""
    data = coerce_pcm_bytes(audio)
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(samplerate)
        handle.writeframes(data)
