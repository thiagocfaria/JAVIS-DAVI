from __future__ import annotations

import shlex
import shutil
import subprocess
import time

from ..cerebro.actions import Action

try:
    import pyautogui  # type: ignore
except Exception:
    pyautogui = None


class AutomationDriver:
    def __init__(self, session_type: str) -> None:
        self.session_type = session_type
        self.has_xdotool = shutil.which("xdotool") is not None
        self.has_wtype = shutil.which("wtype") is not None
        self.has_ydotool = shutil.which("ydotool") is not None

    def execute(self, action: Action) -> str | None:
        action_type = action.action_type
        params = action.params or {}

        if action_type == "open_app":
            app = params.get("app")
            if not app:
                return "missing_app"
            try:
                cmd = shlex.split(str(app))
                subprocess.Popen(cmd, start_new_session=True)
                return None
            except Exception:
                return "open_app_failed"

        if action_type == "open_url":
            url = params.get("url")
            if not url:
                return "missing_url"
            try:
                subprocess.Popen(["xdg-open", str(url)], start_new_session=True)
                return None
            except Exception:
                return "open_url_failed"

        if action_type == "type_text":
            text = params.get("text", "")
            try:
                self._type_text(str(text))
                return None
            except Exception:
                return "type_text_failed"

        if action_type == "hotkey":
            combo = params.get("combo", "")
            try:
                self._hotkey(str(combo))
                return None
            except Exception:
                return "hotkey_failed"

        if action_type == "wait":
            seconds = float(params.get("seconds", 1))
            time.sleep(seconds)
            return None

        if action_type == "scroll":
            amount = params.get("amount")
            if amount is None:
                amount = params.get("dy", 0)
            amount = int(amount)
            if amount == 0:
                return None
            if pyautogui:
                pyautogui.scroll(-amount * 100)
                return None
            if self.has_xdotool:
                button = "5" if amount > 0 else "4"
                subprocess.run(
                    [
                        "xdotool",
                        "click",
                        "--repeat",
                        str(abs(amount)),
                        "--delay",
                        "20",
                        button,
                    ],
                    check=False,
                )
                return None
            return "scroll_failed"

        return "unknown_action"

    def _type_text(self, text: str) -> None:
        if pyautogui:
            pyautogui.write(text, interval=0.02)
            return
        if self.has_wtype:
            subprocess.run(["wtype", text], check=False)
            return
        if self.has_xdotool:
            subprocess.run(["xdotool", "type", "--delay", "20", text], check=False)
            return
        if self.has_ydotool:
            subprocess.run(["ydotool", "type", text], check=False)
            return
        raise RuntimeError(
            "No input driver available. Install pyautogui, wtype, or xdotool."
        )

    def _hotkey(self, combo: str) -> None:
        if pyautogui:
            keys = [key.strip() for key in combo.replace("+", " ").split()]
            pyautogui.hotkey(*keys)
            return
        if self.has_xdotool:
            subprocess.run(["xdotool", "key", combo], check=False)
            return
        raise RuntimeError("No hotkey driver available. Install pyautogui or xdotool.")
