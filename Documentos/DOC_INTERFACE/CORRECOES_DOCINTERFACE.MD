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
14) [ ] [P2] (Problema) Em Wayland sem X11, atalho global nao funciona. (fonte: entrada_shortcut.md)
15) [x] [P2] (Melhoria) Bloquear streaming quando capture_sr != 16k para evitar inconsistencias. (fonte: entrada_stt.md)
16) [ ] [P2] (Melhoria) Opcao de AEC/NS/AGC antes do VAD. (fonte: entrada_stt.md)
17) [x] [P2] (Problema) Em `transcribe_once`, streaming pode rodar com capture_sr != 16k (comportamento atual). (fonte: entrada_stt.md)
18) [x] [P2] (Problema) Se VAD/Rust nao estiverem disponiveis, `check_speech_present` pode aceitar ruido. (fonte: entrada_stt.md)
19) [ ] [P2] (Problema) Sem AEC/NS/AGC; ruido ambiente pode virar texto. (fonte: entrada_stt.md)
20) [x] [P2] (Problema) Audio curto pode gerar falso negativo. (fonte: voz_speaker_verify.md)
21) [x] [P2] (Problema) Nao reamostra audio; espera 16 kHz. (fonte: voz_speaker_verify.md)
22) [ ] [P2] (Problema) Voiceprint e salvo em JSON simples (sem criptografia). (fonte: voz_speaker_verify.md)
23) [x] [P2] (Problema) Falhas de subprocesso sao silenciosas. (fonte: voz_tts.md)
24) [x] [P2] (Problema) Sem fila/queue; chamadas simultaneas podem sobrepor audio. (fonte: voz_tts.md)
25) [ ] [P2] (Problema) Nao ha AEC/NS/AGC antes do VAD. (fonte: voz_vad.md)
26) [ ] [P2] (Problema) webrtcvad pode errar com voz baixa/ruido. (fonte: voz_vad.md)
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
39) [ ] [P3] (Problema) Polling (sem websocket) pode atrasar atualizacoes. (fonte: entrada_chat_ui.md)
40) [ ] [P3] (Melhoria) Expor estado ativo para UI (ex: indicador visual do microfone). (fonte: entrada_followup.md)
41) [ ] [P3] (Problema) Nao tem indicador visual do estado ativo. (fonte: entrada_followup.md)
42) [ ] [P3] (Melhoria) Indicador real de microfone (ligado/desligado) baseado no config. (fonte: entrada_gui_panel.md)
43) [ ] [P3] (Problema) Botao de microfone e apenas indicador; nao altera STT real. (fonte: entrada_gui_panel.md)
44) [ ] [P3] (Melhoria) Separar checks por perfil (voz/UI/desktop) para reduzir ruido. (fonte: entrada_preflight.md)
45) [ ] [P3] (Problema) Deteccao de headless e heuristica; pode errar em ambientes atipicos. (fonte: entrada_preflight.md)
46) [x] [P3] (Melhoria) Padronizar `chat_shortcut_combo` via env/config (hoje e opcional). (fonte: entrada_shortcut.md)
47) [ ] [P3] (Problema) Depende de pynput; se ausente, nao ativa. (fonte: entrada_shortcut.md)
48) [ ] [P3] (Melhoria) Metrics de duracao por etapa (captura, VAD, transcricao). (fonte: entrada_stt.md)
49) [ ] [P3] (Melhoria) Adicionar typing mais estrito (ex: Literal para sample_rate esperado). (fonte: voz_adapters_base.md)
50) [ ] [P3] (Problema) Nao ha enforce de sample_rate/formatos. (fonte: voz_adapters_base.md)
51) [ ] [P3] (Problema) Protocols nao fazem validacao em runtime. (fonte: voz_adapters_base.md)
52) [x] [P3] (Melhoria) Cache de voiceprint em memoria para reduzir IO. (fonte: voz_adapters_speaker_resemblyzer.md)
53) [x] [P3] (Problema) Nao ha cache de voiceprint; pode reler arquivo sempre. (fonte: voz_adapters_speaker_resemblyzer.md)
54) [x] [P3] (Problema) `verify` ignora sample_rate; usa o audio como esta. (fonte: voz_adapters_speaker_resemblyzer.md)
55) [ ] [P3] (Melhoria) Implementar detector real por audio quando houver lib. (fonte: voz_adapters_wakeword_text.md)
56) [ ] [P3] (Problema) Depende do texto ja transcrito para filtrar. (fonte: voz_adapters_wakeword_text.md)
57) [ ] [P3] (Problema) `detect()` sempre retorna False; nao detecta wake word em audio. (fonte: voz_adapters_wakeword_text.md)
58) [ ] [P3] (Melhoria) Explicar UX para cadastro (mensagem guiada + confirmacao). (fonte: voz_speaker_verify.md)
59) [x] [P3] (Melhoria) Log opcional quando Piper falha e cai para espeak. (fonte: voz_tts.md)
60) [ ] [P3] (Problema) Sem controle de volume/ganho. (fonte: voz_tts.md)
61) [ ] [P3] (Melhoria) Expor metricas de frames processados e duracao. (fonte: voz_vad.md)
62) [ ] [P3] (Problema) StreamingVAD nao expone escolha de device. (fonte: voz_vad.md)
63) [ ] [P3] (Problema) Nao mede GPU de forma direta. (fonte: benchmark_interface.md)
64) [ ] [P3] (Problema) Nao faz reamostragem automatica quando o audio nao e 16 kHz. (fonte: benchmark_interface.md)
65) [ ] [P3] (Melhoria) Adicionar opcao de reamostragem usando `scipy` quando necessario. (fonte: benchmark_interface.md)
66) [ ] [P3] (Melhoria) Integrar coleta de CPU/RAM via `psutil`. (fonte: benchmark_interface.md)

## Registro de correcoes
- Item 1 (P1): adicionado `scipy` em `check_stt_deps` e preflight agora avisa quando falta. Resultado: falha de reamostragem deixa de ser silenciosa e o usuario ve o aviso antes de usar voz.
- Item 2 (P2): `ChatInbox` agora persiste o cursor em arquivo `.cursor`, evitando reprocessar comandos apos reinicio.
- Item 3 (P2): escrita no inbox usa `append_line` com lock consultivo; leitura usa lock compartilhado quando disponivel. Resultado: reduz risco de intercalacao entre escritores que usam o helper.
- Item 12 (P2): preflight verifica se ha modelo Piper e emite WARN quando falta, mesmo com piper instalado.
- Itens 15/17 (P2): garantimos bypass do streaming quando capture_sr != 16 kHz (inclui `transcribe_once`), com teste dedicado.
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
- Item 37 (P3): adicionados testes de limites int16 (abaixo/acima e limites validos).
- Item 99 (P3): removida duplicacao de `py-spy` no doc de dependencias (limpeza).
- Item 20 (P2): verificador de voz ignora audio curto com log debug para evitar falso negativo.
- Itens 34/35 (P3): voice-loop agora aceita `--voice-loop-sleep` e nao usa delay fixo.
- Item 36 (P3): CLI aceita `--audio-device` e `--audio-capture-sr` para override de device/SR.
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
