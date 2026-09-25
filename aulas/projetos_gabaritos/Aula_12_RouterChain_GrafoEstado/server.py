"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 12 — Router Chain e Grafo de Estado
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8112
"""
from __future__ import annotations

import importlib.util
import threading
from pathlib import Path
from types import ModuleType

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DIST = BASE_DIR / "frontend" / "dist"

app = FastAPI(
    title="Aula 12 — Router Chain e Grafo de Estado",
    description="Interface web do exercício de roteamento por intenção.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_exercicio: ModuleType | None = None
exercicio_lock = threading.Lock()


def _carregar_main() -> ModuleType:
    caminho = BASE_DIR / "main.py"
    spec = importlib.util.spec_from_file_location("exercicio_main", caminho)
    if spec is None or spec.loader is None:
        raise RuntimeError("não foi possível localizar o carregador de main.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _get_exercicio() -> ModuleType:
    global _exercicio
    if _exercicio is None:
        with exercicio_lock:
            if _exercicio is None:
                try:
                    _exercicio = _carregar_main()
                except Exception as erro:
                    raise HTTPException(
                        502,
                        f"Não foi possível carregar o exercício:\n{erro}",
                    ) from erro
    return _exercicio


class PerguntaBody(BaseModel):
    pergunta: str = Field(min_length=1)


@app.get("/api/info")
def info():
    _get_exercicio()
    return {
        "nome": "Aula 12 — Router Chain e Grafo de Estado",
        "modulo": "Módulo 4 · LangGraph / Spec-Driven",
        "descricao": (
            "Roteie uma pergunta para a chain correta conforme a intenção: "
            "'documentos' (busca no ChromaDB da FIAP), 'calculo' ou 'geral'. "
            "A categoria detectada aparece junto com a resposta."
        ),
        "modo": "acoes",
        "implementado": True,
        "pendentes": [],
        "parametros": [],
        "acoes": [
            {
                "endpoint": "/api/rotear",
                "titulo": "Roteando pergunta",
                "descricao": "Classifica a intenção com structured output e invoca a chain correta.",
                "metodo": "POST",
                "params": [
                    {
                        "nome": "pergunta",
                        "label": "Pergunta",
                        "tipo": "texto",
                        "padrao": "Onde fica a FIAP?",
                    }
                ],
            }
        ],
    }


@app.post("/api/rotear")
def rotear(corpo: PerguntaBody):
    exercicio = _get_exercicio()
    router = getattr(exercicio, "router", None)
    if router is None or not hasattr(router, "invoke"):
        raise HTTPException(500, "main.py não expõe um router executável")
    try:
        resultado = router.invoke({"pergunta": corpo.pergunta})
        if not isinstance(resultado, dict):
            raise ValueError("router retornou um resultado inválido")
        resposta = resultado.get("resposta")
        if not isinstance(resposta, str):
            raise ValueError("router não retornou uma resposta textual")
        normalizador = getattr(exercicio, "normalizar_categoria", None)
        if not callable(normalizador):
            raise ValueError("main.py não expõe normalização de categoria")
        categoria = normalizador(resultado.get("categoria"))
        return {
            "tipo": "json",
            "conteudo": {"categoria": categoria, "resposta": resposta},
        }
    except HTTPException:
        raise
    except Exception as erro:
        raise HTTPException(500, f"Erro ao rotear: {erro}") from erro


if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
else:
    @app.get("/")
    def sem_frontend():
        return {"tipo": "erro", "conteudo": "Frontend não compilado. Rode: cd frontend && npm install && npm run build"}
