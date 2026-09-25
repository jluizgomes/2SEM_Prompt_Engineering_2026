"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 06 — Pipeline RAG Completo

Projeto local: pipeline RAG de ponta a ponta — carregar um PDF, dividir
em chunks, indexar no ChromaDB e responder perguntas citando o contexto.

Como rodar:
    1. pip install -r requirements.txt
    2. configure o ambiente externo
    3. (opcional) coloque um PDF em ./data/
    4. python main.py

Sem PDF em ./data/, o projeto usa um texto de exemplo embutido — assim o
pipeline roda do mesmo jeito para demonstração.
"""
import hashlib
import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

from langchain_core.documents import Document

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "aula06"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
EMBEDDING_OLLAMA_HOST = os.getenv(
    "EMBEDDING_OLLAMA_HOST", "http://localhost:11434"
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
embeddings = None
client = None
vectorstore = None
llm = None
_INDEX_VERSION = 0


def _configuracao() -> tuple[str, str, str, str, str]:
    load_dotenv()
    host = os.getenv("OLLAMA_HOST", OLLAMA_HOST)
    chave = os.getenv("OLLAMA_API_KEY", OLLAMA_API_KEY)
    modelo = os.getenv("OLLAMA_MODEL", OLLAMA_MODEL)
    embedding_host = os.getenv("EMBEDDING_OLLAMA_HOST", EMBEDDING_OLLAMA_HOST)
    modelo_embeddings = os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL)
    return host, chave, modelo, embedding_host, modelo_embeddings


def _host_local(host: str) -> bool:
    return any(marca in host for marca in ("localhost", "127.0.0.1", "0.0.0.0", "::1"))


def _obter_embeddings():
    global embeddings
    if embeddings is not None:
        return embeddings
    _, _, _, embedding_host, modelo_embeddings = _configuracao()
    os.environ["EMBEDDING_OLLAMA_HOST"] = embedding_host
    try:
        from langchain_ollama import OllamaEmbeddings
    except ImportError as erro:
        raise RuntimeError("langchain-ollama não está instalado.") from erro
    embeddings = OllamaEmbeddings(
        model=modelo_embeddings,
        base_url=embedding_host,
    )
    return embeddings


def _obter_client():
    global client
    if client is not None:
        return client
    try:
        import chromadb
    except ImportError as erro:
        raise RuntimeError("chromadb não está instalado.") from erro
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client


def _obter_vectorstore():
    global vectorstore
    if vectorstore is not None:
        return vectorstore
    try:
        from langchain_community.vectorstores import Chroma
    except ImportError as erro:
        raise RuntimeError("langchain-community não está instalado.") from erro
    vectorstore = Chroma(
        client=_obter_client(),
        collection_name=COLLECTION_NAME,
        embedding_function=_obter_embeddings(),
    )
    return vectorstore


def invalidar_cache() -> None:
    global client, vectorstore
    client = None
    vectorstore = None


def _documento_exemplo(texto: str, pagina: int = 1) -> Document:
    return Document(
        page_content=texto,
        metadata={"source": "texto de exemplo", "page": pagina},
    )


def carregar_documentos() -> list[Document]:
    pdfs = sorted(DATA_DIR.glob("*.pdf")) if DATA_DIR.exists() else []
    if pdfs:
        try:
            from langchain_community.document_loaders import PyMuPDFLoader
        except ImportError as erro:
            raise RuntimeError("langchain-community não está instalado.") from erro
        documentos = []
        for pdf in pdfs:
            carregados = PyMuPDFLoader(str(pdf)).load()
            for documento in carregados:
                metadata = dict(documento.metadata or {})
                metadata.setdefault("source", str(pdf))
                documento.metadata = metadata
            documentos.extend(carregados)
        print(f"{len(documentos)} páginas carregadas de {len(pdfs)} PDF(s).")
        return documentos
    print("Nenhum PDF em ./data/ — usando texto de exemplo embutido.")
    return [
        _documento_exemplo(
            "A FIAP é uma instituição de ensino superior "
            "localizada na Avenida Paulista, em São Paulo."
        ),
        _documento_exemplo(
            "O curso de Ciência da Computação forma "
            "profissionais para atuar com tecnologia e inovação."
        ),
        _documento_exemplo(
            "Prompt engineering é escrever instruções claras "
            "para modelos de linguagem."
        ),
        _documento_exemplo(
            "RAG significa Retrieval-Augmented Generation: "
            "buscar contexto e gerar resposta com base nele."
        ),
    ]


def dividir(docs: list[Document]) -> list[Document]:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError as erro:
        raise RuntimeError("langchain-text-splitters não está instalado.") from erro
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)
    for indice, chunk in enumerate(chunks):
        metadata = dict(chunk.metadata or {})
        metadata.setdefault("source", "documento")
        metadata.setdefault("page", 1)
        metadata["chunk"] = indice
        chunk.metadata = metadata
    print(f"{len(chunks)} chunks criados.")
    return chunks


def _identificador_chunk(chunk: Document, indice: int, versao: int | None = None) -> str:
    metadata = getattr(chunk, "metadata", {}) or {}
    fonte = str(metadata.get("source", metadata.get("fonte", "documento")))
    pagina = str(metadata.get("page", metadata.get("pagina", "")))
    conteudo = str(getattr(chunk, "page_content", ""))
    versao_atual = _INDEX_VERSION if versao is None else int(versao)
    bruto = f"{COLLECTION_NAME}|v{versao_atual}|{fonte}|{pagina}|{indice}|{conteudo}"
    return f"{COLLECTION_NAME}-{hashlib.sha256(bruto.encode('utf-8')).hexdigest()}"


def _ids_chunks(chunks: list[Document], versao: int) -> list[str]:
    identificadores = []
    usados = set()
    for indice, chunk in enumerate(chunks):
        base = _identificador_chunk(chunk, indice, versao)
        identificador = base
        sufixo = 2
        while identificador in usados:
            identificador = f"{base}-{sufixo}"
            sufixo += 1
        usados.add(identificador)
        identificadores.append(identificador)
    return identificadores


def _dados_existentes(store: Any) -> dict[str, Any]:
    getter = getattr(store, "get", None)
    if not callable(getter):
        colecao = getattr(store, "_collection", None)
        getter = getattr(colecao, "get", None)
    if callable(getter):
        try:
            resultado = getter(include=["metadatas"])
        except TypeError:
            resultado = getter()
        if isinstance(resultado, dict):
            return resultado
    return {"ids": [], "metadatas": []}


def _ids_existentes(store: Any) -> list[str]:
    resultado = _dados_existentes(store)
    return [str(identificador) for identificador in (resultado.get("ids") or [])]


def _versoes_existentes(store: Any) -> list[int]:
    versoes = []
    for metadata in _dados_existentes(store).get("metadatas") or []:
        if not isinstance(metadata, dict):
            continue
        try:
            versoes.append(int(metadata.get("index_version")))
        except (TypeError, ValueError):
            continue
    return versoes


def _proxima_versao(store: Any) -> int:
    return max([_INDEX_VERSION, *_versoes_existentes(store)]) + 1


def _adicionar(store: Any, chunks: list[Document], ids: list[str]) -> Any:
    if hasattr(store, "add_documents"):
        try:
            return store.add_documents(chunks, ids=ids)
        except TypeError as erro:
            if "ids" not in str(erro).lower():
                raise
            for chunk, identificador in zip(chunks, ids):
                chunk.id = identificador
            return store.add_documents(chunks)
    if hasattr(store, "upsert"):
        return store.upsert(
            ids=ids,
            documents=[chunk.page_content for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
        )
    raise TypeError("A coleção não oferece uma operação de indexação.")


def _sincronizar(
    store: Any,
    chunks: list[Document],
    ids: list[str],
    versao: int,
) -> Any:
    if not chunks:
        return []
    existentes = set(_ids_existentes(store))
    obsoletos = sorted(existentes - set(ids))
    for chunk, identificador in zip(chunks, ids):
        metadata = dict(getattr(chunk, "metadata", {}) or {})
        metadata["id"] = identificador
        metadata["index_version"] = int(versao)
        chunk.metadata = metadata
    try:
        resultado = _adicionar(store, chunks, ids)
    except Exception:
        deleter = getattr(store, "delete", None)
        if callable(deleter):
            try:
                deleter(ids=ids)
            except Exception:
                pass
        raise
    deleter = getattr(store, "delete", None)
    if obsoletos and callable(deleter):
        deleter(ids=obsoletos)
    return resultado


def indexar(chunks: list[Document], store: Any = None) -> Any:
    """Sincroniza chunks na coleção real usando IDs determinísticos."""
    global _INDEX_VERSION
    lista = list(chunks or [])
    destino = store if store is not None else _obter_vectorstore()
    if not lista:
        return destino
    versao = _proxima_versao(destino)
    _sincronizar(destino, lista, _ids_chunks(lista, versao), versao)
    _INDEX_VERSION = versao
    return destino


def versao_indice() -> int:
    return _INDEX_VERSION


def _resposta_texto(resposta: Any) -> str:
    conteudo = getattr(resposta, "content", None)
    if conteudo is not None:
        if isinstance(conteudo, list):
            return "".join(str(item) for item in conteudo)
        return str(conteudo)
    if isinstance(resposta, dict) and "content" in resposta:
        return str(resposta["content"])
    return str(resposta)


def _obter_llm():
    global llm
    if llm is not None:
        return llm
    host, chave, modelo, _, _ = _configuracao()
    if not chave and not _host_local(host):
        raise RuntimeError(
            "OLLAMA_API_KEY não encontrada. Copie .env.example para .env e preencha a chave."
        )
    os.environ["OLLAMA_HOST"] = host
    if chave:
        os.environ["OLLAMA_API_KEY"] = chave
    try:
        from langchain_ollama import ChatOllama
    except ImportError as erro:
        raise RuntimeError("langchain-ollama não está instalado.") from erro
    llm = ChatOllama(model=modelo, base_url=host, temperature=0.2, reasoning=False)
    return llm


def _fonte_documento(documento: Document, indice: int) -> dict:
    metadata = getattr(documento, "metadata", {}) or {}
    fonte = metadata.get("source", metadata.get("fonte", "documento"))
    pagina = metadata.get("page", metadata.get("pagina"))
    identificador = getattr(documento, "id", None) or metadata.get("id")
    return {
        "id": identificador or _identificador_chunk(documento, indice),
        "fonte": str(fonte),
        "pagina": pagina,
        "trecho": str(getattr(documento, "page_content", "")),
    }


def _documentos_retornados(retriever: Any, pergunta: str) -> list[Document]:
    if hasattr(retriever, "invoke"):
        resultado = retriever.invoke(pergunta)
    elif hasattr(retriever, "get_relevant_documents"):
        resultado = retriever.get_relevant_documents(pergunta)
    else:
        return []
    if resultado is None:
        return []
    if not isinstance(resultado, (list, tuple)):
        resultado = [resultado]
    documentos = []
    for item in resultado:
        if hasattr(item, "page_content"):
            documentos.append(item)
        else:
            documentos.append(Document(page_content=str(item)))
    return documentos


class RAGChain:
    def __init__(self, vectorstore: Any, llm: Any = None, k: int = 3):
        self.vectorstore = vectorstore
        self.llm = llm
        self.retriever = vectorstore.as_retriever(search_kwargs={"k": max(1, int(k))})

    def _contexto(self, documentos: list[Document]) -> str:
        partes = []
        for indice, documento in enumerate(documentos, 1):
            fonte = _fonte_documento(documento, indice - 1)
            partes.append(
                f"[Fonte {indice} | {fonte['fonte']} | página {fonte['pagina']}]\n"
                f"{documento.page_content}"
            )
        return "\n\n".join(partes)

    def invoke_with_sources(self, pergunta: str) -> dict:
        pergunta = str(pergunta or "").strip()
        if not pergunta:
            raise ValueError("Informe uma pergunta.")
        documentos = _documentos_retornados(self.retriever, pergunta)
        if not documentos:
            return {
                "resposta": "Não encontrei documentos relevantes para responder à pergunta.",
                "fontes": [],
            }
        contexto = self._contexto(documentos)
        modelo = self.llm if self.llm is not None else _obter_llm()
        mensagens = [
            {
                "role": "system",
                "content": (
                    "Responda APENAS com base no contexto abaixo. Se não houver informação, "
                    "diga que não sabe.\n\nContexto:\n" + contexto
                ),
            },
            {"role": "user", "content": "Pergunta: " + pergunta},
        ]
        resposta = _resposta_texto(modelo.invoke(mensagens))
        return {
            "resposta": resposta,
            "fontes": [_fonte_documento(documento, indice) for indice, documento in enumerate(documentos)],
        }

    def invoke(self, pergunta: str, config=None) -> str:
        return self.invoke_with_sources(pergunta)["resposta"]


def montar_chain(vectorstore: Any, llm: Any = None):
    return RAGChain(vectorstore, llm=llm)


def main() -> None:
    _, _, modelo, _, modelo_embeddings = _configuracao()
    print(f"Ollama Cloud | chat: {modelo} | embeddings locais: {modelo_embeddings}\n")
    docs = carregar_documentos()
    chunks = dividir(docs)
    store = indexar(chunks)
    rag = montar_chain(store)

    print("\n== Perguntas ao pipeline RAG ==")
    for pergunta in [
        "Onde fica a FIAP?",
        "O que significa RAG?",
        "Qual é a capital da Austrália?",
    ]:
        resultado = rag.invoke_with_sources(pergunta)
        print(f"\nP: {pergunta}\nR: {resultado['resposta']}")
        print("Fontes:", resultado["fontes"])


if __name__ == "__main__":
    main()
