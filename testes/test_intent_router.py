from __future__ import annotations

import types

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


class _DummyOrchestrator:
    _process_command_flow = Orchestrator._process_command_flow
    _route_intent = Orchestrator._route_intent
    _contains_action_verb = staticmethod(Orchestrator._contains_action_verb)
    _looks_like_smalltalk = staticmethod(Orchestrator._looks_like_smalltalk)
    _has_any = staticmethod(Orchestrator._has_any)
    _rule_based_plan = Orchestrator._rule_based_plan

    def __init__(self) -> None:
        self.config = _DummyConfig()
        self.telemetry = _DummyTelemetry()
        self.procedures = _DummyProcedures()
        self.chat = types.SimpleNamespace(append=lambda *args, **kwargs: None)
        self.llm_local = object()
        self.last_error = ""
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
        return False

    def _record_success(self, *args, **kwargs) -> None:
        return None

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


def test_intent_router_skips_planner_for_greeting():
    orchestrator = _DummyOrchestrator()
    orchestrator._process_command_flow("e aí jarvis", lambda *args, **kwargs: None)
    assert orchestrator._plan_calls == 0


def test_intent_router_calls_planner_for_action():
    orchestrator = _DummyOrchestrator()
    orchestrator._process_command_flow(
        "abrir calculadora", lambda *args, **kwargs: None
    )
    assert orchestrator._plan_calls == 1
