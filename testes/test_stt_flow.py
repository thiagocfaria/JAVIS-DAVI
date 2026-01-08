from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import wave

import pytest

from jarvis.cerebro.config import Config
from jarvis.entrada.audio_utils import SAMPLE_RATE, coerce_pcm_bytes
from jarvis.entrada.stt import SpeechToText


class _DummyVAD:
    def __init__(self, pattern: list[bool]) -> None:
        self.pattern = pattern

    def frames_from_audio(self, audio_bytes: bytes) -> list[bytes]:
        return [b"\x01" if is_voiced else b"\x00" for is_voiced in self.pattern]

    def is_speech(self, frame: bytes) -> bool:
        return frame == b"\x01"


@pytest.fixture(autouse=True)
def _patch_audio_deps(monkeypatch):
    monkeypatch.setattr("jarvis.entrada.stt.sd", object())
    monkeypatch.setattr("jarvis.entrada.stt.np", object())
    monkeypatch.setattr("jarvis.entrada.stt.check_vad_available", lambda: False)


def _make_stt(tmp_path: Path) -> SpeechToText:
    """Create SpeechToText instance with minimal config for testing."""
    # Create a minimal Config with required fields
    data_dir = tmp_path
    config = Config(
        # Data directories
        data_dir=data_dir,
        cache_dir=data_dir / "cache",
        log_path=data_dir / "events.jsonl",
        memory_db=data_dir / "memory.sqlite3",
        procedures_path=data_dir / "procedures.db",
        policy_user_path=data_dir / "policy_user.json",
        stop_file_path=data_dir / "STOP",
        chat_log_path=data_dir / "chat.log",
        chat_inbox_path=data_dir / "chat_inbox.txt",
        chat_open_cooldown_s=5,
        procedures_max_total=300,
        procedures_max_per_tag=20,
        procedures_ttl_days=90,
        # LLM settings
        local_llm_base_url=None,
        local_llm_api_key=None,
        local_llm_model="qwen2.5-7b-instruct",
        local_llm_timeout_s=30,
        local_llm_cooldown_s=300,
        llm_confidence_min=0.55,
        max_failures_per_command=2,
        max_guidance_attempts=2,
        browser_ai_enabled=True,
        browser_ai_url="https://chatgpt.com",
        auto_learn_procedures=True,
        block_external_sensitive=True,
        external_ask_on_sensitive=True,
        chat_auto_open=True,
        chat_open_command=None,
        # STT settings
        stt_mode="local",
        # TTS settings
        tts_mode="local",
        # Security
        require_approval=True,
        approval_passphrase=None,
        approval_voice_passphrase=None,
        approval_key_passphrase=None,
        approval_mode="voice_and_key",
        # System
        session_type="unknown",
        dry_run=False,
        allow_open_app=True,
        # Privacy
        mask_screenshots=True,
        # Budget
        budget_path=data_dir / "orcamento.json",
        budget_max_calls=100,
        budget_max_chars=100000,
        # Agent S3
        s3_worker_engine_type="openai_compat",
        s3_worker_base_url=None,
        s3_worker_api_key=None,
        s3_worker_model="qwen2.5-7b-instruct",
        s3_grounding_engine_type="openai_compat",
        s3_grounding_base_url=None,
        s3_grounding_api_key=None,
        s3_grounding_model="ui-tars-1.5-7b",
        s3_grounding_width=1920,
        s3_grounding_height=1080,
        s3_max_steps=15,
        s3_max_trajectory=8,
        s3_enable_reflection=True,
        s3_enable_code_agent=False,
        s3_code_agent_budget=20,
        s3_code_workdir=None,
        s3_max_image_dim=1920,
    )
    # STT accesses stt_model_size and stt_audio_trim_backend via getattr with defaults
    # So we don't need to set them - SpeechToText will use defaults from env/config
    return SpeechToText(config)


def test_check_speech_present_detects_voice(tmp_path):
    stt = _make_stt(tmp_path)
    stt._vad = _DummyVAD([False, False, True, True])
    assert stt.check_speech_present(b"ignored")


def test_check_speech_present_rejects_silence(tmp_path):
    stt = _make_stt(tmp_path)
    stt._vad = _DummyVAD([False, False, False])
    assert not stt.check_speech_present(b"ignored")


def test_record_audio_prefers_streaming(tmp_path):
    stt = _make_stt(tmp_path)
    stt._vad = _DummyVAD([True])

    class DummyStreaming:
        def __init__(self):
            self.record_fixed_called = False

        def record_until_silence(self, max_seconds=None):
            # curto demais -> deve cair no fallback fixo
            return b"speech"

        def record_fixed_duration(self, seconds):
            self.record_fixed_called = True
            # retorna áudio “util” no fallback
            return b"\x01\x02" * 20000, True

    streaming = DummyStreaming()
    stt._streaming_vad = streaming
    called = {"fixed": False}

    def fake_fixed(seconds):
        called["fixed"] = True
        return b"\x01\x02" * 20000, True

    stt._record_fixed_duration = fake_fixed
    result = stt._record_audio(5)
    assert called["fixed"]
    assert result == b"\x01\x02" * 20000


def test_record_audio_streaming_long_enough(tmp_path):
    stt = _make_stt(tmp_path)

    class DummyStreaming:
        def __init__(self, payload: bytes):
            self.payload = payload
            self.fixed_called = False

        def record_until_silence(self, max_seconds=None):
            return self.payload

        def record_fixed_duration(self, seconds):
            self.fixed_called = True
            return b"", False

    # gera áudio >= min_bytes para não cair no fallback
    long_payload = b"\x01\x02" * 20000  # 40000 bytes
    streaming = DummyStreaming(long_payload)
    stt._streaming_vad = streaming
    stt._record_fixed_duration = lambda seconds: (b"", False)  # type: ignore

    result = stt._record_audio(5)
    assert result == long_payload


def test_transcribe_once_skips_whisper_when_empty(tmp_path):
    stt = _make_stt(tmp_path)
    stt._record_audio = lambda seconds: b""
    touched = {"transcribed": False}

    def fake_transcribe(audio):
        touched["transcribed"] = True
        return "oops"

    stt._transcribe_local = fake_transcribe
    assert stt.transcribe_once(5) == ""
    assert not touched["transcribed"]


def test_record_audio_accepts_frame_list_from_streaming(tmp_path):
    stt = _make_stt(tmp_path)
    stt._min_audio_seconds = 0.1  # reduz limiar para evitar fallback

    class DummyStreaming:
        def __init__(self):
            self.fixed_called = False

        def record_until_silence(self, max_seconds=None):
            return [b"\x01\x02"] * 2000  # 4000 bytes

        def record_fixed_duration(self, seconds):
            self.fixed_called = True
            return b"", False

    streaming = DummyStreaming()
    stt._streaming_vad = streaming

    result = stt._record_audio(5)
    assert isinstance(result, bytes)
    assert len(result) == 4000
    assert not streaming.fixed_called


def test_record_audio_short_payload_triggers_fallback(monkeypatch, tmp_path):
    stt = _make_stt(tmp_path)
    stt._vad = _DummyVAD([True])

    class DummyStreaming:
        def __init__(self):
            self.fixed_called = False

        def record_until_silence(self, max_seconds=None):
            return b"\x01\x02"  # curto demais

        def record_fixed_duration(self, seconds):
            self.fixed_called = True
            return b"\x03\x04" * 10, True

    streaming = DummyStreaming()
    stt._streaming_vad = streaming
    stt._record_fixed_duration = streaming.record_fixed_duration  # type: ignore[attr-defined]
    result = stt._record_audio(5)
    assert streaming.fixed_called
    assert result == b"\x03\x04" * 10


def test_write_wav_coerces_payloads(tmp_path):
    stt = _make_stt(tmp_path)
    wav_path = tmp_path / "out.wav"
    stt._write_wav(str(wav_path), [0, 1, 2, 3], SAMPLE_RATE)
    expected = coerce_pcm_bytes([0, 1, 2, 3])
    with wave.open(str(wav_path), "rb") as handle:
        frames = handle.readframes(10)
        assert frames == expected
