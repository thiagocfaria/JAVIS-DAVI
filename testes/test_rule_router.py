from __future__ import annotations

import types

import pytest

from jarvis.cerebro.actions import Action, ActionPlan
from jarvis.cerebro.orchestrator import Orchestrator


class _DummyConfig:
    max_failures_per_command = 1
    browser_ai_enabled = False
    local_llm_base_url = "http://localhost:11434"
    require_approval = False
    dry_run = False


class _DummyTelemetry:
    def log_event(self, *args, **kwargs) -> None:
        return None


class _DummyProcedures:
    def match(self, text: str):
        return None


class _DummyDecision:
    def __init__(
        self,
        *,
        allowed: bool = True,
        reason: str = "",
        requires_confirmation: bool = False,
        requires_human: bool = False,
        blocked_by: str = "",
    ) -> None:
        self.allowed = allowed
        self.reason = reason
        self.requires_confirmation = requires_confirmation
        self.requires_human = requires_human
        self.blocked_by = blocked_by


class _DummyOrchestrator:
    # Bind methods from Orchestrator for testing
    # Note: These are bound methods that expect Orchestrator as self, but we use them
    # with _DummyOrchestrator for testing purposes. The type checker complains, but
    # this works at runtime because _DummyOrchestrator has compatible attributes.
    _process_command_flow = Orchestrator._process_command_flow  # type: ignore[misc]
    _route_intent = Orchestrator._route_intent  # type: ignore[misc]
    _contains_action_verb = staticmethod(Orchestrator._contains_action_verb)
    _looks_like_smalltalk = staticmethod(Orchestrator._looks_like_smalltalk)
    _has_any = staticmethod(Orchestrator._has_any)
    _rule_based_plan = Orchestrator._rule_based_plan  # type: ignore[misc]

    def __init__(self) -> None:
        self.config = _DummyConfig()
        self.telemetry = _DummyTelemetry()
        self.procedures = _DummyProcedures()
        self.chat = None
        self.llm_local = object()
        self.last_error = ""
        self.last_plan = None
        self._plan_calls = 0

    def _handle_meta_command(self, text: str) -> bool:
        return False

    def _plan_with_llm(self, text: str, llm_client, source: str):
        self._plan_calls += 1
        return None

    def _is_mock_fallback(self, plan) -> bool:
        return False

    def _allow_mock_fallback(self, text: str) -> bool:
        return True

    def _record_attempt(self, *args, **kwargs) -> None:
        return None

    def _validate_plan(self, plan, source: str):
        return plan

    def _run_plan(self, plan) -> bool:
        self.last_plan = plan
        return True

    def _record_success(self, text: str, plan, guidance=None) -> None:
        self.last_plan = plan

    def _maybe_learn_procedure(self, *args, **kwargs) -> None:
        return None

    def _external_allowed(self, text: str) -> bool:
        return False

    def _collect_external_guidance(self, *args, **kwargs):
        return None

    def _try_parse_plan_from_text(self, text: str):
        return None

    def _say(self, text: str) -> None:
        return None

    def _log_pause(self, *args, **kwargs) -> None:
        return None

    def _handle_guidance_loop(self, *args, **kwargs) -> None:
        return None


@pytest.mark.parametrize(
    ("text", "expected_url"),
    [
        ("abrir navegador", "https://www.google.com"),
        ("abre navegador", "https://www.google.com"),
        ("abrir o navegador", "https://www.google.com"),
        ("abriu o navegador", "https://www.google.com"),
        ("abriu o navegado", "https://www.google.com"),
        ("jarvis abrir navegador", "https://www.google.com"),
        ("abrir youtube", "https://www.youtube.com"),
        ("abrir chat gpt", "https://chatgpt.com"),
    ],
)
def test_rule_based_plan_skips_llm_and_opens_browser(
    text: str, expected_url: str
) -> None:
    orchestrator = _DummyOrchestrator()
    orchestrator._process_command_flow(text, lambda *args, **kwargs: None)  # type: ignore[misc]
    assert orchestrator._plan_calls == 0
    assert orchestrator.last_plan is not None
    action = orchestrator.last_plan.actions[0]
    assert action.action_type == "open_url"
    assert action.params.get("url") == expected_url


def test_rule_based_plan_risk_level_low() -> None:
    orchestrator = _DummyOrchestrator()
    orchestrator._process_command_flow("abrir navegador", lambda *args, **kwargs: None)  # type: ignore[misc]
    assert orchestrator.last_plan is not None
    assert orchestrator.last_plan.risk_level == "low"


def test_rule_based_plan_skips_approval() -> None:
    class DummyPolicy:
        def check_actions(self, actions):
            return _DummyDecision(requires_confirmation=False)

    class DummyConfig:
        require_approval = True
        dry_run = False

    class DummyTelemetry:
        def log_event(self, *args, **kwargs) -> None:
            return None

    def _request_approval() -> bool:
        raise AssertionError("_request_approval nao deveria ser chamado")

    plan = ActionPlan(
        actions=[
            Action(action_type="open_url", params={"url": "https://www.google.com"})
        ],
        risk_level="low",
        notes="rule_based:browser",
    )

    assert plan.notes is not None and plan.notes.startswith("rule_based")

    fake = types.SimpleNamespace(
        config=DummyConfig(),
        policy=DummyPolicy(),
        telemetry=DummyTelemetry(),
        _say=lambda *args, **kwargs: None,
        _log_pause=lambda *args, **kwargs: None,
        _execute_plan=lambda _plan: True,
        _request_approval=_request_approval,
        last_error=None,
    )

    assert Orchestrator._run_plan(fake, plan) is True  # type: ignore[arg-type]


def test_rule_based_plan_still_requires_policy_confirmation() -> None:
    class DummyPolicy:
        def check_actions(self, actions):
            return _DummyDecision(requires_confirmation=True)

    class DummyConfig:
        require_approval = True
        dry_run = False

    class DummyTelemetry:
        def log_event(self, *args, **kwargs) -> None:
            return None

    plan = ActionPlan(
        actions=[
            Action(action_type="open_url", params={"url": "https://www.google.com"})
        ],
        risk_level="low",
        notes="rule_based:browser",
    )

    called = {"approval": 0}

    def _request_approval() -> bool:
        called["approval"] += 1
        return True

    fake = types.SimpleNamespace(
        config=DummyConfig(),
        policy=DummyPolicy(),
        telemetry=DummyTelemetry(),
        _say=lambda *args, **kwargs: None,
        _log_pause=lambda *args, **kwargs: None,
        _execute_plan=lambda _plan: True,
        _request_approval=_request_approval,
        last_error=None,
    )

    assert Orchestrator._run_plan(fake, plan) is True  # type: ignore[arg-type]
    assert called["approval"] == 1
