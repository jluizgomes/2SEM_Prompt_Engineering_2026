"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 04 — Context Engineering
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8104
"""
import importlib.util
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(
    title="Aula 04 — Context Engineering",
    description="Interface web do exercício de tokens, histórico e orçamento de contexto.",
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


def _get_chain(exercicio):
    chain = getattr(exercicio, "chain", None)
    if chain is not None and hasattr(chain, "invoke"):
        return chain
    raise RuntimeError("A chain de contexto não está disponível.")


class TextoBody(BaseModel):
    texto: str


class PerguntaBody(BaseModel):
    pergunta: str
    historico: list[dict[str, str]] = Field(default_factory=list)


@app.get("/api/info")
def info():
    exercicio = _get_exercicio_lenient()
    if exercicio is None:
        return _info_falha(_ERRO_CARGA)
    sistema = getattr(exercicio, "SISTEMA", "Você é um assistente de suporte técnico da FIAP.")
    return {
        "nome": "Aula 04 — Context Engineering",
        "modulo": "Módulo 1 · LangChain / Context Engineering",
        "descricao": (
            "Meça o custo invisível do contexto, preserve o histórico da conversa e "
            f"respeite um orçamento de tokens antes de chamar o modelo. SISTEMA: {sistema[:200]}"
        ),
        "modo": "acoes",
        "implementado": True,
        "pendentes": [],
        "parametros": [],
        "acoes": [
            {
                "endpoint": "/api/contar_tokens",
                "titulo": "Contar tokens",
                "descricao": "Mede quantos tokens um texto consome.",
                "metodo": "POST",
                "params": [
                    {
                        "nome": "texto",
                        "label": "Texto",
                        "tipo": "textarea",
                        "linhas": 3,
                        "padrao": "Explique o que é context window em um LLM e por que ele importa.",
                    }
                ],
            },
            {
                "endpoint": "/api/perguntar",
                "titulo": "Perguntar com contexto",
                "descricao": "Aciona o modelo com sistema, histórico limitado e pergunta atual.",
                "metodo": "POST",
                "params": [
                    {
                        "nome": "pergunta",
                        "label": "Pergunta",
                        "tipo": "texto",
                        "padrao": "O que significa 'janela de contexto'?",
                    }
                ],
            },
        ],
    }


@app.post("/api/contar_tokens")
def contar_tokens(corpo: TextoBody):
    exercicio = _get_exercicio()
    try:
        n = exercicio.contar_tokens(corpo.texto)
        return {"tipo": "texto", "conteudo": f"{n} tokens"}
    except Exception as erro:
        raise HTTPException(500, f"Erro ao contar tokens: {erro}") from erro


@app.post("/api/perguntar")
def perguntar(corpo: PerguntaBody):
    exercicio = _get_exercicio()
    try:
        chain = _get_chain(exercicio)
        resposta = chain.invoke(
            {
                "pergunta": corpo.pergunta,
                "historico": corpo.historico,
            }
        )
        return {"tipo": "texto", "conteudo": str(resposta)}
    except HTTPException:
        raise
    except RuntimeError as erro:
        raise HTTPException(503, str(erro)) from erro
    except Exception as erro:
        raise HTTPException(500, f"Erro ao perguntar: {erro}") from erro


if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
else:
    @app.get("/")
    def sem_frontend():
        return {
            "tipo": "erro",
            "conteudo": "Frontend não compilado. Rode: cd frontend && npm install && npm run build",
        }
