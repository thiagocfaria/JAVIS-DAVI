# JAVIS-DAVI (Jarvis MVP - self-hosted)

A ideia e que ele seja um orquestrador capaz de fazer tudo em um computador, mexendo mouse e teclado.

Jarvis vive na sua maquina e no VPS que voce controla. Nao usamos API paga ou gratuita externa: o cerebro e um modelo open-source (Qwen2.5-7B-Instruct + LoRA) que voce organiza por conta propria. Este repositorio mantem o orquestrador python, a validacao local e o plano que descreve como quantizar, treinar incrementalmente e aplicar LoRA sem depender de terceiros.

## Status rapido
- Testes unitarios atuais: `python -m pytest -q` (28/28 passando).
- Projeto **nao terminou**: faltam portal Wayland + ponte Rust para acoes, deploy do VPS com modelo self-hosted, memoria remota robusta e telemetria de custo (detalhado em `Documentos/PLANO_UNICO.md`).
- Orquestrador agora aplica limite diario de chamadas/caracteres do cerebro via `JARVIS_BUDGET_MAX_CALLS`/`JARVIS_BUDGET_MAX_CHARS` (registra blocos/consumo em `~/.jarvis/events.jsonl`).
- Ponte de memoria remota adicionada: configure `JARVIS_REMOTE_MEMORY_URL`/`JARVIS_REMOTE_MEMORY_TOKEN` para enviar e consultar memórias num serviço HTTP leve (fallback local quando indisponível).
 - Para subir rapidamente o serviço de memória remota, use `./scripts/start_remote_memory_server.sh --host 0.0.0.0 --port 8000` (wrapper para `python -m jarvis.memoria.remote_service`).

## O que ja funciona hoje
- CLI de texto/voz (`python3 -m jarvis.app --loop`, `--text`, `--voice`).
 - Painel flutuante (`python3 -m jarvis.app --gui-panel`) abre uma janela suspensa com campo de texto e botao de envio; os comandos ainda usam o mesmo orquestrador e gravam os eventos em `~/.jarvis/events.jsonl`.
- Orquestrador local com policy, aprovacao, execucao e validacao.
- Procedimentos validados + gate de confianca + MockLLM fallback.
- Entrada/saida local (STT local, TTS local, chat UI, teclado/atalho).
- Automacao desktop/web (xdotool/wtype/Playwright), memoria local (SQLite + embeddings opcionais) e telemetria simples.
- Agent S3 integrado como motor de GUI (loop visual + grounding) com execucao segura via policy/validacao.
- Use `scripts/telemetry_report.py` para transformar `~/.jarvis/events.jsonl` em um resumo com `command_id`, latencia, status e passos executados.
- Pipeline de seguranca: redacao de dados sensiveis, kill switch e logs.

## Como rodar
1. Crie e ative o venv (`python3 -m venv .venv && . .venv/bin/activate`).
2. Instale dependencias (`pip install -r requirements.txt`).
   - Para instalar dependencias de sistema + browsers do Playwright, use `scripts/install_deps.sh`.
   - O Jarvis carrega `.env` automaticamente (desative com `JARVIS_DISABLE_DOTENV=1`).
3. Configure `.env` a partir de `.env.example` (use apenas variaveis self-hosted: `JARVIS_LOCAL_LLM_BASE_URL`, `JARVIS_LOCAL_LLM_MODEL`, `JARVIS_BROWSER_AI_URL`, `JARVIS_STT_MODE=local` etc.).
4. Defina o cerebro no VPS (veja `Documentos/PLANO_UNICO.md`) e execute `python3 -m jarvis.app --loop`.
5. Use `python3 -m jarvis.app --preflight` para validar o ambiente e `scripts/run_benchmarks.sh` (agora salvando em `Documentos/archive/benchmarks/`) para medir peso.
6. Opcional: levante o serviço mínimo de memória remota com `./scripts/start_remote_memory_server.sh --host 0.0.0.0 --port 8000` para compartilhar memórias com um VPS ou outra máquina.

## Agent S3 (GUI)
- Execute `python3 -m jarvis.app --s3 "sua tarefa aqui"`.
- O S3 usa endpoint OpenAI-compat self-hosted (nao API externa).

## Atalho com painel rapido
- Execute `scripts/start_gui_panel.sh` para ativar o virtualenv, instalar dependencias se necessario e abrir o painel flutuante (`python3 -m jarvis.app --gui-panel`). O script ja exporta `JARVIS_REQUIRE_APPROVAL=false` e `JARVIS_DRY_RUN=false` por padrao para evitar travas de aprovacao.
- Para transformar isso em um app no menu/dock, rode `scripts/install_launcher.sh`. Ele gera `~/.local/share/applications/jarvis-panel.desktop` apontando para o script acima e ja deixa o atalho disponivel no menu.
- Depois de instalar o launcher, abra o menu de aplicativos do Pop!_OS, procure por 'Jarvis Panel', clique com o botao direito e escolha 'Adicionar aos Favoritos' (ou arraste o icone para a dock). Agora todo clique abre o painel e grava telemetria automatica.

## Configuracao refletida
- O cerebro local e compativel com OpenAI apenas para apontar para o seu servidor self-hosted (llama.cpp/vLLM) com o modelo `qwen2.5-7b-instruct`. Nao usamos APIs externas.
- O default e `STT local` (faster-whisper) e `TTS local` (piper/espeak). Nao ha variaveis de APIs externas (Groq/OpenAI/Gemini) nem Supabase obrigatorio.
- O fluxo de seguranca continua usando aprovacao (voz+tecla), killswitch, politicas do usuario e monitoramento de telemetria.

## Documentacao essencial
- `Documentos/PLANO_UNICO.md`: esqueleto do plano honesto (quantizacao, LoRA, treino incremental, checklists). Leia antes de alterar a arquitetura.
- `Documentos/DIAGRAMA_ARQUITETURA.svg`: mapa visual atualizado sem APIs externas; mostra o PC, o VPS e o servidor GPU.
- `Documentos/README.md`: resumo do diretorio de documentos e da historia que contamos para o Jarvis.
- `Documentos/archive/`: historico do plano anterior, plano pessoal e benchmarks.
- `PROJECT_SPEC.md`: especificacao tecnica para revisao automatica (setup, testes, estrutura).

Siga o plano, mantenha o cerebro open-source evoluindo com quantizacao e LoRA, e conte a historia para que o Jarvis continue aprendendo com seguranca.
