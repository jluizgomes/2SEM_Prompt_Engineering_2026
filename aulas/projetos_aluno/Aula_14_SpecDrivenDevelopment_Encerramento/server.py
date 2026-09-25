"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 14 — Spec-Driven Development e Encerramento
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8014     (ou: ./run_web.sh)
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
    title="Aula 14 — Spec-Driven Development e Encerramento",
    description="Interface web do exercício de spec-driven development.",
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



def _pendentes(ex, nomes: dict) -> list:
    return [rotulo for nome, rotulo in nomes.items() if _eh_stub(getattr(ex, nome, None))]


def _eh_stub(funcao) -> bool:
    if funcao is None:
        return True
    try:
        fonte = inspect.getsource(funcao)
    except (OSError, TypeError, IOError):
        return False
    fonte = re.sub(r'""".*?"""', "", fonte, flags=re.S)
    return bool(re.search(r"^\s*pass\s*$", fonte, flags=re.M))


def _get_chain(ex):
    chain = getattr(ex, "chain", None)
    if chain is not None:
        return chain
    parser = getattr(ex, "StrOutputParser", None)
    if parser is None:
        from langchain_core.output_parsers import StrOutputParser as parser
    return ex.prompt | ex.llm | parser()


# ─────────────────────────────────────────────────────────────
# Modelos de requisição
# ─────────────────────────────────────────────────────────────
class SpecBody(BaseModel):
    spec: str = ""


# ─────────────────────────────────────────────────────────────
# Endpoints da API
# ─────────────────────────────────────────────────────────────
@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        return _info_falha(_ERRO_CARGA)
    chain_pronta = hasattr(getattr(ex, "chain", None), "invoke")
    pendentes = [] if chain_pronta else ["chain (monte o pipe no main.py)"]
    pendentes += _pendentes(ex, {"main": "main()"})
    spec_padrao = getattr(ex, "SPEC", "")
    return {
        "nome": "Aula 14 — Spec-Driven Development e Encerramento",
        "modulo": "Módulo 4 · LangGraph / Spec-Driven",
        "descricao": (
            "Escreva a ESPECIFICAÇÃO primeiro e deixe o modelo gerar o artefato "
            "conforme o spec — o padrão spec-driven que consolida o semestre."
        ),
        "modo": "acoes",
        "implementado": not pendentes,
        "pendentes": pendentes,
        "parametros": [],
        "acoes": [
            {"endpoint": "/api/gerar", "titulo": "Gerar artefato a partir do spec",
             "descricao": "A spec é o prompt; o modelo gera o plano seguindo o formato.",
             "metodo": "POST",
             "params": [{"nome": "spec", "label": "Especificação (spec)", "tipo": "textarea", "linhas": 14,
                         "padrao": spec_padrao.strip()}]},
        ],
    }


@app.post("/api/gerar")
def gerar(corpo: SpecBody):
    ex = _get_exercicio()
    try:
        spec = corpo.spec.strip() or getattr(ex, "SPEC", "")
        chain = _get_chain(ex)
        resposta = chain.invoke({"spec": spec})
        return {"tipo": "texto", "conteudo": str(resposta)}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao gerar o artefato: {e}")


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