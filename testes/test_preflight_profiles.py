from __future__ import annotations

import types

import pytest

from jarvis.entrada import preflight
from jarvis.cerebro.config import Config
from typing import cast


def _make_config(tmp_path):
    return cast(
        Config,
        types.SimpleNamespace(
            data_dir=tmp_path,
            stop_file_path=tmp_path / "STOP",
            local_llm_base_url=None,
            stt_mode="local",
            tts_mode="local",
            session_type="unknown",
        ),
    )


def _fake_check(name: str):
    def _check(*args, **kwargs):
        return preflight.CheckResult(name=name, status="OK", detail="ok")

    return _check


@pytest.mark.parametrize(
    ("profile", "expected", "excluded"),
    [
        (
            "voice",
            {"STT", "TTS"},
            {
                "Acoes desktop",
                "Acoes web",
                "Validacao (OCR)",
                "Aprendizado",
                "Chat UI",
                "Atalho chat",
            },
        ),
        (
            "ui",
            {"Chat UI", "Atalho chat"},
            {
                "STT",
                "TTS",
                "Acoes desktop",
                "Acoes web",
                "Validacao (OCR)",
                "Aprendizado",
            },
        ),
        (
            "desktop",
            {"Acoes desktop", "Acoes web", "Validacao (OCR)", "Aprendizado"},
            {"STT", "TTS", "Chat UI", "Atalho chat"},
        ),
    ],
)
def test_preflight_profiles_filter_checks(
    monkeypatch, tmp_path, profile, expected, excluded
):
    config = _make_config(tmp_path)

    monkeypatch.setattr(preflight, "_check_stt", _fake_check("STT"))
    monkeypatch.setattr(preflight, "_check_tts", _fake_check("TTS"))
    monkeypatch.setattr(
        preflight, "_check_desktop_drivers", _fake_check("Acoes desktop")
    )
    monkeypatch.setattr(preflight, "_check_web_automation", _fake_check("Acoes web"))
    monkeypatch.setattr(preflight, "_check_validator", _fake_check("Validacao (OCR)"))
    monkeypatch.setattr(preflight, "_check_recorder", _fake_check("Aprendizado"))
    monkeypatch.setattr(preflight, "_check_chat_ui", _fake_check("Chat UI"))
    monkeypatch.setattr(preflight, "_check_chat_shortcut", _fake_check("Atalho chat"))

    monkeypatch.setenv("JARVIS_PREFLIGHT_PROFILE", profile)

    report = preflight.run_preflight(config)
    names = {check.name for check in report.checks}

    for name in expected:
        assert name in names

    for name in excluded:
        assert name not in names
