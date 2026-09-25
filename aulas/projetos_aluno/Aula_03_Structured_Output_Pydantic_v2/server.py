"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 03 — Structured Output com Pydantic v2
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8003     (ou: ./run_web.sh)
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
    title="Aula 03 — Structured Output com Pydantic v2",
    description="Interface web do exercício de saída estruturada (PydanticOutputParser).",
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


# ─────────────────────────────────────────────────────────────
# Modelos de requisição
# ─────────────────────────────────────────────────────────────
class PratoBody(BaseModel):
    prato: str = "bolo de cenoura"


# ─────────────────────────────────────────────────────────────
# Endpoints da API
# ─────────────────────────────────────────────────────────────
@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        return _info_falha(_ERRO_CARGA)
    pendentes = _pendentes(ex, {"main": "main()"})
    return {
        "nome": "Aula 03 — Structured Output com Pydantic v2",
        "modulo": "Módulo 1 · LangChain / Context Engineering",
        "descricao": (
            "Força o LLM a responder com um schema garantido: a chain usa "
            "PydanticOutputParser + BaseModel. Veja o contrato de saída e gere "
            "receitas estruturadas."
        ),
        "modo": "acoes",
        "implementado": not pendentes,
        "pendentes": pendentes,
        "parametros": [],
        "acoes": [
            {"endpoint": "/api/gerar_receita", "titulo": "Gerar receita estruturada",
             "descricao": "Invoca a chain (prompt | llm | parser) e devolve o objeto Pydantic em JSON.",
             "metodo": "POST",
             "params": [{"nome": "prato", "label": "Prato", "tipo": "texto", "padrao": "bolo de cenoura"}]},
            {"endpoint": "/api/schema", "titulo": "Ver schema (Pydantic)",
             "descricao": "Mostra o contrato de saída (JSON Schema) e as instruções de formato.",
             "metodo": "POST", "params": []},
        ],
    }


@app.post("/api/gerar_receita")
def gerar_receita(corpo: PratoBody):
    ex = _get_exercicio()
    try:
        chain = getattr(ex, "chain", None)
        if chain is None:
            chain = ex.prompt | ex.llm | ex.parser
        resultado = chain.invoke({"prato": corpo.prato})
        if hasattr(resultado, "model_dump"):
            conteudo = resultado.model_dump()
        elif hasattr(resultado, "dict"):
            conteudo = resultado.dict()
        else:
            conteudo = resultado
        return {"tipo": "json", "conteudo": conteudo}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao gerar a receita: {e}")


@app.post("/api/schema")
def schema():
    ex = _get_exercicio()
    try:
        receita = getattr(ex, "Receita", None)
        parser = getattr(ex, "parser", None)
        esquema = receita.model_json_schema() if receita is not None else {}
        instrucoes = parser.get_format_instructions() if parser is not None else "(parser não encontrado)"
        return {"tipo": "json",
                "conteudo": {"json_schema": esquema, "instrucoes_formato": instrucoes}}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao ler o schema: {e}")


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