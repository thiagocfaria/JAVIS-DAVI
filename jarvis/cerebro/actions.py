from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Action:
    action_type: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.action_type, "params": self.params}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Action:
        return Action(action_type=data.get("type", ""), params=data.get("params", {}))


@dataclass
class ActionPlan:
    actions: list[Action]
    risk_level: str = "low"
    notes: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "actions": [a.to_dict() for a in self.actions],
            "risk_level": self.risk_level,
            "notes": self.notes,
            "confidence": self.confidence,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ActionPlan:
        actions = [Action.from_dict(item) for item in data.get("actions", [])]
        return ActionPlan(
            actions=actions,
            risk_level=data.get("risk_level", "low"),
            notes=str(data.get("notes", "") or ""),
            confidence=float(data.get("confidence", 0.0) or 0.0),
        )
