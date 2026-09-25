"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 01 — Revisão LangChain: LCEL e ChatOllama
Interface web mínima (FastAPI) para o exercício.

Este arquivo expõe a lógica do main.py via HTTP e serve o frontend React
(previamente compilado em frontend/dist).

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8101

O frontend em desenvolvimento (hot reload) roda com:
    cd frontend && npm install && npm run dev      → http://localhost:5173
"""
import json
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import importlib.util
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

app = FastAPI(
    title="Aula 01 — LCEL e ChatOllama",
    description="Interface web do exercício de revisão LangChain (LCEL + ChatOllama).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def _envelope_erro(mensagem: str, **extra) -> dict:
    return {"tipo": "erro", "conteudo": mensagem, **extra}


def _evento_stream(nome: str, dados: dict) -> str:
    return f"event: {nome}\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n"


class PerguntaBody(BaseModel):
    persona: str = "um chef de culinária brasileira"
    especialidade: str = "culinária brasileira"
    pergunta: str


@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        return _info_falha(_ERRO_CARGA)
    return {
        "nome": "Aula 01 — Revisão LangChain: LCEL e ChatOllama",
        "modulo": "Módulo 1 · LangChain / Context Engineering",
        "descricao": (
            "Construa uma chain LangChain com LCEL e converse com o modelo "
            "Ollama. Compare StrOutputParser, JsonOutputParser e streaming."
        ),
        "modo": "chat",
        "chat_endpoint": "/api/perguntar",
        "implementado": True,
        "pendentes": [],
        "parametros": [
            {"nome": "persona", "label": "Persona", "tipo": "texto", "padrao": "um chef de culinária brasileira"},
            {"nome": "especialidade", "label": "Especialidade", "tipo": "texto", "padrao": "culinária brasileira"},
        ],
        "acoes": [
            {
                "endpoint": "/api/perguntar_json",
                "titulo": "Perguntar (JSON)",
                "descricao": "Chain com JsonOutputParser — responda SOMENTE em JSON pedido no prompt.",
                "metodo": "POST",
                "params": [{"nome": "pergunta", "label": "Pergunta", "tipo": "texto",
                            "padrao": 'Liste 3 ingredientes saudáveis para um bolo de cenoura. Responda SOMENTE em JSON no formato {"ingredientes": ["..."]}.'}],
            },
            {
                "endpoint": "/api/stream",
                "titulo": "Streaming",
                "descricao": "Chain .stream() — cada token chega conforme é gerado.",
                "metodo": "POST",
                "streaming": True,
                "params": [{"nome": "pergunta", "label": "Pergunta", "tipo": "texto",
                            "padrao": "Explique LCEL em 2 frases curtas."}],
            },
        ],
    }


@app.post("/api/perguntar")
def perguntar(corpo: PerguntaBody):
    ex = _get_exercicio()
    try:
        resposta = ex.chain_texto.invoke({
            "persona": corpo.persona,
            "especialidade": corpo.especialidade,
            "pergunta": corpo.pergunta,
        })
        return {"tipo": "texto", "conteudo": str(resposta)}
    except Exception as e:
        raise HTTPException(500, f"Erro ao chamar a chain: {e}") from e


@app.post("/api/perguntar_json")
def perguntar_json(corpo: PerguntaBody):
    ex = _get_exercicio()
    try:
        resultado = ex.chain_json.invoke({
            "persona": corpo.persona,
            "especialidade": corpo.especialidade,
            "pergunta": corpo.pergunta,
        })
        return {"tipo": "json", "conteudo": resultado}
    except Exception as e:
        raise HTTPException(500, f"Erro ao chamar a chain JSON: {e}") from e


@app.post("/api/stream")
def stream(corpo: PerguntaBody):
    ex = _get_exercicio()
    entrada = {
        "persona": corpo.persona,
        "especialidade": corpo.especialidade,
        "pergunta": corpo.pergunta,
    }
    try:
        fluxo = ex.chain_texto.stream(entrada)
        iter(fluxo)
    except Exception as e:
        raise HTTPException(500, f"Erro no streaming: {e}") from e

    def gerar_eventos():
        partes = []
        try:
            for parte in fluxo:
                texto = str(parte)
                partes.append(texto)
                yield _evento_stream("chunk", {"tipo": "chunk", "conteudo": texto})
            yield _evento_stream(
                "done",
                {
                    "tipo": "done",
                    "conteudo": "".join(partes),
                    "extra": {"tokens_recebidos": len(partes)},
                },
            )
        except Exception as e:
            yield _evento_stream(
                "error",
                {"tipo": "erro", "conteudo": f"Erro no streaming: {e}"},
            )

    return StreamingResponse(
        gerar_eventos(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
else:
    @app.get("/")
    def sem_frontend():
        return _envelope_erro(
            "Frontend não compilado. Rode: cd frontend && npm install && npm run build"
        )
