#!/bin/bash
# =========================================================
# FIAP AI Lab — Entrypoint do Ollama (CPU)
# Sobe o servidor Ollama e garante que os modelos padrão
# da disciplina estejam baixados antes de liberar o uso.
#
# Variáveis:
#   CHAT_MODEL       modelo de chat baixado no boot
#   EMBEDDING_MODEL  modelo de embeddings baixado no boot
#   GUARDRAIL_MODELS modelos de guardrail CPU separados por vírgula
#   EXTRA_MODELS     lista extra separada por vírgula (opcional)
# =========================================================
set -e

CHAT_MODEL="${CHAT_MODEL:-qwen3.5:0.8b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding:0.6b}"
# Guardrails leves para demonstração em CPU:
# - Llama Guard 3 1B Q4_K_M: ~955 MB, 128K de contexto, PT-BR suportado
# - Granite Guardian 3.0 2B: ~2,7 GB, 8K de contexto
GUARDRAIL_MODELS="${GUARDRAIL_MODELS:-llama-guard3:1b-q4_K_M,granite3-guardian:2b}"
EXTRA_MODELS="${EXTRA_MODELS:-}"

echo "=========================================================="
echo " FIAP AI Lab - Iniciando servidor Ollama (CPU)"
echo " Modelo de chat:      ${CHAT_MODEL}"
echo " Modelo de embedding: ${EMBEDDING_MODEL}"
echo " Guardrails CPU:      ${GUARDRAIL_MODELS}"
if [ -n "${EXTRA_MODELS}" ]; then
  echo " Modelos extras:      ${EXTRA_MODELS}"
fi
echo "=========================================================="

# Sobe o servidor Ollama em background
ollama serve &
OLLAMA_PID=$!

# Aguarda o servidor responder antes de tentar puxar modelos
echo "Aguardando o servidor Ollama iniciar..."
until curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; do
  sleep 1
done
echo "Servidor Ollama pronto."

pull_model() {
  local model="$1"
  [ -z "${model}" ] && return 0
  if ollama list | awk '{print $1}' | grep -qx "${model}"; then
    echo "-> Modelo '${model}' já presente, pulando download."
  else
    echo "-> Baixando modelo '${model}'..."
    if ! ollama pull "${model}"; then
      echo "AVISO: falha ao baixar '${model}'. Verifique o nome do modelo/conexão." >&2
    fi
  fi
}

pull_model "${CHAT_MODEL}"
pull_model "${EMBEDDING_MODEL}"

if [ -n "${GUARDRAIL_MODELS}" ]; then
  # Baixa os guardrails separadamente para deixá-los visíveis no log da aula.
  IFS=',' read -ra _guardrails <<< "${GUARDRAIL_MODELS}"
  for _m in "${_guardrails[@]}"; do
    pull_model "$(echo "${_m}" | xargs)"
  done
fi

if [ -n "${EXTRA_MODELS}" ]; then
  # Divide a lista por vírgula e baixa cada modelo
  IFS=',' read -ra _extra <<< "${EXTRA_MODELS}"
  for _m in "${_extra[@]}"; do
    pull_model "$(echo "${_m}" | xargs)"
  done
fi

echo "=========================================================="
echo " Modelos disponíveis:"
ollama list
echo "=========================================================="
echo " FIAP AI Lab pronto. Servidor Ollama rodando em :11434"
echo "=========================================================="

# Mantém o container vivo, seguindo o processo do servidor
wait "${OLLAMA_PID}"
