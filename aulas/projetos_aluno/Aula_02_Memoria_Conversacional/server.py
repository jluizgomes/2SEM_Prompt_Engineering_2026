"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 02 — Memória Conversacional (Buffer, Summary, TokenBuffer)
Interface web mínima (FastAPI) para o exercício.

Este arquivo expõe a lógica do main.py via HTTP e serve o frontend React
(previamente compilado em frontend/dist). O servidor mantém UMA conversa por
tipo de memória em memória (estado em processo).

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8002     (ou: ./run_web.sh)

O frontend em desenvolvimento (hot reload) roda com:
    cd frontend && npm install && npm run dev      → http://localhost:5173
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
    title="Aula 02 — Memória Conversacional",
    description="Interface web do exercício de memória conversacional (Buffer/Summary/TokenBuffer).",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DIST = Path(__file__).resolve().parent / "frontend" / "dist"

# ─────────────────────────────────────────────────────────────
# Carga do exercício (main.py) — com cache e erro amigável
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


class _ContadorTokens:
    """Contador de tokens SEM transformers (o ChatOllama não tokeniza localmente).

    Usa tiktoken quando disponível; senão aproxima ~4 caracteres por token.
    Implementa get_num_tokens_from_messages() para a ConversationTokenBufferMemory
    (clássica) truncar o histórico pela janela de tokens.
    """

    @staticmethod
    def _conta(texto: str) -> int:
        try:
            import tiktoken
            try:
                enc = tiktoken.encoding_for_model("gpt-4o")
            except KeyError:
                enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(texto))
        except Exception:  # noqa: BLE001 — fallback heurístico
            return max(1, len(texto) // 4)

    def get_num_tokens_from_messages(self, mensagens) -> int:
        total = 0
        for m in mensagens:
            total += self._conta(str(getattr(m, "content", m)))
        return total


# ─────────────────────────────────────────────────────────────
# Estado da conversa (uma chain por tipo de memória)
# ─────────────────────────────────────────────────────────────
_CANAIS = {}  # tipo -> {"chain": ConversationChain, "memoria": Memory}


def _pegar_canal(ex, tipo: str):
    if tipo not in _CANAIS:
        if tipo == "summary":
            memoria = ex.ConversationSummaryMemory(llm=ex.llm, memory_key="history",
                                                   return_messages=True)
        elif tipo == "token_buffer":
            memoria = ex.ConversationTokenBufferMemory(llm=ex.llm, max_token_limit=500,
                                                       memory_key="history", return_messages=True)
            # troca o tokenizador após a validação do Pydantic: evita exigir
            # `transformers` só para contar tokens (o ChatOllama não tokeniza localmente)
            memoria.llm = _ContadorTokens()
        else:
            memoria = ex.ConversationBufferMemory(memory_key="history", return_messages=True)
        _CANAIS[tipo] = {"chain": ex.ConversationChain(llm=ex.llm, memory=memoria, verbose=False),
                         "memoria": memoria}
    return _CANAIS[tipo]


def _normalizar_historico(historico):
    """Aceita lista de mensagens ou string e normaliza para exibição."""
    if isinstance(historico, str):
        return [{"titulo": 1, "texto": historico}]
    if isinstance(historico, list):
        return [{"titulo": i + 1, "texto": str(m)} for i, m in enumerate(historico)]
    return []


# ─────────────────────────────────────────────────────────────
# Modelos de requisição
# ─────────────────────────────────────────────────────────────
class MensagemBody(BaseModel):
    mensagem: str
    tipo_memoria: str = "buffer"


# ─────────────────────────────────────────────────────────────
# Endpoints da API
# ─────────────────────────────────────────────────────────────
@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        return _info_falha(_ERRO_CARGA)
    pendentes = _pendentes(ex, {
        "demo_buffer": "demo_buffer()",
        "demo_summary": "demo_summary()",
        "demo_token_buffer": "demo_token_buffer()",
        "demo_prompt_customizado": "demo_prompt_customizado()",
    })
    return {
        "nome": "Aula 02 — Memória Conversacional",
        "modulo": "Módulo 1 · LangChain / Context Engineering",
        "descricao": (
            "Converse escolhendo o tipo de memória: Buffer guarda tudo, Summary resume "
            "com o próprio LLM e TokenBuffer mantém uma janela de tokens. O que for "
            "conversado fica na memória do servidor até o reset."
        ),
        "modo": "chat",
        "chat_endpoint": "/api/conversar",
        "implementado": not pendentes,
        "pendentes": pendentes,
        "parametros": [
            {"nome": "tipo_memoria", "label": "Tipo de memória", "tipo": "select", "padrao": "buffer",
             "opcoes": ["buffer", "summary", "token_buffer"]},
        ],
        "acoes": [
            {"endpoint": "/api/estado", "titulo": "Ver estado da memória",
             "descricao": "Mostra o que está armazenado na memória da conversa atual.",
             "metodo": "POST", "params": []},
            {"endpoint": "/api/resetar", "titulo": "Resetar memória",
             "descricao": "Limpa a conversa atual do servidor.",
             "metodo": "POST", "params": []},
        ],
    }


@app.post("/api/conversar")
def conversar(corpo: MensagemBody):
    ex = _get_exercicio()
    try:
        tipo = corpo.tipo_memoria if corpo.tipo_memoria in ("buffer", "summary", "token_buffer") else "buffer"
        canal = _pegar_canal(ex, tipo)
        resposta = canal["chain"].predict(input=corpo.mensagem)
        return {"tipo": "texto", "conteudo": str(resposta), "extra": {"tipo_memoria": tipo}}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao conversar: {e}")


@app.post("/api/estado")
def estado():
    ex = _get_exercicio()
    try:
        # usa o tipo mais recente (última chave criada) ou buffer
        tipo = list(_CANAIS.keys())[-1] if _CANAIS else "buffer"
        canal = _pegar_canal(ex, tipo)
        historico = canal["memoria"].load_memory_variables({}).get("history", [])
        return {"tipo": "lista", "conteudo": _normalizar_historico(historico),
                "extra": {"tipo_memoria": tipo}}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao ler o estado: {e}")


@app.post("/api/resetar")
def resetar():
    _CANAIS.clear()
    return {"tipo": "texto", "conteudo": "Memória resetada."}


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