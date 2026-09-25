# =========================================================
# FIAP - Ollama para uso em sala de aula
# Prompt Engineering & AI - 2o Semestre 2026
# ---------------------------------------------------------
# A imagem oficial detecta em runtime se ha GPU disponivel.
# O build-arg OLLAMA_BASE_IMAGE permite fixar outra tag/base:
#
#   docker build -t fiap-ollama-cpu --build-arg OLLAMA_BASE_IMAGE=ollama/ollama:latest .
#
# O Makefile cuida disso pelos alvos `make build-cpu` / `make build-gpu`.
# =========================================================
ARG OLLAMA_BASE_IMAGE=ollama/ollama:latest
FROM ${OLLAMA_BASE_IMAGE}

ENV OLLAMA_HOST=0.0.0.0 \
    OLLAMA_MODELS=/root/.ollama/models

# curl e usado no healthcheck e no entrypoint para checar se o servidor subiu
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Hash dos arquivos que compoem a imagem, passado pelo Makefile.
# Muda junto com o conteudo dos fontes e invalida o cache do Docker;
# tambem alimenta `make stale`, que compara o selo com o hash atual.
ARG FIAP_BUILD_SHA=dev
LABEL br.fiap.fontes.sha256="${FIAP_BUILD_SHA}"

WORKDIR /root

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 11434

ENTRYPOINT ["/entrypoint.sh"]
