"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 11 — Integradora: Agente + RAG + Gradio
Esqueleto para alunos — complete os TODOs abaixo.

Projeto local: o agente usa o RAG como UMA tool nativa (create_retriever_tool),
junto com busca na web e calculadora, tudo exposto numa interface Gradio.

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py   -> abre em http://localhost:7860
"""
import os

from dotenv import load_dotenv

import chromadb
import gradio as gr

from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain.tools.retriever import create_retriever_tool
from langchain_community.tools import DuckDuckGoSearchRun

# ─────────────────────────────────────────────────────────────
# Configuração via .env
# ─────────────────────────────────────────────────────────────
load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

if not OLLAMA_API_KEY:
    raise RuntimeError(
        "OLLAMA_API_KEY não encontrada. Copie .env.example para .env e preencha a chave."
    )

os.environ["OLLAMA_HOST"] = OLLAMA_HOST
os.environ["OLLAMA_API_KEY"] = OLLAMA_API_KEY

llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0)

# ─────────────────────────────────────────────────────────────
# 1. RAG como tool nativa (create_retriever_tool)
# ─────────────────────────────────────────────────────────────
embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_HOST)
client = chromadb.PersistentClient(path="./chroma_db")
vectorstore = Chroma(
    client=client,
    collection_name="aula11",
    embedding_function=embeddings,
)
vectorstore.add_documents([
    Document(page_content="A FIAP fica na Avenida Paulista, em São Paulo."),
    Document(page_content="O curso de Ciência da Computação tem 4 anos de duração."),
    Document(page_content="Prompt engineering é escrever instruções eficazes para LLMs."),
])

retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
buscar_documentos = create_retriever_tool(
    retriever,
    name="buscar_nos_documentos",
    description="Busca em documentos internos da FIAP. Use para perguntas sobre a instituição.",
)


@tool
def calcular(expressao: str) -> str:
    """Calcula uma expressão matemática simples."""
    # TODO: Implemente o cálculo da expressão usando eval()
    # Retorne "Resultado: {resultado}" ou "Erro: {erro}"
    pass


busca_web = DuckDuckGoSearchRun(name="busca_na_web",
                                description="Busca na web por informações atuais.")

tools = [buscar_documentos, calcular, busca_web]


def obter_prompt_react():
    # TODO: Tente baixar o prompt "hwchase17/react" do Hub
    # Em caso de falha, crie um PromptTemplate offline com o formato ReAct
    pass


# TODO: Crie o agente e o executor
# agent = create_react_agent(llm, tools, obter_prompt_react())
# executor = AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=6)


def responder(mensagem: str, history: list) -> list:
    """Callback Gradio: roda o agente e acumula o histórico."""
    history = history or []
    # TODO: invoque o executor com {"input": mensagem}
    # TODO: acumule (mensagem, resposta["output"]) no history
    # return history
    pass


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL} | embeddings: {EMBEDDING_MODEL}")
    print("Abrindo interface Gradio em http://localhost:7860 ...")

    demo = gr.ChatInterface(
        fn=responder,
        title="Agente FIAP — Aula 11 (RAG + Tools)",
        description="Pergunte sobre a FIAP (RAG), peça contas (calculadora) ou algo atual (web).",
        theme="soft",
    )
    demo.launch()


if __name__ == "__main__":
    main()
