from __future__ import annotations

import importlib
import sys
import types

import pytest


def _build_dummy_tk(entry_value: str = "hello"):
    module = types.SimpleNamespace()
    module._entry_value = entry_value

    class DummyRoot:
        def __init__(self):
            self._exists = True

        def title(self, *args, **kwargs):
            return None

        def geometry(self, *args, **kwargs):
            return None

        def attributes(self, *args, **kwargs):
            return None

        def resizable(self, *args, **kwargs):
            return None

        def protocol(self, *args, **kwargs):
            return None

        def after(self, *args, **kwargs):
            if len(args) >= 2 and callable(args[1]):
                args[1]()
            return None

        def mainloop(self):
            return None

        def destroy(self):
            self._exists = False

        def winfo_exists(self):
            return self._exists

    class DummyWidget:
        def pack(self, *args, **kwargs):
            return None

    class DummyText(DummyWidget):
        def __init__(self, *args, **kwargs):
            self.contents = []
            self.state = "normal"

        def configure(self, *args, **kwargs):
            if "state" in kwargs:
                self.state = kwargs["state"]

        def insert(self, *args, **kwargs):
            if len(args) >= 2:
                self.contents.append(str(args[1]))

        def see(self, *args, **kwargs):
            return None

    class DummyFrame(DummyWidget):
        def __init__(self, *args, **kwargs):
            return None

    class DummyEntry(DummyWidget):
        def __init__(self, *args, **kwargs):
            self._value = module._entry_value
            self.state = "normal"

        def get(self):
            return self._value

        def delete(self, *args, **kwargs):
            self._value = ""

        def bind(self, *args, **kwargs):
            return None

        def focus_set(self):
            return None

        def configure(self, *args, **kwargs):
            if "state" in kwargs:
                self.state = kwargs["state"]

        def set_value(self, value: str) -> None:
            self._value = value

    class DummyLabel(DummyWidget):
        def __init__(self, *args, **kwargs):
            self.text = kwargs.get("text", "")

        def configure(self, *args, **kwargs):
            if "text" in kwargs:
                self.text = kwargs["text"]

    class DummyButton(DummyWidget):
        def __init__(self, *args, **kwargs):
            self.text = kwargs.get("text", "")
            self.command = kwargs.get("command")
            self.state = "normal"

        def configure(self, *args, **kwargs):
            if "text" in kwargs:
                self.text = kwargs["text"]
            if "state" in kwargs:
                self.state = kwargs["state"]

    module.Tk = DummyRoot
    module.Text = DummyText
    module.Frame = DummyFrame
    module.Entry = DummyEntry
    module.Label = DummyLabel
    module.Button = DummyButton

    return module


def test_gui_panel_on_send_calls_orchestrator(monkeypatch):
    tk_dummy = _build_dummy_tk(entry_value="abrir navegador")
    monkeypatch.setitem(sys.modules, "tkinter", tk_dummy)

    gui_panel = importlib.import_module("jarvis.entrada.gui_panel")
    importlib.reload(gui_panel)

    calls = {"text": None}

    class DummyOrch:
        def handle_text(self, text: str) -> None:
            calls["text"] = text

    class DummyThread:
        def __init__(self, target=None, args=(), daemon=False):
            self._target = target
            self._args = args

        def start(self):
            if self._target:
                self._target(*self._args)

    monkeypatch.setattr(gui_panel.threading, "Thread", DummyThread)

    panel = gui_panel.JarvisPanel(DummyOrch())
    panel._on_send()

    assert calls["text"] == "abrir navegador"
    assert panel._busy is False


def test_gui_panel_toggle_microphone(monkeypatch):
    tk_dummy = _build_dummy_tk(entry_value="")
    monkeypatch.setitem(sys.modules, "tkinter", tk_dummy)

    gui_panel = importlib.import_module("jarvis.entrada.gui_panel")
    importlib.reload(gui_panel)

    class DummyOrch:
        def handle_text(self, text: str) -> None:
            return None

    panel = gui_panel.JarvisPanel(DummyOrch())
    panel._toggle_microphone()
    assert "Ligado" in panel.mic_button.text
    panel._toggle_microphone()
    assert "Desligado" in panel.mic_button.text


def test_gui_panel_set_busy_updates_state(monkeypatch):
    tk_dummy = _build_dummy_tk(entry_value="")
    monkeypatch.setitem(sys.modules, "tkinter", tk_dummy)

    gui_panel = importlib.import_module("jarvis.entrada.gui_panel")
    importlib.reload(gui_panel)

    class DummyOrch:
        def handle_text(self, text: str) -> None:
            return None

    panel = gui_panel.JarvisPanel(DummyOrch())
    panel._set_busy(True)
    assert panel.send_button.state == "disabled"
    assert panel.command_entry.state == "disabled"
    assert panel.status_label.text == "Executando..."

    panel._set_busy(False)
    assert panel.send_button.state == "normal"
    assert panel.command_entry.state == "normal"
    assert panel.status_label.text == "Pronto para ouvir comandos"


def test_gui_panel_cancel_toggles_stop_file(monkeypatch, tmp_path):
    tk_dummy = _build_dummy_tk(entry_value="")
    monkeypatch.setitem(sys.modules, "tkinter", tk_dummy)

    gui_panel = importlib.import_module("jarvis.entrada.gui_panel")
    importlib.reload(gui_panel)

    stop_path = tmp_path / "STOP"

    class DummyConfig:
        stop_file_path = stop_path

    class DummyOrch:
        config = DummyConfig()

        def handle_text(self, text: str) -> None:
            return None

    panel = gui_panel.JarvisPanel(DummyOrch())
    panel._request_cancel()
    assert stop_path.exists()

    panel._request_cancel()
    assert not stop_path.exists()
