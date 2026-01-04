from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List, Tuple

MAX_EXTERNAL_CHARS = 4000


@dataclass(frozen=True)
class SanitizationResult:
    text: str
    classification: str
    redactions: list[str]
    removed_lines: int
    truncated: bool


_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|above) instructions",
    r"disregard (all )?(previous|above) instructions",
    r"system prompt",
    r"developer message",
    r"role:\s*(system|developer|assistant)",
    r"^system\s*:",
    r"^assistant\s*:",
    r"^developer\s*:",
    r"jailbreak",
    r"do anything now",
    r"act as",
    r"you are (chatgpt|an ai|a language model)",
    r"remova (as )?regras",
    r"ignore (as )?regras",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_CNPJ_RE = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
_PHONE_RE = re.compile(r"\b\+?\d{1,3}[\s.-]?\(?\d{2}\)?[\s.-]?\d{4,5}[\s.-]?\d{4}\b")
_API_KEY_RE = re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9]{16,}\b")
_TOKEN_RE = re.compile(r"\b[0-9a-f]{32,}\b", re.IGNORECASE)
_PASSWORD_RE = re.compile(r"(?i)\b(senha|password|passphrase)\s*[:=]\s*\S+")

_CONFIDENTIAL_KEYWORDS = [
    "senha",
    "password",
    "passphrase",
    "token",
    "api key",
    "chave api",
    "cartao",
    "cartao de credito",
    "credit card",
]
_SENSITIVE_KEYWORDS = [
    "cpf",
    "cnpj",
    "email",
    "telefone",
    "contato",
]


def _env_bool(key: str, default: bool = False) -> bool:
    from ..cerebro.utils import normalize_text
    
    value = os.environ.get(key)
    if value is None:
        return default
    return normalize_text(value) in {"1", "true", "yes", "on"}


def sanitize_external_text(text: str) -> SanitizationResult:
    """Remove prompt injection lines and redact sensitive data."""
    raw = text or ""
    lines = raw.splitlines()
    kept: list[str] = []
    removed = 0
    for line in lines:
        if _INJECTION_RE.search(line):
            removed += 1
            continue
        kept.append(line)
    cleaned = "\n".join(kept).strip()

    redacted, redactions = redact_text(cleaned)
    classification = classify_text(raw)

    truncated = False
    if len(redacted) > MAX_EXTERNAL_CHARS:
        redacted = redacted[:MAX_EXTERNAL_CHARS].rstrip()
        truncated = True

    return SanitizationResult(
        text=redacted,
        classification=classification,
        redactions=redactions,
        removed_lines=removed,
        truncated=truncated,
    )


def redact_text(text: str) -> tuple[str, list[str]]:
    """Redact sensitive tokens to reduce leakage."""
    if not text:
        return text, []

    redactions: list[str] = []
    output = text

    output, hit = _redact_pattern(output, _EMAIL_RE, "<EMAIL>")
    if hit:
        redactions.append("email")

    output, hit = _redact_pattern(output, _CPF_RE, "<CPF>")
    if hit:
        redactions.append("cpf")

    output, hit = _redact_pattern(output, _CNPJ_RE, "<CNPJ>")
    if hit:
        redactions.append("cnpj")

    output, hit = _redact_pattern(output, _PHONE_RE, "<TELEFONE>")
    if hit:
        redactions.append("telefone")

    output, hit = _redact_pattern(output, _API_KEY_RE, "<CHAVE_API>")
    if hit:
        redactions.append("api_key")

    output, hit = _redact_pattern(output, _TOKEN_RE, "<TOKEN>")
    if hit:
        redactions.append("token")

    output, hit = _redact_passwords(output)
    if hit:
        redactions.append("senha")

    output, hit = _redact_credit_cards(output)
    if hit:
        redactions.append("cartao")

    return output, redactions


def classify_text(text: str) -> str:
    """Classify text sensitivity for external usage."""
    if not text or not text.strip():
        return "publico"

    lowered = text.lower()
    if _has_confidential_tokens(lowered):
        return "sigiloso"
    if _has_sensitive_tokens(lowered):
        return "sensivel"
    return "publico"


def _has_confidential_tokens(text: str) -> bool:
    if _PASSWORD_RE.search(text):
        return True
    if _API_KEY_RE.search(text) or _TOKEN_RE.search(text):
        return True
    if _contains_keyword(text, _CONFIDENTIAL_KEYWORDS):
        return True
    if _find_card_numbers(text):
        return True
    return False


def _has_sensitive_tokens(text: str) -> bool:
    if _EMAIL_RE.search(text) or _PHONE_RE.search(text):
        return True
    if _CPF_RE.search(text) or _CNPJ_RE.search(text):
        return True
    if _env_bool("JARVIS_SENSITIVE_KEYWORDS_STRICT", False):
        if _contains_keyword(text, _SENSITIVE_KEYWORDS):
            return True
    return False


def _contains_keyword(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _redact_pattern(text: str, pattern: re.Pattern[str], token: str) -> tuple[str, bool]:
    if pattern.search(text):
        return pattern.sub(token, text), True
    return text, False


def _redact_passwords(text: str) -> tuple[str, bool]:
    if not _PASSWORD_RE.search(text):
        return text, False
    redacted = _PASSWORD_RE.sub(lambda m: f"{m.group(1)}: <SENHA>", text)
    return redacted, True


def _redact_credit_cards(text: str) -> tuple[str, bool]:
    found = False
    def repl(match: re.Match[str]) -> str:
        nonlocal found
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if len(digits) < 13 or len(digits) > 19:
            return raw
        if not _luhn_check(digits):
            return raw
        found = True
        return "<CARTAO>"

    redacted = re.sub(r"(?:\d[ -]?){13,19}", repl, text)
    return redacted, found


def _find_card_numbers(text: str) -> list[str]:
    matches = []
    for match in re.finditer(r"(?:\d[ -]?){13,19}", text):
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if len(digits) < 13 or len(digits) > 19:
            continue
        if _luhn_check(digits):
            matches.append(digits)
    return matches


def _luhn_check(number: str) -> bool:
    total = 0
    reverse_digits = list(reversed(number))
    for idx, digit in enumerate(reverse_digits):
        if not digit.isdigit():
            return False
        n = int(digit)
        if idx % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0
