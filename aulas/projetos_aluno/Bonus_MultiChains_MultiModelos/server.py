"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Bônus — Multi-Chains e Multi-Modelos
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8099     (ou: ./run_web.sh)
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
# Chains paralelas (replica do gabarito quando chain_persona é stub)
# ─────────────────────────────────────────────────────────────
def _get_mapa(ex):
    if not _eh_stub(getattr(ex, "chain_persona", None)):
        return ex.mapa_personas
    mapa = {}
    for nome, persona in {
        "resumo": "um resumidor técnico objetivo",
        "pratica": "um professor que dá exemplos práticos",
        "critica": "um revisor crítico que aponta limitações",
    }.items():
        prompt = ex.ChatPromptTemplate.from_messages([
            ("system", f"Você é {persona}. Responda em até 2 frases."),
            ("human", "{pergunta}"),
        ])
        mapa[nome] = (prompt | ex.ChatOllama(model=ex.OLLAMA_MODEL, base_url=ex.OLLAMA_HOST,
                                             temperature=0.5) | ex.StrOutputParser())
    return mapa


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
        return _info_falha(_ERRO_CARGA)
    pendentes = _pendentes(ex, {
        "chain_persona": "chain_persona()",
        "demo_parallel": "demo_parallel()",
        "demo_multi_modelos": "demo_multi_modelos()",
    })
    return {
        "nome": "Bônus — Multi-Chains e Multi-Modelos",
        "modulo": "Módulo 4 · LangGraph / Spec-Driven",
        "descricao": (
            "Execute várias chains em PARALELO (RunnableParallel) com personas "
            "diferentes e combine respostas de mais de um modelo sobre a mesma pergunta."
        ),
        "modo": "acoes",
        "implementado": not pendentes,
        "pendentes": pendentes,
        "parametros": [],
        "acoes": [
            {"endpoint": "/api/paralelo", "titulo": "Chains em paralelo",
             "descricao": "3 personas respondem a mesma pergunta ao mesmo tempo.",
             "metodo": "POST",
             "params": [{"nome": "pergunta", "label": "Pergunta", "tipo": "texto", "padrao": "O que é RAG?"}]},
            {"endpoint": "/api/multi_modelos", "titulo": "Multi-modelos",
             "descricao": "Mesma pergunta para modelos diferentes (o 2º modelo pode falhar se não estiver disponível).",
             "metodo": "POST",
             "params": [{"nome": "pergunta", "label": "Pergunta", "tipo": "texto", "padrao": "Defina 'embedding' em uma frase."}]},
        ],
    }


@app.post("/api/paralelo")
def paralelo(corpo: PerguntaBody):
    ex = _get_exercicio()
    try:
        cadeia = ex.RunnableParallel(_get_mapa(ex))
        resultados = cadeia.invoke({"pergunta": corpo.pergunta})
        return {"tipo": "json", "conteudo": {k: str(v) for k, v in resultados.items()}}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro nas chains paralelas: {e}")


@app.post("/api/multi_modelos")
def multi_modelos(corpo: PerguntaBody):
    ex = _get_exercicio()
    try:
        modelos = [ex.OLLAMA_MODEL, "gpt-oss:20b"]
        prompt = ex.ChatPromptTemplate.from_messages([("human", "{pergunta}")])
        itens = []
        for modelo in modelos:
            try:
                llm = ex.ChatOllama(model=modelo, base_url=ex.OLLAMA_HOST, temperature=0)
                resp = (prompt | llm | ex.StrOutputParser()).invoke({"pergunta": corpo.pergunta})
                itens.append({"titulo": modelo, "texto": str(resp)})
            except Exception as e:  # noqa: BLE001
                itens.append({"titulo": modelo, "texto": f"indisponível: {e}"})
        return {"tipo": "lista", "conteudo": itens}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro no multi-modelos: {e}")


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