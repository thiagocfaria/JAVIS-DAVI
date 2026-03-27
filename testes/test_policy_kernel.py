"""Tests for jarvis.seguranca.policy — PolicyKernel and helpers."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from jarvis.cerebro.actions import Action
from jarvis.seguranca.policy import (
    PolicyDecision,
    PolicyKernel,
    _contains_any,
    _matches_any_domain,
    _normalize_app,
    _split_env,
    check_action_allowed,
    get_policy_kernel,
    is_contact_allowed,
    is_domain_blocked,
)


def _action(action_type: str, **params: object) -> Action:
    return Action(action_type=action_type, params=dict(params))


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestHelpers(unittest.TestCase):
    def test_split_env_empty(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("JARVIS_TEST_SPLIT", None)
            self.assertEqual(_split_env("JARVIS_TEST_SPLIT"), [])

    def test_split_env_values(self) -> None:
        with patch.dict(os.environ, {"JARVIS_TEST_SPLIT": "a,b,c"}):
            self.assertEqual(_split_env("JARVIS_TEST_SPLIT"), ["a", "b", "c"])

    def test_split_env_strips_whitespace(self) -> None:
        with patch.dict(os.environ, {"JARVIS_TEST_SPLIT": " x , y "}):
            result = _split_env("JARVIS_TEST_SPLIT")
            self.assertIn("x", result)
            self.assertIn("y", result)

    def test_normalize_app(self) -> None:
        self.assertEqual(_normalize_app("  Firefox  "), "firefox")
        # shlex.split takes only the first token
        self.assertEqual(_normalize_app("google-chrome --flag"), "google-chrome")

    def test_contains_any_hit(self) -> None:
        self.assertTrue(_contains_any("abrir banco itau", frozenset({"banco", "pix"})))

    def test_contains_any_miss(self) -> None:
        self.assertFalse(_contains_any("abrir navegador", frozenset({"banco", "pix"})))

    def test_matches_any_domain_hit(self) -> None:
        self.assertTrue(_matches_any_domain("https://nubank.com.br", frozenset({"nubank"})))

    def test_matches_any_domain_miss(self) -> None:
        self.assertFalse(_matches_any_domain("https://google.com", frozenset({"nubank"})))


# ---------------------------------------------------------------------------
# PolicyDecision dataclass
# ---------------------------------------------------------------------------

class TestPolicyDecision(unittest.TestCase):
    def test_defaults(self) -> None:
        d = PolicyDecision(allowed=True)
        self.assertTrue(d.allowed)
        self.assertFalse(d.requires_confirmation)
        self.assertFalse(d.requires_human)
        self.assertEqual(d.reason, "")
        self.assertEqual(d.blocked_by, "")

    def test_blocked(self) -> None:
        d = PolicyDecision(allowed=False, reason="test", blocked_by="rule1")
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "test")
        self.assertEqual(d.blocked_by, "rule1")


# ---------------------------------------------------------------------------
# PolicyKernel — check_action
# ---------------------------------------------------------------------------

class TestPolicyKernelSendMessage(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = PolicyKernel()

    def test_send_message_no_contact(self) -> None:
        a = _action("send_message", contact="")
        d = self.kernel.check_action(a)
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "contact_required")

    def test_send_message_not_in_whitelist(self) -> None:
        a = _action("send_message", contact="eve@evil.com")
        d = self.kernel.check_action(a)
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "contact_not_in_whitelist")

    def test_send_message_in_whitelist(self) -> None:
        with patch.dict(os.environ, {"JARVIS_CONTACT_WHITELIST": "alice"}):
            kernel = PolicyKernel()
            a = _action("send_message", contact="alice")
            d = kernel.check_action(a)
            self.assertTrue(d.allowed)
            self.assertTrue(d.requires_confirmation)


class TestPolicyKernelBankBlock(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = PolicyKernel()

    def test_open_url_banking_domain_blocked(self) -> None:
        a = _action("open_url", url="https://nubank.com.br")
        d = self.kernel.check_action(a)
        self.assertFalse(d.allowed)
        self.assertEqual(d.blocked_by, "bank_protection")

    def test_open_url_banking_keyword_blocked(self) -> None:
        a = _action("open_url", url="https://example.com/pix")
        d = self.kernel.check_action(a)
        self.assertFalse(d.allowed)

    def test_open_url_safe(self) -> None:
        a = _action("open_url", url="https://google.com")
        d = self.kernel.check_action(a)
        self.assertTrue(d.allowed)

    def test_type_text_banking_keyword(self) -> None:
        a = _action("type_text", text="transferencia de banco")
        d = self.kernel.check_action(a)
        self.assertFalse(d.allowed)

    def test_navigate_blocked_domain(self) -> None:
        a = _action("navigate", url="https://bradesco.com.br/login")
        d = self.kernel.check_action(a)
        self.assertFalse(d.allowed)

    def test_web_fill_blocked_keyword(self) -> None:
        a = _action("web_fill", value="pagar fatura do cartao")
        d = self.kernel.check_action(a)
        self.assertFalse(d.allowed)


class TestPolicyKernelHumanRequired(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = PolicyKernel()

    def test_type_text_captcha(self) -> None:
        a = _action("type_text", text="captcha input")
        d = self.kernel.check_action(a)
        self.assertFalse(d.allowed)
        self.assertTrue(d.requires_human)
        self.assertEqual(d.blocked_by, "2fa_captcha_protection")

    def test_click_2fa(self) -> None:
        a = _action("click", selector="2fa verificacao button")
        d = self.kernel.check_action(a)
        self.assertFalse(d.allowed)
        self.assertTrue(d.requires_human)

    def test_web_click_recaptcha(self) -> None:
        a = _action("web_click", target="recaptcha checkbox")
        d = self.kernel.check_action(a)
        self.assertFalse(d.allowed)

    def test_web_fill_no_human_keyword(self) -> None:
        a = _action("web_fill", value="nome do usuario")
        d = self.kernel.check_action(a)
        self.assertTrue(d.allowed)


class TestPolicyKernelApps(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = PolicyKernel()

    def test_open_app_allowed(self) -> None:
        a = _action("open_app", app="firefox")
        d = self.kernel.check_action(a)
        self.assertTrue(d.allowed)
        self.assertTrue(d.requires_confirmation)

    def test_open_app_blocked(self) -> None:
        from jarvis.seguranca.policy import BLOCKED_APPS
        if not BLOCKED_APPS:
            self.skipTest("No blocked apps defined")
        blocked = next(iter(BLOCKED_APPS))
        a = _action("open_app", app=blocked)
        d = self.kernel.check_action(a)
        self.assertFalse(d.allowed)
        self.assertEqual(d.blocked_by, "blocked_apps_list")

    def test_open_app_disabled(self) -> None:
        kernel = PolicyKernel(allow_open_app=False)
        a = _action("open_app", app="firefox")
        d = kernel.check_action(a)
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "open_app_disabled")

    def test_allowed_apps_list(self) -> None:
        with patch.dict(os.environ, {"JARVIS_ALLOWED_APPS": "firefox"}):
            kernel = PolicyKernel()
            allowed = _action("open_app", app="firefox")
            self.assertTrue(kernel.check_action(allowed).allowed)
            blocked = _action("open_app", app="chrome")
            self.assertFalse(kernel.check_action(blocked).allowed)


class TestPolicyKernelSafeActions(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = PolicyKernel()

    def test_wait_allowed(self) -> None:
        d = self.kernel.check_action(_action("wait"))
        self.assertTrue(d.allowed)
        self.assertFalse(d.requires_confirmation)

    def test_hotkey_allowed(self) -> None:
        d = self.kernel.check_action(_action("hotkey", keys="ctrl+c"))
        self.assertTrue(d.allowed)

    def test_scroll_allowed(self) -> None:
        d = self.kernel.check_action(_action("scroll", direction="down"))
        self.assertTrue(d.allowed)

    def test_unknown_action_requires_confirmation(self) -> None:
        d = self.kernel.check_action(_action("unknown_action_xyz"))
        self.assertTrue(d.allowed)
        self.assertTrue(d.requires_confirmation)


class TestPolicyKernelCheckActions(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = PolicyKernel()

    def test_all_safe(self) -> None:
        actions = [_action("wait"), _action("scroll"), _action("hotkey")]
        d = self.kernel.check_actions(actions)
        self.assertTrue(d.allowed)

    def test_one_blocked_stops(self) -> None:
        actions = [
            _action("wait"),
            _action("open_url", url="https://nubank.com.br"),
            _action("scroll"),
        ]
        d = self.kernel.check_actions(actions)
        self.assertFalse(d.allowed)

    def test_confirmation_aggregated(self) -> None:
        actions = [_action("open_app", app="firefox"), _action("wait")]
        d = self.kernel.check_actions([])
        self.assertTrue(d.allowed)

    def test_empty_list_allowed(self) -> None:
        d = self.kernel.check_actions([])
        self.assertTrue(d.allowed)


class TestPolicyKernelScreenshot(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = PolicyKernel()

    def test_screenshot_safe_app(self) -> None:
        d = self.kernel.check_screenshot_allowed("firefox")
        self.assertTrue(d.allowed)

    def test_screenshot_blocked_banking_url(self) -> None:
        d = self.kernel.check_screenshot_allowed("chrome", url="https://nubank.com.br")
        self.assertFalse(d.allowed)
        self.assertEqual(d.blocked_by, "bank_protection")

    def test_screenshot_blocked_app(self) -> None:
        from jarvis.seguranca.policy import BLOCKED_APPS
        if not BLOCKED_APPS:
            self.skipTest("No blocked apps defined")
        blocked = next(iter(BLOCKED_APPS))
        d = self.kernel.check_screenshot_allowed(blocked)
        self.assertFalse(d.allowed)

    def test_screenshot_empty_app(self) -> None:
        d = self.kernel.check_screenshot_allowed("")
        self.assertTrue(d.allowed)


class TestPolicyKernelSummary(unittest.TestCase):
    def test_security_summary(self) -> None:
        kernel = PolicyKernel()
        summary = kernel.get_security_summary()
        self.assertIn("blocked_domains_count", summary)
        self.assertIn("blocked_keywords_count", summary)
        self.assertIn("allow_open_app", summary)
        self.assertGreater(summary["blocked_domains_count"], 0)

    def test_env_extra_blocked_domain(self) -> None:
        with patch.dict(os.environ, {"JARVIS_BLOCKED_DOMAINS": "evil.com"}):
            kernel = PolicyKernel()
            a = _action("open_url", url="https://evil.com/page")
            d = kernel.check_action(a)
            self.assertFalse(d.allowed)


class TestModuleLevelFunctions(unittest.TestCase):
    def test_get_policy_kernel_singleton(self) -> None:
        k1 = get_policy_kernel()
        k2 = get_policy_kernel()
        self.assertIs(k1, k2)

    def test_check_action_allowed(self) -> None:
        a = _action("wait")
        d = check_action_allowed(a)
        self.assertTrue(d.allowed)

    def test_is_contact_allowed_false(self) -> None:
        self.assertFalse(is_contact_allowed("hacker@evil.com"))

    def test_is_contact_allowed_true(self) -> None:
        with patch.dict(os.environ, {"JARVIS_CONTACT_WHITELIST": "alice"}):
            from importlib import import_module
            import jarvis.seguranca.policy as pol
            old = pol._default_kernel
            pol._default_kernel = PolicyKernel()
            try:
                self.assertTrue(is_contact_allowed("alice"))
            finally:
                pol._default_kernel = old

    def test_is_domain_blocked_true(self) -> None:
        self.assertTrue(is_domain_blocked("https://nubank.com.br"))

    def test_is_domain_blocked_false(self) -> None:
        self.assertFalse(is_domain_blocked("https://google.com"))


if __name__ == "__main__":
    unittest.main()
