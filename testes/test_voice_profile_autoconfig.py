from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from jarvis.interface.infra.voice_profile import auto_configure_voice_profile


def test_auto_configure_voice_profile_sets_defaults_when_piper_model_exists(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    (models_dir / "pt_BR-faber-medium.onnx").write_bytes(b"")
    (models_dir / "pt_BR-faber-medium.onnx.json").write_text("{}", encoding="utf-8")

    config = SimpleNamespace(tts_mode="local")

    old_env = os.environ.copy()
    try:
        os.environ["JARVIS_AUTO_CONFIGURE"] = "1"
        os.environ["JARVIS_PIPER_MODELS_DIR"] = str(models_dir)

        ok, reason = auto_configure_voice_profile(config)
        assert ok is True
        assert reason is None

        assert os.environ.get("JARVIS_TTS_ENGINE") == "piper"
        assert os.environ.get("JARVIS_TTS_ENGINE_STRICT") == "1"
        assert os.environ.get("JARVIS_PIPER_BACKEND") == "python"
        assert os.environ.get("JARVIS_PIPER_INTRA_OP_THREADS") == "1"
        assert os.environ.get("JARVIS_PIPER_INTER_OP_THREADS") == "1"
        assert os.environ.get("JARVIS_VOICE_PHASE1") == "1"
        assert os.environ.get("JARVIS_TTS_ACK_PHRASE")
        assert os.environ.get("JARVIS_TTS_ACK_PHRASE_WARMUP_BLOCKING") == "1"
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def test_auto_configure_voice_profile_fails_without_model() -> None:
    config = SimpleNamespace(tts_mode="local")

    old_env = os.environ.copy()
    try:
        os.environ["JARVIS_AUTO_CONFIGURE"] = "1"
        os.environ["JARVIS_TTS_ENGINE"] = "piper"
        os.environ["JARVIS_TTS_ENGINE_STRICT"] = "1"
        os.environ["JARVIS_PIPER_MODELS_DIR"] = "/tmp/does-not-exist"

        ok, reason = auto_configure_voice_profile(config)
        assert ok is False
        assert isinstance(reason, str)
        assert "Piper" in reason
    finally:
        os.environ.clear()
        os.environ.update(old_env)
