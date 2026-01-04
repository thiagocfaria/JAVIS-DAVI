# Registro de Implementacao

Documento vivo para registrar mudancas concretas, testes executados e proximo passo.

## 2026-01-04
- Adicionado este registro e marcado no plano unico para manter rastro das entregas.
- Suite de testes unitarios `python -m pytest -q` executada localmente (28/28 passando) para validar estado atual antes de novas mudancas de infraestrutura e Rust.
- Itens pendentes mantidos como prioridade: portal Wayland/ponte Rust para acoes, deploy VPS (Tailscale + modelos self-hosted) e memoria remota/telemetria de custo.

Proximo passo sugerido: integrar resultados do preflight estrito no registro e iniciar implementacao da ponte Rust para acoes (JSON-RPC) com client leve no Python.

## 2026-01-05
- Revalidada a suite `python -m pytest -q` (28/28 passando) para confirmar que o estado atual continua estavel.
- Status: automacao local + Agent S3 estao funcionais em Python, mas o projeto nao terminou; faltam portal Wayland/ponte Rust para acoes, deploy VPS (Tailscale + modelo self-hosted), memoria remota e telemetria de custo (ver PLANO_UNICO.md).
- Proximo passo: priorizar ponte Rust/portal Wayland para reduzir peso no PC e iniciar provisionamento do VPS com canal seguro.

## 2026-01-06
- Adicionada ponte de memoria remota (cliente HTTP leve + servidor minimo) com fallback local e testes de integracao que verificam push e merge de resultados.
- Suite `python -m pytest -q` mantem 28/28 passando apos integrar a nova camada de memoria.
- Proximo passo: acoplar o cliente remoto ao fluxo principal do orquestrador (PC <-> VPS) e registrar benchmarks de latencia/custo.

## 2026-01-07
- Servidor de memoria remota ganhou CLI (`python -m jarvis.memoria.remote_service`) e script dedicado (`scripts/start_remote_memory_server.sh`) para facilitar deploy local/VPS.
- Suite `python -m pytest -q` (32/32 passando) incluindo o teste de fumaca do CLI do servidor remoto.
- Proximo passo: ligar o cliente remoto ao fluxo do orquestrador (PC <-> VPS) e medir latencia real para preencher o diagrama com numeros.
