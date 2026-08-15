#!/bin/bash
# ============================================================
# FIAP AI Lab — criação dos bancos das stacks
# Roda uma única vez, no primeiro boot (volume vazio).
#
# O banco padrão ($POSTGRES_DB, normalmente "postgres") fica com a
# fila NuQ do Firecrawl, criada pelo 010-nuq.sql logo depois deste
# script. Aqui criamos os bancos das outras stacks.
# ============================================================
set -euo pipefail

EXTRA_DBS="${EXTRA_DATABASES:-openwebui mem0}"

echo "[init] criando bancos das stacks: ${EXTRA_DBS}"

for db in ${EXTRA_DBS}; do
  # CREATE DATABASE não aceita IF NOT EXISTS; o SELECT evita o erro
  # caso alguém reexecute o script manualmente.
  if psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" \
       -tAc "SELECT 1 FROM pg_database WHERE datname = '${db}'" | grep -q 1; then
    echo "[init] banco '${db}' já existe"
  else
    psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" \
      -c "CREATE DATABASE ${db} OWNER ${POSTGRES_USER}"
    echo "[init] banco '${db}' criado"
  fi
done

# A extensão vector é por banco, não por cluster: precisa ser criada em
# cada um. O mem0 usa no banco 'mem0'; nos demais fica disponível para
# experimentos das aulas de RAG.
for db in "${POSTGRES_DB}" ${EXTRA_DBS}; do
  psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${db}" \
    -c "CREATE EXTENSION IF NOT EXISTS vector"
  echo "[init] extensão vector pronta em '${db}'"
done

echo "[init] Postgres unificado pronto."
