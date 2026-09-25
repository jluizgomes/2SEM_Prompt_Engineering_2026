"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 05 — Embeddings e Busca Semântica com ChromaDB
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8105
"""
import importlib.util
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
        except Exception as erro:
            _ERRO_CARGA = str(erro)
    if _ERRO_CARGA is not None:
        raise HTTPException(502, f"Não foi possível carregar o exercício:\n{_ERRO_CARGA}")
    return _EXERCICIO


def _get_exercicio_lenient():
    try:
        return _get_exercicio()
    except HTTPException:
        return None


def _info_falha(erro):
    return {
        "nome": app.title,
        "modulo": "—",
        "descricao": "Não foi possível carregar o main.py deste exercício.",
        "modo": "acoes",
        "implementado": False,
        "pendentes": [f"main.py não pôde ser importado: {erro}"],
        "parametros": [],
        "acoes": [],
    }


def _envelope_erro(mensagem: str, **extra) -> dict:
    return {"tipo": "erro", "conteudo": mensagem, **extra}


def _erro_embeddings(erro, acao: str) -> dict:
    mensagem = str(erro).lower()
    if any(marca in mensagem for marca in ("connection", "connect", "unreachable", "11434")):
        return _envelope_erro(
            f"Não foi possível {acao}: verifique se o Ollama local está disponível em "
            "EMBEDDING_OLLAMA_HOST e se o modelo de embeddings foi baixado."
        )
    return _envelope_erro(f"Erro ao {acao}: {erro}")


class BuscaBody(BaseModel):
    consulta: str
    k: str = "2"


@app.get("/api/info")
def info():
    exercicio = _get_exercicio_lenient()
    if exercicio is None:
        return _info_falha(_ERRO_CARGA)
    return {
        "nome": "Aula 05 — Embeddings e Busca Semântica com ChromaDB",
        "modulo": "Módulo 2 · RAG / Embeddings",
        "descricao": (
            "Transforme texto em vetores (embeddings), indexe no ChromaDB e faça busca "
            "por similaridade semântica — nenhuma palavra-chave precisa aparecer no texto."
        ),
        "modo": "acoes",
        "implementado": True,
        "pendentes": [],
        "avisos": [
            "A indexação e a busca usam o modelo de embeddings configurado. A listagem de "
            "documentos sempre consulta a coleção Chroma real."
        ],
        "parametros": [],
        "acoes": [
            {
                "endpoint": "/api/indexar",
                "titulo": "Indexar documentos",
                "descricao": "Gera embeddings dos DOCUMENTOS de exemplo com IDs determinísticos.",
                "metodo": "POST",
                "params": [],
            },
            {
                "endpoint": "/api/buscar",
                "titulo": "Busca semântica",
                "descricao": "Similarity search sobre o corpus indexado.",
                "metodo": "POST",
                "params": [
                    {
                        "nome": "consulta",
                        "label": "Consulta",
                        "tipo": "texto",
                        "padrao": "onde fica a faculdade?",
                    },
                    {
                        "nome": "k",
                        "label": "k (nº de resultados)",
                        "tipo": "texto",
                        "padrao": "2",
                    },
                ],
            },
            {
                "endpoint": "/api/documentos",
                "titulo": "Ver documentos indexados",
                "descricao": "Lista os documentos realmente presentes na coleção.",
                "metodo": "POST",
                "params": [],
            },
        ],
    }


@app.post("/api/indexar")
def indexar():
    exercicio = _get_exercicio()
    try:
        total = exercicio.indexar()
        return {"tipo": "texto", "conteudo": f"{total} documentos indexados."}
    except Exception as erro:
        return _erro_embeddings(erro, "indexar")


@app.post("/api/buscar")
def buscar(corpo: BuscaBody):
    exercicio = _get_exercicio()
    try:
        quantidade = int(corpo.k or "2")
    except (TypeError, ValueError):
        return _envelope_erro("O parâmetro k deve ser um número inteiro.")
    try:
        resultados = exercicio.buscar(corpo.consulta, k=quantidade)
        return {
            "tipo": "lista",
            "conteudo": [
                {
                    "titulo": f"Resultado {indice}",
                    "texto": documento.page_content,
                    "fonte": (documento.metadata or {}).get("fonte", ""),
                }
                for indice, documento in enumerate(resultados, 1)
            ],
        }
    except (LookupError, ValueError) as erro:
        return _envelope_erro(str(erro))
    except Exception as erro:
        return _erro_embeddings(erro, "buscar")


@app.post("/api/documentos")
def documentos():
    exercicio = _get_exercicio()
    try:
        documentos = exercicio.documentos_indexados()
        conteudo = [
            {
                "titulo": f"Doc {indice}",
                "texto": documento.page_content,
                "fonte": (documento.metadata or {}).get("fonte", ""),
            }
            for indice, documento in enumerate(documentos, 1)
        ]
        resposta = {"tipo": "lista", "conteudo": conteudo}
        if not conteudo:
            resposta["estado"] = "vazio"
            resposta["mensagem"] = "Nenhum documento indexado. Execute a indexação primeiro."
        return resposta
    except Exception as erro:
        return _erro_embeddings(erro, "consultar os documentos")


if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
else:
    @app.get("/")
    def sem_frontend():
        return {
            "tipo": "erro",
            "conteudo": "Frontend não compilado. Rode: cd frontend && npm install && npm run build",
        }
