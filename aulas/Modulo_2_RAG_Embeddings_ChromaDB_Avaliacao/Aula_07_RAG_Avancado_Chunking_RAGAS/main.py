"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Esqueleto para alunos — complete os TODOs abaixo.
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
    # TODO: Definir um texto longo para teste
    # TODO: Instanciar o SemanticChunker usando os embeddings configurados
    # TODO: Dividir o texto em chunks semânticos
    # TODO: Imprimir os chunks resultantes
    pass


# ─────────────────────────────────────────────────────────────
# 2. ParentDocumentRetriever — recupera o bloco-pai (mais contexto)
# ─────────────────────────────────────────────────────────────
def demo_parent_retriever() -> None:
    print("\n== ParentDocumentRetriever (chunks pequenos -> blocos-pai) ==")
    # TODO: Configurar splitters para documentos pai (grandes) e filhos (pequenos)
    # TODO: Inicializar o cliente ChromaDB persistente
    # TODO: Configurar o vectorstore Chroma com a coleção e função de embedding
    # TODO: Instanciar o ParentDocumentRetriever com vectorstore, docstore e splitters
    # TODO: Adicionar a lista DOCUMENTOS ao retriever
    # TODO: Realizar uma busca (invoke) e imprimir os resultados
    pass


# ─────────────────────────────────────────────────────────────
# 3. Reranking com cross-encoder (opcional — requer sentence-transformers)
# ─────────────────────────────────────────────────────────────
def demo_reranker() -> None:
    print("\n== CrossEncoderReranker (reordena por relevância) ==")
    try:
        from langchain_community.cross_encoders import HuggingFaceCrossEncoder
        from langchain.retrievers.document_compressors import CrossEncoderReranker
        from langchain.retrievers import ContextualCompressionRetriever

        # TODO: Inicializar vectorstore Chroma e adicionar DOCUMENTOS
        # TODO: Instanciar o modelo HuggingFaceCrossEncoder (ex: "cross-encoder/ms-marco-MiniLM-L-6-v2")
        # TODO: Configurar o compressor CrossEncoderReranker
        # TODO: Criar o ContextualCompressionRetriever combinando o compressor e o retriever base
        # TODO: Realizar busca e imprimir resultados reordenados
        pass
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

        # TODO: Instanciar o LLM (ChatOllama) para ser o avaliador
        # TODO: Criar um Dataset com question, answer, contexts e ground_truth
        # TODO: Executar a função evaluate do RAGAS com as métricas desejadas
        # TODO: Imprimir o resultado da avaliação
        pass
    except Exception as e:  # noqa: BLE001 — API do RAGAS muda entre versões
        print(f"  (avaliação pulada: {e})")
        print("  Confira a versão do ragas instalada e ajuste o código se necessário.")


def main() -> None:
    print(f"Ollama Cloud | chat: {OLLAMA_MODEL} | embeddings: {EMBEDDING_MODEL}")
    # TODO: Chamar demo_semantic_chunker()
    # TODO: Chamar demo_parent_retriever()
    # TODO: Chamar demo_reranker()
    # TODO: Chamar avaliar_com_ragas()
    pass


if __name__ == "__main__":
    main()
