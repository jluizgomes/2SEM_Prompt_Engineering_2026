# FIAP AI Lab

Laboratório Docker da disciplina **Prompt Engineering and Artificial Intelligence** — FIAP · 2º Semestre 2026
Prof. Jorge Luiz Gomes

Um único `docker compose` entrega LLM local, interface de chat, vector store, busca web, memória de longo prazo e crawling — tudo integrado entre si, tudo gratuito, tudo rodando na máquina do aluno.

---

## Índice

1. [O que sobe](#1-o-que-sobe)
2. [Perfis](#2-perfis)
3. [Requisitos](#3-requisitos)
4. [Setup e primeiro uso](#4-setup-e-primeiro-uso)
5. [Build](#5-build)
6. [Como subir cada perfil](#6-como-subir-cada-perfil)
7. [Postgres unificado](#7-postgres-unificado)
8. [Integrações do Open WebUI](#8-integrações-do-open-webui)
9. [Usar cada stack no código das aulas](#9-usar-cada-stack-no-código-das-aulas)
10. [Variáveis de ambiente](#10-variáveis-de-ambiente)
11. [Testes](#11-testes)
12. [Comandos do Makefile](#12-comandos-do-makefile)
13. [Solução de problemas](#13-solução-de-problemas)
14. [Estrutura de arquivos](#14-estrutura-de-arquivos)

---

## 1. O que sobe

| Serviço | Container | Porta host | Papel na disciplina |
|---|---|---|---|
| **Postgres** (pgvector + pg_cron) | `fiap-postgres` | `5432` | Banco único de todas as stacks |
| **Ollama** | `fiap-ollama` | `11434` | Servidor de LLM e embeddings, em CPU |
| **Open WebUI** | `fiap-open-webui` | `3000` | Interface de chat das aulas |
| **Pipelines** | `fiap-pipelines` | `9099` | Plugins do Open WebUI (mem0 + Firecrawl) |
| **ChromaDB** | `fiap-chromadb` | `8000` | Vector store do RAG (Aulas 07–12) |
| **SearXNG** | `fiap-searxng` | `8080` | Metabuscador self-hosted, sem API key |
| **Valkey** | `searxng-valkey` | — | Cache do SearXNG |
| **mem0** | `fiap-mem0` | `8100` | Memória de longo prazo de agentes |
| **Firecrawl API** | `fiap-firecrawl-api` | `3002` | Scrape/crawl de páginas em markdown |
| **Firecrawl Playwright** | `fiap-firecrawl-playwright` | — | Navegador headless do Firecrawl |
| **Firecrawl Redis** | `fiap-firecrawl-redis` | — | Rate limit e cache do Firecrawl |
| **Firecrawl RabbitMQ** | `fiap-firecrawl-rabbitmq` | `15672` | Broker da fila NuQ (painel: `guest`/`guest`) |

Fora do `complete`, no perfil `langfuse` (ver [§ 6.1](#61-langfuse-perfil-langfuse)):

| Serviço | Container | Porta host | Papel |
|---|---|---|---|
| **Langfuse Web** | `fiap-langfuse-web` | `3001` | Interface, API pública e migrações do boot |
| **Langfuse Worker** | `fiap-langfuse-worker` | — | Consome a fila e grava os traces no ClickHouse |
| **Langfuse ClickHouse** | `fiap-langfuse-clickhouse` | — | Armazena traces, observações e scores |
| **Langfuse Redis** | `fiap-langfuse-redis` | — | Fila BullMQ entre web e worker |
| **Langfuse MinIO** | `fiap-langfuse-minio` | `9090` / `9091` | Object storage S3-compatible (API / console) |

Todos os containers sobem com `restart: unless-stopped` — reiniciam sozinhos junto com o Docker e só ficam parados se você mandar parar.

Rede interna: `fiap-ai-net`. Dentro dela os serviços se enxergam pelo **nome do serviço** (`ollama`, `postgres`, `chromadb`, `mem0`, `firecrawl-api`, `searxng`, `open-webui`).

> **Não há Jupyter.** As interfaces das aulas são feitas em código, com **Gradio** e **Streamlit** (Aula 09), rodando fora do Docker ou no Colab, apontando para as portas publicadas aqui.

---

## 2. Perfis

O compose usa [profiles](https://docs.docker.com/compose/how-tos/profiles/). Toda a **base** (`postgres` + `ollama` + `open-webui`) entra em **todos** os perfis — o Open WebUI está sempre no ar e já configurado, independente do que mais você subir.

| Perfil | Sobe | Quando usar |
|---|---|---|
| `minimum` | postgres, ollama, open-webui | Máquina fraca, Aulas 01–04. Só chat com o modelo local. |
| `complete` | tudo (12 containers) | Aula normal, todas as integrações ligadas. |
| `rag` | base + pipelines + chromadb | Aulas de RAG isoladas (07, 08). |
| `search` | base + pipelines + chromadb + searxng + valkey | Aula de busca web. |
| `memory` | base + pipelines + chromadb + mem0 | Aula de memória de agentes (11). |
| `crawl` | base + pipelines + chromadb + firecrawl (4 containers) | Aula de ingestão de dados web. |
| `langfuse` | base + Langfuse self-hosted (5 containers) | Observabilidade dos traces. **Fora do `complete`.** |

Regras que importam:

- **Perfis somam.** `docker compose --profile rag --profile memory up -d` sobe as duas stacks.
- **`langfuse` não entra no `complete` de propósito.** São 5 containers e ~5 GB de RAM a mais, e nem toda aula precisa de tracing. Para usar junto com o resto, some os perfis: `docker compose --profile complete --profile langfuse up -d`.
- **`chromadb` e `pipelines` entram em todo perfil que não seja `minimum`.** O ChromaDB porque o Open WebUI configurado com `VECTOR_DB=chroma` **não sobe** se o serviço não existir; o Pipelines para o endpoint OpenAI-compatible da interface não apontar para o vazio.
- **Nunca misture `minimum` com outro perfil.** Existem duas variantes do mesmo serviço — `open-webui` (perfil `minimum`) e `open-webui-full` (demais perfis) — compartilhando de propósito o mesmo `container_name`, a mesma porta e o **mesmo volume**, para contas e chats sobreviverem à troca de perfil. Só uma pode rodar por vez.

---

## 3. Requisitos

- **Docker Desktop** (ou Docker Engine + Compose v2). O `depends_on: required: false` usado aqui exige **Compose ≥ 2.20**.
- **CPU:** qualquer x86_64 ou Apple Silicon. Não precisa de GPU — o Ollama roda em CPU, e é por isso que os modelos padrão são pequenos.
- **RAM e disco:** dependem do perfil. Ver as tabelas abaixo.

### 3.1 Resumo por perfil

| Perfil | RAM em uso | RAM da máquina | Disco (imagens + volumes) | Disco livre a reservar |
|---|---|---|---|---|
| `minimum` | ~3,2 GB | **8 GB** | ~21 GB | **30 GB** |
| `rag` | ~3,9 GB | 8 GB | ~26 GB | 35 GB |
| `search` | ~4,3 GB | 8 GB | ~27 GB | 35 GB |
| `memory` | ~5,8 GB | **16 GB** | ~28 GB | 40 GB |
| `crawl` | ~7,5 GB (pico 11 GB) | **16 GB** | ~30 GB | 40 GB |
| `complete` | ~10 GB (pico 14 GB) | **16 GB** (confortável: 32 GB) | ~33 GB | **45 GB** |
| `langfuse` | ~8 GB (pico 10 GB) | **16 GB** | ~33 GB | 45 GB |
| `complete` + `langfuse` | ~15 GB (pico 19 GB) | **32 GB** | ~37 GB | **60 GB** |

A diferença entre "RAM em uso" e "RAM da máquina" é o sistema operacional, a VM do Docker Desktop e o navegador com o Open WebUI aberto.

> **`complete` + `langfuse` em 16 GB fica apertado.** Ou você roda os dois numa máquina de 32 GB, ou sobe `langfuse` sozinho (ele já traz a base com Ollama e Open WebUI) e baixa `LANGFUSE_CLICKHOUSE_MEM` para `2g`.

### 3.2 De onde vem a RAM

O maior consumidor não é container nenhum: são os **modelos carregados no Ollama**. Com `OLLAMA_KEEP_ALIVE=24h` (o padrão daqui) o modelo **não é descarregado** entre as perguntas — isso deixa a aula fluida, mas mantém a memória ocupada o dia inteiro.

| Processo | RAM típica | Observação |
|---|---|---|
| Ollama — `qwen3.5:0.8b` carregado | ~1,2 GB | modelo de chat |
| Ollama — `qwen3-embedding:0.6b` carregado | ~1,0 GB | fica residente por causa do RAG |
| Ollama — `llama3.2:1b` carregado | ~1,5 GB | só nos perfis `memory` e `complete` (extrator do mem0) |
| Open WebUI | 0,6–0,9 GB | embeddings ficam no Ollama, não aqui |
| Firecrawl API | 1,5–2,5 GB | **teto rígido de 4 GB** (`FIRECRAWL_API_MEM`) |
| Firecrawl Playwright | 0,8–1,5 GB | **teto rígido de 2 GB** (`FIRECRAWL_PW_MEM`) |
| Pipelines | 0,3–0,5 GB | |
| RabbitMQ | 0,3–0,5 GB | VM do Erlang |
| SearXNG (4 workers × 4 threads) | 0,3–0,4 GB | |
| mem0 | 0,25–0,4 GB | |
| ChromaDB | 0,2–0,4 GB | cresce com o tamanho do índice |
| Postgres | 0,1–0,2 GB | |
| Redis / Valkey | ~0,05 GB cada | |
| Langfuse ClickHouse | 1,5–3 GB | **teto de 4 GB** (`LANGFUSE_CLICKHOUSE_MEM`); é o maior da stack |
| Langfuse Web | 0,6–1,5 GB | **teto de 2 GB** (`LANGFUSE_WEB_MEM`); Next.js |
| Langfuse Worker | 0,5–1,2 GB | **teto de 2 GB** (`LANGFUSE_WORKER_MEM`) |
| Langfuse MinIO | 0,1–0,3 GB | **teto de 1 GB** (`LANGFUSE_MINIO_MEM`) |

Como cortar RAM sem trocar de perfil:

```bash
OLLAMA_KEEP_ALIVE=5m       # descarrega o modelo entre as perguntas
FIRECRAWL_WORKERS=2        # padrão daqui é 4; o oficial é 8
FIRECRAWL_BROWSERS=1       # menos abas do Playwright
FIRECRAWL_API_MEM=2g
FIRECRAWL_PW_MEM=1g
SEARXNG_WORKERS=2
LANGFUSE_CLICKHOUSE_MEM=2g # só se o perfil langfuse estiver no ar
```

### 3.3 De onde vem o disco

Tamanhos **descompactados**, medidos com `docker image ls`:

| Imagem | Tamanho | Perfis |
|---|---|---|
| `fiap-ollama-cpu` | 10,6 GB | todos |
| `open-webui:main` | 7,16 GB | todos |
| `pipelines:main` | 4,81 GB | todos menos `minimum` |
| `firecrawl/playwright-service` | 2,03 GB | `crawl`, `complete` |
| `firecrawl:2.11.14` | 1,63 GB | `crawl`, `complete` |
| `chromadb/chroma` | 826 MB | todos menos `minimum` |
| `fiap-postgres` | ~700 MB | todos |
| `fiap-mem0` | 480 MB | `memory`, `complete` |
| `rabbitmq:3-management` | 392 MB | `crawl`, `complete` |
| `searxng` | 375 MB | `search`, `complete` |
| `redis:alpine` | 134 MB | `crawl`, `complete` |
| `valkey:9-alpine` | ~40 MB | `search`, `complete` |
| **Soma do `complete`** | **~29 GB** | |
| `clickhouse-server:25.12` | ~1,1 GB | `langfuse` |
| `langfuse/langfuse:4` | ~1,0 GB | `langfuse` (web) |
| `langfuse/langfuse-worker:4` | ~900 MB | `langfuse` |
| `chainguard/minio` | ~180 MB | `langfuse` |
| `redis:7` | ~150 MB | `langfuse` |
| **Delta do `langfuse`** | **~3,3 GB** | soma-se ao valor acima |

A imagem do Ollama é grande porque carrega as bibliotecas de GPU (CUDA/ROCm) mesmo em execução por CPU.

Volumes, num laboratório recém-criado:

| Volume | Tamanho inicial | Cresce com |
|---|---|---|
| `fiap_ollama_data` | 1,6 GB (`minimum`) · 2,9 GB (`complete`) | cada modelo em `EXTRA_MODELS` |
| `fiap_openwebui_data` | ~280 MB | uploads e arquivos anexados |
| `fiap_postgres_data` | ~80 MB | chats, memórias e a fila de crawling |
| `fiap_chromadb_data` | 0 | cada documento indexado no RAG |
| `fiap_rabbitmq_data` | ~50 MB | fila em trânsito |
| `mem0`, `searxng`, `valkey` | ~0 | histórico e cache |
| `fiap_langfuse_clickhouse_data` | ~100 MB | **cada trace registrado** — o que mais cresce no perfil `langfuse` |
| `fiap_langfuse_minio_data` | ~10 MB | um blob por evento de ingestão, antes de virar linha no ClickHouse |
| `fiap_langfuse_redis_data` | ~10 MB | fila em trânsito |

Um trace de LLM ocupa de 2 a 50 KB no ClickHouse, dependendo do tamanho do prompt e da resposta. Uma turma de 40 alunos rodando exercícios com tracing ligado gera de **200 MB a 1 GB por semestre**.

Modelos padrão baixados: `qwen3.5:0.8b` (610 MB) e `qwen3-embedding:0.6b` (990 MB); nos perfis `memory` e `complete`, mais `llama3.2:1b` (1,3 GB). Cada modelo extra de 7–8 B custa **4 a 6 GB** a mais.

Ao longo de um semestre, com PDFs indexados e turmas usando a interface, some **2 a 5 GB** aos números acima.

> **Docker Desktop no macOS:** o `Docker.raw` **não encolhe sozinho** quando você apaga imagens. Reserve folga sobre o valor da tabela e leia [Disco cheio](#disco-cheio) — quase todo erro esquisito deste stack começa por aí.

---

## 4. Setup e primeiro uso

### 4.1 Subir pela primeira vez

```bash
cd fiap-ai-lab-complete
make up
```

Só isso. O alvo `up` chama `setup` antes (cria o `.env` a partir do `.env.example`, com `WEBUI_SECRET_KEY`, `SEARXNG_SECRET` e os segredos do Langfuse gerados por `openssl rand -hex 32`), constrói as três imagens locais, sobe o perfil `complete` e imprime as URLs.

**O primeiro boot é lento e isso é normal.** São dois tempos somados: o build das imagens (5 a 15 min) e o download dos modelos do Ollama (~2,9 GB). Enquanto o modelo não terminar de baixar, a interface abre mas o chat responde erro. Acompanhe:

```bash
make logs-ollama     # espere o bloco "Modelos disponíveis:" no fim
make ps              # todos os containers devem estar (healthy)
```

Se quiser separar as etapas:

```bash
make setup    # só o .env
make build    # só as imagens
make up       # sobe
```

> Já tem um `.env`? O `make setup` **não sobrescreve** — ele avisa e sai. Para regerar, apague o arquivo antes (você perde as chaves atuais do Langfuse).

### 4.2 Primeiro acesso ao Open WebUI

1. Abra **http://localhost:3000**.
2. **Crie a primeira conta.** Ela vira a administradora da instância — use o seu e-mail, não o de um aluno.
3. Depois de criar a sua, feche o cadastro para a turma não virar bagunça: no `.env`, `ENABLE_SIGNUP=false` e `make restart`. (Nesta máquina já vem `false`.)
4. O seletor já vem em `qwen3.5:0.8b` (`DEFAULT_MODELS`). O `qwen3-embedding:0.6b` aparece na mesma lista, mas **não use em chat**: é modelo de embedding, e o Open WebUI já o usa por baixo no RAG (`RAG_EMBEDDING_MODEL`). Escolhido como modelo de conversa, ele devolve vetor, não texto.
5. Teste o caminho todo: mande uma pergunta qualquer, ligue **Web Search** na caixa de mensagem e mande outra. Se as duas responderem, Ollama e SearXNG estão de pé.

Um comando confirma o resto sem clicar em nada:

```bash
make health     # ping em cada endpoint publicado
make test       # integração ponta a ponta (leva ~2 min)
```

### 4.3 Qual perfil usar em cada aula

Suba **um** perfil por vez. Perfis somam entre si (`--profile A --profile B`), menos o `minimum`, que nunca se mistura.

| Aulas | Comando | Por quê |
|---|---|---|
| 01–04 · prompting, segurança, ética, context engineering | `make up-minimum` | Só precisa do modelo e do chat. Roda em 8 GB. |
| 05–06 · LangChain, chatbots | `make up-rag` | Chains e memory; o ChromaDB já fica pronto para a aula seguinte. |
| 07–08 · embeddings, RAG, RAGAS | `make up-rag` | Vector store no ar, indexação pela interface e pelo código. |
| 09 · Gradio e Streamlit | `make up-rag` | As interfaces rodam **fora** do Docker, apontando para `localhost`. |
| 10–12 · agentes, tools, RAG como tool | `make up` (complete) | Agente precisa de busca, memória e crawling ao mesmo tempo. |
| 13–14 · LangGraph, multiagentes, tendências | `make up` (complete) | Idem, com traces para mostrar o loop agêntico. |
| Qualquer aula com observabilidade | `+ make up-langfuse` | Mostra o trace de cada chamada. Ver [§ 6.1](#61-langfuse-perfil-langfuse). |

Aula isolada de uma stack só: `make up-search` (busca web), `make up-memory` (mem0), `make up-crawl` (Firecrawl).

### 4.4 Rotina de uma aula

```bash
# véspera — deixe as imagens e os modelos baixados
make up && make test

# início da aula
make down          # obrigatório se o perfil de ontem era outro
make up-rag        # o perfil da aula de hoje
make urls          # projete esta saída: é o mapa de portas da turma

# durante — se algo travar
make ps            # quem não está (healthy)
make logs-webui    # ou logs-ollama, logs-mem0, logs-firecrawl...

# fim da aula
make down          # derruba os containers; chats, modelos e vetores ficam
```

**Trocar de perfil exige `make down` antes.** Existem duas variantes do Open WebUI (`minimum` e as demais) dividindo o mesmo `container_name` e o mesmo volume — só uma pode rodar por vez.

`make down` preserva tudo. Quem apaga é o `make down-volumes`: modelos, contas, chats, memórias e vetores, sem confirmação.

### 4.5 Sem `make`

```bash
cp .env.example .env
# edite WEBUI_SECRET_KEY e SEARXNG_SECRET (openssl rand -hex 32)
docker compose --profile complete up -d --build
docker compose --profile complete down
```

O `Makefile` é só um atalho — todo alvo é uma linha de `docker compose` com os perfis certos. Ver [§ 12](#12-comandos-do-makefile).

---

## 5. Build

Três imagens são construídas localmente; o resto vem pronto do registry.

| Imagem | Contexto | Por quê é build local |
|---|---|---|
| `fiap-postgres:latest` | `./postgres` | pgvector **+ pg_cron** + criação automática dos bancos + schema da fila NuQ do Firecrawl |
| `fiap-ollama-cpu:latest` | `./ollama` | Entrypoint que baixa `CHAT_MODEL`, `EMBEDDING_MODEL` e `EXTRA_MODELS` no primeiro boot |
| `fiap-mem0:latest` | `./mem0` | A imagem oficial `mem0/mem0-api-server` só é publicada para `linux/arm64`; aqui a biblioteca `mem0ai` é empacotada com um servidor FastAPI próprio |

```bash
make build            # imagens do perfil complete
make build-minimum    # só postgres + ollama
docker compose --profile complete build --no-cache postgres   # forçar rebuild de uma
```

O `postgres/Dockerfile` baixa o `nuq.sql` direto do repositório do Firecrawl na tag `v${FIRECRAWL_VERSION}`. **A tag da imagem não tem `v`, a tag do git tem** (`2.11.14` vs `v2.11.14`) — o `v` é acrescentado só na URL. Ao trocar de versão, mude os dois no mesmo commit: aplicação e schema da fila precisam casar.

---

## 6. Como subir cada perfil

```bash
make up            # = up-complete
make up-minimum
make up-rag
make up-search
make up-memory
make up-crawl
make up-langfuse   # observabilidade (fora do complete)

make ps            # status
make urls          # o que está no ar e em qual porta
make health        # bate em cada endpoint publicado
make down          # derruba tudo (dados preservados)
make down-volumes  # derruba e APAGA modelos, chats, banco e vetores
```

Trocar de perfil:

```bash
make down          # sempre derrube antes de trocar
make up-rag
```

Somar stacks sem `make`:

```bash
docker compose --profile memory --profile crawl up -d
```

### 6.1 Langfuse (perfil langfuse)

O [Langfuse](https://langfuse.com/self-hosting) é a plataforma de observabilidade de LLM usada aqui: cada chamada de modelo, chain, retriever ou tool vira um **trace** navegável, com prompt, resposta, latência, tokens e custo. Também traz datasets, experimentos, anotação, prompt management e LLM-as-a-judge.

Por que Langfuse e não LangSmith self-hosted: o [LangSmith self-hosted](https://docs.langchain.com/langsmith/self-hosted) é **add-on Enterprise** — sem `LANGSMITH_LICENSE_KEY` válida os containers sobem e morrem em loop — e a instalação oficial é só Helm/Kubernetes. O **core do Langfuse é MIT**: roda self-hosted sem licença, sem chave e sem custo, com `docker-compose.yml` oficial publicado. Isso respeita a regra de custo zero da disciplina. Comparação da própria Langfuse: [langfuse.com/resources/engineering/langsmith-alternative](https://langfuse.com/resources/engineering/langsmith-alternative).

Três coisas que valem saber antes de subir:

1. **São dois processos e três datastores.** `langfuse-web` (interface + API pública) e `langfuse-worker` (consome a fila), mais ClickHouse (traces), Redis (fila BullMQ) e MinIO (blobs).
2. **MinIO é obrigatório, não opcional.** Todo evento de ingestão vira um blob no S3 **antes** de virar linha no ClickHouse. Sem o MinIO no ar a ingestão falha silenciosamente — o trace nunca aparece na interface.
3. **As migrações rodam dentro do `langfuse-web`.** Não existe container de migração: no primeiro boot o web aplica o schema do Postgres e do ClickHouse antes de abrir a porta. É por isso que o healthcheck tem `start_period: 120s`.

Subindo:

```bash
# 1. gere os segredos (o make setup já faz isso)
#    LANGFUSE_SALT / LANGFUSE_ENCRYPTION_KEY / LANGFUSE_NEXTAUTH_SECRET

# 2. suba (o make recusa se a ENCRYPTION_KEY estiver com o placeholder)
make up-langfuse

# 3. o primeiro boot roda as migrações — leva alguns minutos
make logs-langfuse
```

Interface em **http://localhost:3001** (a `3000` já é do Open WebUI). Console do MinIO em **http://localhost:9091**.

Login: as variáveis `LANGFUSE_INIT_*` do `.env` criam **no primeiro boot** a organização, o projeto, o usuário administrador e o par de chaves de API — sem clicar em nada. Entre com `LANGFUSE_ADMIN_EMAIL` e `LANGFUSE_ADMIN_PASSWORD`.

> **`LANGFUSE_SALT` e `LANGFUSE_ENCRYPTION_KEY` são imutáveis na prática.** O salt deriva o hash das API keys e a encryption key cifra os segredos gravados no banco. Trocar qualquer um dos dois depois do primeiro boot invalida de uma vez tudo o que já foi gravado.

Ollama no Playground e no LLM-as-a-judge: o Langfuse **bloqueia hosts de rede privada** por padrão, e `ollama` é um deles. Por isso o `LANGFUSE_LLM_CONNECTION_WHITELISTED_HOST=ollama` já vem no compose — sem ele a conexão de LLM é recusada antes de sair.

Onde ficam os dados: o Postgres é o **mesmo** de todo o resto (banco `langfuse`, criado pelo `EXTRA_DATABASES`) e guarda usuários, projetos, prompts e datasets; os traces vão para um **ClickHouse dedicado**, porque é um banco colunar e o volume de traces derruba qualquer Postgres em pouco tempo.

---

## 7. Postgres unificado

Um único servidor Postgres 17 atende **todas** as stacks. Isso é deliberado: em aula dá para abrir um `psql` e mostrar, lado a lado, o chat do Open WebUI, os vetores da memória e a fila de crawling.

| Banco | Dono | Conteúdo |
|---|---|---|
| `postgres` | Firecrawl | Fila **NuQ** (precisa da extensão `pg_cron`) |
| `openwebui` | Open WebUI | Contas, chats, prompts, configurações |
| `mem0` | mem0 | Memórias vetoriais (extensão `pgvector`) |
| `langfuse` | Langfuse | Organizações, projetos, usuários, prompts, datasets e API keys (só no perfil `langfuse`; os traces vão para o ClickHouse) |

A imagem é `pgvector/pgvector:pg17` + `pg_cron`. O `postgres/init/000-databases.sh` cria os bancos de `EXTRA_DATABASES` e habilita `CREATE EXTENSION vector` em cada um. **Esses scripts só rodam no primeiro boot**, quando o volume `fiap_postgres_data` está vazio.

```bash
make databases     # lista bancos e extensões
make psql          # abre o psql

# de fora do Docker:
psql postgresql://fiap:fiap2026@localhost:5432/openwebui
```

Inspeções úteis em aula:

```sql
\c openwebui
SELECT id, title, created_at FROM chat ORDER BY created_at DESC LIMIT 5;

\c mem0
SELECT id, payload->>'data' AS memoria FROM fiap_memories LIMIT 10;

\c postgres
SELECT status, count(*) FROM nuq.queue_scrape GROUP BY status;
```

---

## 8. Integrações do Open WebUI

Nada precisa ser clicado na interface: tudo abaixo já vem ligado por variável de ambiente.

### 8.1 Vector store no ChromaDB

`VECTOR_DB=chroma` + `CHROMA_HTTP_HOST=chromadb`. Todo documento que o aluno anexa a um chat vira embedding no **mesmo** ChromaDB que o código das aulas usa — dá para consultar a coleção por fora e mostrar o que a interface guardou.

### 8.2 Busca web no SearXNG

`ENABLE_WEB_SEARCH=true` + `WEB_SEARCH_ENGINE=searxng`. Na caixa de mensagem, ligue **Web Search** e pergunte. Sem API key, sem cota. `WEB_SEARCH_RESULT_COUNT=5` por padrão — valores altos estouram o context window dos modelos pequenos.

### 8.3 Pipelines: memória e Firecrawl

O container `pipelines` é registrado como endpoint OpenAI-compatible (`OPENAI_API_BASE_URLS=http://pipelines:9099`). Ele carrega automaticamente os `.py` de `./pipelines`:

| Arquivo | Tipo | Como aparece |
|---|---|---|
| `mem0_memory_filter.py` | `filter` | **Mem0 Memory** — em *Admin → Pipelines*, aplicado a todos os modelos |
| `firecrawl_web_pipe.py` | `pipe` | **Firecrawl Web** — aparece como um modelo no seletor |

**Mem0 Memory** intercepta cada mensagem: no `inlet` busca memórias do usuário e injeta no system prompt; no `outlet` grava a conversa. Toda chamada de rede é protegida — se o perfil `memory` não estiver no ar, o chat continua funcionando normalmente, apenas sem memória.

**Firecrawl Web** é usado como modelo. Sintaxe:

```
https://python.langchain.com/docs/introduction/  o que é LCEL?
/map https://ragas.io
```

Ele faz o scrape em markdown, corta em `MAX_CHARS` e manda para o Ollama responder. As valves (URL base, modelo, limite de caracteres) são editáveis em *Admin → Pipelines*.

---

## 9. Usar cada stack no código das aulas

Do **seu computador** (Gradio, Streamlit, script solto), use `localhost` + a porta publicada. De **dentro da rede** `fiap-ai-net`, use o nome do serviço — e aí a porta é a **interna**, que nem sempre é a mesma.

| Serviço | Do seu computador | De dentro da `fiap-ai-net` |
|---|---|---|
| Ollama | `http://localhost:11434` | `http://ollama:11434` |
| Open WebUI | `http://localhost:3000` | `http://open-webui:8080` |
| ChromaDB | `http://localhost:8000` | `http://chromadb:8000` |
| Pipelines | `http://localhost:9099` | `http://pipelines:9099` |
| SearXNG | `http://localhost:8090` * | `http://searxng:8080` |
| mem0 | `http://localhost:8100` | `http://mem0:8000` |
| Firecrawl | `http://localhost:3002` | `http://firecrawl-api:3002` |
| Langfuse | `http://localhost:3001` | `http://langfuse-web:3000` |
| Postgres | `localhost:5432` | `postgres:5432` |

\* padrão da disciplina é `8080`; **nesta máquina** o `.env` usa `8090` porque a 8080 está ocupada por outro container.

No Colab, `localhost` não existe — o notebook roda na nuvem, não na sua máquina. Para a turma alcançar estes serviços, exponha a porta com um túnel (ngrok) e troque o host pela URL pública.

### Ollama — LLM e embeddings

```python
from langchain_ollama import ChatOllama, OllamaEmbeddings

llm = ChatOllama(
    base_url="http://localhost:11434",
    model="qwen3.5:0.8b",
    temperature=0.2,
    reasoning=False,   # Qwen3/DeepSeek-R pensam por padrão e travam a demo em CPU
)
emb = OllamaEmbeddings(base_url="http://localhost:11434", model="qwen3-embedding:0.6b")
```

```bash
make models              # lista o que já está baixado
make pull M=qwen3:8b     # baixa outro modelo
```

### ChromaDB — RAG

```python
import chromadb
from langchain_chroma import Chroma

client = chromadb.HttpClient(host="localhost", port=8000)
vs = Chroma(client=client, collection_name="aula07", embedding_function=emb)
vs.add_texts(["FIAP fica na Avenida Paulista."])
print(vs.similarity_search("onde fica a FIAP?", k=1))
```

### SearXNG — busca web

```python
from langchain_community.utilities import SearxSearchWrapper

s = SearxSearchWrapper(searx_host="http://localhost:8090")   # veja SEARXNG_PORT no .env
print(s.run("o que é context engineering"))
```

### mem0 — memória de longo prazo

API REST em `http://localhost:8100` (Swagger em `/docs`).

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/health` | Estado do serviço e do banco |
| `GET` | `/config` | Modelos e coleção em uso |
| `POST` | `/memories` | Extrai e grava fatos de uma conversa |
| `GET` | `/memories?user_id=` | Lista as memórias do usuário |
| `POST` | `/search` | Busca semântica |
| `DELETE` | `/memories/{id}` | Apaga uma memória |
| `DELETE` | `/memories?user_id=` | Apaga todas do usuário |

```python
import requests

BASE = "http://localhost:8100"
requests.post(f"{BASE}/memories", json={
    "messages": [
        {"role": "user", "content": "Prefiro respostas curtas e em português."},
    ],
    "user_id": "aluno_01",
})
print(requests.post(f"{BASE}/search", json={"query": "como responder?", "user_id": "aluno_01"}).json())
```

O modelo que **extrai** os fatos (`MEM0_LLM_MODEL`) precisa devolver JSON limpo. Modelos com *thinking* ligado por padrão escrevem o raciocínio antes do JSON e quebram o parser — por isso o padrão é `llama3.2:1b`.

### Firecrawl — crawling

API em `http://localhost:3002`, sem autenticação (`USE_DB_AUTHENTICATION=false`).

```python
import requests

FC = "http://localhost:3002"

# uma página em markdown
r = requests.post(f"{FC}/v2/scrape", json={
    "url": "https://ragas.io",
    "formats": ["markdown"],
    "onlyMainContent": True,
})
print(r.json()["data"]["markdown"][:500])

# descobrir as URLs de um site
print(requests.post(f"{FC}/v2/map", json={"url": "https://ragas.io"}).json())

# crawl assíncrono — entra na fila NuQ do Postgres
job = requests.post(f"{FC}/v2/crawl", json={"url": "https://ragas.io", "limit": 10}).json()
print(requests.get(f"{FC}/v2/crawl/{job['id']}").json()["status"])
```

Com o SDK oficial:

```python
from firecrawl import FirecrawlApp
app = FirecrawlApp(api_url="http://localhost:3002", api_key="nao-usado")
```

Pipeline típico da disciplina: **Firecrawl** extrai markdown → *chunking* → **Ollama** gera embeddings → **ChromaDB** indexa → agente responde com **mem0** lembrando do aluno.

### Langfuse — observabilidade dos traces

As chaves já existem: as variáveis `LANGFUSE_PUBLIC_KEY` e `LANGFUSE_SECRET_KEY` do `.env` são criadas no primeiro boot pelo bootstrap. (Para gerar outras: **Settings → API Keys**, em http://localhost:3001.)

```bash
pip install langfuse langchain-ollama
```

Com LangChain, o `CallbackHandler` instrumenta a chain inteira — **nenhuma linha da lógica muda**:

```python
import os

os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-..."
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-..."
os.environ["LANGFUSE_HOST"]       = "http://localhost:3001"

from langfuse.langchain import CallbackHandler
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

chain = ChatPromptTemplate.from_template("Explique {tema} em uma frase.") | ChatOllama(
    model="qwen3.5:0.8b",
    base_url="http://localhost:11434",
)

# metadata separa os traces por aula — sem isso a turma vira uma lista só
chain.invoke(
    {"tema": "embeddings"},
    config={
        "callbacks": [CallbackHandler()],
        "metadata": {"langfuse_session_id": "aula-07-rag"},
    },
)
```

Do Colab, troque `localhost` pela URL pública do túnel; de outro container na `fiap-ai-net`, use `http://langfuse-web:3000`.

Para instrumentar código que **não** é LangChain, o decorador `@observe` resolve:

```python
from langfuse import observe

@observe(name="pipeline_rag")
def responder(pergunta: str) -> str:
    ...
```

> **O trace não aparece na hora.** O SDK envia em lote e o worker ainda precisa consumir a fila. Em script curto, chame `langfuse.flush()` (ou use o client como context manager) antes de o processo morrer — senão o último lote se perde.

### Postgres

```python
import psycopg2
conn = psycopg2.connect("postgresql://fiap:fiap2026@localhost:5432/mem0")
```

---

## 10. Variáveis de ambiente

Tudo mora no `.env` (criado por `make setup`). O `.env.example` é a referência comentada. Portas do lado esquerdo são as do **seu computador** — se alguma estiver ocupada, troque só o número, nada dentro dos containers muda.

Os que mais importam:

| Variável | Padrão | Efeito |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | `fiap` / `fiap2026` | Credenciais do banco unificado |
| `WEBUI_POSTGRES_DB` / `MEM0_POSTGRES_DB` | `openwebui` / `mem0` | Bancos criados no primeiro boot |
| `CHAT_MODEL` | `qwen3.5:0.8b` | Modelo baixado e padrão da interface |
| `EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | Embeddings do RAG (1024 dimensões) |
| `EXTRA_MODELS` | vazio | Modelos extras, separados por vírgula |
| `WEBUI_SECRET_KEY` | — | **Troque.** Assina as sessões de login |
| `SEARXNG_SECRET` | — | **Troque.** `openssl rand -hex 32` |
| `MEM0_LLM_MODEL` | `llama3.2:1b` | Extrator de fatos; precisa ser sem *thinking* |
| `MEM0_EMBEDDING_DIMS` | `1024` | Precisa bater com o `EMBEDDING_MODEL` |
| `FIRECRAWL_VERSION` | `2.11.14` | Tag da imagem **e** (com `v`) do schema NuQ |
| `FIRECRAWL_WORKERS` | `4` | Padrão oficial é 8; derruba máquina que roda Ollama em CPU |
| `LANGFUSE_PORT` | `3001` | Interface do Langfuse; a `3000` é do Open WebUI |
| `LANGFUSE_VERSION` | `4` | Major das imagens `langfuse` e `langfuse-worker` |
| `LANGFUSE_SALT` / `LANGFUSE_ENCRYPTION_KEY` | gerados | **Não troque depois do primeiro boot** — invalida API keys e segredos gravados |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | gerados | As chaves que o SDK das aulas usa |
| `LANGFUSE_ADMIN_EMAIL` / `LANGFUSE_ADMIN_PASSWORD` | — | Login criado no primeiro boot pelo bootstrap |
| `LANGFUSE_WHITELISTED_HOST` | `ollama` | Sem isso o Playground não alcança o Ollama (host de rede privada) |
| `LANGFUSE_CLICKHOUSE_MEM` | `4g` | Maior consumidor do perfil; `2g` numa máquina de 16 GB |

`SEARXNG_PORT` já vem como `8090` no `.env` desta máquina — a `8080` está ocupada por outro container.

---

## 11. Testes

```bash
make health     # ping em cada endpoint publicado
make test       # integração ponta a ponta, vista do SEU computador
make test-net   # o mesmo, de dentro da rede fiap-ai-net
```

O `scripts/integration_test.py` usa **só a biblioteca padrão** do Python — nada para instalar. Ele lê o `.env`, pula o que não pertence ao perfil ativo e verifica:

- Postgres aceitando conexão
- Ollama com os modelos baixados, respondendo chat e gerando embeddings da dimensão certa
- Open WebUI `/health`
- ChromaDB heartbeat
- Pipelines expondo `mem0_memory_filter` e `firecrawl_web`
- SearXNG devolvendo JSON
- mem0: ciclo completo gravar → buscar → apagar
- Firecrawl: scrape de página real e enfileiramento de crawl (prova que a fila NuQ está no Postgres unificado)
- Langfuse: `/api/public/health` (prova que as migrações terminaram) e um trace de verdade gravado por `/api/public/ingestion` (prova o caminho web → MinIO → Redis → worker → ClickHouse)

`make test-net` é o que vale para o código das aulas: valida os hostnames internos, que é como as aplicações enxergam os serviços.

---

## 12. Comandos do Makefile

```
setup           Cria .env com segredos aleatórios
build           Constrói as imagens do perfil complete
build-minimum   Constrói apenas postgres + ollama

up              Sobe o perfil COMPLETE
up-minimum      postgres + ollama + open-webui
up-rag          base + ChromaDB
up-search       base + SearXNG + Valkey
up-memory       base + mem0
up-crawl        base + Firecrawl
up-langfuse     base + Langfuse self-hosted (observabilidade)

down            Derruba os containers de todos os perfis
down-volumes    Derruba e APAGA os volumes
restart         down + up complete

ps              Status dos containers
urls            URLs de tudo que está no ar
logs            Logs de todos os serviços
logs-ollama | logs-webui | logs-searxng | logs-chromadb
logs-mem0   | logs-firecrawl | logs-pipelines | logs-postgres
logs-langfuse
health          Testa os endpoints publicados
test            Teste de integração (do seu computador)
test-net        Mesmo teste, de dentro da rede

models          Lista os modelos baixados
pull M=nome     Baixa um modelo
databases       Lista bancos e extensões
psql            Abre o psql
shell-ollama | shell-postgres
config          Valida o compose de TODOS os perfis
clean           down + remove as imagens construídas
```

---

## 13. Solução de problemas

### Disco cheio

O sintoma mais comum e o mais confuso: o Docker começa a devolver erros que **parecem** bug de configuração — `input/output error` no containerd, `eacces` lendo o `.erlang.cookie` do RabbitMQ, container morrendo sem log. Antes de investigar qualquer serviço, cheque o disco:

```bash
df -h /
docker system df
```

Para recuperar espaço, do menos para o mais destrutivo:

```bash
docker builder prune -af     # só cache de build — nenhum dado perdido
docker image prune -af       # imagens sem container — precisa rebaixar depois
make down-volumes            # APAGA modelos, chats, banco e vetores
```

No Docker Desktop, o arquivo `Docker.raw` não encolhe sozinho: depois do prune, reinicie o Docker Desktop para o espaço voltar ao macOS.

### Porta já em uso

```
Error: bind: address already in use
```

Troque **só o número da esquerda** no `.env` (`WEBUI_PORT`, `SEARXNG_PORT`, `CHROMADB_PORT`, `POSTGRES_HOST_PORT`…) e suba de novo. Para descobrir quem ocupa: `lsof -i :3000`.

### Open WebUI não sobe no perfil `complete`

Ele tem `CHROMA_HTTP_HOST` apontando para o `chromadb`. Se o ChromaDB não estiver no ar, o boot falha em vez de cair para o modo embutido. Confira `docker ps | grep chromadb` — e não misture `minimum` com outro perfil.

### Modelo não aparece na interface

O download acontece no primeiro boot e demora. `make logs-ollama` mostra o progresso; `make models` confirma o que já chegou.

### Resposta demorando muito / CPU a 100%

Modelos com *reasoning* ligado (Qwen3, DeepSeek-R) geram centenas de tokens de raciocínio antes de responder. Em CPU isso trava a aula. Use `reasoning=False` no LangChain ou `"think": false` na chamada crua da API.

### mem0 devolve 503

Ele inicializa preguiçosamente na primeira chamada: precisa do Postgres de pé e do `MEM0_LLM_MODEL` baixado. `make logs-mem0` mostra a causa. Se o modelo não veio, `make pull M=llama3.2:1b`.

### Firecrawl não fica saudável

O `harness` sobe vários processos antes de abrir a porta 3002 — o `start_period` é de 90s. Se persistir, verifique se o RabbitMQ está saudável (`docker ps`) e se o banco `postgres` tem o schema `nuq` (`make psql`, depois `\dn`). Volume do RabbitMQ corrompido por queda abrupta se resolve com `docker volume rm fiap_rabbitmq_data`.

### Os bancos `openwebui` / `mem0` não existem

Os scripts de `postgres/init/` rodam **uma única vez**, no primeiro boot com volume vazio. Se você mexeu neles depois:

```bash
docker compose --profile complete down
docker volume rm fiap_postgres_data     # apaga contas, chats e memórias
make up
```

### Pipelines não aparecem no Open WebUI

Confira `make logs-pipelines` e se `pipelines/*.py` estão montados. Em *Admin → Settings → Connections* deve existir a conexão `http://pipelines:9099` com a chave `PIPELINES_API_KEY`.

### Langfuse demora a abrir no primeiro boot

Esperado: as migrações do Postgres e do ClickHouse rodam **dentro** do `langfuse-web`, antes de a porta abrir. Alguns minutos é normal (o healthcheck dá 120 s de carência). Acompanhe com `make logs-langfuse`.

Se passar disso, o problema costuma ser o banco `langfuse` inexistente — os scripts de `postgres/init/` só rodam no primeiro boot, então um volume Postgres antigo não tem esse banco. Crie na mão:

```bash
make psql
CREATE DATABASE langfuse;
```

### Langfuse reiniciando em loop

```bash
docker logs fiap-langfuse-web 2>&1 | tail -30
```

Duas causas frequentes:

- **`LANGFUSE_ENCRYPTION_KEY` inválida.** Precisa ser exatamente 64 caracteres hexadecimais (`openssl rand -hex 32`). Valor curto ou com o placeholder derruba o processo no boot.
- **ClickHouse ou Redis fora do ar.** `docker compose ps` mostra quem não ficou `healthy`. O Redis **precisa** de `--maxmemory-policy noeviction`: com qualquer política de despejo o BullMQ perde jobs e o worker entra em erro.

### Traces não aparecem na interface

Na ordem:

1. **Chaves.** `LANGFUSE_PUBLIC_KEY` e `LANGFUSE_SECRET_KEY` do cliente têm de ser do projeto certo, e `LANGFUSE_HOST` tem de ser `http://localhost:3001` (sem `/api`).
2. **Flush.** Em script curto, o processo morre antes de o SDK enviar o lote. Chame `langfuse.flush()` no fim.
3. **MinIO.** Todo evento vira blob **antes** de virar linha no ClickHouse. Se `fiap-langfuse-minio` estiver fora, a ingestão aceita o lote e ele nunca chega ao destino:

```bash
docker logs fiap-langfuse-worker 2>&1 | grep -i "s3\|minio\|bucket"
```

### Playground e LLM-as-a-judge não alcançam o Ollama

O Langfuse **bloqueia hosts de rede privada** por padrão. A conexão só funciona com `LANGFUSE_LLM_CONNECTION_WHITELISTED_HOST=ollama` (já no compose) e com a URL base `http://ollama:11434/v1` — hostname interno, não `localhost`.

---

## 14. Estrutura de arquivos

```
fiap-ai-lab-complete/
├── docker-compose.yml          # todos os serviços e perfis
├── Makefile                    # atalhos de operação
├── .env.example                # referência comentada das variáveis
├── .env                        # local, não versionado
│
├── postgres/
│   ├── Dockerfile              # pgvector + pg_cron + schema NuQ
│   └── init/000-databases.sh   # cria openwebui, mem0 e langfuse; habilita pgvector
│
├── ollama/
│   ├── Dockerfile
│   └── entrypoint.sh           # baixa os modelos no primeiro boot
│
├── mem0/
│   ├── Dockerfile              # mem0ai + FastAPI (imagem oficial é só arm64)
│   └── app.py                  # API REST de memória
│
├── pipelines/
│   ├── mem0_memory_filter.py   # filter: injeta e grava memórias
│   └── firecrawl_web_pipe.py   # pipe: vira o modelo "Firecrawl Web"
│
├── searxng/settings.yml        # configuração do metabuscador
│
└── scripts/integration_test.py # teste ponta a ponta, sem dependências
```

---

*Prof. Jorge Luiz Gomes · profjorge.gomes@fiap.com.br*
*FIAP · Prompt Engineering and Artificial Intelligence · 2º Semestre 2026*
