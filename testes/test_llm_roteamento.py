import unittest

from jarvis.cerebro.actions import Action, ActionPlan
from jarvis.cerebro.llm import LLMClient, MockLLM, SingleShotLLMRouter


class FakeLLM(LLMClient):
    def __init__(self, available: bool = True, fail: bool = False) -> None:
        self._available = available
        self._fail = fail

    def is_available(self) -> bool:
        return self._available

    def plan(self, text: str) -> ActionPlan:
        if self._fail:
            raise RuntimeError("fail")
        return ActionPlan(
            actions=[Action("wait", {"seconds": 1})],
            risk_level="low",
            notes="fake",
        )


class TestLLMRoteamento(unittest.TestCase):
    def test_mock_llm_notes_fallback(self) -> None:
        plan = MockLLM().plan("xyz desconhecido")
        self.assertIn("mock_local_fallback", plan.notes)

    def test_mock_llm_notes_parsed(self) -> None:
        plan = MockLLM().plan("abrir firefox")
        self.assertIn("mock_local", plan.notes)
        self.assertNotIn("fallback", plan.notes)

    def test_single_shot_no_fallback_on_failure(self) -> None:
        router = SingleShotLLMRouter(
            clients=[
                ("a", FakeLLM(available=True, fail=True)),
                ("b", FakeLLM(available=True, fail=False)),
            ],
            enable_cache=False,
        )
        with self.assertRaises(RuntimeError):
            router.plan("teste")

    def test_single_shot_picks_first_available(self) -> None:
        router = SingleShotLLMRouter(
            clients=[
                ("a", FakeLLM(available=False, fail=False)),
                ("b", FakeLLM(available=True, fail=False)),
            ],
            enable_cache=False,
        )
        plan = router.plan("teste")
        self.assertIn("(via b)", plan.notes)


if __name__ == "__main__":
    unittest.main()
