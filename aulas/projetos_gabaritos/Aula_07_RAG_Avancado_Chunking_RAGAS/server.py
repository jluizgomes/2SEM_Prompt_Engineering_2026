"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 07 — RAG Avançado: Chunking, Reranking e RAGAS
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8107
"""
from __future__ import annotations

import importlib.util
import inspect
import os
import re
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

os.chdir(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="Aula 07 — RAG Avançado: Chunking, Reranking e RAGAS",
    description="Interface web do exercício de RAG avançado.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DIST = Path(__file__).resolve().parent / "frontend" / "dist"
_EXERCICIO: Any = None
_ERRO_CARGA: str | None = None


def _carregar_main() -> Any:
    caminho = Path(__file__).resolve().parent / "main.py"
    spec = importlib.util.spec_from_file_location("exercicio_main", caminho)
    if spec is None or spec.loader is None:
        raise ImportError("Não foi possível localizar main.py.")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def _get_exercicio() -> Any:
    global _EXERCICIO, _ERRO_CARGA
    if _EXERCICIO is None and _ERRO_CARGA is None:
        try:
            _EXERCICIO = _carregar_main()
            if hasattr(_EXERCICIO, "configurar"):
                _EXERCICIO.configurar()
        except Exception as error:
            _ERRO_CARGA = f"{type(error).__name__}: {error}"
    if _ERRO_CARGA is not None:
        raise HTTPException(
            502,
            f"Não foi possível carregar o exercício:\n{_ERRO_CARGA}",
        )
    return _EXERCICIO


def _get_exercicio_lenient() -> Any:
    try:
        return _get_exercicio()
    except HTTPException:
        return None


def _info_falha(erro: str | None) -> dict[str, Any]:
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


def _eh_stub(funcao: Any) -> bool:
    if funcao is None:
        return True
    try:
        fonte = inspect.getsource(funcao)
    except (OSError, TypeError, IOError):
        return False
    fonte = re.sub(r'""".*?"""', "", fonte, flags=re.S)
    return bool(re.search(r"^\s*pass\s*$", fonte, flags=re.M))


def _pendentes(exercicio: Any, nomes: dict[str, str]) -> list[str]:
    return [
        rotulo
        for nome, rotulo in nomes.items()
        if _eh_stub(getattr(exercicio, nome, None))
    ]


class TextoBody(BaseModel):
    texto: str


class ConsultaBody(BaseModel):
    consulta: str


@app.get("/api/info")
def info() -> dict[str, Any]:
    exercicio = _get_exercicio_lenient()
    if exercicio is None:
        return _info_falha(_ERRO_CARGA)
    pendentes = _pendentes(
        exercicio,
        {
            "demo_semantic_chunker": "demo_semantic_chunker()",
            "demo_parent_retriever": "demo_parent_retriever()",
            "demo_reranker": "demo_reranker()",
            "avaliar_com_ragas": "avaliar_com_ragas()",
        },
    )
    return {
        "nome": "Aula 07 — RAG Avançado: Chunking, Reranking e RAGAS",
        "modulo": "Módulo 2 · RAG / Embeddings",
        "descricao": (
            "Melhore a qualidade do RAG com chunking semântico, recuperação em "
            "dois níveis, reranking com cross-encoder e avaliação RAGAS. "
            "A execução externa depende das credenciais e dos modelos configurados."
        ),
        "modo": "acoes",
        "implementado": not pendentes,
        "pendentes": pendentes,
        "parametros": [],
        "acoes": [
            {
                "endpoint": "/api/semantic_chunker",
                "titulo": "Chunking semântico",
                "descricao": "Divide o texto por similaridade de significado.",
                "metodo": "POST",
                "params": [
                    {
                        "nome": "texto",
                        "label": "Texto",
                        "tipo": "textarea",
                        "linhas": 3,
                        "padrao": "Aprendizado de máquina é um subcampo da inteligência artificial. Modelos de linguagem são treinados em grandes volumes de texto. Prompt engineering é a arte de escrever boas instruções. RAG adiciona contexto externo para melhorar as respostas.",
                    }
                ],
            },
            {
                "endpoint": "/api/parent_retriever",
                "titulo": "ParentDocumentRetriever",
                "descricao": "Recupera o bloco-pai a partir dos chunks.",
                "metodo": "POST",
                "params": [
                    {
                        "nome": "consulta",
                        "label": "Consulta",
                        "tipo": "texto",
                        "padrao": "como evitar alucinações?",
                    }
                ],
            },
            {
                "endpoint": "/api/reranker",
                "titulo": "Reranking (cross-encoder)",
                "descricao": "Reordena documentos recuperados por relevância.",
                "metodo": "POST",
                "params": [
                    {
                        "nome": "consulta",
                        "label": "Consulta",
                        "tipo": "texto",
                        "padrao": "o que é LangGraph?",
                    }
                ],
            },
            {
                "endpoint": "/api/avaliar_ragas",
                "titulo": "Avaliar com RAGAS",
                "descricao": "Avalia uma execução real; erros externos são exibidos sem métricas simuladas.",
                "metodo": "POST",
                "params": [],
            },
        ],
    }


def _erro(conteudo: str) -> dict[str, str]:
    return {"tipo": "erro", "conteudo": conteudo}


def _documentos_resposta(documentos: list[Any]) -> list[dict[str, str]]:
    return [
        {"titulo": f"Resultado {index}", "texto": document.page_content}
        for index, document in enumerate(documentos, 1)
    ]


@app.post("/api/semantic_chunker")
def semantic_chunker(corpo: TextoBody) -> dict[str, Any]:
    exercicio = _get_exercicio()
    try:
        chunks = exercicio.executar_semantic_chunker(corpo.texto)
    except Exception as error:
        return _erro(str(error))
    return {
        "tipo": "lista",
        "conteudo": [
            {"titulo": f"chunk {index}", "texto": chunk.strip()}
            for index, chunk in enumerate(chunks, 1)
        ],
    }


@app.post("/api/parent_retriever")
def parent_retriever(corpo: ConsultaBody) -> dict[str, Any]:
    exercicio = _get_exercicio()
    try:
        documentos = exercicio.buscar_documentos(corpo.consulta)
    except Exception as error:
        raise HTTPException(500, f"Erro no ParentDocumentRetriever: {error}") from error
    return {"tipo": "lista", "conteudo": _documentos_resposta(documentos)}


@app.post("/api/reranker")
def reranker(corpo: ConsultaBody) -> dict[str, Any]:
    exercicio = _get_exercicio()
    try:
        documentos = exercicio.demo_reranker(consulta=corpo.consulta)
    except Exception as error:
        return _erro(f"Falha no reranking: {error}")
    return {"tipo": "lista", "conteudo": _documentos_resposta(documentos)}


@app.post("/api/avaliar_ragas")
def avaliar_ragas() -> dict[str, Any]:
    exercicio = _get_exercicio()
    try:
        resultado = exercicio.avaliar_com_ragas()
    except Exception as error:
        return _erro(f"Avaliação RAGAS indisponível: {error}")
    if resultado.get("status") != "ok":
        return _erro("RAGAS não retornou uma execução com métricas verificáveis.")
    return {"tipo": "json", "conteudo": resultado}


if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
else:

    @app.get("/")
    def sem_frontend() -> dict[str, str]:
        return _erro(
            "Frontend não compilado. Rode: cd frontend && npm install && npm run build"
        )
