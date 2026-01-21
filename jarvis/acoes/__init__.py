"""
Automation module with separated desktop and web automation.

Desktop: AT-SPI + xdotool (NEVER Playwright)
Web: Playwright (NEVER controls desktop)
"""

from __future__ import annotations

from .desktop import DesktopAutomation
from .web import WebAutomation, check_playwright_deps

__all__ = ["DesktopAutomation", "WebAutomation", "get_automation_driver"]


def get_automation_driver(
    session_type: str = "unknown",
    enable_web: bool = True,
) -> AutomationRouter:
    """Get automation driver with desktop/web separation."""
    return AutomationRouter(session_type=session_type, enable_web=enable_web)


class AutomationRouter:
    """
    Routes automation requests to appropriate driver.

    Desktop actions -> DesktopAutomation
    Web actions -> WebAutomation
    """

    def __init__(
        self,
        session_type: str = "unknown",
        enable_web: bool = True,
    ) -> None:
        self.desktop = DesktopAutomation(session_type=session_type)
        self.web = WebAutomation() if enable_web else None

    def execute(self, action_type: str, params: dict) -> str | None:
        """
        Execute an action, routing to appropriate driver.

        Returns error message or None on success.
        """
        # Web-specific actions
        if action_type in {"navigate", "web_click", "web_fill", "web_screenshot"}:
            if self.web is None:
                return "web_automation_disabled"
            deps = check_playwright_deps()
            if not deps.get("playwright_installed"):
                return "playwright_not_installed (pip install playwright)"
            if not deps.get("browsers_installed"):
                return "playwright_browsers_missing (playwright install chromium)"
            return self.web.execute(action_type, params)

        # Desktop actions
        desktop_actions = {
            "open_app",
            "type_text",
            "hotkey",
            "click",
            "wait",
            "open_url",
            "scroll",
            "drag",
        }
        if action_type in desktop_actions:
            return self.desktop.execute(action_type, params)

        # Try desktop first for unknown actions
        return self.desktop.execute(action_type, params)
