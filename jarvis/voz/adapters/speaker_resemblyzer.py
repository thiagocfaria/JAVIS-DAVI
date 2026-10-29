from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jarvis.voz import speaker_verify

from .base import SpeakerVerifier


class ResemblyzerSpeakerVerifier(SpeakerVerifier):
    def is_enabled(self) -> bool:
        return speaker_verify.is_enabled()

    def is_available(self) -> bool:
        return speaker_verify.is_available()

    def voiceprint_path(self) -> Path:
        return speaker_verify.voiceprint_path()

    def load_voiceprint(self, path: str) -> dict | None:
        if not path:
            path = str(self.voiceprint_path())
        try:
            data: Any = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        embedding = data.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            return None
        return data

    def verify(self, audio_i16: bytes, sample_rate: int) -> float:
        score, _ok = speaker_verify.verify_speaker(audio_i16)
        return score

    def verify_ok(self, audio_i16: bytes, sample_rate: int) -> tuple[float, bool]:
        return speaker_verify.verify_speaker(audio_i16)

    def enroll(self, audio_i16: bytes, sample_rate: int) -> list[float] | None:
        return speaker_verify.enroll_speaker(audio_i16)
