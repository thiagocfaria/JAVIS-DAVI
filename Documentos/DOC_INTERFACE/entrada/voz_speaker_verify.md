# interface/entrada/speaker_verify.py

- Caminho: `jarvis/interface/entrada/speaker_verify.py`
- Papel: verificar se a voz do comando e do locutor cadastrado.
- Onde entra no fluxo: filtro opcional antes de aceitar comando de voz.
- Atualizado em: 2026-01-24 (política de áudio curto conferida; segue ativa)

## Responsabilidades
- Criar embedding (enroll) e salvar voiceprint.
- Comparar embedding atual com voiceprint (cosine similarity).
- Aplicar threshold configuravel.
- Armazenar voiceprint em JSON com lista `embedding` (ou payload criptografado quando passphrase esta ativa).

## Entrada e saida
- Entrada: audio PCM int16 mono; reamostra para 16 kHz quando necessario.
- Saida: `(score, ok)` ou embedding.

## Configuracao (env)
- `JARVIS_SPK_VERIFY` (liga/desliga)
- `JARVIS_SPK_THRESHOLD` (padrao 0.75)
- `JARVIS_SPK_MIN_AUDIO_MS` (padrao 1000; abaixo disso a verificacao falha)
- `JARVIS_CONFIG_DIR` (local do voiceprint)
- `JARVIS_SPK_VOICEPRINT_PASSPHRASE` (opcional, criptografar voiceprint)
- `JARVIS_DEBUG`
  - Default voiceprint: `~/.config/jarvis/voiceprint.json`

## Dependencias diretas
- `resemblyzer`
- `numpy`
- `scipy` (opcional, reamostragem)
- `cryptography` (opcional, criptografar voiceprint)

## Testes relacionados
- `testes/test_speaker_verify_interface.py`
- `testes/test_voice_adapters.py` (usa adapter)

## Comandos uteis
- Teste: `PYTHONPATH=. pytest -q testes/test_speaker_verify_interface.py`
- Verificar path: `python -c "from jarvis.interface.entrada.speaker_verify import voiceprint_path; print(voiceprint_path())"`

## Qualidade e limites
- Se nao houver voiceprint, verif falha.
- Se `JARVIS_SPK_VERIFY=0`, retorna ok.
- Se `JARVIS_SPK_VERIFY=1` mas o resemblyzer nao esta disponivel, a verificacao e ignorada (ok).
- Se `scipy` estiver ausente, a reamostragem nao ocorre (usa o audio original).
- Voiceprint e mantido em cache para reduzir IO.
- Se `JARVIS_SPK_VOICEPRINT_PASSPHRASE` estiver setado e `cryptography` faltar, o enroll falha.
- O modulo salva o voiceprint automaticamente quando chamado; a confirmacao explicita e feita no orquestrador antes do enroll.
- Se o voiceprint estiver criptografado e a passphrase estiver ausente, a verificacao falha.
- Audio curto falha a verificacao para evitar falso positivo.


## Performance (estimativa)
- Uso esperado: medio (embedding).
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Debug por `JARVIS_DEBUG=1`.

## Problemas conhecidos (hoje)
- Sem bloqueios criticos conhecidos neste modulo.

## Melhorias sugeridas
- Adicionar confirmacao explicita antes de salvar o voiceprint (ex: prompt no orquestrador).
