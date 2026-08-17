"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 07 — RAG Avançado: Chunking Semântico e Reranking (RAGAS)

Projeto local: melhorar a qualidade do RAG com chunking semântico
(SemanticChunker), recuperação em dois níveis (ParentDocumentRetriever)
e reranking com cross-encoder. Inclui avaliação opcional com RAGAS.

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py

Atenção: RAGAS é opcional e sensível à versão instalada — a avaliação
está protegida por try/except e imprime orientação se algo faltar.
"""
import os

from dotenv import load_dotenv

import chromadb
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryStore
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

embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_HOST)

DOCUMENTOS = [
    Document(page_content="LangChain é um framework para construir aplicações "
                          "com LLMs, com módulos de chains, memória e retrieval."),
    Document(page_content="LangGraph estende o LangChain para orquestrar "
                          "grafos de estado e fluxos agênticos com checkpoints."),
    Document(page_content="RAG combina recuperação de documentos com geração "
                          "para reduzir alucinações e citar fontes."),
    Document(page_content="Chunking divide textos longos em pedaços menores "
                          "para caber na janela de contexto e melhorar a busca."),
    Document(page_content="Um cross-encoder reordena os documentos recuperados "
                          "para colocar os mais relevantes no topo."),
]


# ─────────────────────────────────────────────────────────────
# 1. Chunking semântico — divide por significado, não por tamanho fixo
# ─────────────────────────────────────────────────────────────
def demo_semantic_chunker() -> None:
    print("\n== SemanticChunker (divisão por similaridade) ==")
    texto_longo = (
        "Aprendizado de máquina é um subcampo da inteligência artificial. "
        "Modelos de linguagem são treinados em grandes volumes de texto. "
        "Prompt engineering é a arte de escrever boas instruções. "
        "RAG adiciona contexto externo para melhorar as respostas."
    )
    chunker = SemanticChunker(embeddings)
    chunks = chunker.split_text(texto_longo)
    for i, c in enumerate(chunks, 1):
        print(f"  chunk {i}: {c.strip()[:70]}...")


# ─────────────────────────────────────────────────────────────
# 2. ParentDocumentRetriever — recupera o bloco-pai (mais contexto)
# ─────────────────────────────────────────────────────────────
def demo_parent_retriever() -> None:
    print("\n== ParentDocumentRetriever (chunks pequenos -> blocos-pai) ==")
    splitter_pai = RecursiveCharacterTextSplitter(chunk_size=1000)
    splitter_filho = RecursiveCharacterTextSplitter(chunk_size=200)

    client = chromadb.PersistentClient(path="./chroma_db")
    vectorstore = Chroma(
        client=client,
        collection_name="aula07_parent",
        embedding_function=embeddings,
    )

    retriever = ParentDocumentRetriever(
        vectorstore=vectorstore,
        docstore=InMemoryStore(),
        child_splitter=splitter_filho,
        parent_splitter=splitter_pai,
    )
    retriever.add_documents(DOCUMENTOS)

    resultados = retriever.invoke("como evitar alucinações?")
    for i, doc in enumerate(resultados, 1):
        print(f"  {i}. {doc.page_content[:80]}...")


# ─────────────────────────────────────────────────────────────
# 3. Reranking com cross-encoder (opcional — requer sentence-transformers)
# ─────────────────────────────────────────────────────────────
def demo_reranker() -> None:
    print("\n== CrossEncoderReranker (reordena por relevância) ==")
    try:
        from langchain_community.cross_encoders import HuggingFaceCrossEncoder
        from langchain.retrievers.document_compressors import CrossEncoderReranker
        from langchain.retrievers import ContextualCompressionRetriever

        client = chromadb.PersistentClient(path="./chroma_db")
        vectorstore = Chroma(
            client=client,
            collection_name="aula07_rerank",
            embedding_function=embeddings,
        )
        vectorstore.add_documents(DOCUMENTOS)

        modelo = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
        compressor = CrossEncoderReranker(model=modelo, top_n=3)
        retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
        )
        resultados = retriever.invoke("o que é LangGraph?")
        for i, doc in enumerate(resultados, 1):
            print(f"  {i}. {doc.page_content[:80]}...")
    except ImportError as e:
        print(f"  (pulando: dependência ausente — {e})")
        print("  Instale: pip install sentence-transformers")


# ─────────────────────────────────────────────────────────────
# 4. Avaliação com RAGAS (opcional)
# ─────────────────────────────────────────────────────────────
def avaliar_com_ragas() -> None:
    print("\n== Avaliação RAGAS (opcional) ==")
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy
        from ragas.llms import LangchainLLMWrapper

        llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0)
        llm_avaliador = LangchainLLMWrapper(llm)

        dataset = Dataset.from_dict({
            "question": ["O que é RAG?"],
            "answer": ["RAG combina recuperação de documentos com geração de texto."],
            "contexts": [["RAG combina recuperação de documentos com geração de texto."]],
            "ground_truth": ["RAG é retrieval-augmented generation."],
        })

        resultado = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy],
            llm=llm_avaliador,
            embeddings=embeddings,
        )
        print(resultado.to_pandas())
    except Exception as e:  # noqa: BLE001 — API do RAGAS muda entre versões
        print(f"  (avaliação pulada: {e})")
        print("  Confira a versão do ragas instalada e ajuste o código se necessário.")


def main() -> None:
    print(f"Ollama Cloud | chat: {OLLAMA_MODEL} | embeddings: {EMBEDDING_MODEL}")
    demo_semantic_chunker()
    demo_parent_retriever()
    demo_reranker()
    avaliar_com_ragas()


if __name__ == "__main__":
    main()
