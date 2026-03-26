from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis.entrada.stt import SpeechToText
from jarvis.voz.adapters import stt_realtimestt


@pytest.fixture(autouse=True)
def _patch_vad(monkeypatch):
    monkeypatch.setattr("jarvis.entrada.stt.check_vad_available", lambda: False)


def _make_stt() -> SpeechToText:
    cfg = SimpleNamespace(
        stt_mode="local",
        stt_model_size="tiny",
        stt_audio_trim_backend="none",
    )
    return SpeechToText(cfg)  # type: ignore[arg-type]


def test_cpu_backend_contract_exposes_capabilities_and_memory():
    stt = _make_stt()
    caps = stt.get_backend_capabilities()
    assert caps.backend_id == "whisper_cpu"
    assert caps.supports_sync is True
    assert caps.supports_partials is True
    assert stt.get_backend_memory_cost_bytes() is not None


def test_realtimestt_adapter_contract_helpers():
    caps = stt_realtimestt.capabilities()
    assert caps.backend_id == "realtimestt_experimental"
    assert caps.supports_streaming is True
    assert caps.experimental is True
    assert stt_realtimestt.estimate_memory_cost_bytes() > 0
