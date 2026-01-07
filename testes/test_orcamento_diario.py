import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from jarvis.cerebro.orcamento import OrcamentoDiario


class TestOrcamentoDiario(unittest.TestCase):
    def test_limite_chamadas(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "orcamento.json"
            orcamento = OrcamentoDiario(path, max_chamadas=1, max_caracteres=0)
            self.assertTrue(orcamento.pode_gastar(1, 10))
            orcamento.consumir(1, 10)
            self.assertFalse(orcamento.pode_gastar(1, 10))

    def test_reset_diario(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "orcamento.json"
            ontem = (date.today() - timedelta(days=1)).isoformat()
            payload = {"data": ontem, "chamadas": 5, "caracteres": 200}
            path.write_text(json.dumps(payload), encoding="utf-8")

            orcamento = OrcamentoDiario(path, max_chamadas=10, max_caracteres=1000)
            resumo = orcamento.resumo()
            self.assertEqual(resumo["chamadas"], 0)
            self.assertEqual(resumo["caracteres"], 0)


if __name__ == "__main__":
    unittest.main()
