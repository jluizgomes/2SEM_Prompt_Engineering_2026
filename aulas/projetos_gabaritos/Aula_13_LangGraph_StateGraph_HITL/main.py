"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 13 — LangGraph: StateGraph e Human-in-the-Loop

Projeto local: construir um grafo de estado com LangGraph — um agente de
pesquisa com nós (buscar/responder), aresta condicional e checkpoint
(MemorySaver) que permite pausar e aprovar antes de uma ação (HITL).

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py
"""
import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

# ─────────────────────────────────────────────────────────────
# Configuração via .env
# ─────────────────────────────────────────────────────────────
load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")

if not OLLAMA_API_KEY:
    raise RuntimeError(
        "OLLAMA_API_KEY não encontrada. Copie .env.example para .env e preencha a chave."
    )

os.environ["OLLAMA_HOST"] = OLLAMA_HOST
os.environ["OLLAMA_API_KEY"] = OLLAMA_API_KEY

llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0)
busca_web = DuckDuckGoSearchRun(name="busca_na_web",
                                description="Busca na web por informações atuais.")


# ─────────────────────────────────────────────────────────────
# 1. Estado — o que circula entre os nós do grafo
# ─────────────────────────────────────────────────────────────
class Estado(TypedDict):
    mensagens: Annotated[list, add_messages]   # add_messages ACUMULA (não substitui)
    resultados_busca: str


# ─────────────────────────────────────────────────────────────
# 2. Nós — funções que transformam o estado
# ─────────────────────────────────────────────────────────────
def node_buscar(estado: Estado) -> dict:
    """Executa a busca na web e guarda o resultado no estado."""
    ultima = estado["mensagens"][-1].content
    resultados = busca_web.invoke(ultima)
    return {"resultados_busca": resultados}


def node_responder(estado: Estado) -> dict:
    """Gera a resposta final usando os resultados da busca."""
    resposta = llm.invoke(
        [HumanMessage(content="Resuma os resultados em português, em até 3 linhas:\n"
                              f"{estado['resultados_busca']}")]
    )
    return {"mensagens": [resposta]}


def decidir_continuar(estado: Estado) -> str:
    """Aresta condicional: segue para responder ou encerra."""
    if estado.get("resultados_busca"):
        return "responder"
    return END


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}\n")

    # ─────────────────────────────────────────────────────────
    # 3. Montar o grafo
    # ─────────────────────────────────────────────────────────
    builder = StateGraph(Estado)
    builder.add_node("buscar", node_buscar)
    builder.add_node("responder", node_responder)
    builder.add_edge(START, "buscar")
    builder.add_conditional_edges("buscar", decidir_continuar, {"responder": "responder"})
    builder.add_edge("responder", END)

    # HITL: pausa ANTES de "responder" para inspeção/aprovação humana
    checkpointer = MemorySaver()
    grafo = builder.compile(checkpointer=checkpointer, interrupt_before=["responder"])

    print("== Grafo (mermaid) ==")
    print(grafo.get_graph().draw_mermaid())

    config = {"configurable": {"thread_id": "pesquisa_demo"}}

    # Primeira execução: para antes de "responder" (HITL)
    grafo.invoke({"mensagens": [HumanMessage(content="Quais são as novidades de IA em 2026?")]},
                 config=config)
    estado_atual = grafo.get_state(config)
    print(f"\n== Pausado em: {estado_atual.next} (HITL) ==")
    print("O grafo aguarda aprovação humana antes de responder.")

    # Aprovação humana: retoma a execução a partir do ponto pausado
    print("\n== Aprovando e retomando ==")
    grafo.invoke(None, config=config)  # None = continua do checkpoint
    estado_final = grafo.get_state(config)
    ultima = estado_final.values["mensagens"][-1]
    print("\n== Resposta final ==")
    print(ultima.content)


if __name__ == "__main__":
    main()
