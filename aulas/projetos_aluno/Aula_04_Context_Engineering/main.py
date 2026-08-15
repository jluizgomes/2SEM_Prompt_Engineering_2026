"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Esqueleto para alunos — complete os TODOs abaixo.
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
    # TODO: Use tiktoken.encoding_for_model() com fallback para cl100k_base
    # TODO: Retorne o tamanho do texto codificado
    pass


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

    # TODO: Crie uma lista de exemplos de textos
    # TODO: Para cada exemplo, imprima contagem de tokens e texto (truncado)
    # TODO: Invoke a chain com uma pergunta sobre "janela de contexto" e imprima
    pass


if __name__ == "__main__":
    main()
