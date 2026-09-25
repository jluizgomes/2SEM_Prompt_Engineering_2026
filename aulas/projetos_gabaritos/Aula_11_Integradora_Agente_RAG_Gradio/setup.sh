#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

falhar() {
  printf '[falha] %s\n' "$*" >&2
  exit 1
}

[ -f "requirements.txt" ] || falhar "requirements.txt nao encontrado."
command -v "$PYTHON_BIN" >/dev/null 2>&1 || falhar "Python nao encontrado."
"$PYTHON_BIN" --version >/dev/null 2>&1 || falhar "Falha ao validar o Python."

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

printf '[ok] ambiente pronto em %s\n' "$SCRIPT_DIR"
printf 'Execute python main.py para iniciar a interface Gradio.\n'
