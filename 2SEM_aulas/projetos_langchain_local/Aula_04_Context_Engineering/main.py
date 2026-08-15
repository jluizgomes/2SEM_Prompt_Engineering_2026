"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 04 — Context Engineering

Projeto local: medir e controlar o que entra no contexto do modelo —
contagem de tokens (tiktoken), janela de contexto e montagem de prompt
com instrução de sistema + histórico + pergunta.

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py
"""
import os

from dotenv import load_dotenv

import tiktoken

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

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

llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0.3)


# ─────────────────────────────────────────────────────────────
# 1. Contagem de tokens — o custo invisível do contexto
# ─────────────────────────────────────────────────────────────
def contar_tokens(texto: str, modelo: str = "gpt-4o") -> int:
    """Conta tokens com tiktoken (aproximação válida para estimar custo)."""
    try:
        enc = tiktoken.encoding_for_model(modelo)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(texto))


# ─────────────────────────────────────────────────────────────
# 2. Engenharia de contexto: instrução de sistema + histórico + pergunta
# ─────────────────────────────────────────────────────────────
SISTEMA = (
    "Você é um assistente de suporte técnico da FIAP. "
    "Responda de forma objetiva e em português do Brasil. "
    "Se não souber a resposta, diga que não sabe — nunca invente."
)

prompt = ChatPromptTemplate.from_messages([
    ("system", SISTEMA),
    ("human", "{pergunta}"),
])

chain = prompt | llm | StrOutputParser()


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}\n")

    # Demonstração de contagem de tokens
    exemplos = [
        "Olá!",
        "Explique o que é context window em um LLM e por que ele importa.",
        (SISTEMA + " " + "Explique o que é context window em um LLM."),
    ]
    print("== Custo de tokens por entrada ==")
    for ex in exemplos:
        print(f"  {contar_tokens(ex):>5} tokens | {ex[:60]}...")

    # Demonstração da chain com a instrução de sistema
    print("\n== Resposta com instrução de sistema ==")
    resposta = chain.invoke({"pergunta": "O que significa 'janela de contexto'?"})
    print(resposta)


if __name__ == "__main__":
    main()
