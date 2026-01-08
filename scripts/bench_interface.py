#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import wave
from pathlib import Path
from typing import Any

import resource


def _read_wav(path: Path) -> tuple[bytes, int, int]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sampwidth = handle.getsampwidth()
        samplerate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    return frames, samplerate, channels


def _measure(fn, repeat: int) -> dict[str, Any]:
    durations: list[float] = []
    cpu_times: list[float] = []
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
    return {
        "repeat": repeat,
        "latency_ms_avg": statistics.mean(durations_ms),
        "latency_ms_p50": statistics.median(durations_ms),
        "latency_ms_p95": statistics.quantiles(durations_ms, n=20)[-1]
        if len(durations_ms) >= 2
        else durations_ms[0],
        "cpu_time_s_avg": statistics.mean(cpu_times),
        "rss_kb": rss_kb,
    }


def _bench_stt(audio_path: Path, repeat: int) -> dict[str, Any]:
    from jarvis.cerebro.config import load_config
    from jarvis.entrada.stt import SpeechToText

    frames, samplerate, channels = _read_wav(audio_path)
    if channels != 1:
        raise ValueError("audio precisa ser mono")
    if samplerate != 16000:
        raise ValueError("audio precisa ser 16kHz para este benchmark")

    stt = SpeechToText(load_config())

    def run() -> None:
        stt._transcribe_audio_bytes(  # type: ignore[attr-defined]
            frames,
            require_wake_word=False,
            skip_speech_check=False,
        )

    result = _measure(run, repeat)
    result.update({"scenario": "stt", "audio": str(audio_path)})
    return result


def _bench_vad(audio_path: Path, repeat: int) -> dict[str, Any]:
    from jarvis.entrada.stt import SpeechToText
    from jarvis.cerebro.config import load_config

    frames, samplerate, channels = _read_wav(audio_path)
    if channels != 1:
        raise ValueError("audio precisa ser mono")
    if samplerate != 16000:
        raise ValueError("audio precisa ser 16kHz para este benchmark")

    stt = SpeechToText(load_config())

    def run() -> None:
        stt.check_speech_present(frames)

    result = _measure(run, repeat)
    result.update({"scenario": "vad", "audio": str(audio_path)})
    return result


def _bench_tts(text: str, repeat: int, mode: str) -> dict[str, Any]:
    from types import SimpleNamespace
    from jarvis.voz.tts import TextToSpeech

    tts = TextToSpeech(SimpleNamespace(tts_mode=mode))

    def run() -> None:
        tts.speak(text)

    result = _measure(run, repeat)
    result.update({"scenario": "tts", "text": text, "tts_mode": mode})
    return result


def _bench_speaker(audio_path: Path, repeat: int) -> dict[str, Any]:
    from jarvis.voz import speaker_verify

    frames, samplerate, channels = _read_wav(audio_path)
    if channels != 1:
        raise ValueError("audio precisa ser mono")
    if samplerate != 16000:
        raise ValueError("audio precisa ser 16kHz para este benchmark")

    def run() -> None:
        speaker_verify.verify_speaker(frames)

    result = _measure(run, repeat)
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
        result = _bench_stt(audio_path, args.repeat)  # type: ignore[arg-type]
    elif args.scenario == "vad":
        result = _bench_vad(audio_path, args.repeat)  # type: ignore[arg-type]
    elif args.scenario == "speaker":
        result = _bench_speaker(audio_path, args.repeat)  # type: ignore[arg-type]
    else:
        result = _bench_tts(args.text, args.repeat, args.tts_mode)

    output = json.dumps(result, ensure_ascii=True, indent=2)
    if args.json:
        Path(args.json).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
