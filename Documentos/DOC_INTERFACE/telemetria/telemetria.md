# interface/telemetria/ (stub)

- Caminho: `jarvis/interface/telemetria/__init__.py`
- Papel: placeholder para telemetria específica da interface.
- Atualizado em: 2026-01-24

## Estado atual
- O módulo só contém um docstring e não expõe funções ou métricas.
- Telemetria de voz hoje é registrada por outras partes (ex.: `TextToSpeech.get_last_metrics()`, métricas de VAD/STT via logs/config).

## Quando atualizar
- Se adicionarmos métricas ou integração de observabilidade específicas da interface (ex.: exportar tempos de STT/TTS, VAD, wake word), este doc deve descrever as APIs e configurações.

## Dependências diretas
- Nenhuma (somente stdlib).

## Testes relacionados
- Não há testes específicos; futuros módulos devem incluir testes ao serem implementados.
