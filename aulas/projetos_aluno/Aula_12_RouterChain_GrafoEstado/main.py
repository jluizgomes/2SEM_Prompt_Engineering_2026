"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 12 — Router Chain e Grafo de Estado
Esqueleto para alunos — complete os TODOs abaixo.

Projeto local: rotear uma pergunta para a chain correta conforme a
intenção (com Pydantic + RunnableLambda) e introduzir o conceito de
grafo de estado que será aprofundado no LangGraph (Aula 13).

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py
"""
import os

from dotenv import load_dotenv

from pydantic import BaseModel, Field

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_core.documents import Document

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
# 1. Classificação da intenção com Pydantic (structured output)
# ─────────────────────────────────────────────────────────────
class Intencao(BaseModel):
    """Classifica a intenção da pergunta do usuário."""
    categoria: str = Field(description="Uma de: 'documentos', 'calculo' ou 'geral'")


classificador_prompt = ChatPromptTemplate.from_messages([
    ("system", "Classifique a pergunta do usuário. Responda SOMENTE em JSON "
               "com a chave 'categoria', cujo valor é 'documentos', 'calculo' ou 'geral'."),
    ("human", "{pergunta}"),
])
# TODO: Monte o classificador usando o pipe: classificador_prompt | llm.with_structured_output(Intencao)
# classificador = ...


# ─────────────────────────────────────────────────────────────
# 2. Chains especializadas por categoria
# ─────────────────────────────────────────────────────────────
embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_HOST)
vectorstore = Chroma(
    collection_name="aula12",
    embedding_function=embeddings,
)
vectorstore.add_documents([
    Document(page_content="A FIAP fica na Avenida Paulista, em São Paulo."),
    Document(page_content="O vestibular da FIAP acontece duas vezes por ano."),
])

# TODO: Monte a chain_documentos com retriever, ChatPromptTemplate, llm e StrOutputParser
# O system prompt deve usar {contexto} para o contexto recuperado
chain_documentos = None  # substitua pelo pipe completo

# TODO: Monte a chain_calculo (prompt de calculadora | llm | StrOutputParser)
chain_calculo = None  # substitua pelo pipe completo

# TODO: Monte a chain_geral (prompt genérico | llm | StrOutputParser)
chain_geral = None  # substitua pelo pipe completo


# ─────────────────────────────────────────────────────────────
# 3. Roteador — decide qual chain chamar (RunnableLambda)
# ─────────────────────────────────────────────────────────────
def rotear(entrada: dict) -> str:
    # TODO: invoque o classificador para obter a intenção
    # TODO: com base na categoria, invoque a chain correspondente
    # (chain_documentos, chain_calculo ou chain_geral)
    pass


router = RunnableLambda(rotear)


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}\n")
    for pergunta in [
        "Onde fica a FIAP?",
        "Quanto é 12 vezes 8?",
        "Me dê uma dica para estudar melhor.",
    ]:
        print(f"P: {pergunta}")
        # TODO: print(f"R: {router.invoke({'pergunta': pergunta})}\n")
        pass


if __name__ == "__main__":
    main()
