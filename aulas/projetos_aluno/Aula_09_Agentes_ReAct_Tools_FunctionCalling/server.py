"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 09 — Agentes ReAct, Tools e Function Calling
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8009     (ou: ./run_web.sh)

Este server tenta usar os objetos/ferramentas declarados no main.py. Se o
main.py não puder ser importado (ex.: versão do LangChain sem langchain.hub),
a interface usa um fallback moderno com langgraph-prebuilt — assim o chat de
demonstração funciona em qualquer ambiente instalado.
"""
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import importlib.util
import inspect
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

app = FastAPI(
    title="Aula 09 — Agentes ReAct, Tools e Function Calling",
    description="Interface web do exercício de agente ReAct com tools.",
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
# Agente: usa o main.py quando possível; senão fallback moderno
# ─────────────────────────────────────────────────────────────
_TEMPLATE_FALLBACK = (
    "Answer the following questions as best you can. You have access "
    "to the following tools:\n\n{tools}\n\n"
    "Use the following format:\n\n"
    "Question: the input question you must answer\n"
    "Thought: you should always think about what to do\n"
    "Action: the action to take, should be one of [{tool_names}]\n"
    "Action Input: the input to the action\n"
    "Observation: the result of the action\n"
    "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
    "Thought: I now know the final answer\n"
    "Final Answer: the final answer to the original input question\n\n"
    "Begin!\n\n"
    "Question: {input}\n"
    "Thought:{agent_scratchpad}"
)


def _tool_calcular():
    from langchain_core.tools import tool

    @tool
    def calcular(expressao: str) -> str:  # noqa: D103
        """Calcula uma expressão matemática simples. Ex.: '13 * 17'."""
        try:
            return f"Resultado: {eval(expressao, {'__builtins__': {}}, {})}"  # noqa: S307
        except Exception as e:  # noqa: BLE001
            return f"Erro ao calcular: {e}"

    return calcular


def _montar_agente(ex):
    """Retorna (motor, info) — motor pode ser um AgentExecutor (clássico)
    ou um grafo langgraph-prebuilt (fallback moderno)."""
    if ex is not None:
        try:
            from langchain.agents import AgentExecutor, create_react_agent
            from langchain_core.prompts import PromptTemplate

            tools = list(getattr(ex, "tools", []))
            prompt_fn = getattr(ex, "obter_prompt_react", None)
            prompt = (prompt_fn() if prompt_fn is not None and not _eh_stub(prompt_fn)
                      else PromptTemplate.from_template(_TEMPLATE_FALLBACK))
            agent = create_react_agent(ex.llm, tools, prompt)
            executor = AgentExecutor(agent=agent, tools=tools, verbose=False,
                                     max_iterations=5, return_intermediate_steps=True)
            return {"executor": executor}
        except Exception:  # noqa: BLE001 — tenta o fallback moderno
            pass

    from langchain_core.prompts import PromptTemplate
    from langchain_ollama import ChatOllama
    from langchain_community.tools import DuckDuckGoSearchRun
    from langgraph.prebuilt import create_react_agent

    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "gpt-oss:120b"),
        base_url=os.getenv("OLLAMA_HOST", "https://ollama.com"),
        temperature=0,
    )
    tools = [
        _tool_calcular(),
        DuckDuckGoSearchRun(name="busca_na_web", description="Busca na web por informações atuais."),
    ]
    sistema = "Você é um agente ReAct. Responda em português do Brasil. Use as tools " \
              "quando precisar. Para contas, use a tool calcular. Para informações atuais, " \
              "use a busca na web."
    grafo = create_react_agent(llm, tools, prompt=sistema) if tools else None
    return {"grafo": grafo, "llm": llm}


# ─────────────────────────────────────────────────────────────
# Modelos de requisição
# ─────────────────────────────────────────────────────────────
class PerguntaBody(BaseModel):
    mensagem: str


# ─────────────────────────────────────────────────────────────
# Endpoints da API
# ─────────────────────────────────────────────────────────────
@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        pendentes = [f"main.py não pôde ser importado: {_ERRO_CARGA}"]
    else:
        pendentes = _pendentes(ex, {
            "calcular": "calcular() (tool)",
            "obter_prompt_react": "obter_prompt_react()",
            "main": "main()",
        })
    return {
        "nome": "Aula 09 — Agentes ReAct, Tools e Function Calling",
        "modulo": "Módulo 3 · Interfaces / Agentes",
        "descricao": (
            "Agente ReAct que decide qual tool usar a cada passo (calculadora e busca "
            "na web) executando o loop Thought → Action → Observation. Se o main.py "
            "não carregar no ambiente instalado, a interface usa um fallback moderno "
            "(langgraph-prebuilt)."
        ),
        "modo": "chat",
        "chat_endpoint": "/api/perguntar",
        "implementado": not pendentes,
        "pendentes": pendentes,
        "parametros": [],
        "acoes": [],
    }


@app.post("/api/perguntar")
def perguntar(corpo: PerguntaBody):
    try:
        ex = _get_exercicio_lenient()
    except Exception:  # noqa: BLE001
        ex = None
    motor = _montar_agente(ex)

    if "executor" in motor:
        r = motor["executor"].invoke({"input": corpo.mensagem})
        passos = []
        for acao, observacao in r.get("intermediate_steps", []):
            passos.append(
                f"🧠 Thought → 🔧 {acao.tool}({acao.tool_input}) → 👀 {str(observacao)[:250]}"
            )
        return {"tipo": "texto", "conteudo": str(r["output"]), "extra": {"passos": passos}}

    # fallback moderno: grafo langgraph-prebuilt
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    grafo = motor["grafo"]
    resultado = grafo.invoke({"messages": [HumanMessage(content=corpo.mensagem)]})
    passos = []
    texto_final = "(sem resposta)"
    for m in resultado["messages"]:
        if isinstance(m, ToolMessage):
            passos.append(f"🔧 {getattr(m, 'name', 'tool')}({getattr(m, 'tool_call_id', '')}): {str(m.content)[:200]}")
        elif isinstance(m, AIMessage):
            conteudo = str(m.content)
            if not getattr(m, "tool_calls", None):
                texto_final = conteudo
            passos.append(f"🟣 {type(m).__name__}: {conteudo[:250]}")
    return {"tipo": "texto", "conteudo": texto_final, "extra": {"passos": passos}}


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