from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class OrcamentoEstado:
    data: str
    chamadas: int
    caracteres: int


class OrcamentoDiario:
    def __init__(self, path: Path, max_chamadas: int, max_caracteres: int) -> None:
        self.path = path
        self.max_chamadas = max(0, int(max_chamadas))
        self.max_caracteres = max(0, int(max_caracteres))

    def pode_gastar(self, chamadas: int, caracteres: int) -> bool:
        estado = self._carregar()
        chamadas_alvo = estado.chamadas + max(0, chamadas)
        caracteres_alvo = estado.caracteres + max(0, caracteres)

        if self.max_chamadas and chamadas_alvo > self.max_chamadas:
            return False
        if self.max_caracteres and caracteres_alvo > self.max_caracteres:
            return False
        return True

    def consumir(self, chamadas: int, caracteres: int) -> None:
        estado = self._carregar()
        estado.chamadas += max(0, chamadas)
        estado.caracteres += max(0, caracteres)
        self._salvar(estado)

    def resumo(self) -> dict:
        estado = self._carregar()
        return {
            "data": estado.data,
            "chamadas": estado.chamadas,
            "caracteres": estado.caracteres,
            "max_chamadas": self.max_chamadas,
            "max_caracteres": self.max_caracteres,
        }

    def _carregar(self) -> OrcamentoEstado:
        hoje = date.today().isoformat()
        if not self.path.exists():
            return OrcamentoEstado(data=hoje, chamadas=0, caracteres=0)
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return OrcamentoEstado(data=hoje, chamadas=0, caracteres=0)

        if payload.get("data") != hoje:
            return OrcamentoEstado(data=hoje, chamadas=0, caracteres=0)

        return OrcamentoEstado(
            data=payload.get("data", hoje),
            chamadas=int(payload.get("chamadas", 0) or 0),
            caracteres=int(payload.get("caracteres", 0) or 0),
        )

    def _salvar(self, estado: OrcamentoEstado) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "data": estado.data,
            "chamadas": estado.chamadas,
            "caracteres": estado.caracteres,
        }
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
        tmp_path.replace(self.path)
