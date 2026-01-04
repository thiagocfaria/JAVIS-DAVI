from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..cerebro.actions import Action, ActionPlan

ALLOWED_ACTIONS = {
    "open_app",
    "open_url",
    "type_text",
    "hotkey",
    "wait",
    "click",
    "scroll",
    "navigate",
    "web_click",
    "web_fill",
    "web_screenshot",
    "drag",
}

REQUIRED_PARAMS: dict[str, list[str]] = {
    "open_app": ["app"],
    "open_url": ["url"],
    "type_text": ["text"],
    "hotkey": ["combo"],
    "wait": ["seconds"],
    "scroll": ["amount"],
    "navigate": ["url"],
    "web_click": ["selector"],
    "web_fill": ["selector", "value"],
    "drag": ["start_x", "start_y", "end_x", "end_y"],
}


@dataclass
class PlanoQualidade:
    confidence: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validar_plano(plan: ActionPlan) -> PlanoQualidade:
    errors: list[str] = []
    warnings: list[str] = []

    if not plan.actions:
        errors.append("no_actions")

    for idx, action in enumerate(plan.actions):
        _validar_acao(action, idx, errors, warnings)

    confidence = _calcular_confianca(errors, warnings, len(plan.actions), plan.risk_level)
    return PlanoQualidade(confidence=confidence, errors=errors, warnings=warnings)


def _validar_acao(
    action: Action,
    idx: int,
    errors: list[str],
    warnings: list[str],
) -> None:
    if action.action_type not in ALLOWED_ACTIONS:
        errors.append(f"unknown_action:{idx}:{action.action_type}")
        return

    if action.action_type == "click":
        _validar_click(action, idx, errors)
        return

    if action.action_type == "scroll":
        _validar_scroll(action, idx, errors, warnings)
        return

    if action.action_type == "wait":
        _validar_wait(action, idx, errors, warnings)
        return

    required = REQUIRED_PARAMS.get(action.action_type, [])
    for field in required:
        value = action.params.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"missing_param:{idx}:{action.action_type}:{field}")


def _validar_click(action: Action, idx: int, errors: list[str]) -> None:
    if action.params.get("target"):
        return
    x = action.params.get("x")
    y = action.params.get("y")
    if x is None or y is None:
        errors.append(f"missing_param:{idx}:click:target_or_xy")


def _validar_scroll(
    action: Action,
    idx: int,
    errors: list[str],
    warnings: list[str],
) -> None:
    amount = action.params.get("amount")
    if amount is None:
        amount = action.params.get("dy")
        if amount is None:
            errors.append(f"missing_param:{idx}:scroll:amount_or_dy")
            return
    try:
        value = int(amount)
    except Exception:
        errors.append(f"invalid_param:{idx}:scroll:amount")
        return
    if value == 0:
        warnings.append(f"zero_scroll:{idx}")


def _validar_wait(
    action: Action,
    idx: int,
    errors: list[str],
    warnings: list[str],
) -> None:
    value = action.params.get("seconds")
    if value is None:
        errors.append(f"missing_param:{idx}:wait:seconds")
        return
    try:
        seconds = float(value)
    except Exception:
        errors.append(f"invalid_param:{idx}:wait:seconds")
        return
    if seconds <= 0:
        errors.append(f"invalid_param:{idx}:wait:seconds")
    if seconds > 30:
        warnings.append(f"long_wait:{idx}")


def _calcular_confianca(
    errors: list[str],
    warnings: list[str],
    steps: int,
    risk_level: str,
) -> float:
    if errors:
        return 0.0
    confidence = 0.95
    if steps > 6:
        confidence -= min(0.25, 0.02 * (steps - 6))
    confidence -= 0.05 * len(warnings)
    risk_penalties = {
        "low": 0.0,
        "medium": 0.08,
        "high": 0.18,
    }
    confidence -= risk_penalties.get(risk_level.lower(), 0.12)
    return max(0.1, min(1.0, confidence))
