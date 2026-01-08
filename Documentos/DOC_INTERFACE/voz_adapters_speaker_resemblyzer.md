# voz/adapters/speaker_resemblyzer.py

- Caminho: `jarvis/voz/adapters/speaker_resemblyzer.py`
- Papel: adapter para speaker verification via Resemblyzer.
- Onde entra no fluxo: usado pelo orquestrador antes de aceitar comando.

## Responsabilidades
- Encapsular `speaker_verify` em uma interface padrao.
- Expor `verify_ok` e `enroll`.
- `verify` retorna apenas score (descarta o ok).

## Entrada e saida
- Entrada: PCM int16 mono; respeita `sample_rate` e reamostra quando necessario.
- Saida: score/ok e embedding.

## Configuracao
- Usa as mesmas envs do `speaker_verify.py`.

## Dependencias diretas
- `jarvis.voz.speaker_verify`

## Testes relacionados
- `testes/test_voice_adapters.py`
- `testes/test_speaker_verify_interface.py`

## Comandos uteis
- Testes: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py testes/test_speaker_verify_interface.py`

## Qualidade e limites
- Se resemblyzer nao estiver disponivel, adapter reporta indisponivel.
- Voiceprint usa cache em memoria (via `speaker_verify`).


## Performance (estimativa)
- Uso esperado: baixo/medio (chama verificador).
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Logs via `speaker_verify` (JARVIS_DEBUG).

## Problemas conhecidos (hoje)
- (nenhum relevante no momento)

## Melhorias sugeridas
- (nenhuma no momento)
