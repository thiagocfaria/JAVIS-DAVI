#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$DESKTOP_DIR/jarvis-panel.desktop"

mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Jarvis Panel
Comment=Abre o Jarvis com o painel flutuante pronto para comandos
Exec=$ROOT_DIR/scripts/start_gui_panel.sh
Icon=utilities-terminal
Terminal=true
Categories=Utility;Development;
StartupNotify=true
EOF

chmod 644 "$DESKTOP_FILE"
echo "Launcher instalado em: $DESKTOP_FILE"
echo "Agora procure por \"Jarvis Panel\" no menu de aplicativos e fixe-o na dock."
