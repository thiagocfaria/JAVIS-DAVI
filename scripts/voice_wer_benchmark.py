#!/usr/bin/env python3
"""
Calcula WER e taxa de acertos dos WAVs padronizados.

Usa o SpeechToText local (offline), transcreve cada WAV e compara com o texto esperado.
Saída: WER global, acertos individuais, e opcionalmente JSON/Markdown.
"""
from __future__ import annotations

import argparse
import json
import os
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


@dataclass
class SampleResult:
    audio: str
    transcript: str
    expected: str
    wer: float
    words: int
    correct: bool


def _load_wav(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        samplerate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    if channels != 1:
        raise ValueError(f"{path} precisa ser mono (1 canal)")
    if samplerate != SAMPLE_RATE:
        if resample_poly is None or np is None:
            raise ValueError("scipy/numpy necessários para resample")
        samples = np.frombuffer(frames, dtype=np.int16)
        resampled = resample_poly(samples, SAMPLE_RATE, samplerate).astype(np.int16)
        frames = resampled.tobytes()
        samplerate = SAMPLE_RATE
    return frames, samplerate


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
                dp[i - 1][j] + 1,      # deleção
                dp[i][j - 1] + 1,      # inserção
                dp[i - 1][j - 1] + cost,  # substituição
            )
    return dp[m][n]


def _wer(ref: str, hyp: str) -> float:
    ref_tokens = _tokenize(ref)
    hyp_tokens = _tokenize(hyp)
    if not ref_tokens:
        return 0.0 if not hyp_tokens else 1.0
    dist = _levenshtein(ref_tokens, hyp_tokens)
    return float(dist) / float(len(ref_tokens))


def run(audio_dir: Path) -> tuple[list[SampleResult], float]:
    config = load_config()
    stt = SpeechToText(config)
    results: list[SampleResult] = []
    total_words = 0
    total_dist = 0.0
    for name, expected in EXPECTED_TEXT.items():
        path = audio_dir / name
        if not path.exists():
            raise FileNotFoundError(f"audio não encontrado: {path}")
        frames, _sr = _load_wav(path)
        stt._reset_last_metrics()  # type: ignore[attr-defined]
        text_result = stt._transcribe_audio_bytes(  # type: ignore[attr-defined]
            frames,
            require_wake_word=False,
            skip_speech_check=True,
            allow_short_audio=True,
            skip_rust_trim=True,
        )
        # _transcribe_audio_bytes returns str | tuple[str, bytes]
        # When return_audio=False (default), it returns str
        text = text_result[0] if isinstance(text_result, tuple) else text_result
        transcript = (text or "").strip()
        wer_value = _wer(expected, transcript)
        words = len(_tokenize(expected))
        total_words += words
        total_dist += wer_value * words
        results.append(
            SampleResult(
                audio=name,
                transcript=transcript,
                expected=expected,
                wer=wer_value,
                words=words,
                correct=wer_value == 0.0,
            )
        )
    wer_global = (total_dist / float(total_words)) if total_words else 0.0
    return results, wer_global


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark de WER nos áudios de teste")
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=Path("Documentos/DOC_INTERFACE/test_audio"),
        help="pasta dos áudios gravados",
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    args = parser.parse_args()

    results, wer_global = run(args.audio_dir)
    print(f"WER global: {wer_global:.3f}")
    for res in results:
        status = "OK" if res.correct else "WER"
        print(
            f"{status} {res.audio}: wer={res.wer:.3f} "
            f"hyp=\"{res.transcript}\" ref=\"{res.expected}\""
        )

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(
                {
                    "wer_global": wer_global,
                    "samples": [res.__dict__ for res in results],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        lines = ["| audio | wer | hyp | ref |", "| --- | --- | --- | --- |"]
        for res in results:
            lines.append(
                f"| {res.audio} | {res.wer:.3f} | {res.transcript} | {res.expected} |"
            )
        args.md_out.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
