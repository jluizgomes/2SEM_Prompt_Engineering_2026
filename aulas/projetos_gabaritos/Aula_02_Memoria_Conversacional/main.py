"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
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
    print("\n== ConversationBufferMemory ==")
    memoria = ConversationBufferMemory(memory_key="history", return_messages=True)
    chat = ConversationChain(llm=llm, memory=memoria, verbose=False)
    print(chat.predict(input="Meu nome é Ana."))
    print(chat.predict(input="Qual é o meu nome?"))
    print("estado:", memoria.load_memory_variables({}))


def demo_summary() -> None:
    """ConversationSummaryMemory: usa o próprio LLM para resumir."""
    print("\n== ConversationSummaryMemory ==")
    memoria = ConversationSummaryMemory(llm=llm, memory_key="history",
                                        return_messages=True)
    chat = ConversationChain(llm=llm, memory=memoria, verbose=False)
    chat.predict(input="Meu nome é Ana e tenho 28 anos.")
    chat.predict(input="Trabalho como engenheira de dados.")
    chat.predict(input="Estou aprendendo LangChain.")
    print("resumo acumulado:", memoria.load_memory_variables({}))


def demo_token_buffer() -> None:
    """ConversationTokenBufferMemory: limite explícito de tokens (janela deslizante)."""
    print("\n== ConversationTokenBufferMemory (max_token_limit=500) ==")
    memoria = ConversationTokenBufferMemory(
        llm=llm, max_token_limit=500, memory_key="history", return_messages=True,
    )
    chat = ConversationChain(llm=llm, memory=memoria, verbose=False)
    chat.predict(input="Primeiro turno de exemplo.")
    chat.predict(input="Segundo turno de exemplo.")
    historico = memoria.load_memory_variables({})
    print("mensagens no buffer:", len(historico.get("history", [])))


def demo_prompt_customizado() -> None:
    """ConversationChain com system prompt customizado do domínio do grupo."""
    print("\n== ConversationChain com prompt customizado ==")
    template = """Você é um assistente especialista em culinária brasileira.
Seja simpático e dê dicas práticas. Sempre que der uma receita,
liste os ingredientes de forma clara.

Histórico da conversa:
{history}

Usuário: {input}
Assistente:"""
    prompt = PromptTemplate(input_variables=["history", "input"], template=template)
    chat = ConversationChain(
        llm=llm,
        memory=ConversationTokenBufferMemory(llm=llm, max_token_limit=800),
        prompt=prompt,
        verbose=False,
    )
    print(chat.predict(input="Como faço um feijão tropeiro?"))


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}")
    demo_buffer()
    demo_summary()
    demo_token_buffer()
    demo_prompt_customizado()


if __name__ == "__main__":
    main()
