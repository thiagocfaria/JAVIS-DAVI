"""
Speech-to-Text module (local only).

Uses faster-whisper locally, with optional VAD and wake word filtering.
"""

from __future__ import annotations

import os
import re
import tempfile
import wave
from fractions import Fraction
from typing import Any, Literal, overload

from ..cerebro.config import Config
from .audio_utils import BYTES_PER_SAMPLE, SAMPLE_RATE, coerce_pcm_bytes

try:
    import numpy as np  # type: ignore
    import sounddevice as sd  # type: ignore
except (ImportError, OSError):
    np = None
    sd = None

try:
    from scipy.signal import resample_poly  # type: ignore
except Exception:
    resample_poly = None

try:
    from faster_whisper import WhisperModel  # type: ignore
except ImportError:
    WhisperModel = None

try:
    from ..voz.vad import StreamingVAD, VoiceActivityDetector, check_vad_available
except Exception:
    # When import fails, assign None - mypy will treat as Any in type context
    StreamingVAD = None  # type: ignore[assignment, misc]
    VoiceActivityDetector = None  # type: ignore[assignment, misc]

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


def _env_int_optional(key: str) -> int | None:
    value = os.environ.get(key)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


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
        self._vad: VoiceActivityDetector | None = None
        self._streaming_vad: Any | None = None

        self._debug_enabled = _env_bool("JARVIS_DEBUG", False)
        self._require_wake_word = _env_bool("JARVIS_REQUIRE_WAKE_WORD", False)
        self._wake_word = os.environ.get("JARVIS_WAKE_WORD", "jarvis").strip()
        self._min_audio_ms = max(0, _env_int("JARVIS_STT_MIN_AUDIO_MS", 300))
        self._min_audio_seconds = max(0.0, _env_float("JARVIS_MIN_AUDIO_SECONDS", 1.2))
        self._audio_device = _env_int_optional("JARVIS_AUDIO_DEVICE")
        self._capture_sr_override = _env_int_optional("JARVIS_AUDIO_CAPTURE_SR")

        model_size = getattr(config, "stt_model_size", None) or os.environ.get(
            "JARVIS_STT_MODEL", "small"
        )
        self._model_size = str(model_size)

        language = os.environ.get("JARVIS_STT_LANGUAGE", "pt").strip()
        if language.lower() in {"auto", "none", ""}:
            self._language = None
        else:
            self._language = language

        if check_vad_available():
            try:
                from ..voz.vad import StreamingVAD, VoiceActivityDetector

                self._vad = VoiceActivityDetector(aggressiveness=2)
                if VADRecorder is not None:
                    self._streaming_vad = VADRecorder(aggressiveness=2)
                else:
                    self._streaming_vad = StreamingVAD(aggressiveness=2)
            except Exception as exc:
                self._debug(f"vad init failed: {exc}")

    def _debug(self, message: str) -> None:
        if self._debug_enabled:
            print(f"[stt] {message}")

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
        if sd is None:
            return device, SAMPLE_RATE, "unknown"
        try:
            info = sd.query_devices(device, "input")
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

        try:
            audio_bytes = self._record_audio(seconds)
        except Exception as exc:
            self._debug(f"record failed: {exc}")
            return ""

        result = self._transcribe_audio_bytes(
            audio_bytes, require_wake_word=require_wake_word
        )
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
    ) -> tuple[str, bytes, bool | None]: ...

    @overload
    def transcribe_with_vad(
        self,
        max_seconds: int = 30,
        *,
        return_audio: Literal[False] = False,
        require_wake_word: bool | None = None,
    ) -> str: ...

    def transcribe_with_vad(
        self,
        max_seconds: int = 30,
        *,
        return_audio: bool = False,
        require_wake_word: bool | None = None,
    ) -> str | tuple[str, bytes, bool | None]:
        """
        Record audio using VAD (Voice Activity Detection) and transcribe.

        Stops recording when speech ends instead of fixed duration.
        """
        mode = getattr(self.config, "stt_mode", "local")
        if mode == "none":
            return ("", b"", None) if return_audio else ""

        audio_bytes, speech_detected = self._record_until_silence(max_seconds)
        if not audio_bytes:
            return ("", b"", speech_detected) if return_audio else ""
        if speech_detected is False:
            return ("", b"", speech_detected) if return_audio else ""
        if self._min_audio_bytes() and len(audio_bytes) < self._min_audio_bytes():
            return (
                ("", coerce_pcm_bytes(audio_bytes), speech_detected)
                if return_audio
                else ""
            )

        # If VAD is unavailable or failed, optionally try Rust trim to detect speech.
        if speech_detected is None and not self._vad and jarvis_audio is not None:
            audio_bytes, rust_speech = self._trim_with_rust(audio_bytes, force=True)
            if rust_speech is False:
                return ("", b"", rust_speech) if return_audio else ""
            allow_short = bool(rust_speech) if rust_speech is not None else False
            result = self._transcribe_audio_bytes(
                audio_bytes,
                skip_rust_trim=True,
                allow_short_audio=allow_short,
                require_wake_word=require_wake_word,
                return_audio=return_audio,
                skip_speech_check=bool(rust_speech),
            )
            if return_audio:
                text, final_bytes = result  # type: ignore[misc]
                return text, final_bytes, rust_speech
            return result  # type: ignore[return-value]

        result = self._transcribe_audio_bytes(
            audio_bytes,
            require_wake_word=require_wake_word,
            return_audio=return_audio,
            skip_speech_check=bool(speech_detected),
        )
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

                self._debug_capture(device, device_name, capture_sr, SAMPLE_RATE, False)
                min_bytes = int(
                    self._min_audio_seconds * SAMPLE_RATE * BYTES_PER_SAMPLE
                )
                if min_bytes <= 0 or len(audio_bytes) >= min_bytes:
                    return audio_bytes
            except Exception as exc:
                self._debug(f"streaming vad record failed: {exc}")

        if sd is None or np is None:
            self._debug("missing sounddevice/numpy")
            return b""

        audio_bytes, _speech = self._record_fixed_duration_compat(
            seconds,
            capture_sr=capture_sr,
            device=device,
            device_name=device_name,
        )
        return audio_bytes

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

        if sd is None or np is None:
            return b"", False

        samplerate = int(capture_sr)
        audio = sd.rec(
            int(seconds * samplerate),
            samplerate=samplerate,
            channels=1,
            dtype="float32",
            device=device,
        )
        sd.wait()

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

        min_bytes = self._min_audio_bytes()
        if min_bytes and len(pcm_bytes) < min_bytes and not allow_short_audio:
            return ("", pcm_bytes) if return_audio else ""

        if not skip_speech_check and not self.check_speech_present(pcm_bytes):
            return ("", pcm_bytes) if return_audio else ""

        try:
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

    def _transcribe_local(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio using local faster-whisper.
        """
        if WhisperModel is None:
            raise STTError("Missing faster-whisper. Run: pip install faster-whisper")

        if self._local_model is None:
            self._local_model = WhisperModel(
                self._model_size,
                device="cpu",
                compute_type="int8",
            )

        kwargs: dict[str, Any] = {}
        if self._language:
            kwargs["language"] = self._language

        if np is not None:
            try:
                samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
                if samples.size:
                    samples /= 32768.0
                segments, _info = self._local_model.transcribe(samples, **kwargs)
                text = " ".join(seg.text.strip() for seg in segments)
                return text.strip()
            except Exception as exc:
                self._debug(f"whisper in-memory failed: {exc}")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
            self._write_wav(wav_path, audio_bytes, SAMPLE_RATE)

        try:
            segments, _info = self._local_model.transcribe(wav_path, **kwargs)
            text = " ".join(seg.text.strip() for seg in segments)
            return text.strip()
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
            return True

        speech_frames = 0
        total_frames = 0

        for frame in self._vad.frames_from_audio(pcm_bytes):
            if self._vad.is_speech(frame):
                speech_frames += 1
            total_frames += 1

        return (speech_frames / total_frames) > 0.1 if total_frames > 0 else False


def check_stt_deps() -> dict:
    """Check STT dependencies."""
    return {
        "sounddevice": sd is not None,
        "numpy": np is not None,
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
