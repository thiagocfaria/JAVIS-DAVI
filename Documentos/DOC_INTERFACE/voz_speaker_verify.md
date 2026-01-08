# voz/speaker_verify.py

- Caminho: `jarvis/voz/speaker_verify.py`
- Papel: verificar se a voz do comando e do locutor cadastrado.
- Onde entra no fluxo: filtro opcional antes de aceitar comando de voz.

## Responsabilidades
- Criar embedding (enroll) e salvar voiceprint.
- Comparar embedding atual com voiceprint (cosine similarity).
- Aplicar threshold configuravel.
- Armazenar voiceprint em JSON com lista `embedding`.

## Entrada e saida
- Entrada: audio PCM int16 mono; reamostra para 16 kHz quando necessario.
- Saida: `(score, ok)` ou embedding.

## Configuracao (env)
- `JARVIS_SPK_VERIFY` (liga/desliga)
- `JARVIS_SPK_THRESHOLD` (padrao 0.75)
- `JARVIS_SPK_MIN_AUDIO_MS` (padrao 1000; abaixo disso a verificacao e pulada)
- `JARVIS_CONFIG_DIR` (local do voiceprint)
- `JARVIS_DEBUG`
  - Default voiceprint: `~/.config/jarvis/voiceprint.json`

## Dependencias diretas
- `resemblyzer`
- `numpy`
- `scipy` (opcional, reamostragem)

## Testes relacionados
- `testes/test_speaker_verify_interface.py`
- `testes/test_voice_adapters.py` (usa adapter)

## Comandos uteis
- Teste: `PYTHONPATH=. pytest -q testes/test_speaker_verify_interface.py`
- Verificar path: `python -c "from jarvis.voz.speaker_verify import voiceprint_path; print(voiceprint_path())"`

## Qualidade e limites
- Se nao houver voiceprint, verif falha.
- Se `JARVIS_SPK_VERIFY=0`, retorna ok.
- Se `JARVIS_SPK_VERIFY=1` mas o resemblyzer nao esta disponivel, a verificacao e ignorada (ok).
- Se `scipy` estiver ausente, a reamostragem nao ocorre (usa o audio original).
- Voiceprint e mantido em cache para reduzir IO.


## Performance (estimativa)
- Uso esperado: medio (embedding).
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Debug por `JARVIS_DEBUG=1`.

## Problemas conhecidos (hoje)
- Voiceprint e salvo em JSON simples (sem criptografia).
- Audio curto pode gerar falso negativo.

## Melhorias sugeridas
- Explicar UX para cadastro (mensagem guiada + confirmacao).
