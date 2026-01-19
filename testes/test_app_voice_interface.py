from __future__ import annotations

import os
import sys
from types import SimpleNamespace


from jarvis.interface.entrada import app as app_module


def _make_config(tmp_path, stt_mode: str = "local"):
    return SimpleNamespace(
        stt_mode=stt_mode,
        chat_log_path=tmp_path / "chat.log",
        chat_inbox_path=tmp_path / "chat_inbox.txt",
        stop_file_path=tmp_path / "STOP",
        chat_open_command=None,
        chat_open_cooldown_s=5,
        chat_ui_command=None,
        chat_shortcut_combo="ctrl+shift+j",
        require_approval=True,
        dry_run=False,
    )


def test_ensure_stt_ready_returns_false_when_missing_audio(monkeypatch):
    class DummyConfig:
        stt_mode = "local"

    monkeypatch.setattr(
        app_module,
        "check_stt_deps",
        lambda: {"sounddevice": False, "numpy": False, "faster_whisper": False},
    )
    assert app_module._ensure_stt_ready(DummyConfig()) is False


def test_ensure_stt_ready_reports_missing_deps(monkeypatch, capsys):
    class DummyConfig:
        stt_mode = "local"

    monkeypatch.setattr(
        app_module,
        "check_stt_deps",
        lambda: {"sounddevice": False, "numpy": True, "faster_whisper": False},
    )
    assert app_module._ensure_stt_ready(DummyConfig()) is False
    output = capsys.readouterr().out
    assert "sounddevice" in output
    assert "faster-whisper" in output
    assert "pip install" in output


def test_ensure_stt_ready_returns_false_when_disabled(monkeypatch):
    class DummyConfig:
        stt_mode = "none"

    monkeypatch.setattr(
        app_module,
        "check_stt_deps",
        lambda: {"sounddevice": True, "numpy": True, "faster_whisper": True},
    )
    assert app_module._ensure_stt_ready(DummyConfig()) is False


def test_main_voice_calls_transcribe(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    calls = {"transcribe": 0}

    class DummyOrchestrator:
        def __init__(self, cfg):
            return None

        def transcribe_and_handle(self):
            calls["transcribe"] += 1

        def handle_text(self, text: str) -> None:
            return None

        def run_s3_loop(self, text: str) -> bool:
            return True

    class DummyInbox:
        def __init__(self, path):
            self._path = path

        def drain(self):
            return []

    monkeypatch.setattr(app_module, "load_config", lambda: config)
    monkeypatch.setattr(app_module, "ensure_dirs", lambda cfg: None)
    monkeypatch.setattr(
        app_module,
        "check_stt_deps",
        lambda: {"sounddevice": True, "numpy": True, "faster_whisper": True},
    )
    monkeypatch.setattr(app_module, "Orchestrator", DummyOrchestrator)
    monkeypatch.setattr(app_module, "ChatInbox", DummyInbox)
    monkeypatch.setattr(app_module, "stop_requested", lambda path: False)
    monkeypatch.setattr(sys, "argv", ["jarvis", "--voice"])

    assert app_module.main() == 0
    assert calls["transcribe"] == 1


def test_main_voice_loop_stops_on_kill_switch(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    calls = {"transcribe": 0}

    class DummyOrchestrator:
        def __init__(self, cfg):
            return None

        def transcribe_and_handle(self):
            calls["transcribe"] += 1

        def handle_text(self, text: str) -> None:
            return None

        def run_s3_loop(self, text: str) -> bool:
            return True

    class DummyInbox:
        def __init__(self, path):
            self._path = path

        def drain(self):
            return []

    monkeypatch.setattr(app_module, "load_config", lambda: config)
    monkeypatch.setattr(app_module, "ensure_dirs", lambda cfg: None)
    monkeypatch.setattr(
        app_module,
        "check_stt_deps",
        lambda: {"sounddevice": True, "numpy": True, "faster_whisper": True},
    )
    monkeypatch.setattr(app_module, "Orchestrator", DummyOrchestrator)
    monkeypatch.setattr(app_module, "ChatInbox", DummyInbox)
    monkeypatch.setattr(app_module, "stop_requested", lambda path: True)
    monkeypatch.setattr(sys, "argv", ["jarvis", "--voice-loop"])

    assert app_module.main() == 0
    assert calls["transcribe"] == 0


def test_main_voice_loop_rechecks_stt_deps(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    calls = {"transcribe": 0, "deps": 0}

    class DummyOrchestrator:
        def __init__(self, cfg):
            return None

        def transcribe_and_handle(self):
            calls["transcribe"] += 1

        def handle_text(self, text: str) -> None:
            return None

        def run_s3_loop(self, text: str) -> bool:
            return True

    class DummyInbox:
        def __init__(self, path):
            self._path = path

        def drain(self):
            return []

    def fake_check_stt_deps():
        calls["deps"] += 1
        if calls["deps"] >= 2:
            return {"sounddevice": False, "numpy": False, "faster_whisper": False}
        return {"sounddevice": True, "numpy": True, "faster_whisper": True}

    monkeypatch.setattr(app_module, "load_config", lambda: config)
    monkeypatch.setattr(app_module, "ensure_dirs", lambda cfg: None)
    monkeypatch.setattr(app_module, "check_stt_deps", fake_check_stt_deps)
    monkeypatch.setattr(app_module, "Orchestrator", DummyOrchestrator)
    monkeypatch.setattr(app_module, "ChatInbox", DummyInbox)
    monkeypatch.setattr(app_module, "stop_requested", lambda path: False)
    monkeypatch.setattr(app_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(sys, "argv", ["jarvis", "--voice-loop"])

    assert app_module.main() == 0
    assert calls["deps"] >= 2
    assert calls["transcribe"] == 0


def test_main_voice_loop_uses_sleep_arg(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    calls = {"sleep": [], "stop": 0}

    class DummyOrchestrator:
        def __init__(self, cfg):
            return None

        def transcribe_and_handle(self):
            return None

        def handle_text(self, text: str) -> None:
            return None

        def run_s3_loop(self, text: str) -> bool:
            return True

    class DummyInbox:
        def __init__(self, path):
            self._path = path

        def drain(self):
            return []

    def fake_stop(_path):
        calls["stop"] += 1
        return calls["stop"] > 1

    monkeypatch.setattr(app_module, "load_config", lambda: config)
    monkeypatch.setattr(app_module, "ensure_dirs", lambda cfg: None)
    monkeypatch.setattr(
        app_module,
        "check_stt_deps",
        lambda: {"sounddevice": True, "numpy": True, "faster_whisper": True},
    )
    monkeypatch.setattr(app_module, "Orchestrator", DummyOrchestrator)
    monkeypatch.setattr(app_module, "ChatInbox", DummyInbox)
    monkeypatch.setattr(app_module, "stop_requested", fake_stop)
    monkeypatch.setattr(
        app_module.time, "sleep", lambda value: calls["sleep"].append(value)
    )
    monkeypatch.setattr(
        sys, "argv", ["jarvis", "--voice-loop", "--voice-loop-sleep", "0.2"]
    )

    assert app_module.main() == 0
    assert calls["sleep"] == [0.2]


def test_main_voice_loop_respects_max_iter(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    calls = {"transcribe": 0}

    class DummyOrchestrator:
        def __init__(self, cfg):
            return None

        def transcribe_and_handle(self):
            calls["transcribe"] += 1

        def handle_text(self, text: str) -> None:
            return None

        def run_s3_loop(self, text: str) -> bool:
            return True

    class DummyInbox:
        def __init__(self, path):
            self._path = path

        def drain(self):
            return []

    monkeypatch.setattr(app_module, "load_config", lambda: config)
    monkeypatch.setattr(app_module, "ensure_dirs", lambda cfg: None)
    monkeypatch.setattr(
        app_module,
        "check_stt_deps",
        lambda: {"sounddevice": True, "numpy": True, "faster_whisper": True},
    )
    monkeypatch.setattr(app_module, "Orchestrator", DummyOrchestrator)
    monkeypatch.setattr(app_module, "ChatInbox", DummyInbox)
    monkeypatch.setattr(app_module, "stop_requested", lambda path: False)
    monkeypatch.setattr(app_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "jarvis",
            "--voice-loop",
            "--voice-loop-max-iter",
            "2",
            "--voice-loop-sleep",
            "0",
        ],
    )

    assert app_module.main() == 0
    assert calls["transcribe"] == 2


def test_main_sets_audio_env_from_cli(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    monkeypatch.setattr(app_module, "load_config", lambda: config)
    monkeypatch.setattr(app_module, "ensure_dirs", lambda cfg: None)
    monkeypatch.setattr(app_module, "run_preflight", lambda cfg, **kwargs: object())
    monkeypatch.setattr(app_module, "format_report", lambda report: "ok")
    monkeypatch.delenv("JARVIS_AUDIO_DEVICE", raising=False)
    monkeypatch.delenv("JARVIS_AUDIO_CAPTURE_SR", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "jarvis",
            "--preflight",
            "--audio-device",
            "3",
            "--audio-capture-sr",
            "44100",
        ],
    )

    assert app_module.main() == 0
    assert app_module.os.environ.get("JARVIS_AUDIO_DEVICE") == "3"
    assert app_module.os.environ.get("JARVIS_AUDIO_CAPTURE_SR") == "44100"
    monkeypatch.delenv("JARVIS_AUDIO_DEVICE", raising=False)
    monkeypatch.delenv("JARVIS_AUDIO_CAPTURE_SR", raising=False)


def test_main_enable_shortcut_uses_env_combo(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    config.__dict__.pop("chat_shortcut_combo", None)
    captured = {}

    class DummyShortcut:
        def __init__(self, chat_command=None, shortcut_combo=None):
            captured["combo"] = shortcut_combo

        def start(self) -> bool:
            return True

        def stop(self) -> None:
            return None

    class DummyOrchestrator:
        def __init__(self, cfg):
            return None

        def handle_text(self, text: str) -> None:
            return None

        def run_s3_loop(self, text: str) -> bool:
            return True

    class DummyInbox:
        def __init__(self, path):
            self._path = path

        def drain(self):
            return []

    monkeypatch.setenv("JARVIS_CHAT_SHORTCUT_COMBO", "alt+shift+k")
    monkeypatch.setattr(app_module, "load_config", lambda: config)
    monkeypatch.setattr(app_module, "ensure_dirs", lambda cfg: None)
    monkeypatch.setattr(app_module, "ChatShortcut", DummyShortcut)
    monkeypatch.setattr(app_module, "Orchestrator", DummyOrchestrator)
    monkeypatch.setattr(app_module, "ChatInbox", DummyInbox)
    monkeypatch.setattr(
        app_module,
        "check_stt_deps",
        lambda: {"sounddevice": True, "numpy": True, "faster_whisper": True},
    )
    monkeypatch.setattr(sys, "argv", ["jarvis", "--enable-shortcut", "--text", "oi"])

    assert app_module.main() == 0
    assert captured.get("combo") == "alt+shift+k"


def test_main_open_chat_invokes_chatlog(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    called = {"open": 0}

    class DummyChatLog:
        def __init__(self, *args, **kwargs):
            return None

        def open(self):
            called["open"] += 1

    monkeypatch.setattr(app_module, "load_config", lambda: config)
    monkeypatch.setattr(app_module, "ensure_dirs", lambda cfg: None)
    monkeypatch.setattr(sys, "argv", ["jarvis", "--open-chat"])
    import jarvis.interface.infra.chat_log as chat_log_module

    monkeypatch.setattr(chat_log_module, "ChatLog", DummyChatLog)

    assert app_module.main() == 0
    assert called["open"] == 1


def test_main_chat_ui_calls_chat_ui_main(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    called = {"chat_ui": 0}

    class DummyTk:
        def __init__(self):
            return None

    monkeypatch.setitem(sys.modules, "tkinter", type("TkDummy", (), {"Tk": DummyTk}))

    import jarvis.interface.entrada.chat_ui as chat_ui_module

    monkeypatch.setattr(
        chat_ui_module, "main", lambda: called.__setitem__("chat_ui", 1) or 0
    )

    monkeypatch.setattr(app_module, "load_config", lambda: config)
    monkeypatch.setattr(app_module, "ensure_dirs", lambda cfg: None)
    monkeypatch.setattr(sys, "argv", ["jarvis", "--chat-ui"])

    assert app_module.main() == 0
    assert called["chat_ui"] == 1


def test_main_gui_panel_invokes_panel(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    called = {"run": 0}

    class DummyTk:
        def __init__(self):
            return None

    monkeypatch.setitem(sys.modules, "tkinter", type("TkDummy", (), {"Tk": DummyTk}))

    class DummyPanel:
        def __init__(self, orchestrator, chat_shortcut=None, followup_poll_ms=None):
            return None

        def run(self):
            called["run"] += 1

    class DummyOrchestrator:
        def __init__(self, cfg):
            return None

        def transcribe_and_handle(self):
            return None

        def handle_text(self, text: str) -> None:
            return None

        def run_s3_loop(self, text: str) -> bool:
            return True

    class DummyInbox:
        def __init__(self, path):
            self._path = path

        def drain(self):
            return []

    import jarvis.interface.entrada.gui_panel as gui_panel_module

    monkeypatch.setattr(gui_panel_module, "JarvisPanel", DummyPanel)

    monkeypatch.setattr(app_module, "load_config", lambda: config)
    monkeypatch.setattr(app_module, "ensure_dirs", lambda cfg: None)
    monkeypatch.setattr(app_module, "Orchestrator", DummyOrchestrator)
    monkeypatch.setattr(app_module, "ChatInbox", DummyInbox)
    monkeypatch.setattr(app_module, "stop_requested", lambda path: False)
    monkeypatch.setattr(sys, "argv", ["jarvis", "--gui-panel"])

    assert app_module.main() == 0
    assert called["run"] == 1


def test_main_gui_panel_sets_followup_poll_env(monkeypatch, tmp_path):
    config = _make_config(tmp_path)
    captured = {"run": 0, "poll": None}

    class DummyTk:
        def __init__(self):
            return None

    monkeypatch.setitem(sys.modules, "tkinter", type("TkDummy", (), {"Tk": DummyTk}))

    class DummyPanel:
        def __init__(self, orchestrator, chat_shortcut=None, followup_poll_ms=None):
            captured["poll"] = followup_poll_ms

        def run(self):
            captured["run"] += 1

    class DummyOrchestrator:
        def __init__(self, cfg):
            return None

        def transcribe_and_handle(self):
            return None

        def handle_text(self, text: str) -> None:
            return None

        def run_s3_loop(self, text: str) -> bool:
            return True

    class DummyInbox:
        def __init__(self, path):
            self._path = path

        def drain(self):
            return []

    import jarvis.interface.entrada.gui_panel as gui_panel_module

    monkeypatch.setattr(gui_panel_module, "JarvisPanel", DummyPanel)

    monkeypatch.setattr(app_module, "load_config", lambda: config)
    monkeypatch.setattr(app_module, "ensure_dirs", lambda cfg: None)
    monkeypatch.setattr(app_module, "Orchestrator", DummyOrchestrator)
    monkeypatch.setattr(app_module, "ChatInbox", DummyInbox)
    monkeypatch.setattr(app_module, "stop_requested", lambda path: False)
    monkeypatch.setattr(
        sys,
        "argv",
        ["jarvis", "--gui-panel", "--gui-followup-poll-ms", "777"],
    )

    assert app_module.main() == 0
    assert os.environ.get("JARVIS_GUI_FOLLOWUP_POLL_MS") == "777"
    assert captured["poll"] == 777
    assert captured["run"] == 1
