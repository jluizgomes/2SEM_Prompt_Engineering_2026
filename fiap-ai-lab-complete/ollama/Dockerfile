# =========================================================
# FIAP AI Lab — Ollama + Guardrails com GPU para uso em sala de aula
# Baseado na imagem oficial mais recente do Ollama (0.32.x+)
# Suporta NVIDIA GPU via CUDA (RTX 3060, etc.)
# =========================================================
FROM ollama/ollama:latest

# Habilita GPU — NÃO definir CUDA_VISIBLE_DEVICES vazio.
# O Ollama detecta automaticamente a GPU via NVIDIA Container Toolkit.
ENV OLLAMA_HOST=0.0.0.0 \
    OLLAMA_MODELS=/root/.ollama/models

# curl é usado no healthcheck e no entrypoint para checar se o servidor subiu
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 11434

ENTRYPOINT ["/entrypoint.sh"]
