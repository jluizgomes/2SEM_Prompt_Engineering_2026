# =========================================================
# FIAP AI Lab - Open WebUI + Ollama
# Makefile de build e orquestracao dos containers
# Prompt Engineering & AI - 2o Semestre 2026
# =========================================================
# Rode `make help` para ver tudo.
# =========================================================

SHELL := /bin/bash
COMPOSE ?= docker compose
FILE    ?= docker-compose.yml
# Arquivo de variaveis usado pelo Compose e lido pelo proprio Makefile.
# Troque para testar outra configuracao sem mexer no .env:
#   make up ENV_FILE=.env.teste
ENV_FILE ?= .env

# Nome das imagens construidas pelo alvo `build`
CPU_IMAGE ?= fiap-ollama-cpu:latest
GPU_IMAGE ?= fiap-ollama-gpu:latest

# Imagem base do Ollama aceita um build-arg (Dockerfile).
# A mesma imagem oficial detecta CPU ou GPU em runtime.
OLLAMA_BASE_IMAGE ?= ollama/ollama:latest

# Hash dos fontes que compoem a imagem. Vira selo na imagem (LABEL) e e
# usado por `make stale` para saber se a imagem ficou desatualizada.
BUILD_SHA := $(shell cat Dockerfile entrypoint.sh 2>/dev/null | sha256sum | cut -c1-16)

# O ENV_FILE sobrescreve as portas abaixo quando existir.
-include $(ENV_FILE)
export

# Portas no host (mesmos defaults do docker-compose.yml).
# Use ?= para o ENV_FILE continuar tendo prioridade.
OLLAMA_PORT     ?= 11434
OLLAMA_GPU_PORT ?= 11435
WEBUI_PORT      ?= 3000
WEBUI_EXTERNAL_PORT ?= 3001

# Modelos GGUF locais (o ENV_FILE tem prioridade quando define)
MODELS_DIR ?= ./models
GGUF_FILE  ?=
GGUF_MODEL ?=

# Modelos da biblioteca do Ollama (o ENV_FILE tem prioridade).
# Usados por `make models-check`, `make models-pull` e `make test`.
CHAT_MODEL       ?= qwen3.5:0.8b
EMBEDDING_MODEL  ?= qwen3-embedding:0.6b
EMBEDDING_CONTEXT ?= 512
GUARDRAIL_MODELS ?= llama-guard3:1b-q4_K_M,granite3-guardian:2b
EXTRA_MODELS     ?=

# Variante enxuta de embeddings criada pelo entrypoint e usada no RAG.
RAG_EMBEDDING_MODEL ?= $(EMBEDDING_MODEL)-ctx$(EMBEDDING_CONTEXT)

# Listas separadas por virgula (GUARDRAIL_MODELS/EXTRA_MODELS) vistas
# como uma so lista de palavras, para percorrer com `for` no shell.
comma     := ,
GUARDRAIL_LIST = $(strip $(subst $(comma), ,$(GUARDRAIL_MODELS)))
EXTRA_LIST     = $(strip $(subst $(comma), ,$(EXTRA_MODELS)))

# Alvos que exigem o servidor Ollama no ar.
OLLAMA_SERVICE ?= ollama

# Profile => servicos levantados
#   webui           -> ollama + open-webui
#   webui-gpu       -> ollama-gpu + open-webui-gpu
#   webui-external  -> open-webui-external (Ollama fora do Docker)
#   gpu             -> ollama-gpu (+ ollama, sem interface)
BASE            := $(COMPOSE) --env-file $(ENV_FILE) -f $(FILE)
ALL_PROFILES    := --profile gpu --profile webui --profile webui-gpu --profile webui-external

.DEFAULT_GOAL := help

# =========================================================
# AJUDA
# =========================================================
.PHONY: help
help: ## Lista todos os alvos disponiveis
	@echo ""
	@echo "  FIAP AI Lab - Open WebUI + Ollama"
	@echo "  ============================================"
	@echo ""
	@echo "  PRIMEIRO USO"
	@echo "    make setup          Prepara .env, cria models/ e constroi a imagem CPU"
	@echo "    make up             Sobe a stack CPU completa"
	@echo "    make test           Smoke test: chat, embeddings e interface"
	@echo "    make open           Abre a interface no navegador"
	@echo ""
	@echo "  SUBIR UM OU MAIS CONTAINERS"
	@echo "    make up                      stack CPU: ollama + open-webui"
	@echo "    make up-gpu                  stack GPU: ollama-gpu + open-webui-gpu"
	@echo "    make up-external             open-webui apontando p/ Ollama externo"
	@echo "    make up-ollama               somente o servidor Ollama (CPU)"
	@echo "    make up-ollama-gpu           somente o servidor Ollama (GPU)"
	@echo "    make up-open-webui           somente a interface (usa Ollama CPU)"
	@echo "    make up-all                  todos os servicos de interface (didatico)"
	@echo ""
	@echo "    make up PROFILE=webui        escolhe o profile livremente"
	@echo "    make up SERVICES=\"a b\"       sobe apenas os servicos listados"
	@echo "    make up-no-check             sobe sem validar as portas"
	@echo "    make profile-list            mostra os profiles e o que cada um sobe"
	@echo "    make ports                   mostra quem ocupa as portas do projeto"
	@echo "    make config                  valida o docker-compose.yml resolvido"
	@echo ""
	@echo "  BUILD"
	@echo "    make build                   constroi as imagens CPU e GPU"
	@echo "    make build-cpu               constroi a imagem CPU"
	@echo "    make build-gpu               constroi a imagem GPU"
	@echo "    make rebuild                 reconstroi sem usar cache"
	@echo "    make stale / stale-gpu       reconstroi a imagem quando os fontes mudam"
	@echo ""
	@echo "  OPERACAO"
	@echo "    make ps / status             status dos containers"
	@echo "    make start                   inicia containers ja criados"
	@echo "    make restart                 RECRIA os containers (aplica o .env,"
	@echo "                                 reimporta os .gguf e baixa o que faltar)"
	@echo "    make ready                   espera ollama e interface ficarem prontos"
	@echo "    make logs [S=ollama]         logs (seguindo)"
	@echo "    make logs-ollama             logs do download/importacao dos modelos"
	@echo "    make logs-webui              logs da interface"
	@echo "    make shell [S=ollama]        shell dentro do container"
	@echo "    make health                  checa a API do Ollama e a interface"
	@echo "    make urls                    mostra as URLs de acesso"
	@echo ""
	@echo "  MODELOS"
	@echo "    make models                  lista os modelos no servidor Ollama"
	@echo "    make models-check            confere se o que o .env pede existe"
	@echo "    make models-pull             baixa o que o projeto exige: embeddings,"
	@echo "                                 variante ctx, guardrails e extras"
	@echo "    make models-sync             importa os .gguf + baixa os da biblioteca"
	@echo "    make embed-variant           (re)cria a variante -ctxN do embedding (RAG)"
	@echo "    make models-rm M=nome        remove um modelo do servidor"
	@echo "    make pull M=qwen3.5:0.8b     baixa UM modelo especifico"
	@echo "    make ask P=\"pergunta\"        manda uma pergunta a um modelo pela API"
	@echo "    make test / make test-embed   smoke test do stack / so do embedding do RAG"
	@echo "    make bench                   mede latencia e tokens/s do modelo"
	@echo "    make bench-threads           compara num_thread na sua maquina"
	@echo ""
	@echo "  DIAGNOSTICO"
	@echo "    make doctor                  Docker + .env + portas + containers + modelos"
	@echo "    make check                   Docker e Compose disponiveis?"
	@echo "    make env-check               variaveis do .env coerentes entre si"
	@echo "    make env                     cria o .env (se nao existir) com segredo aleatorio"
	@echo "    make models-check            idem, conferindo os modelos exigidos"
	@echo ""
	@echo "  MODELOS GGUF LOCAIS (pasta models/)"
	@echo "    make gguf                    lista os .gguf do host e o que esta configurado"
	@echo "    make models-dir              cria a pasta models/"
	@echo "    make gguf-import             importa TODOS os .gguf agora (idempotente)"
	@echo "    make gguf-import FORCE=1     reimporta mesmo os que ja existem"
	@echo "    Coloque o .gguf em models/ e rode 'make restart'."
	@echo ""
	@echo "  PARAR E LIMPAR"
	@echo "    make stop                    para os containers (mantem dados)"
	@echo "    make down                    remove os containers (mantem volumes)"
	@echo "    make down-v                  remove containers + volumes (APAGA modelos)"
	@echo "    make clean                   remove containers e imagens do projeto"
	@echo "    make prune / reset           remove containers + imagens + volumes"
	@echo ""
	@echo "  Variaveis: PROFILE= SERVICES= S= M= P= FORCE= ENV_FILE= THREADS="
	@echo ""

# =========================================================
# SETUP E VALIDACAO
# =========================================================
.PHONY: setup
setup: env models-dir config build-cpu ## Prepara .env, a pasta models/ e a imagem CPU
	@echo ""
	@echo "  Pronto. Agora rode:  make up"
	@echo ""

.PHONY: env
env: ## Cria o .env a partir do .env.example com segredos aleatorios
	@if [ -f $(ENV_FILE) ]; then \
		echo "  $(ENV_FILE) ja existe - mantido intacto."; \
	else \
		cp .env.example $(ENV_FILE); \
		chave=$$(openssl rand -hex 32 2>/dev/null || date +%s | sha256sum | cut -c1-64); \
		sed -i.bak "s|^WEBUI_SECRET_KEY=.*|WEBUI_SECRET_KEY=$$chave|" $(ENV_FILE); \
		rm -f $(ENV_FILE).bak; \
		echo "  $(ENV_FILE) criado a partir do .env.example."; \
		echo "  WEBUI_SECRET_KEY gerado aleatoriamente."; \
	fi

.PHONY: doctor
doctor: ## Diagnostico rapido: .env, portas, imagens e modelos configurados
	@$(MAKE) --no-print-directory check
	@echo ""
	@$(MAKE) --no-print-directory env-check
	@echo ""
	@$(MAKE) --no-print-directory ports
	@echo ""
	@$(MAKE) --no-print-directory status
	@echo ""
	@$(MAKE) --no-print-directory models-check

.PHONY: check
check: ## Checa se o Docker e o Compose estao disponiveis
	@docker version --format '  Docker   : {{.Server.Version}}' 2>/dev/null || { echo "  ERRO: Docker nao esta rodando."; exit 1; }
	@$(COMPOSE) version | sed 's/^/  Compose  : /'

# Compara o hash dos fontes (Dockerfile + entrypoint.sh) com o selo
# gravado na imagem (LABEL br.fiap.fontes.sha256). Reconstroi quando
# os fontes mudarem, para o container nunca subir com entrypoint velho.
.PHONY: stale
stale: stale-cpu ## Reconstroi a imagem CPU quando os fontes mudaram
	@:

.PHONY: stale-cpu
stale-cpu: ## Verifica/reconstroi a imagem CPU quando os fontes mudaram
	@if ! docker image inspect $(CPU_IMAGE) >/dev/null 2>&1; then \
		echo "  Imagem $(CPU_IMAGE) nao existe - construindo..."; \
		$(MAKE) --no-print-directory build-cpu; \
	else \
		selo=$$(docker image inspect $(CPU_IMAGE) --format '{{index .Config.Labels "br.fiap.fontes.sha256"}}' 2>/dev/null); \
		if [ "$$selo" != "$(BUILD_SHA)" ]; then \
			echo "  Fontes mudaram - reconstruindo $(CPU_IMAGE)..."; \
			$(MAKE) --no-print-directory build-cpu; \
		else \
			echo "  Imagem $(CPU_IMAGE) em dia (selo $(BUILD_SHA))."; \
		fi; \
	fi

.PHONY: stale-gpu
stale-gpu: ## Verifica/reconstroi a imagem GPU quando os fontes mudaram
	@if ! docker image inspect $(GPU_IMAGE) >/dev/null 2>&1; then \
		echo "  Imagem $(GPU_IMAGE) nao existe - construindo..."; \
		$(MAKE) --no-print-directory build-gpu; \
	else \
		selo=$$(docker image inspect $(GPU_IMAGE) --format '{{index .Config.Labels "br.fiap.fontes.sha256"}}' 2>/dev/null); \
		if [ "$$selo" != "$(BUILD_SHA)" ]; then \
			echo "  Fontes mudaram - reconstruindo $(GPU_IMAGE)..."; \
			$(MAKE) --no-print-directory build-gpu; \
		else \
			echo "  Imagem $(GPU_IMAGE) em dia (selo $(BUILD_SHA))."; \
		fi; \
	fi

.PHONY: config
config: check ## Valida e mostra o compose resolvido (com os profiles ativos)
	@$(BASE) $(if $(PROFILE),--profile $(PROFILE)) config

.PHONY: profile-list
profile-list: ## Mostra cada profile e os servicos que ele sobe
	@echo ""
	@echo "  PROFILE            SERVICOS"
	@echo "  ------------------------------------------------------------"
	@printf "  %-18s %s\n" "(sem profile)" "ollama (servidor Ollama CPU)"
	@printf "  %-18s %s\n" "webui" "ollama + open-webui"
	@printf "  %-18s %s\n" "webui-gpu" "ollama-gpu + open-webui-gpu"
	@printf "  %-18s %s\n" "webui-external" "open-webui-external (Ollama fora do Docker)"
	@printf "  %-18s %s\n" "gpu" "ollama-gpu (+ ollama, sem interface)"
	@echo ""
	@echo "  Ollama CPU e Ollama GPU sao mutuamente exclusivos:"
	@echo "  cada um usa uma porta no host (11434 e 11435)."
	@echo "  Levante UM dos dois, nunca os dois com dados em uso."
	@echo ""
	@echo "  Detalhe por profile:"
	@for p in gpu webui webui-gpu webui-external; do \
		svcs=$$($(BASE) --profile $$p config --services 2>/dev/null | tr '\n' ' '); \
		printf "    --profile %-16s => %s\n" "$$p" "$$svcs"; \
	done
	@echo ""

.PHONY: ports
ports: ## Mostra quem esta ocupando as portas do projeto
	@echo ""
	@echo "  Projeto: $(COMPOSE_PROJECT_NAME)"
	@echo ""
	@echo "  Porta   Status      Quem esta usando"
	@echo "  ----------------------------------------------------------------"
	@for port in $(OLLAMA_PORT) $(OLLAMA_GPU_PORT) $(WEBUI_PORT); do \
		owner=$$(docker ps --filter "publish=$$port" --format '{{.Names}}' 2>/dev/null | head -1); \
		if [ -n "$$owner" ]; then \
			proj=$$(docker inspect "$$owner" --format '{{index .Config.Labels "com.docker.compose.project"}}' 2>/dev/null); \
			if [ "$$proj" = "$(COMPOSE_PROJECT_NAME)" ]; then \
				printf "  %-7s %-11s %s (este projeto)\n" "$$port" "em uso" "$$owner"; \
			else \
				printf "  %-7s %-11s container %s (projeto %s)\n" "$$port" "OCUPADA" "$$owner" "$$proj"; \
			fi; \
		elif python3 -c "import socket,sys; s=socket.socket(); s.settimeout(0.3); sys.exit(0 if s.connect_ex(('127.0.0.1',$$port))==0 else 1)" 2>/dev/null; then \
			printf "  %-7s %-11s outro processo no host\n" "$$port" "OCUPADA"; \
		else \
			printf "  %-7s %-11s -\n" "$$port" "livre"; \
		fi; \
	done
	@echo ""
	@echo "  'em uso (este projeto)' significa que o servico ja esta no ar - nao e conflito."
	@echo "  Se 'OCUPADA' por outra stack, pare-a antes de rodar 'make up':"
	@echo "    docker compose -f <pasta-da-stack>/docker-compose.yml down"
	@echo "  Ou ajuste OLLAMA_PORT / WEBUI_PORT no .env."
	@echo ""

.PHONY: env-check
env-check: ## Confere se as variaveis obrigatorias do .env estao coerentes
	@falhas=0; \
	confere() { \
		if [ -z "$$2" ]; then echo "  FALTA   $$1"; falhas=1; \
		else echo "  $$3$$1 = $$2"; fi; \
	}; \
	[ -f $(ENV_FILE) ] || { echo "  $(ENV_FILE) nao existe. Rode 'make env'."; exit 1; }; \
	confere CHAT_MODEL "$(CHAT_MODEL)" ""; \
	confere EMBEDDING_MODEL "$(EMBEDDING_MODEL)" ""; \
	[ -d "$(MODELS_DIR)" ] || { echo "  AVISO   MODELS_DIR = $(MODELS_DIR) nao existe (rode 'make models-dir')"; }; \
	if [ -n "$(GGUF_FILE)" ] && [ ! -f "$(MODELS_DIR)/$(GGUF_FILE)" ]; then \
		echo "  AVISO   GGUF_FILE = $(GGUF_FILE) nao existe em $(MODELS_DIR)/"; \
		echo "          o entrypoint cai no primeiro .gguf em ordem alfabetica"; \
	fi; \
	confere MODELS_DIR "$(MODELS_DIR)" ""; \
	echo "  INFO    guardrails = $(if $(GUARDRAIL_MODELS),$(GUARDRAIL_MODELS),(nenhum))"; \
	echo "  INFO    extras     = $(if $(EXTRA_MODELS),$(EXTRA_MODELS),(nenhum))"; \
	echo "  INFO    embeddings = $(RAG_EMBEDDING_MODEL) (RAG do Open WebUI)"; \
	[ "$$falhas" -eq 0 ] && echo "  .env coerente."; \
	exit $$falhas

.PHONY: check-ports
check-ports: ## Falha se as portas do projeto estiverem ocupadas por OUTRA stack
	@busy=""; \
	for port in $(if $(PORTS),$(PORTS),$(OLLAMA_PORT) $(WEBUI_PORT)); do \
		name=$$(docker ps --filter "publish=$$port" --format '{{.Names}}' 2>/dev/null | head -1); \
		if [ -n "$$name" ]; then \
			proj=$$(docker inspect "$$name" --format '{{index .Config.Labels "com.docker.compose.project"}}' 2>/dev/null); \
			if [ "$$proj" != "$(COMPOSE_PROJECT_NAME)" ]; then \
				busy="$$busy\n    porta $$port -> container $$name (projeto $$proj)"; \
			fi; \
		elif python3 -c "import socket,sys; s=socket.socket(); s.settimeout(0.3); sys.exit(0 if s.connect_ex(('127.0.0.1',$$port))==0 else 1)" 2>/dev/null; then \
			busy="$$busy\n    porta $$port -> outro processo no host"; \
		fi; \
	done; \
	if [ -n "$$busy" ]; then \
		echo ""; \
		echo "  ERRO: porta(s) ja em uso por outra stack:"; \
		echo -e "$$busy"; \
		echo ""; \
		echo "  Rode 'make ports' para ver os detalhes. Opcoes:"; \
		echo "    - pare a stack que esta usando a porta;"; \
		echo "    - ajuste OLLAMA_PORT / WEBUI_PORT no .env;"; \
		echo "    - use 'make up-no-check' para ignorar esta verificacao."; \
		echo ""; \
		exit 1; \
	fi

# =========================================================
# BUILD
# =========================================================
.PHONY: build
build: build-cpu build-gpu ## Constroi as imagens CPU e GPU

.PHONY: build-cpu
build-cpu: check ## Constroi a imagem do Ollama CPU
	@echo ""
	@echo "  Construindo $(CPU_IMAGE) ..."
	@$(BASE) build \
		--build-arg OLLAMA_BASE_IMAGE=$(OLLAMA_BASE_IMAGE) \
		--build-arg FIAP_BUILD_SHA=$(BUILD_SHA) \
		ollama
	@echo "  Imagem $(CPU_IMAGE) pronta."

.PHONY: build-gpu
build-gpu: check ## Constroi a imagem do Ollama GPU
	@echo ""
	@echo "  Construindo $(GPU_IMAGE) ..."
	@$(BASE) build \
		--build-arg OLLAMA_BASE_IMAGE=$(OLLAMA_BASE_IMAGE) \
		--build-arg FIAP_BUILD_SHA=$(BUILD_SHA) \
		ollama-gpu
	@echo "  Imagem $(GPU_IMAGE) pronta."

.PHONY: rebuild
rebuild: check ## Reconstroi as imagens sem cache
	@$(BASE) build --no-cache \
		--build-arg OLLAMA_BASE_IMAGE=$(OLLAMA_BASE_IMAGE) \
		--build-arg FIAP_BUILD_SHA=$(BUILD_SHA) \
		ollama ollama-gpu

# =========================================================
# SUBIR OS CONTAINERS
# =========================================================
.PHONY: up
up: check stale models-dir ## Sobe a stack CPU (ollama + open-webui) e espera ficar pronto
	@$(MAKE) --no-print-directory check-ports PORTS="$(OLLAMA_PORT) $(WEBUI_PORT)"
	@if [ -n "$(SERVICES)" ]; then \
		echo "  Subindo servicos: $(SERVICES)"; \
		$(BASE) $(if $(PROFILE),--profile $(PROFILE)) up -d $(SERVICES); \
	else \
		echo "  Subindo profile: $(if $(PROFILE),$(PROFILE),webui)"; \
		$(BASE) --profile $(if $(PROFILE),$(PROFILE),webui) up -d; \
	fi
	@$(MAKE) --no-print-directory status
	@$(MAKE) --no-print-directory ready

.PHONY: up-no-check
up-no-check: stale models-dir ## Sobe a stack CPU ignorando a checagem de portas
	@echo "  Subindo profile: $(if $(PROFILE),$(PROFILE),webui) (sem checar portas)"
	@$(BASE) --profile $(if $(PROFILE),$(PROFILE),webui) up -d
	@$(MAKE) --no-print-directory status

.PHONY: up-gpu
up-gpu: check stale-gpu models-dir ## Sobe a stack GPU (ollama-gpu + open-webui)
	@echo "  Subindo profile webui-gpu (Ollama com GPU NVIDIA) ..."
	@$(BASE) --profile webui-gpu up -d
	@$(MAKE) --no-print-directory status

.PHONY: up-external
up-external: check ## Sobe a interface ligada a um Ollama fora do Docker
	@echo "  Subindo profile webui-external ..."
	@echo "  Destino: $${OLLAMA_EXTERNAL_URL:-http://host.docker.internal:11434}"
	@$(BASE) --profile webui-external up -d
	@$(MAKE) --no-print-directory status
	@echo "  Interface: http://localhost:$(WEBUI_EXTERNAL_PORT)"
	@echo "  O Ollama EXTERNO precisa estar no ar antes (make up-ollama, se for local)."

.PHONY: up-ollama
up-ollama: check stale models-dir ## Sobe SOMENTE o servidor Ollama em CPU
	@$(MAKE) --no-print-directory check-ports PORTS="$(OLLAMA_PORT)"
	@$(BASE) up -d ollama
	@$(MAKE) --no-print-directory status

.PHONY: up-ollama-gpu
up-ollama-gpu: check stale-gpu models-dir ## Sobe SOMENTE o servidor Ollama com GPU
	@$(MAKE) --no-print-directory check-ports PORTS="$(OLLAMA_GPU_PORT)"
	@$(BASE) --profile gpu up -d ollama-gpu
	@$(MAKE) --no-print-directory status

.PHONY: up-open-webui
up-open-webui: check ## Sobe SOMENTE a interface (usa o Ollama CPU)
	@$(MAKE) --no-print-directory check-ports PORTS="$(WEBUI_PORT)"
	@$(BASE) --profile webui up -d open-webui
	@$(MAKE) --no-print-directory status

.PHONY: up-all
up-all: check models-dir ## Sobe TODOS os servicos de interface (uso didatico)
	@$(BASE) $(ALL_PROFILES) up -d

.PHONY: start
start: ## Inicia containers ja criados (nao aplica mudancas no .env)
	@$(BASE) start

# Recria os containers no lugar (--force-recreate): e o que faz o .env
# novo valer, roda o entrypoint de novo (reimporta .gguf) e baixa o que
# faltar. Nao derruba a stack antes, entao uma falha nao deixa tudo fora.
# Use o mesmo profile do ultimo up:  make restart PROFILE=gpu
.PHONY: restart
restart: models-dir ## RECRIA os containers: aplica o .env, reimporta os .gguf
	@echo "  Recriando containers do profile $(if $(PROFILE),$(PROFILE),webui) ..."
	@$(BASE) --profile $(if $(PROFILE),$(PROFILE),webui) up -d --force-recreate $(SERVICES)
	@$(MAKE) --no-print-directory status
	@$(MAKE) --no-print-directory ready

.PHONY: ready
ready: ## Espera o Ollama (e a interface) responderem
	@porta="$(OLLAMA_PORT)"; \
	for i in $$(seq 1 60); do \
		if curl -sf --max-time 2 "http://localhost:$$porta/api/tags" >/dev/null 2>&1; then \
			echo "  Ollama pronto em http://localhost:$$porta"; \
			break; \
		fi; \
		[ "$$i" -eq 1 ] && echo "  Esperando o Ollama subir (importa .gguf e baixa modelos no primeiro boot)..."; \
		sleep 2; \
		if [ "$$i" -eq 60 ]; then echo "  TIMEOUT: o Ollama nao respondeu em 2 min. Veja 'make logs-ollama'."; exit 1; fi; \
	done; \
	if [ -n "$$($(BASE) ps -q open-webui 2>/dev/null)" ]; then \
		webui="$(WEBUI_PORT)"; \
		for i in $$(seq 1 60); do \
			if curl -sf --max-time 2 "http://localhost:$$webui/health" >/dev/null 2>&1; then \
				echo "  Open WebUI pronto em http://localhost:$$webui"; \
				break; \
			fi; \
			sleep 2; \
			if [ "$$i" -eq 60 ]; then echo "  TIMEOUT: a interface nao respondeu em 2 min. Veja 'make logs-webui'."; exit 1; fi; \
		done; \
	fi; \
	echo "  Acesse: make open"

# =========================================================
# STATUS, LOGS E ACESSO
# =========================================================
.PHONY: ps status
ps status: ## Mostra o status dos containers
	@$(BASE) ps

.PHONY: logs
logs: ## Logs em tempo real (S=servico para filtrar)
	@$(BASE) logs -f $(S)

.PHONY: logs-ollama
logs-ollama: ## Logs do download/importacao de modelos do Ollama
	@$(BASE) logs -f ollama

.PHONY: logs-webui
logs-webui: ## Logs da interface do Open WebUI
	@$(BASE) logs -f open-webui open-webui-gpu open-webui-external

.PHONY: shell
shell: ## Shell dentro do container (S=servico, padrao ollama)
	@$(BASE) exec $(or $(S),ollama) bash

# ---------------------------------------------------------
# MODELOS
# ---------------------------------------------------------
# O entrypoint do container ja faz tudo isso no boot (importa
# os .gguf, cria a variante de embeddings e baixa guardrails/
# extras). Os alvos abaixo existem para (a) rodar sem reiniciar
# o container, (b) conferir o que falta e (c) baixar sob demanda.

# FALHA se o servidor Ollama nao estiver no ar.
.PHONY: exigir-ollama
exigir-ollama:
	@if [ -z "$$($(BASE) ps -q $(OLLAMA_SERVICE) 2>/dev/null)" ]; then \
		echo "  O servico '$(OLLAMA_SERVICE)' nao esta rodando."; \
		echo "  Suba com 'make up' (stack completa), 'make up-ollama' (so o servidor)"; \
		echo "  ou 'make up-ollama-gpu' (com GPU)."; \
		exit 1; \
	fi

# Lista de modelos ja instalados no servidor (uma linha por modelo).
modelos-instalados = $(BASE) exec -T $(OLLAMA_SERVICE) ollama list 2>/dev/null | awk 'NR>1 {print $$1}'

.PHONY: models
models: exigir-ollama ## Lista os modelos disponiveis no servidor Ollama
	@$(BASE) exec -T $(OLLAMA_SERVICE) ollama list

.PHONY: models-check
models-check: ## Confere se os modelos exigidos pelo .env estao no servidor
	@echo ""
	@printf "  %-11s %-46s %s\n" "PAPEL" "MODELO" "STATUS"
	@printf "  %-11s %-46s %s\n" "----------" "----------------------------------------------" "------"
	@falta=0; \
	existentes=$$($(modelos-instalados)); \
	confere() { \
		[ -n "$$2" ] || { printf "  %-11s %-46s %s\n" "$$1" "-" "(vazio no .env)"; return 0; }; \
		if printf '%s\n' "$$existentes" | grep -qxF "$$2" \
		   || printf '%s\n' "$$existentes" | grep -qxF "$$2:latest"; then \
			printf "  %-11s %-46s %s\n" "$$1" "$$2" "OK"; \
		else \
			printf "  %-11s %-46s %s\n" "$$1" "$$2" "AUSENTE"; falta=1; \
		fi; \
	}; \
	confere "chat" "$(CHAT_MODEL)"; \
	confere "embedding" "$(EMBEDDING_MODEL)"; \
	confere "rag" "$(RAG_EMBEDDING_MODEL)"; \
	for m in $(GUARDRAIL_LIST); do confere "guardrail" "$$m"; done; \
	for m in $(EXTRA_LIST); do confere "extra" "$$m"; done; \
	echo ""; \
	if [ -z "$$($(BASE) ps -q $(OLLAMA_SERVICE) 2>/dev/null)" ]; then \
		echo "  (servico '$(OLLAMA_SERVICE)' parado: acima esta so o que o .env pede)"; \
		echo "  Suba com 'make up-ollama' para conferir o que ja esta instalado."; \
		exit 0; \
	fi; \
	if [ "$$falta" -eq 0 ]; then \
		echo "  Todos os modelos exigidos estao instalados."; \
	else \
		echo "  Faltam modelos:"; \
		echo "    make models-pull    baixa embeddings, guardrails e extras da biblioteca"; \
		echo "    make gguf-import    importa os .gguf da pasta models/"; \
		echo "    make models-sync    faz os dois de uma vez"; \
	fi; \
	exit $$falta

.PHONY: models-pull
models-pull: exigir-ollama ## Baixa o que o projeto exige: embeddings, guardrails e extras
	@echo ""
	@echo "  Baixando os modelos exigidos (pula os que ja existem)"
	@existentes=$$($(modelos-instalados)); \
	baixar() { \
		[ -n "$$1" ] || return 0; \
		if printf '%s\n' "$$existentes" | grep -qxF "$$1" \
		   || printf '%s\n' "$$existentes" | grep -qxF "$$1:latest"; then \
			echo "  = $$1 ja existe"; return 0; \
		fi; \
		echo "  -> baixando $$1 ..."; \
		if $(BASE) exec -T $(OLLAMA_SERVICE) ollama pull "$$1" >/dev/null 2>&1; then \
			echo "    pronto."; \
		else \
			echo "    AVISO: falha ao baixar $$1 (confira o nome e a conexao)"; \
		fi; \
	}; \
	baixar "$(CHAT_MODEL)"; \
	baixar "$(EMBEDDING_MODEL)"; \
	for m in $(GUARDRAIL_LIST); do baixar "$$m"; done; \
	for m in $(EXTRA_LIST); do baixar "$$m"; done; \
	echo ""
	@$(MAKE) --no-print-directory embed-variant
	@echo "  Modelos no servidor:"
	@$(BASE) exec -T $(OLLAMA_SERVICE) ollama list

.PHONY: models-sync
models-sync: ## Importa TODOS os .gguf e baixa o que falta da biblioteca
	@$(MAKE) --no-print-directory gguf-import
	@$(MAKE) --no-print-directory models-pull

.PHONY: models-rm
models-rm: exigir-ollama ## Remove um modelo do servidor (M=nome)
	@if [ -z "$(M)" ]; then echo "  Informe o modelo: make models-rm M=nome"; exit 1; fi
	@echo "  Removendo $(M) ..."
	@$(BASE) exec -T $(OLLAMA_SERVICE) ollama rm $(M)

.PHONY: embed-variant
embed-variant: exigir-ollama ## (Re)cria a variante enxuta do embedding (-ctxN) usada no RAG
	@if [ -z "$(EMBEDDING_CONTEXT)" ] || [ "$(EMBEDDING_CONTEXT)" = "0" ]; then \
		echo "  EMBEDDING_CONTEXT vazio/0 - o RAG usa $(EMBEDDING_MODEL) direto."; exit 0; \
	fi; \
	variante="$(RAG_EMBEDDING_MODEL)"; \
	existentes=$$($(modelos-instalados)); \
	if printf '%s\n' "$$existentes" | grep -qxF "$$variante" \
	   || printf '%s\n' "$$existentes" | grep -qxF "$$variante:latest"; then \
		echo "  Variante de embeddings '$$variante' ja existe."; exit 0; \
	fi; \
	echo "  Criando '$$variante' (contexto $(EMBEDDING_CONTEXT)) a partir de $(EMBEDDING_MODEL) ..."; \
	$(BASE) exec -T $(OLLAMA_SERVICE) sh -c "printf 'FROM $(EMBEDDING_MODEL)\nPARAMETER num_ctx $(EMBEDDING_CONTEXT)\n' > /tmp/Modelfile.embed && ollama create '$$variante' -f /tmp/Modelfile.embed" \
		&& echo "  Pronto. O RAG do Open WebUI usa '$$variante'."

.PHONY: pull
pull: ## Baixa UM modelo (M=nome). Sem M= baixa tudo que o .env exige
	@if [ -z "$(M)" ]; then \
		echo "  M= nao informado: baixando todos os modelos exigidos pelo .env."; \
		$(MAKE) --no-print-directory models-pull; \
		exit 0; \
	fi; \
	echo "  Baixando $(M) ..."; \
	$(BASE) exec -T $(OLLAMA_SERVICE) ollama pull $(M)

.PHONY: ask
ask: exigir-ollama ## Pergunta a um modelo pela API (P="pergunta", M=modelo)
	@pergunta="$(P)"; \
	modelo="$(if $(M),$(M),$(CHAT_MODEL))"; \
	if [ -z "$$pergunta" ]; then read -r -p "  pergunta para $$modelo: " pergunta; fi; \
	echo ""; \
	curl -sf --max-time 300 "http://localhost:$(OLLAMA_PORT)/api/generate" \
		-H 'Content-Type: application/json' \
		-d "$$(printf '{"model":"%s","prompt":%s,"stream":false,"options":{"num_predict":400}}' \
			"$$modelo" "$$(printf '%s' "$$pergunta" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')")" \
		| python3 -c 'import json,sys; \
d=json.load(sys.stdin); \
print(d.get("response","").strip()); \
n=d.get("eval_count",0); s=d.get("eval_duration",1)/1e9; \
print("  (%s tok, %.1f tok/s)" % (n, n/s if s else 0))'

# ---------------------------------------------------------
# MODELOS GGUF LOCAIS (pasta models/)
# ---------------------------------------------------------
.PHONY: gguf
gguf: ## Lista os arquivos .gguf na pasta de modelos do host
	@echo ""
	@if [ -d "$(MODELS_DIR)" ]; then \
		arquivos=$$(find "$(MODELS_DIR)" -maxdepth 1 -type f -iname '*.gguf' 2>/dev/null | sort); \
		if [ -z "$$arquivos" ]; then \
			echo "  Nenhum .gguf em $(MODELS_DIR)/"; \
			echo "  Coloque o arquivo la e rode 'make restart'."; \
		else \
			echo "  Arquivos .gguf em $(MODELS_DIR)/:"; \
			for f in $$arquivos; do \
				tam=$$(du -h "$$f" | cut -f1); \
				marca=""; \
				[ "$$(basename "$$f")" = "$(GGUF_FILE)" ] && marca="  <- GGUF_FILE (modelo principal)"; \
				printf "    %-56s %8s%s\n" "$$(basename "$$f")" "$$tam" "$$marca"; \
			done; \
		fi; \
	else \
		echo "  Pasta $(MODELS_DIR)/ nao existe. Rode 'make models-dir'."; \
	fi
	@echo ""
	@echo "  Todos os .gguf acima viram modelos no Ollama (nome = arquivo sem .gguf)."
	@echo "  GGUF_FILE=$(if $(GGUF_FILE),$(GGUF_FILE),(nao definido))"
	@echo "  GGUF_MODEL=$(if $(GGUF_MODEL),$(GGUF_MODEL),(nome do arquivo sem .gguf))"
	@echo "  CHAT_MODEL=$(CHAT_MODEL)"
	@echo "  Embeddings (RAG)=$(RAG_EMBEDDING_MODEL)"
	@echo "  Guardrails=$(if $(GUARDRAIL_MODELS),$(GUARDRAIL_MODELS),(nenhum))"
	@echo "  Extras=$(if $(EXTRA_MODELS),$(EXTRA_MODELS),(nenhum))"
	@echo ""

.PHONY: models-dir
models-dir: ## Cria a pasta models/ antes do Docker (evita ela nascer como root)
	@if [ -d "$(MODELS_DIR)" ]; then \
		echo "  Pasta $(MODELS_DIR)/ pronta."; \
	else \
		mkdir -p "$(MODELS_DIR)" && echo "  Pasta $(MODELS_DIR)/ criada (sem .gguf ainda - a stack sobe assim mesmo)."; \
	fi
	@if [ ! -w "$(MODELS_DIR)" ]; then \
		echo "  ATENCAO: $(MODELS_DIR)/ nao e gravavel por voce."; \
		echo "  O Docker pode ter criado a pasta como root. Corrija com:"; \
		echo "    sudo chown -R \$$USER:$$USER \"$(MODELS_DIR)\""; \
	fi

# Importa TODOS os .gguf de models/ sem reiniciar o container.
# O arquivo GGUF_FILE recebe o nome GGUF_MODEL (o que satisfaz
# CHAT_MODEL); os outros entram com o nome do arquivo.
# FORCE=1 reimporta mesmo os que ja existem.
.PHONY: gguf-import
gguf-import: exigir-ollama ## Importa TODOS os .gguf de models/ agora (idempotente)
	@dir="$(MODELS_DIR)"; \
	if [ ! -d "$$dir" ]; then echo "  Pasta $$dir/ nao existe. Rode 'make models-dir'."; exit 1; fi; \
	existentes=$$($(modelos-instalados)); \
	encontrados=0; importados=0; \
	for f in "$$dir"/*.gguf; do \
		[ -e "$$f" ] || continue; \
		arquivo=$$(basename "$$f"); \
		nome=$$(basename "$$arquivo" .gguf); \
		encontrados=$$((encontrados + 1)); \
		if [ "$$arquivo" = "$(GGUF_FILE)" ] && [ -n "$(GGUF_MODEL)" ]; then \
			nome="$(GGUF_MODEL)"; \
		fi; \
		if [ "$(FORCE)" != "1" ] \
		   && { printf '%s\n' "$$existentes" | grep -qxF "$$nome" \
		     || printf '%s\n' "$$existentes" | grep -qxF "$$nome:latest"; }; then \
			echo "  = $$nome ja existe"; continue; \
		fi; \
		echo "  -> importando $$arquivo como $$nome ..."; \
		if $(BASE) exec -T $(OLLAMA_SERVICE) sh -c "printf 'FROM /models/$$arquivo\n' > /tmp/Modelfile.gguf && ollama create '$$nome' -f /tmp/Modelfile.gguf" >/dev/null; then \
			importados=$$((importados + 1)); \
		else \
			echo "     AVISO: falha ao importar $$arquivo"; \
		fi; \
	done; \
	if [ "$$encontrados" -eq 0 ]; then \
		echo "  Nenhum .gguf em $$dir/."; exit 1; \
	fi; \
	echo "  $$encontrados arquivo(s) conferidos, $$importados importado(s) agora."; \
	echo "  CHAT_MODEL=$(CHAT_MODEL) | veja com 'make models'"

# ---------------------------------------------------------
# PERFORMANCE
# ---------------------------------------------------------
.PHONY: bench
bench: ## Mede a performance do Ollama (latencia frio/quente e tokens/s)
	@model="$(CHAT_MODEL)"; \
	port="$(OLLAMA_PORT)"; \
	echo ""; \
	echo "  Medindo performance (porta $$port, modelo $$model)"; \
	echo ""; \
	python3 scripts/bench_ollama.py --port "$$port" --model "$$model" $(if $(THREADS),--threads $(THREADS),)

.PHONY: bench-threads
bench-threads: ## Compara num_thread na sua maquina (ex.: make bench-threads THREADS=4,6,8,12)
	@$(MAKE) --no-print-directory bench THREADS="$(or $(THREADS),4,6,8,12)"

# ---------------------------------------------------------
# SAUDE E TESTE
# ---------------------------------------------------------
.PHONY: health
health: ## Checa a API do Ollama em cada porta conhecida e a interface
	@probe_ollama() { \
		svc="$$1"; porta="$$2"; \
		if [ -z "$$($(BASE) ps -q $$svc 2>/dev/null)" ]; then \
			echo "  $$svc :$$porta  parado      (sobe com: make up-$$svc)"; return; \
		fi; \
		if curl -sf --max-time 3 "http://localhost:$$porta/api/tags" >/dev/null 2>&1; then \
			ver=$$(curl -s --max-time 3 "http://localhost:$$porta/api/version" | tr -d '{}"' | cut -d: -f2); \
			echo "  $$svc :$$porta  OK         (ollama $$ver)"; \
		else \
			echo "  $$svc :$$porta  SEM RESPOSTA (veja: make logs-$$svc)"; \
		fi; \
	}; \
	probe_webui() { \
		svc="$$1"; porta="$$2"; como="$$3"; \
		if [ -z "$$($(BASE) ps -q $$svc 2>/dev/null)" ]; then \
			echo "  $$svc :$$porta  parado      (sobe com: $$como)"; return; \
		fi; \
		if curl -sf --max-time 3 "http://localhost:$$porta/health" >/dev/null 2>&1; then \
			echo "  $$svc :$$porta  OK"; \
		else \
			echo "  $$svc :$$porta  SEM RESPOSTA (veja: make logs-webui)"; \
		fi; \
	}; \
	probe_ollama ollama "$(OLLAMA_PORT)"; \
	probe_ollama ollama-gpu "$(OLLAMA_GPU_PORT)"; \
	probe_webui open-webui "$(WEBUI_PORT)" "make up"; \
	probe_webui open-webui-external "$(WEBUI_EXTERNAL_PORT)" "make up-external"; \
	echo ""; \
	echo "  Modelos instalados: make models      |      exigidos: make models-check"

.PHONY: test
test: ## Teste ponta a ponta: chat, embeddings e interface (falha != 0)
	@python3 scripts/smoke_test.py \
		--port "$(OLLAMA_PORT)" \
		--webui-port "$(if $(filter 1,$(NO_WEBUI)),0,$(WEBUI_PORT))" \
		--chat-model "$(CHAT_MODEL)" \
		--embed-model "$(RAG_EMBEDDING_MODEL)"

.PHONY: test-embed
test-embed: ## Testa so o modelo de embeddings do RAG
	@python3 scripts/smoke_test.py --port "$(OLLAMA_PORT)" --webui-port 0 \
		--chat-model "" --embed-model "$(RAG_EMBEDDING_MODEL)"

.PHONY: open
open: ## Abre a interface no navegador
	@$(MAKE) --no-print-directory urls
	@port=$$(grep -E '^WEBUI_PORT=' $(ENV_FILE) 2>/dev/null | cut -d= -f2); \
	url="http://localhost:$${port:-3000}"; \
	echo "  Abrindo $$url"; \
	(xdg-open "$$url" >/dev/null 2>&1 || open "$$url" >/dev/null 2>&1 || true)

.PHONY: urls
urls: ## Mostra as URLs de acesso
	@echo "  Open WebUI : http://localhost:$(WEBUI_PORT)"; \
	echo "  Ollama CPU : http://localhost:$(OLLAMA_PORT)"; \
	echo "  Ollama GPU : http://localhost:$(OLLAMA_GPU_PORT)"

# =========================================================
# PARAR E LIMPAR
# =========================================================
.PHONY: pause stop
stop pause: ## Para os containers sem remove-los
	@$(BASE) $(ALL_PROFILES) stop

.PHONY: down
down: ## Remove os containers (mantem os volumes/modelos)
	@$(BASE) $(ALL_PROFILES) down --remove-orphans

.PHONY: down-v
down-v: ## Remove containers E volumes (apaga modelos e historico)
	@echo "  ATENCAO: isso apaga modelos baixados e dados do Open WebUI."
	@$(BASE) $(ALL_PROFILES) down -v --remove-orphans

.PHONY: clean
clean: down ## Remove containers e as imagens construidas
	@docker image rm -f $(CPU_IMAGE) $(GPU_IMAGE) 2>/dev/null || true
	@echo "  Imagens $(CPU_IMAGE) e $(GPU_IMAGE) removidas."

.PHONY: prune
prune: down-v ## Remove containers, volumes e imagens (reset total)
	@docker image rm -f $(CPU_IMAGE) $(GPU_IMAGE) 2>/dev/null || true
	@echo "  Reset completo concluido."

.PHONY: reset
reset: prune ## Alias de prune
