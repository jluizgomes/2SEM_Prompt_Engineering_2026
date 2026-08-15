# FIAP AI Lab — Open WebUI + Ollama (100% local, CPU)

Setup para rodar um chat de IA local (sem custo, sem API paga) na sua máquina.

## O que sobe

- **Ollama (CPU)** — servidor de modelos, com download automático de:
  - `qwen3.5:0.8b` (chat)
  - `qwen3-embedding:0.6b` (embeddings, útil para RAG)
- **Open WebUI** — interface de chat estilo ChatGPT, já conectada ao Ollama

## Pré-requisitos

- Docker + Docker Compose instalados ([docs.docker.com](https://docs.docker.com/get-docker/))
- ~4 GB de espaço livre em disco
- Nenhuma GPU necessária — tudo roda em CPU

## Como usar

```bash
# 1. Copie o arquivo de variáveis de ambiente
cp .env.example .env

# 2. Suba os containers (a primeira vez baixa as imagens + modelos, pode levar alguns minutos)
docker compose up -d --build

# 3. Acompanhe o download dos modelos (opcional)
docker compose logs -f ollama

# 4. Acesse a interface no navegador
# http://localhost:3000
```

Na primeira vez, o Open WebUI vai pedir para criar uma conta local (fica salva só na sua máquina).

## Comandos úteis

```bash
docker compose ps            # ver status dos containers
docker compose logs -f       # ver logs de tudo
docker compose down          # parar tudo (mantém os dados/modelos)
docker compose down -v       # parar e apagar TUDO (modelos, histórico, contas)
docker exec -it fiap-ollama ollama list   # ver modelos baixados
```

## Trocar de modelo

Edite `CHAT_MODEL` e/ou `EMBEDDING_MODEL` no `.env`, depois:

```bash
docker compose up -d
```

O `entrypoint.sh` baixa automaticamente qualquer modelo novo definido nessas variáveis (desde que exista no [Ollama Library](https://ollama.com/library)).

## Estrutura dos arquivos

```
.
├── docker-compose.yml   # orquestra os dois serviços
├── Dockerfile           # build customizado do Ollama (CPU) com entrypoint
├── entrypoint.sh         # sobe o servidor e baixa os modelos automaticamente
├── .env.example          # variáveis de ambiente (copiar para .env)
└── README.md
```

## Observações

- Tudo roda 100% local — nenhum dado sai da sua máquina.
- Sem necessidade de chave de API paga.
- Se a máquina for mais fraca, a primeira resposta do modelo pode demorar um pouco (carregamento em memória).
