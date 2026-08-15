# ============================================================
# FIAP AI Lab — Atalhos do stack Docker
# Prompt Engineering & AI · 2º Semestre 2026
#
#   make setup         cria o .env com segredos aleatórios
#   make up            sobe o perfil complete (padrão)
#   make up-minimum    sobe só postgres + ollama + open-webui
#   make up-rag        sobe a base + ChromaDB
#   make up-search     sobe a base + SearXNG
#   make up-memory     sobe a base + mem0
#   make up-crawl      sobe a base + Firecrawl
#   make up-langfuse   sobe a base + Langfuse self-hosted (observabilidade)
#   make down          derruba tudo
#   make help          lista todos os alvos
# ============================================================

# Carrega o .env (se existir) para que os alvos de URL/health usem
# as portas realmente configuradas, e não só os valores padrão.
-include .env
export

COMPOSE      := docker compose
ALL_PROFILES := --profile minimum --profile complete --profile rag \
                --profile search --profile memory --profile crawl \
                --profile langfuse
ALL          := $(COMPOSE) $(ALL_PROFILES)
COMPLETE     := $(COMPOSE) --profile complete
MINIMUM      := $(COMPOSE) --profile minimum

.DEFAULT_GOAL := help
.PHONY: help setup build build-minimum up up-minimum up-complete up-rag up-search \
        up-memory up-crawl up-langfuse down down-volumes restart ps logs logs-ollama \
        logs-webui logs-searxng logs-chromadb logs-mem0 logs-firecrawl logs-pipelines \
        logs-postgres logs-langfuse health test test-net models pull psql databases \
        shell-ollama shell-postgres config urls clean

# ------------------------------------------------------------
# Ajuda
# ------------------------------------------------------------
help:
	@echo ""
	@echo "FIAP AI Lab — alvos disponíveis"
	@echo "------------------------------------------------------------"
	@echo "  setup           Cria .env a partir do .env.example com segredos aleatórios"
	@echo "  build           Constrói as imagens do perfil complete"
	@echo "  build-minimum   Constrói apenas as imagens do perfil minimum"
	@echo ""
	@echo "  up              Sobe o perfil COMPLETE (todas as stacks integradas)"
	@echo "  up-minimum      postgres + ollama + open-webui"
	@echo "  up-rag          base + ChromaDB          (RAG)"
	@echo "  up-search       base + SearXNG + Valkey  (busca web)"
	@echo "  up-memory       base + mem0              (memória de longo prazo)"
	@echo "  up-crawl        base + Firecrawl         (crawling e extração)"
	@echo "  up-langfuse     base + Langfuse          (observabilidade de traces)"
	@echo "                  Perfis somam: make up-rag && make up-memory"
	@echo ""
	@echo "  down            Derruba os containers de todos os perfis"
	@echo "  down-volumes    Derruba e APAGA os volumes (modelos, chats, banco, vetores)"
	@echo "  restart         down + up complete"
	@echo ""
	@echo "  ps              Status dos containers"
	@echo "  urls            URLs de tudo que está no ar"
	@echo "  logs            Logs de todos os serviços (follow)"
	@echo "  logs-ollama | logs-webui | logs-searxng | logs-chromadb"
	@echo "  logs-mem0 | logs-firecrawl | logs-pipelines | logs-postgres"
	@echo "  logs-langfuse"
	@echo "  health          Testa os endpoints publicados de cada serviço"
	@echo "  test            Teste de integração ponta a ponta (do seu computador)"
	@echo "  test-net        Mesmo teste, porém de dentro da rede fiap-ai-net"
	@echo ""
	@echo "  models          Lista os modelos baixados no Ollama"
	@echo "  pull M=nome     Baixa um modelo (ex: make pull M=qwen3:8b)"
	@echo "  databases       Lista os bancos do Postgres unificado"
	@echo "  psql            Abre o psql no Postgres unificado"
	@echo "  shell-ollama | shell-postgres   Abre shell no container"
	@echo "  config          Valida o docker-compose.yml de TODOS os perfis"
	@echo ""

# ------------------------------------------------------------
# Setup inicial
# ------------------------------------------------------------
setup:
	@if [ -f .env ]; then \
		echo ".env já existe — nada alterado."; \
	else \
		cp .env.example .env; \
		WEBUI_KEY=$$(openssl rand -hex 32); \
		SEARX_KEY=$$(openssl rand -hex 32); \
		LF_SALT=$$(openssl rand -hex 32); \
		LF_ENC=$$(openssl rand -hex 32); \
		LF_AUTH=$$(openssl rand -hex 32); \
		LF_PK=pk-lf-$$(uuidgen | tr 'A-Z' 'a-z'); \
		LF_SK=sk-lf-$$(uuidgen | tr 'A-Z' 'a-z'); \
		sed -i.bak "s|^WEBUI_SECRET_KEY=.*|WEBUI_SECRET_KEY=$$WEBUI_KEY|" .env; \
		sed -i.bak "s|^SEARXNG_SECRET=.*|SEARXNG_SECRET=$$SEARX_KEY|" .env; \
		sed -i.bak "s|^LANGFUSE_SALT=.*|LANGFUSE_SALT=$$LF_SALT|" .env; \
		sed -i.bak "s|^LANGFUSE_ENCRYPTION_KEY=.*|LANGFUSE_ENCRYPTION_KEY=$$LF_ENC|" .env; \
		sed -i.bak "s|^LANGFUSE_NEXTAUTH_SECRET=.*|LANGFUSE_NEXTAUTH_SECRET=$$LF_AUTH|" .env; \
		sed -i.bak "s|^LANGFUSE_PUBLIC_KEY=.*|LANGFUSE_PUBLIC_KEY=$$LF_PK|" .env; \
		sed -i.bak "s|^LANGFUSE_SECRET_KEY=.*|LANGFUSE_SECRET_KEY=$$LF_SK|" .env; \
		rm -f .env.bak; \
		echo ".env criado com WEBUI_SECRET_KEY, SEARXNG_SECRET e os segredos"; \
		echo "do Langfuse aleatórios (SALT, ENCRYPTION_KEY, NEXTAUTH_SECRET e o"; \
		echo "par pk-lf-/sk-lf-). Anote as duas chaves: são elas que o código"; \
		echo "das aulas usa no SDK."; \
	fi

# ------------------------------------------------------------
# Build
# ------------------------------------------------------------
build:
	$(COMPLETE) build

build-minimum:
	$(MINIMUM) build

# ------------------------------------------------------------
# Subir / derrubar
# ------------------------------------------------------------
up: up-complete

up-complete: setup
	$(COMPLETE) up -d --build
	@$(MAKE) --no-print-directory urls
	@echo "O primeiro boot baixa os modelos — acompanhe com 'make logs-ollama'."

up-minimum: setup
	$(MINIMUM) up -d --build
	@$(MAKE) --no-print-directory urls

# Stacks individuais. Cada uma sobe junto a base (postgres, ollama,
# open-webui, pipelines, chromadb), então o Open WebUI está sempre
# no ar e já configurado.
up-rag: setup
	$(COMPOSE) --profile rag up -d --build
	@$(MAKE) --no-print-directory urls

up-search: setup
	$(COMPOSE) --profile search up -d --build
	@$(MAKE) --no-print-directory urls

up-memory: setup
	$(COMPOSE) --profile memory up -d --build
	@$(MAKE) --no-print-directory urls

up-crawl: setup
	$(COMPOSE) --profile crawl up -d --build
	@$(MAKE) --no-print-directory urls

# Langfuse fica fora do perfil complete: são 5 containers a mais e
# ~5 GB de RAM. Para usar junto, some os perfis:
#   docker compose --profile complete --profile langfuse up -d
up-langfuse: setup
	@if [ -z "$${LANGFUSE_ENCRYPTION_KEY}" ] || \
	    [ "$${LANGFUSE_ENCRYPTION_KEY}" = "troque-por-openssl-rand-hex-32" ]; then \
		echo ""; \
		echo "LANGFUSE_ENCRYPTION_KEY não configurada no .env."; \
		echo "Gere com: openssl rand -hex 32   (idem SALT e NEXTAUTH_SECRET)"; \
		echo ""; \
		exit 1; \
	fi
	$(COMPOSE) --profile langfuse up -d --build
	@echo "O langfuse-web roda as migrações de Postgres e ClickHouse no boot —"
	@echo "o primeiro start leva alguns minutos. Acompanhe: make logs-langfuse"
	@$(MAKE) --no-print-directory urls

down:
	$(ALL) down --remove-orphans

# ATENÇÃO: apaga modelos baixados, contas e chats do Open WebUI,
# o banco Postgres inteiro, as coleções do ChromaDB, as memórias
# do mem0, o cache do SearXNG e os traces do Langfuse.
down-volumes:
	$(ALL) down -v --remove-orphans

restart: down up-complete

# ------------------------------------------------------------
# Observabilidade
# ------------------------------------------------------------
ps:
	$(ALL) ps

urls:
	@echo ""
	@echo "No ar agora:"
	@docker ps --filter "network=fiap-ai-net" --format '  {{.Names}}\t{{.Ports}}' \
		| sed 's|0.0.0.0:|localhost:|g'
	@echo ""
	@echo "  Open WebUI   http://localhost:$${WEBUI_PORT:-3000}"
	@echo "  Ollama       http://localhost:$${OLLAMA_PORT:-11434}"
	@echo "  ChromaDB     http://localhost:$${CHROMADB_PORT:-8000}"
	@echo "  Pipelines    http://localhost:$${PIPELINES_PORT:-9099}"
	@echo "  SearXNG      http://localhost:$${SEARXNG_PORT:-8080}"
	@echo "  mem0         http://localhost:$${MEM0_PORT:-8100}/docs"
	@echo "  Firecrawl    http://localhost:$${FIRECRAWL_PORT:-3002}"
	@echo "  RabbitMQ UI  http://localhost:$${RABBITMQ_UI_PORT:-15672}  (guest/guest)"
	@echo "  Langfuse     http://localhost:$${LANGFUSE_PORT:-3001}"
	@echo "  MinIO (LF)   http://localhost:$${LANGFUSE_MINIO_CONSOLE_PORT:-9091}"
	@echo "  Postgres     localhost:$${POSTGRES_HOST_PORT:-5432}"
	@echo ""

logs:
	$(ALL) logs -f --tail=100

logs-ollama:
	$(ALL) logs -f --tail=100 ollama

logs-webui:
	$(ALL) logs -f --tail=100 open-webui open-webui-full

logs-searxng:
	$(ALL) logs -f --tail=100 searxng

logs-chromadb:
	$(ALL) logs -f --tail=100 chromadb

logs-mem0:
	$(ALL) logs -f --tail=100 mem0

logs-firecrawl:
	$(ALL) logs -f --tail=100 firecrawl-api firecrawl-playwright

logs-pipelines:
	$(ALL) logs -f --tail=100 pipelines

logs-postgres:
	$(ALL) logs -f --tail=100 postgres

# O `web` loga as migrações no início: se elas falharem, nada indexa.
logs-langfuse:
	$(ALL) logs -f --tail=100 \
		langfuse-web langfuse-worker \
		langfuse-clickhouse langfuse-redis langfuse-minio

health:
	@echo "Postgres:"
	@docker exec fiap-postgres pg_isready -U $${POSTGRES_USER:-fiap} >/dev/null 2>&1 && echo "  OK" || echo "  FALHOU"
	@echo "Ollama:"
	@curl -sf http://localhost:$${OLLAMA_PORT:-11434}/api/tags  >/dev/null && echo "  OK" || echo "  FALHOU"
	@echo "Open WebUI:"
	@curl -sf http://localhost:$${WEBUI_PORT:-3000}/health      >/dev/null && echo "  OK" || echo "  FALHOU"
	@echo "ChromaDB:"
	@curl -sf http://localhost:$${CHROMADB_PORT:-8000}/api/v2/heartbeat >/dev/null && echo "  OK" || echo "  fora do ar (normal no perfil minimum)"
	@echo "Pipelines:"
	@curl -sf http://localhost:$${PIPELINES_PORT:-9099}/health  >/dev/null && echo "  OK" || echo "  fora do ar (normal no perfil minimum)"
	@echo "SearXNG:"
	@curl -sf http://localhost:$${SEARXNG_PORT:-8080}/healthz   >/dev/null && echo "  OK" || echo "  fora do ar (perfis complete/search)"
	@echo "mem0:"
	@curl -sf http://localhost:$${MEM0_PORT:-8100}/health       >/dev/null && echo "  OK" || echo "  fora do ar (perfis complete/memory)"
	@echo "Firecrawl:"
	@curl -sf http://localhost:$${FIRECRAWL_PORT:-3002}/        >/dev/null && echo "  OK" || echo "  fora do ar (perfis complete/crawl)"
	@echo "Langfuse:"
	@curl -sf http://localhost:$${LANGFUSE_PORT:-3001}/api/public/health >/dev/null && echo "  OK" || echo "  fora do ar (perfil langfuse)"

# Integração real entre as stacks, vista do SEU computador.
# Só usa a biblioteca padrão do Python — não precisa instalar nada.
test:
	python3 scripts/integration_test.py

# Mesmo teste, porém de dentro da rede fiap-ai-net: valida os
# hostnames internos (ollama, chromadb, mem0, firecrawl-api...),
# que é como o código das aulas vai enxergar os serviços.
test-net:
	docker run --rm --network fiap-ai-net \
		-v "$(PWD)/scripts:/scripts:ro" \
		-e IN_DOCKER_NETWORK=1 \
		python:3.12-slim python /scripts/integration_test.py

# ------------------------------------------------------------
# Modelos
# ------------------------------------------------------------
models:
	docker exec -it fiap-ollama ollama list

# Uso: make pull M=qwen3:8b
pull:
	@if [ -z "$(M)" ]; then echo "Informe o modelo: make pull M=qwen3:8b"; exit 1; fi
	docker exec -it fiap-ollama ollama pull $(M)

# ------------------------------------------------------------
# Banco unificado
# ------------------------------------------------------------
databases:
	@docker exec -it fiap-postgres psql -U $${POSTGRES_USER:-fiap} -d $${POSTGRES_DB:-postgres} \
		-c "\l" -c "SELECT extname FROM pg_extension ORDER BY 1"

psql:
	docker exec -it fiap-postgres psql -U $${POSTGRES_USER:-fiap} -d $${POSTGRES_DB:-postgres}

# ------------------------------------------------------------
# Acesso aos containers
# ------------------------------------------------------------
shell-ollama:
	docker exec -it fiap-ollama bash

shell-postgres:
	docker exec -it fiap-postgres bash

# ------------------------------------------------------------
# Validação
# ------------------------------------------------------------
config:
	@for p in minimum complete rag search memory crawl langfuse; do \
		$(COMPOSE) --profile $$p config >/dev/null && echo "perfil $$p: OK"; \
	done

clean: down
	docker image rm fiap-ollama-cpu:latest fiap-mem0:latest fiap-postgres:latest 2>/dev/null || true
