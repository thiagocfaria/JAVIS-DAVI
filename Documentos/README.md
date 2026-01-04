# Documentos do Jarvis

Este diretório concentra apenas o que importa agora:
1. `PLANO_UNICO.md` (este plano atualizado).
2. `DIAGRAMA_ARQUITETURA.svg` (mapa visual honesto).
3. `README.md` (este resumo). O resto foi movido para `Documentos/archive/` para preservar histórico sem poluir a raiz.

## Resumo atual
- Jarvis roda localmente e usa um cérebro open-source (Qwen2.5-7B-Instruct) hospedado por nós mesmos no VPS.
- Nenhuma API externa de IA é usada; a confiança depende de quantização, LoRA e regras locais.
- O plano único descreve o ciclo completo: comando → modelo local/VPS → validação → aprendizado incremental.
- Agent S3 integrado ao Jarvis como motor de GUI (loop visual + grounding) com execução segura via policy/validacao (`python3 -m jarvis.app --s3 "tarefa"`).
- OpenAI-compat aqui significa protocolo compatível para servidor self-hosted (não API externa).

## Arquivos-chave
- `PLANO_UNICO.md`: visão estratégica, checklist, e roteiro da quantização/LoRA/treino incremental.
- `DIAGRAMA_ARQUITETURA.svg`: mostra a separação entre a máquina local, o VPS e o servidor GPU (sem nenhuma nuvem externa).
- `archive/`: contém o plano anterior, o plano pessoal e o histórico de benchmarks. Consulte apenas se precisar relembrar decisões antigas.

## Dependencias locais (setup)
- `requirements.txt` lista as dependencias Python para automacao, OCR, STT/TTS e embeddings.
- Para instalar tudo (inclui pacotes do sistema e browsers do Playwright), use `scripts/install_deps.sh`.
- Wayland vs X11: Wayland usa `wtype/ydotool`; X11 usa `xdotool` (o script detecta automaticamente).

## Mini-história para manter a direção
> O Jarvis é um amigo curioso. Ele mora na nossa máquina, mas tem um cérebro que vive em um servidor que nós mesmos cuidamos. Quando damos um comando, ele prepara um plano com cuidado, usa o cérebro quantizado para responder, e depois registra tudo para aprender ainda mais com LoRA e treino incremental. Assim, cada dia ele fica mais esperto sem precisar pagar por APIs.

Use este README como mapa rápido. Alterações reais devem passar primeiro pelo `PLANO_UNICO.md` e depois pelo diagrama.
