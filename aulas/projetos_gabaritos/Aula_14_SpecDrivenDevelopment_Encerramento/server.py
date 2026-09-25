"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 14 — Spec-Driven Development e Encerramento
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8114
"""
import importlib.util
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
        "descricao": "Não foi possível carregar o main.py deste exercício.",
        "modo": "acoes",
        "implementado": False,
        "pendentes": [f"main.py não pôde ser importado: {erro}"],
        "parametros": [],
        "acoes": [],
    }


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
    return {
        "nome": "Aula 14 — Spec-Driven Development e Encerramento",
        "modulo": "Módulo 4 · LangGraph / Spec-Driven",
        "descricao": (
            "A especificação define um contrato Pydantic; a resposta do modelo é "
            "validada e refeita quando necessário antes de ser retornada."
        ),
        "modo": "acoes",
        "implementado": True,
        "pendentes": [],
        "parametros": [],
        "acoes": [
            {"endpoint": "/api/gerar", "titulo": "Gerar artefato a partir do spec",
             "descricao": "Valida a saída no contrato e realiza retry em caso de formato inválido.",
             "metodo": "POST",
             "params": [{"nome": "spec", "label": "Especificação (spec)", "tipo": "textarea", "linhas": 14,
                         "padrao": getattr(ex, "SPEC", "").strip()}]},
        ],
    }


@app.post("/api/gerar")
def gerar(corpo: SpecBody):
    ex = _get_exercicio()
    try:
        spec = corpo.spec.strip() or getattr(ex, "SPEC", "")
        artefato = ex.gerar_artefato(spec)
        return {"tipo": "json", "conteudo": artefato.model_dump(mode="json")}
    except ex.RespostaForaDoContrato as e:
        raise HTTPException(502, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Falha do modelo durante a geração validada: {e}")


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
