#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
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


def _read_wav(path: Path) -> tuple[bytes, int, int]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sampwidth = handle.getsampwidth()
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
            raise ValueError("audio precisa ser 16kHz para este benchmark (ou use --resample)")
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
        "latency_ms_p95": statistics.quantiles(durations_ms, n=20)[-1]
        if len(durations_ms) >= 2
        else durations_ms[0],
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
    audio_path: Path, repeat: int, *, resample: bool, enable_gpu: bool
) -> dict[str, Any]:
    from jarvis.cerebro.config import load_config
    from jarvis.entrada.stt import SpeechToText

    frames, samplerate, channels = _load_audio(
        audio_path, 16000, resample=resample
    )

    stt = SpeechToText(load_config())

    def run() -> None:
        stt._transcribe_audio_bytes(  # type: ignore[attr-defined]
            frames,
            require_wake_word=False,
            skip_speech_check=False,
        )

    result = _measure(run, repeat, enable_gpu=enable_gpu)
    result.update({"scenario": "stt", "audio": str(audio_path)})
    return result


def _bench_vad(
    audio_path: Path, repeat: int, *, resample: bool, enable_gpu: bool
) -> dict[str, Any]:
    from jarvis.entrada.stt import SpeechToText
    from jarvis.cerebro.config import load_config

    frames, samplerate, channels = _load_audio(
        audio_path, 16000, resample=resample
    )

    stt = SpeechToText(load_config())

    def run() -> None:
        stt.check_speech_present(frames)

    result = _measure(run, repeat, enable_gpu=enable_gpu)
    result.update({"scenario": "vad", "audio": str(audio_path)})
    return result


def _bench_tts(
    text: str, repeat: int, mode: str, *, enable_gpu: bool
) -> dict[str, Any]:
    from types import SimpleNamespace
    from jarvis.voz.tts import TextToSpeech

    tts = TextToSpeech(SimpleNamespace(tts_mode=mode))

    def run() -> None:
        tts.speak(text)

    result = _measure(run, repeat, enable_gpu=enable_gpu)
    result.update({"scenario": "tts", "text": text, "tts_mode": mode})
    return result


def _bench_speaker(
    audio_path: Path, repeat: int, *, resample: bool, enable_gpu: bool
) -> dict[str, Any]:
    from jarvis.voz import speaker_verify

    frames, samplerate, channels = _load_audio(
        audio_path, 16000, resample=resample
    )

    def run() -> None:
        speaker_verify.verify_speaker(frames)

    result = _measure(run, repeat, enable_gpu=enable_gpu)
    result.update({"scenario": "speaker", "audio": str(audio_path)})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark da interface de voz")
    parser.add_argument("scenario", choices=["stt", "vad", "tts", "speaker"])
    parser.add_argument("--audio", type=str, help="caminho para WAV 16kHz mono")
    parser.add_argument("--text", type=str, default="ola jarvis", help="texto para TTS")
    parser.add_argument("--repeat", type=int, default=5, help="repeticoes")
    parser.add_argument("--tts-mode", type=str, default="local", help="tts_mode (local/none)")
    parser.add_argument("--json", type=str, help="salvar saida em JSON")
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

    if args.scenario in {"stt", "vad", "speaker"}:
        if not args.audio:
            raise SystemExit("--audio e obrigatorio para este scenario")
        audio_path = Path(args.audio)
        if not audio_path.exists():
            raise SystemExit(f"arquivo nao encontrado: {audio_path}")
    else:
        audio_path = None

    if args.scenario == "stt":
        result = _bench_stt(  # type: ignore[arg-type]
            audio_path, args.repeat, resample=args.resample, enable_gpu=args.gpu
        )
    elif args.scenario == "vad":
        result = _bench_vad(  # type: ignore[arg-type]
            audio_path, args.repeat, resample=args.resample, enable_gpu=args.gpu
        )
    elif args.scenario == "speaker":
        result = _bench_speaker(  # type: ignore[arg-type]
            audio_path, args.repeat, resample=args.resample, enable_gpu=args.gpu
        )
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
