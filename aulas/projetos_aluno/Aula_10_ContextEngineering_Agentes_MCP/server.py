"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 10 — Context Engineering e Agentes MCP
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8010     (ou: ./run_web.sh)
"""
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import importlib.util
import inspect
import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

app = FastAPI(
    title="Aula 10 — Context Engineering e Agentes MCP",
    description="Interface web do exercício de trim_messages e MCP.",
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
# Modelos de requisição
# ─────────────────────────────────────────────────────────────
_DEFAULT_MENSAGENS = [
    {"role": "human", "content": "Olá!"},
    {"role": "ai", "content": "Oi! Como posso ajudar?"},
    {"role": "human", "content": "Me fale sobre LangChain."},
    {"role": "ai", "content": "LangChain é um framework para aplicações com LLMs."},
    {"role": "human", "content": "E sobre memória?"},
]


class TrimBody(BaseModel):
    mensagens: object = _DEFAULT_MENSAGENS  # pode ser lista ou string JSON
    max_tokens: str = "40"


class TextoBody(BaseModel):
    texto: str


# ─────────────────────────────────────────────────────────────
# Endpoints da API
# ─────────────────────────────────────────────────────────────
@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        return _info_falha(_ERRO_CARGA)
    pendentes = _pendentes(ex, {
        "demo_trim_messages": "demo_trim_messages()",
        "contar_palavras": "contar_palavras() (tool)",
        "demo_mcp_tools": "demo_mcp_tools()",
    })
    return {
        "nome": "Aula 10 — Context Engineering e Agentes MCP",
        "modulo": "Módulo 3 · Interfaces / Agentes",
        "descricao": (
            "Controle o tamanho do contexto com trim_messages (janela deslizante de "
            "tokens) e conecte tools via MCP (Model Context Protocol). Para o MCP, "
            "defina MCP_SERVER_URL no .env."
        ),
        "modo": "acoes",
        "implementado": not pendentes,
        "pendentes": pendentes,
        "parametros": [],
        "acoes": [
            {"endpoint": "/api/trim_messages", "titulo": "trim_messages",
             "descricao": "Recorta uma lista de mensagens pela janela de tokens (o campo aceita JSON ou string JSON).",
             "metodo": "POST",
             "params": [
                 {"nome": "mensagens", "label": "Mensagens (JSON)", "tipo": "textarea", "linhas": 8,
                  "padrao": json.dumps(_DEFAULT_MENSAGENS, ensure_ascii=False, indent=2)},
                 {"nome": "max_tokens", "label": "max_tokens", "tipo": "texto", "padrao": "40"},
             ]},
            {"endpoint": "/api/contar_palavras", "titulo": "Contar palavras (tool)",
             "descricao": "Tool local simples do exercício.",
             "metodo": "POST",
             "params": [{"nome": "texto", "label": "Texto", "tipo": "texto", "padrao": "LangChain e MCP em uma frase"}]},
            {"endpoint": "/api/mcp_tools", "titulo": "Carregar tools MCP",
             "descricao": "Conecta no servidor MCP apontado por MCP_SERVER_URL (.env).",
             "metodo": "POST", "params": []},
        ],
    }


@app.post("/api/trim_messages")
def trim_messages(corpo: TrimBody):
    ex = _get_exercicio()
    try:
        max_tokens = int(corpo.max_tokens or "40")
    except ValueError:
        max_tokens = 40
    try:
        dados = corpo.mensagens
        if isinstance(dados, str):
            dados = json.loads(dados)
        if not isinstance(dados, list) or not dados:
            dados = _DEFAULT_MENSAGENS
        mensagens = []
        for item in dados:
            role = (item.get("role") if isinstance(item, dict) else "human") or "human"
            content = item.get("content", "") if isinstance(item, dict) else str(item)
            cls = ex.AIMessage if role == "ai" else ex.HumanMessage
            mensagens.append(cls(content=content))
        total = len(mensagens)
        # "approximate" evita tokenização via transformers (o ChatOllama não tokeniza localmente)
        recortadas = ex.trim_messages(mensagens, max_tokens=max_tokens, strategy="last",
                                      token_counter="approximate", include_system=True)
        return {
            "tipo": "lista",
            "conteudo": [{"titulo": type(m).__name__, "texto": str(m.content)[:200]}
                         for m in recortadas],
            "extra": {"total_original": total, "mantidas": len(recortadas)},
        }
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        return {"tipo": "erro",
                "conteudo": f"Formato de mensagens inválido: {e}. Use um JSON como [{{\"role\": \"human\", \"content\": \"...\"}}]"}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro no trim_messages: {e}")


@app.post("/api/contar_palavras")
def contar_palavras(corpo: TextoBody):
    try:
        n = len(corpo.texto.split())
        return {"tipo": "texto", "conteudo": f"{n} palavras"}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro: {e}")


@app.post("/api/mcp_tools")
def mcp_tools():
    mcp_url = os.getenv("MCP_SERVER_URL", "")
    if not mcp_url:
        return {"tipo": "erro",
                "conteudo": ("MCP_SERVER_URL não definida no .env — pulando. "
                             "Exemplo: MCP_SERVER_URL=http://localhost:8000/sse")}
    try:
        import asyncio
        from langchain_mcp_adapters.client import MultiServerMCPClient

        async def _carregar():
            client = MultiServerMCPClient({"mcp": {"url": mcp_url}})
            return await client.get_tools()

        tools = asyncio.run(_carregar())
        return {"tipo": "lista",
                "conteudo": [{"titulo": t.name, "texto": getattr(t, "description", "") or ""}
                             for t in tools]}
    except ImportError as e:
        return {"tipo": "erro",
                "conteudo": f"Dependência ausente ({e}). Instale: pip install langchain-mcp-adapters"}
    except Exception as e:  # noqa: BLE001
        return {"tipo": "erro", "conteudo": f"Falha ao conectar ao MCP: {e}"}


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