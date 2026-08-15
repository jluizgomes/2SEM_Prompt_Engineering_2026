# ============================================================
# FIAP AI Lab — Postgres unificado
# ------------------------------------------------------------
# Um único banco para TODAS as stacks do lab:
#
#   postgres   → filas NuQ do Firecrawl (exige pg_cron)
#   openwebui  → contas, chats e configurações do Open WebUI
#   mem0       → memórias do mem0 (tabelas pgvector)
#
# Base: pgvector/pgvector:pg17 (= postgres:17 + extensão vector).
# Em cima dela instalamos o pg_cron e o schema da fila do Firecrawl,
# que normalmente viriam da imagem própria deles
# (ghcr.io/firecrawl/nuq-postgres). Fazemos aqui para não subir dois
# Postgres diferentes — o professor pediu um banco unificado.
# ============================================================
ARG PG_MAJOR=17
FROM pgvector/pgvector:pg${PG_MAJOR}

# ARG declarado de novo: o valor definido antes do FROM não atravessa
# o estágio de build automaticamente.
ARG PG_MAJOR=17

# Versão do Firecrawl da qual vem o schema da fila. Precisa ser a MESMA
# usada na imagem ghcr.io/firecrawl/firecrawl do docker-compose.yml —
# schema e aplicação evoluem juntos.
# Atenção: a tag da IMAGEM é "2.11.14" e a tag do GIT é "v2.11.14";
# o "v" é acrescentado só na URL abaixo.
ARG FIRECRAWL_VERSION=2.11.14

# ------------------------------------------------------------
# pg_cron — usado pelo NuQ (fila do Firecrawl) para expirar jobs
# ------------------------------------------------------------
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends postgresql-${PG_MAJOR}-cron; \
    rm -rf /var/lib/apt/lists/*

# shared_preload_libraries precisa estar valendo ANTES do primeiro start
# do servidor. Os scripts de /docker-entrypoint-initdb.d rodam depois,
# então a alteração vai no template de configuração usado pelo initdb.
RUN set -eux; \
    conf="/usr/share/postgresql/${PG_MAJOR}/postgresql.conf.sample"; \
    sed -ri "s/^#?shared_preload_libraries\s*=.*/shared_preload_libraries = 'pg_cron'/" "$conf"; \
    printf "\n# pg_cron (fila NuQ do Firecrawl)\ncron.database_name = 'postgres'\n" >> "$conf"

# ------------------------------------------------------------
# Scripts de inicialização (rodam só quando o volume está vazio)
#   000 → cria os bancos openwebui e mem0 + extensão vector
#   010 → schema da fila NuQ, baixado da tag pinada do Firecrawl
# ------------------------------------------------------------
COPY --chmod=0755 init/000-databases.sh /docker-entrypoint-initdb.d/000-databases.sh
ADD  --chmod=0644 \
     https://raw.githubusercontent.com/firecrawl/firecrawl/v${FIRECRAWL_VERSION}/apps/nuq-postgres/nuq.sql \
     /docker-entrypoint-initdb.d/010-nuq.sql
