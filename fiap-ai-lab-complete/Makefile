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
.PHONY: help setup check-prereqs check-langfuse-env build build-minimum up up-minimum \
        up-complete up-rag up-search up-memory up-crawl up-langfuse \
        up-complete-langfuse _up-langfuse validate-langfuse langfuse-ollama down \
        down-volumes restart ps logs logs-ollama logs-webui logs-searxng \
        logs-chromadb logs-mem0 logs-firecrawl logs-pipelines logs-postgres \
        logs-langfuse health test test-unit test-net models pull psql databases \
        shell-ollama shell-postgres config urls clean gguf models-dir \
        gguf-import searxng-engines restart-searxng

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
	@echo "  up-complete-langfuse  stack completo + Langfuse"
	@echo "  check-langfuse-env     valida todos os secrets e endpoints do .env"
	@echo "  validate-langfuse      valida serviços, conexão, traces e score configs"
	@echo "                  Perfis somam: make up-rag && make up-memory"
	@echo "  langfuse-ollama (re)cria a LLM connection do Ollama no Langfuse —"
	@echo "                  Playground e LLM-as-a-judge ganham os modelos"
	@echo "                  + semeia os score configs de avaliação da aula"
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
	@echo "  test-unit       Testes locais de bootstrap, configuração e Langfuse"
	@echo "  test-net        Mesmo teste, porém de dentro da rede fiap-ai-net"
	@echo ""
	@echo "  models          Lista os modelos baixados no Ollama"
	@echo "  pull M=nome     Baixa um modelo (ex: make pull M=qwen3:8b)"
	@echo "  gguf            Lista os .gguf do host e o que o .env espera importar"
	@echo "  gguf-import     Importa AGORA todos os .gguf de models/ (idempotente)"
	@echo "  models-dir      Cria a pasta models/"
	@echo "  databases       Lista os bancos do Postgres unificado"
	@echo "  psql            Abre o psql no Postgres unificado"
	@echo "  shell-ollama | shell-postgres   Abre shell no container"
	@echo "  config          Valida o docker-compose.yml de TODOS os perfis"
	@echo ""

# ------------------------------------------------------------
# Setup inicial
# ------------------------------------------------------------
check-prereqs:
	@status=0; \
	for comando in docker openssl python3 sed; do \
		if command -v "$$comando" >/dev/null 2>&1; then \
			printf '%s: OK\n' "$$comando"; \
		else \
			printf '%s: AUSENTE\n' "$$comando"; \
			status=1; \
		fi; \
	done; \
	if docker compose version >/dev/null 2>&1; then \
		echo "Docker Compose: OK"; \
	else \
		echo "Docker Compose: AUSENTE"; \
		status=1; \
	fi; \
	exit $$status

setup: check-prereqs
	@mkdir -p "$${MODELS_DIR:-./models}"
	@echo "Pasta $${MODELS_DIR:-./models}/ pronta; GGUF é opcional."
	@if [ -f .env ]; then \
		echo ".env já existe — nada alterado."; \
	else \
		cp .env.example .env; \
		POSTGRES_KEY=$$(openssl rand -hex 24); \
		PIPELINES_KEY=$$(openssl rand -hex 24); \
		WEBUI_KEY=$$(openssl rand -hex 32); \
		SEARX_KEY=$$(openssl rand -hex 32); \
		LF_SALT=$$(openssl rand -hex 32); \
		LF_ENC=$$(openssl rand -hex 32); \
		LF_AUTH=$$(openssl rand -hex 32); \
		LF_ADMIN=$$(openssl rand -hex 16); \
		LF_PK=pk-lf-$$(openssl rand -hex 16); \
		LF_SK=sk-lf-$$(openssl rand -hex 16); \
		LF_CLICKHOUSE=$$(openssl rand -hex 24); \
		LF_REDIS=$$(openssl rand -hex 24); \
		LF_MINIO=$$(openssl rand -hex 24); \
		sed -i.bak "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$$POSTGRES_KEY|" .env; \
		sed -i.bak "s|^PIPELINES_API_KEY=.*|PIPELINES_API_KEY=$$PIPELINES_KEY|" .env; \
		sed -i.bak "s|^WEBUI_SECRET_KEY=.*|WEBUI_SECRET_KEY=$$WEBUI_KEY|" .env; \
		sed -i.bak "s|^SEARXNG_SECRET=.*|SEARXNG_SECRET=$$SEARX_KEY|" .env; \
		sed -i.bak "s|^LANGFUSE_SALT=.*|LANGFUSE_SALT=$$LF_SALT|" .env; \
		sed -i.bak "s|^LANGFUSE_ENCRYPTION_KEY=.*|LANGFUSE_ENCRYPTION_KEY=$$LF_ENC|" .env; \
		sed -i.bak "s|^LANGFUSE_NEXTAUTH_SECRET=.*|LANGFUSE_NEXTAUTH_SECRET=$$LF_AUTH|" .env; \
		sed -i.bak "s|^LANGFUSE_ADMIN_PASSWORD=.*|LANGFUSE_ADMIN_PASSWORD=$$LF_ADMIN|" .env; \
		sed -i.bak "s|^LANGFUSE_PUBLIC_KEY=.*|LANGFUSE_PUBLIC_KEY=$$LF_PK|" .env; \
		sed -i.bak "s|^LANGFUSE_SECRET_KEY=.*|LANGFUSE_SECRET_KEY=$$LF_SK|" .env; \
		sed -i.bak "s|^LANGFUSE_CLICKHOUSE_PASSWORD=.*|LANGFUSE_CLICKHOUSE_PASSWORD=$$LF_CLICKHOUSE|" .env; \
		sed -i.bak "s|^LANGFUSE_REDIS_AUTH=.*|LANGFUSE_REDIS_AUTH=$$LF_REDIS|" .env; \
		sed -i.bak "s|^LANGFUSE_MINIO_PASSWORD=.*|LANGFUSE_MINIO_PASSWORD=$$LF_MINIO|" .env; \
		rm -f .env.bak; \
		echo ".env criado com todos os secrets locais aleatórios."; \
		echo "As chaves do Langfuse estão em LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY."; \
		echo "O login administrativo usa LANGFUSE_ADMIN_EMAIL e LANGFUSE_ADMIN_PASSWORD."; \
	fi

check-langfuse-env:
	@python3 scripts/langfuse_ollama_setup.py --check-env

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
# ~5 GB de RAM. Para usar junto, some os perfis.
up-langfuse: setup
	@$(MAKE) --no-print-directory _up-langfuse \
		LANGFUSE_STACK="$(COMPOSE) --profile langfuse"

up-complete-langfuse: setup
	@$(MAKE) --no-print-directory _up-langfuse \
		LANGFUSE_STACK="$(COMPOSE) --profile complete --profile langfuse"

_up-langfuse:
	@python3 scripts/langfuse_ollama_setup.py --check-env
	$(LANGFUSE_STACK) up -d --build --wait --wait-timeout 300
	@echo "O Langfuse e todas as dependências estão saudáveis."
	@echo "Registrando e validando a conexão com o Ollama..."
	@python3 scripts/langfuse_ollama_setup.py --espera 300
	@echo "Validando ingestão OTLP, sessions, conexão e score configs..."
	@LANGFUSE_REQUIRED=1 python3 scripts/integration_test.py
	@$(MAKE) --no-print-directory urls

validate-langfuse: check-langfuse-env
	@status=0; \
	for service in langfuse-clickhouse langfuse-redis langfuse-minio langfuse-worker langfuse-web; do \
		id=$$($(COMPOSE) --profile langfuse ps -q $$service); \
		if [ -z "$$id" ]; then \
			echo "$$service: FALHOU (container ausente)"; \
			status=1; \
			continue; \
		fi; \
		estado=$$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$$id" 2>/dev/null); \
		if [ "$$estado" = "healthy" ] || [ "$$estado" = "running" ]; then \
			echo "$$service: OK ($$estado)"; \
		else \
			echo "$$service: FALHOU ($${estado:-sem estado})"; \
			status=1; \
		fi; \
	done; \
	exit $$status
	@python3 scripts/langfuse_ollama_setup.py --espera 5
	@LANGFUSE_REQUIRED=1 python3 scripts/integration_test.py

# Cria (ou atualiza) a LLM connection `ollama` no projeto do Langfuse:
# adapter openai + http://ollama:11434/v1 + os modelos instalados.
# Idempotente — rode de novo depois de `make pull M=...` para o modelo
# novo aparecer no Playground. O up-langfuse já o chama sozinho.
langfuse-ollama: check-langfuse-env
	@python3 scripts/langfuse_ollama_setup.py --espera 120

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
	@falhas=0; \
	required() { \
		rotulo="$$1"; shift; \
		if "$$@" >/dev/null 2>&1; then echo "$$rotulo: OK"; else echo "$$rotulo: FALHOU"; falhas=1; fi; \
	}; \
	optional() { \
		rotulo="$$1"; container="$$2"; shift 2; \
		if [ -z "$$(docker inspect --format '{{.State.Running}}' "$$container" 2>/dev/null)" ]; then \
			echo "$$rotulo: fora do ar (perfil opcional)"; \
		elif "$$@" >/dev/null 2>&1; then \
			echo "$$rotulo: OK"; \
		else \
			echo "$$rotulo: FALHOU"; falhas=1; \
		fi; \
	}; \
	llm_connection() { \
		curl -sf -u "$${LANGFUSE_PUBLIC_KEY}:$${LANGFUSE_SECRET_KEY}" \
			"http://localhost:$${LANGFUSE_PORT:-3001}/api/public/llm-connections" \
			| grep -q '"baseURL"[[:space:]]*:[[:space:]]*"http://ollama'; \
	}; \
	score_configs() { \
		resposta=$$(curl -sf -u "$${LANGFUSE_PUBLIC_KEY}:$${LANGFUSE_SECRET_KEY}" \
			"http://localhost:$${LANGFUSE_PORT:-3001}/api/public/score-configs?limit=100") || return 1; \
		printf '%s' "$$resposta" | grep -q 'qualidade-resposta' \
			&& printf '%s' "$$resposta" | grep -q 'aderencia-instrucao' \
			&& printf '%s' "$$resposta" | grep -q 'classificacao-aula'; \
	}; \
	otel_habilitado() { \
		docker inspect fiap-open-webui --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null \
			| grep -q '^ENABLE_OTEL=true'; \
	}; \
	required "Postgres" docker exec fiap-postgres pg_isready -U "$${POSTGRES_USER:-fiap}"; \
	required "Ollama" curl -sf "http://localhost:$${OLLAMA_PORT:-11434}/api/tags"; \
	required "Open WebUI" curl -sf "http://localhost:$${WEBUI_PORT:-3000}/health"; \
	optional "ChromaDB" fiap-chromadb curl -sf "http://localhost:$${CHROMADB_PORT:-8000}/api/v2/heartbeat"; \
	optional "Pipelines" fiap-pipelines curl -sf "http://localhost:$${PIPELINES_PORT:-9099}/"; \
	optional "SearXNG" fiap-searxng curl -sf "http://localhost:$${SEARXNG_PORT:-8080}/healthz"; \
	optional "mem0" fiap-mem0 curl -sf "http://localhost:$${MEM0_PORT:-8100}/health"; \
	optional "Firecrawl" fiap-firecrawl-api curl -sf "http://localhost:$${FIRECRAWL_PORT:-3002}/"; \
	optional "Langfuse" fiap-langfuse-web curl -sf "http://localhost:$${LANGFUSE_PORT:-3001}/api/public/health"; \
	optional "Langfuse ↔ Ollama" fiap-langfuse-web llm_connection; \
	optional "Score configs" fiap-langfuse-web score_configs; \
	if [ "$${WEBUI_OTEL:-true}" = "true" ]; then \
		optional "OTEL Open WebUI → Langfuse" fiap-open-webui otel_habilitado; \
	else \
		echo "OTEL Open WebUI → Langfuse: desligado por configuração"; \
	fi; \
	exit $$falhas

test-unit:
	python3 -m unittest discover -s tests -p 'test_*.py' -v

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
		-e CHAT_MODEL \
		-e EMBEDDING_MODEL \
		-e MEM0_EMBEDDING_DIMS \
		-e PIPELINES_API_KEY \
		-e LANGFUSE_PUBLIC_KEY \
		-e LANGFUSE_SECRET_KEY \
		python:3.12-slim python /scripts/integration_test.py

# ------------------------------------------------------------
# Modelos
# ------------------------------------------------------------
models:
	docker exec -it fiap-ollama ollama list

# Conserta os engines do SearXNG (DuckDuckGo/Google/Brave devolvem CAPTCHA
# nesta rede e a busca volta vazia). Idempotente.
searxng-engines:
	@python3 scripts/searxng_engines.py searxng/settings.yml
	@echo "  Reinicie o SearXNG para aplicar: make restart-searxng"

restart-searxng:
	@$(COMPOSE) --profile search restart searxng
	@echo "  SearXNG reiniciado."

# Lista os .gguf do host e o que o .env espera importar
gguf:
	@echo ""
	@echo "  Arquivos .gguf em $${MODELS_DIR:-./models}/:"
	@if [ -d "$${MODELS_DIR:-./models}" ]; then \
		arquivos=$$(find "$${MODELS_DIR:-./models}" -maxdepth 1 -type f -iname '*.gguf' 2>/dev/null | sort); \
		if [ -z "$$arquivos" ]; then \
			echo "    (nenhum) — coloque o arquivo e rode 'make restart'"; \
		else \
			for f in $$arquivos; do \
				printf "    %-56s %8s%s\n" "$$(basename "$$f")" "$$(du -h "$$f" | cut -f1)" \
					"$$([ "$$(basename "$$f")" = "$${GGUF_FILE}" ] && echo '  <- GGUF_FILE')"; \
			done; \
		fi; \
	else \
		echo "    pasta $${MODELS_DIR:-./models}/ não existe"; \
	fi
	@echo ""
	@echo "  GGUF_FILE=$${GGUF_FILE:-(não definido)}"
	@echo "  GGUF_MODEL=$${GGUF_MODEL:-(nome do arquivo sem .gguf)}"
	@echo "  CHAT_MODEL=$${CHAT_MODEL:-qwen3.5:0.8b}"
	@echo ""

# Cria a pasta models/ com o README de instruções
models-dir:
	@mkdir -p "$${MODELS_DIR:-./models}"
	@echo "  Pasta $${MODELS_DIR:-./models}/ pronta. Coloque os .gguf nela."

# Importa (idempotente) TODOS os .gguf de models/ agora, sem reiniciar.
# O entrypoint já faz isso no boot — este alvo é para quando você copiou
# um .gguf com o container já no ar. Para forçar a reimportação de um,
# apague o modelo antes: docker exec fiap-ollama ollama rm <nome>
gguf-import:
	@if [ -z "$$(docker compose ps -q ollama 2>/dev/null)" ]; then \
		echo "  O serviço 'ollama' não está rodando. Suba com 'make up'."; \
		exit 1; \
	fi; \
	dir="$${MODELS_DIR:-./models}"; \
	if [ ! -d "$$dir" ]; then echo "  Pasta $$dir/ não existe."; exit 1; fi; \
	encontrados=0; \
	for f in "$$dir"/*.gguf; do \
		[ -e "$$f" ] || continue; \
		arquivo=$$(basename "$$f"); \
		nome=$$(basename "$$arquivo" .gguf); \
		encontrados=$$((encontrados + 1)); \
		if docker exec fiap-ollama ollama list | awk 'NR>1{print $$1}' | grep -qxF "$$nome:latest" \
		   || docker exec fiap-ollama ollama list | awk 'NR>1{print $$1}' | grep -qxF "$$nome"; then \
			echo "  = $$nome já existe"; \
		else \
			echo "  -> importando $$arquivo como $$nome ..."; \
			docker exec -i fiap-ollama sh -c "printf 'FROM /models/$$arquivo\n' > /tmp/Modelfile.gguf && ollama create '$$nome' -f /tmp/Modelfile.gguf" \
				|| echo "     AVISO: falha ao importar $$arquivo"; \
		fi; \
	done; \
	if [ "$$encontrados" -eq 0 ]; then \
		echo "  Nenhum .gguf em $$dir/"; \
	else \
		echo "  $$encontrados arquivo(s) conferidos. Veja com 'make models'." \
			" Depois: make langfuse-ollama (atualiza o Playground)."; \
	fi

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
	@status=0; \
	for p in minimum complete rag search memory crawl langfuse; do \
		if $(COMPOSE) --profile $$p config >/dev/null; then \
			echo "perfil $$p: OK"; \
		else \
			echo "perfil $$p: FALHOU"; \
			status=1; \
		fi; \
	done; \
	exit $$status

clean: down
	docker image rm fiap-ollama:latest fiap-mem0:latest fiap-postgres:latest 2>/dev/null || true
