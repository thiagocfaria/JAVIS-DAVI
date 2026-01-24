#!/usr/bin/env python3
"""
Generate 16kHz test audio from source for reproducible benchmarks.

Usage:
    python scripts/generate_test_audio.py
"""

import wave
from fractions import Fraction
from pathlib import Path

try:
    import numpy as np
    from scipy.signal import resample_poly
except ImportError:
    print("ERROR: numpy and scipy required")
    print("Install with: pip install numpy scipy")
    exit(1)


def resample_audio(src_path: Path, dst_path: Path, target_rate: int = 16000) -> None:
    """
    Resample audio file to target sample rate.

    Args:
        src_path: Source audio file
        dst_path: Destination audio file
        target_rate: Target sample rate in Hz
    """
    # Read source audio
    with wave.open(str(src_path), "rb") as f:
        frames = f.readframes(f.getnframes())
        src_rate = f.getframerate()
        channels = f.getnchannels()

    if src_rate == target_rate:
        print(f"Already at {target_rate}Hz, copying...")
        dst_path.write_bytes(src_path.read_bytes())
        return

    # Convert to numpy
    samples = np.frombuffer(frames, dtype=np.int16)

    # Resample
    ratio = Fraction(target_rate, src_rate).limit_denominator(1000)
    print(f"Resampling from {src_rate}Hz to {target_rate}Hz (ratio {ratio})")
    resampled = resample_poly(samples, ratio.numerator, ratio.denominator)
    resampled = np.clip(resampled, -32768, 32767).astype(np.int16)

    # Write destination audio
    with wave.open(str(dst_path), "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(target_rate)
        f.writeframes(resampled.tobytes())

    duration = len(resampled) / target_rate
    print(f"✓ Created {dst_path.name} ({len(resampled)} samples, {duration:.2f}s)")


def main() -> int:
    """Generate 16kHz test audio files."""
    base_dir = Path("Documentos/DOC_INTERFACE/bench_audio")
    if not base_dir.exists():
        print(f"ERROR: Directory not found: {base_dir}")
        return 1

    # Generate voice_clean_16k.wav
    src = base_dir / "voice_clean.wav"
    dst = base_dir / "voice_clean_16k.wav"
    if not src.exists():
        print(f"ERROR: Source audio not found: {src}")
        return 1

    resample_audio(src, dst, target_rate=16000)

    # Generate voice_noise_16k.wav (if exists)
    src_noise = base_dir / "voice_noise.wav"
    if src_noise.exists():
        dst_noise = base_dir / "voice_noise_16k.wav"
        resample_audio(src_noise, dst_noise, target_rate=16000)

    print("\n✓ Test audio generation complete")
    print(f"  - {dst}")
    if src_noise.exists():
        print(f"  - {base_dir / 'voice_noise_16k.wav'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
