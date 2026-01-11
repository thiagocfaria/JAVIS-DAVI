# Correcoes e melhorias da interface

Checklist enumerado em ordem de prioridade (P1 -> P2 -> P3).
Legenda: (Problema) = algo ruim hoje. (Melhoria) = sugestao de evolucao.

## P1
1) [x] [P1] (Problema) Sem `scipy`, a reamostragem falha quando o device nao suporta 16 kHz. (fonte: entrada_stt.md)
## P2
2) [x] [P2] (Problema) Nao ha confirmacao/ack do consumo do comando. (fonte: comunicacao_chat_inbox.md)
3) [x] [P2] (Problema) Sem lock de arquivo; multiplos escritores podem intercalar linhas. (fonte: comunicacao_chat_inbox.md)
4) [x] [P2] (Melhoria) Rotacao basica (por tamanho) para nao crescer sem controle. (fonte: comunicacao_chat_log.md)
5) [x] [P2] (Problema) Nao ha rotacao automatica; log pode crescer sem limite. (fonte: comunicacao_chat_log.md)
6) [x] [P2] (Problema) Checagem de deps de STT acontece apenas no inicio; falhas posteriores nao sao tratadas. (fonte: entrada_app.md)
7) [x] [P2] (Problema) Lista de ints 0-255 e tratada como bytes, o que pode mascarar erro. (fonte: entrada_audio_utils.md)
8) [x] [P2] (Problema) Nao valida sample rate ou canais; apenas tipo do payload. (fonte: entrada_audio_utils.md)
9) [x] [P2] (Problema) UI baseada em arquivos; sem lock/concorrencia. (fonte: entrada_chat_ui.md)
10) [x] [P2] (Problema) Follow-up e apenas por tempo; pode aceitar fala de fundo. (fonte: entrada_followup.md)
11) [x] [P2] (Problema) Nao ha cancelamento de comando em execucao. (fonte: entrada_gui_panel.md)
12) [x] [P2] (Problema) Pode reportar TTS OK mesmo sem modelo Piper instalado. (fonte: entrada_preflight.md)
13) [x] [P2] (Problema) Preflight valida presenca de deps, mas nao testa captura/tts de fato. (fonte: entrada_preflight.md)
14) [x] [P2] (Problema) Em Wayland sem X11, atalho global nao funciona. (fonte: entrada_shortcut.md)
15) [x] [P2] (Melhoria) Bloquear streaming em `transcribe_with_vad` quando capture_sr != 16k. (fonte: entrada_stt.md)
16) [x] [P2] (Melhoria) Opcao de AEC/NS/AGC antes do VAD. (fonte: entrada_stt.md)
17) [x] [P2] (Problema) Em `transcribe_once`, streaming pode rodar com capture_sr != 16k e ignorar `JARVIS_AUDIO_DEVICE`. (fonte: entrada_stt.md)
18) [x] [P2] (Problema) Se VAD/Rust nao estiverem disponiveis, `check_speech_present` pode aceitar ruido. (fonte: entrada_stt.md)
19) [x] [P2] (Problema) Sem AEC/NS/AGC; ruido ambiente pode virar texto. (fonte: entrada_stt.md)
20) [x] [P2] (Problema) Audio curto pode permitir falso positivo (aceita sem verificar). (fonte: voz_speaker_verify.md)
21) [x] [P2] (Problema) Nao reamostra audio; espera 16 kHz. (fonte: voz_speaker_verify.md)
22) [x] [P2] (Problema) Voiceprint e salvo em JSON simples (sem criptografia). (fonte: voz_speaker_verify.md)
23) [x] [P2] (Problema) Falhas de subprocesso sao silenciosas. (fonte: voz_tts.md)
24) [x] [P2] (Problema) Sem fila/queue; chamadas simultaneas podem sobrepor audio. (fonte: voz_tts.md)
25) [x] [P2] (Problema) Nao ha AEC/NS/AGC antes do VAD. (fonte: voz_vad.md)
26) [x] [P2] (Problema) webrtcvad pode errar com voz baixa/ruido. (fonte: voz_vad.md)
## P3
27) [x] [P3] (Melhoria) Opcao de debounce quando ha muitas linhas. (fonte: comunicacao_chat_inbox.md)
28) [x] [P3] (Problema) Auto-open depende do sistema (xdg-open/open/cmd) e pode falhar silenciosamente. (fonte: comunicacao_chat_log.md)
29) [x] [P3] (Problema) Formato nao e JSONL estrito (linha com texto + meta). (fonte: comunicacao_chat_log.md)
30) [x] [P3] (Melhoria) Adicionar teste unitario para `validar_mensagem`. (fonte: comunicacao_protocolo.md)
31) [x] [P3] (Problema) Nao ha versionamento de mensagens. (fonte: comunicacao_protocolo.md)
32) [x] [P3] (Problema) Validacao e minima (apenas campos obrigatorios). (fonte: comunicacao_protocolo.md)
33) [x] [P3] (Melhoria) Exibir um resumo claro de deps faltantes no modo voz-loop. (fonte: entrada_app.md)
34) [x] [P3] (Melhoria) Permitir `--voice-loop-sleep` via CLI (hoje usa delay fixo no loop). (fonte: entrada_app.md)
35) [x] [P3] (Problema) Loop de voz usa sleep fixo de 0.5s; nao e configuravel por CLI. (fonte: entrada_app.md)
36) [x] [P3] (Problema) Nao expone configuracao de device/SR por CLI; depende de env do STT. (fonte: entrada_app.md)
37) [x] [P3] (Melhoria) Adicionar testes para faixas de int16 invalidas (ja valida, mas sem teste dedicado). (fonte: entrada_audio_utils.md)
38) [x] [P3] (Melhoria) Scroll virtual com mais performance para logs grandes. (fonte: entrada_chat_ui.md)
39) [x] [P3] (Problema) Polling (sem websocket) pode atrasar atualizacoes. (fonte: entrada_chat_ui.md)
40) [x] [P3] (Melhoria) Expor estado ativo para UI (ex: indicador visual do microfone). (fonte: entrada_followup.md)
41) [x] [P3] (Problema) Nao tem indicador visual do estado ativo. (fonte: entrada_followup.md)
42) [x] [P3] (Melhoria) Indicador real de microfone (ligado/desligado) baseado no config. (fonte: entrada_gui_panel.md)
43) [x] [P3] (Problema) Botao de microfone e apenas indicador; nao altera STT real. (fonte: entrada_gui_panel.md)
44) [x] [P3] (Melhoria) Separar checks por perfil (voz/UI/desktop) para reduzir ruido. (fonte: entrada_preflight.md)
45) [x] [P3] (Problema) Deteccao de headless e heuristica; pode errar em ambientes atipicos. (fonte: entrada_preflight.md)
46) [x] [P3] (Melhoria) Padronizar `chat_shortcut_combo` via env/config (hoje e opcional). (fonte: entrada_shortcut.md)
47) [x] [P3] (Problema) Depende de pynput; se ausente, nao ativa. (fonte: entrada_shortcut.md)
48) [x] [P3] (Melhoria) Metrics de duracao por etapa (captura, VAD, transcricao). (fonte: entrada_stt.md)
49) [x] [P3] (Melhoria) Adicionar typing mais estrito (ex: Literal para sample_rate esperado). (fonte: voz_adapters_base.md)
50) [x] [P3] (Problema) Nao ha enforce de sample_rate/formatos. (fonte: voz_adapters_base.md)
51) [x] [P3] (Problema) Protocols nao fazem validacao em runtime. (fonte: voz_adapters_base.md)
52) [x] [P3] (Melhoria) Cache de voiceprint em memoria para reduzir IO. (fonte: voz_adapters_speaker_resemblyzer.md)
53) [x] [P3] (Problema) Nao ha cache de voiceprint; pode reler arquivo sempre. (fonte: voz_adapters_speaker_resemblyzer.md)
54) [x] [P3] (Problema) `verify` ignora sample_rate; usa o audio como esta. (fonte: voz_adapters_speaker_resemblyzer.md)
55) [x] [P3] (Melhoria) Implementar detector real por audio quando houver lib. (fonte: voz_adapters_wakeword_text.md)
56) [x] [P3] (Problema) Depende do texto ja transcrito para filtrar. (fonte: voz_adapters_wakeword_text.md)
57) [x] [P3] (Problema) `detect()` sempre retorna False; nao detecta wake word em audio. (fonte: voz_adapters_wakeword_text.md)
58) [x] [P3] (Melhoria) Adicionar confirmacao explicita no cadastro de voz (UX guiada + confirmacao). (fonte: voz_speaker_verify.md)
59) [x] [P3] (Melhoria) Log opcional quando Piper falha e cai para espeak. (fonte: voz_tts.md)
60) [x] [P3] (Problema) Sem controle de volume/ganho. (fonte: voz_tts.md)
61) [x] [P3] (Melhoria) Expor metricas de frames processados e duracao. (fonte: voz_vad.md)
62) [x] [P3] (Problema) StreamingVAD nao expone escolha de device. (fonte: voz_vad.md)
63) [x] [P3] (Problema) Nao mede GPU de forma direta. (fonte: benchmark_interface.md)
64) [x] [P3] (Problema) Nao faz reamostragem automatica quando o audio nao e 16 kHz. (fonte: benchmark_interface.md)
65) [x] [P3] (Melhoria) Adicionar opcao de reamostragem usando `scipy` quando necessario. (fonte: benchmark_interface.md)
66) [x] [P3] (Melhoria) Integrar coleta de CPU/RAM via `psutil`. (fonte: benchmark_interface.md)
67) [x] [P3] (Problema) AEC real (echo) ainda nao existe; precisa referencia de playback. (fonte: entrada_stt.md, voz_vad.md)
68) [x] [P3] (Melhoria) Preflight/diagnostico deve avisar quando `JARVIS_WAKE_WORD_AUDIO=1` e `pvporcupine` nao esta instalado. (fonte: voz_adapters_wakeword_porcupine.md)
69) [x] [P1] (Problema) Import do `sounddevice` trava no ambiente; corrigir backend de audio (PortAudio/ALSA) para liberar captura e benchmark sem stub. (fonte: benchmark_interface.md)
70) [x] [P3] (Melhoria) Preflight deve mostrar device e sample_rate usados no probe de audio. (fonte: entrada_preflight.md)
71) [x] [P3] (Melhoria) Chat UI: destacar erros/roles com cores para leitura mais clara. (fonte: entrada_chat_ui.md)
72) [x] [P3] (Melhoria) Painel GUI: tornar o polling do follow-up configuravel (env/CLI). (fonte: entrada_gui_panel.md)
73) [x] [P3] (Melhoria) Atalho: ler `JARVIS_CHAT_SHORTCUT_COMBO` direto no modulo (sem depender de config). (fonte: entrada_shortcut.md)
74) [x] [P3] (Problema) Toggle do microfone pode falhar se o Config nao puder ser clonado; criar fallback ou erro mais claro. (fonte: entrada_gui_panel.md)
75) [x] [P2] (Problema) Quando o trim Rust confirma fala, a rechecagem por VAD podia bloquear audio curto. (fonte: entrada_stt.md)
76) [x] [P3] (Melhoria) Testes STT limpam env `JARVIS_AUDIO_*` para evitar interferencia entre suites. (fonte: test_stt_flow.py, test_stt_rust_trim.py)
77) [ ] [P3] (Problema) Latencia perceptivel no comando de voz manual; medir STT/TTS e reduzir tempo de resposta. (fonte: TESTE_MANUAL.md)
78) [ ] [P2] (Problema) Wake word exigida: comando com "jarvis" nao foi reconhecido em teste real (sem resposta). Investigar VAD, limiar de audio e microfone. (fonte: TESTE_MANUAL.md)
79) [x] [P3] (Melhoria) Debounce entre gravacoes de voz via `JARVIS_STT_MIN_GAP_SECONDS`. (fonte: repositorios_interface.md)
80) [x] [P3] (Melhoria) Limite opcional de latencia da transcricao (`JARVIS_STT_ALLOWED_LATENCY_MS`). (fonte: repositorios_interface.md)
81) [x] [P3] (Melhoria) Normalizacao opcional do audio antes do STT (`JARVIS_STT_NORMALIZE_AUDIO`). (fonte: repositorios_interface.md)
82) [x] [P3] (Melhoria) Ajustes de VAD por env (silence/pre/post-roll) para endpointing. (fonte: repositorios_interface.md)
83) [x] [P3] (Melhoria) Limite maximo do StreamingVAD por env (`JARVIS_VAD_MAX_SECONDS`). (fonte: repositorios_interface.md)
84) [x] [P3] (Melhoria) Warmup opcional do Whisper para reduzir primeira latencia. (fonte: repositorios_interface.md)
85) [x] [P3] (Melhoria) Parametros do Whisper via env (beam/best/temperatura/prompt/suppress). (fonte: repositorios_interface.md)
86) [x] [P3] (Melhoria) VAD filter do Whisper via env (`JARVIS_WHISPER_VAD_FILTER`). (fonte: repositorios_interface.md)
87) [x] [P3] (Problema) `test_stt_vad_env` falhava quando `JARVIS_AUDIO_DEVICE` vinha do ambiente; teste agora limpa esse env. (fonte: testes/test_stt_vad_env.py)

## Garantias atuais (wake word + follow-up)
- Wake word so e exigida quando `JARVIS_REQUIRE_WAKE_WORD=1` **e** a janela de follow-up nao esta ativa.
- Depois de um comando aceito, a janela de follow-up permite falar sem dizer "jarvis" por `JARVIS_FOLLOWUP_SECONDS` e ate `JARVIS_FOLLOWUP_MAX_COMMANDS`.
- Se o comando falhar, se houver silencio, ou se a verificacao de locutor falhar, o follow-up reseta e volta a exigir wake word.
- Se `JARVIS_WAKE_WORD_AUDIO=1`, o STT tenta detectar a wake word no **audio** antes de transcrever (Porcupine opcional).
- Testes que garantem isso:
  - `testes/test_followup_mode.py` (follow-up exige/dispensa wake word por tempo/limite).
  - `testes/test_stt_filters.py` (filtro de wake word no texto).
  - `testes/test_stt_flow.py::test_transcribe_with_vad_blocks_without_audio_wake` (bloqueio por audio).

## Pendencias reais (transparencia)
- AEC real (eco) ainda nao existe; depende de um pipeline com referencia de playback.
- Wake word por audio depende de lib opcional (Porcupine); sem ela, o filtro continua sendo por texto.
- Speaker verify agora falha em audio curto para evitar falso positivo; comandos curtos podem exigir falar um pouco mais.

## Registro de correcoes
- Item 1 (P1): adicionado `scipy` em `check_stt_deps` e preflight agora avisa quando falta. Resultado: falha de reamostragem deixa de ser silenciosa e o usuario ve o aviso antes de usar voz.
- Item 2 (P2): `ChatInbox` agora persiste o cursor em arquivo `.cursor`, evitando reprocessar comandos apos reinicio.
- Item 3 (P2): escrita no inbox usa `append_line` com lock consultivo; leitura usa lock compartilhado quando disponivel. Resultado: reduz risco de intercalacao entre escritores que usam o helper.
- Item 12 (P2): preflight verifica se ha modelo Piper e emite WARN quando falta, mesmo com piper instalado.
- Item 15 (P2): `transcribe_with_vad` bloqueia streaming quando capture_sr != 16 kHz, com teste dedicado.
- Itens 4/5 (P2): log agora rotaciona por tamanho com backups configuraveis por env.
- Item 7 (P2): listas de int agora sempre viram int16 (nao bytes crus), evitando mascarar erro de payload.
- Item 8 (P2): validacao de alinhamento int16 (tamanho par) para bytes/frames em `coerce_pcm_bytes`.
- Item 6 (P2): voice-loop revalida deps de STT e encerra se faltar dependencias.
- Item 9 (P2): Chat UI escreve no inbox usando `append_line` com lock consultivo.
- Item 13 (P2): preflight ganhou probe opcional de captura/TTS via `JARVIS_PREFLIGHT_PROBE`, com WARN se a captura/fala falhar.
- Item 18 (P2): fallback de `check_speech_present` usa limiar de pico quando nao ha VAD/Rust, reduzindo ruido.
- Item 21 (P2): speaker_verify agora reamostra audio para 16 kHz quando necessario.
- Item 54 (P3): adapter passa `sample_rate` para o speaker_verify (nao ignora mais).
- Item 23 (P2): TTS loga falhas de subprocesso quando `JARVIS_DEBUG=1`.
- Item 30 (P3): adicionado teste unitario para `validar_mensagem`.
- Item 33 (P3): _ensure_stt_ready lista deps ausentes e sugere pip install no voice-loop.
- Itens 79-81 (P3): STT ganhou debounce entre gravacoes, limite opcional de latencia e normalizacao de audio antes da transcricao (todos via env).
- Itens 82-83 (P3): StreamingVAD agora aceita ajuste de silencio/pre/post-roll e limite maximo via env.
- Itens 84-86 (P3): Whisper ganhou warmup opcional e parametros configuraveis (beam/best/temperatura/prompt/suppress + vad_filter).
- Item 37 (P3): adicionados testes de limites int16 (abaixo/acima e limites validos).
- Item 99 (P3): removida duplicacao de `py-spy` no doc de dependencias (limpeza).
- Itens 34/35 (P3): voice-loop agora aceita `--voice-loop-sleep` e nao usa delay fixo.
- Item 36 (P3): CLI aceita `--audio-device` e `--audio-capture-sr` para override de device/SR.
- Item 20 (P2): audio curto agora falha a verificacao de locutor; evita falso positivo e força fala minima via `JARVIS_SPK_MIN_AUDIO_MS`. Resultado: comandos curtos nao passam sem validar voz.
- Item 69 (P1): `sounddevice` passou a ser importado de forma lazy; benchmark em WAV nao trava, e docs agora descrevem dependencias de PortAudio/ALSA. Resultado: ferramentas de benchmark rodam mesmo sem backend de audio.
- Item 58 (P3): cadastro de voz agora pede confirmacao explicita no orquestrador antes de salvar o voiceprint. Resultado: evita salvar voiceprint errado por engano.
- Item 59 (P3): TTS loga fallback para espeak quando Piper nao atende.
- Item 46 (P3): env `JARVIS_CHAT_SHORTCUT_COMBO` define o combo quando config nao existe.
- Item 28 (P3): chat_log agora loga falha de auto-open em debug.
- Item 32 (P3): validar_mensagem agora valida tipos e payload dict.
- Item 27 (P3): chat_inbox limita linhas por drain via `JARVIS_CHAT_INBOX_MAX_LINES`.
- Item 29 (P3): chat_log agora grava JSONL estrito e a UI interpreta o formato.
- Item 31 (P3): protocolo agora exige `version` nas mensagens e valida o campo; mensagens criadas saem com `PROTO_VERSION`.
- Item 38 (P3): chat_ui passou a ler o log em blocos para pegar o tail sem carregar o arquivo inteiro.
- Itens 52/53 (P3): voiceprint agora usa cache em memoria e evita releitura do arquivo a cada verificacao.
- Item 11 (P2): painel agora pode alternar o STOP para cancelar comandos em execucao.
- Item 10 (P2): follow-up agora e limitado por tempo e por quantidade de comandos (env `JARVIS_FOLLOWUP_MAX_COMMANDS`).
- Item 24 (P2): TTS agora serializa chamadas com lock interno para evitar sobreposicao.
- Item 62 (P3): StreamingVAD agora aceita device e o STT repassa `JARVIS_AUDIO_DEVICE`.
- Itens 50/51 (P3): adicionada validacao de audio e sample_rate nos adapters (helper `validate_audio_i16`).
- Item 44 (P3): preflight agora suporta perfil por voz/UI/desktop via env/CLI para reduzir ruido.
- Item 45 (P3): heuristica de headless agora considera XDG_SESSION_TYPE e CI para reduzir falsos positivos.
- Item 48 (P3): STT agora loga duracoes de captura/transcricao via `JARVIS_STT_METRICS=1`.
- Item 49 (P3): adapters agora expõem `SampleRate=Literal[16000]` para indicar o SR esperado.
- Item 61 (P3): VAD agora loga frames/duracao via `JARVIS_VAD_METRICS=1`.
- Item 14 (P2): atalho agora retorna `last_error` e o app mostra dica especifica para Wayland sem X11/pynput ausente.
- Item 39 (P3): chat_ui usa watchdog quando disponivel e cai para polling quando nao ha suporte.
- Item 22 (P2): voiceprint agora pode ser criptografado via `JARVIS_SPK_VOICEPRINT_PASSPHRASE` (com `cryptography` opcional).
- Itens 40/41 (P3): gui_panel agora exibe estado de follow-up (ativo/inativo).
- Itens 42/43 (P3): botao de microfone alterna `stt_mode` (local/none) e o texto reflete o estado real do STT.
- Item 26 (P2): VAD agora aceita `JARVIS_VAD_AGGRESSIVENESS` (0..3) para ajustar sensibilidade a voz baixa/ruido.
- Itens 16/19/25 (P2): adicionado pre-processamento opcional (NS/AGC leve) antes do VAD via env; AEC real segue pendente.
- Item 60 (P3): TTS agora aceita `JARVIS_TTS_VOLUME` para ajustar o volume (Piper + espeak).
- Itens 64/65 (P3): benchmark agora suporta `--resample` com `scipy` para WAVs fora de 16 kHz.
- Item 66 (P3): benchmark agora inclui CPU/RAM por processo quando `psutil` esta disponivel.
- Item 63 (P3): benchmark agora coleta GPU via `nvidia-smi` com `--gpu`.
- Item 47 (P3): atalho agora tem fallback por arquivo via `JARVIS_CHAT_SHORTCUT_FILE`.
- Itens 55/56/57 (P3): adicionado detector de wake word por audio via Porcupine (opcional) e STT passa a bloquear antes da transcricao quando `JARVIS_WAKE_WORD_AUDIO=1`.
- Item 68 (P3): preflight agora emite WARN quando wake word por audio esta ativo e `pvporcupine` nao esta instalado.
- Item 70 (P3): preflight passou a incluir device e sample_rate no probe de audio.
- Item 17 (P2): `transcribe_once` agora bloqueia streaming quando `JARVIS_AUDIO_DEVICE` esta definido ou o capture_sr != 16 kHz.
- Item 72 (P3): painel GUI agora aceita `JARVIS_GUI_FOLLOWUP_POLL_MS` e `--gui-followup-poll-ms` para ajustar o polling do follow-up.
- Item 73 (P3): `ChatShortcut` passou a ler `JARVIS_CHAT_SHORTCUT_COMBO` direto no modulo quando nenhum combo e fornecido.
- Item 71 (P3): chat_ui aplica cores por role/erro usando tags do Tkinter para leitura mais clara.
- Item 74 (P3): painel GUI tenta atualizar `stt_mode` no config atual quando nao consegue clonar e mostra erro claro se falhar.
- Item 67 (P3): AEC simples (com referencia de playback) foi adicionado no VAD/STT; TTS Piper alimenta o buffer de playback.
- Item 75 (P2): quando o trim Rust detecta fala, o STT agora pula a rechecagem de VAD para evitar falso negativo em audio curto.
- Item 76 (P3): testes de STT agora limpam `JARVIS_AUDIO_*` antes de rodar, evitando interferencia entre arquivos de teste.
- Item 87 (P3): `test_stt_vad_env` passou a limpar `JARVIS_AUDIO_DEVICE`/`JARVIS_AUDIO_CAPTURE_SR`, evitando falhas em ambientes com device fixo.
