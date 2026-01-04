#!/usr/bin/env bash
# Script de instalação de dependências do Jarvis
# Detecta o sistema e instala dependências necessárias

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Jarvis - Instalação de Dependências ==="
echo ""

# Detectar gerenciador de pacotes
if command -v apt >/dev/null 2>&1; then
    PKG_MGR="apt"
    INSTALL_CMD="sudo apt install -y"
elif command -v yum >/dev/null 2>&1; then
    PKG_MGR="yum"
    INSTALL_CMD="sudo yum install -y"
elif command -v pacman >/dev/null 2>&1; then
    PKG_MGR="pacman"
    INSTALL_CMD="sudo pacman -S --noconfirm"
else
    echo "Erro: Gerenciador de pacotes não detectado (apt/yum/pacman)"
    exit 1
fi

echo "Gerenciador detectado: $PKG_MGR"
echo ""

# Criar venv se não existir
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv "$PROJECT_ROOT/.venv"
fi

# Ativar venv
source "$PROJECT_ROOT/.venv/bin/activate"

# Atualizar pip
echo "Atualizando pip..."
pip install --upgrade pip --quiet

# Instalar dependências Python
echo "Instalando dependências Python..."
pip install -r "$PROJECT_ROOT/requirements.txt" --quiet

# Instalar browsers do Playwright
echo "Instalando browsers do Playwright..."
playwright install chromium --quiet 2>&1 | grep -v "BEWARE" || true

# Instalar dependências de sistema (baseado em apt)
if [ "$PKG_MGR" = "apt" ]; then
    echo "Instalando dependências de sistema (apt)..."
    $INSTALL_CMD \
        tesseract-ocr \
        tesseract-ocr-por \
        espeak-ng \
        python3-tk \
        portaudio19-dev \
        || echo "Aviso: Algumas dependências podem ter falhado (pode ser normal)"

    # Verificar Wayland vs X11
    if [ -n "${WAYLAND_DISPLAY:-}" ] || [ -n "${XDG_SESSION_TYPE:-}" ] && [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
        echo "Wayland detectado - instalando wtype/ydotool..."
        $INSTALL_CMD wtype ydotool || echo "Aviso: wtype/ydotool podem não estar disponíveis"
    else
        echo "X11 detectado - instalando xdotool..."
        $INSTALL_CMD xdotool || echo "Aviso: xdotool pode não estar disponível"
    fi
elif [ "$PKG_MGR" = "yum" ]; then
    echo "Instalando dependências de sistema (yum)..."
    $INSTALL_CMD \
        tesseract \
        tesseract-langpack-por \
        espeak \
        python3-tkinter \
        portaudio-devel \
        || echo "Aviso: Algumas dependências podem ter falhado"
elif [ "$PKG_MGR" = "pacman" ]; then
    echo "Instalando dependências de sistema (pacman)..."
    $INSTALL_CMD \
        tesseract \
        tesseract-data-por \
        espeak-ng \
        tk \
        portaudio \
        || echo "Aviso: Algumas dependências podem ter falhado"
fi

echo ""
echo "=== Validação ==="
echo "Rodando preflight check..."
cd "$PROJECT_ROOT"
python3 -m jarvis.app --preflight

echo ""
echo "=== Instalação concluída ==="
echo "Para usar o Jarvis, ative o ambiente virtual:"
echo "  source .venv/bin/activate"
echo "Ou use diretamente:"
echo "  .venv/bin/python3 -m jarvis.app --preflight"
