#!/usr/bin/env bash
# =============================================================================
# rodar.sh — Roda ESTE exercicio (pasta autossuficiente).
#
# Prepara o ambiente (cria .venv, instala dependencias, compila o frontend se
# faltar) e sobe o servidor em PRIMEIRO PLANO. Ctrl+C encerra.
#
# Uso:  ./rodar.sh [porta]
# =============================================================================
set -uo pipefail

PASTA="$(cd "$(dirname "$0")" && pwd)"
cd "$PASTA"

PORTA="${1:-8001}"

echo "[..] preparando ambiente local..."
if [ ! -x ".venv/bin/python" ]; then
  echo "[..] criando .venv..."
  python3 -m venv .venv || { echo "[!!] falha ao criar o .venv"; exit 1; }
fi
if ! .venv/bin/python -c "import fastapi" >/dev/null 2>&1; then
  echo "[..] instalando dependencias (primeira vez)..."
  .venv/bin/pip install -q -r requirements.txt || { echo "[!!] falha no pip install"; exit 1; }
fi
if [ ! -f "frontend/dist/index.html" ]; then
  echo "[..] compilando frontend (primeira vez)..."
  (cd frontend && npm install --no-fund --no-audit >/dev/null 2>&1 && npm run build >/dev/null 2>&1) \
    || { echo "[!!] falha ao compilar o frontend"; exit 1; }
fi

# .env não é versionado: cria a partir do exemplo se faltar
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  echo "[..] .env criado a partir de .env.example — confira OLLAMA_API_KEY."
fi

echo
echo "[ok] servidor em: http://127.0.0.1:${PORTA}"
echo "[..] Ctrl+C para encerrar."
echo
exec .venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port "$PORTA"
