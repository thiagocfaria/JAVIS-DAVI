# Teste manual da interface (entrada/saida)

Este roteiro foca somente na interface de entrada/saida (voz + UI). Ele nao avalia o "cerebro" nem a automacao. Pense assim: estamos testando se o ouvido (entrada) e a boca (saida) estao funcionando direitinho.

Antes de comecar:
1) Abra o terminal na raiz do projeto (`/home/u/Documentos/Jarvis`).
2) Use o venv: `source .venv/bin/activate` (se nao usar venv, troque por `python` nos comandos).
3) Feche apps que usam o microfone.
4) Ajuste o volume do microfone e do alto-falante.

Formato de cada teste:
- Comando: o que voce deve rodar (copiar/colar).
- Sinal para falar: o que aparece no terminal para voce comecar a falar.
- O que falar: a frase exata.
- Tempo de fala: por quanto tempo falar (se importar).
- Resultado esperado: o que tem que acontecer para passar.

1) P1 - Preflight de voz (saude basica)
Comando: `PYTHONPATH=. ./.venv/bin/python -m jarvis.app --preflight --preflight-profile voice`
Sinal para falar: nao precisa falar.
O que falar: nada.
Tempo de fala: 0s.
Resultado esperado: relatorio com status OK/OK+WARN. Se aparecer "FAIL" para microfone/voz, este teste falha.
Status: OK (2026-01-10)

2) P1 - Voz unica (captura + STT + TTS)
Comando: `PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice`
Sinal para falar: assim que o comando rodar (nao precisa esperar mensagem).
O que falar: "jarvis, oi".
Tempo de fala: 2 a 4s.
Resultado esperado: aparece uma resposta no terminal e voce ouve a resposta falada (TTS). Sem erro no terminal.
Status: OK parcial (2026-01-10)
Observacao: respondeu, mas demorou mais que o esperado. Provavel causa fora da interface pura (latencia de STT/TTS/LLM ou carga do sistema). Medir em `Documentos/DOC_INTERFACE/EVOLUCAO_PERFOMACE.MD` usando `scripts/bench_interface.py` e registrar para correcao futura em `Documentos/DOC_INTERFACE/CORRECOES_DOCINTERFACE.MD`.

3) P1 - Wake word obrigatoria (nao ouvir sem "jarvis")
Comando: `JARVIS_REQUIRE_WAKE_WORD=1 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice`
Sinal para falar: assim que o comando rodar.
O que falar: "abrir navegador" (sem dizer jarvis).
Tempo de fala: 2 a 4s.
Resultado esperado: nenhum comando e aceito; nao deve aparecer resposta falada.
Status: OK (2026-01-10)

4) P1 - Wake word obrigatoria (ouvir com "jarvis")
Comando: `JARVIS_REQUIRE_WAKE_WORD=1 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice`
Sinal para falar: assim que o comando rodar.
O que falar: "jarvis, abrir navegador".
Tempo de fala: 2 a 4s.
Resultado esperado: deve transcrever e responder. O foco aqui e apenas ouvir e transcrever, nao importa a acao final.
Status: FALHOU (2026-01-10) - sem resposta; TV ligada pode ter atrapalhado o VAD/ruido.
Status: FALHOU (2026-01-10) - sem resposta mesmo com TV desligada.

5) P1 - Follow-up (continuar sem repetir wake word)
Comando: `JARVIS_REQUIRE_WAKE_WORD=1 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice-loop`
Sinal para falar: quando aparecer "Jarvis MVP - voice loop (Ctrl+C para sair)".
O que falar: primeiro "jarvis, status". Em seguida (em ate 20s) diga "status" sem jarvis.
Tempo de fala: 2 a 4s por frase.
Resultado esperado: a segunda frase tambem e aceita (porque o follow-up esta ativo). Se a segunda nao funcionar, falhou.

6) P2 - Interface de texto (chat_ui)
Comando: `PYTHONPATH=. ./.venv/bin/python -m jarvis.app --chat-ui`
Sinal para falar: nao precisa falar.
O que fazer: digitar uma mensagem no campo da janela e enviar.
Tempo: livre.
Resultado esperado: a mensagem aparece no log/inbox sem erro.

7) P2 - Painel flutuante (gui_panel)
Comando: `PYTHONPATH=. ./.venv/bin/python -m jarvis.app --gui-panel`
Sinal para falar: nao precisa falar.
O que fazer: digitar um comando simples e enviar.
Tempo: livre.
Resultado esperado: o painel envia o texto para o Jarvis (sem travar).

8) P2 - Atalho global do chat (Wayland/X11)
Comando: `PYTHONPATH=. ./.venv/bin/python -m jarvis.app --enable-shortcut --voice-loop`
Sinal para falar: quando aparecer "Atalho global ativado: ctrl+shift+j ..." ou aviso de Wayland.
O que fazer: pressione Ctrl+Shift+J.
Tempo: 1s.
Resultado esperado: a janela do chat abre. Se aparecer aviso de Wayland sem X11, este teste fica como "nao aplicavel".

9) P2 - Wake word por audio (Porcupine)
Comando: `JARVIS_WAKE_WORD_AUDIO=1 JARVIS_PORCUPINE_ACCESS_KEY=SEU_TOKEN PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice-loop`
Sinal para falar: quando aparecer "Jarvis MVP - voice loop (Ctrl+C para sair)".
O que falar: diga apenas "jarvis" e depois espere 1s. Depois diga "abrir navegador".
Tempo de fala: 1 a 3s.
Resultado esperado: o sistema so aceita o comando depois de ouvir a wake word no audio.

10) P2 - Speaker verification (voz autorizada)
Comando: `JARVIS_SPK_VERIFY=1 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice-loop`
Sinal para falar: quando aparecer "Jarvis MVP - voice loop (Ctrl+C para sair)".
O que falar: diga "cadastrar voz" e fale por ~10s. Depois diga "jarvis, status".
Tempo de fala: 10s no cadastro, 2 a 4s no comando.
Resultado esperado: cadastro confirmado, e depois o comando e aceito para a mesma voz.

11) P2 - Speaker verification (voz nao autorizada)
Comando: `JARVIS_SPK_VERIFY=1 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice-loop`
Sinal para falar: quando aparecer "Jarvis MVP - voice loop (Ctrl+C para sair)".
O que falar: uma outra pessoa tenta falar "jarvis, status".
Tempo de fala: 2 a 4s.
Resultado esperado: o comando deve ser ignorado (sem resposta).

12) P3 - Device e reamostragem (microfone 44.1k/48k)
Comando: `JARVIS_AUDIO_DEVICE=3 JARVIS_AUDIO_CAPTURE_SR=44100 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice`
Sinal para falar: assim que o comando rodar.
O que falar: "jarvis, oi".
Tempo de fala: 2 a 4s.
Resultado esperado: nao deve dar erro de sample rate e a fala deve ser entendida.

Como encerrar:
Para sair do voice-loop, use Ctrl+C.

Se algum teste falhar:
Anote o problema em `Documentos/DOC_INTERFACE/CORRECOES_DOCINTERFACE.MD` e descreva o erro.
