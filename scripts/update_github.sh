#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v git >/dev/null 2>&1; then
  echo "Erro: git nao encontrado. Instale o git e tente novamente."
  exit 1
fi

cd "$ROOT_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Erro: este diretorio nao e um repo git."
  echo "Dica: rode 'git init' na raiz e tente novamente."
  exit 1
fi

if [ -z "$(git config user.name || true)" ] || [ -z "$(git config user.email || true)" ]; then
  echo "Aviso: git user.name/email nao configurado."
  echo "Dica: git config --global user.name \"Seu Nome\""
  echo "      git config --global user.email \"voce@exemplo.com\""
fi

if [ -z "$(git status --porcelain)" ]; then
  echo "Sem alteracoes para commitar."
  exit 0
fi

remote_url="$(git remote get-url origin 2>/dev/null || true)"
if [ -z "$remote_url" ]; then
  echo "Remote 'origin' nao configurado."
  read -r -p "Cole a URL do repo no GitHub (ou deixe vazio para cancelar): " remote_url
  if [ -z "$remote_url" ]; then
    echo "Cancelado."
    exit 1
  fi
  git remote add origin "$remote_url"
fi

branch="$(git symbolic-ref --short HEAD 2>/dev/null || true)"
if [ -z "$branch" ]; then
  branch="main"
  git checkout -b "$branch"
fi

git add -A
read -r -p "Mensagem do commit: " commit_msg
commit_msg="${commit_msg:-chore: update}"
git commit -m "$commit_msg"
git push -u origin "$branch"

echo "Atualizado com sucesso: $remote_url ($branch)"
