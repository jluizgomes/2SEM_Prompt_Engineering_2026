#!/bin/bash
# =========================================================
# FIAP - Entrypoint do Ollama
# Sobe o servidor Ollama, importa TODOS os modelos GGUF locais
# (pasta models/) e garante que os modelos padrao da disciplina
# estejam disponiveis.
# Funciona em CPU ou GPU: a imagem oficial detecta o hardware.
#
# Variaveis lidas do ambiente (todas vindas do .env via Compose):
#   CHAT_MODEL        modelo de chat padrao do Open WebUI
#   EMBEDDING_MODEL   modelo de embeddings do RAG
#   EMBEDDING_CONTEXT contexto da variante enxuta de embeddings
#   GUARDRAIL_MODELS  modelos de guardrail, separados por virgula
#   EXTRA_MODELS      modelos extras, separados por virgula
#   GGUF_DIR          pasta montada com os .gguf (read-only)
#   GGUF_FILE         .gguf que satisfaz CHAT_MODEL
#   GGUF_MODEL        nome do modelo principal (padrao: nome do arquivo)
#   GGUF_LICENSE      licenca declarada no Modelfile (opcional)
# =========================================================
set -e

CHAT_MODEL="${CHAT_MODEL:-qwen3.5:0.8b}"
# Modelo de reserva usado quando o .gguf de CHAT_MODEL nao esta na
# pasta models/. Vazio = apenas avisa e nao baixa nada.
CHAT_MODEL_FALLBACK="${CHAT_MODEL_FALLBACK:-}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding:0.6b}"
# Guardrails para demonstracao:
# - Llama Guard 3 1B Q4_K_M: ~955 MB, PT-BR suportado
# - Granite Guardian 3.0 2B: ~2,7 GB
GUARDRAIL_MODELS="${GUARDRAIL_MODELS:-llama-guard3:1b-q4_K_M,granite3-guardian:2b}"
EXTRA_MODELS="${EXTRA_MODELS:-}"
GGUF_DIR="${GGUF_DIR:-/models}"
GGUF_FILE="${GGUF_FILE:-}"
GGUF_MODEL="${GGUF_MODEL:-}"

# Ha GPU NVIDIA de verdade disponivel neste container?
tem_gpu_nvidia() {
  [ -e /dev/nvidia0 ] || [ -e /dev/nvidiactl ]
}

if tem_gpu_nvidia; then
  MODO="GPU (NVIDIA)"
else
  MODO="CPU"
fi

echo "=========================================================="
echo " FIAP AI Lab - Iniciando servidor Ollama (${MODO})"
echo " Modelo de chat:      ${CHAT_MODEL}"
echo " Modelo de embedding: ${EMBEDDING_MODEL}"
echo " Guardrails:          ${GUARDRAIL_MODELS:-(nenhum)}"
if [ -n "${EXTRA_MODELS}" ]; then
  echo " Modelos extras:      ${EXTRA_MODELS}"
fi
echo " Diretorio de GGUF:   ${GGUF_DIR}"
echo "=========================================================="

# ---------------------------------------------------------
# Ajuste de performance em CPU
# ---------------------------------------------------------

# Quantos nucleos fisicos a maquina tem (sem contar hyperthreading).
# Conta pares unicos (physical id, core id) em /proc/cpuinfo.
nucleos_fisicos() {
  grep -E '^(physical id|core id)' /proc/cpuinfo 2>/dev/null \
    | sed 's/^[[:space:]]*//' \
    | awk '{print $NF}' \
    | paste - - \
    | sort -u \
    | grep -c .
}

# Quantos threads o processo pode usar (respeita cgroup/cpuset do container).
threads_disponiveis() {
  nproc 2>/dev/null || grep -c '^processor' /proc/cpuinfo 2>/dev/null || echo 0
}

# Detecta quantos nucleos de alta performance (P-cores) usar em CPUs
# hibridas Intel. Agrupa os nucleos fisicos por frequencia maxima: os
# P-cores ficam nos bins de turbo mais altos e os E-cores num bin baixo.
# Usa /sys quando exposto; senao cai para o total de nucleos fisicos.
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
      if (maxf == minf) { exit 1 }   # CPU homogenea: nao ha P/E cores
      # nucleos cuja frequencia esta no topo (tolerancia p/ bins de turbo)
      limiar = maxf * 0.9
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
    # Nunca pedir mais threads do que os CPUs disponiveis.
    if [ -n "${threads}" ] && [ "${threads}" -gt 0 ] 2>/dev/null; then
      if [ -z "${sugerido}" ] || [ "${sugerido}" -gt "${threads}" ] 2>/dev/null; then
        sugerido="${threads}"
      fi
    fi
    if [ -n "${sugerido}" ] && [ "${sugerido}" -gt 0 ] 2>/dev/null; then
      export OLLAMA_NUM_THREADS="${sugerido}"
      echo "-> OLLAMA_NUM_THREADS nao definido; usando ${sugerido}."
    fi
  fi

  echo "----------------------------------------------------------"
  echo " Perfil de performance (${MODO})"
  echo "   threads de inferencia : ${OLLAMA_NUM_THREADS:-auto}"
  echo "   CPUs disponiveis      : ${threads:-?} (nucleos fisicos: ${fisicos:-?}, p-cores: ${pcores:-n/d})"
  echo "   paralelismo           : ${OLLAMA_NUM_PARALLEL:-auto}"
  echo "   modelos residentes    : ${OLLAMA_MAX_LOADED_MODELS:-auto}"
  echo "   contexto por modelo   : ${OLLAMA_CONTEXT_LENGTH:-auto}"
  echo "   keep_alive            : ${OLLAMA_KEEP_ALIVE:-auto}"
  echo "=========================================================="
}

# ---------------------------------------------------------
# Sobe o servidor Ollama em background
# ---------------------------------------------------------
afinar_cpu

ollama serve &
OLLAMA_PID=$!

# Aguarda o servidor responder antes de importar/baixar modelos
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
# Baixa da biblioteca publica, se ainda nao existir.
pull_model() {
  local modelo="$1"
  [ -z "${modelo}" ] && return 0
  if modelo_local "${modelo}"; then
    echo "-> Modelo '${modelo}' ja presente, pulando download."
  else
    echo "-> Baixando modelo '${modelo}'..."
    if ! ollama pull "${modelo}"; then
      echo "AVISO: falha ao baixar '${modelo}'. Verifique o nome do modelo/conexao." >&2
    fi
  fi
}

# O nome do modelo de chat vem da biblioteca publica? Todo modelo da
# biblioteca tem TAG (qwen3:0.6b). Um nome sem tag (MiniCPM5-2B-...)
# so pode existir localmente, vindo de um .gguf: nao adianta tentar
# baixar da biblioteca.
chat_da_biblioteca() {
  case "${CHAT_MODEL}" in
    *:*) return 0 ;;
    *)   return 1 ;;
  esac
}

# Baixa uma lista separada por virgula (guardrails, modelos extras).
pull_lista() {
  local lista="$1" item
  [ -z "${lista}" ] && return 0
  local IFS=,
  for item in ${lista}; do
    item="$(echo "${item}" | xargs)"
    [ -n "${item}" ] && pull_model "${item}"
  done
  return 0
}

# ---------------------------------------------------------
# Importacao dos GGUF montados em ${GGUF_DIR}
# ---------------------------------------------------------
# A pasta models/ pode ter varios .gguf: TODOS viram modelos do
# Ollama (nome = arquivo sem .gguf). GGUF_FILE/GGUF_MODEL definem
# apenas o modelo PRINCIPAL, o que satisfaz CHAT_MODEL; os demais
# entram como opcoes no Open WebUI.

PRINCIPAL_IMPORTADO=1

# Importa um .gguf se o modelo equivalente ainda nao existir.
importar_arquivo() {
  local arquivo="$1" nome="$2"

  if modelo_local "${nome}"; then
    echo "-> Modelo GGUF '${nome}' ja importado, pulando criacao."
    return 0
  fi

  echo "-> Importando '$(basename "${arquivo}")' como '${nome}'..."
  local modelfile="/tmp/Modelfile.gguf"

  {
    echo "FROM ${arquivo}"
    # Licenca declarada opcionalmente via GGUF_LICENSE no .env
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

# Nome do modelo principal: GGUF_MODEL > nome do arquivo sem .gguf
principal_de() {
  if [ -n "${GGUF_MODEL}" ]; then
    printf '%s' "${GGUF_MODEL}"
  else
    basename "$1" .gguf
  fi
}

importar_todos_ggufs() {
  if [ ! -d "${GGUF_DIR}" ]; then
    echo "-> Diretorio ${GGUF_DIR} nao existe; nenhum GGUF para importar."
    return 1
  fi

  local arquivos
  arquivos=$(find "${GGUF_DIR}" -maxdepth 1 -type f -iname '*.gguf' 2>/dev/null | sort)

  if [ -z "${arquivos}" ]; then
    echo "-> Nenhum arquivo .gguf em ${GGUF_DIR}. Pulando importacao."
    if [ -n "${GGUF_FILE}" ]; then
      echo "   GGUF_FILE='${GGUF_FILE}' esta definido no .env mas o arquivo nao existe."
      echo "   Coloque-o em 'models/' (o download ainda pode estar em andamento)."
    else
      echo "   Coloque um .gguf na pasta 'models/' do projeto e reinicie os containers."
    fi
    return 1
  fi

  # Qual arquivo satisfaz CHAT_MODEL: GGUF_FILE se existir; senao o
  # primeiro em ordem alfabetetica (com aviso quando houver varios).
  local principal
  if [ -n "${GGUF_FILE}" ] && [ -f "${GGUF_DIR}/${GGUF_FILE}" ]; then
    principal="${GGUF_DIR}/${GGUF_FILE}"
  else
    principal=$(printf '%s\n' "${arquivos}" | head -1)
    if [ "$(printf '%s\n' "${arquivos}" | grep -c .)" -gt 1 ] && [ -n "${GGUF_FILE}" ]; then
      echo "AVISO: GGUF_FILE='${GGUF_FILE}' nao existe em ${GGUF_DIR};" \
           "usando '$(basename "${principal}")' como modelo principal." >&2
    fi
  fi

  local total
  total=$(printf '%s\n' "${arquivos}" | grep -c .)
  echo "-> ${total} arquivo(s) .gguf em ${GGUF_DIR}; importando."

  PRINCIPAL_IMPORTADO=1
  local arquivo nome
  while IFS= read -r arquivo; do
    [ -n "${arquivo}" ] || continue
    if [ "${arquivo}" = "${principal}" ]; then
      nome=$(principal_de "${arquivo}")
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

# ---------------------------------------------------------
# Modelo de chat
# ---------------------------------------------------------
# Nenhum .gguf e um estado valido: o stack sobe, o servidor Ollama
# funciona e o Open WebUI abre. Nenhum erro, nenhuma saida abortada.
if [ "${PRINCIPAL_IMPORTADO}" -eq 0 ] && modelo_local "${CHAT_MODEL}"; then
  echo "-> Modelo de chat '${CHAT_MODEL}' atendido pelo GGUF local."
else
  if chat_da_biblioteca; then
    # Tem tag: e um modelo da biblioteca, pode ser baixado.
    pull_model "${CHAT_MODEL}"
  else
    # Sem tag: o modelo de chat pretendido e local (vem de models/).
    echo "-> Modelo de chat '${CHAT_MODEL}' NAO esta disponivel:"
    if [ -n "${GGUF_FILE}" ]; then
      echo "   o .gguf '${GGUF_FILE}' nao esta em '${GGUF_DIR}' (montada read-only no container)."
    else
      echo "   a pasta '${GGUF_DIR}' nao tem nenhum .gguf."
    fi
    echo "   Copie o arquivo para a pasta models/ do projeto e rode 'make restart',"
    echo "   ou aponte GGUF_FILE/GGUF_MODEL/CHAT_MODEL no .env para o arquivo correto."
    if [ -n "${CHAT_MODEL_FALLBACK}" ]; then
      echo "   CHAT_MODEL_FALLBACK='${CHAT_MODEL_FALLBACK}': baixando o modelo de reserva..."
      pull_model "${CHAT_MODEL_FALLBACK}"
    else
      echo "   Sem CHAT_MODEL_FALLBACK no .env: nada foi baixado. O servidor sobe assim mesmo;"
      echo "   use 'make pull M=<modelo-da-biblioteca>' se precisar de um chat agora."
    fi
  fi
fi

pull_model "${EMBEDDING_MODEL}"

# ---------------------------------------------------------
# Variante enxuta do modelo de embeddings
# ---------------------------------------------------------
# OLLAMA_CONTEXT_LENGTH vale para todo modelo servido. Um modelo
# de embeddings, porem, processa trechos curtos: manter 8192 de
# contexto nele so desperdica RAM/VRAM. Ex.: qwen3-embedding:0.6b
# ocupa ~1,0 GB com 512 de contexto e ~2,9 GB com 8192. A variante
# <modelo>-ctx<contexto> e o que o Open WebUI usa no RAG
# (ver RAG_EMBEDDING_MODEL no docker-compose.yml).
EMBEDDING_CONTEXT="${EMBEDDING_CONTEXT:-512}"
EMBEDDING_VARIANT=""

preparar_embedding_leve() {
  local base="$1" contexto="$2" variante
  [ -z "${base}" ] && return 0
  if [ -z "${contexto}" ] || [ "${contexto}" -le 0 ] 2>/dev/null; then
    return 0
  fi

  variante="${base}-ctx${contexto}"
  EMBEDDING_VARIANT="${variante}"

  if modelo_local "${variante}"; then
    echo "-> Variante de embeddings '${variante}' ja existe."
  else
    echo "-> Criando '${variante}' (contexto ${contexto}) a partir de '${base}'..."
    printf 'FROM %s\nPARAMETER num_ctx %s\n' "${base}" "${contexto}" > /tmp/Modelfile.embed
    if ! ollama create "${variante}" -f /tmp/Modelfile.embed; then
      echo "AVISO: nao foi possivel criar '${variante}'." >&2
      EMBEDDING_VARIANT=""
      return 0
    fi
  fi

  echo "   O RAG do Open WebUI usa '${variante}' para manter a memoria folgada."
}

preparar_embedding_leve "${EMBEDDING_MODEL}" "${EMBEDDING_CONTEXT}"

# ---------------------------------------------------------
# Guardrails e modelos extras
# ---------------------------------------------------------
pull_lista "${GUARDRAIL_MODELS}"
pull_lista "${EXTRA_MODELS}"

echo "=========================================================="
echo " Modelos disponiveis:"
ollama list
echo "=========================================================="
echo " Modelo padrao do Open WebUI: ${CHAT_MODEL}"
echo " Embeddings do RAG:           ${EMBEDDING_VARIANT:-${EMBEDDING_MODEL}}"
echo " FIAP AI Lab pronto. Servidor Ollama rodando em :11434"
echo "=========================================================="

# Mantem o container vivo, seguindo o processo do servidor
wait "${OLLAMA_PID}"

