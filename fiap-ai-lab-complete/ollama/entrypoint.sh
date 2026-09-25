#!/bin/bash
# =========================================================
# FIAP AI Lab — Entrypoint do Ollama
# Sobe o servidor Ollama, importa modelos GGUF locais (pasta models/),
# afina a performance e garante os modelos padrão da disciplina.
# Funciona com GPU (se reservada no compose) ou só em CPU.
#
# Variáveis:
#   CHAT_MODEL       modelo de chat padrão
#   EMBEDDING_MODEL  modelo de embeddings
#   GUARDRAIL_MODELS modelos de guardrail separados por vírgula
#   EXTRA_MODELS     lista extra separada por vírgula (opcional)
#   GGUF_FILE        arquivo .gguf em /models a importar no boot
#   GGUF_MODEL       nome do modelo importado (padrão: nome do arquivo)
#   EMBEDDING_CONTEXT contexto da variante enxuta de embeddings
#
# Performance:
#   OLLAMA_KEEP_ALIVE        -1 mantém o modelo residente
#   OLLAMA_NUM_THREADS       vazio = detecta os P-cores
#   OLLAMA_NUM_PARALLEL      requisições simultâneas por modelo
#   OLLAMA_MAX_LOADED_MODELS modelos residentes ao mesmo tempo
#   OLLAMA_CONTEXT_LENGTH    janela de contexto (tokens)
# =========================================================
set -e

CHAT_MODEL="${CHAT_MODEL:-qwen3.5:0.8b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding:0.6b}"
# Guardrails para demonstração:
# - Llama Guard 3 1B Q4_K_M: ~955 MB, 128K de contexto, PT-BR suportado
# - Granite Guardian 3.0 2B: ~2,7 GB, 8K de contexto
GUARDRAIL_MODELS="${GUARDRAIL_MODELS:-llama-guard3:1b-q4_K_M,granite3-guardian:2b}"
EXTRA_MODELS="${EXTRA_MODELS:-}"
GGUF_DIR="${GGUF_DIR:-/models}"
GGUF_FILE="${GGUF_FILE:-}"
GGUF_MODEL="${GGUF_MODEL:-}"

# ---------------------------------------------------------
# Detecção de hardware
# ---------------------------------------------------------

# Há GPU NVIDIA de verdade disponível neste container?
tem_gpu_nvidia() {
  [ -e /dev/nvidia0 ] || [ -e /dev/nvidiactl ]
}

if tem_gpu_nvidia; then
  MODO="GPU ($(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo NVIDIA))"
else
  MODO="CPU"
fi

# Quantos núcleos físicos a máquina tem (sem contar hyperthreading).
nucleos_fisicos() {
  grep -E '^(physical id|core id)' /proc/cpuinfo 2>/dev/null \
    | sed 's/^[[:space:]]*//' \
    | awk '{print $NF}' \
    | paste - - \
    | sort -u \
    | grep -c .
}

# Quantos threads o processo pode usar (respeita cgroup/cpuset).
threads_disponiveis() {
  nproc 2>/dev/null || grep -c '^processor' /proc/cpuinfo 2>/dev/null || echo 0
}

# Detecta quantos núcleos de alta performance (P-cores) usar em CPUs
# híbridas Intel. Agrupa os núcleos físicos por frequência máxima: os
# P-cores ficam nos bins de turbo mais altos e os E-cores num bin baixo.
# Usa /sys quando exposto; senão cai para o total de núcleos físicos.
detectar_pcores() {
  local freq_dir="/sys/devices/system/cpu/cpufreq"
  [ -d "${freq_dir}" ] || return 1

  awk '
    BEGIN {
      while (("cat /sys/devices/system/cpu/cpu*/cpufreq/cpuinfo_max_freq 2>/dev/null" | getline linha) > 0) {
        cpus++
        freq[cpus] = linha + 0
      }
      if (cpus == 0) { exit 1 }
      for (i = 1; i <= cpus; i++) {
        if (freq[i] > maxf) maxf = freq[i]
        if (freq[i] < minf || minf == 0) minf = freq[i]
      }
      if (maxf == minf) { exit 1 }   # CPU homogênea: não há P/E cores
      limiar = maxf * 0.9            # tolerância para bins de turbo
      for (i = 1; i <= cpus; i++) {
        if (freq[i] >= limiar) pcores++
      }
      if (pcores > 0) print pcores
      else exit 1
    }
  ' 2>/dev/null
}

afinar_cpu() {
  local fisicos pcores threads sugerido
  fisicos=$(nucleos_fisicos)
  pcores=$(detectar_pcores) || pcores=""
  threads=$(threads_disponiveis)

  if [ -z "${OLLAMA_NUM_THREADS:-}" ] || [ "${OLLAMA_NUM_THREADS}" = "0" ]; then
    sugerido="${pcores}"
    [ -n "${sugerido}" ] || sugerido="${fisicos}"
    # Nunca pedir mais threads do que os CPUs disponíveis.
    if [ -n "${threads}" ] && [ "${threads}" -gt 0 ] 2>/dev/null; then
      if [ -z "${sugerido}" ] || [ "${sugerido}" -gt "${threads}" ] 2>/dev/null; then
        sugerido="${threads}"
      fi
    fi
    if [ -n "${sugerido}" ] && [ "${sugerido}" -gt 0 ] 2>/dev/null; then
      export OLLAMA_NUM_THREADS="${sugerido}"
      echo "-> OLLAMA_NUM_THREADS não definido; usando ${sugerido}."
    fi
  fi

  echo "----------------------------------------------------------"
  echo " Perfil de performance (${MODO})"
  echo "   threads de inferência : ${OLLAMA_NUM_THREADS:-auto}"
  echo "   CPUs disponíveis      : ${threads:-?} (núcleos físicos: ${fisicos:-?}, p-cores: ${pcores:-n/d})"
  echo "   paralelismo           : ${OLLAMA_NUM_PARALLEL:-auto}"
  echo "   modelos residentes    : ${OLLAMA_MAX_LOADED_MODELS:-auto}"
  echo "   contexto por modelo   : ${OLLAMA_CONTEXT_LENGTH:-auto}"
  echo "   keep_alive            : ${OLLAMA_KEEP_ALIVE:-auto}"
  echo "=========================================================="
}

echo "=========================================================="
echo " FIAP AI Lab - Iniciando servidor Ollama"
echo " Modelo de chat:      ${CHAT_MODEL}"
echo " Modelo de embedding: ${EMBEDDING_MODEL}"
echo " Guardrails:          ${GUARDRAIL_MODELS}"
if [ -n "${EXTRA_MODELS}" ]; then
  echo " Modelos extras:      ${EXTRA_MODELS}"
fi
echo "=========================================================="

afinar_cpu

# ---------------------------------------------------------
# Sobe o servidor Ollama em background
# ---------------------------------------------------------
ollama serve &
OLLAMA_PID=$!

# Aguarda o servidor responder antes de importar/puxar modelos
echo "Aguardando o servidor Ollama iniciar..."
until curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; do
  sleep 1
done
echo "Servidor Ollama pronto."

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

# Um modelo existe no servidor? Aceita "nome" e "nome:latest".
modelo_local() {
  local alvo="$1"
  case "${alvo}" in
    *:*) ;;
    *) alvo="${alvo}:latest" ;;
  esac

  local linha
  while IFS= read -r linha; do
    case "${linha}" in
      "${alvo}") return 0 ;;
    esac
  done < <(ollama list | awk 'NR>1 {print $1}')

  return 1
}

pull_model() {
  local model="$1"
  [ -z "${model}" ] && return 0
  if modelo_local "${model}"; then
    echo "-> Modelo '${model}' já presente, pulando download."
  else
    echo "-> Baixando modelo '${model}'..."
    if ! ollama pull "${model}"; then
      echo "AVISO: falha ao baixar '${model}'. Verifique o nome do modelo/conexão." >&2
    fi
  fi
}

# ---------------------------------------------------------
# Importa TODOS os modelos GGUF montados em ${GGUF_DIR}
# ---------------------------------------------------------
# A pasta models/ pode ter vários .gguf — todos viram modelos do
# Ollama (nome = arquivo sem .gguf). O GGUF_FILE/GGUF_MODEL do .env
# define apenas o modelo PRINCIPAL (o que satisfaz CHAT_MODEL); os
# demais entram como opções no Open WebUI e no Playground.

PRINCIPAL_IMPORTADO=1

# Importa um .gguf se o modelo equivalente ainda não existir.
importar_arquivo() {
  local arquivo="$1" nome="$2"

  if modelo_local "${nome}"; then
    echo "-> Modelo GGUF '${nome}' já importado, pulando criação."
    return 0
  fi

  echo "-> Importando '$(basename "${arquivo}")' como '${nome}'..."
  local modelfile="/tmp/Modelfile.gguf"

  {
    echo "FROM ${arquivo}"
    if [ -n "${GGUF_LICENSE:-}" ]; then
      echo "LICENSE \"${GGUF_LICENSE}\""
    fi
  } > "${modelfile}"

  if ollama create "${nome}" -f "${modelfile}"; then
    echo "-> Modelo '${nome}' pronto."
    return 0
  fi

  echo "AVISO: falha ao importar '${arquivo}'. O container continua no ar." >&2
  return 1
}

importar_todos_ggufs() {
  [ -d "${GGUF_DIR}" ] || {
    echo "-> Diretório ${GGUF_DIR} não existe; nenhum GGUF para importar."
    return 1
  }

  local arquivos arquivo nome principal

  arquivos=$(find "${GGUF_DIR}" -maxdepth 1 -type f -iname '*.gguf' 2>/dev/null | sort)

  if [ -z "${arquivos}" ]; then
    echo "-> Nenhum arquivo .gguf em ${GGUF_DIR}. Pulando importação."
    if [ -n "${GGUF_FILE}" ]; then
      echo "   GGUF_FILE='${GGUF_FILE}' está definido no .env mas o arquivo não existe."
      echo "   Coloque-o em 'models/' (o download pode estar em andamento)."
    else
      echo "   Coloque um .gguf na pasta 'models/' e reinicie os containers."
    fi
    return 1
  fi

  # Qual arquivo satisfaz CHAT_MODEL: GGUF_FILE se existir; senão o
  # primeiro em ordem alfabética. Todos os outros entram com o nome
  # do arquivo (sem extensão).
  if [ -n "${GGUF_FILE}" ] && [ -f "${GGUF_DIR}/${GGUF_FILE}" ]; then
    principal="${GGUF_DIR}/${GGUF_FILE}"
  else
    principal=$(printf '%s\n' "${arquivos}" | head -1)
  fi

  PRINCIPAL_IMPORTADO=1
  while IFS= read -r arquivo; do
    [ -n "${arquivo}" ] || continue
    if [ "${arquivo}" = "${principal}" ]; then
      nome="${GGUF_MODEL:-$(basename "${arquivo}" .gguf)}"
      if importar_arquivo "${arquivo}" "${nome}"; then
        PRINCIPAL_IMPORTADO=0
      fi
    else
      importar_arquivo "${arquivo}" "$(basename "${arquivo}" .gguf)" || true
    fi
  done <<< "${arquivos}"
  return 0
}

importar_todos_ggufs || true

if [ "${PRINCIPAL_IMPORTADO}" -eq 0 ] && modelo_local "${CHAT_MODEL}"; then
  echo "-> Modelo de chat '${CHAT_MODEL}' atendido pelo GGUF local."
else
  pull_model "${CHAT_MODEL}"
fi

pull_model "${EMBEDDING_MODEL}"

# ---------------------------------------------------------
# Variante enxuta do modelo de embeddings
# ---------------------------------------------------------
# OLLAMA_CONTEXT_LENGTH vale para todo modelo servido. Um modelo de
# embeddings, porém, processa trechos curtos: manter 8192 de contexto nele
# só desperdiça VRAM. Ex.: qwen3-embedding:0.6b ocupa ~1,0 GB com 512 de
# contexto e ~2,9 GB com 8192 — nesse tamanho ele deixa de caber sozinho
# na GPU de 6 GB e passa a rodar parte em CPU (bem mais lento no RAG).
EMBEDDING_CONTEXT="${EMBEDDING_CONTEXT:-512}"

preparar_embedding_leve() {
  local base="$1" contexto="$2" variante
  [ -z "${base}" ] && return 0
  if [ -z "${contexto}" ] || [ "${contexto}" -le 0 ] 2>/dev/null; then
    return 0
  fi

  variante="${base}-ctx${contexto}"

  if modelo_local "${variante}"; then
    echo "-> Variante de embeddings '${variante}' já existe."
  else
    echo "-> Criando '${variante}' (contexto ${contexto}) a partir de '${base}'..."
    printf 'FROM %s\nPARAMETER num_ctx %s\n' "${base}" "${contexto}" > /tmp/Modelfile.embed
    if ! ollama create "${variante}" -f /tmp/Modelfile.embed; then
      echo "AVISO: não foi possível criar '${variante}'." >&2
      return 0
    fi
  fi

  echo "   Use '${variante}' como modelo de embeddings para manter a GPU folgada."
}

preparar_embedding_leve "${EMBEDDING_MODEL}" "${EMBEDDING_CONTEXT}"

# ---------------------------------------------------------
# Guardrails e modelos extras
# ---------------------------------------------------------
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
echo " Modelo padrão do Open WebUI: ${CHAT_MODEL}"
echo " GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'N/A')"
echo "=========================================================="

# Mantém o container vivo, seguindo o processo do servidor
wait "${OLLAMA_PID}"
