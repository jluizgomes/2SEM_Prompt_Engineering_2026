# ============================================================
# FIAP AI Lab — mem0 (memória de longo prazo para agentes)
# ------------------------------------------------------------
# A imagem oficial mem0/mem0-api-server só existe para linux/arm64,
# então empacotamos a biblioteca `mem0ai` com um servidor FastAPI
# próprio (app.py), pré-configurado para Ollama + Postgres/pgvector.
# ============================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# libpq5 é a runtime do psycopg2-binary; curl serve ao healthcheck.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl libpq5 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Versões pinadas: o lab inteiro precisa ser reprodutível entre as aulas.
RUN pip install --no-cache-dir \
      "mem0ai==2.0.18" \
      "fastapi==0.121.2" \
      "uvicorn[standard]==0.41.0" \
      "psycopg2-binary==2.9.11" \
      "ollama==0.6.2" \
      "httpx==0.28.1"

COPY app.py /app/app.py

# Histórico de operações do mem0 (SQLite). Fica em volume para
# sobreviver a rebuilds — o conteúdo semântico vai para o Postgres.
RUN mkdir -p /app/history

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=10 --start-period=30s \
  CMD curl -sf http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
