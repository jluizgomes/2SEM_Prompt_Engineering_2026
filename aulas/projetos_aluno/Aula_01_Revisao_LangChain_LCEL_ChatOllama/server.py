"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 01 — Revisão LangChain: LCEL e ChatOllama
Interface web mínima (FastAPI) para o exercício.

Este arquivo expõe a lógica do main.py via HTTP e serve o frontend React
(previamente compilado em frontend/dist).

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8001     (ou: ./run_web.sh)

O frontend em desenvolvimento (hot reload) roda com:
    cd frontend && npm install && npm run dev      → http://localhost:5173
"""
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # resolve caminhos relativos (.env, chroma_db, data/)

import importlib.util
import inspect
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────
# Configuração do app
# ─────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────
# Carga do exercício (main.py) — com cache e erro amigável
# ─────────────────────────────────────────────────────────────
_EXERCICIO = None
_ERRO_CARGA = None


def _carregar_main():
    """Importa o main.py da mesma pasta (funciona mesmo fora do CWD)."""
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
        except Exception as e:  # noqa: BLE001 — exibe o erro para o usuário
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
    """True se a função ainda é um esqueleto com 'pass' (TODO não resolvido)."""
    if funcao is None:
        return True
    try:
        fonte = inspect.getsource(funcao)
    except (OSError, TypeError, IOError):
        return False
    fonte = re.sub(r'""".*?"""', "", fonte, flags=re.S)  # remove docstrings
    return bool(re.search(r"^\s*pass\s*$", fonte, flags=re.M))


def _pendentes(ex, nomes: dict) -> list:
    """Nomes legíveis das funções do main.py que ainda são esqueletos (TODO)."""
    return [rotulo for nome, rotulo in nomes.items() if _eh_stub(getattr(ex, nome, None))]


def _envelope_erro(mensagem: str, **extra) -> dict:
    return {"tipo": "erro", "conteudo": mensagem, **extra}


# ─────────────────────────────────────────────────────────────
# Modelos de requisição
# ─────────────────────────────────────────────────────────────
class PerguntaBody(BaseModel):
    persona: str = "um chef de culinária brasileira"
    especialidade: str = "culinária brasileira"
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
        "demo_chain_texto": "demo_chain_texto()",
        "demo_chain_json": "demo_chain_json()",
        "demo_stream": "demo_stream()",
    })
    return {
        "nome": "Aula 01 — Revisão LangChain: LCEL e ChatOllama",
        "modulo": "Módulo 1 · LangChain / Context Engineering",
        "descricao": (
            "Construa uma chain LangChain com LCEL e converse com o modelo "
            "Ollama. Compare StrOutputParser, JsonOutputParser e streaming."
        ),
        "modo": "chat",
        "chat_endpoint": "/api/perguntar",
        "implementado": not pendentes,
        "pendentes": pendentes,
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
                "params": [{"nome": "pergunta", "label": "Pergunta", "tipo": "texto",
                            "padrao": "Explique LCEL em 2 frases curtas."}],
            },
        ],
    }


@app.post("/api/perguntar")
def perguntar(corpo: PerguntaBody):
    """Chain com StrOutputParser: devolve string direta."""
    ex = _get_exercicio()
    try:
        resposta = ex.chain_texto.invoke({
            "persona": corpo.persona,
            "especialidade": corpo.especialidade,
            "pergunta": corpo.pergunta,
        })
        return {"tipo": "texto", "conteudo": str(resposta)}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao chamar a chain: {e}")


@app.post("/api/perguntar_json")
def perguntar_json(corpo: PerguntaBody):
    """Chain com JsonOutputParser: devolve dict."""
    ex = _get_exercicio()
    try:
        resultado = ex.chain_json.invoke({
            "persona": corpo.persona,
            "especialidade": corpo.especialidade,
            "pergunta": corpo.pergunta,
        })
        return {"tipo": "json", "conteudo": resultado}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao chamar a chain JSON: {e}")


@app.post("/api/stream")
def stream(corpo: PerguntaBody):
    """Chain .stream(): coleta os tokens e devolve o texto completo."""
    ex = _get_exercicio()
    try:
        partes = list(ex.chain_texto.stream({
            "persona": corpo.persona,
            "especialidade": corpo.especialidade,
            "pergunta": corpo.pergunta,
        }))
        texto = "".join(str(p) for p in partes)
        return {"tipo": "texto", "conteudo": texto,
                "extra": {"tokens_recebidos": len(partes)}}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro no streaming: {e}")


# ─────────────────────────────────────────────────────────────
# Frontend estático (React) — se já estiver compilado
# ─────────────────────────────────────────────────────────────
if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
else:
    @app.get("/")
    def sem_frontend():
        return _envelope_erro(
            "Frontend não compilado. Rode: cd frontend && npm install && npm run build"
        )