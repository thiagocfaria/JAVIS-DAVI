#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import threading
import wave
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any

import resource

try:
    import numpy as np  # type: ignore
except Exception:
    np = None

try:
    from scipy.signal import resample_poly  # type: ignore
except Exception:
    resample_poly = None

try:
    import psutil  # type: ignore
except Exception:
    psutil = None


def _env_int(key: str, default: int) -> int:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _read_wav(path: Path) -> tuple[bytes, int, int]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        samplerate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    return frames, samplerate, channels


def _resample_audio(frames: bytes, src_sr: int, target_sr: int) -> bytes:
    if resample_poly is None or np is None:
        raise ValueError("scipy/numpy required for resampling")
    if src_sr == target_sr:
        return frames
    samples = np.frombuffer(frames, dtype=np.int16)
    if samples.size == 0:
        return b""
    ratio = Fraction(target_sr, src_sr).limit_denominator(1000)
    resampled = resample_poly(samples, ratio.numerator, ratio.denominator)
    resampled = np.clip(resampled, -32768, 32767).astype(np.int16)
    return resampled.tobytes()


def _load_audio(
    path: Path,
    target_sr: int,
    *,
    resample: bool = False,
) -> tuple[bytes, int, int]:
    frames, samplerate, channels = _read_wav(path)
    if channels != 1:
        raise ValueError("audio precisa ser mono")
    if samplerate != target_sr:
        if not resample:
            raise ValueError(
                "audio precisa ser 16kHz para este benchmark (ou use --resample)"
            )
        frames = _resample_audio(frames, samplerate, target_sr)
        samplerate = target_sr
    return frames, samplerate, channels


def _collect_psutil_metrics(proc) -> dict[str, Any] | None:
    try:
        cpu_percent = proc.cpu_percent(interval=None)
        mem = proc.memory_info()
    except Exception:
        return None
    return {
        "psutil_cpu_percent": cpu_percent,
        "psutil_rss_bytes": getattr(mem, "rss", 0),
        "psutil_vms_bytes": getattr(mem, "vms", 0),
    }


def _collect_gpu_metrics() -> dict[str, Any]:
    if shutil.which("nvidia-smi") is None:
        return {"gpu_available": False}
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
    except Exception:
        return {"gpu_available": False}

    line = ""
    for raw in result.stdout.splitlines():
        if raw.strip():
            line = raw.strip()
            break
    if not line:
        return {"gpu_available": False}
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 3:
        return {"gpu_available": False}
    try:
        util = int(float(parts[0]))
        mem_used = int(float(parts[1]))
        mem_total = int(float(parts[2]))
    except ValueError:
        return {"gpu_available": False}
    return {
        "gpu_available": True,
        "gpu_util_percent": util,
        "gpu_mem_used_mb": mem_used,
        "gpu_mem_total_mb": mem_total,
    }


def _measure(fn, repeat: int, *, enable_gpu: bool = False) -> dict[str, Any]:
    durations: list[float] = []
    cpu_times: list[float] = []
    psutil_proc = None
    if psutil is not None:
        try:
            psutil_proc = psutil.Process()
            psutil_proc.cpu_percent(interval=None)
        except Exception:
            psutil_proc = None
    for _ in range(repeat):
        start_usage = resource.getrusage(resource.RUSAGE_SELF)
        start = time.perf_counter()
        fn()
        end = time.perf_counter()
        end_usage = resource.getrusage(resource.RUSAGE_SELF)
        durations.append(end - start)
        cpu_times.append(
            (end_usage.ru_utime - start_usage.ru_utime)
            + (end_usage.ru_stime - start_usage.ru_stime)
        )
    rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    durations_ms = [d * 1000.0 for d in durations]
    result = {
        "repeat": repeat,
        "latency_ms_avg": statistics.mean(durations_ms),
        "latency_ms_p50": statistics.median(durations_ms),
        "latency_ms_p95": (
            statistics.quantiles(durations_ms, n=20)[-1]
            if len(durations_ms) >= 2
            else durations_ms[0]
        ),
        "cpu_time_s_avg": statistics.mean(cpu_times),
        "rss_kb": rss_kb,
    }
    if psutil_proc is not None:
        psutil_metrics = _collect_psutil_metrics(psutil_proc)
        if psutil_metrics:
            result.update(psutil_metrics)
            result["psutil_available"] = True
    if enable_gpu:
        result.update(_collect_gpu_metrics())
    return result


def _bench_stt(
    audio_path: Path | None,
    repeat: int,
    *,
    resample: bool,
    enable_gpu: bool,
    require_wake_word: bool,
    print_text: bool,
    warmup: bool,
) -> dict[str, Any]:
    from jarvis.cerebro.config import load_config
    from jarvis.interface.entrada.stt import SpeechToText

    if audio_path is None:
        raise ValueError("audio_path is required for STT benchmark")
    frames, samplerate, channels = _load_audio(audio_path, 16000, resample=resample)

    stt = SpeechToText(load_config())
    last_text: str | None = None

    if warmup:
        try:
            get_model = getattr(stt, "_get_whisper_model", None)
            if callable(get_model):
                get_model(realtime=False)
            transcribe = getattr(stt, "_transcribe_audio_bytes", None)
            if callable(transcribe):
                warm_bytes = frames[: min(len(frames), 16000 * 2)]
                if warm_bytes:
                    transcribe(
                        warm_bytes,
                        require_wake_word=False,
                        skip_speech_check=True,
                    )
        except Exception:
            pass

    def run() -> None:
        nonlocal last_text
        result = stt._transcribe_audio_bytes(  # type: ignore[attr-defined]
            frames,
            require_wake_word=require_wake_word,
            skip_speech_check=False,
        )
        if isinstance(result, tuple):
            last_text = str(result[0] or "")
        else:
            last_text = str(result or "")

    result = _measure(run, repeat, enable_gpu=enable_gpu)
    result.update({"scenario": "stt", "audio": str(audio_path) if audio_path else "none"})
    if print_text:
        result["transcribed_text_last"] = last_text
        result["require_wake_word"] = require_wake_word
        result["stt_warmed"] = bool(warmup)
    return result


def _bench_stt_realtimestt(
    audio_path: Path | None, repeat: int, *, resample: bool, enable_gpu: bool
) -> dict[str, Any]:
    from jarvis.interface.entrada.adapters import stt_realtimestt

    if audio_path is None:
        raise ValueError("audio_path is required for STT realtime benchmark")
    frames, samplerate, channels = _load_audio(audio_path, 16000, resample=resample)
    if not stt_realtimestt.is_available():
        raise ValueError(f"RealtimeSTT indisponivel: {stt_realtimestt.last_error()}")

    model = (os.environ.get("JARVIS_STT_MODEL") or "tiny").strip() or "tiny"
    language = (os.environ.get("JARVIS_STT_LANGUAGE") or "").strip()
    pace_realtime = os.environ.get("JARVIS_BENCH_REALTIME_PACE", "1").strip() not in {
        "0",
        "false",
        "no",
        "off",
    }
    allow_downloads = os.environ.get("JARVIS_BENCH_ALLOW_DOWNLOADS", "0").strip() in {
        "1",
        "true",
        "yes",
        "on",
    }

    durations_ms: list[float] = []
    ttfp_ms: list[float] = []
    for _ in range(repeat):
        first_partial: list[float] = []

        def on_partial(_text: str) -> None:
            if not first_partial:
                first_partial.append(time.perf_counter())

        old_hf_offline = os.environ.get("HF_HUB_OFFLINE")
        old_hf_telemetry = os.environ.get("HF_HUB_DISABLE_TELEMETRY")
        if not allow_downloads:
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        recorder = stt_realtimestt.build_recorder(
            model=model,
            language=language,
            device="cpu",
            use_microphone=False,
            spinner=False,
            enable_realtime_transcription=True,
            use_main_model_for_realtime=True,
            realtime_model_type=model,
            init_realtime_after_seconds=0.0,
            on_realtime_transcription_update=on_partial,
            wake_words="",
            silero_sensitivity=0.0,
            silero_deactivity_detection=False,
            allowed_latency_limit=100000,
        )
        start = time.perf_counter()
        try:
            if hasattr(recorder, "listen"):
                recorder.listen()

            stop_flag = {"done": False}

            def feed() -> None:
                chunk_samples = 1024
                chunk_bytes = chunk_samples * 2
                for offset in range(0, len(frames), chunk_bytes):
                    recorder.feed_audio(frames[offset : offset + chunk_bytes])
                    if pace_realtime:
                        time.sleep(chunk_samples / 16000.0)
                    else:
                        time.sleep(0)
                recorder.feed_audio(b"\x00" * (16000 * 2))
                stop_flag["done"] = True

            thread = threading.Thread(target=feed, daemon=True)
            thread.start()
            _text = recorder.text()
            thread.join(timeout=2.0)
        finally:
            for method in ("shutdown", "close", "abort", "stop"):
                if hasattr(recorder, method):
                    try:
                        getattr(recorder, method)()
                    except Exception:
                        pass
            if not allow_downloads:
                if old_hf_offline is None:
                    os.environ.pop("HF_HUB_OFFLINE", None)
                else:
                    os.environ["HF_HUB_OFFLINE"] = old_hf_offline
                if old_hf_telemetry is None:
                    os.environ.pop("HF_HUB_DISABLE_TELEMETRY", None)
                else:
                    os.environ["HF_HUB_DISABLE_TELEMETRY"] = old_hf_telemetry
        end = time.perf_counter()
        durations_ms.append((end - start) * 1000.0)
        if first_partial:
            ttfp_ms.append((first_partial[0] - start) * 1000.0)

    result = {
        "repeat": repeat,
        "latency_ms_avg": statistics.mean(durations_ms),
        "latency_ms_p50": statistics.median(durations_ms),
        "latency_ms_p95": (
            statistics.quantiles(durations_ms, n=20)[-1]
            if len(durations_ms) >= 2
            else durations_ms[0]
        ),
        "realtimestt_ttfp_ms_p50": statistics.median(ttfp_ms) if ttfp_ms else None,
        "rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "scenario": "stt_realtimestt",
        "audio": str(audio_path),
        "model": model,
        "language": language or None,
        "pace_realtime": pace_realtime,
    }
    if enable_gpu:
        result.update(_collect_gpu_metrics())
    return result


def _bench_vad(
    audio_path: Path | None, repeat: int, *, resample: bool, enable_gpu: bool
) -> dict[str, Any]:
    from jarvis.interface.entrada.stt import SpeechToText
    from jarvis.cerebro.config import load_config

    if audio_path is None:
        raise ValueError("audio_path is required for VAD benchmark")
    frames, samplerate, channels = _load_audio(audio_path, 16000, resample=resample)

    stt = SpeechToText(load_config())

    def run() -> None:
        stt.check_speech_present(frames)

    result = _measure(run, repeat, enable_gpu=enable_gpu)
    result.update({"scenario": "vad", "audio": str(audio_path) if audio_path else "none"})
    return result


def _compute_endpointing(
    audio_bytes: bytes,
    vad,
    *,
    silence_ms: int,
) -> dict[str, Any]:
    frame_ms = int(getattr(vad, "frame_duration_ms", 30))
    if frame_ms <= 0:
        frame_ms = 30
    silence_frames = max(1, int(silence_ms / frame_ms))
    bytes_per_frame = int(getattr(vad, "bytes_per_frame", 0)) or None
    speech_detected = False
    silence_count = 0
    speech_frames = 0
    total_frames = 0
    last_voiced_idx: int | None = None
    endpoint_idx: int | None = None

    for idx, frame in enumerate(vad.frames_from_audio(audio_bytes)):
        processed = vad.preprocess_frame(frame)
        is_speech = vad.is_speech_preprocessed(processed)
        total_frames += 1
        if is_speech:
            speech_frames += 1
            speech_detected = True
            silence_count = 0
            last_voiced_idx = idx
        elif speech_detected:
            silence_count += 1
            if silence_count >= silence_frames:
                endpoint_idx = idx
                break

    if not speech_detected or last_voiced_idx is None:
        return {
            "speech_detected": False,
            "endpoint_reached": False,
            "endpoint_ms": None,
            "frame_ms": frame_ms,
            "bytes_per_frame": bytes_per_frame,
            "silence_ms": silence_ms,
            "silence_frames": silence_frames,
            "speech_frames": speech_frames,
            "total_frames": total_frames,
            "last_voiced_idx": None,
            "endpoint_idx": None,
        }

    endpoint_reached = endpoint_idx is not None
    if endpoint_idx is None:
        endpoint_idx = max(0, total_frames - 1)
    endpoint_ms = max(0, (endpoint_idx - last_voiced_idx) * frame_ms)

    return {
        "speech_detected": True,
        "endpoint_reached": endpoint_reached,
        "endpoint_ms": endpoint_ms,
        "frame_ms": frame_ms,
        "bytes_per_frame": bytes_per_frame,
        "silence_ms": silence_ms,
        "silence_frames": silence_frames,
        "speech_frames": speech_frames,
        "total_frames": total_frames,
        "last_voiced_idx": last_voiced_idx,
        "endpoint_idx": endpoint_idx,
    }


def _bench_endpointing(
    audio_path: Path | None, repeat: int, *, resample: bool, enable_gpu: bool
) -> dict[str, Any]:
    from jarvis.interface.entrada.vad import VoiceActivityDetector, resolve_vad_aggressiveness

    if audio_path is None:
        raise ValueError("audio_path is required for endpointing benchmark")
    frames, samplerate, channels = _load_audio(audio_path, 16000, resample=resample)

    silence_ms = max(0, _env_int("JARVIS_VAD_SILENCE_MS", 400))
    vad = VoiceActivityDetector(
        aggressiveness=resolve_vad_aggressiveness(2),
        sample_rate=16000,
        frame_duration_ms=30,
    )
    results: list[dict[str, Any]] = []

    def run() -> None:
        results.append(_compute_endpointing(frames, vad, silence_ms=silence_ms))

    result = _measure(run, repeat, enable_gpu=enable_gpu)
    endpoint_values = [
        item["endpoint_ms"] for item in results if item.get("endpoint_ms") is not None
    ]
    speech_detected = any(item.get("speech_detected") for item in results)
    endpoint_reached = (
        all(item.get("endpoint_reached") for item in results) if results else False
    )
    if endpoint_values:
        result["endpoint_ms_avg"] = statistics.mean(endpoint_values)
        result["endpoint_ms_p50"] = statistics.median(endpoint_values)
        result["endpoint_ms_p95"] = (
            statistics.quantiles(endpoint_values, n=20)[-1]
            if len(endpoint_values) >= 2
            else endpoint_values[0]
        )
    else:
        result["endpoint_ms_avg"] = None
        result["endpoint_ms_p50"] = None
        result["endpoint_ms_p95"] = None

    result.update(
        {
            "scenario": "endpointing",
            "audio": str(audio_path) if audio_path else "none",
            "speech_detected": speech_detected,
            "endpoint_reached": endpoint_reached,
            "frame_ms": results[0]["frame_ms"] if results else 30,
            "silence_ms": silence_ms,
            "silence_frames": results[0]["silence_frames"] if results else 0,
        }
    )
    return result


def _bench_tts(
    text: str, repeat: int, mode: str, *, enable_gpu: bool
) -> dict[str, Any]:
    from types import SimpleNamespace
    from jarvis.interface.saida.tts import TextToSpeech

    tts = TextToSpeech(SimpleNamespace(tts_mode=mode))  # type: ignore[arg-type]
    first_audio_values: list[float] = []
    ack_values: list[float] = []
    engines: list[str] = []

    def run() -> None:
        tts.speak(text)
        metrics = tts.get_last_metrics()
        engine = metrics.get("tts_engine")
        if isinstance(engine, str) and engine:
            engines.append(engine)
        ack_ms = metrics.get("tts_ack_ms")
        if ack_ms is not None:
            ack_values.append(float(ack_ms))
        first_audio = metrics.get("tts_first_audio_ms")
        if first_audio is not None:
            first_audio_values.append(float(first_audio))

    result = _measure(run, repeat, enable_gpu=enable_gpu)
    result.update({"scenario": "tts", "text": text, "tts_mode": mode})
    if engines:
        result["tts_engine"] = max(set(engines), key=engines.count)
    if ack_values:
        result["tts_ack_ms_avg"] = statistics.mean(ack_values)
        result["tts_ack_ms_p50"] = statistics.median(ack_values)
        result["tts_ack_ms_p95"] = (
            statistics.quantiles(ack_values, n=20)[-1]
            if len(ack_values) >= 2
            else ack_values[0]
        )
    if first_audio_values:
        result["tts_first_audio_ms_avg"] = statistics.mean(first_audio_values)
        result["tts_first_audio_ms_p50"] = statistics.median(first_audio_values)
        result["tts_first_audio_ms_p95"] = (
            statistics.quantiles(first_audio_values, n=20)[-1]
            if len(first_audio_values) >= 2
            else first_audio_values[0]
        )
    return result


def _bench_llm_plan(
    text: str,
    repeat: int,
    *,
    enable_gpu: bool,
) -> dict[str, Any]:
    from jarvis.cerebro.config import load_config
    from jarvis.cerebro.llm import build_local_llm_client

    config = load_config()
    llm = build_local_llm_client(
        base_url=getattr(config, "local_llm_base_url", None),
        api_key=getattr(config, "local_llm_api_key", None),
        model=getattr(config, "local_llm_model", "local"),
        timeout_s=int(getattr(config, "local_llm_timeout_s", 30)),
        confidence_min=float(getattr(config, "llm_confidence_min", 0.55)),
        cooldown_s=int(getattr(config, "local_llm_cooldown_s", 300)),
    )

    plan_notes: list[str] = []

    def run() -> None:
        plan = llm.plan(text)
        if plan.notes:
            plan_notes.append(str(plan.notes))

    result = _measure(run, repeat, enable_gpu=enable_gpu)
    result.update(
        {
            "scenario": "llm_plan",
            "text": text,
            "llm_prompt_style": os.environ.get("JARVIS_LLM_PROMPT_STYLE", "compact"),
            "llm_base_url_configured": bool(getattr(config, "local_llm_base_url", None)),
            "plan_notes_last": plan_notes[-1] if plan_notes else None,
        }
    )
    return result


def _bench_eos_to_first_audio(
    audio_path: Path | None,
    repeat: int,
    reply_text: str,
    *,
    resample: bool,
    enable_gpu: bool,
) -> dict[str, Any]:
    from jarvis.cerebro.config import load_config
    from jarvis.interface.entrada.stt import SpeechToText
    from jarvis.interface.saida.tts import TextToSpeech
    from jarvis.interface.entrada.vad import VoiceActivityDetector, resolve_vad_aggressiveness

    if audio_path is None:
        raise ValueError("audio_path is required for eos_to_first_audio benchmark")

    config = load_config()
    if getattr(config, "tts_mode", "local") == "none":
        raise ValueError("tts_mode=none; eos_to_first_audio nao pode ser medido sem TTS")

    frames, samplerate, channels = _load_audio(audio_path, 16000, resample=resample)
    stt = SpeechToText(config)
    tts = TextToSpeech(config)

    silence_ms = max(0, _env_int("JARVIS_VAD_SILENCE_MS", 400))
    post_roll_ms = max(0, _env_int("JARVIS_VAD_POST_ROLL_MS", 200))
    vad = VoiceActivityDetector(
        aggressiveness=resolve_vad_aggressiveness(2),
        sample_rate=16000,
        frame_duration_ms=30,
    )

    eos_to_first_audio_values: list[float] = []
    eos_to_ack_values: list[float] = []
    eos_to_phase1_values: list[float] = []
    stt_ms_values: list[float] = []
    tts_first_audio_ms_values: list[float] = []
    tts_ack_ms_values: list[float] = []
    endpoint_reached_values: list[bool] = []
    trimmed_ms_values: list[float] = []
    phase1_sources: list[str] = []

    # Warm up STT model so repeat stats reflect "service already running"
    # (avoids p95 being dominated by first model load).
    try:
        get_model = getattr(stt, "_get_model", None)
        if callable(get_model):
            get_model()
        transcribe = getattr(stt, "_transcribe_audio_bytes", None)
        if callable(transcribe):
            warm_bytes = frames[: min(len(frames), vad.bytes_per_frame * 2)]
            if warm_bytes:
                transcribe(
                    warm_bytes,
                    require_wake_word=False,
                    skip_speech_check=True,
                )
    except Exception:
        pass

    for _ in range(repeat):
        endpoint = _compute_endpointing(frames, vad, silence_ms=silence_ms)
        endpoint_reached = bool(endpoint.get("endpoint_reached"))
        bytes_per_frame = endpoint.get("bytes_per_frame")
        frame_ms = int(endpoint.get("frame_ms") or 30)
        last_voiced_idx = endpoint.get("last_voiced_idx")
        trimmed_audio = frames
        if (
            endpoint_reached
            and isinstance(bytes_per_frame, int)
            and bytes_per_frame > 0
            and isinstance(last_voiced_idx, int)
            and last_voiced_idx >= 0
        ):
            post_roll_frames = max(0, int((post_roll_ms + frame_ms - 1) / frame_ms))
            end_frame_idx = last_voiced_idx + 1 + post_roll_frames
            end_bytes = min(len(frames), end_frame_idx * bytes_per_frame)
            trimmed_audio = frames[:end_bytes]

        endpoint_reached_values.append(endpoint_reached)
        if frame_ms > 0 and isinstance(bytes_per_frame, int) and bytes_per_frame > 0:
            trimmed_ms_values.append(
                (len(trimmed_audio) / float(bytes_per_frame)) * float(frame_ms)
            )

        eos_ts = time.perf_counter()
        if os.environ.get("JARVIS_BENCH_PHASE1", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            play_phase1 = getattr(tts, "play_phase1_ack", None)
            if callable(play_phase1):
                play_phase1()
                phase1_metrics = tts.get_last_metrics()
                phase1_ts = phase1_metrics.get("tts_first_audio_perf_ts")
                if phase1_ts is None:
                    phase1_ts = time.perf_counter()
                eos_to_phase1_values.append((float(phase1_ts) - eos_ts) * 1000.0)
                src = phase1_metrics.get("tts_ack_source")
                if isinstance(src, str) and src:
                    phase1_sources.append(src)
        stt._transcribe_audio_bytes(  # type: ignore[attr-defined]
            trimmed_audio,
            require_wake_word=False,
            skip_speech_check=False,
        )
        stt_metrics = stt.get_last_metrics()
        stt_ms = stt_metrics.get("stt_ms")
        if stt_ms is not None:
            stt_ms_values.append(float(stt_ms))

        tts.speak(reply_text)
        tts_metrics = tts.get_last_metrics()
        first_audio_ts = tts_metrics.get("tts_first_audio_perf_ts")
        if first_audio_ts is None:
            first_audio_ts = time.perf_counter()
        eos_to_first_audio_values.append((float(first_audio_ts) - eos_ts) * 1000.0)
        ack_ts = tts_metrics.get("tts_ack_perf_ts")
        if ack_ts is not None:
            eos_to_ack_values.append((float(ack_ts) - eos_ts) * 1000.0)

        first_audio_ms = tts_metrics.get("tts_first_audio_ms")
        if first_audio_ms is not None:
            tts_first_audio_ms_values.append(float(first_audio_ms))
        ack_ms = tts_metrics.get("tts_ack_ms")
        if ack_ms is not None:
            tts_ack_ms_values.append(float(ack_ms))

    eos_to_first_audio_p95 = (
        statistics.quantiles(eos_to_first_audio_values, n=20)[-1]
        if len(eos_to_first_audio_values) >= 2
        else eos_to_first_audio_values[0]
    )
    result: dict[str, Any] = {
        "scenario": "eos_to_first_audio",
        "audio": str(audio_path),
        "reply_text": reply_text,
        "repeat": repeat,
        "eos_to_first_audio_ms_avg": statistics.mean(eos_to_first_audio_values),
        "eos_to_first_audio_ms_p50": statistics.median(eos_to_first_audio_values),
        "eos_to_first_audio_ms_p95": eos_to_first_audio_p95,
        "rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "endpoint_silence_ms": silence_ms,
        "endpoint_post_roll_ms": post_roll_ms,
        "endpoint_reached_rate": (
            (sum(1 for ok in endpoint_reached_values if ok) / len(endpoint_reached_values))
            if endpoint_reached_values
            else None
        ),
        "stt_warmed": True,
    }
    if trimmed_ms_values:
        result["trimmed_audio_ms_p50"] = statistics.median(trimmed_ms_values)
    if stt_ms_values:
        result["stt_ms_p50"] = statistics.median(stt_ms_values)
    if tts_first_audio_ms_values:
        result["tts_first_audio_ms_p50"] = statistics.median(tts_first_audio_ms_values)
    if eos_to_ack_values:
        eos_to_ack_p95 = (
            statistics.quantiles(eos_to_ack_values, n=20)[-1]
            if len(eos_to_ack_values) >= 2
            else eos_to_ack_values[0]
        )
        result["eos_to_ack_ms_avg"] = statistics.mean(eos_to_ack_values)
        result["eos_to_ack_ms_p50"] = statistics.median(eos_to_ack_values)
        result["eos_to_ack_ms_p95"] = eos_to_ack_p95
    if eos_to_phase1_values:
        eos_to_phase1_p95 = (
            statistics.quantiles(eos_to_phase1_values, n=20)[-1]
            if len(eos_to_phase1_values) >= 2
            else eos_to_phase1_values[0]
        )
        result["eos_to_phase1_ms_avg"] = statistics.mean(eos_to_phase1_values)
        result["eos_to_phase1_ms_p50"] = statistics.median(eos_to_phase1_values)
        result["eos_to_phase1_ms_p95"] = eos_to_phase1_p95
        if phase1_sources:
            result["phase1_source"] = max(set(phase1_sources), key=phase1_sources.count)
    if tts_ack_ms_values:
        result["tts_ack_ms_p50"] = statistics.median(tts_ack_ms_values)
    if enable_gpu:
        result.update(_collect_gpu_metrics())
    return result


def _bench_speaker(
    audio_path: Path | None, repeat: int, *, resample: bool, enable_gpu: bool
) -> dict[str, Any]:
    from jarvis.interface.entrada import speaker_verify

    if audio_path is None:
        raise ValueError("audio_path is required for speaker benchmark")
    frames, samplerate, channels = _load_audio(audio_path, 16000, resample=resample)

    def run() -> None:
        speaker_verify.verify_speaker(frames)

    result = _measure(run, repeat, enable_gpu=enable_gpu)
    result.update({"scenario": "speaker", "audio": str(audio_path) if audio_path else "none"})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark da interface de voz")
    parser.add_argument(
        "scenario",
        choices=[
            "stt",
            "stt_realtimestt",
            "vad",
            "endpointing",
            "tts",
            "speaker",
            "eos_to_first_audio",
            "llm_plan",
        ],
    )
    parser.add_argument("--audio", type=str, help="caminho para WAV 16kHz mono")
    parser.add_argument("--text", type=str, default="ola jarvis", help="texto para TTS")
    parser.add_argument("--repeat", type=int, default=5, help="repeticoes")
    parser.add_argument(
        "--tts-mode", type=str, default="local", help="tts_mode (local/none)"
    )
    parser.add_argument("--json", type=str, help="salvar saida em JSON")
    parser.add_argument(
        "--print-text",
        action="store_true",
        help="para STT: inclui o ultimo texto transcrito no JSON",
    )
    parser.add_argument(
        "--require-wake-word",
        action="store_true",
        help="para STT: exige wake word (ex.: 'jarvis') no inicio da frase",
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="para STT: nao faz warmup (inclui custo de carregar modelo no tempo medido)",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="coletar metricas de GPU via nvidia-smi (se disponivel)",
    )
    parser.add_argument(
        "--resample",
        action="store_true",
        help="reamostrar para 16 kHz quando o WAV nao estiver em 16 kHz",
    )
    args = parser.parse_args()

    if args.scenario in {
        "stt",
        "stt_realtimestt",
        "vad",
        "endpointing",
        "speaker",
        "eos_to_first_audio",
    }:
        if not args.audio:
            raise SystemExit("--audio e obrigatorio para este scenario")
        audio_path = Path(args.audio)
        if not audio_path.exists():
            raise SystemExit(f"arquivo nao encontrado: {audio_path}")
    else:
        audio_path = None

    if args.scenario == "stt":
        result = _bench_stt(
            audio_path,
            args.repeat,
            resample=args.resample,
            enable_gpu=args.gpu,
            require_wake_word=bool(args.require_wake_word),
            print_text=bool(args.print_text),
            warmup=not bool(args.no_warmup),
        )
    elif args.scenario == "stt_realtimestt":
        result = _bench_stt_realtimestt(
            audio_path, args.repeat, resample=args.resample, enable_gpu=args.gpu
        )
    elif args.scenario == "vad":
        result = _bench_vad(
            audio_path, args.repeat, resample=args.resample, enable_gpu=args.gpu
        )
    elif args.scenario == "endpointing":
        result = _bench_endpointing(
            audio_path, args.repeat, resample=args.resample, enable_gpu=args.gpu
        )
    elif args.scenario == "speaker":
        result = _bench_speaker(
            audio_path, args.repeat, resample=args.resample, enable_gpu=args.gpu
        )
    elif args.scenario == "eos_to_first_audio":
        result = _bench_eos_to_first_audio(
            audio_path,
            args.repeat,
            args.text,
            resample=args.resample,
            enable_gpu=args.gpu,
        )
    elif args.scenario == "llm_plan":
        result = _bench_llm_plan(args.text, args.repeat, enable_gpu=args.gpu)
    else:
        result = _bench_tts(args.text, args.repeat, args.tts_mode, enable_gpu=args.gpu)

    output = json.dumps(result, ensure_ascii=True, indent=2)
    if args.json:
        Path(args.json).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
