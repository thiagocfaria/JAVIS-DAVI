#!/usr/bin/env bash
set -euo pipefail

# Reproduz todos os WAVs de teste em um sink virtual e usa seu monitor como microfone.
# Serve para testar o pipeline de voz end-to-end sem intervenção manual.
#
# Requisitos: pactl (PulseAudio/PipeWire), aplay/paplay, env do Jarvis configurado.
#
# Fluxo:
# 1) Cria sink nulo jarvis_loopback e guarda sink/source atuais.
# 2) Mantém o sink padrão físico (você ouve normalmente).
#    Cria um loopback do monitor do sink físico para o jarvis_loopback (capturado pelo Jarvis).
# 3) Define source padrão para jarvis_loopback.monitor (Jarvis "ouve" o áudio reproduzido).
# 4) Sobe o Jarvis em --voice-loop com TTS volume 0 (evita feedback) no background.
# 5) Toca cada WAV com paplay no sink padrão físico (você escuta; o loopback entrega ao Jarvis).
# 6) Encerra o Jarvis, restaura sink/source e descarrega os módulos.

AUDIO_DIR="${1:-Documentos/DOC_INTERFACE/test_audio}"
JARVIS_CMD="${JARVIS_CMD:-python -m jarvis.interface.entrada.app --voice-loop --voice-loop-max-iter 0}"
SLEEP_BETWEEN="${SLEEP_BETWEEN:-2}"
SINK_NAME="jarvis_loopback"
# Sink físico (override via PHYSICAL_SINK se quiser forçar)
PHYSICAL_SINK="${PHYSICAL_SINK:-}"
# Modo silencioso: toca no sink virtual (não sai no alto-falante)
SILENT="${SILENT:-0}"

get_default() {
  pactl info | awk -F': ' '/Default Sink|Destino padrão/ {print $2; exit}'
}

get_default_source() {
  pactl info | awk -F': ' '/Default Source|Fonte padrão/ {print $2; exit}'
}

if ! command -v pactl >/dev/null 2>&1; then
  echo "pactl não encontrado; instale PulseAudio/PipeWire tools." >&2
  exit 1
fi

if [ ! -d "$AUDIO_DIR" ]; then
  echo "Pasta de áudios não encontrada: $AUDIO_DIR" >&2
  exit 1
fi

orig_sink="$(get_default)"
orig_source="$(get_default_source)"
if [ -z "$orig_sink" ]; then
  orig_sink="$(pactl list short sinks | awk '!/jarvis_loopback/ {print $2; exit}')"
fi
if [ -z "$orig_source" ]; then
  orig_source="$(pactl list short sources | awk '!/jarvis_loopback/ {print $2; exit}')"
fi
if [ -z "$orig_sink" ]; then
  echo "Não consegui detectar sink físico. Informe via PHYSICAL_SINK=<sink>." >&2
  exit 1
fi

if [ -n "$PHYSICAL_SINK" ]; then
  orig_sink="$PHYSICAL_SINK"
  pactl set-default-sink "$orig_sink" || true
fi

module_id="$(pactl load-module module-null-sink sink_name=${SINK_NAME} sink_properties=device.description=JarvisLoopback || true)"
if [ -z "$module_id" ]; then
  echo "Falha ao criar sink virtual." >&2
  exit 1
fi

loop_id=""
if [ "$SILENT" = "0" ] && [ -n "$orig_sink" ]; then
  # Espelha o áudio do sink físico para o loopback (Jarvis ouve pelo monitor virtual).
  loop_id="$(pactl load-module module-loopback source=${orig_sink}.monitor sink=${SINK_NAME} latency_msec=1 || true)"
fi

cleanup() {
  # Restaura defaults e descarrega módulo
  if [ -n "$orig_sink" ]; then pactl set-default-sink "$orig_sink" || true; fi
  if [ -n "$orig_source" ]; then pactl set-default-source "$orig_source" || true; fi
  if [ -n "$loop_id" ]; then pactl unload-module "$loop_id" || true; fi
  if [ -n "$module_id" ]; then pactl unload-module "$module_id" || true; fi
}
trap cleanup EXIT INT TERM

pactl set-default-source "${SINK_NAME}.monitor"

# Forçar TTS mudo para evitar interferência
export JARVIS_TTS_VOLUME="${JARVIS_TTS_VOLUME:-0}"

echo "[loopback] Sink padrão físico: ${orig_sink:-desconhecido} | Source padrão: ${SINK_NAME}.monitor"

set +e
$JARVIS_CMD >/tmp/jarvis_loopback_stdout.log 2>/tmp/jarvis_loopback_stderr.log &
JARVIS_PID=$!
set -e

echo "[loopback] Jarvis PID=$JARVIS_PID"
sleep 2

for f in "$AUDIO_DIR"/*.wav; do
  [ -e "$f" ] || continue
  echo ">> tocando $(basename "$f")"
  if [ "$SILENT" = "1" ]; then
    paplay --device="$SINK_NAME" "$f"
  else
    paplay --device="$orig_sink" "$f"
  fi
  sleep "$SLEEP_BETWEEN"
done

echo "[loopback] Finalizando Jarvis..."
kill "$JARVIS_PID" 2>/dev/null || true
wait "$JARVIS_PID" 2>/dev/null || true
echo "[loopback] Pronto."
