#!/usr/bin/env python3
'"""Generate a structured summary from Jarvis telemetry events."""'
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence, TypedDict


class _Event(TypedDict):
    type: str | None
    timestamp: float | int | None
    payload: dict[str, Any]


class _Plan(TypedDict):
    source: Any
    duration: Any
    success: Any
    actions: Any
    risk_level: Any


class _CommandSummary(TypedDict):
    text: str
    status: str
    duration: Any
    error: Any
    events: list[_Event]
    plans: list[_Plan]


def load_events(log_path: Path) -> list[dict]:
    """Load telemetry events from a JSONL log."""
    events: list[dict] = []
    if not log_path.exists():
        raise FileNotFoundError(f"Telemetry log not found: {log_path}")
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def build_summary(events: Sequence[dict]) -> dict:
    """Build command-oriented summary from telemetry events."""
    summary: dict[str, _CommandSummary] = {}
    for event in events:
        payload = event.get("payload", {})
        command_id = payload.get("command_id")
        if not command_id:
            continue

        command = summary.setdefault(
            command_id,
            {
                "text": str(payload.get("text", "")),
                "status": "unknown",
                "duration": None,
                "error": None,
                "events": [],
                "plans": [],
            },
        )

        ts = event.get("ts")
        timestamp: float | int | None = ts if isinstance(ts, (int, float)) else None
        command["events"].append(
            {
                "type": event.get("type"),
                "timestamp": timestamp,
                "payload": payload if isinstance(payload, dict) else {},
            }
        )

        if event.get("type") == "command.start":
            command["status"] = "started"
        elif event.get("type") == "command.end":
            command["status"] = str(payload.get("status", command["status"]))
            command["duration"] = payload.get("duration")
            command["error"] = payload.get("error")
        elif event.get("type") == "plan.executed":
            command["plans"].append(
                {
                    "source": payload.get("source"),
                    "duration": payload.get("duration"),
                    "success": payload.get("success"),
                    "actions": payload.get("actions"),
                    "risk_level": payload.get("risk_level"),
                }
            )
    for command in summary.values():
        command["events"].sort(key=lambda item: float(item["timestamp"] or 0))
    return {"commands": summary}


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Jarvis telemetry events.")
    parser.add_argument(
        "--log",
        type=Path,
        default=Path.home() / ".jarvis" / "events.jsonl",
        help="Telemetry log file (JSONL)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Path to write the summary JSON (default prints to stdout)",
    )
    args = parser.parse_args()

    events = load_events(args.log)
    summary = build_summary(events)
    output = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
