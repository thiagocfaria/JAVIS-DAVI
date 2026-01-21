"""
Voice Activity Detection (VAD) module using webrtcvad.

This module provides lightweight voice activity detection without PyTorch.
webrtcvad is a C library wrapped in Python, very efficient and low memory.
"""

from __future__ import annotations

import collections
import os
import threading
import time
from collections.abc import Generator
from typing import TYPE_CHECKING, Any, TypeAlias

try:
    import webrtcvad  # type: ignore
except ImportError:
    webrtcvad = None

try:
    import numpy as np  # type: ignore
except (ImportError, OSError):
    np = None

if TYPE_CHECKING:
    import numpy as _np

    NDArrayFloat: TypeAlias = _np.ndarray
else:
    NDArrayFloat: TypeAlias = Any

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


class VADError(Exception):
    """Voice Activity Detection error."""

    pass


def _env_int_optional(key: str) -> int | None:
    value = os.environ.get(key)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


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


def _env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _aec_backend() -> str:
    value = os.environ.get("JARVIS_AEC_BACKEND", "")
    value = value.strip().lower()
    return value or "none"


def is_aec_enabled() -> bool:
    backend = _aec_backend()
    if backend not in {"simple", "speex", "webrtc"}:
        return False
    try:
        disable_below = float(os.environ.get("JARVIS_AEC_DISABLE_BELOW_RMS", "0"))
    except Exception:
        disable_below = 0.0
    if disable_below > 0.0:
        try:
            rms_env = float(os.environ.get("JARVIS_AUDIO_INPUT_RMS", "0"))
        except Exception:
            rms_env = 0.0
        if rms_env < disable_below:
            return False
    return True


def _frame_rms(audio_frame: bytes) -> float:
    if np is None or not audio_frame:
        return 0.0
    samples = np.frombuffer(audio_frame, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return 0.0
    samples /= 32768.0
    return float(np.sqrt(np.mean(samples**2)) + 1e-8)


class _PlaybackReference:
    def __init__(self, max_seconds: int, sample_rate: int = 16000) -> None:
        self.max_seconds = max(1, int(max_seconds))
        self.sample_rate = sample_rate
        self._max_bytes = max(1, int(self.max_seconds * sample_rate * 2))
        self._buffer = bytearray()
        self._lock = threading.Lock()

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()

    def push(self, audio_bytes: bytes) -> None:
        if not audio_bytes:
            return
        with self._lock:
            self._buffer.extend(audio_bytes)
            if len(self._buffer) > self._max_bytes:
                del self._buffer[: -self._max_bytes]

    def pop(self, size: int) -> bytes:
        if size <= 0:
            return b""
        with self._lock:
            if not self._buffer:
                return b""
            if len(self._buffer) >= size:
                chunk = bytes(self._buffer[:size])
                del self._buffer[:size]
                return chunk
            chunk = bytes(self._buffer)
            self._buffer.clear()
            return chunk + (b"\x00" * (size - len(chunk)))


_AEC_REF: _PlaybackReference | None = None
_AEC_PROCESSOR: _SimpleAec | None = None  # type: ignore[name-defined]
_AEC_KEY: tuple[str, int, int, float, int] | None = None


def _get_playback_reference() -> _PlaybackReference:
    global _AEC_REF
    max_seconds = _env_int("JARVIS_AEC_REF_SECONDS", 5)
    if _AEC_REF is None or _AEC_REF.max_seconds != max_seconds:
        _AEC_REF = _PlaybackReference(max_seconds=max_seconds, sample_rate=16000)
    return _AEC_REF


def reset_playback_reference() -> None:
    global _AEC_REF, _AEC_PROCESSOR, _AEC_KEY
    _AEC_REF = None
    _AEC_PROCESSOR = None
    _AEC_KEY = None


def _resample_to_target(
    audio_bytes: bytes, sample_rate: int, target_rate: int
) -> bytes:
    if np is None:
        return b""
    if not audio_bytes or sample_rate <= 0 or target_rate <= 0:
        return b""
    if sample_rate == target_rate:
        return audio_bytes
    samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return b""
    target_len = int(round(samples.size * (target_rate / sample_rate)))
    if target_len <= 0:
        return b""
    x_old = np.linspace(0.0, 1.0, num=samples.size, endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=target_len, endpoint=False)
    resampled = np.interp(x_new, x_old, samples).astype(np.float32)
    resampled = np.clip(resampled, -32768.0, 32767.0)
    return resampled.astype(np.int16).tobytes()


def push_playback_reference(audio_bytes: bytes, sample_rate: int) -> bool:
    if not is_aec_enabled() or np is None:
        return False
    if not isinstance(audio_bytes, (bytes, bytearray, memoryview)):
        return False
    raw_bytes = bytes(audio_bytes)
    if not raw_bytes:
        return False
    resampled = _resample_to_target(raw_bytes, sample_rate, 16000)
    if not resampled:
        return False
    _get_playback_reference().push(resampled)
    return True


class _SimpleAec:
    def __init__(
        self, reference: _PlaybackReference, sample_rate: int, frame_ms: int
    ) -> None:
        self._reference = reference
        self._sample_rate = sample_rate
        self._frame_samples = max(1, int(sample_rate * frame_ms / 1000))
        self._frame_bytes = self._frame_samples * 2
        self._max_gain = max(0.0, _env_float("JARVIS_AEC_MAX_GAIN", 1.0))
        self._noise_gate = max(0.0, _env_float("JARVIS_AEC_NOISE_GATE", 0.002))

    def process(self, audio_frame: bytes) -> bytes:
        if np is None or not audio_frame:
            return audio_frame
        if len(audio_frame) != self._frame_bytes:
            return audio_frame
        ref_frame = self._reference.pop(self._frame_bytes)
        if not ref_frame:
            return audio_frame
        near = np.frombuffer(audio_frame, dtype=np.int16).astype(np.float32)
        far = np.frombuffer(ref_frame, dtype=np.int16).astype(np.float32)
        denom = float((far * far).sum()) + 1e-6
        gain = float((near * far).sum()) / denom
        if gain < 0.0:
            gain = 0.0
        if gain > self._max_gain:
            gain = self._max_gain
        cleaned = near - gain * far
        cleaned = np.clip(cleaned, -32768.0, 32767.0)
        if self._noise_gate > 0.0:
            rms = float(np.sqrt(np.mean(cleaned**2)) + 1e-8)
            if rms < self._noise_gate:
                return b"\x00" * len(audio_frame)
        return cleaned.astype(np.int16).tobytes()


def _get_aec_processor(sample_rate: int, frame_ms: int) -> _SimpleAec | None:
    global _AEC_PROCESSOR, _AEC_KEY
    backend = _aec_backend()
    if backend not in {"simple", "speex", "webrtc"} or np is None or sample_rate != 16000:
        _AEC_PROCESSOR = None
        _AEC_KEY = None
        return None
    key = (
        backend,
        sample_rate,
        frame_ms,
        float(_env_float("JARVIS_AEC_MAX_GAIN", 1.0)),
        _env_int("JARVIS_AEC_REF_SECONDS", 5),
    )
    if _AEC_PROCESSOR is None or _AEC_KEY != key:
        _AEC_PROCESSOR = _SimpleAec(_get_playback_reference(), sample_rate, frame_ms)
        _AEC_KEY = key
    return _AEC_PROCESSOR


def apply_aec_to_audio(
    audio_bytes: bytes, sample_rate: int, frame_ms: int = 30
) -> bytes:
    processor = _get_aec_processor(sample_rate, frame_ms)
    if processor is None:
        return audio_bytes
    frame_samples = max(1, int(sample_rate * frame_ms / 1000))
    frame_bytes = frame_samples * 2
    if frame_bytes <= 0:
        return audio_bytes
    output: list[bytes] = []
    total = len(audio_bytes)
    for offset in range(0, total, frame_bytes):
        frame = audio_bytes[offset : offset + frame_bytes]
        if len(frame) < frame_bytes:
            frame = frame + (b"\x00" * (frame_bytes - len(frame)))
        output.append(processor.process(frame))
    joined = b"".join(output)
    return joined[:total]


def resolve_vad_aggressiveness(default: int = 2) -> int:
    value = _env_int_optional("JARVIS_VAD_AGGRESSIVENESS")
    if value is None:
        return default
    if value < 0:
        return 0
    if value > 3:
        return 3
    return value


class VoiceActivityDetector:
    """
    Lightweight VAD using webrtcvad (C library, no PyTorch).

    Aggressiveness levels:
        0 - Least aggressive (more false positives, catches more speech)
        1 - Low aggressiveness
        2 - Medium aggressiveness
        3 - Most aggressive (fewer false positives, may miss quiet speech)
    """

    # Supported sample rates by webrtcvad
    SUPPORTED_RATES = (8000, 16000, 32000, 48000)
    # Frame duration must be 10, 20, or 30 ms
    SUPPORTED_FRAME_DURATIONS_MS = (10, 20, 30)

    def __init__(
        self,
        aggressiveness: int | None = None,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
    ) -> None:
        if webrtcvad is None:
            raise VADError("webrtcvad not installed. Run: pip install webrtcvad")

        if sample_rate not in self.SUPPORTED_RATES:
            raise VADError(f"Sample rate must be one of {self.SUPPORTED_RATES}")

        if frame_duration_ms not in self.SUPPORTED_FRAME_DURATIONS_MS:
            raise VADError(
                f"Frame duration must be one of {self.SUPPORTED_FRAME_DURATIONS_MS} ms"
            )

        if aggressiveness is None:
            aggressiveness = resolve_vad_aggressiveness(2)

        if not 0 <= aggressiveness <= 3:
            raise VADError("Aggressiveness must be 0-3")

        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.bytes_per_frame = self.frame_size * 2  # 16-bit audio = 2 bytes per sample

        self._vad = webrtcvad.Vad(aggressiveness)
        self._aggressiveness = aggressiveness  # Expor para testes
        self._preprocess_enabled = _env_bool("JARVIS_VAD_PREPROCESS", False)
        self._agc_target_rms = max(0.0, _env_float("JARVIS_AUDIO_AGC_TARGET_RMS", 0.06))
        self._agc_max_gain = max(1.0, _env_float("JARVIS_AUDIO_AGC_MAX_GAIN", 6.0))
        self._ns_gate_rms = max(0.0, _env_float("JARVIS_AUDIO_NS_GATE_RMS", 0.01))
        self._dynamic_ns_gate_rms: float | None = None
        self._aec = _get_aec_processor(self.sample_rate, self.frame_duration_ms)

    def is_speech(self, audio_frame: bytes) -> bool:
        """
        Check if an audio frame contains speech.

        Args:
            audio_frame: Raw 16-bit PCM audio bytes (mono)

        Returns:
            True if speech detected, False otherwise
        """
        if len(audio_frame) != self.bytes_per_frame:
            raise VADError(
                f"Frame must be {self.bytes_per_frame} bytes, got {len(audio_frame)}"
            )
        frame = self.preprocess_frame(audio_frame)
        return self.is_speech_preprocessed(frame)

    def preprocess_frame(self, audio_frame: bytes) -> bytes:
        return self._preprocess_frame(audio_frame)

    def is_speech_preprocessed(self, audio_frame: bytes) -> bool:
        if len(audio_frame) != self.bytes_per_frame:
            raise VADError(
                f"Frame must be {self.bytes_per_frame} bytes, got {len(audio_frame)}"
            )
        return self._vad.is_speech(audio_frame, self.sample_rate)

    def is_speech_numpy(self, audio_array: NDArrayFloat) -> bool:
        """
        Check if a numpy audio array contains speech.

        Args:
            audio_array: Numpy array of float32 audio samples (-1.0 to 1.0)

        Returns:
            True if speech detected, False otherwise
        """
        if np is None:
            raise VADError("numpy not installed")

        # Convert float32 to int16 bytes
        int16_data = (audio_array * 32767).astype(np.int16)
        audio_bytes = int16_data.tobytes()

        return self.is_speech(audio_bytes)

    def frames_from_audio(self, audio_bytes: bytes) -> Generator[bytes, None, None]:
        """
        Split audio bytes into frames suitable for VAD processing.

        Args:
            audio_bytes: Raw 16-bit PCM audio bytes

        Yields:
            Audio frames of correct size for VAD
        """
        offset = 0
        while offset + self.bytes_per_frame <= len(audio_bytes):
            yield audio_bytes[offset : offset + self.bytes_per_frame]
            offset += self.bytes_per_frame

    def _preprocess_frame(self, audio_frame: bytes) -> bytes:
        frame = audio_frame
        if self._aec is not None:
            frame = self._aec.process(frame)
        if not self._preprocess_enabled or np is None:
            return frame
        if not frame:
            return frame

        samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
        if samples.size == 0:
            return frame

        samples -= float(samples.mean())
        samples /= 32768.0
        rms = float(np.sqrt(np.mean(samples**2)) + 1e-8)

        gate_rms = self._ns_gate_rms
        if self._dynamic_ns_gate_rms is not None:
            gate_rms = max(gate_rms, self._dynamic_ns_gate_rms)
        if gate_rms > 0.0 and rms < gate_rms:
            return b"\x00" * len(frame)

        if self._agc_target_rms > 0.0:
            gain = min(self._agc_max_gain, self._agc_target_rms / rms)
            samples *= gain

        samples = np.clip(samples, -1.0, 1.0)
        return (samples * 32767.0).astype(np.int16).tobytes()

    def set_dynamic_ns_gate(self, rms: float | None) -> None:
        if rms is None or rms <= 0.0:
            self._dynamic_ns_gate_rms = None
        else:
            self._dynamic_ns_gate_rms = rms

    def disable_dynamic_ns_gate(self) -> None:
        self._dynamic_ns_gate_rms = None

    def detect_speech_segments(
        self,
        audio_bytes: bytes,
        padding_frames: int = 10,
        threshold_ratio: float = 0.9,
    ) -> list[tuple[int, int]]:
        """
        Detect speech segments in audio.

        Uses a ring buffer to smooth out detection and avoid choppy segments.

        Args:
            audio_bytes: Raw 16-bit PCM audio bytes
            padding_frames: Number of frames to buffer for smoothing
            threshold_ratio: Ratio of voiced frames needed to trigger speech

        Returns:
            List of (start_byte, end_byte) tuples for speech segments
        """
        segments = []
        ring_buffer = collections.deque(maxlen=padding_frames)
        triggered = False
        voiced_frames = []
        segment_start = 0

        frame_idx = 0
        for frame in self.frames_from_audio(audio_bytes):
            is_speech = self.is_speech(frame)
            ring_buffer.append((frame_idx, frame, is_speech))

            maxlen = ring_buffer.maxlen
            if maxlen is None:
                maxlen = len(ring_buffer)
            if not triggered:
                num_voiced = sum(1 for _, _, speech in ring_buffer if speech)
                if num_voiced > threshold_ratio * maxlen:
                    triggered = True
                    segment_start = ring_buffer[0][0] * self.bytes_per_frame
                    voiced_frames = [f for _, f, _ in ring_buffer]
            else:
                voiced_frames.append(frame)
                num_unvoiced = sum(1 for _, _, speech in ring_buffer if not speech)
                if num_unvoiced > threshold_ratio * maxlen:
                    triggered = False
                    segment_end = (frame_idx + 1) * self.bytes_per_frame
                    segments.append((segment_start, segment_end))
                    voiced_frames = []

            frame_idx += 1

        # Handle remaining speech at end
        if triggered and voiced_frames:
            segment_end = frame_idx * self.bytes_per_frame
            segments.append((segment_start, segment_end))

        return segments


class StreamingVAD:
    """
    Streaming VAD for real-time audio capture.

    Records audio until speech ends, using VAD to detect when to stop.
    """

    def __init__(
        self,
        aggressiveness: int | None = None,
        sample_rate: int = 16000,
        silence_duration_ms: int = 800,
        max_duration_s: int = 30,
        pre_roll_ms: int = 200,
        post_roll_ms: int = 200,
        device: int | None = None,
    ) -> None:
        if np is None:
            raise VADError("numpy required for streaming VAD")

        if aggressiveness is None:
            aggressiveness = resolve_vad_aggressiveness(2)

        self.vad = VoiceActivityDetector(
            aggressiveness=aggressiveness,
            sample_rate=sample_rate,
            frame_duration_ms=30,
        )
        self.sample_rate = sample_rate
        frame_ms = getattr(self.vad, "frame_duration_ms", 30)
        self.frame_ms = frame_ms
        self.silence_frames = max(1, int(silence_duration_ms / frame_ms))
        self.max_frames = max(1, int(max_duration_s * 1000 / frame_ms))
        self.pre_roll_frames = max(1, int(pre_roll_ms / frame_ms))
        self.post_roll_frames = max(0, int(post_roll_ms / frame_ms))
        self.device = device
        self._metrics_enabled = os.environ.get(
            "JARVIS_VAD_METRICS", ""
        ).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self._last_metrics: dict[str, float | None] = {
            "vad_ms": None,
            "endpoint_ms": None,
            "eos_perf_ts": None,
        }

    def _log_metrics(self, label: str, **values: object) -> None:
        if not self._metrics_enabled:
            return
        parts = [f"{key}={value}" for key, value in values.items()]
        print(f"[vad-metrics] {label} " + " ".join(parts))

    def get_last_metrics(self) -> dict[str, float | None]:
        return dict(self._last_metrics)

    def _process_frame(self, frame_bytes: bytes) -> bytes:
        if hasattr(self.vad, "preprocess_frame"):
            return self.vad.preprocess_frame(frame_bytes)
        return frame_bytes

    def _is_speech_processed(self, frame_bytes: bytes) -> bool:
        if hasattr(self.vad, "is_speech_preprocessed"):
            return self.vad.is_speech_preprocessed(frame_bytes)
        return self.vad.is_speech(frame_bytes)

    def record_until_silence(
        self,
        max_seconds: float | None = None,
        *,
        return_speech_flag: bool = False,
        empty_if_no_speech: bool = True,
    ) -> bytes | tuple[bytes, bool]:
        """
        Record audio until silence is detected after speech.

        Captures a small pre-roll (defaults to 200 ms) before the first speech frame
        so we do not chop the beginning of the command.
        """
        frame_size = self.vad.frame_size
        frame_events: list[tuple[bytes, bool]] = []
        silence_count = 0
        speech_detected = False
        frame_count = 0
        max_frames_limit = self.max_frames
        if max_seconds is not None:
            max_frames_limit = min(
                self.max_frames, max(1, int((max_seconds * 1000) / self.frame_ms))
            )
        adaptive_ns = _env_bool("JARVIS_AUDIO_NS_ADAPTIVE", False)
        adaptive_ms = max(0, _env_int("JARVIS_AUDIO_NS_ADAPTIVE_MS", 1000))
        adaptive_mult = max(0.0, _env_float("JARVIS_AUDIO_NS_ADAPTIVE_MULT", 2.0))
        rms_silence = max(0.0, _env_float("JARVIS_VAD_RMS_SILENCE", 0.0))
        adaptive_frames_limit = (
            max(1, int(adaptive_ms / self.frame_ms))
            if adaptive_ns and adaptive_ms
            else 0
        )
        noise_rms_sum = 0.0
        noise_rms_count = 0
        start_ts = time.perf_counter()
        stop_reason: str | None = None
        eos_perf_ts: float | None = None
        hard_timeout_s = (
            float(max_seconds)
            if max_seconds is not None
            else (max_frames_limit * self.frame_ms / 1000.0)
        )
        deadline_ts = start_ts + max(0.0, hard_timeout_s) + 0.5

        def callback(indata, frames, time_info, status):
            nonlocal silence_count, speech_detected, frame_count, noise_rms_sum, noise_rms_count, eos_perf_ts
            if np is None:
                return
            mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
            int16_data = (mono * 32767).astype(np.int16)

            for i in range(0, len(int16_data), frame_size):
                chunk = int16_data[i : i + frame_size]
                if len(chunk) == frame_size:
                    frame_bytes = chunk.tobytes()
                    processed = self._process_frame(frame_bytes)
                    is_speech = self._is_speech_processed(processed)
                    if rms_silence > 0.0 and _frame_rms(frame_bytes) < rms_silence:
                        is_speech = False
                    frame_events.append((processed, is_speech))

                    if is_speech:
                        speech_detected = True
                        silence_count = 0
                        if adaptive_ns:
                            self.vad.disable_dynamic_ns_gate()
                    elif speech_detected:
                        silence_count += 1
                        if (
                            eos_perf_ts is None
                            and silence_count >= self.silence_frames
                        ):
                            eos_perf_ts = time.perf_counter()
                    elif adaptive_ns and adaptive_frames_limit:
                        if noise_rms_count < adaptive_frames_limit:
                            noise_rms_sum += _frame_rms(frame_bytes)
                            noise_rms_count += 1
                            avg_rms = noise_rms_sum / max(1, noise_rms_count)
                            self.vad.set_dynamic_ns_gate(avg_rms * adaptive_mult)
                    frame_count += 1

        sd_module = _ensure_sounddevice()
        if sd_module is None:
            raise VADError("sounddevice not available; install PortAudio/ALSA")

        with sd_module.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=frame_size,
            device=self.device,
            callback=callback,
        ):
            while True:
                time.sleep(0.05)
                if time.perf_counter() >= deadline_ts:
                    stop_reason = "timeout"
                    break
                if speech_detected and silence_count >= self.silence_frames:
                    stop_reason = "silence"
                    break
                if frame_count >= max_frames_limit:
                    stop_reason = "max_frames"
                    break

        audio_bytes = self._assemble_frames(
            frame_events,
            self.pre_roll_frames,
            self.post_roll_frames,
            self.silence_frames,
            empty_if_no_speech=empty_if_no_speech,
        )

        duration_ms = (time.perf_counter() - start_ts) * 1000.0
        endpoint_ms: float | None = None
        if stop_reason == "silence" and speech_detected:
            endpoint_ms = float(silence_count * self.frame_ms)

        self._last_metrics = {
            "vad_ms": float(duration_ms),
            "endpoint_ms": endpoint_ms,
            "eos_perf_ts": eos_perf_ts,
        }

        speech_frames = sum(1 for _, is_speech in frame_events if is_speech)
        self._log_metrics(
            "streaming",
            frames=frame_count,
            speech_frames=speech_frames,
            duration_ms=int(duration_ms),
            speech=bool(speech_detected),
        )

        if return_speech_flag:
            return audio_bytes, bool(speech_detected)
        return audio_bytes

    @staticmethod
    def _assemble_frames(
        frame_events: list[tuple[bytes, bool]],
        pre_roll_frames: int,
        post_roll_frames: int,
        silence_frames: int,
        *,
        empty_if_no_speech: bool = True,
    ) -> bytes:
        pre_roll = collections.deque(maxlen=pre_roll_frames)
        result_frames: list[bytes] = []
        triggered = False
        silence_count = 0
        last_voiced_idx = 0

        for frame_bytes, is_speech in frame_events:
            if not triggered:
                if is_speech:
                    triggered = True
                    result_frames.extend(pre_roll)
                    pre_roll.clear()
                    result_frames.append(frame_bytes)
                    last_voiced_idx = len(result_frames)
                    silence_count = 0
                else:
                    pre_roll.append(frame_bytes)
                continue

            result_frames.append(frame_bytes)
            if is_speech:
                silence_count = 0
                last_voiced_idx = len(result_frames)
            else:
                silence_count += 1
            if silence_count >= silence_frames:
                break

        if not triggered:
            return b"" if empty_if_no_speech else b"".join(pre_roll)

        end_idx = min(len(result_frames), last_voiced_idx + post_roll_frames)
        return b"".join(result_frames[:end_idx])

    def record_fixed_duration(self, seconds: int = 5) -> tuple[bytes, bool]:
        """
        Record audio for a fixed duration.

        Args:
            seconds: Duration to record

        Returns:
            Tuple of (audio_bytes, speech_detected)
        """
        total_samples = int(seconds * self.sample_rate)

        start_ts = time.perf_counter()
        sd_module = _ensure_sounddevice()
        if sd_module is None:
            raise VADError("sounddevice not available; install PortAudio/ALSA")

        audio = sd_module.rec(
            total_samples,
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            device=self.device,
        )
        sd_module.wait()
        duration_ms = int((time.perf_counter() - start_ts) * 1000.0)

        # Convert to int16 bytes
        if np is None:
            raise RuntimeError("numpy not available")
        int16_data = (audio.flatten() * 32767).astype(np.int16)
        audio_bytes = int16_data.tobytes()

        analysis_start = time.perf_counter()
        processed_frames: list[bytes] = []
        speech_frames = 0
        total_frames = 0
        frame_bytes = getattr(self.vad, "bytes_per_frame", self.vad.frame_size * 2)
        for offset in range(0, len(audio_bytes), frame_bytes):
            frame = audio_bytes[offset : offset + frame_bytes]
            if len(frame) < frame_bytes:
                frame = frame + (b"\x00" * (frame_bytes - len(frame)))
            processed = self._process_frame(frame)
            processed_frames.append(processed)
            if self._is_speech_processed(processed):
                speech_frames += 1
            total_frames += 1
        analysis_ms = (time.perf_counter() - analysis_start) * 1000.0

        speech_detected = speech_frames > (total_frames * 0.1)  # 10% threshold
        if processed_frames:
            audio_bytes = b"".join(processed_frames)[: len(audio_bytes)]
        self._last_metrics = {
            "vad_ms": float(analysis_ms),
            "endpoint_ms": None,
        }
        self._log_metrics(
            "fixed",
            frames=total_frames,
            speech_frames=speech_frames,
            duration_ms=duration_ms,
            speech=bool(speech_detected),
        )

        return audio_bytes, speech_detected


def check_vad_available() -> bool:
    """Check if VAD dependencies are available."""
    return webrtcvad is not None and np is not None
