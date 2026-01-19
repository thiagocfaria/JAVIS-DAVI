#!/usr/bin/env python3
"""Teste de verificação pós-correção dos bugs do TTS."""

import os
import sys
import subprocess
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from types import SimpleNamespace
from jarvis.interface.saida.tts import TextToSpeech
from jarvis.cerebro.config import Config
from typing import cast

# Configurar variáveis de ambiente
os.environ["JARVIS_TTS_STREAMING"] = "1"
os.environ["JARVIS_TTS_CHUNKING"] = "1"

config = cast(
    Config,
    SimpleNamespace(tts_mode="auto", stop_file_path=Path.home() / ".jarvis" / "STOP"),
)
tts = TextToSpeech(config)

print("=== Teste 1: Chunking com lock (deve proteger contra race conditions) ===")


def test_chunking():
    tts.speak(
        "Esta é uma frase muito longa que deve ser dividida em múltiplos chunks para testar o comportamento do sistema de chunking quando há múltiplas chamadas simultâneas."
    )


# Teste simultâneo para verificar race condition
print("Executando 3 chamadas simultâneas...")
threads = []
for i in range(3):
    t = threading.Thread(target=test_chunking)
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("\n=== Teste 2: Verificação de processos ===")
print("Verificando processos órfãos...")
result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
piper_procs = [
    line
    for line in result.stdout.split("\n")
    if "piper" in line.lower() and "grep" not in line
]
aplay_procs = [
    line
    for line in result.stdout.split("\n")
    if "aplay" in line.lower() and "grep" not in line
]

if piper_procs:
    print(f"AVISO: {len(piper_procs)} processos piper ainda rodando")
    for proc in piper_procs:
        print(f"  {proc}")
else:
    print("✓ Nenhum processo piper órfão encontrado")

if aplay_procs:
    print(f"AVISO: {len(aplay_procs)} processos aplay ainda rodando")
    for proc in aplay_procs:
        print(f"  {proc}")
else:
    print("✓ Nenhum processo aplay órfão encontrado")

print("\nTestes concluídos. Verifique storage/logs/log_ops.jsonl")
