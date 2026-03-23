# Inventario de deprecacoes da interface

Atualizado em: 2026-03-23.
Prazo alvo de remocao dos wrappers temporarios: **2026-06-30**.

## Objetivo
Registrar todos os caminhos legados ainda aceitos por compatibilidade, seus substitutos oficiais em `jarvis.interface.*` e o prazo esperado para remocao.

## Inventario
| Caminho legado | Caminho oficial | Escopo atual | Status | Remocao alvo |
| --- | --- | --- | --- | --- |
| `jarvis.entrada.stt` | `jarvis.interface.entrada.stt` | scripts antigos / compat | deprecated | 2026-06-30 |
| `jarvis.entrada.followup` | `jarvis.interface.entrada.followup` | compat | deprecated | 2026-06-30 |
| `jarvis.entrada.audio_utils` | `jarvis.interface.audio.audio_utils` | compat | deprecated | 2026-06-30 |
| `jarvis.entrada.preflight` | `jarvis.interface.entrada.preflight` | compat / testes legados | deprecated | 2026-06-30 |
| `jarvis.entrada.app` | `jarvis.interface.entrada.app` | compat | deprecated | 2026-06-30 |
| `jarvis.voz.tts` | `jarvis.interface.saida.tts` | compat / monkeypatch legado | deprecated | 2026-06-30 |
| `jarvis.voz.vad` | `jarvis.interface.entrada.vad` | compat | deprecated | 2026-06-30 |
| `jarvis.voz.speaker_verify` | `jarvis.interface.entrada.speaker_verify` | compat | deprecated | 2026-06-30 |
| `jarvis.voz.adapters.*` | `jarvis.interface.entrada.adapters.*` | compat | deprecated | 2026-06-30 |
| `jarvis.comunicacao.chat_log` | `jarvis.interface.infra.chat_log` | compat | deprecated | 2026-06-30 |
| `jarvis.comunicacao.chat_inbox` | `jarvis.interface.infra.chat_inbox` | compat | deprecated | 2026-06-30 |

## Consumidores revisados nesta consolidacao
- `jarvis.cerebro.orchestrator`
- `scripts/bench_interface.py`
- `scripts/measure_local_weights.py`

## Regras
- Wrapper legado deve delegar integralmente para o modulo oficial.
- Wrapper legado nao deve introduzir logica de negocio nova.
- Toda referencia nova em codigo de produto, script ou teste deve apontar para `jarvis.interface.*`.
