"""
Voice profiles for JARVIS Interface.

Provides 3 pre-defined voice profiles optimized for different hardware/environments:
- FAST_CPU: Optimized for weak CPU (< 2 cores), clean audio
- BALANCED_CPU: Default, medium CPU (2-4 cores)
- NOISY_ROOM: Optimized for noisy environments

Selection via JARVIS_VOICE_PROFILE env var:
  JARVIS_VOICE_PROFILE=fast_cpu       # Weak CPU
  JARVIS_VOICE_PROFILE=balanced_cpu   # Default
  JARVIS_VOICE_PROFILE=noisy_room     # Noisy environments

Precedence: env var JARVIS_VOICE_PROFILE > env vars > default (balanced_cpu)
"""

from __future__ import annotations

import os
from typing import TypedDict


class VoiceProfile(TypedDict):
    """Voice profile parameters."""

    name: str
    silence_ms: int
    min_speech_ms: int
    pre_roll_ms: int
    post_roll_ms: int
    vad_aggressiveness: int
    stt_model: str


# Profile definitions
PROFILES: dict[str, VoiceProfile] = {
    "fast_cpu": {
        "name": "fast_cpu",
        "silence_ms": 400,
        "min_speech_ms": 300,
        "pre_roll_ms": 100,
        "post_roll_ms": 100,
        "vad_aggressiveness": 3,
        "stt_model": "tiny",
    },
    "balanced_cpu": {
        "name": "balanced_cpu",
        "silence_ms": 500,
        "min_speech_ms": 400,
        "pre_roll_ms": 150,
        "post_roll_ms": 150,
        "vad_aggressiveness": 2,
        "stt_model": "tiny",
    },
    "noisy_room": {
        "name": "noisy_room",
        "silence_ms": 800,
        "min_speech_ms": 500,
        "pre_roll_ms": 200,
        "post_roll_ms": 200,
        "vad_aggressiveness": 1,
        "stt_model": "tiny",
    },
}


def load_profile(profile_name: str | None = None) -> VoiceProfile:
    """
    Load a voice profile by name.

    Precedence:
    1. profile_name parameter (if provided)
    2. JARVIS_VOICE_PROFILE env var (if set)
    3. default: balanced_cpu

    Args:
        profile_name: Optional profile name to load

    Returns:
        Profile dict with all parameters

    Raises:
        ValueError: If profile name is invalid
    """
    # Determine which profile to load
    name_to_load = profile_name
    if name_to_load is None:
        name_to_load = os.environ.get("JARVIS_VOICE_PROFILE", "").strip()
    if not name_to_load:
        name_to_load = "balanced_cpu"

    # Validate and return
    name_to_load_lower = name_to_load.lower()
    if name_to_load_lower not in PROFILES:
        available = ", ".join(PROFILES.keys())
        raise ValueError(
            f"Invalid profile '{name_to_load}'. Available: {available}"
        )

    return PROFILES[name_to_load_lower].copy()


def apply_profile(profile: VoiceProfile) -> None:
    """
    Apply a profile by setting environment variables.

    Only sets env vars that are NOT already explicitly set,
    so user can override individual parameters.

    Args:
        profile: Profile to apply
    """
    # Silence duration for VAD
    if not _env_is_set("JARVIS_VAD_SILENCE_MS"):
        os.environ["JARVIS_VAD_SILENCE_MS"] = str(profile["silence_ms"])

    # Minimum speech duration to trigger recording
    if not _env_is_set("JARVIS_MIN_AUDIO_SECONDS"):
        min_seconds = profile["min_speech_ms"] / 1000.0
        os.environ["JARVIS_MIN_AUDIO_SECONDS"] = f"{min_seconds:.1f}"

    # VAD pre/post roll
    if not _env_is_set("JARVIS_VAD_PRE_ROLL_MS"):
        os.environ["JARVIS_VAD_PRE_ROLL_MS"] = str(profile["pre_roll_ms"])

    if not _env_is_set("JARVIS_VAD_POST_ROLL_MS"):
        os.environ["JARVIS_VAD_POST_ROLL_MS"] = str(profile["post_roll_ms"])

    # VAD aggressiveness (only if JARVIS_VAD_AGGRESSIVENESS is NOT set)
    if not _env_is_set("JARVIS_VAD_AGGRESSIVENESS"):
        os.environ["JARVIS_VAD_AGGRESSIVENESS"] = str(profile["vad_aggressiveness"])

    # STT model (only if JARVIS_STT_MODEL is NOT set)
    if not _env_is_set("JARVIS_STT_MODEL"):
        os.environ["JARVIS_STT_MODEL"] = profile["stt_model"]


def _env_is_set(key: str) -> bool:
    """Check if an environment variable is explicitly set."""
    value = os.environ.get(key)
    return value is not None and value != ""
