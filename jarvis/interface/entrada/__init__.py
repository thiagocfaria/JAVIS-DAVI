"""API publica estavel de entrada da interface."""

from .followup import FollowUpSession
from .speaker_verify import (
    enroll_speaker,
    has_voiceprint,
    is_available,
    is_enabled,
    load_voiceprint,
    verify_speaker,
    voiceprint_path,
)
from .stt import STTError, SpeechToText, apply_wake_word_filter, check_stt_deps, resample_audio_float
from .vad import (
    StreamingVAD,
    VADError,
    VoiceActivityDetector,
    apply_aec_to_audio,
    check_vad_available,
    push_playback_reference,
    reset_playback_reference,
    resolve_vad_aggressiveness,
)

__all__ = [
    "FollowUpSession",
    "SpeechToText",
    "STTError",
    "apply_wake_word_filter",
    "check_stt_deps",
    "resample_audio_float",
    "VADError",
    "VoiceActivityDetector",
    "StreamingVAD",
    "resolve_vad_aggressiveness",
    "check_vad_available",
    "apply_aec_to_audio",
    "push_playback_reference",
    "reset_playback_reference",
    "is_enabled",
    "is_available",
    "has_voiceprint",
    "voiceprint_path",
    "load_voiceprint",
    "enroll_speaker",
    "verify_speaker",
]
