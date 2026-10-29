from __future__ import annotations

from jarvis.entrada.stt import apply_wake_word_filter

from .base import WakeWordDetector


class TextWakeWordDetector(WakeWordDetector):
    """
    Wake word adapter for text-based flows.

    This keeps the same interface as audio detectors, but does not detect on audio.
    """

    def detect(self, audio_i16: bytes, sample_rate: int) -> bool:
        return False

    def filter_text(
        self,
        text: str,
        *,
        wake_word: str | None = None,
        require: bool | None = None,
    ) -> str:
        return apply_wake_word_filter(text, wake_word=wake_word, require=require)
