#!/usr/bin/env python3
"""
FIAP AI Lab — teste de integração ponta a ponta
================================================

Confere que cada stack está no ar E que elas se enxergam entre si.

Roda de dois jeitos:

    make test        do seu computador, usando localhost + as portas do .env
    make test-net    de dentro da rede fiap-ai-net, usando os hostnames
                     internos (ollama, chromadb, mem0, firecrawl-api...) —
                     que é exatamente como o código das aulas enxerga tudo

Só usa a biblioteca padrão do Python: nada para instalar.

Serviço fora do ar vira SKIP, não erro: subir só `make up-rag` e ver
Firecrawl como SKIP é o comportamento esperado.

Códigos de saída:  0 = tudo passou   ·   1 = algum teste falhou
"""

from __future__ import annotations

import base64
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

IN_NETWORK = os.getenv("IN_DOCKER_NETWORK") == "1"


def env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def load_dotenv() -> None:
    """
    Lê o .env do projeto sem depender do python-dotenv.
    Só preenche o que ainda não veio do ambiente.
    """
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.isfile(caminho):
        return
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            os.environ.setdefault(chave.strip(), valor.strip())


if not IN_NETWORK:
    load_dotenv()

# ------------------------------------------------------------------
# Endereços: hostname interno na rede do Docker, localhost fora dela
# ------------------------------------------------------------------
if IN_NETWORK:
    OLLAMA = "http://ollama:11434"
    WEBUI = "http://open-webui:8080"
    CHROMA = "http://chromadb:8000"
    SEARXNG = "http://searxng:8080"
    MEM0 = "http://mem0:8000"
    FIRECRAWL = "http://firecrawl-api:3002"
    PIPELINES = "http://pipelines:9099"
    LANGFUSE = "http://langfuse-web:3000"
    PG_HOST, PG_PORT = "postgres", 5432
else:
    OLLAMA = f"http://localhost:{env('OLLAMA_PORT', '11434')}"
    WEBUI = f"http://localhost:{env('WEBUI_PORT', '3000')}"
    CHROMA = f"http://localhost:{env('CHROMADB_PORT', '8000')}"
    SEARXNG = f"http://localhost:{env('SEARXNG_PORT', '8080')}"
    MEM0 = f"http://localhost:{env('MEM0_PORT', '8100')}"
    FIRECRAWL = f"http://localhost:{env('FIRECRAWL_PORT', '3002')}"
    PIPELINES = f"http://localhost:{env('PIPELINES_PORT', '9099')}"
    LANGFUSE = f"http://localhost:{env('LANGFUSE_PORT', '3001')}"
    PG_HOST, PG_PORT = "localhost", int(env("POSTGRES_HOST_PORT", "5432"))

CHAT_MODEL = env("CHAT_MODEL", "qwen3.5:0.8b")
EMBEDDING_MODEL = env("EMBEDDING_MODEL", "qwen3-embedding:0.6b")
PIPELINES_KEY = env("PIPELINES_API_KEY", "0p3n-w3bu!")
LANGFUSE_PK = env("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SK = env("LANGFUSE_SECRET_KEY", "")

# Sem verificação de certificado: tudo aqui é HTTP interno.
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

VERDE, VERMELHO, AMARELO, CINZA, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"

resultados: list[Tuple[str, str, str]] = []  # (status, nome, detalhe)


def http(
    url: str,
    method: str = "GET",
    payload: Optional[dict] = None,
    timeout: int = 15,
    headers: Optional[dict] = None,
) -> Tuple[int, Any]:
    dados = json.dumps(payload).encode() if payload is not None else None
    requisicao = urllib.request.Request(url, data=dados, method=method)
    requisicao.add_header("Content-Type", "application/json")
    for chave, valor in (headers or {}).items():
        requisicao.add_header(chave, valor)
    with urllib.request.urlopen(requisicao, timeout=timeout, context=SSL_CTX) as resposta:
        corpo = resposta.read().decode("utf-8", "replace")
        try:
            return resposta.status, json.loads(corpo)
        except json.JSONDecodeError:
            return resposta.status, corpo


def porta_aberta(host: str, porta: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, porta), timeout=timeout):
            return True
    except OSError:
        return False


def secao(titulo: str) -> None:
    print(f"\n{CINZA}{'─' * 62}{RESET}\n{titulo}")


def check(nome: str, funcao) -> None:
    """
    Executa um teste. Diferencia serviço FORA DO AR (skip) de
    serviço no ar respondendo errado (falha).
    """
    inicio = time.time()
    try:
        detalhe = funcao()
        segundos = time.time() - inicio
        print(f"  {VERDE}PASSOU{RESET}  {nome}  {CINZA}({segundos:.1f}s) {detalhe or ''}{RESET}")
        resultados.append(("PASSOU", nome, detalhe or ""))
    except SkipTest as exc:
        print(f"  {AMARELO}SKIP{RESET}    {nome}  {CINZA}{exc}{RESET}")
        resultados.append(("SKIP", nome, str(exc)))
    except Exception as exc:  # noqa: BLE001
        print(f"  {VERMELHO}FALHOU{RESET}  {nome}\n          {type(exc).__name__}: {exc}")
        resultados.append(("FALHOU", nome, f"{type(exc).__name__}: {exc}"))


class SkipTest(Exception):
    """Serviço não está no perfil que está no ar."""


def exige(url: str, nome_stack: str, caminho: str = "/", timeout: int = 5) -> None:
    """Marca SKIP se o serviço não responde nada na porta."""
    try:
        http(url.rstrip("/") + caminho, timeout=timeout)
    except urllib.error.HTTPError:
        # Respondeu (mesmo que 4xx/5xx): está no ar.
        return
    except Exception as exc:  # noqa: BLE001
        raise SkipTest(f"{nome_stack} fora do ar — suba o perfil correspondente") from exc


# ==================================================================
# Testes
# ==================================================================
def teste_postgres() -> str:
    if not porta_aberta(PG_HOST, PG_PORT):
        raise SkipTest(f"nada escutando em {PG_HOST}:{PG_PORT}")
    return f"{PG_HOST}:{PG_PORT} aceitando conexões"


def teste_ollama_modelos() -> str:
    exige(OLLAMA, "Ollama", "/api/tags")
    _, dados = http(f"{OLLAMA}/api/tags")
    nomes = [modelo["name"] for modelo in dados.get("models", [])]
    faltando = [m for m in (CHAT_MODEL, EMBEDDING_MODEL) if m not in nomes]
    if faltando:
        raise AssertionError(
            f"modelos ausentes: {', '.join(faltando)} — o primeiro boot ainda pode "
            f"estar baixando (make logs-ollama). Presentes: {', '.join(nomes) or 'nenhum'}"
        )
    return f"{len(nomes)} modelos"


def teste_ollama_chat() -> str:
    exige(OLLAMA, "Ollama", "/api/tags")
    _, dados = http(
        f"{OLLAMA}/api/generate",
        "POST",
        {
            "model": CHAT_MODEL,
            "prompt": "Responda apenas: OK",
            "stream": False,
            # Modelos com thinking (Qwen3, DeepSeek-R) rodam por minutos
            # em CPU se o raciocínio não for desligado.
            "think": False,
            "options": {"num_predict": 16},
        },
        timeout=300,
    )
    resposta = (dados.get("response") or "").strip()
    if not resposta:
        raise AssertionError("modelo respondeu vazio")
    return f'"{resposta[:40]}"'


def teste_ollama_embedding() -> str:
    exige(OLLAMA, "Ollama", "/api/tags")
    _, dados = http(
        f"{OLLAMA}/api/embed",
        "POST",
        {"model": EMBEDDING_MODEL, "input": "engenharia de contexto"},
        timeout=120,
    )
    vetores = dados.get("embeddings") or []
    if not vetores or not vetores[0]:
        raise AssertionError("nenhum embedding devolvido")
    dimensoes = len(vetores[0])
    esperado = int(env("MEM0_EMBEDDING_DIMS", "1024"))
    aviso = "" if dimensoes == esperado else f" ATENÇÃO: MEM0_EMBEDDING_DIMS={esperado} no .env"
    return f"{dimensoes} dimensões{aviso}"


def teste_chromadb() -> str:
    exige(CHROMA, "ChromaDB", "/api/v2/heartbeat")
    _, dados = http(f"{CHROMA}/api/v2/heartbeat")
    if "nanosecond heartbeat" not in json.dumps(dados):
        raise AssertionError(f"heartbeat inesperado: {dados}")
    return "heartbeat OK"


def teste_openwebui() -> str:
    exige(WEBUI, "Open WebUI", "/health")
    codigo, _ = http(f"{WEBUI}/health")
    if codigo != 200:
        raise AssertionError(f"HTTP {codigo}")
    return "healthy"


def teste_pipelines() -> str:
    exige(PIPELINES, "Pipelines", "/health")
    cabecalho = {"Authorization": f"Bearer {PIPELINES_KEY}"}
    _, dados = http(f"{PIPELINES}/v1/models", headers=cabecalho, timeout=30)
    ids = [modelo.get("id", "") for modelo in dados.get("data", [])]
    esperadas = {"mem0_memory_filter", "firecrawl_web"}
    carregadas = esperadas.intersection(ids)
    if not carregadas:
        raise AssertionError(
            f"nenhuma pipeline do lab carregada. Encontradas: {', '.join(ids) or 'nenhuma'}"
        )
    return f"{len(ids)} pipelines ({', '.join(sorted(carregadas))})"


def teste_searxng() -> str:
    exige(SEARXNG, "SearXNG", "/healthz")
    _, dados = http(f"{SEARXNG}/search?q=langchain&format=json", timeout=45)
    total = len(dados.get("results", []))
    if total == 0:
        raise AssertionError("busca sem resultados — confira searxng/settings.yml (formats: json)")
    return f"{total} resultados"


def teste_mem0_health() -> str:
    exige(MEM0, "mem0", "/health")
    _, dados = http(f"{MEM0}/health")
    if dados.get("status") != "ok":
        raise AssertionError(f"health inesperado: {dados}")
    return f"llm={dados.get('llm_model')}"


def teste_mem0_ciclo() -> str:
    """
    Gravar memória usa LLM + embedding: em CPU leva bastante tempo.
    É o teste mais lento da suíte, e o mais importante da stack de memória.
    """
    exige(MEM0, "mem0", "/health")
    usuario = "teste_integracao"
    http(
        f"{MEM0}/memories",
        "POST",
        {
            "messages": [
                {"role": "user", "content": "Meu nome é Jorge e eu ensino Prompt Engineering na FIAP."}
            ],
            "user_id": usuario,
        },
        timeout=600,
    )
    _, busca = http(
        f"{MEM0}/search",
        "POST",
        {"query": "Onde eu dou aula?", "user_id": usuario, "limit": 3},
        timeout=300,
    )
    encontradas = busca.get("results", [])
    if not encontradas:
        raise AssertionError("memória gravada mas a busca não devolveu nada")
    # Limpa para o teste ser repetível.
    try:
        http(f"{MEM0}/memories?user_id={usuario}", "DELETE", timeout=60)
    except Exception:  # noqa: BLE001
        pass
    return f'{len(encontradas)} memórias · "{encontradas[0].get("memory", "")[:40]}"'


def teste_firecrawl() -> str:
    exige(FIRECRAWL, "Firecrawl", "/", timeout=10)
    _, dados = http(
        f"{FIRECRAWL}/v2/scrape",
        "POST",
        {"url": "https://example.com", "formats": ["markdown"], "onlyMainContent": True},
        timeout=300,
    )
    if not dados.get("success"):
        raise AssertionError(f"scrape falhou: {dados}")
    markdown = dados.get("data", {}).get("markdown", "")
    if "Example Domain" not in markdown:
        raise AssertionError(f"markdown inesperado: {markdown[:120]}")
    return f"{len(markdown)} caracteres extraídos"


def teste_firecrawl_usa_postgres() -> str:
    """
    A fila NuQ do Firecrawl vive no Postgres unificado. Se o /v2/crawl
    aceita um job, é porque o schema nuq.sql e o pg_cron estão de pé.
    """
    exige(FIRECRAWL, "Firecrawl", "/", timeout=10)
    _, dados = http(
        f"{FIRECRAWL}/v2/crawl",
        "POST",
        {"url": "https://example.com", "limit": 1},
        timeout=120,
    )
    if not dados.get("id"):
        raise AssertionError(f"fila não aceitou o job: {dados}")
    return f"job {dados['id'][:8]}… enfileirado no Postgres"


def teste_langfuse_web() -> str:
    """
    /api/public/health só devolve 200 depois que as migrações do
    Postgres e do ClickHouse terminaram — é o sinal de que a stack
    inteira subiu, não só o processo web.
    """
    exige(LANGFUSE, "Langfuse", "/api/public/health", timeout=10)
    status, dados = http(f"{LANGFUSE}/api/public/health", timeout=20)
    versao = dados.get("version", "desconhecida") if isinstance(dados, dict) else "desconhecida"
    return f"web e migrações OK ({status}) · versão {versao}"


def teste_langfuse_ingestao() -> str:
    """
    Grava um trace de verdade pela API pública. O caminho exercitado é
    o mesmo do SDK das aulas: web → MinIO (blob do evento) → Redis
    (fila BullMQ) → worker → ClickHouse.

    A resposta é 207 (multi-status): o Langfuse aceita o lote e informa
    o resultado item a item, então é preciso olhar dentro do corpo.
    """
    exige(LANGFUSE, "Langfuse", "/api/public/health", timeout=10)
    if not LANGFUSE_PK or not LANGFUSE_SK:
        raise SkipTest("LANGFUSE_PUBLIC_KEY/SECRET_KEY não configuradas no .env")

    credencial = base64.b64encode(f"{LANGFUSE_PK}:{LANGFUSE_SK}".encode()).decode()
    agora = datetime.now(timezone.utc).isoformat()
    trace_id = str(uuid.uuid4())
    lote = {
        "batch": [
            {
                "id": str(uuid.uuid4()),
                "type": "trace-create",
                "timestamp": agora,
                "body": {
                    "id": trace_id,
                    "name": "fiap-integration-test",
                    "input": "ping",
                    "output": "pong",
                    "tags": ["integration-test"],
                },
            }
        ]
    }
    status, dados = http(
        f"{LANGFUSE}/api/public/ingestion",
        method="POST",
        payload=lote,
        timeout=30,
        headers={"Authorization": f"Basic {credencial}"},
    )
    if isinstance(dados, dict) and dados.get("errors"):
        raise AssertionError(f"ingestão recusada: {str(dados['errors'])[:120]}")
    return f"trace {trace_id[:8]}… aceito na fila ({status})"


# ==================================================================
# Execução
# ==================================================================
def main() -> int:
    origem = "de dentro da rede fiap-ai-net" if IN_NETWORK else "do seu computador (localhost)"
    print("=" * 62)
    print("FIAP AI Lab — teste de integração")
    print(f"Origem: {origem}")
    print("=" * 62)

    secao("Infraestrutura (perfis: todos)")
    check("Postgres unificado aceita conexões", teste_postgres)
    check("Ollama tem os modelos do .env", teste_ollama_modelos)
    check("Ollama responde chat", teste_ollama_chat)
    check("Ollama gera embeddings", teste_ollama_embedding)
    check("Open WebUI está healthy", teste_openwebui)

    secao("Stacks")
    check("ChromaDB responde (RAG)", teste_chromadb)
    check("Pipelines carregou os plugins do lab", teste_pipelines)
    check("SearXNG devolve JSON (busca web)", teste_searxng)
    check("mem0 está de pé (memória)", teste_mem0_health)
    check("mem0 grava e recupera memória", teste_mem0_ciclo)
    check("Firecrawl extrai página em markdown", teste_firecrawl)
    check("Firecrawl enfileira no Postgres unificado", teste_firecrawl_usa_postgres)
    check("Langfuse está de pé (observabilidade)", teste_langfuse_web)
    check("Langfuse aceita trace pela API pública", teste_langfuse_ingestao)

    passou = sum(1 for status, _, _ in resultados if status == "PASSOU")
    pulou = sum(1 for status, _, _ in resultados if status == "SKIP")
    falhou = [item for item in resultados if item[0] == "FALHOU"]

    print(f"\n{CINZA}{'═' * 62}{RESET}")
    print(f"  {VERDE}{passou} passaram{RESET} · {AMARELO}{pulou} pulados{RESET} · "
          f"{VERMELHO}{len(falhou)} falharam{RESET}")
    if falhou:
        print("\nFalhas:")
        for _, nome, detalhe in falhou:
            print(f"  - {nome}: {detalhe}")
    print(f"{CINZA}{'═' * 62}{RESET}\n")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
