"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Esqueleto para alunos — complete os TODOs abaixo.
Aula 02 — Memória conversacional: Buffer, Summary e TokenBuffer

Projeto local: tornar a chain da Aula 01 stateful, escolhendo o tipo de
memória certo para o domínio, e entender o trade-off de custo de tokens.

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py
"""
import os

from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_classic.memory import (
    ConversationBufferMemory,
    ConversationSummaryMemory,
    ConversationTokenBufferMemory,
)
from langchain_classic.chains import ConversationChain
from langchain_core.prompts import PromptTemplate

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

llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0.7)


def demo_buffer() -> None:
    """ConversationBufferMemory: guarda TUDO — crescimento linear."""
    # TODO: Instancie ConversationBufferMemory com memory_key="history" e return_messages=True
    # TODO: Crie uma ConversationChain com llm e memória
    # TODO: Envie 2 mensagens e imprima o estado da memória
    pass


def demo_summary() -> None:
    """ConversationSummaryMemory: usa o próprio LLM para resumir."""
    # TODO: Instancie ConversationSummaryMemory passando llm
    # TODO: Crie ConversationChain e envie 3 mensagens
    # TODO: Imprima o resumo acumulado
    pass


def demo_token_buffer() -> None:
    """ConversationTokenBufferMemory: limite explícito de tokens (janela deslizante)."""
    # TODO: Instancie ConversationTokenBufferMemory com max_token_limit=500
    # TODO: Crie ConversationChain e envie 2 mensagens
    # TODO: Imprima quantas mensagens ficaram no buffer
    pass


def demo_prompt_customizado() -> None:
    """ConversationChain com system prompt customizado do domínio do grupo."""
    # TODO: Crie um PromptTemplate com template de culinária brasileira
    # TODO: Crie ConversationChain com prompt customizado e ConversationTokenBufferMemory
    # TODO: Envie uma pergunta e imprima a resposta
    pass


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}")
    # TODO: Chamar demo_buffer()
    # TODO: Chamar demo_summary()
    # TODO: Chamar demo_token_buffer()
    # TODO: Chamar demo_prompt_customizado()


if __name__ == "__main__":
    main()
