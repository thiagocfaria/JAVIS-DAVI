import tempfile

from jarvis.acoes.desktop import DesktopAutomation
from jarvis.cerebro.config import load_config
from jarvis.entrada.preflight import run_preflight


def test_preflight_headless_treats_desktop_as_warning(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("JARVIS_DATA_DIR", tmpdir)
        monkeypatch.setenv("JARVIS_HEADLESS", "1")
        monkeypatch.setenv("XDG_SESSION_TYPE", "unknown")
        monkeypatch.setenv("JARVIS_STT_MODE", "none")
        monkeypatch.setenv("JARVIS_TTS_MODE", "none")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

        def _fake_tools(self):
            return {
                "xdotool": False,
                "wtype": False,
                "ydotool": False,
                "ydotool_socket": None,
                "pyautogui": False,
                "atspi": False,
                "session_type": "unknown",
                "is_wayland": False,
            }

        monkeypatch.setattr(DesktopAutomation, "check_available_tools", _fake_tools)

        config = load_config()
        report = run_preflight(config)

        assert not report.has_failures
        desktop_check = next(c for c in report.checks if c.name == "Acoes desktop")
        assert desktop_check.status == "WARN"
        assert "headless" in desktop_check.detail
