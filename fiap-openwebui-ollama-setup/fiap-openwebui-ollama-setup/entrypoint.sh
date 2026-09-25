#!/bin/bash
# =========================================================
# FIAP - Entrypoint do Ollama (CPU)
# Sobe o servidor Ollama e garante que os modelos padrão
# da disciplina estejam baixados antes de liberar o uso.
# =========================================================
set -e

CHAT_MODEL="${CHAT_MODEL:-qwen3.5:0.8b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding:0.6b}"

echo "=========================================================="
echo " FIAP AI Lab - Iniciando servidor Ollama (CPU)"
echo " Modelo de chat:      ${CHAT_MODEL}"
echo " Modelo de embedding: ${EMBEDDING_MODEL}"
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

echo "=========================================================="
echo " Modelos disponíveis:"
ollama list
echo "=========================================================="
echo " FIAP AI Lab pronto. Servidor Ollama rodando em :11434"
echo "=========================================================="

# Mantém o container vivo, seguindo o processo do servidor
wait "${OLLAMA_PID}"
