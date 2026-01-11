# voz/adapters/base.py

- Caminho: `jarvis/voz/adapters/base.py`
- Papel: protocolos (interfaces) para wake word e speaker verification.
- Onde entra no fluxo: padroniza como o orquestrador usa adapters.
- Atualizado em: 2026-01-10 (revisado com o codigo)

## Responsabilidades
- Definir assinaturas minimas para detectores.
- Validar audio PCM int16 e sample_rate em runtime.

## Entrada e saida
- `WakeWordDetector.detect(audio_i16, sample_rate=16000) -> bool`
- `SpeakerVerifier.load_voiceprint(path) -> dict | None`
- `SpeakerVerifier.verify(audio_i16, sample_rate=16000) -> float`
- `validate_audio_i16(audio_i16, sample_rate) -> str | None`

## Configuracao
- Nao usa env.

## Dependencias diretas
- Apenas stdlib (`typing.Protocol`, `typing.Literal`).

## Testes relacionados
- `testes/test_voice_adapters.py`

## Comandos uteis
- Teste: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py`

## Qualidade e limites
- Protocol usa `SampleRate=Literal[16000]` para deixar claro o SR esperado.
- Helper de validacao (`validate_audio_i16`) retorna string de erro ou `None`.


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Sem logs.

## Problemas conhecidos (hoje)
- (nenhum relevante no momento)

## Melhorias sugeridas
- (nenhuma pendente relevante no momento)
