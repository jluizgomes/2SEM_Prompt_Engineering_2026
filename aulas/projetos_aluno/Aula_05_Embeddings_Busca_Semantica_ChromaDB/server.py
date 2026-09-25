"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 05 — Embeddings e Busca Semântica com ChromaDB
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8005     (ou: ./run_web.sh)
"""
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import importlib.util
import inspect
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

app = FastAPI(
    title="Aula 05 — Embeddings e Busca Semântica com ChromaDB",
    description="Interface web do exercício de embeddings + ChromaDB.",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DIST = Path(__file__).resolve().parent / "frontend" / "dist"

# ─────────────────────────────────────────────────────────────
# Carga do exercício (main.py)
# ─────────────────────────────────────────────────────────────
_EXERCICIO = None
_ERRO_CARGA = None


def _carregar_main():
    caminho = Path(__file__).resolve().parent / "main.py"
    spec = importlib.util.spec_from_file_location("exercicio_main", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _get_exercicio():
    global _EXERCICIO, _ERRO_CARGA
    if _EXERCICIO is None and _ERRO_CARGA is None:
        try:
            _EXERCICIO = _carregar_main()
        except Exception as e:  # noqa: BLE001
            _ERRO_CARGA = str(e)
    if _ERRO_CARGA is not None:
        raise HTTPException(502, f"Não foi possível carregar o exercício:\n{_ERRO_CARGA}")
    return _EXERCICIO

def _get_exercicio_lenient():
    """Versão tolerante: devolve None se o main.py não puder ser importado."""
    try:
        return _get_exercicio()
    except HTTPException:
        return None


def _info_falha(erro):
    return {
        "nome": app.title,
        "modulo": "—",
        "descricao": "Não foi possível carregar o main.py deste exercício (ver pendentes).",
        "modo": "acoes",
        "implementado": False,
        "pendentes": [f"main.py não pôde ser importado: {erro}"],
        "parametros": [],
        "acoes": [],
    }



def _eh_stub(funcao) -> bool:
    if funcao is None:
        return True
    try:
        fonte = inspect.getsource(funcao)
    except (OSError, TypeError, IOError):
        return False
    fonte = re.sub(r'""".*?"""', "", fonte, flags=re.S)
    return bool(re.search(r"^\s*pass\s*$", fonte, flags=re.M))


def _pendentes(ex, nomes: dict) -> list:
    return [rotulo for nome, rotulo in nomes.items() if _eh_stub(getattr(ex, nome, None))]



def _envelope_erro(mensagem: str, **extra) -> dict:
    return {"tipo": "erro", "conteudo": mensagem, **extra}

def _erro_embeddings(erro, acao: str) -> dict:
    msg = str(erro).lower()
    if any(marca in msg for marca in ("connection", "connect", "unreachable", "11434")):
        return _envelope_erro(
            f"Não foi possível {acao}: verifique se o Ollama local está disponível em "
            "EMBEDDING_OLLAMA_HOST e se o modelo de embeddings foi baixado."
        )
    return _envelope_erro(f"Erro ao {acao}: {erro}")


# ─────────────────────────────────────────────────────────────
# Modelos de requisição
# ─────────────────────────────────────────────────────────────
class BuscaBody(BaseModel):
    consulta: str
    k: str = "2"


# ─────────────────────────────────────────────────────────────
# Endpoints da API
# ─────────────────────────────────────────────────────────────
@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        return _info_falha(_ERRO_CARGA)
    pendentes = _pendentes(ex, {"indexar": "indexar()", "buscar": "buscar()"})
    return {
        "nome": "Aula 05 — Embeddings e Busca Semântica com ChromaDB",
        "modulo": "Módulo 2 · RAG / Embeddings",
        "descricao": (
            "Transforme texto em vetores (embeddings), indexe no ChromaDB e faça busca "
            "por similaridade semântica — nenhuma palavra-chave precisa aparecer no texto."
        ),
        "modo": "acoes",
        "implementado": not pendentes,
        "pendentes": pendentes,
        "avisos": [
            "Indexar/buscar usam Ollama local em EMBEDDING_OLLAMA_HOST com o modelo "
            "nomic-embed-text; esta aula não usa o Ollama Cloud."
        ],
        "parametros": [],
        "acoes": [
            {"endpoint": "/api/indexar", "titulo": "Indexar documentos",
             "descricao": "Gera embeddings dos DOCUMENTOS de exemplo e grava no ChromaDB.",
             "metodo": "POST", "params": []},
            {"endpoint": "/api/buscar", "titulo": "Busca semântica",
             "descricao": "Similarity search sobre o corpus indexado.",
             "metodo": "POST",
             "params": [{"nome": "consulta", "label": "Consulta", "tipo": "texto", "padrao": "onde fica a faculdade?"},
                        {"nome": "k", "label": "k (nº de resultados)", "tipo": "texto", "padrao": "2"}]},
            {"endpoint": "/api/documentos", "titulo": "Ver documentos indexados",
             "descricao": "Lista o corpus de exemplo.",
             "metodo": "POST", "params": []},
        ],
    }


@app.post("/api/indexar")
def indexar():
    ex = _get_exercicio()
    try:
        ex.vectorstore.add_documents(ex.DOCUMENTOS)
        return {"tipo": "texto", "conteudo": f"{len(ex.DOCUMENTOS)} documentos indexados."}
    except Exception as e:  # noqa: BLE001
        return _erro_embeddings(e, "indexar")


@app.post("/api/buscar")
def buscar(corpo: BuscaBody):
    ex = _get_exercicio()
    try:
        k = int(corpo.k or "2")
    except ValueError:
        k = 2
    try:
        resultados = ex.vectorstore.similarity_search(corpo.consulta, k=k)
        return {"tipo": "lista",
                "conteudo": [{"titulo": f"Resultado {i}", "texto": d.page_content}
                             for i, d in enumerate(resultados, 1)]}
    except Exception as e:  # noqa: BLE001
        return _erro_embeddings(e, "buscar")


@app.post("/api/documentos")
def documentos():
    ex = _get_exercicio()
    return {"tipo": "lista",
            "conteudo": [{"titulo": f"Doc {i + 1}", "texto": d.page_content}
                         for i, d in enumerate(ex.DOCUMENTOS)]}


# ─────────────────────────────────────────────────────────────
# Frontend estático (React) — se já estiver compilado
# ─────────────────────────────────────────────────────────────
if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
else:
    @app.get("/")
    def sem_frontend():
        return {"tipo": "erro",
                "conteudo": "Frontend não compilado. Rode: cd frontend && npm install && npm run build"}