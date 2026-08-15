"""
Pipeline RAG — DocMind CDC
==========================
load → split → embed → store → retrieve → generate

CKP02 exige:
- RecursiveCharacterTextSplitter com separators=['\n\n','\n','. ',' ']
- nomic-embed-text via Ollama
- ChromaDB PersistentClient
- Pipeline end-to-end com citação de fonte
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ============================================================
# Configuração
# ============================================================

DATA_DIR = os.getenv("DATA_DIR", "./data")
CHROMADB_DIR = os.getenv("CHROMADB_PERSIST_DIR", "./chromadb_data")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen3.5:0.8b")
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_KEY = os.getenv("OLLAMA_API_KEY", "")

# ============================================================
# Step 1: Load — carregar documentos
# ============================================================

def load_documents(data_dir: str = DATA_DIR) -> list:
    """
    Carrega documentos .txt e .md do diretório de dados.

    Returns:
        Lista de documentos LangChain.
    """
    loader = DirectoryLoader(
        data_dir,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()

    # Adiciona metadata (nome do arquivo como fonte)
    for doc in documents:
        source = Path(doc.metadata.get("source", "desconhecido"))
        doc.metadata["filename"] = source.name
        doc.metadata["category"] = _categorize(source.name)

    print(f"📄 {len(documents)} documentos carregados de {data_dir}/")
    for doc in documents:
        print(f"   → {doc.metadata.get('filename')} ({len(doc.page_content)} chars) "
              f"[{doc.metadata.get('category')}]")

    return documents


def _categorize(filename: str) -> str:
    """Classifica documento por categoria baseado no nome do arquivo."""
    cats = {
        "direitos": "direitos_basicos",
        "vicios": "vicios_defeitos",
        "praticas": "praticas_abusivas",
        "protecao": "protecao_contratual",
        "sancoes": "sancoes",
    }
    for key, value in cats.items():
        if key in filename.lower():
            return value
    return "geral"


# ============================================================
# Step 2: Split — dividir em chunks
# ============================================================

def split_documents(
    documents: list,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list:
    """
    Divide documentos usando RecursiveCharacterTextSplitter.

    Args:
        documents: lista de documentos LangChain
        chunk_size: tamanho do chunk em caracteres
        chunk_overlap: sobreposição entre chunks adjacentes

    Returns:
        Lista de chunks.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        keep_separator=True,
    )

    chunks = splitter.split_documents(documents)
    print(f"✂️ {len(chunks)} chunks gerados (chunk_size={chunk_size}, overlap={chunk_overlap})")
    return chunks


# ============================================================
# Step 3: Embed + Step 4: Store
# ============================================================

def create_vectorstore(
    chunks: list,
    persist_dir: str = CHROMADB_DIR,
    collection_name: str = "cdc_consultoria",
) -> Chroma:
    """
    Gera embeddings e armazena no ChromaDB.

    Args:
        chunks: lista de chunks
        persist_dir: diretório de persistência
        collection_name: nome da coleção

    Returns:
        Chroma vectorstore.
    """
    # Configurar embeddings — nomic-embed-text (obrigatório CKP02)
    if OLLAMA_KEY:
        embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_BASE,
            client_kwargs={"headers": {"Authorization": f"Bearer {OLLAMA_KEY}"}},
        )
    else:
        embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_BASE,
        )

    # Criar vectorstore
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name=collection_name,
    )

    print(f"🗄️ Vectorstore criado: {len(chunks)} chunks indexados em '{collection_name}'")
    print(f"   Persistência: {persist_dir}")

    return vectorstore


def load_vectorstore(
    persist_dir: str = CHROMADB_DIR,
    collection_name: str = "cdc_consultoria",
) -> Chroma:
    """Carrega vectorstore existente do disco."""
    if OLLAMA_KEY:
        embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_BASE,
            client_kwargs={"headers": {"Authorization": f"Bearer {OLLAMA_KEY}"}},
        )
    else:
        embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_BASE,
        )

    return Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name=collection_name,
    )


# ============================================================
# Step 5: Retrieve + Step 6: Generate
# ============================================================

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Você é o Dr. Consumidor, especialista em Direito do Consumidor Brasileiro "
            "(CDC - Lei 8.078/90). Responda com base EXCLUSIVAMENTE no contexto abaixo. "
            "Sempre cite a fonte (nome do documento e trecho relevante). "
            "Se o contexto não contiver a resposta, diga: "
            "'Não encontrei esta informação na base do CDC. Consulte um advogado.'\n\n"
            "CONTEXTO:\n{context}",
        ),
        ("human", "{question}"),
    ]
)


def get_llm() -> ChatOllama:
    """Retorna o LLM configurado."""
    if OLLAMA_KEY:
        return ChatOllama(
            model=CHAT_MODEL,
            base_url=OLLAMA_BASE,
            temperature=0.2,
            client_kwargs={"headers": {"Authorization": f"Bearer {OLLAMA_KEY}"}},
        )
    return ChatOllama(model=CHAT_MODEL, base_url=OLLAMA_BASE, temperature=0.2)


def build_rag_chain(vectorstore: Chroma, top_k: int = 4):
    """
    Constrói a chain RAG completa.

    Pipeline:
        retrieve (top_k chunks) → format context → prompt → llm → resposta

    Args:
        vectorstore: Chroma vectorstore indexado
        top_k: número de chunks a recuperar

    Returns:
        Chain executável: invoke({"question": "..."}) → resposta
    """
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": top_k},
    )
    llm = get_llm()

    def format_docs(docs: list) -> str:
        """Formata documentos recuperados para o prompt."""
        formatted = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("filename", "fonte desconhecida")
            formatted.append(
                f"[Documento {i} — {source}]\n{doc.page_content}\n"
            )
        return "\n---\n".join(formatted)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )

    return rag_chain


def buscar(
    query: str,
    vectorstore: Chroma = None,
    top_k: int = 4,
) -> dict:
    """
    Função de busca — interface principal do RAG.

    Esta função é usada como @tool no CKP03.

    Args:
        query: pergunta do usuário
        vectorstore: vectorstore indexado (se None, carrega do disco)
        top_k: número de chunks

    Returns:
        dict com 'resposta', 'fontes', 'chunks'
    """
    if vectorstore is None:
        vectorstore = load_vectorstore()

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": top_k},
    )

    chunks = retriever.invoke(query)
    chain = build_rag_chain(vectorstore, top_k=top_k)
    resposta = chain.invoke(query)

    fontes = list(set(doc.metadata.get("filename", "?") for doc in chunks))

    return {
        "resposta": resposta,
        "fontes": fontes,
        "chunks": [
            {
                "conteudo": doc.page_content[:200],
                "fonte": doc.metadata.get("filename", "?"),
                "categoria": doc.metadata.get("category", "?"),
            }
            for doc in chunks
        ],
    }


# ============================================================
# Pipeline completo
# ============================================================

def pipeline_completo(
    data_dir: str = DATA_DIR,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    force_reindex: bool = False,
) -> Chroma:
    """
    Executa o pipeline RAG completo: load → split → embed → store.

    Args:
        data_dir: diretório com documentos
        chunk_size: tamanho do chunk
        chunk_overlap: sobreposição
        force_reindex: se True, reindexa mesmo se já existir

    Returns:
        Chroma vectorstore pronto para consultas.
    """
    persist_dir = os.getenv("CHROMADB_PERSIST_DIR", "./chromadb_data")

    # Verifica se já existe índice
    if not force_reindex and Path(persist_dir).exists():
        print(f"⚡ Vectorstore já existe em {persist_dir}. Use force_reindex=True para reindexar.")
        return load_vectorstore(persist_dir)

    print("=" * 60)
    print("🚀 PIPELINE RAG — DocMind CDC")
    print("=" * 60)

    # Step 1: Load
    docs = load_documents(data_dir)

    # Step 2: Split
    chunks = split_documents(docs, chunk_size, chunk_overlap)

    # Step 3 + 4: Embed + Store
    vectorstore = create_vectorstore(chunks, persist_dir)

    print("=" * 60)
    print("✅ Pipeline concluído! Vectorstore pronto para consultas.")
    print(f"   Coleção: cdc_consultoria | Chunks: {len(chunks)}")
    print("=" * 60)

    return vectorstore


if __name__ == "__main__":
    # Teste rápido do pipeline
    vs = pipeline_completo()
    resultado = buscar("Quais são os direitos básicos do consumidor?", vs)
    print(f"\n📝 Pergunta: Quais são os direitos básicos do consumidor?")
    print(f"📚 Fonte(s): {resultado['fontes']}")
    print(f"💬 Resposta: {resultado['resposta'][:300]}...")
