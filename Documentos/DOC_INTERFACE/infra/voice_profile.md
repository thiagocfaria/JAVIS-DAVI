# interface/infra/voice_profile.py

- Caminho: `jarvis/interface/infra/voice_profile.py`
- Papel: auto-configurar o perfil de voz para usuários não técnicos (Piper obrigatório, CPU/latência previsíveis).
- Onde entra no fluxo: chamado por `jarvis/interface/entrada/app.py` antes de iniciar modos `--voice`/`--voice-loop`.
- Atualizado em: 2026-01-19 (revisado com o codigo)

## Responsabilidades
- Aplicar o perfil de voz solicitado (`JARVIS_VOICE_PROFILE`) usando `profiles.py`.
- Selecionar automaticamente um dispositivo de microfone viável e calibrar nível/ruído.
- Forçar defaults seguros de TTS (Piper), VAD/STT e wake word sem sobrescrever envs já setadas.
- Desabilitar recursos que atrapalham voz (auto-open de chat, overlap de voz, follow-up window).
- Validar se o Piper/modelo existe; se não, aborta com motivo (não cai para espeak-ng).

## Entrada e saida
- Entrada: `config` (objeto de configuração já carregado).
- Saida: tupla `(ok: bool, reason: str | None)`; `ok=False` quando Piper/modelo não está pronto.

## Configuracao (env principal)
- Toggle geral: `JARVIS_AUTO_CONFIGURE=0` desliga toda a auto-configuração.
- Perfil: `JARVIS_VOICE_PROFILE` (fast_cpu/balanced_cpu/noisy_room) aplicado se definido.
- Seleção de microfone: `JARVIS_AUTO_AUDIO_DEVICE` (on), `JARVIS_AUDIO_DEVICE_STRICT`, `JARVIS_AUDIO_AUTO_CALIBRATE`, `JARVIS_AUDIO_CALIB_SECONDS`.
- TTS (defaults se ausentes): `JARVIS_TTS_ENGINE=piper`, `JARVIS_TTS_ENGINE_STRICT=1`, `JARVIS_PIPER_MODELS_DIR`, `JARVIS_PIPER_VOICE`, `JARVIS_PIPER_BACKEND=python`, `JARVIS_PIPER_INTRA_OP_THREADS=1`, `JARVIS_PIPER_INTER_OP_THREADS=1`, `JARVIS_TTS_STREAMING=1`, `JARVIS_TTS_CACHE=1`, `JARVIS_TTS_WARMUP=1`, `JARVIS_TTS_ACK_PHRASE_WARMUP_BLOCKING=1`, `JARVIS_TTS_ACK_PHRASE`, `JARVIS_VOICE_PHASE1=1`.
- STT/VAD/wake word (defaults se ausentes): `JARVIS_STT_PROFILE=fast`, `JARVIS_STT_CPU_THREADS=2`, `JARVIS_STT_WORKERS=1`, `JARVIS_MIN_AUDIO_SECONDS=0.6`, `JARVIS_VAD_AGGRESSIVENESS=3`, `JARVIS_VAD_SILENCE_MS=250`, `JARVIS_VAD_PRE_ROLL_MS=120`, `JARVIS_VAD_POST_ROLL_MS=120`, `JARVIS_REQUIRE_WAKE_WORD=1`, `JARVIS_WAKE_WORD=jarvis`, `JARVIS_STT_LANGUAGE=pt`, `JARVIS_STT_COMMAND_BIAS="jarvis, oi jarvis"`, `JARVIS_STT_INITIAL_PROMPT=Jarvis`, `JARVIS_STT_WARMUP=1`, `JARVIS_STT_NORMALIZE_AUDIO=0`.
- Outros ajustes: `JARVIS_VOICE_OVERLAP_PLAN=0`, `JARVIS_FOLLOWUP_SECONDS=0`, `JARVIS_FOLLOWUP_MAX_COMMANDS=0`, `JARVIS_EMOTION_ENABLED=0`, `JARVIS_VOICE_MAX_SECONDS=8`, `JARVIS_AUDIO_PREFER_16K=1`, `JARVIS_AEC_BACKEND=simple`, `JARVIS_DEBUG=0`.
- Respeito a overrides: se `JARVIS_TTS_ENGINE` for `espeak`/`espeak-ng`, não força Piper.

## Dependencias diretas
- `numpy` e `sounddevice` (opcionais) para auto-seleção/calibração de microfone.
- `jarvis.interface.infra.profiles` para carregar/aplicar perfis quando configurados.
- stdlib: `os`, `pathlib`.

## Testes relacionados
- `testes/test_voice_profile_autoconfig.py`
- Coberto indiretamente em `testes/test_app_voice_interface.py` (patches de auto-config).

## Qualidade e limites
- Só seta envs que estão vazias; usuários avançados podem sobrescrever manualmente.
- Se Piper ou modelo não existirem, retorna `ok=False` com mensagem e não cai para voz robótica.
- Auto-seleção de microfone é best-effort; se falhar, mantém envs do usuário.

## Observabilidade
- Sem logs diretos; falhas retornam `reason` para o chamador exibir.
