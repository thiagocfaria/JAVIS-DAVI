"""
LLM module for self-hosted inference.

Uses OpenAI-compatible local/VPS servers (llama.cpp, vLLM, etc.)
with a Mock fallback. No external paid API integrations.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from urllib import request

from ..telemetria.telemetry import Telemetry
from ..validacao.plano import validar_plano
from .actions import Action, ActionPlan
from .orcamento import OrcamentoDiario

# ============================================================================
# RESPONSE CACHE (for rate limiting and performance)
# ============================================================================


@dataclass
class CacheEntry:
    """Cached LLM response."""

    plan: ActionPlan
    timestamp: float
    ttl_seconds: int = 3600  # 1 hour default


class ResponseCache:
    """Simple in-memory cache for LLM responses."""

    def __init__(self, max_size: int = 100) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._max_size = max_size

    def get(self, key: str) -> ActionPlan | None:
        """Get cached response if valid."""
        entry = self._cache.get(key)
        if entry is None:
            return None

        # Check if expired
        if time.time() - entry.timestamp > entry.ttl_seconds:
            del self._cache[key]
            return None

        return entry.plan

    def set(self, key: str, plan: ActionPlan, ttl_seconds: int = 3600) -> None:
        """Cache a response."""
        # Evict old entries if cache is full
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._cache, key=lambda k: self._cache[k].timestamp)
            del self._cache[oldest_key]

        self._cache[key] = CacheEntry(
            plan=plan,
            timestamp=time.time(),
            ttl_seconds=ttl_seconds,
        )

    @staticmethod
    def make_key(text: str) -> str:
        """Create cache key from text."""
        normalized = text.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()


# ============================================================================
# BASE LLM CLIENT
# ============================================================================


class LLMClient:
    """Base class for LLM clients."""

    def plan(self, text: str) -> ActionPlan:
        """Generate an action plan from text command."""
        raise NotImplementedError

    def is_available(self) -> bool:
        """Check if this LLM is available."""
        return True


class BudgetedLLMClient(LLMClient):
    """LLM client wrapper that enforces a daily budget before invoking the model."""

    def __init__(
        self,
        wrapped: LLMClient,
        budget: OrcamentoDiario | None,
        telemetry: Telemetry | None,
        name: str = "llm",
    ) -> None:
        self._wrapped = wrapped
        self._budget = budget
        self._telemetry = telemetry
        self._name = name

    def plan(self, text: str) -> ActionPlan:
        characters = len(text.strip())
        if self._budget and not self._budget.pode_gastar(1, characters):
            if self._telemetry:
                self._telemetry.log_event(
                    "budget.block",
                    {
                        "source": self._name,
                        "chars": characters,
                    },
                )
            raise RuntimeError("orcamento_diario_excedido")

        plan = self._wrapped.plan(text)

        if self._budget:
            try:
                self._budget.consumir(1, characters)
                if self._telemetry:
                    self._telemetry.log_event(
                        "budget.consume",
                        {
                            "source": self._name,
                            "chars": characters,
                        },
                    )
            except Exception:
                # Budget errors should not break the plan flow
                if self._telemetry:
                    self._telemetry.log_event(
                        "budget.error",
                        {"source": self._name, "chars": characters},
                    )

        return plan

    def is_available(self) -> bool:
        return self._wrapped.is_available()

    def get_available_clients(self) -> list[str]:
        getter = getattr(self._wrapped, "get_available_clients", None)
        if not callable(getter):
            return []
        try:
            result = getter()
        except Exception:
            return []
        return result if isinstance(result, list) else []


def _normalize_confidence(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0.0 or parsed > 1.0:
        return None
    return parsed


def _merge_confidence(
    model_confidence: float | None, quality_confidence: float
) -> float:
    if model_confidence is None:
        return quality_confidence
    return min(model_confidence, quality_confidence)


# ============================================================================
# MOCK LLM (Local fallback - regex based)
# ============================================================================


class MockLLM(LLMClient):
    """
    Local regex-based command parser.

    Used as fallback when no local LLM is available.
    Handles simple commands without calling external APIs.
    """

    def plan(self, text: str) -> ActionPlan:
        actions: list[Action] = []
        parsed_any = False
        normalized = text.strip()

        # Split on "e" (and) or "then"
        parts = re.split(
            r"\s+e\s+|\s+then\s+|\s+depois\s+", normalized, flags=re.IGNORECASE
        )

        for part in parts:
            action = self._parse_single_command(part.strip())
            if action:
                actions.append(action)
                parsed_any = True

        # If no actions parsed, treat as text to type
        if not actions:
            actions.append(Action("type_text", {"text": normalized}))

        notes = "mock_local" if parsed_any else "mock_local_fallback"
        return ActionPlan(actions=actions, risk_level="low", notes=notes)

    def _parse_single_command(self, text: str) -> Action | None:
        """Parse a single command into an action."""
        lowered = text.lower()

        # Open app patterns
        open_patterns = [
            r"^(?:abrir?|abra|abre|open)\s+(.+)$",
            r"^(?:iniciar?|inicie|start)\s+(.+)$",
            r"^(?:executar?|execute|run)\s+(.+)$",
        ]
        for pattern in open_patterns:
            match = re.match(pattern, lowered)
            if match:
                app = match.group(1).strip()
                # Check if it's a URL
                if app.startswith("http") or app.startswith("www.") or "." in app:
                    return Action("open_url", {"url": app})
                return Action("open_app", {"app": app})

        # URL patterns
        url_patterns = [
            r"^(?:ir\s+para|vai\s+para|go\s+to|navigate\s+to)\s+(.+)$",
            r"^(?:abrir?\s+(?:url|site|página|pagina))\s+(.+)$",
            r"^(?:acessar?|acesse)\s+(.+)$",
        ]
        for pattern in url_patterns:
            match = re.match(pattern, lowered)
            if match:
                url = match.group(1).strip()
                if not url.startswith("http"):
                    url = "https://" + url
                return Action("open_url", {"url": url})

        # Type text patterns
        type_patterns = [
            r"^(?:digitar?|digite|escrever?|escreva|type|write)\s+(.+)$",
        ]
        for pattern in type_patterns:
            match = re.match(pattern, lowered)
            if match:
                return Action("type_text", {"text": match.group(1).strip()})

        # Hotkey patterns
        hotkey_patterns = [
            r"^(?:tecla|atalho|hotkey|pressione?|press)\s+(.+)$",
            r"^(?:ctrl|alt|shift|super)\s*\+\s*.+$",
        ]
        for pattern in hotkey_patterns:
            match = re.match(pattern, lowered)
            if match:
                combo = match.group(1).strip() if match.lastindex else text.strip()
                return Action("hotkey", {"combo": combo})

        # Wait patterns
        wait_patterns = [
            r"^(?:esperar?|espere|aguardar?|aguarde|wait)\s+(\d+)\s*(?:segundos?|s|sec)?$",
        ]
        for pattern in wait_patterns:
            match = re.match(pattern, lowered)
            if match:
                seconds = int(match.group(1))
                return Action("wait", {"seconds": seconds})

        # Scroll patterns
        scroll_patterns = [
            r"^(?:rolar|role|scroll|descer|subir)(?:\s+para)?\s+(baixo|cima|down|up)?\s*(\d+)?$",
        ]
        for pattern in scroll_patterns:
            match = re.match(pattern, lowered)
            if match:
                direction = match.group(1) or "down"
                amount = int(match.group(2)) if match.group(2) else 3
                if direction in {"cima", "up", "subir"}:
                    amount = -amount
                return Action("scroll", {"amount": amount})

        # Click patterns
        click_patterns = [
            r"^(?:clicar?|clique|click)\s+(?:em\s+)?(.+)$",
        ]
        for pattern in click_patterns:
            match = re.match(pattern, lowered)
            if match:
                return Action("click", {"target": match.group(1).strip()})

        return None


# ============================================================================
# OPENAI COMPATIBLE LLM (self-hosted servers)
# ============================================================================


class OpenAICompatLLM(LLMClient):
    """OpenAI-compatible API client (self-hosted LLM servers)."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout_s: int = 30,
        require_api_key: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self.require_api_key = require_api_key

    def is_available(self) -> bool:
        if self.require_api_key:
            return bool(self.base_url and self.api_key)
        return bool(self.base_url)

    def plan(self, text: str) -> ActionPlan:
        style = (os.environ.get("JARVIS_LLM_PROMPT_STYLE", "compact") or "compact").strip().lower()
        allowed_types = (
            "open_app, open_url, type_text, hotkey, wait, click, scroll, "
            "navigate, web_click, web_fill, web_screenshot"
        )
        if style == "verbose":
            prompt = (
                "You are a desktop automation planner. Return ONLY JSON. "
                "Schema: {actions:[{type,params}], risk_level, confidence, notes}. "
                f"Types: {allowed_types}. "
                f"Command: {text}"
            )
            messages = [
                {"role": "system", "content": "Return JSON only."},
                {"role": "user", "content": prompt},
            ]
        else:
            system = (
                "Return ONLY a valid JSON object (no markdown). "
                "Schema: {actions:[{type,params}], risk_level, confidence, notes}. "
                f"Allowed action types: {allowed_types}."
            )
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ]

        try:
            max_tokens = int(os.environ.get("JARVIS_LLM_MAX_TOKENS", "600"))
        except ValueError:
            max_tokens = 600

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": max(64, max_tokens),
        }

        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=data,
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_s) as resp:
                response = json.loads(resp.read().decode("utf-8"))
            content = response["choices"][0]["message"]["content"].strip()
            plan_dict = _safe_json_loads(content)
            return ActionPlan.from_dict(plan_dict)
        except Exception as exc:
            raise RuntimeError(f"LLM plan failed: {exc}") from exc


# ============================================================================
# LOCAL LLM ROUTER (Local-first with Mock fallback)
# ============================================================================


class LocalLLMRouter(LLMClient):
    """
    Local-first router for the "cerebro" (no paid API).

    Priority:
    1. Local OpenAI-compatible server (llama.cpp, LM Studio, etc.)
    2. MockLLM (regex fallback)
    """

    def __init__(
        self,
        base_url: str | None,
        api_key: str | None,
        model: str,
        enable_cache: bool = True,
        confidence_min: float = 0.55,
        timeout_s: int = 30,
        cooldown_s: int = 300,
    ) -> None:
        self._clients: list[tuple[str, LLMClient]] = []
        self._cache = ResponseCache() if enable_cache else None
        self._fallback = MockLLM()
        self._confidence_min = max(0.0, min(1.0, float(confidence_min)))
        self._timeout_s = timeout_s
        self._cooldown_s = max(0, int(cooldown_s))
        self._cooldown_until = 0.0

        if base_url:
            self._clients.append(
                (
                    "local",
                    OpenAICompatLLM(
                        base_url=base_url,
                        api_key=api_key,
                        model=model,
                        timeout_s=self._timeout_s,
                        require_api_key=False,
                    ),
                )
            )

        self._clients.append(("mock", self._fallback))

    def plan(self, text: str) -> ActionPlan:
        cache_key = None
        if self._cache:
            cache_key = ResponseCache.make_key(text)
            cached = self._cache.get(cache_key)
            if cached:
                cached.notes = f"{cached.notes} (cached)"
                return cached

        last_error = None
        for name, client in self._clients:
            if not client.is_available():
                continue
            if name == "local" and time.time() < self._cooldown_until:
                last_error = RuntimeError("local_llm_cooldown_active")
                continue

            try:
                plan = client.plan(text)
                plan.notes = f"{plan.notes} (via {name})"

                model_confidence = _normalize_confidence(plan.confidence)
                qualidade = validar_plano(plan)
                plan.confidence = _merge_confidence(
                    model_confidence, qualidade.confidence
                )
                if qualidade.errors:
                    plan.notes = f"{plan.notes} (plan_invalid:{len(qualidade.errors)})"
                    last_error = RuntimeError("plan_invalid")
                    continue

                if model_confidence is not None:
                    plan.notes = (
                        f"{plan.notes} (model_confidence={model_confidence:.2f}, "
                        f"quality={qualidade.confidence:.2f}, confidence={plan.confidence:.2f})"
                    )
                else:
                    plan.notes = f"{plan.notes} (confidence={plan.confidence:.2f})"
                if name != "mock" and plan.confidence < self._confidence_min:
                    last_error = RuntimeError("confidence_below_min")
                    continue

                if self._cache and name != "mock" and cache_key is not None:
                    self._cache.set(cache_key, plan)
                return plan

            except Exception as exc:
                if name == "local" and self._cooldown_s > 0:
                    self._cooldown_until = time.time() + self._cooldown_s
                last_error = exc
                continue

        if last_error:
            raise RuntimeError(f"Local LLM failed. Last error: {last_error}")

        return ActionPlan(
            actions=[], risk_level="unknown", notes="no_local_llm_available"
        )

    def get_available_clients(self) -> list[str]:
        return [name for name, client in self._clients if client.is_available()]


def build_local_llm_client(
    base_url: str | None,
    api_key: str | None,
    model: str,
    timeout_s: int,
    confidence_min: float,
    cooldown_s: int,
) -> LLMClient:
    """Build local brain client (local server + mock fallback)."""
    return LocalLLMRouter(
        base_url=base_url,
        api_key=api_key,
        model=model,
        confidence_min=confidence_min,
        timeout_s=timeout_s,
        cooldown_s=cooldown_s,
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _parse_number(text: str) -> int:
    """Extract number from text."""
    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))
    return 1


def _safe_json_loads(content: str) -> dict:
    """Safely parse JSON from LLM response."""
    text = content.strip()

    # Remove markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines if they're code fences
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON object
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from: {content[:200]}")


def check_llm_deps() -> dict:
    """Check local LLM configuration."""
    import os

    return {
        "local_base_url": bool(os.environ.get("JARVIS_LOCAL_LLM_BASE_URL")),
    }


class SingleShotLLMRouter(LLMClient):
    """Router that calls the first available LLM client once."""

    def __init__(
        self,
        clients: list[tuple[str, LLMClient]],
        enable_cache: bool = True,
    ) -> None:
        self._clients = clients
        self._cache: dict[str, ActionPlan] | None = {} if enable_cache else None

    def plan(self, text: str) -> ActionPlan:
        if self._cache is not None and text in self._cache:
            cached = self._cache[text]
            cached.notes = f"{cached.notes} (cached)"
            return cached

        for name, client in self._clients:
            if not client.is_available():
                continue
            try:
                plan = client.plan(text)
            except Exception:
                raise
            plan.notes = f"{plan.notes} (via {name})"
            if self._cache is not None:
                self._cache[text] = plan
            return plan

        raise RuntimeError("no LLM client available")
