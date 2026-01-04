Documento Geral — Infra + Treinamento do Agente Jarvis (1 usuario)
Atualizado: 2026-01-04

1. Resumo executivo (decisao unica)
Decidimos manter 100% self-hosted para inferencia: o PC local executa o Jarvis (policy, kill-switch, validacao e automacao), enquanto o cerebro pesado (LLM) e o grounding visual (UI-TARS) rodam em GPU alugada sob demanda, apenas durante o uso (~5h/dia). Para caber no orcamento de R$ 300/mes, usamos roteamento: modelo medio como padrao e modelo 70B apenas para tarefas realmente complexas. O treino LoRA e offline, em ciclos quinzenais, sempre em GPU alugada e com dados sanitizados.

2. Objetivos e restricoes
Objetivos:
    • Agente que opera um desktop (Linux/Wayland) como humano: mouse, teclado, copiar/colar, navegacao em apps.
    • Rodar em producao para 1 usuario por pelo menos 5 horas por dia.
    • Evoluir comportamento com supervisao humana (aprovando/corrigindo acoes) e treino incremental (LoRA).
    • Manter custo mensal no menor valor possivel (teto: R$ 300/mes).
Restricoes:
    • 100% self-hosted (sem APIs externas de IA).
    • Policy, kill-switch e validacao devem ficar no PC local.
    • Nao manter GPU 24/7: somente durante o uso.
    • Preferir acoes estruturadas (A11Y) quando possivel, com fallback XY.

3. Decisao final de infraestrutura (producao 1 usuario)
Infra escolhida:
    • PC local (Pop!_OS/Wayland): Jarvis completo (policy, validacao, automacao, logs).
    • GPU alugada sob demanda (marketplace): apenas para LLM e grounding.
    • Modelos:
        - Grounding visual: UI-TARS-1.5-7B (S3).
        - Cerebro padrao (texto): Qwen2.5-32B (quantizado).
        - Cerebro pesado (texto): Llama 3.1-70B (quantizado), usado apenas quando necessario.
    • Conexao segura: Tailscale (PC local <-> GPU) com allowlist e firewall.
    • Persistencia: volume/slot de disco para manter pesos e checkpoints (>= 200 GB).

Notas de VRAM (para dimensionar GPU):
    • UI-TARS 7B + Qwen 32B Q4 cabem em 24 GB se otimizarmos contexto/imagem.
    • Llama 70B Q4 precisa ~40-48 GB VRAM (ideal: L40S 48 GB ou superior).
    • Se 48 GB estiver fora do orcamento, o modo pesado fica desativado.

4. Custos — como calculamos e quanto vamos pagar
4.1 Variaveis (ajustaveis):
    • preco_gpu_usd_h
    • horas_dia = 5
    • dias_mes = 30 (150 h/mes)
    • cambio_brl_usd
    • overhead_mensal_brl (storage/egress/logs)

4.2 Formula:
    • horas_mes = horas_dia x dias_mes
    • custo_gpu_brl = preco_gpu_usd_h x horas_mes x cambio_brl_usd
    • custo_total_brl = custo_gpu_brl + overhead_mensal_brl

4.3 Teto para caber em R$ 300/mes:
    • preco_gpu_usd_h <= (300 - overhead_mensal_brl) / (horas_mes x cambio_brl_usd)

Exemplo (apenas para referencia):
    • Se overhead = R$ 40, cambio = 5.5, horas_mes = 150
    • preco_gpu_usd_h <= (260 / 150 / 5.5) = ~0.31 USD/h

Isso define o limite do marketplace. Acima disso, precisamos reduzir horas, usar modelo menor ou dividir modo pesado em poucas horas por mes.

5. Arquitetura (como tudo se conecta)
Fluxo (visao simples):
    • Usuario da tarefa no PC local.
    • Jarvis captura tela local + contexto.
    • Envia imagem/inputs para o grounding (UI-TARS) no servidor GPU.
    • Envia contexto e instrucoes para o LLM no servidor GPU.
    • Recebe acao proposta -> policy local -> aprovacao humana -> execucao local.
    • Validacao local (OCR/screenshot) + logs.
    • Periodicamente: exporta logs -> treino LoRA -> valida -> publica adaptador.

6. Contrato de acoes (Action Space) — alinhado ao Jarvis
Acoes sao objetos JSON com schema fixo. Preferir A11Y, usar XY apenas quando necessario.
Acoes MVP:
    • open_app {app}
    • open_url {url}
    • type_text {text, target|x,y, overwrite, enter}
    • hotkey {combo}
    • click {x,y | target}
    • drag {start_x,start_y,end_x,end_y}
    • scroll {amount}
    • wait {seconds}
    • navigate/web_click/web_fill/web_screenshot (web)
Exemplo:
{ "type": "click", "params": { "target": "Salvar" } }

7. Logging (dados para treino e auditoria)
Formato: JSONL (1 passo por linha). Campos minimos:
    • timestamp, task_id, app_name, window_title
    • obs: screenshot_path, (opcional) a11y_snapshot
    • prompt/contexto de alto nivel
    • action_pred (acao sugerida), action_gold (acao aprovada/corrigida)
    • result: success/fail + evidencia

8. Treino (como o agente melhora sem gastar caro)
Treino e offline e self-hosted (sem Kaggle/terceiros):
    • Ciclo recomendado: quinzenal (para caber no orcamento).
    • Comecar pelo PLANNER (texto): mais barato e melhora qualidade rapido.
    • So depois, treinar o executor GUI (UI-TARS) com dados visuais.
Pipeline:
    • Exportar logs -> limpar/sanitizar -> dataset (instrucao -> plano correto)
    • Treinar LoRA/QLoRA do planner (Qwen 32B; opcionalmente Llama 70B em ciclos raros)
    • Avaliar em tarefas fixas
    • Se melhorou: publicar adaptador e ativar

9. Runbook (passo a passo)
9.1 Provisionar GPU no marketplace:
    1) Escolher GPU conforme VRAM e preco/hora (preferir >= 24 GB, ideal 48 GB para 70B).
    2) Subir instancia com Ubuntu + Docker + driver NVIDIA.
    3) Criar volume persistente (>= 200 GB) para pesos/ckpts.
    4) Instalar Tailscale e restringir acesso por allowlist.

9.2 Subir servicos de inferencia:
    5) Subir servidor OpenAI-compat (vLLM ou llama.cpp) para LLM.
    6) Subir servidor do grounding (UI-TARS) no mesmo host ou GPU separada.
    7) Testar endpoints com uma requisicao simples.

9.3 Configurar PC local:
    8) Ajustar .env com JARVIS_LOCAL_LLM_BASE_URL e JARVIS_S3_* apontando para o servidor GPU.
    9) Rodar preflight e um teste curto com --s3.

9.4 Operacao diaria (5h/dia):
    10) Iniciar GPU apenas no horario de uso.
    11) Executar tarefas reais com gate humano.
    12) Encerrar GPU e salvar logs ao final.

9.5 Treino quinzenal (LoRA):
    13) Subir dataset sanitizado no servidor GPU.
    14) Rodar LoRA/QLoRA do planner.
    15) Validar com tarefas fixas.
    16) Publicar adaptador e registrar metricas.

10. Checklists (para producao com seguranca)
10.1 Checklist de seguranca
    • [ ] Gate humano ativo.
    • [ ] PC local com kill-switch funcional.
    • [ ] Tailscale com allowlist e firewall.
    • [ ] Logs sem segredos (redacao automatica).

10.2 Checklist de observabilidade
    • [ ] Taxa de sucesso por tarefa.
    • [ ] Tempo por tarefa e numero de passos.
    • [ ] Evidencia de erro (screenshot + acao).

10.3 Checklist de controle de custo
    • [ ] GPU desligada fora da janela diaria.
    • [ ] Limite de chamadas para modo pesado (70B).
    • [ ] Revisao semanal de gasto.

11. Criterios de aceitacao do MVP
    • Executar 10 tarefas-alvo com gate humano e logs completos.
    • Apos 1 ciclo de LoRA, reduzir em pelo menos 15% passos ou aumentar taxa de sucesso.
    • Operacao diaria estavel por 5h/dia sem custo acima do teto.

12. Referencias (para consulta)
    • UI-TARS-1.5-7B (Hugging Face)
    • Llama 3.1 (Meta)
    • Qwen2.5 (Alibaba)
    • vLLM / llama.cpp (servidor OpenAI-compat)
    • Tailscale (rede privada)
