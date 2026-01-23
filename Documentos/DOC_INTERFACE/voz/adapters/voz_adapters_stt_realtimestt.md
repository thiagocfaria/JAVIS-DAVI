# voz/adapters/stt_realtimestt.py

- Caminho: `jarvis/voz/adapters/stt_realtimestt.py`
- Papel: carregar RealtimeSTT (pip ou clone local) e expor o recorder.
- Onde entra no fluxo: usado pelo STT quando `JARVIS_STT_STREAMING=1` e backend `realtimestt`.
- Atualizado em: 2026-01-14 (revisado com o codigo)

## Responsabilidades
- Importar `RealtimeSTT` do pip; fallback para copia vendorizada em `jarvis/third_party/realtimestt`; fallback final para `jarvis/REPOSITORIOS_CLONAR/realtimestt` (transicao).
- Cachear modulo/classe para reduzir overhead.
- Expor `build_recorder(**kwargs)` e `set_partial_callback`.
- Expor `is_available()` e `last_error()` para diagnostico.

## Entrada e saida
- Entrada: kwargs de inicializacao do `AudioToTextRecorder`.
- Saida: instancia do recorder do RealtimeSTT.

## Configuracao
- Nao le env direto; o STT decide quando usar (ver `entrada_stt.md`).
- Backend selecionado por `JARVIS_STT_STREAMING_BACKEND=realtimestt`.

## Dependencias diretas
- `RealtimeSTT` (pip) **ou** copia vendorizada em `jarvis/third_party/realtimestt`.
- `jarvis/REPOSITORIOS_CLONAR/realtimestt` fica apenas como fallback de transicao (pode ser removido quando a copia vendorizada estiver validada no seu ambiente).

## Testes relacionados
- `testes/test_stt_realtimestt_backend.py`
- `testes/test_vad_strategy.py`

## Comandos uteis
- Teste: `PYTHONPATH=. pytest -q testes/test_stt_realtimestt_backend.py`

## Qualidade e limites
- Se o modulo nao existir, retorna indisponivel sem quebrar o STT.
- Erros de import ficam em cache (`last_error`) ate reiniciar o processo.
- O recorder e encerrado com shutdown seguro e descartado apos uso (evita handles fechados).

## Observabilidade
- Debug no STT via `JARVIS_DEBUG=1` (loga indisponibilidade).

## Problemas conhecidos (hoje)
- (nenhum no momento)

## Melhorias sugeridas
- (nenhuma pendente no momento)
