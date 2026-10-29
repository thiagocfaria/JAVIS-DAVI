from __future__ import annotations

from typing import Protocol


class WakeWordDetector(Protocol):
    def detect(self, audio_i16: bytes, sample_rate: int) -> bool:
        ...


class SpeakerVerifier(Protocol):
    def load_voiceprint(self, path: str) -> dict | None:
        ...

    def verify(self, audio_i16: bytes, sample_rate: int) -> float:
        ...
