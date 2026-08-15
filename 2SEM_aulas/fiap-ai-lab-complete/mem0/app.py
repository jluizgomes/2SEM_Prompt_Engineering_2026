"""
FIAP AI Lab — Serviço de memória (mem0) em REST
================================================

Expõe a biblioteca oficial `mem0ai` como uma API HTTP, pré-configurada
para rodar 100% local:

    LLM          → Ollama (extrai os fatos das conversas)
    Embeddings   → Ollama (mesmo modelo de embedding das aulas)
    Vector store → Postgres unificado do lab, via pgvector

Não usamos a imagem `mem0/mem0-api-server` porque ela só é publicada
para linux/arm64 e o lab roda em x86_64 — este arquivo cumpre o mesmo
papel com as mesmas rotas principais.

Rotas
-----
    GET    /health              estado do serviço e config resumida
    GET    /config              configuração efetiva (sem senhas)
    POST   /memories            grava memórias a partir de mensagens
    GET    /memories            lista memórias de um user_id
    POST   /search              busca semântica nas memórias
    DELETE /memories/{id}       apaga uma memória
    DELETE /memories            apaga todas as memórias de um user_id
    GET    /docs                Swagger UI (FastAPI)
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Body, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
log = logging.getLogger("fiap.mem0")

# ------------------------------------------------------------------
# Configuração — tudo por variável de ambiente (ver .env.example)
# ------------------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

# ATENÇÃO ao escolher o LLM: o mem0 pede um JSON de volta para extrair os
# fatos da conversa. Modelos da família Qwen3 vêm com thinking ligado por
# padrão e cospem o raciocínio antes do JSON, o que quebra o parser. Por
# isso o padrão aqui é um modelo pequeno SEM thinking.
LLM_MODEL = os.getenv("MEM0_LLM_MODEL", "llama3.2:1b")
EMBED_MODEL = os.getenv("MEM0_EMBEDDER_MODEL", os.getenv("EMBEDDING_MODEL", "qwen3-embedding:0.6b"))
EMBED_DIMS = int(os.getenv("MEM0_EMBEDDING_DIMS", "1024"))

PG_HOST = os.getenv("POSTGRES_HOST", "postgres")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
PG_DB = os.getenv("MEM0_POSTGRES_DB", "mem0")
PG_USER = os.getenv("POSTGRES_USER", "fiap")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "fiap2026")

COLLECTION = os.getenv("MEM0_COLLECTION", "fiap_memories")
HISTORY_DB = os.getenv("MEM0_HISTORY_DB", "/app/history/history.db")
AUTO_PULL = os.getenv("MEM0_AUTO_PULL", "true").lower() == "true"

MEM0_CONFIG: Dict[str, Any] = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model": LLM_MODEL,
            "temperature": 0.1,
            "max_tokens": 1024,
            "ollama_base_url": OLLAMA_BASE_URL,
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": EMBED_MODEL,
            "embedding_dims": EMBED_DIMS,
            "ollama_base_url": OLLAMA_BASE_URL,
        },
    },
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "host": PG_HOST,
            "port": PG_PORT,
            "dbname": PG_DB,
            "user": PG_USER,
            "password": PG_PASSWORD,
            "collection_name": COLLECTION,
            "embedding_model_dims": EMBED_DIMS,
        },
    },
    "history_db_path": HISTORY_DB,
    "version": "v1.1",
}

app = FastAPI(
    title="FIAP AI Lab — mem0",
    description="Camada de memória de longo prazo para agentes, 100% local (Ollama + pgvector).",
    version="1.0.0",
)

# O Memory é criado sob demanda: se o Ollama ou o Postgres ainda estiverem
# subindo, o container não morre em loop — só a primeira chamada falha.
_memory = None
_memory_lock = threading.Lock()
_memory_error: Optional[str] = None


def get_memory():
    global _memory, _memory_error
    if _memory is not None:
        return _memory
    with _memory_lock:
        if _memory is None:
            from mem0 import Memory  # import tardio: acelera o boot do container

            try:
                _memory = Memory.from_config(MEM0_CONFIG)
                _memory_error = None
                log.info("mem0 inicializado (llm=%s, embedder=%s)", LLM_MODEL, EMBED_MODEL)
            except Exception as exc:  # noqa: BLE001 - queremos o motivo na resposta HTTP
                _memory_error = f"{type(exc).__name__}: {exc}"
                log.error("falha ao inicializar o mem0: %s", _memory_error)
                raise HTTPException(status_code=503, detail=_memory_error) from exc
    return _memory


def ensure_models() -> None:
    """
    Garante que os modelos usados pelo mem0 existem no Ollama.

    O entrypoint do Ollama só baixa o modelo de chat e o de embedding das
    aulas; o modelo de extração do mem0 é outro. Fazemos o pull daqui, em
    background, para não travar o boot nem o healthcheck.
    """
    if not AUTO_PULL:
        return
    for model in {LLM_MODEL, EMBED_MODEL}:
        try:
            with httpx.Client(base_url=OLLAMA_BASE_URL, timeout=30) as client:
                tags = client.get("/api/tags").json().get("models", [])
                if any(m.get("name") == model for m in tags):
                    log.info("modelo '%s' já está no Ollama", model)
                    continue
                log.info("baixando modelo '%s' no Ollama (pode demorar)...", model)
                with httpx.Client(base_url=OLLAMA_BASE_URL, timeout=1800) as pull:
                    resp = pull.post("/api/pull", json={"model": model, "stream": False})
                    resp.raise_for_status()
                log.info("modelo '%s' pronto", model)
        except Exception as exc:  # noqa: BLE001 - pull é best-effort
            log.warning("não consegui garantir o modelo '%s': %s", model, exc)


@app.on_event("startup")
def on_startup() -> None:
    threading.Thread(target=ensure_models, daemon=True).start()


# ------------------------------------------------------------------
# Modelos de entrada
# ------------------------------------------------------------------
class Message(BaseModel):
    role: str = Field(..., description="user | assistant | system")
    content: str


class AddRequest(BaseModel):
    messages: Optional[List[Message]] = None
    text: Optional[str] = Field(None, description="Atalho para uma única mensagem de usuário")
    user_id: str = "default"
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchRequest(BaseModel):
    query: str
    user_id: str = "default"
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    limit: int = 5


def _scope(user_id: str, agent_id: Optional[str], run_id: Optional[str]) -> Dict[str, str]:
    scope = {"user_id": user_id}
    if agent_id:
        scope["agent_id"] = agent_id
    if run_id:
        scope["run_id"] = run_id
    return scope


# ------------------------------------------------------------------
# Rotas
# ------------------------------------------------------------------
@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "initialized": _memory is not None,
        "last_error": _memory_error,
        "llm_model": LLM_MODEL,
        "embedder_model": EMBED_MODEL,
        "vector_store": f"pgvector://{PG_HOST}:{PG_PORT}/{PG_DB}#{COLLECTION}",
    }


@app.get("/config")
def config() -> Dict[str, Any]:
    safe = {k: v for k, v in MEM0_CONFIG.items()}
    safe["vector_store"] = {
        "provider": "pgvector",
        "config": {k: v for k, v in MEM0_CONFIG["vector_store"]["config"].items() if k != "password"},
    }
    return safe


@app.post("/memories")
def add_memories(req: AddRequest) -> Dict[str, Any]:
    if not req.messages and not req.text:
        raise HTTPException(status_code=422, detail="Envie 'messages' ou 'text'.")
    messages = (
        [m.model_dump() for m in req.messages]
        if req.messages
        else [{"role": "user", "content": req.text}]
    )
    try:
        return get_memory().add(
            messages=messages,
            metadata=req.metadata,
            **_scope(req.user_id, req.agent_id, req.run_id),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.get("/memories")
def list_memories(
    user_id: str = Query("default"),
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    try:
        return get_memory().get_all(limit=limit, **_scope(user_id, agent_id, run_id))
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.post("/search")
def search(req: SearchRequest) -> Dict[str, Any]:
    try:
        return get_memory().search(
            query=req.query,
            limit=req.limit,
            **_scope(req.user_id, req.agent_id, req.run_id),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.delete("/memories/{memory_id}")
def delete_memory(memory_id: str) -> Dict[str, Any]:
    try:
        get_memory().delete(memory_id=memory_id)
        return {"deleted": memory_id}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.delete("/memories")
def delete_all(
    user_id: str = Query(..., description="Obrigatório: evita apagar tudo sem querer"),
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        get_memory().delete_all(**_scope(user_id, agent_id, run_id))
        return {"deleted_scope": _scope(user_id, agent_id, run_id)}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.post("/configure")
def configure(new_config: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Troca a configuração do mem0 em tempo de execução — útil para
    demonstrar em aula a diferença entre providers sem recriar o container.
    A mudança vale até o próximo restart.
    """
    global _memory, _memory_error
    from mem0 import Memory

    with _memory_lock:
        try:
            _memory = Memory.from_config(new_config)
            MEM0_CONFIG.clear()
            MEM0_CONFIG.update(new_config)
            _memory_error = None
        except Exception as exc:  # noqa: BLE001
            _memory_error = f"{type(exc).__name__}: {exc}"
            raise HTTPException(status_code=400, detail=_memory_error) from exc
    return {"status": "reconfigurado"}
