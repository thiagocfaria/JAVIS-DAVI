"""
Policy Kernel - IMMUTABLE SECURITY CORE

██╗███╗   ███╗███╗   ███╗██╗   ██╗████████╗ █████╗ ██████╗ ██╗     ███████╗
██║████╗ ████║████╗ ████║██║   ██║╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
██║██╔████╔██║██╔████╔██║██║   ██║   ██║   ███████║██████╔╝██║     █████╗
██║██║╚██╔╝██║██║╚██╔╝██║██║   ██║   ██║   ██╔══██║██╔══██╗██║     ██╔══╝
██║██║ ╚═╝ ██║██║ ╚═╝ ██║╚██████╔╝   ██║   ██║  ██║██████╔╝███████╗███████╗
╚═╝╚═╝     ╚═╝╚═╝     ╚═╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝

THIS MODULE CONTAINS SECURITY RULES THAT THE AGENT CANNOT MODIFY.

Rules enforced:
1. Block banking domains and keywords
2. Block contacts outside whitelist
3. Require human intervention for 2FA/CAPTCHA
4. Require voice + key approval for sensitive actions
5. Block sensitive apps from automation

DO NOT allow the agent to modify this file.
Any changes require manual human approval outside the agent workflow.
"""

from __future__ import annotations

import os
import shlex
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ..cerebro.actions import Action
from .policy_usuario import PolicyUsuarioStore

# ============================================================================
# IMMUTABLE BLOCKED LISTS - DO NOT MODIFY PROGRAMMATICALLY
# ============================================================================

# Banking domains - NEVER allow access
BLOCKED_BANK_DOMAINS: frozenset[str] = frozenset(
    {
        # Brazilian banks
        "nubank",
        "itau",
        "bradesco",
        "santander",
        "caixa",
        "bb.com.br",
        "bancodobrasil",
        "inter",
        "c6bank",
        "original",
        "safra",
        "btg",
        "banrisul",
        "sicoob",
        "sicredi",
        "banestes",
        # Payment services
        "picpay",
        "mercadopago",
        "pagseguro",
        "pagbank",
        "ame",
        # International
        "paypal",
        "stripe",
        "wise",
        "revolut",
        # Crypto
        "binance",
        "coinbase",
        "kraken",
        "ftx",
        "crypto.com",
    }
)

# Keywords that indicate financial/banking context
BLOCKED_BANK_KEYWORDS: frozenset[str] = frozenset(
    {
        "banco",
        "bank",
        "pix",
        "transfer",
        "transferencia",
        "saldo",
        "extrato",
        "fatura",
        "boleto",
        "pagamento",
        "payment",
        "cartao",
        "cartão",
        "credit",
        "credito",
        "débito",
        "debito",
        "conta corrente",
        "poupanca",
        "investimento",
    }
)

# Keywords that require human intervention
REQUIRE_HUMAN_KEYWORDS: frozenset[str] = frozenset(
    {
        "captcha",
        "recaptcha",
        "hcaptcha",
        "2fa",
        "two-factor",
        "two factor",
        "dois fatores",
        "verificacao",
        "verificação",
        "verification",
        "codigo",
        "código",
        "code",
        "otp",
        "one-time",
        "token",
        "sms",
        "autenticacao",
        "autenticação",
    }
)

# Apps that should never be automated
BLOCKED_APPS: frozenset[str] = frozenset(
    {
        # Password managers
        "1password",
        "bitwarden",
        "keepass",
        "keepassxc",
        "lastpass",
        "dashlane",
        "enpass",
        # Banking apps
        "nubank",
        "itau",
        "bradesco",
        "santander",
        "caixa",
        "bb",
        "inter",
        "c6bank",
        "picpay",
        "mercadopago",
        # Crypto wallets
        "metamask",
        "exodus",
        "ledger",
        "trezor",
        # System security
        "gnome-keyring",
        "seahorse",
        "kwallet",
    }
)


# ============================================================================
# POLICY DECISION
# ============================================================================


@dataclass(frozen=True)
class PolicyDecision:
    """Immutable policy decision result."""

    allowed: bool
    reason: str = ""
    requires_confirmation: bool = False
    requires_human: bool = False
    blocked_by: str = ""  # Which rule blocked this


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _split_env(key: str) -> list[str]:
    """Split environment variable by comma."""
    raw = os.environ.get(key, "")
    items = [item.strip().lower() for item in raw.split(",") if item.strip()]
    return items


def _normalize_app(app: str) -> str:
    """Normalize app name for comparison."""
    try:
        parts = shlex.split(app)
    except ValueError:
        return app.strip().lower()
    if not parts:
        return ""
    return parts[0].strip().lower()


def _contains_any(text: str, keywords: frozenset[str]) -> bool:
    """Check if text contains any of the keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def _matches_any_domain(text: str, domains: frozenset[str]) -> bool:
    """Check if text contains any blocked domain."""
    text_lower = text.lower()
    return any(domain in text_lower for domain in domains)


# ============================================================================
# POLICY KERNEL - IMMUTABLE CORE
# ============================================================================


class PolicyKernel:
    """
    Immutable security policy kernel.

    This class enforces security rules that the agent CANNOT modify.
    All rules are loaded at initialization and cannot be changed at runtime.
    """

    def __init__(
        self, allow_open_app: bool = True, user_policy_path: Path | None = None
    ) -> None:
        # Load contact whitelist from environment (the ONLY way to add contacts)
        self.allowed_contacts: frozenset[str] = frozenset(
            _split_env("JARVIS_CONTACT_WHITELIST")
        )

        # Load additional blocked domains from environment
        env_blocked = set(_split_env("JARVIS_BLOCKED_DOMAINS"))
        self.blocked_domains: frozenset[str] = BLOCKED_BANK_DOMAINS | frozenset(
            env_blocked
        )

        # Load additional blocked keywords from environment
        env_keywords = set(_split_env("JARVIS_BLOCKED_KEYWORDS"))
        self.blocked_keywords: frozenset[str] = BLOCKED_BANK_KEYWORDS | frozenset(
            env_keywords
        )

        # Load allowed apps from environment (if set, only these apps can be opened)
        self.allowed_apps: frozenset[str] = frozenset(_split_env("JARVIS_ALLOWED_APPS"))

        # Blocked apps - combine immutable list with environment
        env_blocked_apps = set(_split_env("JARVIS_BLOCKED_APPS"))
        self.blocked_apps: frozenset[str] = BLOCKED_APPS | frozenset(env_blocked_apps)

        # Human intervention keywords
        self.require_human_keywords: frozenset[str] = REQUIRE_HUMAN_KEYWORDS

        # Allow opening apps (can be disabled via environment)
        self.allow_open_app = allow_open_app

        # User policy overlay (extra blocks from file)
        if user_policy_path:
            store = PolicyUsuarioStore(user_policy_path)
            usuario = store.load()
            if usuario.blocked_domains:
                self.blocked_domains = self.blocked_domains | frozenset(
                    usuario.blocked_domains
                )
            if usuario.blocked_apps:
                self.blocked_apps = self.blocked_apps | frozenset(usuario.blocked_apps)

    def check_action(self, action: Action) -> PolicyDecision:
        """
        Check if an action is allowed by the security policy.

        This method enforces immutable security rules.
        """
        action_type = action.action_type
        params = action.params or {}

        # ================================================================
        # RULE 1: Block sending messages to contacts outside whitelist
        # ================================================================
        if action_type == "send_message":
            contact = (params.get("contact") or "").strip().lower()
            if not contact:
                return PolicyDecision(
                    allowed=False,
                    reason="contact_required",
                    blocked_by="contact_whitelist",
                )
            if contact not in self.allowed_contacts:
                return PolicyDecision(
                    allowed=False,
                    reason="contact_not_in_whitelist",
                    blocked_by="contact_whitelist",
                )
            return PolicyDecision(allowed=True, requires_confirmation=True)

        # ================================================================
        # RULE 2: Block banking domains and keywords
        # ================================================================
        if action_type in {"open_url", "type_text", "navigate", "web_fill"}:
            text = str(
                params.get("url")
                or params.get("text")
                or params.get("value")
                or params.get("selector")
                or ""
            ).lower()

            # Check for blocked domains
            if _matches_any_domain(text, self.blocked_domains):
                return PolicyDecision(
                    allowed=False,
                    reason="banking_domain_blocked",
                    blocked_by="bank_protection",
                )

            # Check for blocked keywords
            if _contains_any(text, self.blocked_keywords):
                return PolicyDecision(
                    allowed=False,
                    reason="banking_keyword_blocked",
                    blocked_by="bank_protection",
                )

        # ================================================================
        # RULE 3: Require human for 2FA/CAPTCHA
        # ================================================================
        if action_type in {"type_text", "click", "web_click", "web_fill"}:
            text = str(
                params.get("text")
                or params.get("selector")
                or params.get("target")
                or params.get("value")
                or ""
            ).lower()
            if _contains_any(text, self.require_human_keywords):
                return PolicyDecision(
                    allowed=False,
                    reason="requires_human_intervention",
                    requires_human=True,
                    blocked_by="2fa_captcha_protection",
                )

        # ================================================================
        # RULE 4: Block forbidden apps
        # ================================================================
        if action_type == "open_app":
            if not self.allow_open_app:
                return PolicyDecision(
                    allowed=False,
                    reason="open_app_disabled",
                    blocked_by="app_policy",
                )

            app = (params.get("app") or "").strip()
            if app:
                base = _normalize_app(app)

                # Check if app is blocked
                for blocked in self.blocked_apps:
                    if blocked in base:
                        return PolicyDecision(
                            allowed=False,
                            reason="app_blocked",
                            blocked_by="blocked_apps_list",
                        )

                # Check if app is in allowed list (if list is set)
                if self.allowed_apps and base not in self.allowed_apps:
                    return PolicyDecision(
                        allowed=False,
                        reason="app_not_in_allowed_list",
                        blocked_by="allowed_apps_list",
                    )

            # Opening apps always requires confirmation
            return PolicyDecision(allowed=True, requires_confirmation=True)

        # ================================================================
        # RULE 5: Safe actions - allow with/without confirmation
        # ================================================================
        if action_type in {"wait"}:
            return PolicyDecision(allowed=True, requires_confirmation=False)

        if action_type in {
            "hotkey",
            "click",
            "type_text",
            "open_url",
            "scroll",
            "drag",
        }:
            return PolicyDecision(allowed=True, requires_confirmation=False)

        # Unknown actions require confirmation
        return PolicyDecision(allowed=True, requires_confirmation=True)

    def check_actions(self, actions: Iterable[Action]) -> PolicyDecision:
        """
        Check multiple actions against security policy.

        Returns the first blocking decision, or an aggregate decision.
        """
        requires_confirmation = False
        requires_human = False

        for action in actions:
            decision = self.check_action(action)
            if not decision.allowed:
                return decision
            requires_confirmation = (
                requires_confirmation or decision.requires_confirmation
            )
            requires_human = requires_human or decision.requires_human

        return PolicyDecision(
            allowed=True,
            requires_confirmation=requires_confirmation,
            requires_human=requires_human,
        )

    def check_screenshot_allowed(self, app_name: str, url: str = "") -> PolicyDecision:
        """
        Check if taking/sending a screenshot is allowed.

        Args:
            app_name: Name of the app in focus
            url: URL if it's a browser

        Returns:
            PolicyDecision indicating if screenshot can be sent to AI
        """
        app_lower = (app_name or "").lower()
        url_lower = (url or "").lower()

        # Check blocked apps
        for blocked in self.blocked_apps:
            if blocked in app_lower:
                return PolicyDecision(
                    allowed=False,
                    reason="screenshot_blocked_app",
                    blocked_by="blocked_apps_list",
                )

        # Check blocked domains in URL
        if _matches_any_domain(url_lower, self.blocked_domains):
            return PolicyDecision(
                allowed=False,
                reason="screenshot_blocked_domain",
                blocked_by="bank_protection",
            )

        return PolicyDecision(allowed=True)

    def get_security_summary(self) -> dict:
        """
        Get a summary of active security rules.

        Useful for debugging and logging.
        """
        return {
            "blocked_domains_count": len(self.blocked_domains),
            "blocked_keywords_count": len(self.blocked_keywords),
            "blocked_apps_count": len(self.blocked_apps),
            "allowed_contacts_count": len(self.allowed_contacts),
            "allowed_apps_count": len(self.allowed_apps),
            "require_human_keywords_count": len(self.require_human_keywords),
            "allow_open_app": self.allow_open_app,
        }


# ============================================================================
# MODULE-LEVEL FUNCTIONS (for backwards compatibility)
# ============================================================================

_default_kernel: PolicyKernel | None = None


def get_policy_kernel() -> PolicyKernel:
    """Get the default policy kernel singleton."""
    global _default_kernel
    if _default_kernel is None:
        _default_kernel = PolicyKernel()
    return _default_kernel


def check_action_allowed(action: Action) -> PolicyDecision:
    """Check if an action is allowed by the default policy."""
    return get_policy_kernel().check_action(action)


def is_contact_allowed(contact: str) -> bool:
    """Check if a contact is in the whitelist."""
    kernel = get_policy_kernel()
    return contact.strip().lower() in kernel.allowed_contacts


def is_domain_blocked(url: str) -> bool:
    """Check if a domain is blocked."""
    kernel = get_policy_kernel()
    return _matches_any_domain(url, kernel.blocked_domains)
