"""API publica estavel de saida da interface."""

from .tts import TextToSpeech, check_tts_deps

__all__ = ["TextToSpeech", "check_tts_deps"]
