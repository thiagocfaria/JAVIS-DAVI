import tempfile
import unittest
from pathlib import Path

from jarvis.cerebro.actions import Action, ActionPlan
from jarvis.memoria.procedures import ProcedureStore


class TestProcedureStore(unittest.TestCase):
    def test_add_and_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "procedures.db"
            store = ProcedureStore(db_path, max_total=10, max_per_tag=5, ttl_days=30)
            plan = ActionPlan(
                actions=[Action("open_url", {"url": "https://example.com"})]
            )
            store.add_from_command("abrir example.com", plan)
            matched = store.match("abrir example.com")
            self.assertIsNotNone(matched)
            assert matched is not None
            found_plan, _values = matched
            self.assertEqual(found_plan.actions[0].action_type, "open_url")
            assert store._procedures is not None
            self.assertIn("web", store._procedures[0].tags)

    def test_prune_total(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "procedures.db"
            store = ProcedureStore(db_path, max_total=2, max_per_tag=10, ttl_days=30)
            plan = ActionPlan(
                actions=[Action("open_url", {"url": "https://example.com"})]
            )
            store.add_from_command("abrir example.com", plan)
            store.add_from_command("abrir example.org", plan)
            store.add_from_command("abrir example.net", plan)
            self.assertLessEqual(len(store._procedures), 2)

    def test_prune_per_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "procedures.db"
            store = ProcedureStore(db_path, max_total=10, max_per_tag=1, ttl_days=30)
            plan = ActionPlan(
                actions=[Action("open_url", {"url": "https://example.com"})]
            )
            store.add_from_command("abrir example.com", plan)
            store.add_from_command("abrir example.org", plan)
            web_count = sum(1 for proc in store._procedures if "web" in proc.tags)
            self.assertLessEqual(web_count, 1)

    def test_ambiguous_match_prefers_specific(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "procedures.db"
            store = ProcedureStore(db_path, max_total=10, max_per_tag=5, ttl_days=30)
            plan_specific = ActionPlan(
                actions=[Action("open_url", {"url": "https://github.com"})]
            )
            plan_generic = ActionPlan(
                actions=[Action("open_url", {"url": "https://{site}"})]
            )
            store.add_from_command('abrir "github"', plan_generic)
            store.add_from_command("abrir github", plan_specific)
            matched = store.match("abrir github")
            self.assertIsNotNone(matched)
            assert matched is not None
            found_plan, _values = matched
            assert store._procedures is not None
            self.assertIn("github.com", found_plan.actions[0].params.get("url", ""))


if __name__ == "__main__":
    unittest.main()
