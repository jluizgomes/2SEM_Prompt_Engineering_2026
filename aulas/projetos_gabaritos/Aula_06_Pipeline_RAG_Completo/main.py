"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
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
    pdfs = sorted(DATA_DIR.glob("*.pdf")) if DATA_DIR.exists() else []
    if pdfs:
        docs = []
        for pdf in pdfs:
            docs.extend(PyMuPDFLoader(str(pdf)).load())
        print(f"{len(docs)} páginas carregadas de {len(pdfs)} PDF(s).")
        return docs
    print("Nenhum PDF em ./data/ — usando texto de exemplo embutido.")
    return [
        Document(page_content="A FIAP é uma instituição de ensino superior "
                              "localizada na Avenida Paulista, em São Paulo."),
        Document(page_content="O curso de Ciência da Computação forma "
                              "profissionais para atuar com tecnologia e inovação."),
        Document(page_content="Prompt engineering é escrever instruções claras "
                              "para modelos de linguagem."),
        Document(page_content="RAG significa Retrieval-Augmented Generation: "
                              "buscar contexto e gerar resposta com base nele."),
    ]


# ─────────────────────────────────────────────────────────────
# 2. Dividir em chunks (chunk_size e overlap ajustáveis)
# ─────────────────────────────────────────────────────────────
def dividir(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_documents(docs)
    print(f"{len(chunks)} chunks criados.")
    return chunks


# ─────────────────────────────────────────────────────────────
# 3. Indexar no ChromaDB
# ─────────────────────────────────────────────────────────────
def indexar(chunks: list[Document]) -> Chroma:
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_HOST)
    client = chromadb.PersistentClient(path="./chroma_db")
    vectorstore = Chroma(
        client=client,
        collection_name="aula06",
        embedding_function=embeddings,
    )
    vectorstore.add_documents(chunks)
    return vectorstore


# ─────────────────────────────────────────────────────────────
# 4. Montar a chain RAG com LCEL (retriever + prompt + modelo)
# ─────────────────────────────────────────────────────────────
def montar_chain(vectorstore: Chroma):
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Responda a pergunta APENAS com base no contexto abaixo. "
                   "Se não houver informação, diga que não sabe.\n\n"
                   "Contexto:\n{contexto}"),
        ("human", "Pergunta: {pergunta}"),
    ])

    llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0.2)

    chain = (
        {"contexto": retriever, "pergunta": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


def main() -> None:
    print(f"Ollama Cloud | chat: {OLLAMA_MODEL} | embeddings: {EMBEDDING_MODEL}\n")
    docs = carregar_documentos()
    chunks = dividir(docs)
    vectorstore = indexar(chunks)
    chain = montar_chain(vectorstore)

    print("\n== Perguntas ao pipeline RAG ==")
    for pergunta in [
        "Onde fica a FIAP?",
        "O que significa RAG?",
        "Qual é a capital da Austrália?",  # fora do contexto -> deve dizer que não sabe
    ]:
        resposta = chain.invoke(pergunta)
        print(f"\nP: {pergunta}\nR: {resposta}")


if __name__ == "__main__":
    main()
