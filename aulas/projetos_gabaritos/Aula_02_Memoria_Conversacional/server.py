"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 02 — Memória Conversacional (Buffer, Summary, TokenBuffer)
Interface web mínima (FastAPI) para o exercício.

Este arquivo expõe a lógica do main.py via HTTP e serve o frontend React
(previamente compilado em frontend/dist). O servidor mantém uma conversa por
tipo de memória e por sessão, em memória de processo.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8102

O frontend em desenvolvimento (hot reload) roda com:
    cd frontend && npm install && npm run dev      → http://localhost:5173
"""
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import importlib.util
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from memory import criar_contador_tokens

app = FastAPI(
    title="Aula 02 — Memória Conversacional",
    description="Interface web do exercício de memória conversacional (Buffer/Summary/TokenBuffer).",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DIST = Path(__file__).resolve().parent / "frontend" / "dist"
_SESSION_COOKIE = "aula02_session_id"
_SESSION_HEADER = "X-Session-ID"
_EXERCICIO = None
_ERRO_CARGA = None
_SESSOES = {}


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


def _normalizar_tipo(tipo: str | None) -> str:
    return tipo if tipo in ("buffer", "summary", "token_buffer") else "buffer"


def _validar_session_id(valor: str | None) -> str | None:
    if valor is None:
        return None
    normalizado = str(valor).strip()
    if not normalizado:
        return None
    if len(normalizado) > 128 or any(
        not (caractere.isalnum() or caractere in "-_.") for caractere in normalizado
    ):
        raise HTTPException(400, "session_id inválido.")
    return normalizado


def _resolver_session_id(session_id: str | None, request: Request) -> str:
    valor = _validar_session_id(
        session_id or request.headers.get(_SESSION_HEADER) or request.cookies.get(_SESSION_COOKIE)
    )
    return valor or uuid4().hex


def _definir_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        _SESSION_COOKIE,
        session_id,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _estado_sessao(session_id: str) -> dict:
    return _SESSOES.setdefault(
        session_id,
        {"canais": {}, "tipo_selecionado": "buffer"},
    )


def _pegar_canal(ex, tipo: str, estado: dict):
    tipo = _normalizar_tipo(tipo)
    canais = estado["canais"]
    if tipo not in canais:
        if tipo == "summary":
            memoria = ex.ConversationSummaryMemory(
                llm=ex.llm,
                memory_key="history",
                return_messages=True,
            )
        elif tipo == "token_buffer":
            memoria = ex.ConversationTokenBufferMemory(
                llm=criar_contador_tokens(),
                max_token_limit=500,
                memory_key="history",
                return_messages=True,
            )
        else:
            memoria = ex.ConversationBufferMemory(
                memory_key="history",
                return_messages=True,
            )
        canais[tipo] = {
            "chain": ex.ConversationChain(llm=ex.llm, memory=memoria, verbose=False),
            "memoria": memoria,
        }
    return canais[tipo]


def _extrair_texto(valor) -> str:
    if isinstance(valor, list):
        partes = []
        for item in valor:
            if isinstance(item, dict):
                partes.append(str(item.get("text", item.get("content", ""))))
            else:
                partes.append(str(item))
        return "".join(partes)
    if isinstance(valor, dict):
        return str(valor.get("text", valor.get("content", "")))
    return str(valor if valor is not None else "")


def _normalizar_historico(historico):
    if isinstance(historico, str):
        return [{"titulo": "Histórico", "papel": "sistema", "texto": historico}]
    if isinstance(historico, dict):
        historico = [historico]
    if not isinstance(historico, list):
        return []

    rotulos = {
        "human": ("Usuário", "usuario"),
        "user": ("Usuário", "usuario"),
        "ai": ("Assistente", "assistente"),
        "assistant": ("Assistente", "assistente"),
        "system": ("Sistema", "sistema"),
        "tool": ("Ferramenta", "ferramenta"),
    }
    itens = []
    for mensagem in historico:
        if isinstance(mensagem, dict):
            papel = mensagem.get("role") or mensagem.get("type") or "mensagem"
            conteudo = mensagem.get("content", mensagem.get("texto", mensagem.get("text", "")))
        else:
            papel = getattr(mensagem, "type", None) or getattr(mensagem, "role", None) or "mensagem"
            conteudo = getattr(mensagem, "content", mensagem)
        titulo, papel_normalizado = rotulos.get(str(papel).lower(), ("Mensagem", "mensagem"))
        itens.append({
            "titulo": titulo,
            "papel": papel_normalizado,
            "texto": _extrair_texto(conteudo),
        })
    return itens


class MensagemBody(BaseModel):
    mensagem: str
    tipo_memoria: str = "buffer"
    session_id: str | None = None


class EstadoBody(BaseModel):
    tipo_memoria: str | None = None
    session_id: str | None = None


@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        return _info_falha(_ERRO_CARGA)
    return {
        "nome": "Aula 02 — Memória Conversacional",
        "modulo": "Módulo 1 · LangChain / Context Engineering",
        "descricao": (
            "Converse escolhendo o tipo de memória: Buffer guarda tudo, Summary resume "
            "com o próprio LLM e TokenBuffer mantém uma janela de tokens. O que for "
            "conversado fica isolado por sessão até o reset."
        ),
        "modo": "chat",
        "chat_endpoint": "/api/conversar",
        "implementado": True,
        "pendentes": [],
        "parametros": [
            {
                "nome": "tipo_memoria",
                "label": "Tipo de memória",
                "tipo": "select",
                "padrao": "buffer",
                "opcoes": ["buffer", "summary", "token_buffer"],
            },
        ],
        "acoes": [
            {
                "endpoint": "/api/estado",
                "titulo": "Ver estado da memória",
                "descricao": "Mostra o canal selecionado e o que está armazenado na sessão atual.",
                "metodo": "POST",
                "params": [],
            },
            {
                "endpoint": "/api/resetar",
                "titulo": "Resetar memória",
                "descricao": "Limpa a conversa da sessão atual do servidor.",
                "metodo": "POST",
                "params": [],
            },
        ],
    }


@app.post("/api/conversar")
def conversar(corpo: MensagemBody, request: Request, response: Response):
    ex = _get_exercicio()
    try:
        session_id = _resolver_session_id(corpo.session_id, request)
        _definir_cookie(response, session_id)
        tipo = _normalizar_tipo(corpo.tipo_memoria)
        estado = _estado_sessao(session_id)
        canal = _pegar_canal(ex, tipo, estado)
        estado["tipo_selecionado"] = tipo
        resposta = canal["chain"].predict(input=corpo.mensagem)
        return {
            "tipo": "texto",
            "conteudo": str(resposta),
            "extra": {
                "tipo_memoria": tipo,
                "canal": tipo,
                "session_id": session_id,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erro ao conversar: {e}") from e


@app.post("/api/estado")
def estado(request: Request, response: Response, corpo: EstadoBody | None = None):
    ex = _get_exercicio()
    try:
        corpo = corpo or EstadoBody()
        session_id = _resolver_session_id(corpo.session_id, request)
        _definir_cookie(response, session_id)
        estado_sessao = _estado_sessao(session_id)
        tipo = _normalizar_tipo(corpo.tipo_memoria or estado_sessao["tipo_selecionado"])
        canal = _pegar_canal(ex, tipo, estado_sessao)
        estado_sessao["tipo_selecionado"] = tipo
        historico = canal["memoria"].load_memory_variables({}).get("history", [])
        return {
            "tipo": "lista",
            "conteudo": _normalizar_historico(historico),
            "extra": {
                "tipo_memoria": tipo,
                "canal": tipo,
                "session_id": session_id,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erro ao ler o estado: {e}") from e


@app.post("/api/resetar")
def resetar(request: Request, response: Response, corpo: EstadoBody | None = None):
    try:
        corpo = corpo or EstadoBody()
        session_id = _resolver_session_id(corpo.session_id, request)
        _SESSOES.pop(session_id, None)
        response.delete_cookie(_SESSION_COOKIE, path="/")
        return {
            "tipo": "texto",
            "conteudo": "Memória resetada.",
            "extra": {"tipo_memoria": "buffer", "canal": "buffer", "session_id": session_id},
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erro ao resetar a memória: {e}") from e


if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
else:
    @app.get("/")
    def sem_frontend():
        return {
            "tipo": "erro",
            "conteudo": "Frontend não compilado. Rode: cd frontend && npm install && npm run build",
        }
