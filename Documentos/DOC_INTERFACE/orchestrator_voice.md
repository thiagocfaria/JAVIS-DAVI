# Orchestrator (voz) — Overlap + fase 1 (latencia percebida)

- Caminho: `jarvis/cerebro/orchestrator.py`
- Entrada: `transcribe_and_handle()` (modo `--voice`)
- Objetivo: reduzir “silencio” percebido entre o fim da fala do usuario e o inicio de uma resposta do Jarvis.

## O que foi implementado

### 1) Fase 1 (“Entendi…”) instantanea, sem voz robotica
Quando habilitado, o Jarvis pode emitir um “ack” imediato (frase curta ou beep) para o usuario perceber que o sistema esta vivo, enquanto o resto do pipeline roda (LLM/acoes).

- Env:
  - `JARVIS_VOICE_PHASE1=1` (liga)
- Implementacao:
  - O STT dispara `on_eos` assim que a gravacao termina e ele vai comecar a transcrever (antes do texto final ficar pronto).
    - Isso permite tocar a fase 1 enquanto o STT/LLM ainda estao trabalhando.
  - `Orchestrator._try_voice_phase1_ack()` chama `TextToSpeech.play_phase1_ack()`.
  - `TextToSpeech.play_phase1_ack()` (em `jarvis/interface/saida/tts.py`) usa:
    - Preferencia: frase humanizada pre-gerada via `JARVIS_TTS_ACK_PHRASE` (Piper)
    - Fallback: earcon/beep (nao usa espeak-ng)
  - Telemetria: `eos_to_phase1_ms` e `eos_to_ack_ms` expostos em `voice_stage_metrics`.

### 2) Overlap: prefetch de plano com parciais (quando houver)
Quando o backend de STT fornece parciais (RealtimeSTT), da para comecar a “pensar” (gerar o plano) antes do texto final estar 100% pronto.

- Env:
  - `JARVIS_VOICE_OVERLAP_PLAN=1` (liga)
  - `JARVIS_VOICE_OVERLAP_STABLE_MS=350` (espera a parcial estabilizar)
  - `JARVIS_VOICE_OVERLAP_MIN_CHARS=12`
- Regras de seguranca/qualidade:
  - O plano prefetch nao substitui o fluxo normal “a qualquer custo”.
  - Se o plano prefetch for invalido/falhar, o fluxo normal gera um novo plano.
- Observacao: overlap depende de parciais do backend de STT; o default `faster_whisper` (tiny) e offline e nao gera parciais. So entra em acao com streaming (RealtimeSTT).

## Métricas (telemetria)
O evento `voice_stage_metrics` agora inclui:
- `eos_to_phase1_ms`: fim da fala -> inicio do “ack”/fase 1
- `eos_to_ack_ms`: fim da fala -> ack interno do TTS (earcon/phrase durante o TTS)
- `eos_to_first_audio_ms`: fim da fala -> primeiro audio da resposta principal

Obs: `eos_to_phase1_ms` e a metrica mais “humana” para perceber se o Jarvis responde rapido (mesmo que a resposta completa venha depois).

## Benchmark offline (sem microfone)
Para medir `eos_to_phase1_ms` sem depender de microfone, o benchmark `eos_to_first_audio` suporta:
- `JARVIS_BENCH_PHASE1=1` (toca a fase 1 imediatamente apos `eos_ts` no benchmark).
