# interface/saida/tts.py

- Caminho: `jarvis/interface/saida/tts.py`
- Papel: TTS local (Piper) com fallback para espeak-ng.
- Onde entra no fluxo: saida de voz (fala do Jarvis).
- Atualizado em: 2026-01-24 (backend Piper in-proc, TTFA warm ~50–80ms)

## Responsabilidades
- Resolver engine/backends de TTS (Piper in-proc preferido, CLI como fallback; espeak-ng como último recurso).
- Manter modelo Piper carregado em memória (backend Python via `piper-tts`) para TTFA baixo.
- Suportar streaming/chunking, cache de frases curtas e barge-in (interromper playback).
- Modo silencioso (`tts_mode=none`).

## Entrada e saída
- Entrada: texto UTF-8.
- Saída: áudio no dispositivo ALSA; opcional callback `on_audio_chunk` (streaming).

## Configuração (env/config)
- `JARVIS_TTS_ENGINE` (`auto`/`piper`/`espeak-ng`) seleciona engine de forma explicita.
  - `auto` (padrao): tenta Piper; se falhar, cai para espeak-ng.
  - `piper`: tenta usar Piper; se indisponivel, pode cair para espeak-ng (ou ficar mudo se `JARVIS_TTS_ENGINE_STRICT=1`).
  - `espeak-ng`: força espeak-ng (voz robotica).
- `JARVIS_TTS_ENGINE_STRICT=1` (quando `JARVIS_TTS_ENGINE=piper`) nao faz fallback para espeak-ng.
- `JARVIS_PIPER_MODELS_DIR`
- `JARVIS_PIPER_VOICE`
- `JARVIS_PIPER_BIN` (opcional): caminho explicito para o binario `piper` (se nao estiver no PATH).
- `JARVIS_PIPER_BACKEND` (`auto`/`python`/`cli`) (opcional):
  - `auto` (padrao): tenta backend Python (mantem modelo carregado em memoria); se falhar, tenta CLI `piper`.
  - `python`: força backend Python (menor TTFA “warm” e menos overhead por fala).
  - `cli`: força o caminho antigo `piper | aplay` (spawna processo por fala).
- `JARVIS_PIPER_INTRA_OP_THREADS` / `JARVIS_PIPER_INTER_OP_THREADS` (opcional): limita threads do ONNX Runtime do Piper (reduz pico de CPU, sem mudar qualidade).
  - Recomendado (CPU-safe): `1/1`
  - Se tiver CPU sobrando e quiser TTFA um pouco menor: `2/1`
- `JARVIS_PIPER_MODEL` (opcional): caminho completo para o `.onnx` (ignora busca por voz/pastas).
- `JARVIS_PIPER_VOICE_QUALITY_ORDER` (opcional): ordem de preferencia quando `JARVIS_PIPER_VOICE` for um prefixo sem qualidade (default `low,medium,high`).
- Config `tts_mode` (local/none) e env `JARVIS_TTS_MODE`
- `JARVIS_TTS_VOLUME` (0.0 a 2.0; default 1.0)
- `JARVIS_TTS_WARMUP=1` (pre-aquece o Piper no startup)
- `JARVIS_TTS_WARMUP_TEXT` (texto curto do warmup; default "ola")
- `JARVIS_TTS_WARMUP_BLOCKING=1` (opcional): faz o warmup de forma bloqueante (carrega o modelo antes do 1o uso; bom para servico/bench).
- `JARVIS_TTS_CACHE=1` (cache de audio para frases curtas)
- `JARVIS_TTS_CACHE_MAX_CHARS` (default 120)
- `JARVIS_TTS_CACHE_MAX_ITEMS` (default 32)
- `JARVIS_TTS_CHUNKING=1` (fala em chunks por sentenca)
- `JARVIS_TTS_CHUNK_MAX_CHARS` (default 160)
- `JARVIS_TTS_BARGE_IN=1` (interrompe chunks quando arquivo stop existe)
- `JARVIS_TTS_BARGE_IN_STOP_FILE` (default `~/.jarvis/STOP`)
- `JARVIS_TTS_STREAMING=1` (stream de audio em chunks do Piper para reduzir TTFA)
- `JARVIS_TTS_STREAM_CHUNK_BYTES` (default 4096; tamanho do chunk do stream)
- `JARVIS_TTS_AUTO_CHUNK_LONG_TEXT=1` (opcional; default **0**): tenta quebrar textos longos em sentencas automaticamente.
  - `JARVIS_TTS_AUTO_CHUNK_MIN_CHARS` (default 240)
  - Nota: neste ambiente, piorou `tts_first_audio_ms` (entao manter desligado).
  - `JARVIS_TTS_ACK_EARCON=1` (opcional): toca um “beep/ack” rapido se o Piper demorar para comecar (melhora latencia percebida sem usar voz robotica).
  - `JARVIS_TTS_ACK_PHRASE` (opcional): fala uma frase curta humanizada como ack (ex: "Entendi. Já vou responder."). Se configurado e pré-gerado, substitui o beep.
- `JARVIS_TTS_ACK_PHRASE_WARMUP=1` (default): tenta pré-gerar a frase de ack no startup (para ficar rápido na hora).
- `JARVIS_TTS_ACK_PHRASE_WARMUP_BLOCKING=1` (opcional): gera a frase de ack de forma bloqueante (útil em benchmark).
- `JARVIS_TTS_ACK_TIMEOUT_MS` (default 350): atraso ate o ack.
- `JARVIS_TTS_ACK_DURATION_MS` (default 120): duracao do beep.
- `JARVIS_TTS_ACK_FREQ_HZ` (default 880): frequencia do beep.
- `JARVIS_TTS_ACK_VOLUME` (0-100; default 20): volume do beep.
- `JARVIS_TTS_ASYNC=1` (fala em thread separada)
- `JARVIS_TTS_AUDIO_DEVICE` (seleciona device do `aplay`, ex: `hw:1,0`)
- `JARVIS_TTS_WORD_TIMING=1` (habilita word timing estimado)
- `JARVIS_TTS_WPM` (palavras por minuto para estimativa; default 150)
- `JARVIS_AEC_BACKEND` (`simple`/`none`) quando quiser alimentar referencia de playback

## Dependências diretas
- `piper-tts` (backend Python e binário `piper`)
- `espeak-ng` (binário fallback)
- `aplay` (binário)

## Testes relacionados
- `testes/test_tts_interface.py`

## Instalacao e configuracao do Piper (voz humanizada)

Para usar a voz humanizada (Piper) ao inves da robotica (espeak-ng):

### Auto-config (modo voz)
Quando voce roda `python -m jarvis.app --voice` / `--voice-loop`, o Jarvis tenta aplicar automaticamente um perfil “producao/CPU-safe” (sem exigir que o usuario edite `.env`), **desde que** exista modelo local do Piper em `storage/models/piper/`.

Se o modelo nao existir, o Jarvis vai avisar e **nao** vai cair para `espeak-ng` (voz robotica).

Para desligar o auto-config (dev/power users):
- `JARVIS_AUTO_CONFIGURE=0`

Se seu `.env` tiver paths hardcoded sem permissao (ex.: `/home/u/.jarvis/...`), o Jarvis tenta relocarlos automaticamente para `JARVIS_DATA_DIR`.
Para desligar:
- `JARVIS_AUTO_RELOCATE_PATHS=0`

Obs: o auto-config liga `JARVIS_TTS_WARMUP=1`, mas deixa o warmup **nao-bloqueante** por padrao (para o app abrir rapido).
Se quiser warmup bloqueante (mais “p95” consistente), configure manualmente:
- `JARVIS_TTS_WARMUP_BLOCKING=1`

Para garantir que a **fase 1** (frase humanizada) sai perfeita já na 1a interação, o auto-config liga:
- `JARVIS_TTS_ACK_PHRASE_WARMUP_BLOCKING=1`

1. **Instalar binario piper**:
   - Baixar de: https://github.com/rhasspy/piper/releases
   - Ou compilar do codigo fonte
   - Colocar em um dos locais: `~/.local/bin/`, `/usr/local/bin/`, `/usr/bin/`, ou adicionar ao PATH
   - Alternativa (recomendado no dev): se a venv tiver `piper-tts` instalado, o binario costuma estar em `.venv/bin/piper` e o Jarvis ja detecta automaticamente (sem precisar ativar a venv).

2. **Baixar modelo de voz**:
   ```bash
   mkdir -p ~/.local/share/piper-models
   cd ~/.local/share/piper-models
   # Voz portugues brasileiro (padrao)
   wget https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx
   wget https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json
   ```

3. **Verificar instalacao**:
   ```bash
   # Verificar binario
   which piper
   # Ou
   ~/.local/bin/piper --version

   # Verificar modelo
   ls ~/.local/share/piper-models/*.onnx

   # Testar voz
   echo "Olá, eu sou o Jarvis" | piper --model ~/.local/share/piper-models/pt_BR-faber-medium.onnx --output-raw | aplay -r 22050 -f S16_LE -t raw -
   ```

4. **Configurar variaveis de ambiente (opcional)**:
   ```bash
   export JARVIS_PIPER_MODELS_DIR="$HOME/.local/share/piper-models"
   export JARVIS_PIPER_VOICE="pt_BR-faber-medium"
   ```

### Padrao recomendado no repo (sem depender de ~/.local)
Para manter o sistema “portavel” (e evitar depender do HOME do servidor), o Jarvis tambem procura modelos em:
- `storage/models/piper/` (dentro do repo)

Padrao sugerido:
```bash
export JARVIS_TTS_ENGINE=piper
export JARVIS_TTS_ENGINE_STRICT=1
export JARVIS_PIPER_MODELS_DIR="storage/models/piper"
export JARVIS_PIPER_VOICE="pt_BR-faber-medium"
export JARVIS_TTS_STREAMING=1
export JARVIS_TTS_STREAM_CHUNK_BYTES=4096
export JARVIS_TTS_CACHE=1
export JARVIS_TTS_WARMUP=1
export JARVIS_TTS_ACK_EARCON=1
export JARVIS_TTS_ACK_TIMEOUT_MS=250
export JARVIS_TTS_ACK_PHRASE="Entendi. Já vou responder."
```

### Notas de performance (importante)
- `JARVIS_TTS_STREAM_CHUNK_BYTES`: neste ambiente, `4096` ficou melhor que `1024` para `tts_first_audio_ms` (TTFA) no Piper.
- `JARVIS_TTS_CACHE=1`: acelera muito frases curtas repetidas (ex.: “Entendi.”). Na 1a vez o Piper gera audio; na 2a vez sai do cache e vira “quase instantaneo”.

5. **Verificar qual engine esta sendo usado**:
   ```bash
   PYTHONPATH=. python -c "from jarvis.interface.saida.tts import TextToSpeech, check_tts_deps; from types import SimpleNamespace; print('Deps:', check_tts_deps()); tts = TextToSpeech(SimpleNamespace(tts_mode='local')); print('Engines disponiveis:', tts.get_available_engines())"
   ```
   - Se mostrar `['piper', 'espeak-ng']`: Piper disponivel (usara voz humanizada)
   - Se mostrar apenas `['espeak-ng']`: Piper nao encontrado (usara voz robotica)

## Comandos úteis
- Teste: `PYTHONPATH=. pytest -q testes/test_tts_interface.py`
- Falar: `PYTHONPATH=. python -c "from jarvis.interface.saida.tts import TextToSpeech; from types import SimpleNamespace; TextToSpeech(SimpleNamespace(tts_mode='local')).speak('ola')"`
- Verificar engines: `PYTHONPATH=. python -c "from jarvis.interface.saida.tts import check_tts_deps; print(check_tts_deps())"`

## Qualidade e limites
- Ignora texto vazio/espacos.
- Piper in-proc preferido (TTFA warm baixo); CLI é fallback quando backend Python não carrega.
- Fallback para espeak-ng se Piper indisponível (ainda depende de binário/modelo).
- Streaming + `JARVIS_TTS_BARGE_IN=1` permitem interromper playback; `_terminate_process` usa `terminate` + `wait(1s)` + `kill`, então barge-in é best-effort (pode atrasar se o subprocess travar).
- `JARVIS_TTS_VOLUME=0` silencia fala mantendo fluxo.
- AEC simples: áudio do Piper pode ser usado como referência (`JARVIS_AEC_BACKEND=simple`).
- Logs de debug (`JARVIS_DEBUG=1`) mostram engine/fallback.


## Performance (estimativa)
- Uso esperado: medio (piper/espeak).
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- `TextToSpeech.get_last_metrics()`: `tts_ms`, `play_ms`, `tts_first_audio_ms`, `tts_first_audio_perf_ts`.
- `TextToSpeech.get_last_word_timings()`: palavras com `start_ms`/`end_ms` (estimado).
- Logs via `JARVIS_DEBUG=1` (engine/fallback/erros).

## Fase 1 (ack imediato do orchestrator)
No modo voz (`jarvis/cerebro/orchestrator.py`), existe um “ack” opcional de latencia percebida:
- `TextToSpeech.play_phase1_ack()` toca um beep/frase curta imediatamente.
- Habilita via `JARVIS_VOICE_PHASE1=1` (ver `Documentos/DOC_INTERFACE/orchestrator_voice.md`).

## Warmup (implementado - Etapa 1)
- **Warmup TTS:** `tts.speak(reply_text[:20])` implementado em `scripts/bench_interface.py` (linhas 676-680).
- **Beneficio:** Pre-carrega o modelo Piper antes das medições, evitando cold start no p95.
- **Impacto medido:** p95 reduzido de ~1500ms para **~1190ms** quando combinado com warmup STT (META OURO atingida no limite com faster_whisper).
- **Nota:** O warmup usa uma substring curta do texto de resposta para ser rápido e relevante.

## Problemas conhecidos (hoje)
- **Barge-in lento:** `tts.stop()` tem p95 de ~1005ms devido a `proc.wait(timeout=1)` em `_terminate_process()` (linha 618).
  - **Meta PRATA:** p95 < 120ms
  - **Meta OURO:** p95 < 80ms
  - **Correção necessária:** Remover `wait()` e usar `kill()` fire-and-forget para stop instantâneo.

## Melhorias sugeridas
- ~~Implementar warmup TTS no benchmark.~~ (resolvido - Etapa 1)
- Corrigir `_terminate_process()` para barge-in < 80ms (prioridade P0).
