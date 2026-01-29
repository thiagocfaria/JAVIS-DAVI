# interface/infra/profiles.py

- Caminho: `jarvis/interface/infra/profiles.py`
- Papel: definir perfis de voz pré-definidos (fast_cpu, balanced_cpu, noisy_room) e aplicar envs padrão.
- Onde entra no fluxo: chamado por `voice_profile.auto_configure_voice_profile` e pelo preflight para sugerir parâmetros.
- Atualizado em: 2026-01-28 (revisado com o código; todos os perfis usam STT tiny, backend padrão faster_whisper; whisper_cpp bloqueado)

## Responsabilidades
- Guardar perfis com parâmetros de VAD/STT (silence_ms, pre/post-roll, modelo STT).
- `load_profile()` resolve o perfil via argumento ou `JARVIS_VOICE_PROFILE`.
- `apply_profile()` seta envs padrão respeitando valores já definidos pelo usuário.

## Entrada e saida
- Entrada: nome do perfil (str opcional).
- Saida: dict `VoiceProfile` (cópia) ou envs ajustadas (sem retorno).

## Configuracao
- `JARVIS_VOICE_PROFILE` (`fast_cpu` | `balanced_cpu` | `noisy_room`); default `balanced_cpu`.
- Perfis ajustam `JARVIS_VAD_*`, `JARVIS_MIN_AUDIO_SECONDS`, `JARVIS_STT_MODEL` apenas se ausentes.

## Dependencias diretas
- Apenas stdlib (`os`, `typing`).

## Testes relacionados
- `testes/test_profiles.py`
- `testes/test_preflight_profiles.py`

## Qualidade e limites
- Perfil inválido gera `ValueError`.
- `apply_profile` não sobrescreve envs já setadas (overrides do usuário são preservados).
