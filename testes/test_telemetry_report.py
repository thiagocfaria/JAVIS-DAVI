import json
import tempfile
import unittest
from pathlib import Path

from scripts.telemetry_report import build_summary, load_events


class TestTelemetryReport(unittest.TestCase):
    def test_build_summary_collects_events(self) -> None:
        events = [
            {"ts": 1.0, "type": "command.start", "payload": {"command_id": "cmd1", "text": "acao"}},
            {
                "ts": 2.0,
                "type": "plan.executed",
                "payload": {"command_id": "cmd1", "source": "local", "success": True, "duration": 0.1, "actions": 3, "risk_level": "low"},
            },
            {
                "ts": 3.0,
                "type": "command.end",
                "payload": {"command_id": "cmd1", "status": "success", "duration": 0.3, "error": ""},
            },
        ]
        summary = build_summary(events)
        commands = summary["commands"]
        self.assertIn("cmd1", commands)
        cmd_summary = commands["cmd1"]
        self.assertEqual(cmd_summary["status"], "success")
        self.assertEqual(cmd_summary["duration"], 0.3)
        self.assertEqual(len(cmd_summary["plans"]), 1)

    def test_load_events_reads_jsonl(self) -> None:
        data = {"ts": 1.0, "type": "command.start", "payload": {"command_id": "foo"}}
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "events.jsonl"
            log_path.write_text(json.dumps(data) + "\n", encoding="utf-8")
            events = load_events(log_path)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["type"], "command.start")
