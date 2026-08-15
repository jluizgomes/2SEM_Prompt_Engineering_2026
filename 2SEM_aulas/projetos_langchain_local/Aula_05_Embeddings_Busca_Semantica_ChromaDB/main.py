"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 05 — Embeddings e Busca Semântica com ChromaDB

Projeto local: transformar texto em vetores (embeddings), indexar no
ChromaDB e fazer busca por similaridade semântica (não por palavra-chave).

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py

O banco vetorial fica em ./chroma_db (PersistentClient). Para usar o
ChromaDB do Docker (FIAP AI Lab), troque para HttpClient (veja comentário).
"""
import os

from dotenv import load_dotenv

import chromadb
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
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

# ─────────────────────────────────────────────────────────────
# Embeddings — modelo dedicado (não é o de chat)
# ─────────────────────────────────────────────────────────────
embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_HOST)

# ─────────────────────────────────────────────────────────────
# Vector store — ChromaDB local (persistente em disco)
# Para usar o container do FIAP AI Lab:
#   client = chromadb.HttpClient(host="localhost", port=8000)
# ─────────────────────────────────────────────────────────────
client = chromadb.PersistentClient(path="./chroma_db")
vectorstore = Chroma(
    client=client,
    collection_name="aula05",
    embedding_function=embeddings,
)

# ─────────────────────────────────────────────────────────────
# Documentos de exemplo (troque pelo domínio do grupo)
# ─────────────────────────────────────────────────────────────
DOCUMENTOS = [
    Document(page_content="A FIAP fica na Avenida Paulista, em São Paulo."),
    Document(page_content="O curso de Ciência da Computação tem 4 anos de duração."),
    Document(page_content="Prompt engineering é a prática de escrever instruções eficazes para LLMs."),
    Document(page_content="RAG combina busca em documentos com geração de texto por LLM."),
    Document(page_content="O Brasil é o maior produtor de café do mundo."),
]


def indexar() -> None:
    """Indexa os documentos (gera embeddings e grava no ChromaDB)."""
    vectorstore.add_documents(DOCUMENTOS)
    print(f"{len(DOCUMENTOS)} documentos indexados.")


def buscar(consulta: str, k: int = 2) -> None:
    """Busca semântica: retorna os documentos mais próximos em significado."""
    print(f"\n== Busca: \"{consulta}\" ==")
    resultados = vectorstore.similarity_search(consulta, k=k)
    for i, doc in enumerate(resultados, 1):
        print(f"  {i}. {doc.page_content}")


def main() -> None:
    print(f"Ollama Cloud | chat: {OLLAMA_MODEL} | embeddings: {EMBEDDING_MODEL}\n")
    indexar()
    # Repare: nenhuma palavra-chave exata aparece nas buscas abaixo.
    buscar("onde fica a faculdade?")
    buscar("como fazer o computador me entender melhor?")
    buscar("quanto tempo dura a graduação?")


if __name__ == "__main__":
    main()
