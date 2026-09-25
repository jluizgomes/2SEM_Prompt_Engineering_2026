"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Bônus — Multi-Chains e Multi-Modelos
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8199
"""
import importlib.util
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

app = FastAPI(
    title="Bônus — Multi-Chains e Multi-Modelos",
    description="Interface web do exercício bônus (RunnableParallel + multi-modelos).",
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
class PerguntaBody(BaseModel):
    pergunta: str


class MultiModelosBody(PerguntaBody):
    modelo_primario: str | None = None
    modelo_secundario: str | None = None


# ─────────────────────────────────────────────────────────────
# Endpoints da API
# ─────────────────────────────────────────────────────────────
@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        return _info_falha(_ERRO_CARGA)
    return {
        "nome": "Bônus — Multi-Chains e Multi-Modelos",
        "modulo": "Módulo 4 · LangGraph / Spec-Driven",
        "descricao": (
            "Execute chains em RunnableParallel por persona, rode dois modelos "
            "em paralelo e receba uma síntese com degradação explícita."
        ),
        "modo": "acoes",
        "implementado": True,
        "pendentes": [],
        "parametros": [],
        "acoes": [
            {"endpoint": "/api/paralelo", "titulo": "Chains em paralelo",
             "descricao": "3 personas respondem a mesma pergunta ao mesmo tempo.",
             "metodo": "POST",
             "params": [{"nome": "pergunta", "label": "Pergunta", "tipo": "texto", "padrao": "O que é RAG?"}]},
            {"endpoint": "/api/multi_modelos", "titulo": "Multi-modelos",
             "descricao": "Dois modelos rodam em paralelo e as respostas são sintetizadas.",
             "metodo": "POST",
             "params": [
                 {"nome": "pergunta", "label": "Pergunta", "tipo": "texto", "padrao": "Defina 'embedding' em uma frase."},
                 {"nome": "modelo_primario", "label": "Modelo primário", "tipo": "texto", "padrao": ex.OLLAMA_MODEL},
                 {"nome": "modelo_secundario", "label": "Modelo secundário", "tipo": "texto", "padrao": ex.OLLAMA_MODEL_SECUNDARIO},
             ]},
        ],
    }


@app.post("/api/paralelo")
def paralelo(corpo: PerguntaBody):
    ex = _get_exercicio()
    try:
        resultados = ex.executar_personas(corpo.pergunta)
        return {"tipo": "json", "conteudo": {k: str(v) for k, v in resultados.items()}}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro nas chains paralelas: {e}")


@app.post("/api/multi_modelos")
def multi_modelos(corpo: MultiModelosBody):
    ex = _get_exercicio()
    try:
        resultado = ex.executar_multi_modelos(
            corpo.pergunta,
            modelo_primario=corpo.modelo_primario,
            modelo_secundario=corpo.modelo_secundario,
        )
        return {"tipo": "json", "conteudo": resultado}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Não foi possível gerar a síntese: {e}")


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
