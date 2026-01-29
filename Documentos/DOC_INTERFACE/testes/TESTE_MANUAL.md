# Teste manual da interface (entrada/saida)

Roteiro rápido para validar a interface de voz/UI sem depender do cérebro/automação.

Antes de começar:
1) `cd /home/u/Documentos/Jarvis`
2) Ative o venv: `source .venv/bin/activate`
3) Feche apps que usam o microfone e ajuste volumes.

Formato de cada teste: comando → sinal para falar/agir → frase/ação → resultado esperado. Use `Ctrl+C` para sair do voice-loop.

1) Preflight de voz (saúde básica)  
`PYTHONPATH=. python -m jarvis.interface.entrada.app --preflight --preflight-profile voice`  
Resultado: relatório OK/OK+WARN; sem FAIL para mic/voz.

2) Benchmark automático (voz real, silêncio + ruído)  
`PYTHONPATH=. python scripts/auto_voice_bench.py --device <idx> --with-noise --output-dir Documentos/DOC_INTERFACE/bench_audio --phrase "oi jarvis teste automatico" --seconds 4`  
Resultado: JSONs criados em `bench_audio/` e mensagem de sucesso.

3) Voz única (captura + STT + TTS)  
`PYTHONPATH=. python -m jarvis.interface.entrada.app --voice`  
Fale: “jarvis, oi”. Esperado: texto transcrito e resposta falada.

4) Wake word obrigatória  
`JARVIS_REQUIRE_WAKE_WORD=1 PYTHONPATH=. python -m jarvis.interface.entrada.app --voice`  
- Fale “abrir navegador” → não deve agir.  
- Fale “jarvis, abrir navegador” → deve transcrever/responder.

5) STT streaming (RealtimeSTT)  
`JARVIS_STT_STREAMING=1 JARVIS_STT_STREAMING_BACKEND=realtimestt JARVIS_STT_STREAMING_FORCE_START=1 JARVIS_REQUIRE_WAKE_WORD=0 PYTHONPATH=. python -m jarvis.interface.entrada.app --voice`  
Fale “oi”. Esperado: transcrição e resposta. Se `bytes=0`, gate de áudio falhou.

6) Follow-up (sem repetir wake word)  
`JARVIS_REQUIRE_WAKE_WORD=1 PYTHONPATH=. python -m jarvis.interface.entrada.app --voice-loop`  
Fale “jarvis, status” e depois “status”. Esperado: segunda frase aceita.

7) Interface de texto (chat_ui)  
`PYTHONPATH=. python -m jarvis.interface.entrada.app --chat-ui`  
Digite uma mensagem; esperado: aparece no log/inbox sem erro.

8) Painel flutuante (gui_panel)  
`PYTHONPATH=. python -m jarvis.interface.entrada.app --gui-panel`  
Digite comando simples; esperado: envia ao Jarvis sem travar.

9) Atalho global do chat (Wayland/X11)  
`PYTHONPATH=. python -m jarvis.interface.entrada.app --enable-shortcut --voice-loop`  
Pressione Ctrl+Shift+J; esperado: abre chat UI (ou aviso de Wayland sem X11).

10) Wake word por áudio (Porcupine)  
`JARVIS_WAKE_WORD_AUDIO=1 JARVIS_PORCUPINE_ACCESS_KEY=<token> PYTHONPATH=. python -m jarvis.interface.entrada.app --voice-loop`  
Fale “jarvis”, depois “abrir navegador”; só deve aceitar após wake word no áudio.

11) Speaker verification (voz autorizada e não autorizada)  
`JARVIS_SPK_VERIFY=1 PYTHONPATH=. python -m jarvis.interface.entrada.app --voice-loop`  
- Cadastro: “cadastrar voz” (~10s) e “jarvis, status” (deve aceitar).  
- Outra pessoa: “jarvis, status” (deve ignorar).

12) Device e reamostragem (44.1k/48k)  
`JARVIS_AUDIO_DEVICE=<idx> JARVIS_AUDIO_CAPTURE_SR=44100 PYTHONPATH=. python -m jarvis.interface.entrada.app --voice`  
Fale “jarvis, oi”; esperado: sem erro de sample rate e transcreve.

Se algum teste falhar, registre em `Documentos/DOC_INTERFACE/CORRECOES_DOCINTERFACE.MD` com comando, ambiente e erro.
