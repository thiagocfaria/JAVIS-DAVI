# Auto-config de voz (estilo “ChatGPT”)

Objetivo: o usuario final nao deve precisar configurar `.env`/variaveis para ter:
- voz humanizada (Piper)
- baixa latencia percebida (fase 1 “Entendi…”)
- uso de CPU previsivel (threads limitadas)
- **sem** cair para voz robotica (espeak-ng)

## Onde fica no codigo
- `jarvis/interface/infra/voice_profile.py`
  - Funcao: `auto_configure_voice_profile(config)`
- `jarvis/interface/entrada/app.py`
  - Chama o auto-config quando roda `--voice` ou `--voice-loop`.

## O que o auto-config faz (na pratica)
Quando o usuario executa `python -m jarvis.app --voice`:
1) O Jarvis aplica defaults seguros **somente se** a env nao estiver setada (ou seja: usuario avancado ainda consegue sobrescrever).
2) O Jarvis verifica se o Piper esta disponivel e se existe um modelo local do Piper.
3) Se o modelo existir: segue com voz humanizada e perfil CPU-safe.
4) Se o modelo nao existir: o Jarvis avisa e aborta (nao cai para voz robotica).

## Defaults aplicados automaticamente (quando ausentes)
- `JARVIS_TTS_ENGINE=piper`
- `JARVIS_TTS_ENGINE_STRICT=1` (nao faz fallback para espeak-ng)
- `JARVIS_PIPER_MODELS_DIR=storage/models/piper`
- `JARVIS_PIPER_VOICE=pt_BR-faber-medium`
- `JARVIS_PIPER_BACKEND=python` (modelo carregado em memoria)
- `JARVIS_PIPER_INTRA_OP_THREADS=1`
- `JARVIS_PIPER_INTER_OP_THREADS=1`
- `JARVIS_TTS_STREAMING=1`
- `JARVIS_TTS_CACHE=1`
- `JARVIS_TTS_WARMUP=1` (warmup **nao-bloqueante** por padrao)
- `JARVIS_TTS_ACK_PHRASE_WARMUP_BLOCKING=1` (garante que a frase da fase 1 já está pronta na 1a interação)
- `JARVIS_VOICE_PHASE1=1`
- `JARVIS_TTS_ACK_PHRASE="Entendi. Já vou responder."`
- `JARVIS_VOICE_OVERLAP_PLAN=0` (evita disputar CPU por padrao)
- `JARVIS_STT_CPU_THREADS=2` (limita CPU do STT)
- `JARVIS_STT_WORKERS=1` (evita paralelismo extra)

## Auto-relocate de paths (quando `.env` tem caminhos sem permissao)
Se o `.env` tiver caminhos hardcoded sem permissao (ex.: `/home/u/.jarvis/...`), o Jarvis tenta relocarlos automaticamente para dentro de `JARVIS_DATA_DIR` para nao quebrar em maquinas diferentes.

## Flags para dev/power users
- Desligar auto-config:
  - `JARVIS_AUTO_CONFIGURE=0`
- Desligar auto-relocate de paths:
  - `JARVIS_AUTO_RELOCATE_PATHS=0`
- Warmup bloqueante (opcional, mais consistente pra p95):
  - `JARVIS_TTS_WARMUP_BLOCKING=1`

## Auto-selecao do microfone (novo)
Problema real observado: alguns dispositivos ALSA (`hw:*`) podem estar "bugados" para voz, chegando clipados (peak=1.0) mesmo em silencio. Isso faz o VAD nunca achar silencio, aumenta a latencia e causa transcricoes erradas.

No modo voz, o Jarvis tenta selecionar automaticamente um input melhor quando `JARVIS_AUDIO_DEVICE` nao esta definido:
- testa rapidamente alguns candidatos comuns (ex.: `pulse`, `pipewire`, `default`)
- mede um "silence probe" curto (<= 0.25s)
- escolhe o menor ruido/menor clipping

Flag:
- Desligar auto-selecao do microfone:
  - `JARVIS_AUTO_AUDIO_DEVICE=0`
- Nao sobrescrever um `JARVIS_AUDIO_DEVICE` escolhido manualmente:
  - `JARVIS_AUDIO_DEVICE_STRICT=1`
