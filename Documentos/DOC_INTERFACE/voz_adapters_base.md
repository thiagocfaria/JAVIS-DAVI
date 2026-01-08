# voz/adapters/base.py

- Caminho: `jarvis/voz/adapters/base.py`
- Papel: protocolos (interfaces) para wake word e speaker verification.
- Onde entra no fluxo: padroniza como o orquestrador usa adapters.

## Responsabilidades
- Definir assinaturas minimas para detectores.

## Entrada e saida
- `WakeWordDetector.detect(audio_i16, sample_rate) -> bool`
- `SpeakerVerifier.load_voiceprint(path) -> dict | None`
- `SpeakerVerifier.verify(audio_i16, sample_rate) -> float`

## Configuracao
- Nao usa env.

## Dependencias diretas
- Apenas typing.Protocol.

## Testes relacionados
- `testes/test_voice_adapters.py`

## Comandos uteis
- Teste: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py`

## Qualidade e limites
- Protocol apenas; nao valida runtime.


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Sem logs.

## Problemas conhecidos (hoje)
- Protocols nao fazem validacao em runtime.
- Nao ha enforce de sample_rate/formatos.

## Melhorias sugeridas
- Adicionar typing mais estrito (ex: Literal para sample_rate esperado).
