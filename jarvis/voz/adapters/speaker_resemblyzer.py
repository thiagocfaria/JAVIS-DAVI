from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jarvis.voz import speaker_verify

from .base import SampleRate, SpeakerVerifier, validate_audio_i16


class ResemblyzerSpeakerVerifier(SpeakerVerifier):
    def is_enabled(self) -> bool:
        return speaker_verify.is_enabled()

    def is_available(self) -> bool:
        return speaker_verify.is_available()

    def voiceprint_path(self) -> Path:
        return speaker_verify.voiceprint_path()

    def load_voiceprint(self, path: str) -> dict | None:
        default_path = str(self.voiceprint_path())
        if not path or path == default_path:
            embedding = speaker_verify.load_voiceprint()
            if not embedding:
                return None
            return {"embedding": embedding}
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

    def verify(self, audio_i16: bytes, sample_rate: SampleRate) -> float:
        error = validate_audio_i16(audio_i16, sample_rate)
        if error:
            return 0.0
        score, _ok = speaker_verify.verify_speaker(audio_i16, sample_rate)
        return score

    def verify_ok(
        self, audio_i16: bytes, sample_rate: SampleRate
    ) -> tuple[float, bool]:
        error = validate_audio_i16(audio_i16, sample_rate)
        if error:
            return 0.0, False
        return speaker_verify.verify_speaker(audio_i16, sample_rate)

    def enroll(self, audio_i16: bytes, sample_rate: SampleRate) -> list[float] | None:
        error = validate_audio_i16(audio_i16, sample_rate)
        if error:
            return None
        return speaker_verify.enroll_speaker(audio_i16, sample_rate)
