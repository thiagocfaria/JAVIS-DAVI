"""
Web automation using Playwright.

This module handles:
- Browser navigation
- Form filling
- Element clicking
- Page scraping
- Screenshot capture

NEVER controls desktop - that's handled by desktop.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Page, Playwright

try:
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    sync_playwright = None
    HAS_PLAYWRIGHT = False

BrowserType: TypeAlias = "Browser"
PageType: TypeAlias = "Page"
PlaywrightType: TypeAlias = "Playwright"

if not TYPE_CHECKING:
    BrowserType = Any  # type: ignore[assignment]
    PageType = Any  # type: ignore[assignment]
    PlaywrightType = Any  # type: ignore[assignment]


class WebAutomation:
    """
    Web automation using Playwright.

    Features:
    - Browser navigation
    - Form interaction
    - Element detection
    - CAPTCHA/2FA detection (pause for human)
    - Screenshot capture
    """

    def __init__(self, headless: bool = False) -> None:
        self.headless = headless
        self._playwright: PlaywrightType | None = None
        self._browser: BrowserType | None = None
        self._page: PageType | None = None

    def is_available(self) -> bool:
        """Check if Playwright is installed."""
        return HAS_PLAYWRIGHT

    def _ensure_browser(self) -> PageType:
        """Ensure browser is started and return page."""
        if not HAS_PLAYWRIGHT:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install"
            )

        if self._page is not None:
            return self._page

        if sync_playwright is None:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install"
            )

        try:
            self._playwright = sync_playwright().start()
            if self._playwright is not None:
                self._browser = self._playwright.chromium.launch(headless=self.headless)
                if self._browser is not None:
                    self._page = self._browser.new_page()
        except Exception:
            raise

        if self._page is None:
            raise RuntimeError("Failed to create browser page")

        return self._page

    def close(self) -> None:
        """Close browser and cleanup."""
        if self._page:
            self._page.close()
            self._page = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def execute(self, action_type: str, params: dict) -> str | None:
        """
        Execute a web action.

        Returns error message or None on success.
        """
        try:
            if action_type == "navigate":
                return self._navigate(params.get("url", ""))

            if action_type == "web_click":
                return self._click(params.get("selector", ""))

            if action_type == "web_fill":
                return self._fill(
                    params.get("selector", ""),
                    params.get("value", ""),
                )

            if action_type == "web_screenshot":
                return self._screenshot(params.get("path", ""))

            return f"unknown_web_action: {action_type}"

        except Exception as e:
            return f"web_error: {e}"

    def _navigate(self, url: str) -> str | None:
        """Navigate to URL."""
        if not url:
            return "missing_url"

        page = self._ensure_browser()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Check for CAPTCHA/2FA
            if self._detect_captcha_2fa(page):
                return "requires_human_intervention"

            return None
        except Exception as e:
            return f"navigate_failed: {e}"

    def _click(self, selector: str) -> str | None:
        """Click an element."""
        if not selector:
            return "missing_selector"

        page = self._ensure_browser()

        try:
            page.click(selector, timeout=10000)
            return None
        except Exception as e:
            return f"click_failed: {e}"

    def _fill(self, selector: str, value: str) -> str | None:
        """Fill a form field."""
        if not selector:
            return "missing_selector"

        page = self._ensure_browser()

        try:
            page.fill(selector, value, timeout=10000)
            return None
        except Exception as e:
            return f"fill_failed: {e}"

    def _screenshot(self, path: str) -> str | None:
        """Take a screenshot."""
        page = self._ensure_browser()

        try:
            if path:
                page.screenshot(path=path)
            else:
                page.screenshot(path="/tmp/jarvis_screenshot.png")
            return None
        except Exception as e:
            return f"screenshot_failed: {e}"

    def _detect_captcha_2fa(self, page: Page) -> bool:
        """
        Detect CAPTCHA or 2FA on page.

        Returns True if human intervention needed.
        """
        # Common CAPTCHA indicators
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            ".g-recaptcha",
            ".h-captcha",
            "[data-captcha]",
            "[class*='captcha']",
        ]

        # Common 2FA indicators
        twofa_selectors = [
            "input[name*='otp']",
            "input[name*='2fa']",
            "input[name*='code']",
            "[class*='verification']",
            "[class*='two-factor']",
        ]

        for selector in captcha_selectors + twofa_selectors:
            try:
                if page.locator(selector).count() > 0:
                    return True
            except Exception:
                pass

        return False

    def get_page_text(self) -> str:
        """Get all text content from current page."""
        if self._page is None:
            return ""

        try:
            return self._page.inner_text("body")
        except Exception:
            return ""

    def get_page_title(self) -> str:
        """Get current page title."""
        if self._page is None:
            return ""

        try:
            return self._page.title()
        except Exception:
            return ""

    def get_current_url(self) -> str:
        """Get current page URL."""
        if self._page is None:
            return ""

        try:
            return self._page.url
        except Exception:
            return ""

    def wait_for_selector(self, selector: str, timeout_ms: int = 30000) -> bool:
        """Wait for element to appear."""
        if self._page is None:
            return False

        try:
            self._page.wait_for_selector(selector, timeout=timeout_ms)
            return True
        except Exception:
            return False

    def extract_data(self, selectors: dict[str, str]) -> dict[str, Any]:
        """
        Extract data from page using selectors.

        Args:
            selectors: Dict of {field_name: css_selector}

        Returns:
            Dict of {field_name: extracted_value}
        """
        if self._page is None:
            return {}

        result = {}
        for name, selector in selectors.items():
            try:
                element = self._page.locator(selector).first
                if element:
                    result[name] = element.inner_text()
            except Exception:
                result[name] = None

        return result

    def fill_form(self, fields: dict[str, str]) -> list[str]:
        """
        Fill multiple form fields.

        Args:
            fields: Dict of {selector: value}

        Returns:
            List of error messages (empty if all successful)
        """
        errors = []

        for selector, value in fields.items():
            error = self._fill(selector, value)
            if error:
                errors.append(f"{selector}: {error}")

        return errors


def check_playwright_deps() -> dict:
    """Check Playwright dependencies."""
    return {
        "playwright_installed": HAS_PLAYWRIGHT,
        "browsers_installed": _check_browsers_installed(),
    }


def _check_browsers_installed() -> bool:
    """Check if Playwright browsers are installed."""
    if not HAS_PLAYWRIGHT:
        return False

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # Try to get executable path
            browser_path = p.chromium.executable_path
            return browser_path is not None
    except Exception:
        return False
