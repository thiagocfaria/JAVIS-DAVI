import unittest

from jarvis.cerebro.actions import Action, ActionPlan
from jarvis.validacao.plano import validar_plano


class TestValidacaoPlano(unittest.TestCase):
    def test_plano_valido(self) -> None:
        plan = ActionPlan(
            actions=[
                Action("open_url", {"url": "https://example.com"}),
                Action("type_text", {"text": "ola"}),
                Action("hotkey", {"combo": "ctrl+l"}),
                Action("wait", {"seconds": 1}),
            ],
            risk_level="low",
        )
        qualidade = validar_plano(plan)
        self.assertEqual(qualidade.errors, [])
        self.assertGreaterEqual(qualidade.confidence, 0.8)

    def test_plano_invalido(self) -> None:
        plan = ActionPlan(
            actions=[
                Action("open_url", {}),
                Action("click", {}),
                Action("algo_invalido", {}),
            ]
        )
        qualidade = validar_plano(plan)
        self.assertTrue(qualidade.errors)
        self.assertEqual(qualidade.confidence, 0.0)

    def test_serializacao_confidence(self) -> None:
        plan = ActionPlan(actions=[], confidence=0.7)
        data = plan.to_dict()
        novo = ActionPlan.from_dict(data)
        self.assertEqual(novo.confidence, 0.7)


if __name__ == "__main__":
    unittest.main()
