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
import uuid
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
    mensagens: Annotated[list, add_messages]
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


def mapa_decisao() -> dict[str, str]:
    return {"responder": "responder", END: END}


def criar_grafo(checkpointer: MemorySaver | None = None):
    builder = StateGraph(Estado)
    builder.add_node("buscar", node_buscar)
    builder.add_node("responder", node_responder)
    builder.add_edge(START, "buscar")
    builder.add_conditional_edges("buscar", decidir_continuar, mapa_decisao())
    builder.add_edge("responder", END)
    return builder.compile(
        checkpointer=checkpointer or MemorySaver(),
        interrupt_before=["responder"],
    )


def configuracao_thread(thread_id: str | None = None, prefixo: str = "requisicao"):
    identificador = (thread_id or "").strip() or f"{prefixo}-{uuid.uuid4()}"
    return identificador, {"configurable": {"thread_id": identificador}}


def aguardando_revisao(estado) -> bool:
    return tuple(estado.next or ()) == ("responder",)


class AprovacaoInvalida(RuntimeError):
    pass


def resposta_revisao(estado, thread_id: str) -> dict:
    if not aguardando_revisao(estado):
        raise AprovacaoInvalida("O grafo não está pausado antes de 'responder'.")
    resultados = str(estado.values.get("resultados_busca") or "").strip()
    return {
        "tipo": "texto",
        "conteudo": (
            "Resultados da busca para revisão:\n\n"
            f"{resultados}\n\n"
            f"Grafo pausado em {list(estado.next)}. Aprovar para gerar a resposta."
        ),
        "extra": {
            "thread_id": thread_id,
            "proximo": list(estado.next),
            "resultados_busca": resultados,
        },
        "aprovacao_pendente": True,
        "aprovacao_titulo": "Revisar e aprovar resposta (HITL)",
    }


def retomar_grafo(grafo, config):
    estado = grafo.get_state(config)
    if not aguardando_revisao(estado):
        raise AprovacaoInvalida("Não há uma pausa HITL ativa para esta thread.")
    grafo.invoke(None, config=config)
    estado_final = grafo.get_state(config)
    if aguardando_revisao(estado_final):
        raise RuntimeError("O grafo permaneceu pausado após a retomada.")
    mensagens = estado_final.values.get("mensagens", [])
    if not mensagens:
        raise RuntimeError("O grafo concluiu sem produzir uma resposta.")
    return estado_final


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}\n")
    grafo = criar_grafo()
    print("== Grafo (mermaid) ==")
    print(grafo.get_graph().draw_mermaid())

    thread_id, config = configuracao_thread(prefixo="cli")
    pergunta = input("Pergunta: ").strip() or "Quais são as novidades de IA em 2026?"
    grafo.invoke({"mensagens": [HumanMessage(content=pergunta)]}, config=config)
    estado_atual = grafo.get_state(config)
    if not aguardando_revisao(estado_atual):
        print("A busca terminou sem resultados; não há aprovação pendente.")
        return

    print("\n== Resultados para revisão ==")
    print(estado_atual.values.get("resultados_busca", ""))
    print(f"\nPausado em {list(estado_atual.next)} (HITL).")
    aprovacao = input("Aprovar e continuar? [s/N]: ").strip().lower()
    if aprovacao not in {"s", "sim"}:
        print("Execução cancelada; a thread foi preservada sem aprovar a resposta.")
        return

    estado_final = retomar_grafo(grafo, config)
    print("\n== Resposta final ==")
    print(estado_final.values["mensagens"][-1].content)
    print(f"\nThread: {thread_id}")


if __name__ == "__main__":
    main()
