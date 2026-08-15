# =========================================================
# FIAP AI Lab — Ollama + Guardrails (CPU only) para uso em sala de aula
# Baseado na imagem oficial mais recente do Ollama
# =========================================================
FROM ollama/ollama:latest

# Garante que o container rode apenas em CPU (sem CUDA/ROCm).
# Os guardrails são baixados pelo entrypoint e compartilham o mesmo Ollama.
ENV OLLAMA_HOST=0.0.0.0 \
    OLLAMA_MODELS=/root/.ollama/models \
    CUDA_VISIBLE_DEVICES="" \
    HIP_VISIBLE_DEVICES=""

# curl é usado no healthcheck e no entrypoint para checar se o servidor subiu
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 11434

ENTRYPOINT ["/entrypoint.sh"]
