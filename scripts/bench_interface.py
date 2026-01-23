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
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any


@dataclass
class IterationMetrics:
    """Per-iteration timing breakdown for eos_to_first_audio benchmark."""

    iteration: int
    eos_ts: float  # timestamp inicio
    trim_ms: float  # tempo de processamento do trim (perf_counter)
    endpointing_ms: float  # tempo calculo endpointing
    stt_ms: float  # tempo transcricao
    tts_first_audio_ms: float  # tempo até primeiro áudio (NÃO tempo total)
    tts_total_ms: float | None  # tempo total do speak (opcional, para contexto)
    ack_ms: float | None  # tempo ack (se habilitado)
    total_eos_to_first_audio_ms: float
    overhead_ms: float  # gap nao medido entre componentes (clampeado >= 0)
    bottleneck: str  # "endpointing" | "stt" | "tts"
    trimmed_audio_duration_ms: float  # duração do áudio pós-trim (contexto)

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


def _calc_p99(values: list[float]) -> float | None:
    """Calcula p99 se houver amostras suficientes (N >= 2)."""
    if len(values) < 2:
        return None
    return statistics.quantiles(values, n=100)[-1]


def _calc_p995(values: list[float]) -> float | None:
    """Calcula p99.5 apenas se N >= 200."""
    if len(values) < 200:
        return None
    return statistics.quantiles(values, n=200)[-1]


def _get_git_commit() -> str | None:
    """Retorna o commit hash atual do git, se disponível."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _build_benchmark_config(
    *,
    warmup: bool | None = None,
    require_wake_word: bool | None = None,
    stt_model: str | None = None,
    resample: bool | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """
    Constrói o dicionário benchmark_config com informações do ambiente.

    Registra todas as configurações relevantes para reproduzir o benchmark.
    """
    import platform
    from datetime import datetime, timezone

    config: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _get_git_commit(),
        "python_version": platform.python_version(),
    }

    # Adiciona parâmetros opcionais (apenas se não forem None)
    if warmup is not None:
        config["warmup"] = warmup
    if require_wake_word is not None:
        config["require_wake_word"] = require_wake_word
    if stt_model is not None:
        config["stt_model"] = stt_model
    if resample is not None:
        config["resample"] = resample

    # Adiciona parâmetros extras
    config.update(extra)

    return config


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
        "latency_ms_p99": _calc_p99(durations_ms),
        "latency_ms_p995": _calc_p995(durations_ms),
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
    from jarvis.entrada.stt import SpeechToText

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

    # Adiciona benchmark_config
    stt_model = os.environ.get("JARVIS_STT_MODEL", "tiny").strip() or "tiny"
    result["benchmark_config"] = _build_benchmark_config(
        warmup=warmup,
        require_wake_word=require_wake_word,
        stt_model=stt_model,
        resample=resample,
    )

    if print_text:
        result["transcribed_text_last"] = last_text
        result["require_wake_word"] = require_wake_word
        result["stt_warmed"] = bool(warmup)
    return result


def _bench_stt_realtimestt(
    audio_path: Path | None, repeat: int, *, resample: bool, enable_gpu: bool
) -> dict[str, Any]:
    from jarvis.voz.adapters import stt_realtimestt

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
        "latency_ms_p99": _calc_p99(durations_ms),
        "latency_ms_p995": _calc_p995(durations_ms),
        "realtimestt_ttfp_ms_p50": statistics.median(ttfp_ms) if ttfp_ms else None,
        "rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "scenario": "stt_realtimestt",
        "audio": str(audio_path),
        "model": model,
        "language": language or None,
        "pace_realtime": pace_realtime,
    }
    result["benchmark_config"] = _build_benchmark_config(
        stt_model=model,
        resample=resample,
        pace_realtime=pace_realtime,
        language=language or None,
    )
    if enable_gpu:
        result.update(_collect_gpu_metrics())
    return result


def _bench_vad(
    audio_path: Path | None, repeat: int, *, resample: bool, enable_gpu: bool
) -> dict[str, Any]:
    from jarvis.entrada.stt import SpeechToText
    from jarvis.cerebro.config import load_config

    if audio_path is None:
        raise ValueError("audio_path is required for VAD benchmark")
    frames, samplerate, channels = _load_audio(audio_path, 16000, resample=resample)

    stt = SpeechToText(load_config())

    def run() -> None:
        stt.check_speech_present(frames)

    result = _measure(run, repeat, enable_gpu=enable_gpu)
    result.update({"scenario": "vad", "audio": str(audio_path) if audio_path else "none"})
    result["benchmark_config"] = _build_benchmark_config(resample=resample)
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
    from jarvis.voz.vad import VoiceActivityDetector, resolve_vad_aggressiveness

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
    result["benchmark_config"] = _build_benchmark_config(
        resample=resample,
        vad_silence_ms=silence_ms,
    )
    return result


def _bench_tts(
    text: str, repeat: int, mode: str, *, enable_gpu: bool
) -> dict[str, Any]:
    from types import SimpleNamespace
    from jarvis.voz.tts import TextToSpeech

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
    result["benchmark_config"] = _build_benchmark_config(tts_mode=mode)
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
    result["benchmark_config"] = _build_benchmark_config(
        llm_prompt_style=os.environ.get("JARVIS_LLM_PROMPT_STYLE", "compact"),
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
    """
    Benchmark completo de eos_to_first_audio (endpointing + STT + TTS).

    IMPORTANTE: Este benchmark SEMPRE faz warmup de STT e TTS (simula produção).
    Para medir cold start, use o cenário 'stt' com --no-warmup.

    Protocolo de warmup (linhas 657-680):
    - STT: carrega modelo Whisper e faz 1 transcricao warmup
    - TTS: faz 1 speak() warmup para carregar Piper

    Meta OURO: p95 < 1200ms
    """
    from jarvis.cerebro.config import load_config
    from jarvis.entrada.stt import SpeechToText
    from jarvis.voz.tts import TextToSpeech
    from jarvis.voz.vad import VoiceActivityDetector, resolve_vad_aggressiveness

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
    trim_ms_values: list[float] = []
    stt_ms_values: list[float] = []
    tts_total_ms_values: list[float] = []
    tts_ack_ms_values: list[float] = []
    endpoint_reached_values: list[bool] = []
    phase1_sources: list[str] = []
    iterations_data: list[IterationMetrics] = []

    # Warm up STT model so repeat stats reflect "service already running"
    # (avoids p95 being dominated by first model load).
    try:
        get_model = getattr(stt, "_get_whisper_model", None)
        if callable(get_model):
            get_model(realtime=False)
        transcribe = getattr(stt, "_transcribe_audio_bytes", None)
        bytes_per_frame = getattr(vad, "bytes_per_frame", None)
        if callable(transcribe) and isinstance(bytes_per_frame, int) and bytes_per_frame > 0:
            warm_bytes = frames[: min(len(frames), bytes_per_frame * 2)]
            if warm_bytes:
                transcribe(
                    warm_bytes,
                    require_wake_word=False,
                    skip_speech_check=True,
                )
    except Exception:
        pass

    # Warm up TTS model (avoids first speak() loading Piper from scratch)
    try:
        tts.speak(reply_text[:20] if len(reply_text) > 20 else reply_text)
    except Exception:
        pass

    for i in range(repeat):
        # Start measuring total EOS-to-first-audio time from here
        eos_ts = time.perf_counter()

        # Track endpointing time
        endpoint_start = time.perf_counter()
        endpoint = _compute_endpointing(frames, vad, silence_ms=silence_ms)
        endpoint_end = time.perf_counter()
        iter_endpointing_ms = (endpoint_end - endpoint_start) * 1000.0

        endpoint_reached = bool(endpoint.get("endpoint_reached"))
        bytes_per_frame = endpoint.get("bytes_per_frame")
        frame_ms = int(endpoint.get("frame_ms") or 30)
        last_voiced_idx = endpoint.get("last_voiced_idx")

        # Measure trim processing time with perf_counter
        trim_start = time.perf_counter()
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
        trim_end = time.perf_counter()
        iter_trim_ms = (trim_end - trim_start) * 1000.0
        trim_ms_values.append(iter_trim_ms)

        endpoint_reached_values.append(endpoint_reached)
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

        # Measure STT locally with perf_counter
        stt_start = time.perf_counter()
        stt._transcribe_audio_bytes(  # type: ignore[attr-defined]
            trimmed_audio,
            require_wake_word=False,
            skip_speech_check=False,
        )
        stt_end = time.perf_counter()
        iter_stt_ms = (stt_end - stt_start) * 1000.0
        stt_ms_values.append(iter_stt_ms)

        # Measure TTS locally with perf_counter (total time for context)
        tts_start = time.perf_counter()
        tts.speak(reply_text)
        tts_end = time.perf_counter()
        iter_tts_total_ms = (tts_end - tts_start) * 1000.0
        tts_total_ms_values.append(iter_tts_total_ms)

        tts_metrics = tts.get_last_metrics()
        first_audio_ts = tts_metrics.get("tts_first_audio_perf_ts")
        if first_audio_ts is None:
            first_audio_ts = time.perf_counter()
        iter_eos_to_first_audio_ms = (float(first_audio_ts) - eos_ts) * 1000.0
        eos_to_first_audio_values.append(iter_eos_to_first_audio_ms)
        ack_ts = tts_metrics.get("tts_ack_perf_ts")
        if ack_ts is not None:
            eos_to_ack_values.append((float(ack_ts) - eos_ts) * 1000.0)

        # Get tts_first_audio_ms from tts_metrics (time to first audio, NOT total)
        first_audio_ms = tts_metrics.get("tts_first_audio_ms")
        iter_tts_first_audio_ms = float(first_audio_ms) if first_audio_ms is not None else iter_tts_total_ms

        ack_ms = tts_metrics.get("tts_ack_ms")
        iter_ack_ms: float | None = float(ack_ms) if ack_ms is not None else None
        if ack_ms is not None:
            tts_ack_ms_values.append(float(ack_ms))

        # Calculate trimmed audio duration (for context)
        iter_trimmed_audio_duration_ms = 0.0
        if frame_ms > 0 and isinstance(bytes_per_frame, int) and bytes_per_frame > 0:
            iter_trimmed_audio_duration_ms = (len(trimmed_audio) / float(bytes_per_frame)) * float(frame_ms)

        # Calculate overhead (gap between measured components and total)
        # Use tts_first_audio_ms (NOT tts_total_ms) for correct breakdown
        # Clamp to >= 0 to avoid negative values from timing discrepancies
        measured_sum = iter_endpointing_ms + iter_trim_ms + iter_stt_ms + iter_tts_first_audio_ms
        iter_overhead_ms = max(0.0, iter_eos_to_first_audio_ms - measured_sum)

        # Identify bottleneck (component with largest contribution - excluding ack)
        # Use tts_first_audio_ms (NOT tts_total_ms) for accurate bottleneck identification
        components: dict[str, float] = {
            "endpointing": iter_endpointing_ms,
            "stt": iter_stt_ms,
            "tts": iter_tts_first_audio_ms,
        }
        iter_bottleneck = max(components, key=lambda k: components[k])

        iterations_data.append(
            IterationMetrics(
                iteration=i,
                eos_ts=eos_ts,
                trim_ms=iter_trim_ms,
                endpointing_ms=iter_endpointing_ms,
                stt_ms=iter_stt_ms,
                tts_first_audio_ms=iter_tts_first_audio_ms,
                tts_total_ms=iter_tts_total_ms,
                ack_ms=iter_ack_ms,
                total_eos_to_first_audio_ms=iter_eos_to_first_audio_ms,
                overhead_ms=iter_overhead_ms,
                bottleneck=iter_bottleneck,
                trimmed_audio_duration_ms=iter_trimmed_audio_duration_ms,
            )
        )

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
    if trim_ms_values:
        result["trim_ms_p50"] = statistics.median(trim_ms_values)
    if stt_ms_values:
        result["stt_ms_p50"] = statistics.median(stt_ms_values)
    if tts_total_ms_values:
        result["tts_total_ms_p50"] = statistics.median(tts_total_ms_values)
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

    # Adiciona benchmark_config (documenta que warmup é OBRIGATÓRIO neste cenário)
    stt_model = os.environ.get("JARVIS_STT_MODEL", "tiny").strip() or "tiny"
    result["benchmark_config"] = _build_benchmark_config(
        warmup=True,  # SEMPRE True para eos_to_first_audio
        stt_model=stt_model,
        resample=resample,
        vad_silence_ms=silence_ms,
        vad_post_roll_ms=post_roll_ms,
        note="warmup is MANDATORY for eos_to_first_audio (simulates production). For cold start, use 'stt' scenario with --no-warmup.",
    )

    if enable_gpu:
        result.update(_collect_gpu_metrics())

    # Top 10 slow runs with breakdown
    if iterations_data:
        sorted_runs = sorted(
            iterations_data, key=lambda x: x.total_eos_to_first_audio_ms, reverse=True
        )
        top_10 = sorted_runs[:10]
        top_10_output = [
            {
                "rank": rank + 1,
                "iteration": m.iteration,
                "total_ms": round(m.total_eos_to_first_audio_ms, 2),
                "breakdown": {
                    "endpointing_ms": round(m.endpointing_ms, 2),
                    "trim_ms": round(m.trim_ms, 2),
                    "stt_ms": round(m.stt_ms, 2),
                    "tts_first_audio_ms": round(m.tts_first_audio_ms, 2),
                    "ack_ms": round(m.ack_ms, 2) if m.ack_ms is not None else None,
                    "overhead_ms": round(m.overhead_ms, 2),
                },
                "tts_total_ms": round(m.tts_total_ms, 2) if m.tts_total_ms else None,
                "trimmed_audio_duration_ms": round(m.trimmed_audio_duration_ms, 2),
                "bottleneck": m.bottleneck,
            }
            for rank, m in enumerate(top_10)
        ]
        result["top_10_slow_runs"] = top_10_output

        # Stage breakdown with avg/p50/p95
        def _calc_stats(values: list[float]) -> dict[str, float]:
            # Filter out invalid values (None and 0.0 fallback values)
            valid_values = [v for v in values if v is not None and v > 0.0]
            if not valid_values:
                return {"avg_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0}
            p95 = (
                statistics.quantiles(valid_values, n=20)[-1]
                if len(valid_values) >= 2
                else valid_values[0]
            )
            return {
                "avg_ms": round(statistics.mean(valid_values), 2),
                "p50_ms": round(statistics.median(valid_values), 2),
                "p95_ms": round(p95, 2),
            }

        def _calc_stats_optional(values: list[float | None]) -> dict[str, float]:
            # For optional values like ack_ms that can be None
            valid_values = [v for v in values if v is not None and v > 0.0]
            if not valid_values:
                return {"avg_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0}
            p95 = (
                statistics.quantiles(valid_values, n=20)[-1]
                if len(valid_values) >= 2
                else valid_values[0]
            )
            return {
                "avg_ms": round(statistics.mean(valid_values), 2),
                "p50_ms": round(statistics.median(valid_values), 2),
                "p95_ms": round(p95, 2),
            }

        endpointing_vals = [m.endpointing_ms for m in iterations_data]
        trim_vals = [m.trim_ms for m in iterations_data]
        stt_vals = [m.stt_ms for m in iterations_data]
        tts_first_audio_vals = [m.tts_first_audio_ms for m in iterations_data]
        ack_vals: list[float | None] = [m.ack_ms for m in iterations_data]
        overhead_vals = [m.overhead_ms for m in iterations_data]

        stage_breakdown: dict[str, Any] = {
            "endpointing": _calc_stats(endpointing_vals),
            "trim": _calc_stats(trim_vals),
            "stt": _calc_stats(stt_vals),
            "tts": _calc_stats(tts_first_audio_vals),  # tts_first_audio, NÃO tts_total
            "ack": _calc_stats_optional(ack_vals),
            "overhead": _calc_stats(overhead_vals),
        }
        result["stage_breakdown"] = stage_breakdown

        # Bottleneck summary (count of bottlenecks per component)
        bottleneck_counts: dict[str, int] = {}
        for m in iterations_data:
            bottleneck_counts[m.bottleneck] = bottleneck_counts.get(m.bottleneck, 0) + 1
        result["bottleneck_summary"] = bottleneck_counts

    return result


def _bench_speaker(
    audio_path: Path | None, repeat: int, *, resample: bool, enable_gpu: bool
) -> dict[str, Any]:
    from jarvis.voz import speaker_verify

    if audio_path is None:
        raise ValueError("audio_path is required for speaker benchmark")
    frames, samplerate, channels = _load_audio(audio_path, 16000, resample=resample)

    def run() -> None:
        speaker_verify.verify_speaker(frames)

    result = _measure(run, repeat, enable_gpu=enable_gpu)
    result.update({"scenario": "speaker", "audio": str(audio_path) if audio_path else "none"})
    result["benchmark_config"] = _build_benchmark_config(resample=resample)
    return result


def _bench_barge_in(
    text: str, repeat: int, *, enable_gpu: bool, delay_ms: int = 200
) -> dict[str, Any]:
    """
    Benchmark do tempo de barge-in (stop do TTS até silêncio real).

    Mede o tempo entre chamar tts.stop() e o áudio REALMENTE parar:
    - Poll até processo aplay terminar (proc.poll() != None)
    - Delay adicional de 50ms para dreno de buffer ALSA
    - Captura timestamp final após parada completa

    Meta PRATA: p95 < 120ms
    Meta OURO: p95 < 80ms
    """
    from types import SimpleNamespace
    from jarvis.interface.saida.tts import TextToSpeech

    config = SimpleNamespace(tts_mode="local")
    tts = TextToSpeech(config)  # type: ignore[arg-type]

    stop_times: list[float] = []

    # Texto longo para garantir que TTS esteja reproduzindo
    long_text = text * 5 if len(text) < 50 else text

    def run() -> None:
        # Inicia TTS em thread separada
        def play_tts() -> None:
            try:
                tts.speak(long_text)
            except Exception:
                pass

        tts_thread = threading.Thread(target=play_tts, daemon=True)
        tts_thread.start()

        # Espera TTS começar a reproduzir áudio
        time.sleep(delay_ms / 1000.0)

        # Mede tempo REAL até áudio parar (com wait_completion)
        stop_start = time.perf_counter()

        # stop(wait_completion=True) aguarda término dos processos internamente
        # - Kill dos processos (aplay primeiro, piper depois)
        # - Wait até processos terminarem (timeout 0.5s)
        tts.stop(wait_completion=True)

        # Delay adicional para dreno de buffer ALSA
        # Configurável via env: JARVIS_BENCH_ALSA_DRAIN_MS (default: 50ms)
        alsa_drain_ms = int(os.environ.get("JARVIS_BENCH_ALSA_DRAIN_MS", "50"))
        time.sleep(alsa_drain_ms / 1000.0)

        stop_end = time.perf_counter()

        stop_ms = (stop_end - stop_start) * 1000.0
        stop_times.append(stop_ms)

        # Espera thread terminar para não acumular
        tts_thread.join(timeout=1.0)

    result = _measure(run, repeat, enable_gpu=enable_gpu)
    result.update({
        "scenario": "barge_in",
        "text": text[:50] + "..." if len(text) > 50 else text,
        "delay_before_stop_ms": delay_ms,
    })
    result["benchmark_config"] = _build_benchmark_config(
        tts_mode="local",
        delay_before_stop_ms=delay_ms,
    )

    if stop_times:
        result["barge_in_stop_ms_avg"] = statistics.mean(stop_times)
        result["barge_in_stop_ms_p50"] = statistics.median(stop_times)
        result["barge_in_stop_ms_p95"] = (
            statistics.quantiles(stop_times, n=20)[-1]
            if len(stop_times) >= 2
            else stop_times[0]
        )
        result["barge_in_stop_ms_min"] = min(stop_times)
        result["barge_in_stop_ms_max"] = max(stop_times)

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
            "barge_in",
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
    parser.add_argument(
        "--profile",
        type=str,
        choices=["fast_cpu", "balanced_cpu", "noisy_room"],
        help="usar um perfil de voz pré-definido (fast_cpu, balanced_cpu, noisy_room)",
    )
    args = parser.parse_args()

    # Apply voice profile if specified
    if args.profile:
        try:
            from jarvis.interface.infra.profiles import load_profile, apply_profile
            profile = load_profile(args.profile)
            apply_profile(profile)
        except Exception as e:
            print(f"Warning: Failed to apply profile '{args.profile}': {e}", flush=True)

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
    elif args.scenario == "barge_in":
        result = _bench_barge_in(args.text, args.repeat, enable_gpu=args.gpu)
    else:
        result = _bench_tts(args.text, args.repeat, args.tts_mode, enable_gpu=args.gpu)

    # Add profile to result if it was applied
    if args.profile:
        if "benchmark_config" not in result:
            result["benchmark_config"] = {}
        result["benchmark_config"]["profile"] = args.profile

    output = json.dumps(result, ensure_ascii=True, indent=2)
    if args.json:
        Path(args.json).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
