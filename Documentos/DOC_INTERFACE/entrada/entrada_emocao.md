# interface/entrada/emocao.py

- Caminho: `jarvis/interface/entrada/emocao.py`
- Papel: detector leve de emoção/tonalidade (heurístico) para áudio de voz.
- Onde entra no fluxo: chamado pelo STT para registrar a última emoção de um comando.
- Atualizado em: 2026-01-19 (revisado com o codigo)

## Responsabilidades
- Calcular métricas simples (RMS, ZCR, pitch aproximado) e mapear para rótulos como `neutro`, `triste`, `agitado`, `feliz`, `calmo`.
- Suportar execução assíncrona (`detect_emotion_async`) para não bloquear o STT.
- Registrar eventos de emoção em log JSONL quando habilitado.

## Entrada e saida
- Entrada: `audio_bytes` PCM int16 mono + `sample_rate` (tipicamente 16 kHz).
- Saida: dict com `label`, `confidence`, `backend`, `metrics` ou `None` (quando desabilitado/inviável).

## Configuracao (env)
- `JARVIS_EMOTION_ENABLED` (default on) — liga/desliga o detector.
- `JARVIS_EMOTION_BACKEND` (default `heuristic`; outros valores retornam `None`).
- `JARVIS_EMOTION_MIN_MS` (default ~800 ms) — áudio mínimo para avaliar.
- `JARVIS_EMOTION_LOG` (liga log em `storage/logs/log_ops.jsonl`).

## Dependencias diretas
- `numpy` (opcional; sem ele o detector retorna `None`).
- stdlib: `threading`, `json`, `time`, `pathlib`.

## Testes relacionados
- `testes/test_emocao_interface.py`
- `testes/test_emocao_completo.py`
- `testes/test_gravacoes_reais.py` (integração)

## Qualidade e limites
- Heurístico simples em português; não usa modelo treinado.
- Retorna `None` se faltar `numpy`, se o áudio for muito curto ou se a feature estiver desligada.
- Logging é best-effort e silencioso em caso de falha.

## Observabilidade
- Log opcional via `JARVIS_EMOTION_LOG=1` (JSONL).
