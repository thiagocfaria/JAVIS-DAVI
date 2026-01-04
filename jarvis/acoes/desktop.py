"""
Desktop automation using AT-SPI and xdotool.

This module handles:
- Opening applications
- Typing text
- Keyboard shortcuts
- Mouse clicks (by coordinates or element search)
- Window management

NEVER uses Playwright - that's for web only.
"""
from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

# pyautogui/mouseinfo falham em ambientes sem DISPLAY; tratamos amplo para
# permitir execucao headless (preflight/smoke) sem quebrar import.
try:
    import pyautogui  # type: ignore
    pyautogui.FAILSAFE = True
except Exception:  # pragma: no cover - fallback defensivo
    pyautogui = None

try:
    import gi  # type: ignore
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi  # type: ignore
    HAS_ATSPI = True
except (ImportError, ValueError):
    Atspi = None
    HAS_ATSPI = False


def _find_ydotool_socket() -> str | None:
    env_socket = os.environ.get("YDTOOL_SOCKET")
    if env_socket and Path(env_socket).exists():
        return env_socket
    uid = os.getuid()
    candidates = [
        f"/run/user/{uid}/ydotoold.socket",
        f"/run/user/{uid}/ydotool_socket",
        f"/run/user/{uid}/.ydotool_socket",
        "/run/ydotoold.socket",
        "/tmp/.ydotool_socket",
        str(Path.home() / ".ydotool_socket"),
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    return None


class DesktopAutomation:
    """
    Desktop automation using AT-SPI and xdotool.

    Priority order for input:
    1. xdotool (most reliable on X11)
    2. wtype (for Wayland)
    3. ydotool (for Wayland, needs daemon)
    4. pyautogui (fallback)
    """

    def __init__(self, session_type: str = "unknown") -> None:
        self.session_type = session_type
        self.is_wayland = session_type.lower() == "wayland"

        # Check available tools
        self.has_xdotool = shutil.which("xdotool") is not None
        self.has_wtype = shutil.which("wtype") is not None
        self.has_ydotool = shutil.which("ydotool") is not None
        self.ydotool_socket = _find_ydotool_socket() if self.has_ydotool else None
        self.has_pyautogui = pyautogui is not None
        self.has_atspi = HAS_ATSPI

    def _run_ydotool(self, args: list[str], timeout: int = 10) -> None:
        if not self.has_ydotool or not self.ydotool_socket:
            raise RuntimeError("ydotool_not_ready")
        env = os.environ.copy()
        env["YDTOOL_SOCKET"] = self.ydotool_socket
        subprocess.run(["ydotool", *args], check=True, timeout=timeout, env=env)

    def execute(self, action_type: str, params: dict) -> str | None:
        """
        Execute a desktop action.

        Returns error message or None on success.
        """
        try:
            if action_type == "open_app":
                return self._open_app(params.get("app", ""))

            if action_type == "open_url":
                return self._open_url(params.get("url", ""))

            if action_type == "type_text":
                return self._type_text(
                    params.get("text", ""),
                    x=params.get("x"),
                    y=params.get("y"),
                    target=params.get("target"),
                    overwrite=bool(params.get("overwrite", False)),
                    enter=bool(params.get("enter", False)),
                )

            if action_type == "hotkey":
                return self._hotkey(params.get("combo", ""))

            if action_type == "click":
                return self._click(
                    params.get("x"),
                    params.get("y"),
                    params.get("target"),
                    button=params.get("button"),
                    clicks=params.get("clicks", 1),
                    hold_keys=params.get("hold_keys"),
                )

            if action_type == "scroll":
                amount = params.get("amount")
                if amount is None:
                    amount = params.get("dy", 0)
                return self._scroll(amount)

            if action_type == "drag":
                return self._drag(
                    params.get("start_x"),
                    params.get("start_y"),
                    params.get("end_x"),
                    params.get("end_y"),
                    button=params.get("button"),
                    hold_keys=params.get("hold_keys"),
                )

            if action_type == "wait":
                seconds = float(params.get("seconds", 1))
                time.sleep(seconds)
                return None

            return f"unknown_action: {action_type}"

        except Exception as e:
            return f"error: {e}"

    def _open_app(self, app: str) -> str | None:
        """Open an application."""
        if not app:
            return "missing_app"

        try:
            cmd = shlex.split(str(app))
            subprocess.Popen(
                cmd,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return None
        except Exception as e:
            return f"open_app_failed: {e}"

    def _open_url(self, url: str) -> str | None:
        """Open URL in default browser."""
        if not url:
            return "missing_url"

        try:
            subprocess.Popen(
                ["xdg-open", str(url)],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return None
        except Exception as e:
            return f"open_url_failed: {e}"

    def _type_text(
        self,
        text: str,
        x: int | None = None,
        y: int | None = None,
        target: str | None = None,
        overwrite: bool = False,
        enter: bool = False,
    ) -> str | None:
        """Type text using available input method."""
        if not text:
            return None

        if target or (x is not None and y is not None):
            click_error = self._click(x=x, y=y, target=target)
            if click_error:
                return click_error
            time.sleep(0.2)

        if overwrite:
            key = "command" if platform.system().lower() == "darwin" else "ctrl"
            hotkey_error = self._hotkey(f"{key}+a")
            if hotkey_error:
                return hotkey_error
            time.sleep(0.05)
            backspace_error = self._hotkey("backspace")
            if backspace_error:
                return backspace_error
            time.sleep(0.05)

        typed = False

        # Try xdotool first (X11)
        if self.has_xdotool and not self.is_wayland:
            try:
                subprocess.run(
                    ["xdotool", "type", "--delay", "20", text],
                    check=True,
                    timeout=30,
                )
                typed = True
            except Exception:
                pass

        # Try wtype (Wayland)
        if not typed and self.has_wtype and self.is_wayland:
            try:
                subprocess.run(["wtype", text], check=True, timeout=30)
                typed = True
            except Exception:
                pass

        # Try ydotool (Wayland, requires daemon)
        if not typed and self.has_ydotool and self.ydotool_socket:
            try:
                self._run_ydotool(["type", text], timeout=30)
                typed = True
            except Exception:
                pass

        # Fallback to pyautogui
        if not typed and self.has_pyautogui:
            try:
                pyautogui.write(text, interval=0.02)
                typed = True
            except Exception:
                pass

        if not typed:
            return "no_input_driver_available"

        if enter:
            enter_error = self._hotkey("enter")
            if enter_error:
                return enter_error

        return None

    def _hotkey(self, combo: str) -> str | None:
        """Press keyboard shortcut."""
        if not combo:
            return "missing_combo"

        # Normalize combo format
        combo = combo.replace("+", " ").replace("  ", " ")

        # Try xdotool first
        if self.has_xdotool and not self.is_wayland:
            try:
                # xdotool expects "ctrl+c" format
                xdotool_combo = combo.replace(" ", "+")
                subprocess.run(
                    ["xdotool", "key", xdotool_combo],
                    check=True,
                    timeout=10,
                )
                return None
            except Exception:
                pass

        # Try wtype for Wayland
        if self.has_wtype and self.is_wayland:
            try:
                # wtype uses -M for modifiers
                keys = combo.split()
                cmd = ["wtype"]
                for key in keys[:-1]:  # Modifiers
                    cmd.extend(["-M", key.lower()])
                cmd.extend(["-k", keys[-1]])  # Final key
                subprocess.run(cmd, check=True, timeout=10)
                return None
            except Exception:
                pass

        # Fallback to pyautogui
        if self.has_pyautogui:
            try:
                keys = [k.strip().lower() for k in combo.split()]
                pyautogui.hotkey(*keys)
                return None
            except Exception:
                pass

        return "no_hotkey_driver_available"

    def _click(
        self,
        x: int | None = None,
        y: int | None = None,
        target: str | None = None,
        button: str | int | None = None,
        clicks: int = 1,
        hold_keys: list[str] | None = None,
    ) -> str | None:
        """Click at coordinates or on element."""
        # If target specified, try to find it via AT-SPI
        if target and self.has_atspi:
            coords = self._find_element_atspi(target)
            if coords:
                x, y = coords

        if x is None or y is None:
            return "missing_coordinates"

        if isinstance(hold_keys, str):
            hold_keys = [hold_keys]
        hold_keys = hold_keys or []
        button_name = str(button or "left").lower()
        button_map = {"left": 1, "middle": 2, "right": 3}
        button_num = button_map.get(button_name, 1)
        try:
            click_count = max(1, int(clicks))
        except Exception:
            click_count = 1

        # Try xdotool
        if self.has_xdotool and not self.is_wayland:
            try:
                for key in hold_keys:
                    subprocess.run(["xdotool", "keydown", key], check=True, timeout=5)
                subprocess.run(
                    ["xdotool", "mousemove", str(x), str(y)],
                    check=True,
                    timeout=10,
                )
                subprocess.run(
                    ["xdotool", "click", "--repeat", str(click_count), str(button_num)],
                    check=True,
                    timeout=10,
                )
                for key in hold_keys:
                    subprocess.run(["xdotool", "keyup", key], check=True, timeout=5)
                return None
            except Exception:
                pass

        # Try ydotool on Wayland
        if self.has_ydotool and self.ydotool_socket:
            try:
                self._run_ydotool(["mousemove", "--absolute", "-x", str(x), "-y", str(y)])
                if button_num != 1:
                    return "unsupported_button_on_ydotool"
                for _ in range(click_count):
                    self._run_ydotool(["click", "0xC0"])
                return None
            except Exception:
                pass

        # Fallback to pyautogui
        if self.has_pyautogui:
            try:
                for key in hold_keys:
                    pyautogui.keyDown(key)
                pyautogui.click(x, y, clicks=click_count, button=button_name)
                for key in hold_keys:
                    pyautogui.keyUp(key)
                return None
            except Exception:
                pass

        return "no_click_driver_available"

    def _drag(
        self,
        start_x: int | None = None,
        start_y: int | None = None,
        end_x: int | None = None,
        end_y: int | None = None,
        button: str | int | None = None,
        hold_keys: list[str] | None = None,
    ) -> str | None:
        if None in {start_x, start_y, end_x, end_y}:
            return "missing_coordinates"

        if isinstance(hold_keys, str):
            hold_keys = [hold_keys]
        hold_keys = hold_keys or []
        button_name = str(button or "left").lower()
        button_map = {"left": 1, "middle": 2, "right": 3}
        button_num = button_map.get(button_name, 1)

        if self.has_xdotool and not self.is_wayland:
            try:
                for key in hold_keys:
                    subprocess.run(["xdotool", "keydown", key], check=True, timeout=5)
                subprocess.run(["xdotool", "mousemove", str(start_x), str(start_y)], check=True, timeout=10)
                subprocess.run(["xdotool", "mousedown", str(button_num)], check=True, timeout=10)
                subprocess.run(["xdotool", "mousemove", str(end_x), str(end_y)], check=True, timeout=10)
                subprocess.run(["xdotool", "mouseup", str(button_num)], check=True, timeout=10)
                for key in hold_keys:
                    subprocess.run(["xdotool", "keyup", key], check=True, timeout=5)
                return None
            except Exception:
                pass

        if self.has_pyautogui:
            try:
                for key in hold_keys:
                    pyautogui.keyDown(key)
                pyautogui.moveTo(start_x, start_y)
                pyautogui.dragTo(end_x, end_y, duration=1.0, button=button_name)
                for key in hold_keys:
                    pyautogui.keyUp(key)
                return None
            except Exception:
                pass

        return "no_drag_driver_available"

    def _scroll(self, amount: int) -> str | None:
        """Scroll screen. Positive=down, negative=up."""
        try:
            amount_int = int(amount)
        except Exception:
            amount_int = 0

        if amount_int == 0:
            return None

        # Try xdotool on X11
        if self.has_xdotool and not self.is_wayland:
            try:
                button = "5" if amount_int > 0 else "4"  # 5=down, 4=up
                count = str(abs(amount_int))
                subprocess.run(
                    ["xdotool", "click", "--repeat", count, "--delay", "20", button],
                    check=True,
                    timeout=10,
                )
                return None
            except Exception:
                pass

        # Wayland: approximate scroll via PageUp/PageDown
        if self.has_wtype and self.is_wayland:
            try:
                key = "Page_Down" if amount_int > 0 else "Page_Up"
                for _ in range(abs(amount_int)):
                    subprocess.run(["wtype", "-k", key], check=True, timeout=10)
                return None
            except Exception:
                pass

        if self.has_ydotool and self.ydotool_socket:
            try:
                keycode = "109" if amount_int > 0 else "104"  # PageDown/PageUp
                for _ in range(abs(amount_int)):
                    self._run_ydotool(["key", f"{keycode}:1", f"{keycode}:0"])
                return None
            except Exception:
                pass

        # Fallback to pyautogui
        if self.has_pyautogui:
            try:
                # pyautogui positive = up, negative = down
                pyautogui.scroll(-amount_int * 100)
                return None
            except Exception:
                pass

        return "no_scroll_driver_available"

    def _find_element_atspi(self, label: str) -> tuple[int, int] | None:
        """
        Find element by label using AT-SPI accessibility API.

        Returns (x, y) center coordinates or None.
        """
        if not self.has_atspi:
            return None

        try:
            desktop = Atspi.get_desktop(0)
            return self._search_atspi_tree(desktop, label.lower())
        except Exception:
            return None

    def _search_atspi_tree(
        self,
        node,
        label: str,
        depth: int = 0,
        max_depth: int = 10,
    ) -> tuple[int, int] | None:
        """Recursively search AT-SPI tree for element."""
        if depth > max_depth:
            return None

        try:
            # Check this node
            name = node.get_name()
            if name and label in name.lower():
                # Get component interface for coordinates
                component = node.get_component_iface()
                if component:
                    rect = component.get_extents(Atspi.CoordType.SCREEN)
                    x = rect.x + rect.width // 2
                    y = rect.y + rect.height // 2
                    return (x, y)

            # Search children
            child_count = node.get_child_count()
            for i in range(child_count):
                child = node.get_child_at_index(i)
                if child:
                    result = self._search_atspi_tree(child, label, depth + 1, max_depth)
                    if result:
                        return result
        except Exception:
            pass

        return None

    def get_active_window(self) -> dict | None:
        """Get information about the active window."""
        if self.has_xdotool and not self.is_wayland:
            try:
                result = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return {"title": result.stdout.strip()}
            except Exception:
                pass

        return None

    def list_windows(self) -> list[dict]:
        """List all visible windows."""
        windows = []

        if self.has_xdotool and not self.is_wayland:
            try:
                result = subprocess.run(
                    ["xdotool", "search", "--name", ""],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    for wid in result.stdout.strip().split("\n"):
                        if wid:
                            name_result = subprocess.run(
                                ["xdotool", "getwindowname", wid],
                                capture_output=True,
                                text=True,
                                timeout=5,
                            )
                            if name_result.returncode == 0:
                                windows.append({
                                    "id": wid,
                                    "title": name_result.stdout.strip(),
                                })
            except Exception:
                pass

        return windows

    def check_available_tools(self) -> dict:
        """Check which automation tools are available."""
        return {
            "xdotool": self.has_xdotool,
            "wtype": self.has_wtype,
            "ydotool": self.has_ydotool,
            "ydotool_socket": self.ydotool_socket,
            "pyautogui": self.has_pyautogui,
            "atspi": self.has_atspi,
            "session_type": self.session_type,
            "is_wayland": self.is_wayland,
        }
