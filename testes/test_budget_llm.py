from __future__ import annotations

import json
import tempfile
from pathlib import Path

from jarvis.cerebro.actions import Action, ActionPlan
from jarvis.cerebro.llm import BudgetedLLMClient, LLMClient
from jarvis.cerebro.orcamento import OrcamentoDiario
from jarvis.telemetria.telemetry import Telemetry


class _StubLLM(LLMClient):
    def __init__(self) -> None:
        self.calls = 0

    def plan(self, text: str) -> ActionPlan:
        self.calls += 1
        return ActionPlan(
            actions=[Action("type_text", {"text": text})], risk_level="low"
        )


def _load_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_budget_allows_and_consumes():
    with tempfile.TemporaryDirectory() as tmpdir:
        budget_path = Path(tmpdir) / "orcamento.json"
        telemetry_path = Path(tmpdir) / "events.jsonl"
        budget = OrcamentoDiario(budget_path, max_chamadas=2, max_caracteres=50)
        telemetry = Telemetry(telemetry_path)
        llm = BudgetedLLMClient(_StubLLM(), budget, telemetry, name="test")

        plan = llm.plan("hello")

        assert plan.actions[0].params["text"] == "hello"
        resumo = budget.resumo()
        assert resumo["chamadas"] == 1
        assert resumo["caracteres"] == len("hello")
        events = _load_events(telemetry_path)
        assert any(e.get("type") == "budget.consume" for e in events)


def test_budget_block_logs_and_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        budget_path = Path(tmpdir) / "orcamento.json"
        telemetry_path = Path(tmpdir) / "events.jsonl"
        budget = OrcamentoDiario(budget_path, max_chamadas=1, max_caracteres=5)
        budget.consumir(1, 5)
        telemetry = Telemetry(telemetry_path)
        llm = BudgetedLLMClient(_StubLLM(), budget, telemetry, name="blocked")

        try:
            llm.plan("block me")
            assert False, "should have raised"
        except RuntimeError as exc:
            assert "orcamento_diario_excedido" in str(exc)

        events = _load_events(telemetry_path)
        assert any(e.get("type") == "budget.block" for e in events)
