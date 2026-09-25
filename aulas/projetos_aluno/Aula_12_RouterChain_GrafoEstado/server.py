"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 12 — Router Chain e Grafo de Estado
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8012     (ou: ./run_web.sh)
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
    title="Aula 12 — Router Chain e Grafo de Estado",
    description="Interface web do exercício de roteamento por intenção.",
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
# Roteador (usa objetos do main.py; replica o padrão do gabarito
# quando o aluno ainda não montou classifier/chains)
# ─────────────────────────────────────────────────────────────
def _get_classificador(ex):
    classificador = getattr(ex, "classificador", None)
    if classificador is not None:
        return classificador
    return ex.classificador_prompt | ex.llm.with_structured_output(ex.Intencao)


def _get_chains(ex):
    """Retorna (chain_documentos, chain_calculo, chain_geral)."""
    parser = getattr(ex, "StrOutputParser", None) or __import__(
        "langchain_core.output_parsers", fromlist=["StrOutputParser"]).StrOutputParser

    chain_documentos = getattr(ex, "chain_documentos", None)
    if chain_documentos is None:
        retriever = ex.vectorstore.as_retriever(search_kwargs={"k": 2})
        prompt = ex.ChatPromptTemplate.from_messages([
            ("system", "Responda com base no contexto:\n{contexto}"),
            ("human", "{pergunta}"),
        ])
        chain_documentos = (
            {"contexto": retriever, "pergunta": ex.RunnableLambda(lambda x: x["pergunta"])}
            | prompt | ex.llm | parser()
        )

    chain_calculo = getattr(ex, "chain_calculo", None)
    if chain_calculo is None:
        prompt = ex.ChatPromptTemplate.from_messages([
            ("system", "Você é uma calculadora. Resolva a conta e responda só o número."),
            ("human", "{pergunta}"),
        ])
        chain_calculo = prompt | ex.llm | parser()

    chain_geral = getattr(ex, "chain_geral", None)
    if chain_geral is None:
        prompt = ex.ChatPromptTemplate.from_messages([
            ("system", "Responda de forma geral e objetiva."),
            ("human", "{pergunta}"),
        ])
        chain_geral = prompt | ex.llm | parser()

    return chain_documentos, chain_calculo, chain_geral


# ─────────────────────────────────────────────────────────────
# Modelos de requisição
# ─────────────────────────────────────────────────────────────
class PerguntaBody(BaseModel):
    pergunta: str


# ─────────────────────────────────────────────────────────────
# Endpoints da API
# ─────────────────────────────────────────────────────────────
@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        base = _info_falha(_ERRO_CARGA)
        base["pendentes"].append(
            "Dica: verifique o Ollama local em EMBEDDING_OLLAMA_HOST e se o "
            "modelo de embeddings foi baixado."
        )
        return base
    pendentes = _pendentes(ex, {
        "classificador": "classificador",
        "chain_documentos": "chain_documentos",
        "chain_calculo": "chain_calculo",
        "chain_geral": "chain_geral",
        "rotear": "rotear()",
    })
    return {
        "nome": "Aula 12 — Router Chain e Grafo de Estado",
        "modulo": "Módulo 4 · LangGraph / Spec-Driven",
        "descricao": (
            "Roteie uma pergunta para a chain correta conforme a intenção: "
            "'documentos' (busca no ChromaDB da FIAP), 'calculo' ou 'geral'. "
            "A categoria detectada aparece junto com a resposta."
        ),
        "modo": "acoes",
        "implementado": not pendentes,
        "pendentes": pendentes,
        "parametros": [],
        "acoes": [
            {"endpoint": "/api/rotear", "titulo": "Roteando pergunta",
             "descricao": "Classifica a intenção com structured output e invoca a chain correta.",
             "metodo": "POST",
             "params": [{"nome": "pergunta", "label": "Pergunta", "tipo": "texto",
                         "padrao": "Onde fica a FIAP?"}]},
        ],
    }


@app.post("/api/rotear")
def rotear(corpo: PerguntaBody):
    ex = _get_exercicio()
    try:
        classificador = _get_classificador(ex)
        intencao = classificador.invoke({"pergunta": corpo.pergunta})
        categoria = (intencao.categoria or "").lower()
        chain_documentos, chain_calculo, chain_geral = _get_chains(ex)
        if categoria == "documentos":
            resposta = chain_documentos.invoke({"pergunta": corpo.pergunta})
        elif categoria == "calculo":
            resposta = chain_calculo.invoke({"pergunta": corpo.pergunta})
        else:
            resposta = chain_geral.invoke({"pergunta": corpo.pergunta})
        return {"tipo": "json",
                "conteudo": {"categoria": categoria, "resposta": str(resposta)}}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao rotear: {e}")


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