"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 10 — Context Engineering e Agentes MCP
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8110
"""
import importlib.util
import json
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
    title="Aula 10 — Context Engineering e Agentes MCP",
    description="Interface web do exercício de trim_messages e MCP.",
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
_DEFAULT_MENSAGENS = [
    {"role": "system", "content": "Você é um assistente didático."},
    {"role": "human", "content": "Olá!"},
    {"role": "ai", "content": "Oi! Como posso ajudar?"},
    {"role": "human", "content": "Me fale sobre LangChain."},
    {"role": "ai", "content": "LangChain é um framework para aplicações com LLMs."},
    {"role": "human", "content": "E sobre memória?"},
]


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


class TrimBody(BaseModel):
    mensagens: object = Field(default_factory=lambda: list(_DEFAULT_MENSAGENS))
    max_tokens: str = "40"


class TextoBody(BaseModel):
    texto: str = Field(min_length=1, max_length=10000)


@app.get("/api/info")
def info():
    return {
        "nome": "Aula 10 — Context Engineering e Agentes MCP",
        "modulo": "Módulo 3 · Interfaces / Agentes",
        "descricao": (
            "Controle o tamanho do contexto com trim_messages preservando os roles "
            "system, human, ai e tool, e conecte tools via MCP quando configurado."
        ),
        "modo": "acoes",
        "implementado": True,
        "pendentes": [],
        "parametros": [],
        "acoes": [
            {
                "endpoint": "/api/trim_messages",
                "titulo": "trim_messages",
                "descricao": "Recorta uma lista de mensagens pela janela de tokens.",
                "metodo": "POST",
                "params": [
                    {
                        "nome": "mensagens",
                        "label": "Mensagens (JSON)",
                        "tipo": "textarea",
                        "linhas": 8,
                        "padrao": json.dumps(_DEFAULT_MENSAGENS, ensure_ascii=False, indent=2),
                    },
                    {"nome": "max_tokens", "label": "max_tokens", "tipo": "texto", "padrao": "40"},
                ],
            },
            {
                "endpoint": "/api/contar_palavras",
                "titulo": "Contar palavras (tool)",
                "descricao": "Tool local simples do exercício.",
                "metodo": "POST",
                "params": [
                    {
                        "nome": "texto",
                        "label": "Texto",
                        "tipo": "texto",
                        "padrao": "LangChain e MCP em uma frase",
                    }
                ],
            },
            {
                "endpoint": "/api/mcp_tools",
                "titulo": "Carregar tools MCP",
                "descricao": "Usa o transporte e as variáveis MCP configurados no ambiente.",
                "metodo": "POST",
                "params": [],
            },
        ],
    }


@app.post("/api/trim_messages")
def trim_messages(corpo: TrimBody):
    exercicio = _get_exercicio()
    try:
        max_tokens = int(corpo.max_tokens or "40")
        dados = corpo.mensagens
        if isinstance(dados, str):
            dados = json.loads(dados)
        if not isinstance(dados, list) or not dados:
            dados = list(_DEFAULT_MENSAGENS)
        mensagens = exercicio.mensagens_de_entrada(dados)
        recortadas = exercicio.recortar_mensagens(mensagens, max_tokens=max_tokens)
        return {
            "tipo": "lista",
            "conteudo": [
                {"titulo": type(mensagem).__name__, "texto": str(mensagem.content)[:200]}
                for mensagem in recortadas
            ],
            "extra": {"total_original": len(mensagens), "mantidas": len(recortadas)},
        }
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "tipo": "erro",
            "conteudo": (
                f"Formato de mensagens inválido: {exc}. Use roles system, human, ai e tool; "
                "mensagens tool exigem tool_call_id."
            ),
        }
    except Exception as exc:
        raise HTTPException(500, f"Erro no trim_messages: {exc}")


@app.post("/api/contar_palavras")
def contar_palavras(corpo: TextoBody):
    try:
        return {"tipo": "texto", "conteudo": _get_exercicio().contar_palavras.invoke(corpo.texto)}
    except Exception as exc:
        raise HTTPException(500, f"Erro ao contar palavras: {exc}")


@app.post("/api/mcp_tools")
def mcp_tools():
    exercicio = _get_exercicio()
    saida = []
    ferramentas = exercicio.demo_mcp_tools(environ=None, output=saida.append)
    if ferramentas:
        return {
            "tipo": "lista",
            "conteudo": [
                {"titulo": ferramenta.name, "texto": getattr(ferramenta, "description", "") or ""}
                for ferramenta in ferramentas
            ],
        }
    return {"tipo": "texto", "conteudo": "\n".join(saida)}


if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
else:
    @app.get("/")
    def sem_frontend():
        return {
            "tipo": "erro",
            "conteudo": "Frontend não compilado. Rode: cd frontend && npm install && npm run build",
        }
