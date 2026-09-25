"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 03 — Structured Output com Pydantic v2
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8103
"""
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import importlib.util
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from structured_output import Receita, executar_com_retry, validar_receita

app = FastAPI(
    title="Aula 03 — Structured Output com Pydantic v2",
    description="Interface web do exercício de saída estruturada (PydanticOutputParser).",
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
        except Exception as e:
            _ERRO_CARGA = str(e)
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
        "pendentes": [],
        "erro": erro,
        "parametros": [],
        "acoes": [],
    }


class PratoBody(BaseModel):
    prato: str = "bolo de cenoura"


def _modelo_receita(ex):
    return getattr(ex, "Receita", None) or Receita


def _executar_receita(ex, prato: str):
    modelo = _modelo_receita(ex)
    gerador = getattr(ex, "gerar_receita", None)
    if callable(gerador):
        try:
            return validar_receita(gerador(prato), modelo)
        except Exception as e:
            raise ValueError(f"Saída estruturada inválida: {e}") from e

    chain = getattr(ex, "chain", None)
    if chain is None:
        raise RuntimeError("Chain estruturada não configurada.")
    return executar_com_retry(prato, chain, modelo=modelo)


@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        return _info_falha(_ERRO_CARGA)
    return {
        "nome": "Aula 03 — Structured Output com Pydantic v2",
        "modulo": "Módulo 1 · LangChain / Context Engineering",
        "descricao": (
            "Força o LLM a responder com um schema garantido: a chain usa "
            "PydanticOutputParser + BaseModel. Veja o contrato de saída e gere "
            "receitas estruturadas."
        ),
        "modo": "acoes",
        "implementado": True,
        "pendentes": [],
        "parametros": [],
        "acoes": [
            {
                "endpoint": "/api/gerar_receita",
                "titulo": "Gerar receita estruturada",
                "descricao": "Invoca a chain estruturada e devolve uma Receita validada em JSON.",
                "metodo": "POST",
                "params": [
                    {
                        "nome": "prato",
                        "label": "Prato",
                        "tipo": "texto",
                        "padrao": "bolo de cenoura",
                    }
                ],
            },
            {
                "endpoint": "/api/schema",
                "titulo": "Ver schema (Pydantic)",
                "descricao": "Mostra o contrato de saída (JSON Schema) e as instruções de formato.",
                "metodo": "POST",
                "params": [],
            },
        ],
    }


@app.post("/api/gerar_receita")
def gerar_receita(corpo: PratoBody):
    ex = _get_exercicio()
    try:
        resultado = _executar_receita(ex, corpo.prato)
        receita = validar_receita(resultado, _modelo_receita(ex))
        return {"tipo": "json", "conteudo": receita.model_dump(mode="json")}
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar a receita estruturada: {e}") from e


@app.post("/api/schema")
def schema():
    ex = _get_exercicio()
    try:
        receita = getattr(ex, "Receita", None)
        parser = getattr(ex, "parser", None)
        if receita is None or not hasattr(receita, "model_json_schema"):
            raise RuntimeError("Modelo Pydantic de saída não configurado.")
        if parser is None or not hasattr(parser, "get_format_instructions"):
            raise RuntimeError("Parser de formato não configurado.")
        return {
            "tipo": "json",
            "conteudo": {
                "json_schema": receita.model_json_schema(),
                "instrucoes_formato": parser.get_format_instructions(),
            },
        }
    except Exception as e:
        raise HTTPException(500, f"Erro ao ler o schema: {e}") from e


if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
else:
    @app.get("/")
    def sem_frontend():
        return {
            "tipo": "erro",
            "conteudo": "Frontend não compilado. Rode: cd frontend && npm install && npm run build",
        }
