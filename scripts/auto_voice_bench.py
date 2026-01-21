#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import wave
from pathlib import Path
from typing import Any

try:
    import numpy as np  # type: ignore
except Exception:
    np = None

try:
    import sounddevice as sd  # type: ignore
except Exception as exc:
    sd = None
    _SD_ERROR = exc
else:
    _SD_ERROR = None


def _die(message: str) -> None:
    print(message)
    raise SystemExit(1)


def _query_device(device: int | None) -> tuple[int | None, int, str]:
    if sd is None:
        _die(f"sounddevice indisponivel: {_SD_ERROR}")
    assert sd is not None
    try:
        info: dict[str, Any] = sd.query_devices(device, "input")  # type: ignore
    except Exception as exc:
        print(f"[warn] falha ao consultar device: {exc}")
        info = {}
    name = str(info.get("name") or "default")
    samplerate = int(info.get("default_samplerate") or 44100)
    return device, samplerate, name


def _record_wav(
    path: Path,
    *,
    seconds: float,
    samplerate: int,
    device: int | None,
    prompt: str,
) -> int:
    if sd is None or np is None:
        _die("sounddevice/numpy indisponivel. Ative a venv e instale as deps.")
    assert sd is not None
    assert np is not None
    print(prompt)
    for i in range(3, 0, -1):
        print(f"  ...{i}")
        time.sleep(1)
    print("GRAVANDO agora!")
    audio = sd.rec(
        int(seconds * samplerate),
        samplerate=samplerate,
        channels=1,
        dtype="int16",
        device=device,
    )
    sd.wait()
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(samplerate)
        handle.writeframes(audio.tobytes())
    size_bytes = int(audio.size * 2)
    print(f"[ok] gravado: {path} ({size_bytes} bytes)")
    return size_bytes


def _run_bench(audio_path: Path, *, repeat: int, resample: bool, scenario: str) -> None:
    cmd = [
        sys.executable,
        str(Path("scripts") / "bench_interface.py"),
        scenario,
        "--audio",
        str(audio_path),
        "--repeat",
        str(repeat),
        "--json",
        str(audio_path.with_suffix(f".{scenario}.json")),
    ]
    if resample:
        cmd.append("--resample")
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    print(f"[bench] {' '.join(cmd)}")
    subprocess.run(cmd, check=False, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Grava audio uma vez e roda benchmarks STT/VAD automaticamente."
    )
    parser.add_argument("--device", type=int, default=None, help="indice do device")
    parser.add_argument("--seconds", type=float, default=4.0, help="duracao da fala")
    parser.add_argument(
        "--phrase",
        type=str,
        default="oi jarvis teste automatico",
        help="frase para falar",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/tmp/jarvis_voice_bench",
        help="pasta de saida",
    )
    parser.add_argument("--repeat-stt", type=int, default=5)
    parser.add_argument("--repeat-vad", type=int, default=10)
    parser.add_argument("--repeat-endpointing", type=int, default=10)
    parser.add_argument(
        "--with-noise",
        action="store_true",
        help="grava tambem amostra com TV/ruido ligado",
    )
    parser.add_argument(
        "--no-pause",
        action="store_true",
        help="nao esperar enter entre gravacao limpa e com ruido",
    )
    args = parser.parse_args()

    device, samplerate, name = _query_device(args.device)
    resample = samplerate != 16000
    print(
        f"[info] device={device if device is not None else 'default'} name={name} "
        f"samplerate={samplerate} resample={'yes' if resample else 'no'}"
    )

    out_dir = Path(args.output_dir)
    clean_path = out_dir / "voice_clean.wav"
    noise_path = out_dir / "voice_noise.wav"

    _record_wav(
        clean_path,
        seconds=args.seconds,
        samplerate=samplerate,
        device=device,
        prompt=(
            "Ambiente silencioso. Quando comecar a gravacao, diga:\n"
            f'  "{args.phrase}"\n'
            "Fale de forma clara por 2-3 segundos."
        ),
    )

    if args.with_noise:
        if not args.no_pause:
            input("Ligue a TV/ruido e pressione Enter quando estiver pronto...")
        _record_wav(
            noise_path,
            seconds=args.seconds,
            samplerate=samplerate,
            device=device,
            prompt=(
                "Ligue a TV/ruido. Quando comecar a gravacao, diga a mesma frase:\n"
                f'  "{args.phrase}"'
            ),
        )

    _run_bench(clean_path, repeat=args.repeat_stt, resample=resample, scenario="stt")
    _run_bench(clean_path, repeat=args.repeat_vad, resample=resample, scenario="vad")
    _run_bench(
        clean_path,
        repeat=args.repeat_endpointing,
        resample=resample,
        scenario="endpointing",
    )
    if args.with_noise:
        _run_bench(
            noise_path, repeat=args.repeat_stt, resample=resample, scenario="stt"
        )
        _run_bench(
            noise_path, repeat=args.repeat_vad, resample=resample, scenario="vad"
        )
        _run_bench(
            noise_path,
            repeat=args.repeat_endpointing,
            resample=resample,
            scenario="endpointing",
        )

    print("[ok] benchmarks concluidos. Veja os arquivos *.json em", out_dir)


if __name__ == "__main__":
    main()
