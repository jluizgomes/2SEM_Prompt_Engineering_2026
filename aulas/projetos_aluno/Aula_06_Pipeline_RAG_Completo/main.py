"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Esqueleto para alunos — complete os TODOs abaixo.
Aula 06 — Pipeline RAG Completo

Projeto local: pipeline RAG de ponta a ponta — carregar um PDF, dividir
em chunks, indexar no ChromaDB e responder perguntas citando o contexto.

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. (opcional) coloque um PDF em ./data/
    4. python main.py

Sem PDF em ./data/, o projeto usa um texto de exemplo embutido — assim o
pipeline roda do mesmo jeito para demonstração.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

import chromadb
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
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

DATA_DIR = Path("./data")


# ─────────────────────────────────────────────────────────────
# 1. Carregar documentos (PDF em ./data/ ou texto de exemplo)
# ─────────────────────────────────────────────────────────────
def carregar_documentos() -> list[Document]:
    # TODO: Verifique se há PDFs em ./data/
    # TODO: Se houver, carregue com PyMuPDFLoader e retorne
    # TODO: Se não houver, retorne documentos de exemplo embutidos
    pass


# ─────────────────────────────────────────────────────────────
# 2. Dividir em chunks (chunk_size e overlap ajustáveis)
# ─────────────────────────────────────────────────────────────
def dividir(docs: list[Document]) -> list[Document]:
    # TODO: Instancie RecursiveCharacterTextSplitter (chunk_size=500, overlap=100)
    # TODO: Divida os documentos e retorne os chunks
    pass


# ─────────────────────────────────────────────────────────────
# 3. Indexar no ChromaDB
# ─────────────────────────────────────────────────────────────
def indexar(chunks: list[Document]) -> Chroma:
    # TODO: Crie embeddings com OllamaEmbeddings
    # TODO: Crie.PersistentClient e Chroma vectorstore
    # TODO: Adicione os chunks ao vectorstore
    pass


# ─────────────────────────────────────────────────────────────
# 4. Montar a chain RAG com LCEL (retriever + prompt + modelo)
# ─────────────────────────────────────────────────────────────
def montar_chain(vectorstore: Chroma):
    # TODO: Crie um retriever do vectorstore (k=3)
    # TODO: Crie prompt com system message pedindo resposta baseada no contexto
    # TODO: Monte a chain: {"contexto": retriever, "pergunta": RunnablePassthrough()} | prompt | llm | StrOutputParser()
    pass


def main() -> None:
    print(f"Ollama Cloud | chat: {OLLAMA_MODEL} | embeddings: {EMBEDDING_MODEL}\n")
    # TODO: Chamar carregar_documentos()
    # TODO: Chamar dividir()
    # TODO: Chamar indexar()
    # TODO: Chamar montar_chain()
    # TODO: Fazer 3 perguntas e imprimir respostas
    pass


if __name__ == "__main__":
    main()
