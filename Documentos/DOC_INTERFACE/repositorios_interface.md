# Repositórios externos úteis (interface)

Foco: só manter o que ainda faz sentido considerar para o sistema atual. Itens já integrados (RealtimeSTT, RealtimeTTS, AEC/barge-in, wake word, streaming local) foram removidos.

## 1) UI/Chat (Vercel AI Chatbot)
- Por que considerar: front pronto para chat streaming, upload e “tool UI”. Pode substituir/estilizar a `chat_ui` atual, mantendo backend local do Jarvis (chat_log/chat_inbox).
- O que avaliar: streaming resumable, DataStream paralelo, upload de arquivos, títulos automáticos e UX de erros.
- Passos se for usar: mapear pontos do template (components/chat.tsx, app/(chat)/api/chat/route.ts), definir endpoint local/SSE, desligar Auth/DB, integrar com Tauri se empacotar.

## 2) Empacotamento desktop (Tauri)
- Por que considerar: bundlar UI + backend sidecar para uso offline em desktop.
- O que avaliar: healthcheck do sidecar, acesso a microfone/áudio, instalação de deps nativas (sounddevice/webrtcvad) e atualização automática.

## 3) Emoção/tonalidade (SpeechBrain/openSMILE) — opcional futuro
- Estado atual: temos heurística leve em `interface/entrada/emocao.py`. Modelos pesados (SpeechBrain) não estão integrados.
- Por que considerar: metadados de emoção para UI/telemetria; não deve bloquear STT/TTS.
- Se for seguir: baixar modelo, gate por duração/VAD, cache lazy, threshold de confiança, telemetria; rodar de forma assíncrona e segura.

Checklist (estrutura de modulo no Jarvis):
1) [x] Criar modulo `jarvis/interface/entrada/emocao.py`
2) [x] Configurar entrada padrao
3) [x] Configurar saida padrao
4) [x] Integrar no fluxo de voz
5) [x] Adicionar flags/env
6) [x] Registrar telemetria
7) [x] Expor para UI

Checklist (testes manuais - sem GPU):
1) [ ] Teste com audio curto
2) [ ] Teste com fala normal
3) [ ] Teste sem VAD (silencio)
4) [ ] Teste de falha segura

### 6) Turn-taking leve + lock de locutor (interface)
- Turn-taking: `SpeechToText.get_last_turn_info()` retorna `is_complete`, `hold_ms` e `reason`.
- Uso futuro no cerebro: se `is_complete=False`, aguardar `hold_ms`; se nao vier nova fala, perguntar continuacao.
- Lock de locutor: `SpeechToText.get_last_speaker_state()` indica `ok/score/locked` para ignorar falas de fundo.
- Idioma unico: `SpeechToText.get_last_language_state()` pode retornar `action=confirm_switch` para pedir confirmacao antes de trocar idioma ativo.

Checklist (o que NAO importar):
1) [ ] Treinamento completo (recipes) no fluxo principal
2) [ ] Diarizacao em tempo real por padrao
3) [ ] Modelos gigantes sem GPU

Checklist (o que manter do Jarvis):
1) [ ] Pipeline de audio 16k mono + VAD
2) [ ] STT/TTS locais como fluxo principal

#### openSMILE (features rapidas, completo)
Checklist (openSMILE no Jarvis - completo):
1) [ ] Validar licenca para uso comercial
2) [ ] Definir modo de execucao
3) [ ] Garantir binario disponivel
4) [ ] Padronizar config de features
5) [ ] Integrar no pipeline do Jarvis
6) [ ] Classificador leve
7) [ ] Gate por VAD e duracao
8) [ ] Execucao assincrona
9) [ ] Cache de features
10) [ ] Telemetria de custo
11) [ ] Flags/ambiente
12) [ ] Falha segura

Ordem recomendada (producao, sem MVP):
1) Licenca + binario (itens 1-3)
2) Config padrao + qualidade (itens 4 + boas praticas)
3) Integracao no pipeline + flags (itens 5, 11)
4) Classificador leve + normalizacao (item 6)
5) Gate VAD + execucao assincrona + cache (itens 7-9)
6) Telemetria + falha segura (itens 10, 12)

Checklist (o que NAO importar do openSMILE):
1) [ ] Pipeline de treino completo (scripts/modeltrain)
2) [ ] Configs gigantes sem necessidade
3) [ ] Modos live/streaming no inicio

Checklist (boas praticas para qualidade):
1) [ ] Normalizar audio antes de extrair
2) [ ] Fixar sample rate (16k) no WAV
3) [ ] Documentar features usadas

### 6) Observabilidade/bench
Checklist (medicao sem atrapalhar):
1) [ ] Telemetria por etapa (captura, VAD, STT, TTS)
2) [ ] Metricas de latencia (tempo total e time-to-first-token/chunk)
3) [ ] CPU/RAM (psutil) e GPU (nvidia-smi quando disponivel)
4) [ ] Logs em JSONL (eventos e resultados)
5) [ ] Bench por comando padrao (mesma frase para comparacao)
6) [ ] Modo silencioso para medir STT isolado

### 7) Empacotamento desktop (Tauri)
Checklist (como empacotar corretamente):
1) [ ] Definir onde a UI roda no desktop
2) [ ] Configurar `tauri.conf.json`
3) [ ] Ligar a UI ao backend do Jarvis
4) [ ] Sidecar do Jarvis (opcional)
5) [ ] Permissoes do app
6) [ ] CSP/localhost/WS
7) [ ] Build e distribuicao
8) [ ] Atualizador (opcional)
9) [ ] Logs e diagnostico

## Matriz de substituicao (Jarvis vs repo)
| Funcionalidade | Jarvis atual | Repositorio(s) | Acao | Observacao |
| --- | --- | --- | --- | --- |
| UI/Chat | chat_log + UI simples | vercel-ai-chatbot | Hibrido | Manter log local + streaming na UI |
| Transporte audio | sounddevice local | livekit-agents | Hibrido | LiveKit remoto, sounddevice local |
| VAD/turn detection | webrtcvad (local) | livekit-agents + RealtimeSTT | Hibrido | Um VAD por fluxo; endpointing curto |
| Wake word | filtro por texto + Porcupine/OpenWakeWord (audio) | RealtimeSTT | Hibrido | Audio primeiro, texto como fallback |
| STT parcial | parciais via callback | RealtimeSTT | Adicionar | Parciais so atualizam UI |
| STT final | faster-whisper local | RealtimeSTT (backend) | Manter | Final sempre no Jarvis |
| TTS | Piper/espeak local | RealtimeTTS | Hibrido | Streaming + AEC + fallback local |
| Emoção | nao tem | SpeechBrain + openSMILE | Adicionar | Metadata apenas |
| Observabilidade | Telemetry | scripts/bench | Manter | Medir sem interferir |
| Desktop app | nao tem | Tauri | Adicionar | UI bundlada + sidecar |

## Repositorios (referencias e caminhos locais)
- Vercel AI Chatbot: https://github.com/vercel/ai-chatbot
  - Local: `jarvis/REPOSITORIOS_CLONAR/vercel-ai-chatbot`
- LiveKit Agents: https://github.com/livekit/agents
  - Local: `jarvis/REPOSITORIOS_CLONAR/livekit-agents`
- RealtimeSTT: https://github.com/KoljaB/RealtimeSTT
  - Local (clone, transicao): `jarvis/REPOSITORIOS_CLONAR/realtimestt`
  - Extraido (copia vendorizada usada pelo Jarvis): `jarvis/third_party/realtimestt`
- RealtimeTTS: https://github.com/KoljaB/RealtimeTTS
  - Local: `jarvis/REPOSITORIOS_CLONAR/realtimetts`
- RealtimeVoiceChat (extra): https://github.com/KoljaB/RealtimeVoiceChat
  - Local: `jarvis/REPOSITORIOS_CLONAR/realtimevoicechat`
- SpeechBrain: https://github.com/speechbrain/speechbrain
  - Local: `jarvis/REPOSITORIOS_CLONAR/speechbrain`
- SpeechBrain emotion model: https://huggingface.co/speechbrain/emotion-recognition-wav2vec2-IEMOCAP
  - Local: `jarvis/REPOSITORIOS_CLONAR/speechbrain-emotion-model`
- openSMILE: https://github.com/audeering/opensmile
  - Local: `jarvis/REPOSITORIOS_CLONAR/opensmile`
- Tauri: https://github.com/tauri-apps/tauri
  - Local: `jarvis/REPOSITORIOS_CLONAR/tauri`

## Recomendacao (performance maxima sem baguncar o Jarvis)
- UI: vercel/ai-chatbot (bonita + streaming + customizavel)
- Voz realtime: livekit/agents (WebRTC + turn detection)
- STT streaming: RealtimeSTT (transcricao parcial)
- TTS streaming: RealtimeTTS (fala enquanto responde)
- Emocao: speechbrain + modelo pronto (metadata)
- Desktop app: tauri (empacotar a UI como software)

## Como encaixar no Jarvis
- Entrada/Saida: migrar por etapas (UI e voz podem vir primeiro).
- Cerebro: manter orchestrator/politica/validacao como backend.
- Execucao: manter automacao atual e plugar por API.
