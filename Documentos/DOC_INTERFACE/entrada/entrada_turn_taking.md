# interface/entrada/turn_taking.py

- Caminho: `jarvis/interface/entrada/turn_taking.py`
- Papel: heurísticas de turn-taking para decidir se a frase terminou e quanto esperar.
- Onde entra no fluxo: usado pelo STT para ajustar o hold entre turnos/endpoint.
- Atualizado em: 2026-01-19 (revisado com o codigo)

## Responsabilidades
- Inspecionar texto final/pontuação para marcar se a frase está completa.
- Retornar `hold_ms` extra quando a frase parece incompleta ou quando o silêncio é curto.
- Permitir tunar sensibilidade via variáveis de ambiente.

## Entrada e saida
- Entrada: `text` (str) + opcional `endpoint_ms` (silêncio detectado).
- Saida: dict com `is_complete`, `hold_ms`, `reason`, `last_token`.

## Configuracao (env)
- `JARVIS_TURN_TAKING_MIN_WORDS` (default 3) — mínimo de palavras para considerar completo.
- `JARVIS_TURN_TAKING_HOLD_MS` (default 600) — espera adicional quando incompleto.
- `JARVIS_TURN_TAKING_SHORT_SILENCE_MS` (default 300) — silêncios curtos geram hold extra.

## Dependencias diretas
- Apenas stdlib (`os`).

## Testes relacionados
- `testes/test_turn_taking_interface.py`
- `testes/test_turn_taking_completo.py`

## Qualidade e limites
- Heurística simples em português; tokens de função (e, mas, ou, etc.) indicam frase incompleta.
- Não usa prosódia/áudio; depende só do texto final.
