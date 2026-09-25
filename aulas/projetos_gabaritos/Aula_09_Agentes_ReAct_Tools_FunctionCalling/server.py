"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 09 — Agentes ReAct, Tools e Function Calling
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8109
"""
import importlib.util
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

PASTA = Path(__file__).resolve().parent
if str(PASTA) not in sys.path:
    sys.path.insert(0, str(PASTA))

app = FastAPI(
    title="Aula 09 — Agentes ReAct, Tools e Function Calling",
    description="Interface web do exercício de agente ReAct com tools.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
DIST = Path(__file__).resolve().parent / "frontend" / "dist"
_EXERCICIO = None
_AGENTE = None
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
        except Exception as exc:
            _ERRO_CARGA = str(exc)
    if _ERRO_CARGA is not None:
        raise HTTPException(502, f"Não foi possível carregar o exercício:\n{_ERRO_CARGA}")
    return _EXERCICIO


def _get_agente():
    global _AGENTE, _ERRO_CARGA
    if _AGENTE is None and _ERRO_CARGA is None:
        try:
            exercicio = _get_exercicio()
            configuracao = exercicio.configuracao_modelo()
            llm = exercicio.criar_llm(configuracao)
            _AGENTE = exercicio.criar_agente(llm, exercicio.criar_tools())
        except HTTPException:
            raise
        except Exception as exc:
            _ERRO_CARGA = str(exc)
    if _ERRO_CARGA is not None:
        raise HTTPException(502, f"Não foi possível inicializar o agente:\n{_ERRO_CARGA}")
    return _AGENTE


class PerguntaBody(BaseModel):
    mensagem: str = Field(min_length=1, max_length=4000)


@app.get("/api/info")
def info():
    return {
        "nome": "Aula 09 — Agentes ReAct, Tools e Function Calling",
        "modulo": "Módulo 3 · Interfaces / Agentes",
        "descricao": (
            "Agente ReAct atual criado com langchain.agents.create_agent, "
            "calculadora segura e busca DDGS tolerante a falhas."
        ),
        "modo": "chat",
        "chat_endpoint": "/api/perguntar",
        "implementado": True,
        "pendentes": [],
        "parametros": [],
        "acoes": [],
    }


@app.post("/api/perguntar")
def perguntar(corpo: PerguntaBody):
    try:
        agente = _get_agente()
        resultado = agente.invoke({"messages": [{"role": "user", "content": corpo.mensagem}]})
        return {
            "tipo": "texto",
            "conteudo": _get_exercicio().extrair_resultado(resultado),
            "extra": {"passos": _get_exercicio().extrair_passos(resultado)},
        }
    except HTTPException as exc:
        return {"tipo": "erro", "conteudo": str(exc.detail)}
    except Exception as exc:
        return {
            "tipo": "erro",
            "conteudo": f"A execução desta pergunta falhou: {exc}. A próxima pergunta poderá ser enviada normalmente.",
        }


if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
else:
    @app.get("/")
    def sem_frontend():
        return {
            "tipo": "erro",
            "conteudo": "Frontend não compilado. Rode: cd frontend && npm install && npm run build",
        }
