"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Bônus — Multi-Chains e Multi-Modelos

Projeto local: executar várias chains em PARALELO (RunnableParallel) e
combinar respostas de mais de um modelo sobre a mesma pergunta.

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py
"""
import os

from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel

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

# ─────────────────────────────────────────────────────────────
# 1. Chains especializadas (personas diferentes)
# ─────────────────────────────────────────────────────────────
def chain_persona(persona: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"Você é {persona}. Responda em até 2 frases."),
        ("human", "{pergunta}"),
    ])
    return prompt | ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST,
                               temperature=0.5) | StrOutputParser()


mapa_personas = {
    "resumo": chain_persona("um resumidor técnico objetivo"),
    "pratica": chain_persona("um professor que dá exemplos práticos"),
    "critica": chain_persona("um revisor crítico que aponta limitações"),
}


def demo_parallel() -> None:
    print("\n== RunnableParallel (3 chains ao mesmo tempo) ==")
    cadeia_paralela = RunnableParallel(mapa_personas)
    resultados = cadeia_paralela.invoke({"pergunta": "O que é RAG?"})
    for chave, texto in resultados.items():
        print(f"\n[{chave}]\n  {texto}")


def demo_multi_modelos() -> None:
    print("\n== Multi-modelos (mesma pergunta, modelos diferentes) ==")
    # Troque/adicione modelos disponíveis na sua conta Ollama.
    modelos = [OLLAMA_MODEL, "gpt-oss:20b"]
    prompt = ChatPromptTemplate.from_messages([
        ("human", "Defina 'embedding' em uma frase."),
    ])
    for modelo in modelos:
        try:
            llm = ChatOllama(model=modelo, base_url=OLLAMA_HOST, temperature=0)
            resp = (prompt | llm | StrOutputParser()).invoke({})
            print(f"  [{modelo}] {resp}")
        except Exception as e:  # noqa: BLE001
            print(f"  [{modelo}] indisponível: {e}")


def main() -> None:
    print(f"Ollama Cloud | modelo padrão: {OLLAMA_MODEL}")
    demo_parallel()
    demo_multi_modelos()


if __name__ == "__main__":
    main()
