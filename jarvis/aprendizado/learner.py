"""
Learning module for extracting procedures from demonstrations.

Uses LLM to analyze recordings and convert to ActionPlans.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..cerebro.actions import Action, ActionPlan
from ..cerebro.llm import LLMClient, MockLLM
from .recorder import RecordedEvent, Recording

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ExtractedStep:
    """An extracted step from a demonstration."""
    action_type: str
    params: dict[str, Any]
    timestamp: float
    confidence: float = 1.0
    description: str = ""


@dataclass
class ExtractedProcedure:
    """A procedure extracted from a demonstration."""
    name: str
    steps: list[ExtractedStep]
    source_recording: str
    extraction_time: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_action_plan(self) -> ActionPlan:
        """Convert to ActionPlan."""
        actions = [
            Action(
                action_type=step.action_type,
                params=step.params,
            )
            for step in self.steps
        ]
        return ActionPlan(
            actions=actions,
            risk_level="low",
            notes=f"Learned from: {self.source_recording}",
        )


# ============================================================================
# LEARNER
# ============================================================================

class DemonstrationLearner:
    """
    Learns procedures from recorded demonstrations.
    
    Uses LLM to:
    1. Analyze event sequences
    2. Group related events into steps
    3. Convert to parameterized ActionPlans
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client or MockLLM()

    def extract_procedure(
        self,
        recording: Recording,
        name: str | None = None,
    ) -> ExtractedProcedure:
        """
        Extract a procedure from a recording.
        
        Uses rule-based extraction first, then LLM refinement.
        """
        # Step 1: Rule-based extraction
        raw_steps = self._extract_steps_rule_based(recording)

        # Step 2: LLM refinement (optional)
        if self._llm_can_refine():
            try:
                refined_steps = self._refine_with_llm(raw_steps, recording)
                raw_steps = refined_steps
            except Exception:
                pass  # Use raw steps if LLM fails

        return ExtractedProcedure(
            name=name or recording.name,
            steps=raw_steps,
            source_recording=recording.name,
            extraction_time=time.time(),
            metadata={
                "duration": recording.end_time - recording.start_time,
                "event_count": len(recording.events),
            },
        )

    def _extract_steps_rule_based(
        self,
        recording: Recording,
    ) -> list[ExtractedStep]:
        """
        Extract steps using rule-based analysis.
        
        Groups events into logical steps:
        - Clicks become click actions
        - Key sequences become type_text or hotkey actions
        """
        steps = []
        events = recording.events
        i = 0

        while i < len(events):
            event = events[i]

            # Handle clicks
            if event.event_type == "click":
                step = ExtractedStep(
                    action_type="click",
                    params={
                        "x": event.data.get("x"),
                        "y": event.data.get("y"),
                    },
                    timestamp=event.timestamp,
                    description=f"Click at ({event.data.get('x')}, {event.data.get('y')})",
                )
                steps.append(step)
                i += 1
                continue

            # Handle key sequences
            if event.event_type == "key_press":
                # Collect consecutive key presses
                key_sequence = []
                while i < len(events) and events[i].event_type in {"key_press", "key_release"}:
                    if events[i].event_type == "key_press":
                        key_sequence.append(events[i].data.get("key", ""))
                    i += 1

                # Determine if it's text or hotkey
                if self._is_hotkey_sequence(key_sequence):
                    step = ExtractedStep(
                        action_type="hotkey",
                        params={"combo": self._keys_to_combo(key_sequence)},
                        timestamp=event.timestamp,
                        description=f"Hotkey: {'+'.join(key_sequence)}",
                    )
                else:
                    text = self._keys_to_text(key_sequence)
                    step = ExtractedStep(
                        action_type="type_text",
                        params={"text": text},
                        timestamp=event.timestamp,
                        description=f"Type: {text}",
                    )
                steps.append(step)
                continue

            # Handle scrolls
            if event.event_type == "scroll":
                dy = event.data.get("dy", 0)
                try:
                    amount = -int(dy)
                except Exception:
                    amount = 0
                step = ExtractedStep(
                    action_type="scroll",
                    params={
                        "amount": amount,
                    },
                    timestamp=event.timestamp,
                    description="Scroll",
                )
                steps.append(step)
                i += 1
                continue

            # Skip other events
            i += 1

        # Add waits between steps
        steps_with_waits = self._add_waits(steps)

        return steps_with_waits

    def _is_hotkey_sequence(self, keys: list[str]) -> bool:
        """Check if key sequence is a hotkey (has modifier)."""
        modifiers = {"Key.ctrl", "Key.alt", "Key.shift", "Key.cmd", "Key.super"}
        return any(key in modifiers for key in keys)

    def _keys_to_combo(self, keys: list[str]) -> str:
        """Convert key sequence to hotkey combo string."""
        # Map pynput key names to standard names
        key_map = {
            "Key.ctrl": "ctrl",
            "Key.ctrl_l": "ctrl",
            "Key.ctrl_r": "ctrl",
            "Key.alt": "alt",
            "Key.alt_l": "alt",
            "Key.alt_r": "alt",
            "Key.shift": "shift",
            "Key.shift_l": "shift",
            "Key.shift_r": "shift",
            "Key.cmd": "super",
            "Key.super": "super",
        }

        combo_parts = []
        for key in keys:
            mapped = key_map.get(key, key.replace("Key.", ""))
            if mapped not in combo_parts:
                combo_parts.append(mapped)

        return "+".join(combo_parts)

    def _keys_to_text(self, keys: list[str]) -> str:
        """Convert key sequence to typed text."""
        text_parts = []

        for key in keys:
            if key.startswith("Key."):
                # Handle special keys
                if key == "Key.space":
                    text_parts.append(" ")
                elif key == "Key.enter":
                    text_parts.append("\n")
                elif key == "Key.tab":
                    text_parts.append("\t")
                elif key == "Key.backspace":
                    if text_parts:
                        text_parts.pop()
                # Skip other special keys
            else:
                text_parts.append(key)

        return "".join(text_parts)

    def _add_waits(self, steps: list[ExtractedStep]) -> list[ExtractedStep]:
        """Add wait steps between actions if there are significant pauses."""
        if len(steps) < 2:
            return steps

        result = []
        for i, step in enumerate(steps):
            result.append(step)

            if i < len(steps) - 1:
                gap = steps[i + 1].timestamp - step.timestamp
                if gap > 1.0:  # Significant pause
                    wait_step = ExtractedStep(
                        action_type="wait",
                        params={"seconds": int(gap)},
                        timestamp=step.timestamp + 0.1,
                        description=f"Wait {int(gap)} seconds",
                    )
                    result.append(wait_step)

        return result

    def _refine_with_llm(
        self,
        steps: list[ExtractedStep],
        recording: Recording,
    ) -> list[ExtractedStep]:
        """
        Use LLM to refine extracted steps.
        
        The LLM can:
        - Group related clicks into single semantic actions
        - Convert coordinates to element names
        - Add context from screenshots
        """
        # Build prompt with steps summary
        steps_summary = "\n".join(
            f"- {step.action_type}: {step.description}"
            for step in steps[:20]  # Limit for context
        )

        prompt = f"""Convert this recorded demonstration into an ActionPlan.

Recording: {recording.name}
Duration: {recording.end_time - recording.start_time:.1f} seconds

Raw steps:
{steps_summary}

Return ONLY JSON in this schema:
{{"actions":[{{"type":"open_app|open_url|type_text|hotkey|click|scroll|wait|navigate|web_click|web_fill|web_screenshot","params":{{}}}}], "risk_level":"low", "notes":"..."}}"""

        try:
            plan = self._llm.plan(prompt)
            allowed = {
                "open_app", "open_url", "type_text", "hotkey", "click",
                "scroll", "wait", "navigate", "web_click", "web_fill", "web_screenshot",
            }
            refined = []
            for action in plan.actions:
                if action.action_type not in allowed:
                    continue
                refined.append(ExtractedStep(
                    action_type=action.action_type,
                    params=action.params,
                    timestamp=time.time(),
                    description=f"LLM refined: {action.action_type}",
                ))
            return refined or steps
        except Exception:
            return steps

    def _llm_can_refine(self) -> bool:
        """Check if a non-mock LLM client is available for refinement."""
        if isinstance(self._llm, MockLLM):
            return False
        if hasattr(self._llm, "get_available_clients"):
            clients = self._llm.get_available_clients()
            return any(client != "mock" for client in clients)
        return True

    def save_procedure(
        self,
        procedure: ExtractedProcedure,
        path: Path,
    ) -> None:
        """Save extracted procedure to JSON."""
        data = {
            "name": procedure.name,
            "steps": [
                {
                    "action_type": step.action_type,
                    "params": step.params,
                    "timestamp": step.timestamp,
                    "confidence": step.confidence,
                    "description": step.description,
                }
                for step in procedure.steps
            ],
            "source_recording": procedure.source_recording,
            "extraction_time": procedure.extraction_time,
            "metadata": procedure.metadata,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_procedure(self, path: Path) -> ExtractedProcedure:
        """Load procedure from JSON."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        steps = [
            ExtractedStep(
                action_type=s["action_type"],
                params=s.get("params", {}),
                timestamp=s.get("timestamp", 0),
                confidence=s.get("confidence", 1.0),
                description=s.get("description", ""),
            )
            for s in data.get("steps", [])
        ]

        return ExtractedProcedure(
            name=data.get("name", ""),
            steps=steps,
            source_recording=data.get("source_recording", ""),
            extraction_time=data.get("extraction_time", 0),
            metadata=data.get("metadata", {}),
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def learn_from_recording(
    recording_path: Path,
    output_path: Path | None = None,
) -> ExtractedProcedure:
    """
    Convenience function to learn from a recording file.
    
    Args:
        recording_path: Path to recording JSON
        output_path: Path to save procedure (optional)
        
    Returns:
        Extracted procedure
    """
    from .recorder import Recording

    with open(recording_path) as f:
        data = json.load(f)

    recording = Recording.from_dict(data)

    learner = DemonstrationLearner()
    procedure = learner.extract_procedure(recording)

    if output_path:
        learner.save_procedure(procedure, output_path)

    return procedure
