#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORTA="${1:-8101}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

falhar() {
  printf '[falha] %s\n' "$*" >&2
  exit 1
}

case "$PORTA" in
  ''|*[!0-9]*) falhar "Porta invalida: $PORTA" ;;
esac
[ -f "requirements.txt" ] || falhar "requirements.txt nao encontrado."
[ -f "frontend/package.json" ] || falhar "frontend/package.json nao encontrado."
command -v "$PYTHON_BIN" >/dev/null 2>&1 || falhar "Python nao encontrado."
command -v node >/dev/null 2>&1 || falhar "Node.js nao encontrado."
command -v npm >/dev/null 2>&1 || falhar "npm nao encontrado."
"$PYTHON_BIN" --version >/dev/null 2>&1 || falhar "Falha ao validar o Python."
node --version >/dev/null 2>&1 || falhar "Falha ao validar o Node.js."
npm --version >/dev/null 2>&1 || falhar "Falha ao validar o npm."

if [ ! -f ".env" ]; then
  [ -f ".env.example" ] || falhar ".env.example nao encontrado."
  cp .env.example .env || falhar "Falha ao criar .env."
fi

if [ ! -x ".venv/bin/python" ]; then
  "$PYTHON_BIN" -m venv .venv || falhar "Falha ao criar o .venv."
fi
[ -x ".venv/bin/python" ] || falhar ".venv criado sem Python."

.venv/bin/python -m pip install --upgrade pip || falhar "Falha ao atualizar o pip."
.venv/bin/python -m pip install -r requirements.txt || falhar "Falha ao instalar as dependencias Python."

(
  cd frontend
  if [ -f "package-lock.json" ]; then
    npm ci --no-fund --no-audit || falhar "Falha no npm ci."
  else
    npm install --no-fund --no-audit || falhar "Falha no npm install."
  fi
  npm run build || falhar "Falha no build do frontend."
)

printf '[ok] servidor em http://127.0.0.1:%s\n' "$PORTA"
if .venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port "$PORTA"; then
  exit 0
else
  status=$?
  printf '[falha] Uvicorn terminou com codigo %s.\n' "$status" >&2
  exit "$status"
fi
