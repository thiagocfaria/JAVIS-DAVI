#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import os
import sys
import wave
from pathlib import Path
from typing import Any

import difflib

try:
    import numpy as np  # type: ignore
    from scipy.signal import resample_poly  # type: ignore
except Exception:
    np = None
    resample_poly = None

from jarvis.cerebro.config import load_config
from jarvis.interface.entrada.stt import SpeechToText
from jarvis.interface.audio.audio_utils import SAMPLE_RATE

EXPECTED_TEXT = {
    "oi_jarvis_clean.wav": "oi jarvis",
    "oi_jarvis_tv.wav": "oi jarvis",
    "oi_jarvis_tv_alta.wav": "oi jarvis",
    "comando_longo.wav": "jarvis, este é um teste longo de comando de voz para benchmark",
    "comando_longo_tv.wav": "jarvis, este é um teste longo de comando de voz para benchmark",
    "ruido_puro.wav": "",
    "sussurro.wav": "jarvis",
}


def run_bench(audio: Path, repeat: int, text: str) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "scripts/bench_interface.py",
        "eos_to_first_audio",
        "--audio",
        str(audio),
        "--text",
        text,
        "--repeat",
        str(repeat),
        "--resample",
    ]
    env = {**os.environ, "PYTHONPATH": "."}
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env={**env, **dict(**dict())},
    )
    if result.returncode != 0:
        raise RuntimeError(f"bench failed for {audio}: {result.stderr.strip()}")
    data = json.loads(result.stdout.strip().splitlines()[-1])
    return data


def _load_wav(path: Path) -> bytes:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        samplerate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    if channels != 1:
        raise ValueError(f"{path} precisa ser mono (1 canal)")
    if samplerate != SAMPLE_RATE:
        if resample_poly is None or np is None:
            raise ValueError(f"{path} não está em 16 kHz e scipy/numpy indisponíveis")
        samples = np.frombuffer(frames, dtype=np.int16)
        resampled = resample_poly(samples, SAMPLE_RATE, samplerate).astype(np.int16)
        frames = resampled.tobytes()
    return frames


def _tokenize(text: str) -> list[str]:
    return [tok for tok in text.lower().strip().split() if tok]


def _levenshtein(a: list[str], b: list[str]) -> int:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost
            )
    return dp[m][n]


def _wer(ref: str, hyp: str) -> float:
    ref_tokens = _tokenize(ref)
    hyp_tokens = _tokenize(hyp)
    if not ref_tokens:
        return 0.0 if not hyp_tokens else 1.0
    dist = _levenshtein(ref_tokens, hyp_tokens)
    return float(dist) / float(len(ref_tokens))


def _similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(a=a.lower(), b=b.lower()).ratio()


def run_wer(audio_dir: Path) -> dict[str, Any]:
    config = load_config()
    stt = SpeechToText(config)
    samples: list[dict[str, Any]] = []
    total_words = 0
    total_dist = 0.0
    for name, expected in EXPECTED_TEXT.items():
        path = audio_dir / name
        if not path.exists():
            continue
        audio_bytes = _load_wav(path)
        stt._reset_last_metrics()  # type: ignore[attr-defined]
        text_result = stt._transcribe_audio_bytes(  # type: ignore[attr-defined]
            audio_bytes,
            require_wake_word=False,
            skip_speech_check=True,
            allow_short_audio=True,
            skip_rust_trim=True,
        )
        # _transcribe_audio_bytes returns str | tuple[str, bytes]
        # When return_audio=False (default), it returns str
        text = text_result[0] if isinstance(text_result, tuple) else text_result
        transcript = (text or "").strip()
        wer_val = _wer(expected, transcript)
        sim = _similarity(expected, transcript)
        words = len(_tokenize(expected))
        total_words += words
        total_dist += wer_val * words
        samples.append(
            {
                "audio": name,
                "expected": expected,
                "transcript": transcript,
                "wer": wer_val,
                "similarity": sim,
            }
        )
    wer_global = (total_dist / float(total_words)) if total_words else 0.0
    return {"wer_global": wer_global, "samples": samples}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Roda bench eos_to_first_audio em todos os WAVs de um diretório."
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=Path("Documentos/DOC_INTERFACE/test_audio"),
        help="diretório com WAVs de teste",
    )
    parser.add_argument("--repeat", type=int, default=20)
    parser.add_argument("--text", type=str, default="ok")
    parser.add_argument("--json-out", type=Path, help="arquivo para salvar JSON")
    parser.add_argument("--md-out", type=Path, help="arquivo para salvar Markdown")
    parser.add_argument("--with-wer", action="store_true", help="calcula WER dos WAVs")
    parser.add_argument(
        "--baseline-json",
        type=Path,
        help="resultado anterior para comparar regressão (>10%)",
    )
    args = parser.parse_args()

    audios = sorted(args.audio_dir.glob("*.wav"))
    results: list[dict[str, Any]] = []
    for audio in audios:
        data = run_bench(audio, repeat=args.repeat, text=args.text)
        results.append(data)
        print(
            f"{audio.name}: p50={data.get('eos_to_first_audio_ms_p50')} "
            f"p95={data.get('eos_to_first_audio_ms_p95')}"
        )

    wer_report = None
    if args.with_wer:
        wer_report = run_wer(args.audio_dir)
        print(f"WER global: {wer_report.get('wer_global')}")
        for sample in wer_report.get("samples", []):
            print(
                f"WER {sample['audio']}: wer={sample['wer']:.3f} sim={sample['similarity']:.2f} hyp=\"{sample['transcript']}\""
            )

    regression_alerts: list[str] = []
    if args.baseline_json and args.baseline_json.exists():
        try:
            baseline = json.loads(args.baseline_json.read_text(encoding="utf-8"))
            if isinstance(baseline, list) and results:
                def avg(key: str, data: list[dict[str, Any]]) -> float:
                    vals = [float(item.get(key, 0)) for item in data if key in item]
                    return sum(vals) / len(vals) if vals else 0.0
                for metric in ["eos_to_first_audio_ms_p50", "eos_to_first_audio_ms_p95"]:
                    new_avg = avg(metric, results)
                    base_avg = avg(metric, baseline)
                    if base_avg > 0 and new_avg > base_avg * 1.1:
                        regression_alerts.append(
                            f"Regressão {metric}: baseline={base_avg:.1f} new={new_avg:.1f}"
                        )
        except Exception:
            pass

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {"latency": results}
        if wer_report:
            payload["wer"] = wer_report
        if regression_alerts:
            payload["regressions"] = regression_alerts
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        lines = ["| audio | p50 (ms) | p95 (ms) |", "| --- | --- | --- |"]
        for item in results:
            lines.append(
                f"| {Path(item.get('audio','')).name} | "
                f"{int(item.get('eos_to_first_audio_ms_p50',0))} | "
                f"{int(item.get('eos_to_first_audio_ms_p95',0))} |"
            )
        if wer_report:
            lines.append("")
            lines.append("| audio | wer | sim | hyp | ref |")
            lines.append("| --- | --- | --- | --- | --- |")
            for sample in wer_report.get("samples", []):
                lines.append(
                    f"| {sample['audio']} | {sample['wer']:.3f} | {sample['similarity']:.2f} | "
                    f"{sample['transcript']} | {sample['expected']} |"
                )
            lines.append(f"| **WER global** | {wer_report.get('wer_global'):.3f} | | | |")
        if regression_alerts:
            lines.append("")
            lines.append("Regressões detectadas (>10%):")
            for alert in regression_alerts:
                lines.append(f"- {alert}")
        args.md_out.write_text("\n".join(lines), encoding="utf-8")

    if regression_alerts:
        print("ALERTA de regressão:")
        for alert in regression_alerts:
            print(f" - {alert}")


if __name__ == "__main__":
    main()
