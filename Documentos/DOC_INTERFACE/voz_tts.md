# voz/tts.py

- Caminho: `jarvis/voz/tts.py`
- Papel: TTS local (Piper) com fallback para espeak-ng.
- Onde entra no fluxo: saida de voz (fala do Jarvis).

## Responsabilidades
- Resolver modelo Piper e executar pipeline `piper | aplay`.
- Procurar modelo em `JARVIS_PIPER_MODELS_DIR`, `~/.local/share/piper`, `/usr/share/piper-voices`.
- Fallback para espeak-ng.
- Modo silencioso (`tts_mode=none`).

## Entrada e saida
- Entrada: texto UTF-8.
- Saida: audio no dispositivo de saida (ALSA).

## Configuracao (env/config)
- `JARVIS_PIPER_MODELS_DIR`
- `JARVIS_PIPER_VOICE`
- Config `tts_mode` (local/none) e env `JARVIS_TTS_MODE`

## Dependencias diretas
- `piper` (binario)
- `espeak-ng` (binario)
- `aplay` (binario)

## Testes relacionados
- `testes/test_tts_interface.py`

## Comandos uteis
- Teste: `PYTHONPATH=. pytest -q testes/test_tts_interface.py`
- Falar: `PYTHONPATH=. python -c "from jarvis.voz.tts import TextToSpeech; from types import SimpleNamespace; TextToSpeech(SimpleNamespace(tts_mode='local')).speak('ola')"`

## Qualidade e limites
- Ignora texto vazio/espacos.
- Piper depende de modelo local; sem modelo cai para espeak-ng.
- Piper usa `--output-raw` e toca em 22050 Hz via `aplay`.
- Se piper falhar e espeak-ng nao existir, nao ha audio.
- Preflight avisa quando piper esta instalado sem modelo local.
- Chamadas sao serializadas (lock interno) para evitar sobreposicao.


## Performance (estimativa)
- Uso esperado: medio (piper/espeak).
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Logs opcionais via `JARVIS_DEBUG=1` (erros e fallback piper->espeak).

## Problemas conhecidos (hoje)
- Sem controle de volume/ganho.

## Melhorias sugeridas
Nenhuma pendente.
