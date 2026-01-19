from __future__ import annotations

from typing import Literal, Protocol


def _audio_nbytes(audio_i16: bytes | bytearray | memoryview) -> int:
    if isinstance(audio_i16, memoryview):
        return int(audio_i16.nbytes)
    return len(audio_i16)


SampleRate = Literal[16000]


def validate_audio_i16(
    audio_i16: bytes | bytearray | memoryview, sample_rate: int
) -> str | None:
    if not isinstance(audio_i16, (bytes, bytearray, memoryview)):
        return "invalid_audio_type"
    if not isinstance(sample_rate, int) or sample_rate <= 0:
        return "invalid_sample_rate"
    nbytes = _audio_nbytes(audio_i16)
    if nbytes == 0:
        return "empty_audio"
    if nbytes % 2 != 0:
        return "invalid_audio_length"
    return None


class WakeWordDetector(Protocol):
    def detect(self, audio_i16: bytes, sample_rate: SampleRate) -> bool: ...


class SpeakerVerifier(Protocol):
    def load_voiceprint(self, path: str) -> dict | None: ...

    def verify(self, audio_i16: bytes, sample_rate: SampleRate) -> float: ...
