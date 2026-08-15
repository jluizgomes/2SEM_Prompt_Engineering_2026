"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Esqueleto para alunos — complete os TODOs abaixo.
Aula 08 — Interfaces: Gradio e Streamlit

Projeto local: expor uma chain RAG (com memória por sessão) através de
duas interfaces — Gradio (main.py) e Streamlit (app_streamlit.py).

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. Gradio:    python main.py          -> abre em http://localhost:7860
    4. Streamlit: streamlit run app_streamlit.py
"""
import os

from dotenv import load_dotenv

import gradio as gr

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

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

llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0.5)

# ─────────────────────────────────────────────────────────────
# Chain base com memória por sessão
# ─────────────────────────────────────────────────────────────
prompt = ChatPromptTemplate.from_messages([
    ("system", "Você é um assistente prestativo. Responda em português do Brasil."),
    ("human", "{pergunta}"),
])

chain_base = prompt | llm | StrOutputParser()

# Históricos por session_id (multi-usuário)
_store: dict[str, ChatMessageHistory] = {}


def _get_history(session_id: str) -> ChatMessageHistory:
    if session_id not in _store:
        _store[session_id] = ChatMessageHistory()
    return _store[session_id]


chain_com_memoria = RunnableWithMessageHistory(
    chain_base,
    _get_history,
    input_messages_key="pergunta",
)


def responder(mensagem: str, history: list) -> list:
    """Callback da interface Gradio: acumula o histórico e devolve a resposta."""
    # TODO: Invoke chain_com_memoria com a mensagem e session_id
    # TODO: Acumule (mensagem, resposta) no history e retorne
    pass


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}")
    # TODO: Crie gr.ChatInterface com fn=responder, título e descrição
    # TODO: Lançe a interface com demo.launch()
    pass


if __name__ == "__main__":
    main()
