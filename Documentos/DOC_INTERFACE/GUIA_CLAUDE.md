# Guia do Claude - Interface de Entrada/Saida do Jarvis

**Atualizado em:** 2026-01-19
**Idioma:** Este guia esta em portugues. Sempre responda em portugues claro.

---

## REGRAS GERAIS PARA O CLAUDE

### 1. Sempre Responder em Portugues Claro

- Use portugues brasileiro simples e direto
- Evite jargoes tecnicos quando possivel
- Quando usar termos tecnicos, explique de forma simples

**Exemplo de explicacao simples:**
- "Latencia" = o tempo que demora para algo acontecer
- "TTFA" (Time To First Audio) = tempo ate o primeiro som sair
- "VAD" = detector de fala (sabe quando voce esta falando)
- "STT" = transforma sua voz em texto
- "TTS" = transforma texto em voz

### 2. Documentar Tudo que Fizer

Apos cada alteracao no projeto:

1. **Atualizar CORRECOES_DOCINTERFACE.MD**
   - Marcar itens como `[x] FEITO` quando completar
   - Adicionar novos itens se necessario
   - Explicar o que foi feito de forma simples

2. **Atualizar documentacao do codigo alterado**
   - Ir ate `Documentos/DOC_INTERFACE/<nome_do_modulo>.md`
   - Atualizar a secao "O que esta implementado"
   - Atualizar a data de revisao
   - Se o documento nao existir, criar um novo

3. **Se criar codigo novo**
   - Criar documentacao correspondente em `Documentos/DOC_INTERFACE/`
   - Seguir o padrao dos outros documentos (veja exemplo abaixo)

### 3. Padrao para Novos Documentos

```markdown
# <nome_do_modulo>.py

- Caminho: `jarvis/<path>/<nome_do_modulo>.py`
- Papel: <descricao curta do que o modulo faz>
- Onde entra no fluxo: <quando e como e usado>
- Atualizado em: YYYY-MM-DD

## Responsabilidades
- <lista do que o modulo faz>

## Entrada e saida
- Entrada: <o que recebe>
- Saida: <o que retorna>

## Configuracao (env/config)
- `NOME_DA_VAR`: <descricao>

## Dependencias diretas
- <biblioteca ou modulo>

## Testes relacionados
- `testes/test_<nome>.py`

## Comandos uteis
- <como testar>

## Qualidade e limites
- <limitacoes conhecidas>

## Performance (estimativa)
- Uso esperado: <baixo/medio/alto>

## Observabilidade
- <como monitorar>

## Problemas conhecidos (hoje)
- <bugs ou limitacoes>

## Melhorias sugeridas
- <o que pode ser melhorado>
```

---

## FLUXO DE TRABALHO

### Antes de Comecar

1. **Ler o diagrama de arquitetura:**
   - `Documentos/DOC_INTERFACE/DIAGRAMA_ARQUITETURA.md`

2. **Ver o que ja foi feito:**
   - `Documentos/DOC_INTERFACE/CORRECOES_DOCINTERFACE.MD`

3. **Entender o codigo que vai alterar:**
   - Ler a documentacao em `Documentos/DOC_INTERFACE/<modulo>.md`
   - Ler o codigo fonte correspondente

### Durante o Trabalho

1. **Seguir a arquitetura existente**
   - Nao criar pastas novas sem necessidade
   - Seguir os padroes de nomes existentes
   - Manter a organizacao modular

2. **Testar antes de finalizar**
   - Rodar os testes do modulo alterado
   - Se criar codigo novo, criar testes

3. **Documentar enquanto faz**
   - Anotar o que esta fazendo
   - Atualizar documentacao imediatamente

### Depois de Finalizar

1. **Rodar testes completos:**
   ```bash
   PYTHONPATH=. ./.venv/bin/python -m pytest -q testes/
   ```

2. **Se for codigo de voz, rodar benchmark:**
   ```bash
   PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio \
     --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav \
     --text "ok" --repeat 5 --resample
   ```

3. **Atualizar documentacao:**
   - CORRECOES_DOCINTERFACE.MD
   - Documento do modulo alterado
   - TESTES_REALISADOS_INTERFACE.MD (se rodar testes)

---

## ESTRUTURA DO PROJETO

```
jarvis/interface/
├── entrada/          # Modulos de entrada (voz, texto)
│   ├── stt.py       # Speech-to-Text
│   ├── vad.py       # Voice Activity Detection
│   ├── chat_ui.py   # Interface de texto
│   └── ...
├── saida/           # Modulos de saida (voz)
│   └── tts.py       # Text-to-Speech
├── audio/           # Utilidades de audio
├── infra/           # Infraestrutura
└── telemetria/      # Metricas

Documentos/DOC_INTERFACE/
├── DIAGRAMA_ARQUITETURA.md   # Visao geral da arquitetura
├── CORRECOES_DOCINTERFACE.MD # Checklist do que fazer
├── GUIA_CLAUDE.md            # Este guia
├── <modulo>.md               # Documentacao de cada modulo
├── bench_audio/              # Audios para benchmark
└── test_audio/               # Audios para testes
```

---

## METAS DO PROJETO

### Meta Principal: Latencia Baixa

- **p50 <= 1200ms** (tempo ate primeira resposta)
- **p95 <= 1600ms** (em 95% dos casos)

### O que ja foi alcancado:

- p50 ~600ms em alguns cenarios
- Voz humanizada (Piper) funcionando
- Fase 1 ("Entendi...") instantanea

### O que ainda falta (ver CORRECOES_DOCINTERFACE.MD):

- Validar em maquinas mais fracas
- Implementar barge-in (interromper quando usuario fala)
- Melhorar tratamento de ruido

---

## VARIAVEIS DE AMBIENTE IMPORTANTES

### Voz Humanizada (Piper)
```bash
JARVIS_TTS_ENGINE=piper           # Usa Piper (voz bonita)
JARVIS_TTS_ENGINE_STRICT=1        # Nao usa voz robotica
JARVIS_PIPER_BACKEND=python       # Carrega modelo em memoria
```

### STT (Transcrever voz)
```bash
JARVIS_STT_MODEL=tiny             # Modelo rapido
JARVIS_STT_WARMUP=1               # Pre-aquece o modelo
```

### VAD (Detectar fala)
```bash
JARVIS_VAD_STRATEGY=webrtc        # Detector leve
JARVIS_VAD_SILENCE_MS=400         # Tempo de silencio
```

### Latencia Percebida
```bash
JARVIS_VOICE_PHASE1=1             # Fala "Entendi..." rapido
JARVIS_TTS_ACK_PHRASE="Entendi. Ja vou responder."
```

---

## COMANDOS UTEIS

### Rodar Testes
```bash
# Todos os testes
PYTHONPATH=. ./.venv/bin/python -m pytest -q testes/

# Testes de um modulo
PYTHONPATH=. ./.venv/bin/python -m pytest -q testes/test_tts_interface.py
```

### Benchmark de Latencia
```bash
PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio \
  --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav \
  --text "ok" --repeat 20 --resample
```

### Verificar TTS
```bash
PYTHONPATH=. ./.venv/bin/python -c "from jarvis.interface.saida.tts import check_tts_deps; print(check_tts_deps())"
```

### Rodar Jarvis em Modo Voz
```bash
PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice
```

---

## ERROS COMUNS E SOLUCOES

### "webrtcvad not installed"
```bash
pip install webrtcvad
```

### "Piper model not found"
- Verificar se o modelo existe em `storage/models/piper/`
- Baixar de: https://huggingface.co/rhasspy/piper-voices

### "sounddevice" nao funciona
```bash
# No Ubuntu/Pop!_OS
sudo apt-get install libportaudio2
```

### Latencia muito alta
- Verificar se `JARVIS_STT_MODEL=tiny`
- Verificar se `JARVIS_TTS_WARMUP=1`
- Verificar se `JARVIS_AUDIO_PREFER_16K=1`

---

## DOCUMENTOS IMPORTANTES

| Documento | O que contem |
|-----------|--------------|
| `DIAGRAMA_ARQUITETURA.md` | Visao geral do sistema |
| `CORRECOES_DOCINTERFACE.MD` | Checklist de tarefas |
| `DEPENDENCIAS_INTERFACE.md` | O que precisa instalar |
| `TESTES_INTERFACE.md` | Como rodar os testes |
| `TESTES_REALISADOS_INTERFACE.MD` | Resultados de testes |
| `TESTES_VOZ_SEM_MICROFONE.MD` | Testes sem hardware |
| `auto_config_voz.md` | Config automatica de voz |
| `benchmark_interface.md` | Como medir performance |

---

## RESUMO

1. **Sempre responder em portugues claro**
2. **Ler a documentacao antes de alterar**
3. **Testar depois de alterar**
4. **Documentar tudo que fizer**
5. **Atualizar CORRECOES_DOCINTERFACE.MD**
6. **Seguir a arquitetura existente**

Quando terminar uma tarefa, sempre pergunte: "Atualizei a documentacao?"
