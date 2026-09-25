"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 04 — Context Engineering
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8004     (ou: ./run_web.sh)
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
    title="Aula 04 — Context Engineering",
    description="Interface web do exercício de Context Engineering (tokens + prompt de sistema).",
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


def _get_chain(ex):
    chain = getattr(ex, "chain", None)
    if chain is None and hasattr(ex, "prompt"):
        parser = getattr(ex, "StrOutputParser", None)
        chain = ex.prompt | ex.llm | (parser() if parser else lambda x: str(x.content))
    return chain


# ─────────────────────────────────────────────────────────────
# Modelos de requisição
# ─────────────────────────────────────────────────────────────
class TextoBody(BaseModel):
    texto: str


class PerguntaBody(BaseModel):
    pergunta: str


# ─────────────────────────────────────────────────────────────
# Endpoints da API
# ─────────────────────────────────────────────────────────────
@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        return _info_falha(_ERRO_CARGA)
    pendentes = _pendentes(ex, {"main": "main()"})
    sistema = getattr(ex, "SISTEMA", "Você é um assistente de suporte técnico da FIAP.")
    return {
        "nome": "Aula 04 — Context Engineering",
        "modulo": "Módulo 1 · LangChain / Context Engineering",
        "descricao": (
            "Meça o custo invisível do contexto: conte tokens com tiktoken e pergunte "
            "para a chain que monta o prompt com instrução de sistema embutida.\n\n"
            f"SISTEMA: {sistema[:200]}"
        ),
        "modo": "acoes",
        "implementado": not pendentes,
        "pendentes": pendentes,
        "parametros": [],
        "acoes": [
            {"endpoint": "/api/contar_tokens", "titulo": "Contar tokens",
             "descricao": "Mede quantos tokens (tiktoken, aprox. gpt-4o) um texto consome.",
             "metodo": "POST",
             "params": [{"nome": "texto", "label": "Texto", "tipo": "textarea", "linhas": 3,
                         "padrao": "Explique o que é context window em um LLM e por que ele importa."}]},
            {"endpoint": "/api/perguntar", "titulo": "Perguntar (com instrução de sistema)",
             "descricao": "Chain com o SISTEMA embutido — responda objetivamente em pt-BR.",
             "metodo": "POST",
             "params": [{"nome": "pergunta", "label": "Pergunta", "tipo": "texto",
                         "padrao": "O que significa 'janela de contexto'?"}]},
        ],
    }


@app.post("/api/contar_tokens")
def contar_tokens(corpo: TextoBody):
    ex = _get_exercicio()
    try:
        exportado = getattr(ex, "contar_tokens", None)
        if exportado is not None and not _eh_stub(exportado):
            n = exportado(corpo.texto)
            return {"tipo": "texto", "conteudo": f"{n} tokens"}
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model("gpt-4o")
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        n = len(enc.encode(corpo.texto))
        return {"tipo": "texto", "conteudo": f"{n} tokens"}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao contar tokens: {e}")


@app.post("/api/perguntar")
def perguntar(corpo: PerguntaBody):
    ex = _get_exercicio()
    try:
        chain = _get_chain(ex)
        if chain is None:
            raise HTTPException(501, "TODO não implementado: monte a chain no main.py (prompt | llm | StrOutputParser).")
        resposta = chain.invoke({"pergunta": corpo.pergunta})
        return {"tipo": "texto", "conteudo": str(resposta)}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao perguntar: {e}")


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