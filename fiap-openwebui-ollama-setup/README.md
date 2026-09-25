# FIAP AI Lab — Open WebUI + Ollama (100% local)

Setup para rodar um chat de IA local (sem custo, sem API paga) na sua máquina.
Os containers são orquestrados por um `Makefile` com **profiles** do Docker Compose,
permitindo subir **um ou vários serviços de uma vez**.

O modelo de chat padrão é um **GGUF local** colocado em `models/`: no start dos
containers o Ollama importa **todos** os `.gguf` da pasta automaticamente, e o
principal vira o modelo padrão do Open WebUI. Embeddings, guardrails e extras
são baixados no mesmo boot, com a mesma lista do projeto `fiap-ai-lab-complete`.

---

## O que sobe

| Serviço | Container | O que é |
|---|---|---|
| `ollama` | `fiap-openwebui-ollama-ollama-1` | Servidor de modelos em **CPU**. Importa todos os `.gguf` de `models/`, baixa os embeddings (e a variante do RAG), os guardrails e os extras. |
| `ollama-gpu` | `fiap-openwebui-ollama-ollama-gpu-1` | Mesmo servidor, com **GPU NVIDIA** reservada. Porta `11435`. |
| `open-webui` | `fiap-openwebui-ollama-open-webui-1` | Interface de chat estilo ChatGPT, já conectada ao Ollama. |
| `open-webui-external` | `...-open-webui-external-1` | Mesma interface, apontando para um **Ollama fora do Docker**. |

Modelos padrão (definidos no `.env`):

- `CHAT_MODEL` → modelo de chat, padrão do Open WebUI
- `GGUF_FILE` / `GGUF_MODEL` → arquivo `.gguf` em `models/` e o nome que ele terá no Ollama
- `EMBEDDING_MODEL` → embeddings (usado no RAG do Open WebUI)

---

## Modelos

O stack sobe com **três grupos de modelos**, todos configurados no `.env`:

| Origem | Variáveis | Quando acontece |
|---|---|---|
| **`.gguf` locais** em `models/` | `GGUF_FILE`, `GGUF_MODEL` | Importados no boot — **todos** os `.gguf` da pasta, não só o principal |
| **Embeddings** | `EMBEDDING_MODEL`, `EMBEDDING_CONTEXT` | Baixados no boot + variante enxuta `-ctx<N>` usada no RAG |
| **Guardrails e extras** | `GUARDRAIL_MODELS`, `EXTRA_MODELS` | Baixados no boot (listas separadas por vírgula) |

Os últimos dois grupos usam a mesma lista do projeto `fiap-ai-lab-complete`,
para o comportamento em sala ser idêntico nos dois projetos.

### Modelo GGUF local

O modelo de chat padrão vem de um arquivo `.gguf` em `models/`:

```
models/MiniCPM5-2B-heretic-abliterated-Q4_K_M.gguf
```

A pasta `models/` é montada em `/models` (read-only) no container. No start, o
`entrypoint.sh` gera um `Modelfile` para **cada** `.gguf` da pasta e roda
`ollama create` — só nos que ainda não existem. Com os 5 arquivos do lab, todos
viram modelos no Open WebUI:

```
LFM2.5-2.6B-Uncensored-Q4_K_M
MiniCPM5-2B-heretic-abliterated-Q4_K_M      <- principal (CHAT_MODEL)
Qwen3-0.6B-heretic-abliterated-uncensored.Q4_K_M
Qwen3.8-2B-Uncensored-Q4_K_M
gemma-3-1b-it-heretic-extreme-uncensored-abliterated.i1-Q4_K_M
```

```bash
# 1. confira o que está na pasta e o que o .env espera
make gguf

# 2. suba os containers — os modelos são importados no start
make up

# 3. confira o que ficou instalado e teste tudo
make models
make test
```

Configuração no `.env`:

| Variável | Padrão | Para que serve |
|---|---|---|
| `GGUF_FILE` | `MiniCPM5-2B-heretic-abliterated-Q4_K_M.gguf` | Arquivo que satisfaz o `CHAT_MODEL` |
| `GGUF_MODEL` | `MiniCPM5-2B-heretic-abliterated-Q4_K_M` | Nome do modelo principal no Ollama |
| `CHAT_MODEL` | mesmo nome acima | Modelo padrão do Open WebUI |
| `MODELS_DIR` | `./models` | Pasta no host montada em `/models` |
| `CHAT_MODEL_FALLBACK` | vazio | Modelo da biblioteca usado quando o `.gguf` não está na pasta |

Se `GGUF_FILE` não existir e houver vários `.gguf`, o entrypoint usa o primeiro
em ordem alfabética e avisa no log. Os **outros** `.gguf` são importados
sempre, com o nome do arquivo. Detalhes em `models/README.md`.

**Trocando de modelo GGUF:**

```bash
cp ~/Downloads/Outro-Modelo.gguf models/
# edite GGUF_FILE, GGUF_MODEL e CHAT_MODEL no .env
make restart          # recria o container e importa
make models-check     # confere se está tudo instalado
```

Para importar sem reiniciar o container: `make gguf-import`
(`FORCE=1` reimporta os que já existem).

### Se a pasta `models/` estiver vazia

**Nada quebra.** O container sobe, o Ollama responde, o Open WebUI abre e o
RAG funciona (os embeddings vêm da biblioteca). A pasta é criada pelo
`make up*` antes do Docker — assim ela já nasce com o seu usuário como dono,
e não como `root`.

O que falta é apenas o modelo de chat local, e o log diz exatamente o que
fazer. Para ter um chat funcionando mesmo assim, defina um modelo de reserva
no `.env`:

```bash
CHAT_MODEL_FALLBACK=qwen3:0.6b   # baixado automaticamente quando faltar o .gguf
```

### Embeddings e RAG

O entrypoint baixa `EMBEDDING_MODEL` e cria a variante
`<modelo>-ctx<EMBEDDING_CONTEXT>` com o contexto reduzido (512 por padrão).
O Open WebUI usa essa variante no RAG: um modelo de embeddings processa
trechos curtos, e 8192 de contexto só gastaria RAM/VRAM à toa.

```bash
make test-embed   # testa só o embedding do RAG
```

Para o RAG usar o modelo sem a variante: `RAG_EMBEDDING_MODEL=<modelo>` no `.env`.

---

## Pré-requisitos

- Docker + Docker Compose
- GNU Make (já vem no Linux e no macOS; no Windows use WSL2)
- ~4 GB livres em disco (mais o tamanho do `.gguf` baixado)
- GPU **opcional** — sem ela, use os alvos de CPU

---

## Início rápido

```bash
make setup     # cria o .env, a pasta models/ e constroi a imagem CPU
# coloque os .gguf em models/  (ou siga com a pasta vazia mesmo)
make up        # sobe ollama + open-webui, importa os .gguf e baixa o resto
make test      # confere chat, embeddings e interface de ponta a ponta
make open      # abre http://localhost:3000
```

> A pasta `models/` pode ficar vazia: o stack sobe e só o chat local fica
> indisponível. Veja [Se a pasta `models/` estiver vazia](#se-a-pasta-models-estiver-vazia).

`make help` lista todos os alvos disponíveis.

> O `make up` reconstrói a imagem automaticamente quando o `Dockerfile` ou o
> `entrypoint.sh` mudam (alvo `make stale`). Assim o container nunca sobe com um
> entrypoint antigo.

---

## Profiles — subindo um ou vários serviços

Cada profile agrupa um conjunto de serviços:

| Profile | Serviços | Quando usar |
|---|---|---|
| *(sem profile)* | `ollama` | Só o servidor de modelos |
| `webui` | `ollama` + `open-webui` | **Uso normal em sala** (CPU) |
| `webui-gpu` | `ollama-gpu` + `open-webui-gpu` | Máquina com GPU NVIDIA |
| `webui-external` | `open-webui-external` | Ollama já rodando fora do Docker |
| `gpu` | `ollama` + `ollama-gpu` | Só o servidor, com GPU disponível |

> `ollama` e `ollama-gpu` são **mutuamente exclusivos**: compartilham o mesmo volume
> de modelos e usam portas diferentes no host (`11434` e `11435`). Por isso o
> profile `webui-gpu` sobe a interface ligada **somente** ao `ollama-gpu` — nunca
> aos dois servidores ao mesmo tempo.
>
> Cada projeto Compose é isolado pelo `COMPOSE_PROJECT_NAME`: containers, volumes
> e rede levam esse prefixo, então `make down` aqui **não** derruba containers,
> volumes ou redes de outra stack que esteja rodando na sua máquina. O único
> ponto de disputa possível são as portas do host — veja `make ports`.

### Formas de subir

```bash
make up                        # stack CPU completa (profile webui)
make up-gpu                    # stack com GPU (profile webui-gpu)
make up-external               # interface + Ollama fora do Docker

make up-ollama                 # SOMENTE o servidor Ollama (CPU)
make up-ollama-gpu             # SOMENTE o servidor Ollama (GPU)
make up-open-webui             # SOMENTE a interface

make up PROFILE=webui-gpu      # escolhe o profile livremente
make up SERVICES="ollama open-webui"   # sobe só os serviços listados

make profile-list              # mostra o que cada profile sobe
```

Equivalentes diretos em `docker compose`, caso prefira:

```bash
docker compose up -d                          # ollama
docker compose --profile webui up -d          # ollama + open-webui
docker compose --profile webui-gpu up -d      # ollama-gpu + open-webui
docker compose --profile gpu up -d            # ollama + ollama-gpu
```

---

## Build das imagens

```bash
make build        # constrói as imagens CPU e GPU
make build-cpu    # fiap-ollama-cpu:latest
make build-gpu    # fiap-ollama-gpu:latest
make rebuild      # reconstrói sem cache
```

O `Dockerfile` aceita o build-arg `OLLAMA_BASE_IMAGE` para fixar outra tag base:

```bash
docker build -t fiap-ollama-cpu \
  --build-arg OLLAMA_BASE_IMAGE=ollama/ollama:0.32.15 .
```

---

## Operação

```bash
make status                    # status dos containers
make logs                      # logs de tudo (seguindo)
make logs S=ollama             # logs de um serviço
make logs-ollama               # acompanha a importação/download dos modelos
make logs-webui                # logs da interface
make shell S=ollama            # shell dentro do container
make health                    # testa Ollama e interface (só o que está no ar)
make urls                      # mostra as URLs de acesso
make stale / stale-gpu         # verifica/reconstrói a imagem se os fontes mudaram
make restart                   # recria os containers (aplica o .env)
make ready                     # espera o Ollama e a interface responderem
make test                      # smoke test: chat, embeddings e interface
```

### Modelos

```bash
make models                    # o que está instalado no Ollama
make models-check              # o que o .env exige (sai != 0 se faltar algo)
make models-pull               # baixa embeddings, guardrails e extras (idempotente)
make models-sync               # importa os .gguf + baixa o que falta
make models-rm M=nome          # remove um modelo do servidor
make embed-variant             # (re)cria a variante -ctx<N> do embedding
make pull M=gpt-oss:20b        # baixa UM modelo específico
make pull                      # sem M=: baixa tudo que o .env exige
make ask P="sua pergunta"      # pergunta a um modelo pela API
make gguf                      # os .gguf do host e o que o .env espera
make gguf-import               # importa todos os .gguf agora (idempotente)
make gguf-import FORCE=1       # reimporta mesmo os que já existem
```

`make doctor` junta o diagnóstico: Docker, coerência do `.env`, portas,
containers e modelos. Útil antes de uma aula.

---

## Parar e limpar

```bash
make stop      # para os containers (mantém tudo)
make down      # remove os containers (mantém modelos e histórico)
make down-v    # remove containers + volumes  (APAGA modelos importados e histórico)
make clean     # down + remove as imagens construídas
make prune     # reset total
```

> Os arquivos `.gguf` em `models/` **nunca** são apagados — eles ficam no host.
> O `down-v` remove só a cópia que o Ollama fez dentro do volume.

---

## Trocar de modelo

**Modelo GGUF local** (padrão do projeto): veja a seção
[Modelo GGUF local](#modelo-gguf-local) — troque `GGUF_FILE`, `GGUF_MODEL` e
`CHAT_MODEL` no `.env` e rode `make restart`.

**Modelo da biblioteca pública**: aponte `CHAT_MODEL` para um nome **com tag**
(ex.: `qwen3:0.6b`) e rode `make restart`. O `entrypoint.sh` verifica se ele já
existe (`ollama list`) e só baixa o que faltar. Se o download falhar, o container
continua no ar com um aviso no log — útil quando a internet da sala oscila.

> Nome de modelo **sem tag** (`MiniCPM5-2B-...`) nunca existe na biblioteca do
> Ollama: ele só pode vir de um `.gguf` em `models/`. Nesse caso o entrypoint
> não tenta baixar nada e explica o que fazer no log.

**Guardrails e extras**: editando `GUARDRAIL_MODELS` / `EXTRA_MODELS` no `.env`
e rodando `make models-pull`, os modelos da biblioteca são baixados sem
reiniciar nada.

---

## Performance em CPU

O projeto já vem ajustado para CPU. O que cada ajuste faz e por quê:

| Ajuste | Valor | Efeito |
|---|---|---|
| `OLLAMA_KEEP_ALIVE` | `-1` | **Maior ganho.** O modelo nunca sai da memória: a primeira resposta carrega do disco, as seguintes não. |
| `OLLAMA_NUM_THREADS` | auto | Detecta os P-cores e usa só eles (ver abaixo). |
| `OLLAMA_NUM_PARALLEL` | `1` | Um usuário monopoliza os núcleos, sem dividir com requisições concorrentes. |
| `OLLAMA_MAX_LOADED_MODELS` | `2` | Mantém chat **e** embeddings residentes — o RAG não recarrega o modelo a cada busca. |
| `OLLAMA_CONTEXT_LENGTH` | `8192` | Contexto suficiente para o MiniCPM5, com KV cache enxuto. |

### Detecção automática de threads

Em CPUs híbridas Intel (P-cores + E-cores) usar **todos** os threads é pior:
os E-cores são bem mais lentos e a disputa pela banda de memória derruba o
desempenho. No start, o `entrypoint.sh`:

1. conta os núcleos físicos em `/proc/cpuinfo`;
2. agrupa por frequência máxima via `/sys/.../cpufreq` e identifica os
   **P-cores** (bins de turbo mais altos);
3. usa esse número como `OLLAMA_NUM_THREADS`, nunca acima dos CPUs disponíveis.

No i7-12700H desta bancada: 14 núcleos físicos, **12 threads de P-core** (6
P-cores × 2) → `OLLAMA_NUM_THREADS=12`. Em máquinas sem `/sys` de frequência
(ou homogêneas), cai para o total de núcleos físicos.

### Meça na sua máquina

```bash
make bench                      # latência frio/quente + tokens/s
make bench-threads THREADS=4,6,8,12
```

Saída real de referência (i7-12700H, MiniCPM5-2B Q4_K_M, Ollama 0.32.15):

```
Latencia (modelo frio x quente)
  primeira resposta (carregando do disco) : 2.72s (load 1.30s)
  respostas seguintes (residente)         : 0.94s (load 0.00s)
```

O `load_duration` de **0.00s** na segunda resposta é o `KEEP_ALIVE=-1`
funcionando. Ajuste os valores no `.env` e rode `make restart`.

> Não existe ganho mágico de threads nesta classe de máquina: medindo 6, 8, 12
> e 20 threads, o decode fica em ~26 tok/s e **20 threads derruba para ~9 tok/s**.
> O que realmente muda a experiência é manter o modelo residente.

---

## Usando uma GPU NVIDIA

1. Instale o [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) no host.
2. Ajuste no `.env` se necessário: `OLLAMA_GPU_COUNT`, `NVIDIA_VISIBLE_DEVICES`, `OLLAMA_GPU_PORT`.
3. Suba:

```bash
make up-gpu
```

O GGUF é importado no servidor GPU da mesma forma (a pasta `models/` é montada
nos dois serviços).

Se já estiver com a stack CPU no ar, pare antes e suba só com GPU — assim não
fica nenhum container CPU consumindo memória à toa:

```bash
make down && make up-gpu
```

---

## Problemas comuns

**`bind: address already in use`** — outra stack já usa a porta `11434` ou `3000`
(por exemplo o projeto `fiap-ai-lab`).

```bash
make ports     # mostra quem está ocupando as portas, e se é deste projeto
```

`em uso (este projeto)` não é conflito — é o seu próprio serviço já no ar.
`OCUPADA` com o nome de outro projeto é conflito: pare a outra stack ou mude
`OLLAMA_PORT` / `WEBUI_PORT` no `.env`.

**O modelo GGUF não aparece / log diz "Nenhum arquivo .gguf"** — o arquivo não
está na pasta certa ou o download ainda não terminou:

```bash
make gguf          # confere se o arquivo está em models/ e o que o .env espera
make gguf-import   # importa agora, sem reiniciar
```

Depois de colocar o arquivo, rode `make restart` (ou `make gguf-import`).

**Faltam modelos na lista / `make test` acusa AUSENTE** — o que o `.env` pede
ainda não foi baixado:

```bash
make models-check   # mostra o que falta, por papel (chat, embedding, guardrail)
make models-pull    # baixa o que falta da biblioteca
make models-sync    # importa os .gguf e baixa o resto
```

**`models/` não existe (ou o Docker a criou como `root`)** — os alvos `make up*`
já criam a pasta antes do Docker subir. Se ela nasceu com dono `root` de uma
execução antiga:

```bash
sudo chown -R $USER:$USER models
```

**A pasta `models/` está vazia e o chat não funciona** — isso é esperado: o
servidor sobe, o RAG funciona, só falta o modelo de chat local. Coloque o
`.gguf` na pasta ou defina `CHAT_MODEL_FALLBACK=qwen3:0.6b` no `.env`.

**`Conflict. The container name ... is already in use`** — outra composição já
criou containers com esse nome. Ajuste o projeto no `.env` e suba de novo —
containers, volumes e rede passam a usar o novo prefixo:

```bash
COMPOSE_PROJECT_NAME=meulab   # -> meulab-ollama-1, meulab_ollama_data, ...
```

**Mudei o `entrypoint.sh` e o container não pegou a mudança** — a imagem precisa
ser reconstruída. O `make up` faz isso sozinho via `make stale`; para forçar:

```bash
make build-cpu && make up
```

**Container `unhealthy` no Ollama** — o download/importação dos modelos ainda
está em andamento. Acompanhe com `make logs-ollama`.

**`could not select device driver "nvidia"`** — o NVIDIA Container Toolkit não
está instalado/configurado. Use os alvos de CPU ou instale o toolkit.

**A interface não vê os modelos** — confirme que o Ollama está saudável
(`make health`) e que `OLLAMA_BASE_URL` aponta para o serviço correto.

---

## Variáveis mais usadas (`.env`)

| Variável | Padrão | Para que serve |
|---|---|---|
| `GGUF_FILE` | `MiniCPM5-2B-...Q4_K_M.gguf` | Arquivo `.gguf` importado no start |
| `GGUF_MODEL` | `MiniCPM5-2B-...Q4_K_M` | Nome do modelo no Ollama |
| `CHAT_MODEL` | mesmo nome acima | Modelo padrão do Open WebUI |
| `MODELS_DIR` | `./models` | Pasta no host montada em `/models` |
| `GGUF_LICENSE` | vazio | Licença declarada no Modelfile (opcional) |
| `CHAT_MODEL_FALLBACK` | vazio | Modelo de reserva quando o `.gguf` falta |
| `EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | Modelo de embeddings do RAG |
| `EMBEDDING_CONTEXT` | `512` | Contexto da variante enxuta usada no RAG |
| `GUARDRAIL_MODELS` | 2 modelos | Guardrails baixados no boot (lista) |
| `EXTRA_MODELS` | 3–4 modelos | Extras baixados no boot (lista) |
| `RAG_EMBEDDING_MODEL` | `<embedding>-ctx512` | Embedding usado no RAG |
| `OLLAMA_PORT` | `11434` | Porta do Ollama CPU no host |
| `OLLAMA_GPU_PORT` | `11435` | Porta do Ollama GPU no host |
| `WEBUI_PORT` | `3000` | Porta da interface no host |
| `OLLAMA_KEEP_ALIVE` | `-1` | Tempo que o modelo fica em memória (`-1` = sempre) |
| `OLLAMA_NUM_THREADS` | vazio | Threads de inferência; vazio = detecta os P-cores |
| `OLLAMA_NUM_PARALLEL` | `1` | Requisições simultâneas por modelo |
| `OLLAMA_MAX_LOADED_MODELS` | `2` | Modelos residentes ao mesmo tempo |
| `OLLAMA_CONTEXT_LENGTH` | `8192` | Janela de contexto (tokens) |
| `COMPOSE_PROJECT_NAME` | `fiap-openwebui-ollama` | Prefixo de todos os recursos Docker |
| `OLLAMA_EXTERNAL_URL` | `http://host.docker.internal:11434` | Ollama de fora do Docker |

## Testando com outra configuração

Para experimentar sem mexer no `.env` do projeto:

```bash
cp .env .env.teste
# edite .env.teste (portas e COMPOSE_PROJECT_NAME diferentes)
make up ENV_FILE=.env.teste
make down-v ENV_FILE=.env.teste
```

---

## Estrutura dos arquivos

```
.
├── Makefile             # build e orquestração (make help)
├── docker-compose.yml   # serviços + profiles
├── Dockerfile           # imagem do Ollama com entrypoint próprio
├── entrypoint.sh        # sobe o servidor, importa o GGUF, afina a CPU e baixa o que faltar
├── scripts/
│   ├── bench_ollama.py  # medidor de latência e tokens/s (make bench)
│   └── smoke_test.py    # teste ponta a ponta do stack (make test)
├── models/              # arquivos .gguf locais (montados em /models)
│   └── README.md        # instruções da pasta de modelos
├── .env.example         # variáveis de ambiente (copiar para .env)
├── .gitignore           # ignora *.gguf e .env
└── README.md
```

---

## Observações

- Tudo roda 100% local — nenhum dado sai da sua máquina.
- Sem necessidade de chave de API paga.
- O Ollama **copia** o GGUF para o volume `ollama_data` ao importar, então o
  modelo ocupa espaço duas vezes (o arquivo em `models/` e o blob interno).
- Em máquinas mais fracas, a primeira resposta do modelo demora um pouco
  (carregamento dos pesos em memória).
