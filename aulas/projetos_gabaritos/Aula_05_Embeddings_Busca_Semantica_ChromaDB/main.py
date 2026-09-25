"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 05 — Embeddings e Busca Semântica com ChromaDB

Projeto local: transformar texto em vetores (embeddings), indexar no
ChromaDB e fazer busca por similaridade semântica (não por palavra-chave).

Como rodar:
    1. pip install -r requirements.txt
    2. configure o ambiente externo
    3. python main.py
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
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "aula05"
EMBEDDING_OLLAMA_HOST = os.getenv(
    "EMBEDDING_OLLAMA_HOST", "http://localhost:11434"
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
embeddings = None
client = None
vectorstore = None


def _configuracao() -> tuple[str, str]:
    load_dotenv()
    host = os.getenv("EMBEDDING_OLLAMA_HOST", EMBEDDING_OLLAMA_HOST)
    modelo_embeddings = os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL)
    return host, modelo_embeddings


def _obter_embeddings():
    global embeddings
    if embeddings is not None:
        return embeddings
    host, modelo_embeddings = _configuracao()
    os.environ["EMBEDDING_OLLAMA_HOST"] = host
    try:
        from langchain_ollama import OllamaEmbeddings
    except ImportError as erro:
        raise RuntimeError("langchain-ollama não está instalado.") from erro
    embeddings = OllamaEmbeddings(model=modelo_embeddings, base_url=host)
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


def _obter_colecao():
    return _obter_client().get_or_create_collection(name=COLLECTION_NAME)


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


def _documento_exemplo(identificador: str, texto: str) -> Document:
    documento = Document(
        page_content=texto,
        metadata={"id": identificador, "fonte": "Aula 05 — exemplos"},
    )
    try:
        documento.id = identificador
    except (AttributeError, ValueError):
        return documento
    return documento


DOCUMENTOS = [
    _documento_exemplo("doc-01", "A FIAP fica na Avenida Paulista, em São Paulo."),
    _documento_exemplo("doc-02", "O curso de Ciência da Computação tem 4 anos de duração."),
    _documento_exemplo(
        "doc-03",
        "Prompt engineering é a prática de escrever instruções eficazes para LLMs.",
    ),
    _documento_exemplo(
        "doc-04",
        "RAG combina busca em documentos com geração de texto por LLM.",
    ),
    _documento_exemplo("doc-05", "O Brasil é o maior produtor de café do mundo."),
]


def _ids_documentos(documentos: list[Document]) -> list[str]:
    ids = []
    usados = set()
    for documento in documentos:
        metadata = getattr(documento, "metadata", {}) or {}
        identificador = metadata.get("id") or getattr(documento, "id", None)
        if not identificador:
            identificador = hashlib.sha256(
                str(documento.page_content).encode("utf-8")
            ).hexdigest()
        base = f"{COLLECTION_NAME}-{identificador}"
        identificador = base
        sufixo = 2
        while identificador in usados:
            identificador = f"{base}-{sufixo}"
            sufixo += 1
        usados.add(identificador)
        ids.append(identificador)
    return ids


def _adicionar_documentos(store: Any, documentos: list[Document], ids: list[str]):
    if hasattr(store, "add_documents"):
        try:
            return store.add_documents(documentos, ids=ids)
        except TypeError as erro:
            if "ids" not in str(erro).lower():
                raise
            for documento, identificador in zip(documentos, ids):
                documento.id = identificador
            return store.add_documents(documentos)
    if hasattr(store, "upsert"):
        return store.upsert(
            ids=ids,
            documents=[documento.page_content for documento in documentos],
            metadatas=[documento.metadata for documento in documentos],
        )
    raise TypeError("A coleção não oferece uma operação de indexação.")


def _ids_existentes(store: Any) -> list[str]:
    resultado = _consultar_colecao(store, ["metadatas"])
    return [str(identificador) for identificador in (resultado.get("ids") or [])]


def _sincronizar(store: Any, documentos: list[Document], ids: list[str]) -> Any:
    obsoletos = sorted(set(_ids_existentes(store)) - set(ids))
    deleter = getattr(store, "delete", None)
    if obsoletos and callable(deleter):
        deleter(ids=obsoletos)
    if not documentos:
        return []
    return _adicionar_documentos(store, documentos, ids)


def indexar(documentos: list[Document] | None = None, store: Any = None) -> int:
    """Indexa documentos com IDs determinísticos, sem duplicar em novas execuções."""
    lista = list(DOCUMENTOS if documentos is None else documentos)
    destino = store if store is not None else _obter_vectorstore()
    _sincronizar(destino, lista, _ids_documentos(lista))
    return len(lista)


def _consultar_colecao(store: Any, include: list[str] | None = None) -> dict:
    getter = getattr(store, "get", None)
    if callable(getter):
        try:
            resultado = getter(include=include) if include is not None else getter()
        except TypeError:
            resultado = getter()
        if isinstance(resultado, dict):
            return resultado
    colecao = getattr(store, "_collection", None)
    if colecao is not None and hasattr(colecao, "get"):
        try:
            resultado = colecao.get(include=include) if include is not None else colecao.get()
        except TypeError:
            resultado = colecao.get()
        if isinstance(resultado, dict):
            return resultado
    return {}


def _documentos_do_resultado(resultado: dict) -> list[Document]:
    textos = resultado.get("documents") or []
    metadatas = resultado.get("metadatas") or []
    identificadores = resultado.get("ids") or []
    documentos = []
    for indice, texto in enumerate(textos):
        metadata = metadatas[indice] if indice < len(metadatas) else {}
        identificador = identificadores[indice] if indice < len(identificadores) else None
        documento = Document(page_content=str(texto), metadata=metadata or {})
        if identificador is not None:
            try:
                documento.id = str(identificador)
            except (AttributeError, ValueError):
                identificador = None
        documentos.append(documento)
    return documentos


def documentos_indexados(store: Any = None) -> list[Document]:
    """Retorna os documentos presentes na coleção real, não a lista de exemplo."""
    origem = store if store is not None else (
        vectorstore if vectorstore is not None else _obter_colecao()
    )
    return _documentos_do_resultado(_consultar_colecao(origem, ["documents", "metadatas"]))


def _tem_documentos(store: Any) -> bool:
    colecao = getattr(store, "_collection", None)
    if colecao is not None and hasattr(colecao, "count"):
        return int(colecao.count()) > 0
    resultado = _consultar_colecao(store, ["metadatas"])
    identificadores = resultado.get("ids")
    if identificadores is not None:
        return bool(identificadores)
    return bool(resultado.get("documents") or resultado.get("metadatas"))


def buscar(consulta: str, k: int = 2, store: Any = None) -> list[Document]:
    """Busca documentos semanticamente próximos após confirmar a indexação."""
    consulta = str(consulta or "").strip()
    if not consulta:
        raise ValueError("Informe uma consulta para buscar.")
    quantidade = max(1, int(k))
    if store is None:
        colecao = _obter_colecao()
        if not _tem_documentos(colecao):
            raise LookupError(
                "Nenhum documento indexado. Execute a indexação antes de fazer uma busca."
            )
        destino = _obter_vectorstore()
    else:
        destino = store
        if not _tem_documentos(destino):
            raise LookupError(
                "Nenhum documento indexado. Execute a indexação antes de fazer uma busca."
            )
    return destino.similarity_search(consulta, k=quantidade)


def main() -> None:
    _, modelo_embeddings = _configuracao()
    print(f"Ollama local | embeddings: {modelo_embeddings}\n")
    total = indexar()
    print(f"{total} documentos indexados.")
    for consulta in [
        "onde fica a faculdade?",
        "como fazer o computador me entender melhor?",
        "quanto tempo dura a graduação?",
    ]:
        resultados = buscar(consulta)
        print(f"\n== Busca: \"{consulta}\" ==")
        for indice, documento in enumerate(resultados, 1):
            print(f"  {indice}. {documento.page_content}")


if __name__ == "__main__":
    main()
