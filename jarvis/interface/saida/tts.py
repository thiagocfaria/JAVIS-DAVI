"""
Text-to-Speech module with Piper support.

Piper is a fast, local neural TTS engine with natural-sounding voices.
Falls back to espeak-ng if Piper is not available.
"""

from __future__ import annotations

import collections
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import audioop
from array import array
from pathlib import Path
from typing import Callable, Iterable, Optional, Protocol, cast

from jarvis.cerebro.config import Config


class _PiperChunk(Protocol):
    audio_int16_bytes: bytes


class _PiperVoice(Protocol):
    def synthesize(self, text: str) -> Iterable[_PiperChunk]: ...


def _env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float_optional(key: str) -> float | None:
    value = os.environ.get(key)
    if value is None or value == "":
        return None
    try:
        return float(value)
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


def _env_str(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.strip()


def _is_executable_file(path: Path) -> bool:
    try:
        return path.exists() and path.is_file() and os.access(path, os.X_OK)
    except OSError:
        return False


def _script_shebang_interpreter(path: Path) -> Path | None:
    try:
        with path.open("rb") as handle:
            line = handle.readline(200).decode("utf-8", errors="ignore").strip()
    except Exception:
        return None
    if not line.startswith("#!"):
        return None
    interpreter = line[2:].strip().split()[0] if line[2:].strip() else ""
    if not interpreter:
        return None
    return Path(interpreter)


class TextToSpeech:
    """
    Text-to-Speech engine with Piper support.

    Priority order:
    1. Piper (neural TTS, natural voice)
    2. espeak-ng (robotic but always available)
    3. No TTS (silent mode)
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._piper_available: bool | None = None
        self._piper_cmd: list[str] | None = None
        self._espeak_available: bool | None = None
        self._piper_model: str | None = _env_str("JARVIS_PIPER_MODEL")
        self._piper_backend = (
            (_env_str("JARVIS_PIPER_BACKEND", "auto") or "auto").strip().lower()
        )
        self._piper_intra_op_threads = max(0, _env_int("JARVIS_PIPER_INTRA_OP_THREADS", 0))
        self._piper_inter_op_threads = max(0, _env_int("JARVIS_PIPER_INTER_OP_THREADS", 0))
        self._piper_voice: _PiperVoice | None = None
        self._piper_voice_model_path: Path | None = None
        self._debug_enabled = _env_bool("JARVIS_DEBUG", False)
        self._speak_lock = threading.RLock()  # RLock permite reentrância para chunking
        self._last_tts_ms: float | None = None
        self._last_play_ms: float | None = None
        self._last_first_audio_ms: float | None = None
        self._last_first_audio_perf_ts: float | None = None
        self._last_first_speech_ms: float | None = None
        self._last_first_speech_perf_ts: float | None = None
        self._last_ack_ms: float | None = None
        self._last_ack_perf_ts: float | None = None
        self._last_ack_source: str | None = None
        self._last_engine: str | None = None
        self._engine_preference = (
            (_env_str("JARVIS_TTS_ENGINE", "auto") or "auto").strip().lower()
        )
        self._volume_override = _env_float_optional("JARVIS_TTS_VOLUME")
        self._warmup_enabled = _env_bool("JARVIS_TTS_WARMUP", False)
        self._warmup_blocking = _env_bool("JARVIS_TTS_WARMUP_BLOCKING", False)
        self._warmup_text = _env_str("JARVIS_TTS_WARMUP_TEXT", "ola") or "ola"
        self._cache_enabled = _env_bool("JARVIS_TTS_CACHE", False)
        self._cache_max_chars = max(0, _env_int("JARVIS_TTS_CACHE_MAX_CHARS", 120))
        self._cache_max_items = max(0, _env_int("JARVIS_TTS_CACHE_MAX_ITEMS", 32))
        self._chunking_enabled = _env_bool("JARVIS_TTS_CHUNKING", False)
        self._chunk_max_chars = max(40, _env_int("JARVIS_TTS_CHUNK_MAX_CHARS", 160))
        self._auto_chunk_long_text = _env_bool("JARVIS_TTS_AUTO_CHUNK_LONG_TEXT", False)
        self._auto_chunk_min_chars = max(
            80, _env_int("JARVIS_TTS_AUTO_CHUNK_MIN_CHARS", 240)
        )
        self._barge_in_enabled = _env_bool("JARVIS_TTS_BARGE_IN", False)
        default_stop = getattr(
            config, "stop_file_path", Path.home() / ".jarvis" / "STOP"
        )
        self._barge_in_stop_file = Path(
            _env_str("JARVIS_TTS_BARGE_IN_STOP_FILE", str(default_stop))
            or str(default_stop)
        )
        self._streaming_enabled = _env_bool("JARVIS_TTS_STREAMING", False)
        self._stream_chunk_bytes = max(
            512, _env_int("JARVIS_TTS_STREAM_CHUNK_BYTES", 4096)
        )
        self._ack_enabled = _env_bool("JARVIS_TTS_ACK_EARCON", False)
        self._ack_timeout_ms = max(0, _env_int("JARVIS_TTS_ACK_TIMEOUT_MS", 350))
        self._ack_duration_ms = max(0, _env_int("JARVIS_TTS_ACK_DURATION_MS", 120))
        self._ack_freq_hz = max(100, _env_int("JARVIS_TTS_ACK_FREQ_HZ", 880))
        self._ack_volume = float(_env_int("JARVIS_TTS_ACK_VOLUME", 20)) / 100.0
        if self._ack_volume < 0.0:
            self._ack_volume = 0.0
        if self._ack_volume > 1.0:
            self._ack_volume = 1.0
        self._earcon_raw: bytes | None = None
        self._ack_phrase = _env_str("JARVIS_TTS_ACK_PHRASE")
        self._ack_phrase_raw: bytes | None = None
        if self._ack_phrase:
            self._ack_enabled = True
        self._aplay_device = _env_str("JARVIS_TTS_AUDIO_DEVICE")
        self._word_timing_enabled = _env_bool("JARVIS_TTS_WORD_TIMING", False)
        self._word_timing_wpm = max(60, _env_int("JARVIS_TTS_WPM", 150))
        self._last_word_timings: list[dict[str, float | str]] | None = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._pause_buffer: "collections.deque[bytes]" = collections.deque()
        self._pause_buffer_bytes = 0
        self._pause_max_bytes = max(
            0, _env_int("JARVIS_TTS_PAUSE_MAX_BYTES", 22050 * 2 * 3)
        )
        self._active_piper_proc: subprocess.Popen | None = None
        self._active_aplay_proc: subprocess.Popen | None = None
        self._cache: "collections.OrderedDict[str, bytes]" = collections.OrderedDict()
        if self._volume_override is None:
            self._volume = 1.0
            self._volume_is_default = True
        else:
            self._volume = self._clamp_volume(self._volume_override)
            self._volume_is_default = False

        piper_models_env = _env_str("JARVIS_PIPER_MODELS_DIR")
        if piper_models_env:
            self._piper_models_dir = Path(piper_models_env)
        else:
            repo_models_dir = Path(__file__).resolve().parents[3] / "storage/models/piper"
            if repo_models_dir.exists():
                self._piper_models_dir = repo_models_dir
            else:
                self._piper_models_dir = Path.home() / ".local/share/piper-models"

        # Default Portuguese Brazilian voice
        self._default_voice = os.environ.get("JARVIS_PIPER_VOICE", "pt_BR-faber-medium")
        if self._warmup_enabled and self._warmup_blocking:
            self._warmup()
        elif self._warmup_enabled:
            threading.Thread(target=self._warmup, daemon=True).start()
        if self._ack_phrase and self._ack_timeout_ms > 0:
            warm_phrase = _env_bool("JARVIS_TTS_ACK_PHRASE_WARMUP", True)
            if warm_phrase:
                if _env_bool("JARVIS_TTS_ACK_PHRASE_WARMUP_BLOCKING", False):
                    self._ack_phrase_raw = self._synthesize_piper_raw(self._ack_phrase)
                else:
                    threading.Thread(target=self._warmup_ack_phrase, daemon=True).start()

    def _debug(self, message: str) -> None:
        if self._debug_enabled:
            print(f"[tts] {message}")

    def _lock_is_held(self) -> bool:
        locked = getattr(self._speak_lock, "locked", None)
        if callable(locked):
            return bool(locked())
        return False

    @staticmethod
    def _clamp_volume(volume: float) -> float:
        if volume < 0.0:
            return 0.0
        if volume > 2.0:
            return 2.0
        return volume

    def _scale_audio(self, audio_bytes: bytes) -> bytes:
        if not audio_bytes or self._volume == 1.0:
            return audio_bytes
        try:
            return audioop.mul(audio_bytes, 2, float(self._volume))
        except Exception:
            return audio_bytes

    def _prepare_audio(self, audio_bytes: bytes, sample_rate: int) -> bytes:
        if not audio_bytes:
            return audio_bytes
        trimmed = self._trim_silence(audio_bytes, sample_rate)
        return self._apply_fade(trimmed, sample_rate)

    def _trim_silence(self, audio_bytes: bytes, sample_rate: int) -> bytes:
        if not _env_bool("JARVIS_TTS_TRIM_SILENCE", False):
            return audio_bytes
        threshold = max(0, _env_int("JARVIS_TTS_TRIM_THRESHOLD", 200))
        frame_ms = max(5, _env_int("JARVIS_TTS_TRIM_FRAME_MS", 20))
        frame_bytes = int(sample_rate * frame_ms / 1000) * 2
        if frame_bytes <= 0 or len(audio_bytes) <= frame_bytes:
            return audio_bytes
        start = 0
        end = len(audio_bytes)
        while start + frame_bytes < end:
            if audioop.rms(audio_bytes[start : start + frame_bytes], 2) > threshold:
                break
            start += frame_bytes
        while end - frame_bytes > start:
            if audioop.rms(audio_bytes[end - frame_bytes : end], 2) > threshold:
                break
            end -= frame_bytes
        return audio_bytes[start:end] if start < end else audio_bytes

    def _apply_fade(self, audio_bytes: bytes, sample_rate: int) -> bytes:
        fade_ms = max(0, _env_int("JARVIS_TTS_FADE_MS", 0))
        if fade_ms <= 0 or not audio_bytes:
            return audio_bytes
        samples = array("h")
        try:
            samples.frombytes(audio_bytes)
        except Exception:
            return audio_bytes
        fade_samples = int(sample_rate * fade_ms / 1000)
        fade_samples = min(fade_samples, len(samples) // 2)
        if fade_samples <= 0:
            return audio_bytes
        for i in range(fade_samples):
            scale = i / float(fade_samples)
            samples[i] = int(samples[i] * scale)
            samples[-(i + 1)] = int(samples[-(i + 1)] * scale)
        return samples.tobytes()

    def _espeak_amplitude(self) -> int | None:
        if self._volume_is_default:
            return None
        amplitude = int(self._volume * 100)
        if amplitude < 0:
            amplitude = 0
        if amplitude > 200:
            amplitude = 200
        return amplitude

    def _build_aplay_cmd(self, sample_rate: int) -> list[str]:
        cmd = ["aplay"]
        if self._aplay_device:
            cmd.extend(["-D", self._aplay_device])
        cmd.extend(["-r", str(sample_rate), "-f", "S16_LE", "-t", "raw", "-"])
        return cmd

    def _estimate_word_timings(
        self, text: str, *, offset_ms: float = 0.0
    ) -> tuple[list[dict[str, float | str]], float]:
        words = re.findall(r"\w+", text, flags=re.UNICODE)
        if not words:
            return [], 0.0
        per_word_ms = 60000.0 / float(self._word_timing_wpm)
        timings: list[dict[str, float | str]] = []
        for idx, word in enumerate(words):
            start_ms = offset_ms + (idx * per_word_ms)
            timings.append(
                {"word": word, "start_ms": start_ms, "end_ms": start_ms + per_word_ms}
            )
        return timings, len(words) * per_word_ms

    def speak(
        self, text: str, on_audio_chunk: Callable[[bytes], None] | None = None
    ) -> None:
        """
        Speak the given text.

        Tries Piper first, falls back to espeak-ng.
        """
        self._stop_event.clear()
        self._pause_event.set()
        self._pause_buffer.clear()
        self._pause_buffer_bytes = 0
        if self.config.tts_mode == "none":
            self._last_tts_ms = None
            self._last_play_ms = None
            self._last_first_audio_ms = None
            self._last_word_timings = None
            return

        if self._word_timing_enabled:
            self._last_word_timings, _ = self._estimate_word_timings(text)
        else:
            self._last_word_timings = None

        if not text or not text.strip():
            self._last_tts_ms = None
            self._last_play_ms = None
            self._last_first_audio_ms = None
            return

        cleaned = text.strip()
        auto_chunk = (
            self._auto_chunk_long_text
            and not self._chunking_enabled
            and len(cleaned) >= self._auto_chunk_min_chars
        )
        if self._chunking_enabled or auto_chunk:
            chunks = self._split_chunks(text)
            tts_total_ms = 0.0
            play_total_ms = 0.0
            tts_any = False
            play_any = False
            first_audio_ms: float | None = None
            first_audio_perf_ts: float | None = None
            first_speech_ms: float | None = None
            first_speech_perf_ts: float | None = None
            ack_ms: float | None = None
            ack_perf_ts: float | None = None
            ack_source: str | None = None
            engine: str | None = None

            # Proteger todo o loop de chunks com lock para evitar race conditions
            with self._speak_lock:
                for chunk in chunks:
                    if not chunk:
                        continue
                    if self._should_stop_playback():
                        return
                    # _speak_once já tem seu próprio lock, mas manter o lock externo
                    # garante que chunks não sejam intercalados entre chamadas
                    self._speak_once(chunk, on_audio_chunk=on_audio_chunk)

                    if self._last_tts_ms is not None:
                        tts_total_ms += float(self._last_tts_ms)
                        tts_any = True
                    if self._last_play_ms is not None:
                        play_total_ms += float(self._last_play_ms)
                        play_any = True
                    if first_audio_perf_ts is None and self._last_first_audio_perf_ts is not None:
                        first_audio_ms = self._last_first_audio_ms
                        first_audio_perf_ts = self._last_first_audio_perf_ts
                    if first_speech_perf_ts is None and self._last_first_speech_perf_ts is not None:
                        first_speech_ms = self._last_first_speech_ms
                        first_speech_perf_ts = self._last_first_speech_perf_ts
                    if ack_perf_ts is None and self._last_ack_perf_ts is not None:
                        ack_ms = self._last_ack_ms
                        ack_perf_ts = self._last_ack_perf_ts
                        ack_source = self._last_ack_source
                    if engine is None and self._last_engine is not None:
                        engine = self._last_engine

            self._last_tts_ms = tts_total_ms if tts_any else None
            self._last_play_ms = play_total_ms if play_any else None
            self._last_first_audio_ms = first_audio_ms
            self._last_first_audio_perf_ts = first_audio_perf_ts
            self._last_first_speech_ms = first_speech_ms
            self._last_first_speech_perf_ts = first_speech_perf_ts
            self._last_ack_ms = ack_ms
            self._last_ack_perf_ts = ack_perf_ts
            self._last_ack_source = ack_source
            self._last_engine = engine
            return

        self._speak_once(text, on_audio_chunk=on_audio_chunk)

    def speak_stream(
        self, chunks, on_audio_chunk: Callable[[bytes], None] | None = None
    ) -> None:
        """
        Speak text in partes (streaming de texto).

        Cada chunk eh falado assim que chega, mantendo ordem e baixa latencia.
        """
        if self.config.tts_mode == "none":
            return
        self._stop_event.clear()
        self._pause_event.set()
        self._pause_buffer.clear()
        self._pause_buffer_bytes = 0
        offset_ms = 0.0
        timings: list[dict[str, float | str]] = []
        with self._speak_lock:
            for chunk in chunks:
                if not chunk:
                    continue
                if self._should_stop_playback():
                    break
                chunk_text = str(chunk)
                if self._word_timing_enabled:
                    chunk_timings, duration_ms = self._estimate_word_timings(
                        chunk_text, offset_ms=offset_ms
                    )
                    if chunk_timings:
                        timings.extend(chunk_timings)
                    offset_ms += duration_ms
                self._speak_once(chunk_text, on_audio_chunk=on_audio_chunk)
        if self._word_timing_enabled:
            self._last_word_timings = timings
        else:
            self._last_word_timings = None

    def pause(self) -> None:
        self._pause_event.clear()

    def resume(self) -> None:
        self._pause_event.set()

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.set()
        self._terminate_process(self._active_piper_proc)
        self._terminate_process(self._active_aplay_proc)
        self._active_piper_proc = None
        self._active_aplay_proc = None

    def _speak_once(
        self, text: str, on_audio_chunk: Callable[[bytes], None] | None = None
    ) -> None:
        self._last_tts_ms = None
        self._last_play_ms = None
        self._last_first_audio_ms = None
        self._last_first_audio_perf_ts = None
        self._last_first_speech_ms = None
        self._last_first_speech_perf_ts = None
        self._last_ack_ms = None
        self._last_ack_perf_ts = None
        self._last_ack_source = None
        self._last_engine = None

        with self._speak_lock:
            pref = self._engine_preference
            if pref in {"espeak", "espeak-ng"}:
                self._speak_espeak(text)
                return

            if pref == "piper":
                if self._try_piper(text, on_audio_chunk=on_audio_chunk):
                    self._last_engine = "piper"
                    return
                strict = _env_bool("JARVIS_TTS_ENGINE_STRICT", False)
                if strict:
                    self._debug("JARVIS_TTS_ENGINE=piper (strict) mas piper indisponivel")
                    self._last_engine = "none"
                    return
                self._debug("JARVIS_TTS_ENGINE=piper mas piper indisponivel; usando espeak-ng")
                self._speak_espeak(text)
                return

            # auto: Try Piper first, fallback to espeak-ng
            if self._try_piper(text, on_audio_chunk=on_audio_chunk):
                self._last_engine = "piper"
                return

            self._debug("piper indisponivel; usando espeak-ng")
            self._speak_espeak(text)

    def _split_chunks(self, text: str) -> list[str]:
        cleaned = text.strip()
        if len(cleaned) <= self._chunk_max_chars:
            return [cleaned]
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            if not sentence:
                continue
            if not current:
                current = sentence
                continue
            if len(current) + 1 + len(sentence) <= self._chunk_max_chars:
                current = f"{current} {sentence}"
                continue
            chunks.append(current)
            current = sentence
        if current:
            chunks.append(current)
        return chunks

    def _should_stop_playback(self) -> bool:
        if self._stop_event.is_set():
            return True
        if not self._barge_in_enabled:
            return False
        try:
            return self._barge_in_stop_file.exists()
        except Exception:
            return False

    def _start_barge_in_listener(self) -> Callable[[], None] | None:
        """
        Start a lightweight VAD listener to trigger barge-in during TTS playback.

        Uses webrtcvad on mic input (16 kHz mono) and sets the internal stop_event
        as soon as speech is detected.
        """
        if not self._barge_in_enabled:
            return None
        try:
            import numpy as np  # type: ignore
            import sounddevice as sd  # type: ignore
            import webrtcvad  # type: ignore
        except Exception:
            return None

        try:
            aggressiveness = int(
                os.environ.get("JARVIS_TTS_BARGE_IN_AGGR", "2").strip() or "2"
            )
        except Exception:
            aggressiveness = 2
        aggressiveness = max(0, min(3, aggressiveness))
        try:
            vad = webrtcvad.Vad(aggressiveness)
        except Exception:
            return None

        sample_rate = 16000
        frame_ms = 30
        frame_samples = int(sample_rate * frame_ms / 1000)
        stop_flag = threading.Event()

        def callback(indata, frames, time_info, status):  # type: ignore[override]
            if self._stop_event.is_set() or stop_flag.is_set():
                raise sd.CallbackStop  # type: ignore[misc]
            try:
                mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
                int16_data = (mono * 32767.0).astype(np.int16)
                for i in range(0, len(int16_data), frame_samples):
                    frame = int16_data[i : i + frame_samples]
                    if frame.size != frame_samples:
                        continue
                    if vad.is_speech(frame.tobytes(), sample_rate):
                        self._stop_event.set()
                        raise sd.CallbackStop  # type: ignore[misc]
            except Exception:
                return

        def runner() -> None:
            try:
                with sd.InputStream(
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=frame_samples,
                    callback=callback,
                ):
                    while not stop_flag.is_set() and not self._stop_event.is_set():
                        time.sleep(0.02)
            except Exception:
                return

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()

        def stopper() -> None:
            stop_flag.set()
            try:
                thread.join(timeout=0.5)
            except Exception:
                pass

        return stopper

    def _terminate_process(self, proc: subprocess.Popen | None) -> None:
        if proc is None:
            return
        try:
            proc.terminate()
        except Exception:
            return
        try:
            proc.wait(timeout=1)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def _stream_piper_audio(
        self,
        text: str,
        piper_cmd: list[str],
        aplay_cmd: list[str],
        *,
        aec_enabled: bool,
        aec_module: Optional[object],
        use_cache: bool,
        on_audio_chunk: Callable[[bytes], None] | None = None,
    ) -> bool:
        # Clear previous stop flag before playback.
        self._stop_event.clear()
        barge_in_stop = self._start_barge_in_listener() if self._barge_in_enabled else None
        tts_start = time.perf_counter()
        piper_proc = subprocess.Popen(
            piper_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if piper_proc.stdin is not None:
            piper_proc.stdin.write(text.encode("utf-8"))
            piper_proc.stdin.close()

        if self._volume <= 0.0:
            aplay_proc = None
        else:
            aplay_proc = subprocess.Popen(
                aplay_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        self._active_piper_proc = piper_proc
        self._active_aplay_proc = aplay_proc

        first_audio_ts: float | None = None
        first_speech_ts: float | None = None
        ack_written = threading.Event()
        speech_started = threading.Event()
        cache_buffer: bytearray | None = bytearray() if use_cache else None
        interrupted = False
        exception_occurred = False

        if self._ack_enabled and self._ack_timeout_ms > 0:
            def _ack_worker() -> None:
                try:
                    time.sleep(self._ack_timeout_ms / 1000.0)
                    if (
                        ack_written.is_set()
                        or speech_started.is_set()
                        or self._stop_event.is_set()
                    ):
                        return
                    ack_ts = time.perf_counter()
                    self._last_ack_perf_ts = ack_ts
                    self._last_ack_ms = (ack_ts - tts_start) * 1000.0
                    phrase_raw = self._ack_phrase_raw
                    if phrase_raw:
                        self._last_ack_source = "phrase"
                    else:
                        self._last_ack_source = "earcon"
                    ack_written.set()
                    if aplay_proc is None or aplay_proc.stdin is None:
                        return
                    if phrase_raw:
                        try:
                            aplay_proc.stdin.write(phrase_raw)
                        except Exception:
                            return
                    else:
                        if self._ack_duration_ms <= 0:
                            return
                        earcon = self._get_earcon_raw(sample_rate=22050)
                        if not earcon:
                            return
                        try:
                            aplay_proc.stdin.write(earcon)
                        except Exception:
                            return
                except Exception:
                    return

            threading.Thread(target=_ack_worker, daemon=True).start()

        try:
            if piper_proc.stdout is None:
                return False

            def _write_audio(raw: bytes) -> None:
                if self._volume <= 0.0:
                    return
                scaled = self._scale_audio(raw)
                if not scaled:
                    return
                if aec_enabled and aec_module is not None:
                    push_fn = getattr(aec_module, "push_playback_reference", None)
                    if callable(push_fn):
                        try:
                            push_fn(scaled, 22050)
                        except Exception:
                            pass
                if aplay_proc is not None and aplay_proc.stdin is not None:
                    aplay_proc.stdin.write(scaled)
                if on_audio_chunk is not None:
                    try:
                        on_audio_chunk(scaled)
                    except Exception:
                        pass

            while True:
                chunk = piper_proc.stdout.read(self._stream_chunk_bytes)
                if not chunk:
                    break
                if cache_buffer is not None:
                    cache_buffer.extend(chunk)
                if first_speech_ts is None:
                    first_speech_ts = time.perf_counter()
                    self._last_first_speech_perf_ts = first_speech_ts
                    speech_started.set()
                if first_audio_ts is None:
                    first_audio_ts = first_speech_ts or time.perf_counter()
                    self._last_first_audio_perf_ts = first_audio_ts
                if not self._pause_event.is_set():
                    self._pause_buffer.append(chunk)
                    self._pause_buffer_bytes += len(chunk)
                    while (
                        self._pause_max_bytes
                        and self._pause_buffer_bytes > self._pause_max_bytes
                        and self._pause_buffer
                    ):
                        dropped = self._pause_buffer.popleft()
                        self._pause_buffer_bytes -= len(dropped)
                    time.sleep(0.01)
                    continue
                while self._pause_buffer:
                    buffered = self._pause_buffer.popleft()
                    self._pause_buffer_bytes -= len(buffered)
                    _write_audio(buffered)
                _write_audio(chunk)
                if self._should_stop_playback():
                    interrupted = True
                    self._terminate_process(piper_proc)
                    self._terminate_process(aplay_proc)
                    self._last_tts_ms = (time.perf_counter() - tts_start) * 1000.0
                    self._last_play_ms = None
                    if first_audio_ts is not None:
                        self._last_first_audio_ms = (
                            first_audio_ts - tts_start
                        ) * 1000.0
                    return True
        except Exception:
            exception_occurred = True
            # Terminar processos antes de relançar exceção
            self._terminate_process(piper_proc)
            self._terminate_process(aplay_proc)
            raise
        finally:
            # Fechar stdin apenas se não foi interrompido e não houve exceção
            if not interrupted and not exception_occurred:
                if aplay_proc is not None and aplay_proc.stdin is not None:
                    try:
                        aplay_proc.stdin.close()
                    except Exception:
                        pass
            if self._active_piper_proc is piper_proc:
                self._active_piper_proc = None
            if self._active_aplay_proc is aplay_proc:
                self._active_aplay_proc = None
            if barge_in_stop:
                try:
                    barge_in_stop()
                except Exception:
                    pass

        if interrupted or exception_occurred:
            return True

        piper_rc = piper_proc.wait(timeout=30)
        self._last_tts_ms = (time.perf_counter() - tts_start) * 1000.0
        if piper_rc != 0:
            self._debug(f"piper retornou codigo {piper_rc}")

        if first_audio_ts is not None:
            self._last_first_audio_ms = (first_audio_ts - tts_start) * 1000.0
            self._last_first_audio_perf_ts = first_audio_ts
        if first_speech_ts is not None:
            self._last_first_speech_ms = (first_speech_ts - tts_start) * 1000.0
            self._last_first_speech_perf_ts = first_speech_ts
        if cache_buffer is not None and cache_buffer:
            self._cache_put(text, bytes(cache_buffer))

        if aplay_proc is None:
            self._last_play_ms = None
            return True

        play_start = time.perf_counter()
        aplay_rc = aplay_proc.wait(timeout=30)
        self._last_play_ms = (time.perf_counter() - play_start) * 1000.0
        if aplay_rc != 0:
            self._debug(f"aplay retornou codigo {aplay_rc}")
        return True

    def _find_piper_binary(self) -> str | None:
        """Find a runnable Piper command.

        Notes:
        - Em ambientes onde o repo/venv foi movido, o script `.venv/bin/piper` pode ter
          shebang quebrado. Nesse caso, usamos `python -m piper`.
        """
        override = _env_str("JARVIS_PIPER_BIN")
        if override:
            path = Path(override)
            if _is_executable_file(path):
                return str(path)

        # PATH first
        piper_path = shutil.which("piper")
        if piper_path and _is_executable_file(Path(piper_path)):
            return piper_path

        # Venv script (pode ter shebang quebrado em venv movida)
        venv_candidate = Path(sys.executable).parent / "piper"
        if venv_candidate.exists() and venv_candidate.is_file():
            interpreter = _script_shebang_interpreter(venv_candidate)
            if interpreter is not None and _is_executable_file(interpreter):
                if _is_executable_file(venv_candidate):
                    return str(venv_candidate)
            # Shebang quebrado: preferir `python -m piper` (o módulo está na venv)
            return None

        return None

    def _ensure_piper_cmd(self) -> list[str] | None:
        if self._piper_cmd is not None:
            return self._piper_cmd

        binary = self._find_piper_binary()
        if binary:
            self._piper_cmd = [binary]
            return self._piper_cmd

        # Fallback: python -m piper (funciona mesmo com shebang quebrado)
        try:
            import importlib.util

            if importlib.util.find_spec("piper") is None:
                self._piper_cmd = None
                return None
        except Exception:
            self._piper_cmd = None
            return None

        self._piper_cmd = [sys.executable, "-m", "piper"]
        return self._piper_cmd

        # Check common installation locations
        common_paths = [
            Path.home() / ".local/bin/piper",
            Path("/usr/local/bin/piper"),
            Path("/usr/bin/piper"),
            Path.home() / "bin/piper",
        ]

        for path in common_paths:
            if path.exists() and path.is_file() and os.access(path, os.X_OK):
                return str(path)

        return None

    def _piper_python_available(self) -> bool:
        try:
            import importlib.util

            return importlib.util.find_spec("piper.voice") is not None
        except Exception:
            return False

    def _ensure_piper_voice(self, model_path: Path) -> _PiperVoice | None:
        if (
            self._piper_voice is not None
            and self._piper_voice_model_path is not None
            and self._piper_voice_model_path == model_path
        ):
            return self._piper_voice

        if not self._piper_python_available():
            return None

        try:
            import onnxruntime
            from piper.config import PiperConfig
            from piper.voice import PiperVoice

            try:
                from piper.phonemize_espeak import ESPEAK_DATA_DIR
            except Exception:
                from piper.voice import ESPEAK_DATA_DIR  # type: ignore[attr-defined]

            config_path = Path(f"{model_path}.json")
            with config_path.open("r", encoding="utf-8") as handle:
                config_dict = json.load(handle)

            sess_options = onnxruntime.SessionOptions()
            if self._piper_intra_op_threads > 0:
                sess_options.intra_op_num_threads = int(self._piper_intra_op_threads)
            if self._piper_inter_op_threads > 0:
                sess_options.inter_op_num_threads = int(self._piper_inter_op_threads)

            voice = PiperVoice(
                session=onnxruntime.InferenceSession(
                    str(model_path),
                    sess_options=sess_options,
                    providers=["CPUExecutionProvider"],
                ),
                config=PiperConfig.from_dict(config_dict),
                espeak_data_dir=Path(ESPEAK_DATA_DIR),
            )
        except Exception as exc:
            self._debug(f"piper python backend falhou ao carregar modelo: {exc}")
            return None

        self._piper_voice = cast(_PiperVoice, voice)
        self._piper_voice_model_path = model_path
        return self._piper_voice

    def _stream_piper_voice_audio(
        self,
        text: str,
        model_path: Path,
        aplay_cmd: list[str],
        *,
        aec_enabled: bool,
        aec_module: Optional[object],
        use_cache: bool,
        on_audio_chunk: Callable[[bytes], None] | None = None,
    ) -> bool:
        tts_start = time.perf_counter()
        voice = self._ensure_piper_voice(model_path)
        if voice is None:
            return False

        if self._volume <= 0.0:
            aplay_proc = None
        else:
            aplay_proc = subprocess.Popen(
                aplay_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        self._active_piper_proc = None
        self._active_aplay_proc = aplay_proc

        first_audio_ts: float | None = None
        first_speech_ts: float | None = None
        ack_written = threading.Event()
        speech_started = threading.Event()
        cache_buffer: bytearray | None = bytearray() if use_cache else None
        interrupted = False
        exception_occurred = False

        if self._ack_enabled and self._ack_timeout_ms > 0:

            def _ack_worker() -> None:
                try:
                    time.sleep(self._ack_timeout_ms / 1000.0)
                    if (
                        ack_written.is_set()
                        or speech_started.is_set()
                        or self._stop_event.is_set()
                    ):
                        return
                    ack_ts = time.perf_counter()
                    self._last_ack_perf_ts = ack_ts
                    self._last_ack_ms = (ack_ts - tts_start) * 1000.0
                    phrase_raw = self._ack_phrase_raw
                    if phrase_raw:
                        self._last_ack_source = "phrase"
                    else:
                        self._last_ack_source = "earcon"
                    ack_written.set()
                    if aplay_proc is None or aplay_proc.stdin is None:
                        return
                    if phrase_raw:
                        try:
                            aplay_proc.stdin.write(phrase_raw)
                        except Exception:
                            return
                    else:
                        if self._ack_duration_ms <= 0:
                            return
                        earcon = self._get_earcon_raw(sample_rate=22050)
                        if not earcon:
                            return
                        try:
                            aplay_proc.stdin.write(earcon)
                        except Exception:
                            return
                except Exception:
                    return

            threading.Thread(target=_ack_worker, daemon=True).start()

        try:
            def _write_audio(raw: bytes) -> None:
                if self._volume <= 0.0:
                    return
                scaled = self._scale_audio(raw)
                if not scaled:
                    return
                if aec_enabled and aec_module is not None:
                    push_fn = getattr(aec_module, "push_playback_reference", None)
                    if callable(push_fn):
                        try:
                            push_fn(scaled, 22050)
                        except Exception:
                            pass
                if aplay_proc is not None and aplay_proc.stdin is not None:
                    aplay_proc.stdin.write(scaled)
                if on_audio_chunk is not None:
                    try:
                        on_audio_chunk(scaled)
                    except Exception:
                        pass

            for audio_chunk in voice.synthesize(text):
                if self._should_stop_playback():
                    interrupted = True
                    break
                raw = getattr(audio_chunk, "audio_int16_bytes", b"")
                if not raw:
                    continue
                if cache_buffer is not None:
                    cache_buffer.extend(raw)
                if first_speech_ts is None:
                    first_speech_ts = time.perf_counter()
                    self._last_first_speech_perf_ts = first_speech_ts
                    speech_started.set()
                if first_audio_ts is None:
                    first_audio_ts = first_speech_ts or time.perf_counter()
                    self._last_first_audio_perf_ts = first_audio_ts
                if not self._pause_event.is_set():
                    self._pause_buffer.append(raw)
                    self._pause_buffer_bytes += len(raw)
                    while (
                        self._pause_max_bytes
                        and self._pause_buffer_bytes > self._pause_max_bytes
                        and self._pause_buffer
                    ):
                        dropped = self._pause_buffer.popleft()
                        self._pause_buffer_bytes -= len(dropped)
                    time.sleep(0.01)
                    continue
                while self._pause_buffer:
                    buffered = self._pause_buffer.popleft()
                    self._pause_buffer_bytes -= len(buffered)
                    _write_audio(buffered)
                _write_audio(raw)

            if interrupted:
                if aplay_proc is not None:
                    self._terminate_process(aplay_proc)
                self._last_tts_ms = (time.perf_counter() - tts_start) * 1000.0
                self._last_play_ms = None
                if first_audio_ts is not None:
                    self._last_first_audio_ms = (first_audio_ts - tts_start) * 1000.0
                return True
        except Exception:
            exception_occurred = True
            self._terminate_process(aplay_proc)
            raise
        finally:
            if not interrupted and not exception_occurred:
                if aplay_proc is not None and aplay_proc.stdin is not None:
                    try:
                        aplay_proc.stdin.close()
                    except Exception:
                        pass
            if self._active_aplay_proc is aplay_proc:
                self._active_aplay_proc = None

        if interrupted or exception_occurred:
            return True

        self._last_tts_ms = (time.perf_counter() - tts_start) * 1000.0
        if first_audio_ts is not None:
            self._last_first_audio_ms = (first_audio_ts - tts_start) * 1000.0
            self._last_first_audio_perf_ts = first_audio_ts
        if first_speech_ts is not None:
            self._last_first_speech_ms = (first_speech_ts - tts_start) * 1000.0
            self._last_first_speech_perf_ts = first_speech_ts
        if cache_buffer is not None and cache_buffer:
            self._cache_put(text, bytes(cache_buffer))

        if aplay_proc is None:
            self._last_play_ms = None
            return True

        play_start = time.perf_counter()
        aplay_rc = aplay_proc.wait(timeout=30)
        self._last_play_ms = (time.perf_counter() - play_start) * 1000.0
        if aplay_rc != 0:
            self._debug(f"aplay retornou codigo {aplay_rc}")
        return True

    def _try_piper(
        self, text: str, on_audio_chunk: Callable[[bytes], None] | None = None
    ) -> bool:
        """
        Try to speak using Piper TTS.

        Returns True if successful, False to fallback.
        """
        if self._piper_available is False:
            if self._debug_enabled:
                self._debug("Piper marcado como indisponivel (fallback anterior)")
            return False

        # Check if piper is installed
        if self._piper_available is None:
            self._piper_cmd = self._ensure_piper_cmd()
            self._piper_available = (self._piper_cmd is not None) or self._piper_python_available()
            if not self._piper_available:
                if self._debug_enabled:
                    self._debug("Piper nao encontrado no sistema (usando espeak-ng)")
                return False

        # Find model file
        model_path = self._find_piper_model()
        if model_path is None:
            self._piper_available = False
            if self._debug_enabled:
                self._debug(
                    f"Modelo Piper nao encontrado (procurou em {self._piper_models_dir}, "
                    f"~/.local/share/piper, /usr/share/piper-voices). Usando espeak-ng"
                )
            return False

        aec_module = None
        aec_enabled = False
        try:
            from jarvis.interface.entrada import vad as vad_module

            aec_enabled = vad_module.is_aec_enabled()
            aec_module = vad_module
        except Exception:
            aec_enabled = False

        try:
            aplay_cmd = self._build_aplay_cmd(22050)

            use_cache = (
                self._cache_enabled
                and self._cache_max_chars > 0
                and len(text.strip()) <= self._cache_max_chars
            )
            # Se cache hit: tocar direto (independente do backend)
            if use_cache:
                cached = self._cache_get(text)
                if cached is not None:
                    first_audio_ts = time.perf_counter()
                    self._last_tts_ms = 0.0
                    self._last_play_ms = None
                    self._last_first_audio_ms = 0.0
                    self._last_first_audio_perf_ts = first_audio_ts
                    self._last_first_speech_ms = 0.0
                    self._last_first_speech_perf_ts = first_audio_ts
                    self._last_engine = "piper"
                    self._last_ack_ms = None
                    self._last_ack_perf_ts = None
                    self._last_ack_source = "cache"
                    if self._volume <= 0.0:
                        return True
                    return self._play_raw_audio(
                        cached,
                        aplay_cmd,
                        aec_enabled,
                        aec_module,
                        sample_rate=22050,
                        on_audio_chunk=on_audio_chunk,
                    )

            backend = (self._piper_backend or "auto").strip().lower()
            prefer_python = backend in {"auto", "python", "py"}
            prefer_cli = backend in {"cli", "bin", "binary"}
            if prefer_python and not prefer_cli:
                ok = self._stream_piper_voice_audio(
                    text,
                    model_path,
                    aplay_cmd,
                    aec_enabled=aec_enabled,
                    aec_module=aec_module,
                    use_cache=use_cache,
                    on_audio_chunk=on_audio_chunk,
                )
                if ok:
                    return True

            # Fallback: CLI (piper | aplay)
            piper_cmd_prefix = self._ensure_piper_cmd()
            if piper_cmd_prefix is None:
                if self._debug_enabled:
                    self._debug("Piper indisponivel (comando nao resolvido)")
                return False
            piper_cmd = [
                *piper_cmd_prefix,
                "--model",
                str(model_path),
                "--output-raw",
            ]
            streaming_playback = self._streaming_enabled or self._barge_in_enabled
            if streaming_playback:
                return self._stream_piper_audio(
                    text,
                    piper_cmd,
                    aplay_cmd,
                    aec_enabled=aec_enabled,
                    aec_module=aec_module,
                    use_cache=use_cache,
                    on_audio_chunk=on_audio_chunk,
                )
            if (
                not use_cache
                and not aec_enabled
                and (self._volume_is_default or self._volume == 1.0)
            ):
                # Run piper | aplay pipeline
                tts_start = time.perf_counter()
                piper_proc = subprocess.Popen(
                    piper_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )

                play_start = time.perf_counter()
                aplay_proc = subprocess.Popen(
                    aplay_cmd,
                    stdin=piper_proc.stdout,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._active_piper_proc = piper_proc
                self._active_aplay_proc = aplay_proc

                # Send text to piper
                if piper_proc.stdin is not None:
                    piper_proc.stdin.write(text.encode("utf-8"))
                    piper_proc.stdin.close()

                # Wait for completion (with timeout)
                piper_rc = piper_proc.wait(timeout=30)
                self._last_tts_ms = (time.perf_counter() - tts_start) * 1000.0
                aplay_rc = aplay_proc.wait(timeout=30)
                self._last_play_ms = (time.perf_counter() - play_start) * 1000.0
                if self._active_piper_proc is piper_proc:
                    self._active_piper_proc = None
                if self._active_aplay_proc is aplay_proc:
                    self._active_aplay_proc = None
                if piper_rc != 0 or aplay_rc != 0:
                    self._debug(f"piper/aplay retornaram codigo {piper_rc}/{aplay_rc}")
                return True

            tts_start = time.perf_counter()
            piper_proc = subprocess.Popen(
                piper_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            if piper_proc.stdin is not None:
                piper_proc.stdin.write(text.encode("utf-8"))
                piper_proc.stdin.close()

            raw_audio = b""
            if piper_proc.stdout is not None:
                raw_audio = piper_proc.stdout.read()
            piper_rc = piper_proc.wait(timeout=30)
            self._last_tts_ms = (time.perf_counter() - tts_start) * 1000.0
            if piper_rc != 0:
                self._debug(f"piper retornou codigo {piper_rc}")

            if use_cache and raw_audio:
                self._cache_put(text, raw_audio)
            if self._volume <= 0.0:
                self._last_play_ms = None
                self._last_first_audio_ms = None
                return True

            return self._play_raw_audio(
                raw_audio,
                aplay_cmd,
                aec_enabled,
                aec_module,
                sample_rate=22050,
                on_audio_chunk=on_audio_chunk,
            )

        except Exception as exc:
            self._debug(f"piper falhou: {exc}")
            return False

    def _find_piper_model(self) -> Path | None:
        """Find Piper model file."""
        if self._piper_model:
            return Path(self._piper_model) if Path(self._piper_model).exists() else None

        # Check common locations
        repo_root = Path(__file__).resolve().parents[3]
        search_paths = [
            self._piper_models_dir,
            repo_root / "storage/models/piper",
            Path.home() / ".local/share/piper",
            Path("/usr/share/piper-voices"),
            Path("/usr/local/share/piper-voices"),
        ]

        voice = (self._default_voice or "").strip()
        quality_order = (
            _env_str("JARVIS_PIPER_VOICE_QUALITY_ORDER", "low,medium,high")
            or "low,medium,high"
        )
        qualities = [q.strip() for q in quality_order.split(",") if q.strip()]
        has_quality_suffix = any(
            voice.endswith(suffix) for suffix in ("-low", "-medium", "-high")
        )
        if voice and not has_quality_suffix:
            candidates = [f"{voice}-{q}" for q in qualities] + [voice]
        else:
            candidates = [voice] if voice else []

        for base_path in search_paths:
            if not base_path.exists():
                continue

            models_by_stem: dict[str, Path] = {}
            for model_file in base_path.rglob("*.onnx"):
                models_by_stem.setdefault(model_file.stem, model_file)

            for candidate in candidates:
                if candidate and candidate in models_by_stem:
                    chosen = models_by_stem[candidate]
                    self._piper_model = str(chosen)
                    return chosen

            # Any Portuguese model
            for model_file in base_path.rglob("*pt_BR*.onnx"):
                self._piper_model = str(model_file)
                return model_file

            # Any model at all
            for model_file in base_path.rglob("*.onnx"):
                self._piper_model = str(model_file)
                return model_file

        return None

    def _cache_get(self, text: str) -> bytes | None:
        if not self._cache_enabled or self._cache_max_items <= 0:
            return None
        key = text.strip()
        if not key:
            return None
        cached = self._cache.get(key)
        if cached is None:
            return None
        self._cache.move_to_end(key)
        return cached

    def _cache_put(self, text: str, audio: bytes) -> None:
        if not self._cache_enabled or self._cache_max_items <= 0:
            return
        key = text.strip()
        if not key or not audio:
            return
        if len(key) > self._cache_max_chars:
            return
        self._cache[key] = audio
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_max_items:
            self._cache.popitem(last=False)

    def _play_raw_audio(
        self,
        raw_audio: bytes,
        aplay_cmd: list[str],
        aec_enabled: bool,
        aec_module: Optional[object],
        sample_rate: int = 22050,
        on_audio_chunk: Callable[[bytes], None] | None = None,
    ) -> bool:
        if self._stop_event.is_set():
            return True
        raw_audio = self._prepare_audio(raw_audio, sample_rate)
        scaled_audio = self._scale_audio(raw_audio)
        if aec_enabled and aec_module is not None and scaled_audio:
            push_fn = getattr(aec_module, "push_playback_reference", None)
            if callable(push_fn):
                try:
                    push_fn(scaled_audio, 22050)
                except Exception:
                    pass
        play_start = time.perf_counter()
        aplay_proc = subprocess.Popen(
            aplay_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._active_aplay_proc = aplay_proc
        if aplay_proc.stdin is not None and scaled_audio:
            if on_audio_chunk is not None:
                try:
                    on_audio_chunk(scaled_audio)
                except Exception:
                    pass
            aplay_proc.stdin.write(scaled_audio)
            aplay_proc.stdin.close()
        aplay_rc = aplay_proc.wait(timeout=30)
        self._last_play_ms = (time.perf_counter() - play_start) * 1000.0
        if self._active_aplay_proc is aplay_proc:
            self._active_aplay_proc = None
        if aplay_rc != 0:
            self._debug(f"aplay retornou codigo {aplay_rc}")
        return True

    def _warmup(self) -> None:
        if not self._warmup_enabled:
            return
        try:
            ok = self._warmup_piper(self._warmup_text)
            if not ok:
                self._debug("warmup piper indisponivel")
        except Exception as exc:
            self._debug(f"warmup falhou: {exc}")

    def _warmup_ack_phrase(self) -> None:
        phrase = (self._ack_phrase or "").strip()
        if not phrase or self._ack_phrase_raw is not None:
            return
        try:
            raw = self._synthesize_piper_raw(phrase)
            if raw:
                self._ack_phrase_raw = raw
        except Exception:
            return

    def _synthesize_piper_raw(self, text: str) -> bytes:
        text = str(text or "").strip()
        if not text:
            return b""
        model_path = self._find_piper_model()
        if model_path is None:
            return b""
        backend = (self._piper_backend or "auto").strip().lower()
        prefer_python = backend in {"auto", "python", "py"}
        prefer_cli = backend in {"cli", "bin", "binary"}
        if prefer_python and not prefer_cli:
            voice = self._ensure_piper_voice(model_path)
            if voice is not None:
                try:
                    out = bytearray()
                    for audio_chunk in voice.synthesize(text):
                        raw = getattr(audio_chunk, "audio_int16_bytes", b"")
                        if raw:
                            out.extend(raw)
                    return bytes(out)
                except Exception:
                    pass

        piper_cmd_prefix = self._ensure_piper_cmd()
        if piper_cmd_prefix is None:
            return b""
        piper_cmd = [*piper_cmd_prefix, "--model", str(model_path), "--output-raw"]
        proc = subprocess.Popen(
            piper_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if proc.stdin is not None:
            proc.stdin.write(text.encode("utf-8"))
            proc.stdin.close()
        raw = b""
        if proc.stdout is not None:
            raw = proc.stdout.read()
        proc.wait(timeout=60)
        return raw

    def _warmup_piper(self, text: str) -> bool:
        model_path = self._find_piper_model()
        if model_path is None:
            self._piper_available = False
            return False

        backend = (self._piper_backend or "auto").strip().lower()
        prefer_python = backend in {"auto", "python", "py"}
        prefer_cli = backend in {"cli", "bin", "binary"}
        if prefer_python and not prefer_cli:
            voice = self._ensure_piper_voice(model_path)
            if voice is not None:
                try:
                    for audio_chunk in voice.synthesize(text):
                        raw = getattr(audio_chunk, "audio_int16_bytes", b"")
                        if raw:
                            break
                    return True
                except Exception:
                    pass

        if self._piper_available is False:
            return False
        if self._piper_available is None:
            self._piper_cmd = self._ensure_piper_cmd()
            self._piper_available = self._piper_cmd is not None
            if not self._piper_available:
                return False
        piper_cmd_prefix = self._ensure_piper_cmd()
        if piper_cmd_prefix is None:
            return False
        piper_cmd = [*piper_cmd_prefix, "--model", str(model_path), "--output-raw"]
        proc = subprocess.Popen(
            piper_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if proc.stdin is not None:
            proc.stdin.write(text.encode("utf-8"))
            proc.stdin.close()
        if proc.stdout is not None:
            proc.stdout.read()
        proc.wait(timeout=30)
        return True

    def _speak_espeak(self, text: str) -> None:
        """Speak using espeak-ng (fallback)."""
        if self._espeak_available is False:
            return

        if self._espeak_available is None:
            self._espeak_available = shutil.which("espeak-ng") is not None
            if not self._espeak_available:
                return

        cmd = ["espeak-ng", "-v", "pt-br"]
        amplitude = self._espeak_amplitude()
        if amplitude is not None:
            cmd.extend(["-a", str(amplitude)])
        cmd.append(text)
        try:
            start_ts = time.perf_counter()
            subprocess.Popen(
                cmd,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            first_audio_ts = time.perf_counter()
            self._last_tts_ms = (first_audio_ts - start_ts) * 1000.0
            self._last_play_ms = None
            self._last_first_audio_ms = self._last_tts_ms
            self._last_first_audio_perf_ts = first_audio_ts
            self._last_first_speech_ms = self._last_tts_ms
            self._last_first_speech_perf_ts = first_audio_ts
            self._last_engine = "espeak-ng"
        except Exception as exc:
            self._debug(f"espeak falhou: {exc}")

    def speak_async(self, text: str) -> None:
        """
        Speak text asynchronously (non-blocking).

        Uses a background thread to avoid blocking the main loop.
        """
        thread = threading.Thread(target=self.speak, args=(text,), daemon=True)
        thread.start()

    def play_phase1_ack(self) -> None:
        """
        Play a fast "I'm listening / one moment" acknowledgment immediately.

        Purpose (voice UX):
        - Reduce perceived latency by emitting an immediate sound/short phrase
          while the system is still processing (STT/LLM/actions).

        Behavior:
        - Prefer pre-generated Piper raw audio from `JARVIS_TTS_ACK_PHRASE` (warmup).
        - Otherwise, fall back to an earcon tone.
        - Never uses espeak-ng (avoids robotic fallback).
        """
        with self._speak_lock:
            if self.config.tts_mode == "none":
                return
            if self._stop_event.is_set():
                return

            aec_module = None
            aec_enabled = False
            try:
                from jarvis.interface.entrada import vad as vad_module

                aec_enabled = bool(vad_module.is_aec_enabled())
                aec_module = vad_module
            except Exception:
                aec_enabled = False

            raw = self._ack_phrase_raw
            source = "phase1_phrase"
            if not raw:
                raw = self._get_earcon_raw(sample_rate=22050)
                source = "phase1_earcon"

            now = time.perf_counter()
            self._last_tts_ms = 0.0
            self._last_play_ms = None
            self._last_first_audio_ms = 0.0
            self._last_first_audio_perf_ts = now
            self._last_first_speech_ms = 0.0
            self._last_first_speech_perf_ts = now
            self._last_engine = "piper" if source == "phase1_phrase" else "earcon"
            self._last_ack_ms = 0.0
            self._last_ack_perf_ts = now
            self._last_ack_source = source

            if self._volume <= 0.0 or not raw:
                return

            aplay_cmd = self._build_aplay_cmd(22050)
            self._play_raw_audio(
                raw,
                aplay_cmd,
                aec_enabled,
                aec_module,
                sample_rate=22050,
                on_audio_chunk=None,
            )

    def get_last_metrics(self) -> dict[str, float | None | str]:
        return {
            "tts_ms": self._last_tts_ms,
            "play_ms": self._last_play_ms,
            "tts_first_audio_ms": self._last_first_audio_ms,
            "tts_first_audio_perf_ts": self._last_first_audio_perf_ts,
            "tts_first_speech_ms": self._last_first_speech_ms,
            "tts_first_speech_perf_ts": self._last_first_speech_perf_ts,
            "tts_ack_ms": self._last_ack_ms,
            "tts_ack_perf_ts": self._last_ack_perf_ts,
            "tts_ack_source": self._last_ack_source,
            "tts_engine": self._last_engine,
        }

    def _get_earcon_raw(self, *, sample_rate: int) -> bytes:
        if self._earcon_raw is not None:
            return self._earcon_raw
        duration_ms = self._ack_duration_ms
        if duration_ms <= 0 or self._ack_volume <= 0.0:
            self._earcon_raw = b""
            return self._earcon_raw
        num_samples = int(sample_rate * (duration_ms / 1000.0))
        if num_samples <= 0:
            self._earcon_raw = b""
            return self._earcon_raw
        amplitude = int(32767 * self._ack_volume)
        freq = float(self._ack_freq_hz)
        samples = array("h")
        for i in range(num_samples):
            t = i / float(sample_rate)
            value = int(amplitude * math.sin(2.0 * math.pi * freq * t))
            samples.append(value)
        self._earcon_raw = samples.tobytes()
        return self._earcon_raw

    def get_last_word_timings(self) -> list[dict[str, float | str]] | None:
        return self._last_word_timings

    def get_available_engines(self) -> list[str]:
        """Get list of available TTS engines."""
        engines = []

        piper_cmd = self._ensure_piper_cmd()
        if piper_cmd and self._find_piper_model():
            engines.append("piper")

        if shutil.which("espeak-ng"):
            engines.append("espeak-ng")

        return engines


def _find_piper_binary_static() -> str | None:
    """Static helper to find piper binary."""
    override = _env_str("JARVIS_PIPER_BIN")
    if override:
        path = Path(override)
        if _is_executable_file(path):
            return str(path)

    piper_path = shutil.which("piper")
    if piper_path and _is_executable_file(Path(piper_path)):
        return piper_path

    # In venvs that got moved, `.venv/bin/piper` may be present but not runnable.
    # In that case, we consider Piper available if the module exists in the venv.
    try:
        import importlib.util

        if importlib.util.find_spec("piper") is not None:
            return "python -m piper"
    except Exception:
        return None

    common_paths = [
        Path.home() / ".local/bin/piper",
        Path("/usr/local/bin/piper"),
        Path("/usr/bin/piper"),
        Path.home() / "bin/piper",
    ]

    for path in common_paths:
        if _is_executable_file(path):
            return str(path)

    return None


def check_tts_deps() -> dict:
    """Check TTS dependencies."""
    return {
        "piper": _find_piper_binary_static() is not None,
        "espeak-ng": shutil.which("espeak-ng") is not None,
        "aplay": shutil.which("aplay") is not None,
    }


def install_piper_instructions() -> str:
    """Get instructions for installing Piper."""
    return """
Para instalar Piper TTS:

1. Baixe o binário:
   wget https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz
   tar -xzf piper_linux_x86_64.tar.gz
   sudo mv piper /usr/local/bin/

2. Baixe uma voz em português:
   mkdir -p ~/.local/share/piper-models
   cd ~/.local/share/piper-models
   wget https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx
   wget https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json

3. Teste:
   echo "Olá, eu sou o Jarvis" | piper --model ~/.local/share/piper-models/pt_BR-faber-medium.onnx --output-raw | aplay -r 22050 -f S16_LE -t raw -
"""
