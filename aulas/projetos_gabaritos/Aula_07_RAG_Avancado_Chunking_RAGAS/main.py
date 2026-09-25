from __future__ import annotations

import importlib
import math
import os
import re
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from langchain_classic.retrievers import ContextualCompressionRetriever, ParentDocumentRetriever
from langchain_core.documents import Document
from langchain_core.stores import InMemoryStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from langchain_ollama import ChatOllama, OllamaEmbeddings
except ImportError:
    ChatOllama = None
    OllamaEmbeddings = None

try:
    from langchain_chroma import Chroma
except ImportError:
    Chroma = None

try:
    from langchain_community.cross_encoders import HuggingFaceCrossEncoder
except ImportError:
    HuggingFaceCrossEncoder = None

try:
    from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
except ImportError:
    CrossEncoderReranker = None

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
EMBEDDING_OLLAMA_HOST = os.getenv(
    "EMBEDDING_OLLAMA_HOST", "http://localhost:11434"
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
CROSS_ENCODER_MODEL = os.getenv(
    "CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")


@dataclass(frozen=True)
class Config:
    ollama_host: str
    ollama_api_key: str
    ollama_model: str
    embedding_host: str
    embedding_model: str
    cross_encoder_model: str
    chroma_path: str


class PipelineError(RuntimeError):
    pass


class MissingDependencyError(PipelineError):
    pass


class ExternalServiceError(PipelineError):
    pass


class SemanticTextChunker:
    def __init__(self, embedding_model: Any, threshold: float = 0.65):
        if embedding_model is None or not hasattr(embedding_model, "embed_documents"):
            raise MissingDependencyError(
                "O chunking semântico exige um modelo com embed_documents."
            )
        try:
            self.threshold = float(threshold)
        except (TypeError, ValueError) as error:
            raise ValueError("threshold deve ser numérico") from error
        if not math.isfinite(self.threshold) or not 0 <= self.threshold <= 1:
            raise ValueError("threshold deve estar entre 0 e 1")
        self.embedding_model = embedding_model

    @staticmethod
    def _normalizar(vetor: Any) -> list[float]:
        valores = [float(valor) for valor in vetor]
        if not valores or not all(math.isfinite(valor) for valor in valores):
            raise ValueError("O modelo de embeddings retornou um vetor inválido")
        norma = math.sqrt(sum(valor * valor for valor in valores))
        if norma == 0:
            raise ValueError("O modelo de embeddings retornou um vetor nulo")
        return [valor / norma for valor in valores]

    @staticmethod
    def _similaridade(primeiro: list[float], segundo: list[float]) -> float:
        if len(primeiro) != len(segundo):
            raise ValueError("Embeddings com dimensões diferentes não podem ser comparados")
        return sum(a * b for a, b in zip(primeiro, segundo))

    def split_text(self, text: str) -> list[str]:
        conteudo = str(text or "").strip()
        if not conteudo:
            return []
        segmentos = [
            segmento.strip()
            for segmento in re.split(r"(?<=[.!?])\s+|\n+", conteudo)
            if segmento.strip()
        ]
        if len(segmentos) == 1:
            return segmentos
        embeddings = list(self.embedding_model.embed_documents(segmentos))
        if len(embeddings) != len(segmentos):
            raise ValueError("O número de embeddings não corresponde aos segmentos")
        vetores = [self._normalizar(embedding) for embedding in embeddings]
        grupos = [[segmentos[0]]]
        for indice in range(1, len(segmentos)):
            similaridade = self._similaridade(vetores[indice - 1], vetores[indice])
            if similaridade < self.threshold:
                grupos.append([segmentos[indice]])
            else:
                grupos[-1].append(segmentos[indice])
        return [" ".join(grupo) for grupo in grupos]


class RagExecutionError(PipelineError):
    pass


class RagasEvaluationError(PipelineError):
    pass


_CONFIG: Config | None = None


def _read_config() -> Config:
    return Config(
        ollama_host=os.getenv("OLLAMA_HOST", OLLAMA_HOST),
        ollama_api_key=os.getenv("OLLAMA_API_KEY", OLLAMA_API_KEY),
        ollama_model=os.getenv("OLLAMA_MODEL", OLLAMA_MODEL),
        embedding_host=os.getenv(
            "EMBEDDING_OLLAMA_HOST", EMBEDDING_OLLAMA_HOST
        ),
        embedding_model=os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL),
        cross_encoder_model=os.getenv(
            "CROSS_ENCODER_MODEL", CROSS_ENCODER_MODEL
        ),
        chroma_path=os.getenv("CHROMA_PATH", CHROMA_PATH),
    )


def configurar() -> Config:
    global _CONFIG
    global OLLAMA_API_KEY
    global OLLAMA_HOST
    global OLLAMA_MODEL
    global EMBEDDING_OLLAMA_HOST
    global EMBEDDING_MODEL
    global CROSS_ENCODER_MODEL
    global CHROMA_PATH

    load_dotenv()
    _CONFIG = _read_config()
    OLLAMA_HOST = _CONFIG.ollama_host
    OLLAMA_API_KEY = _CONFIG.ollama_api_key
    OLLAMA_MODEL = _CONFIG.ollama_model
    EMBEDDING_OLLAMA_HOST = _CONFIG.embedding_host
    EMBEDDING_MODEL = _CONFIG.embedding_model
    CROSS_ENCODER_MODEL = _CONFIG.cross_encoder_model
    CHROMA_PATH = _CONFIG.chroma_path
    os.environ["OLLAMA_HOST"] = _CONFIG.ollama_host
    os.environ["OLLAMA_API_KEY"] = _CONFIG.ollama_api_key
    os.environ["EMBEDDING_OLLAMA_HOST"] = _CONFIG.embedding_host
    return _CONFIG


def _config() -> Config:
    return _CONFIG or _read_config()


def _is_local_ollama(host: str) -> bool:
    parsed = urlparse(host if "://" in host else f"http://{host}")
    hostname = (parsed.hostname or "").lower()
    return hostname in {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "ollama",
        "host.docker.internal",
    } or hostname.endswith(".local")


def _require_remote_credentials(config: Config) -> None:
    if not _is_local_ollama(config.ollama_host) and not config.ollama_api_key:
        raise ExternalServiceError(
            "OLLAMA_API_KEY não configurada para um host Ollama remoto."
        )


def _semantic_chunker_class() -> Any:
    return SemanticTextChunker


def _chroma_class() -> Any:
    if Chroma is not None:
        return Chroma
    try:
        module = importlib.import_module("langchain_chroma")
        return module.Chroma
    except (ImportError, AttributeError) as error:
        raise MissingDependencyError(
            "Chroma exige langchain-chroma e chromadb."
        ) from error


def _cross_encoder_class() -> Any:
    if HuggingFaceCrossEncoder is not None:
        return HuggingFaceCrossEncoder
    try:
        module = importlib.import_module("langchain_community.cross_encoders")
        return module.HuggingFaceCrossEncoder
    except (ImportError, AttributeError) as error:
        raise MissingDependencyError(
            "O reranker exige langchain-community e sentence-transformers."
        ) from error


def _cross_encoder_reranker_class() -> Any:
    if CrossEncoderReranker is not None:
        return CrossEncoderReranker
    try:
        module = importlib.import_module(
            "langchain_classic.retrievers.document_compressors"
        )
        return module.CrossEncoderReranker
    except (ImportError, AttributeError) as error:
        raise MissingDependencyError(
            "CrossEncoderReranker não está disponível no ambiente atual."
        ) from error


def criar_embeddings(
    config: Config | None = None,
    model_cls: Any = None,
) -> Any:
    config = config or _config()
    if model_cls is None:
        raise MissingDependencyError("OllamaEmbeddings não está instalado.")
    return model_cls(model=config.embedding_model, base_url=config.embedding_host)


def criar_chat(config: Config | None = None, model_cls: Any = None) -> Any:
    config = config or _config()
    if model_cls is None:
        _require_remote_credentials(config)
    if model_cls is None:
        raise MissingDependencyError("ChatOllama não está instalado.")
    return model_cls(
        model=config.ollama_model,
        base_url=config.ollama_host,
        temperature=0,
    )


DOCUMENTOS = [
    Document(
        page_content=(
            "LangChain é um framework para construir aplicações com LLMs, com "
            "módulos de chains, memória e retrieval."
        )
    ),
    Document(
        page_content=(
            "LangGraph estende o LangChain para orquestrar grafos de estado e "
            "fluxos agênticos com checkpoints."
        )
    ),
    Document(
        page_content=(
            "RAG combina recuperação de documentos com geração para reduzir "
            "alucinações e citar fontes."
        )
    ),
    Document(
        page_content=(
            "Chunking divide textos longos em pedaços menores para caber na "
            "janela de contexto e melhorar a busca."
        )
    ),
    Document(
        page_content=(
            "Um cross-encoder reordena os documentos recuperados para colocar "
            "os mais relevantes no topo."
        )
    ),
]

TEXTO_SEMANTICO = (
    "Aprendizado de máquina é um subcampo da inteligência artificial. "
    "Modelos de linguagem são treinados em grandes volumes de texto. "
    "Prompt engineering é a arte de escrever boas instruções. "
    "RAG adiciona contexto externo para melhorar as respostas."
)
PERGUNTA_RAGAS = "O que é RAG?"
GROUND_TRUTH_RAGAS = "RAG combina recuperação de documentos com geração de texto."
PROMPT_RAG = (
    "Responda à pergunta usando somente os contextos fornecidos. "
    "Se os contextos não forem suficientes, diga que não sabe.\n"
    "Contextos:\n{contexts}\n\nPergunta: {question}\nResposta:"
)


def _documentos(documents: Sequence[Document] | None) -> list[Document]:
    return list(DOCUMENTOS if documents is None else documents)


def _chromadb() -> Any:
    try:
        return importlib.import_module("chromadb")
    except ImportError as error:
        raise MissingDependencyError("Chroma exige chromadb.") from error


def _missing_collection(error: Exception) -> bool:
    name = type(error).__name__.lower()
    message = str(error).lower()
    return name in {"notfounderror", "notfound", "keyerror"} or any(
        marker in message for marker in ("not found", "does not exist")
    )


def _clear_collection(client: Any, collection_name: str) -> str:
    delete_collection = getattr(client, "delete_collection", None)
    if callable(delete_collection):
        try:
            delete_collection(collection_name)
        except Exception as error:
            if not _missing_collection(error):
                raise
        return collection_name
    return f"{collection_name}_{uuid.uuid4().hex}"


def _new_chroma_client(path: str) -> Any:
    return _chromadb().PersistentClient(path=path)


def criar_vectorstore(
    embedding_model: Any = None,
    *,
    collection_name: str = "aula07_documents",
    client: Any = None,
    client_factory: Callable[[], Any] | None = None,
    vectorstore_cls: Any = None,
    documents: Sequence[Document] | None = None,
    reset_collection: bool = True,
    path: str | None = None,
) -> Any:
    if embedding_model is None:
        embedding_model = criar_embeddings()
    if client is None:
        client = client_factory() if client_factory is not None else _new_chroma_client(
            path or _config().chroma_path
        )
    if reset_collection:
        collection_name = _clear_collection(client, collection_name)
    vectorstore_cls = vectorstore_cls or _chroma_class()
    vectorstore = vectorstore_cls(
        client=client,
        collection_name=collection_name,
        embedding_function=embedding_model,
    )
    vectorstore.add_documents(_documentos(documents))
    return vectorstore


def criar_parent_retriever(
    embedding_model: Any = None,
    documents: Sequence[Document] | None = None,
    *,
    client: Any = None,
    client_factory: Callable[[], Any] | None = None,
    vectorstore_cls: Any = None,
    retriever_cls: Any = None,
    docstore: Any = None,
    parent_splitter: Any = None,
    child_splitter: Any = None,
    collection_name: str = "aula07_parent",
    reset_collection: bool = True,
    path: str | None = None,
) -> Any:
    if embedding_model is None:
        embedding_model = criar_embeddings()
    if parent_splitter is None:
        parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
    if child_splitter is None:
        child_splitter = RecursiveCharacterTextSplitter(chunk_size=200)
    if docstore is None:
        docstore = InMemoryStore()
    retriever_cls = retriever_cls or ParentDocumentRetriever
    vectorstore = criar_vectorstore(
        embedding_model,
        collection_name=collection_name,
        client=client,
        client_factory=client_factory,
        vectorstore_cls=vectorstore_cls,
        documents=[],
        reset_collection=reset_collection,
        path=path,
    )
    retriever = retriever_cls(
        vectorstore=vectorstore,
        docstore=docstore,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
    )
    retriever.add_documents(_documentos(documents))
    return retriever


def executar_semantic_chunker(
    texto: str,
    embedding_model: Any = None,
    chunker_cls: Any = None,
) -> list[str]:
    if embedding_model is None:
        embedding_model = criar_embeddings()
    chunker_cls = chunker_cls or _semantic_chunker_class()
    chunks = chunker_cls(embedding_model).split_text(texto)
    return list(chunks)


def demo_semantic_chunker(
    embedding_model: Any = None,
    texto: str = TEXTO_SEMANTICO,
    chunker_cls: Any = None,
) -> list[str]:
    print("\n== SemanticChunker (divisão por similaridade) ==")
    chunks = executar_semantic_chunker(texto, embedding_model, chunker_cls)
    for index, chunk in enumerate(chunks, 1):
        print(f"  chunk {index}: {chunk.strip()[:70]}...")
    return chunks


def buscar_documentos(
    consulta: str,
    embedding_model: Any = None,
    documents: Sequence[Document] | None = None,
    **retriever_options: Any,
) -> list[Document]:
    retriever = criar_parent_retriever(
        embedding_model,
        documents,
        **retriever_options,
    )
    return list(retriever.invoke(consulta))


def demo_parent_retriever(
    embedding_model: Any = None,
    documents: Sequence[Document] | None = None,
    consulta: str = "como evitar alucinações?",
) -> list[Document]:
    print("\n== ParentDocumentRetriever (chunks pequenos -> blocos-pai) ==")
    resultados = buscar_documentos(consulta, embedding_model, documents)
    for index, document in enumerate(resultados, 1):
        print(f"  {index}. {document.page_content[:80]}...")
    return resultados


def criar_reranker_retriever(
    embedding_model: Any = None,
    documents: Sequence[Document] | None = None,
    *,
    model: Any = None,
    model_factory: Callable[[], Any] | None = None,
    vectorstore: Any = None,
    vectorstore_cls: Any = None,
    client: Any = None,
    client_factory: Callable[[], Any] | None = None,
    collection_name: str = "aula07_rerank",
    reset_collection: bool = True,
    path: str | None = None,
    compressor_cls: Any = None,
    retriever_cls: Any = None,
) -> Any:
    if embedding_model is None:
        embedding_model = criar_embeddings()
    if vectorstore is None:
        vectorstore = criar_vectorstore(
            embedding_model,
            collection_name=collection_name,
            client=client,
            client_factory=client_factory,
            vectorstore_cls=vectorstore_cls,
            documents=documents,
            reset_collection=reset_collection,
            path=path,
        )
    if model is None:
        if model_factory is not None:
            model = model_factory()
        else:
            model = _cross_encoder_class()(
                model_name=_config().cross_encoder_model
            )
    compressor_cls = compressor_cls or _cross_encoder_reranker_class()
    retriever_cls = retriever_cls or ContextualCompressionRetriever
    compressor = compressor_cls(model=model, top_n=3)
    return retriever_cls(
        base_compressor=compressor,
        base_retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
    )


def demo_reranker(
    embedding_model: Any = None,
    documents: Sequence[Document] | None = None,
    consulta: str = "o que é LangGraph?",
    *,
    model: Any = None,
    model_factory: Callable[[], Any] | None = None,
) -> list[Document]:
    print("\n== CrossEncoderReranker (reordena por relevância) ==")
    retriever = criar_reranker_retriever(
        embedding_model,
        documents,
        model=model,
        model_factory=model_factory,
    )
    resultados = list(retriever.invoke(consulta))
    for index, document in enumerate(resultados, 1):
        print(f"  {index}. {document.page_content[:80]}...")
    return resultados


@dataclass(frozen=True)
class ExemploRag:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "contexts": list(self.contexts),
            "ground_truth": self.ground_truth,
        }


def _call_retriever(retriever: Any, pergunta: str) -> Any:
    if hasattr(retriever, "invoke"):
        return retriever.invoke(pergunta)
    if callable(retriever):
        return retriever(pergunta)
    raise RagExecutionError("O retriever não oferece invoke nem callable.")


def _answer_text(response: Any) -> str:
    if isinstance(response, str):
        return response.strip()
    if isinstance(response, Mapping):
        response = response.get("content", "")
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, Sequence) and not isinstance(content, (str, bytes)):
        parts: list[str] = []
        for item in content:
            if isinstance(item, Mapping):
                value = item.get("text", item.get("content", ""))
            else:
                value = item
            if value:
                parts.append(str(value))
        return "".join(parts).strip()
    return str(content).strip()


def executar_rag(
    pergunta: str,
    retriever: Any,
    llm: Any,
    ground_truth: str,
) -> ExemploRag:
    documents = list(_call_retriever(retriever, pergunta))
    contexts = [
        str(getattr(document, "page_content", document)).strip()
        for document in documents
    ]
    contexts = [context for context in contexts if context]
    if not contexts:
        raise RagExecutionError("A execução RAG não recuperou nenhum contexto.")
    if not hasattr(llm, "invoke") and not callable(llm):
        raise RagExecutionError("O modelo de resposta não oferece invoke nem callable.")
    prompt = PROMPT_RAG.format(
        contexts="\n\n".join(contexts),
        question=pergunta,
    )
    response = llm.invoke(prompt) if hasattr(llm, "invoke") else llm(prompt)
    answer = _answer_text(response)
    if not answer:
        raise RagExecutionError("A execução RAG produziu uma resposta vazia.")
    return ExemploRag(
        question=pergunta,
        answer=answer,
        contexts=contexts,
        ground_truth=ground_truth,
    )


def _dataset_payload(examples: Sequence[ExemploRag]) -> dict[str, list[Any]]:
    return {
        "question": [example.question for example in examples],
        "answer": [example.answer for example in examples],
        "contexts": [list(example.contexts) for example in examples],
        "ground_truth": [example.ground_truth for example in examples],
    }


def _build_dataset(
    examples: Sequence[ExemploRag],
    dataset_factory: Any = None,
) -> Any:
    payload = _dataset_payload(examples)
    if dataset_factory is None:
        try:
            dataset_factory = importlib.import_module("datasets").Dataset
        except ImportError as error:
            raise MissingDependencyError("RAGAS exige datasets.") from error
    if hasattr(dataset_factory, "from_dict"):
        return dataset_factory.from_dict(payload)
    return dataset_factory(payload)


def _ragas_metrics() -> list[Any]:
    try:
        from ragas.metrics import answer_relevancy, faithfulness

        return [faithfulness, answer_relevancy]
    except ImportError as error:
        raise MissingDependencyError(
            "A API de métricas RAGAS instalada não expõe faithfulness e answer_relevancy."
        ) from error


def _ragas_evaluator() -> Any:
    try:
        return importlib.import_module("ragas").evaluate
    except ImportError as error:
        raise MissingDependencyError("RAGAS não está instalado.") from error


def _contem_valor_nao_finito(value: Any) -> bool:
    if isinstance(value, Real):
        return not math.isfinite(float(value))
    if isinstance(value, Mapping):
        return any(_contem_valor_nao_finito(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contem_valor_nao_finito(item) for item in value)
    return False


def _ragas_records(result: Any) -> list[dict[str, Any]]:
    if result is not None and hasattr(result, "to_pandas"):
        result = result.to_pandas()
    if result is not None and hasattr(result, "to_dict") and not isinstance(result, Mapping):
        converted = result.to_dict(orient="records")
        if isinstance(converted, list):
            result = converted
        else:
            result = [converted]
    elif isinstance(result, Mapping):
        result = [dict(result)]
    elif not isinstance(result, list):
        result = []
    records = [
        dict(item)
        for item in result
        if isinstance(item, Mapping) and item
    ]
    if not records or not any(
        value is not None for record in records for value in record.values()
    ):
        raise RagasEvaluationError("RAGAS não retornou métricas verificáveis.")
    for record in records:
        for nome, valor in record.items():
            if _contem_valor_nao_finito(valor):
                raise RagasEvaluationError(
                    f"RAGAS retornou uma métrica não finita: {nome}."
                )
    return records


def _exemplo_from_value(value: Any) -> ExemploRag:
    if isinstance(value, ExemploRag):
        return value
    if isinstance(value, Mapping):
        return ExemploRag(
            question=str(value["question"]),
            answer=str(value["answer"]),
            contexts=[str(context) for context in value["contexts"]],
            ground_truth=str(value["ground_truth"]),
        )
    raise TypeError("execution deve ser ExemploRag ou um mapeamento equivalente.")


def avaliar_com_ragas(
    pergunta: str = PERGUNTA_RAGAS,
    ground_truth: str = GROUND_TRUTH_RAGAS,
    *,
    documents: Sequence[Document] | None = None,
    embedding_model: Any = None,
    chat_model: Any = None,
    retriever: Any = None,
    retriever_factory: Callable[[Any], Any] | None = None,
    evaluator: Any = None,
    dataset_factory: Any = None,
    llm_wrapper_factory: Callable[[Any], Any] | None = None,
    metrics: Sequence[Any] | None = None,
    execution: ExemploRag | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if execution is None:
        if embedding_model is None:
            embedding_model = criar_embeddings()
        if chat_model is None:
            chat_model = criar_chat()
        if retriever is None:
            if retriever_factory is None:
                retriever = criar_parent_retriever(embedding_model, documents)
            else:
                retriever = retriever_factory(embedding_model)
        execution = executar_rag(
            pergunta,
            retriever,
            chat_model,
            ground_truth,
        )
    example = _exemplo_from_value(execution)
    dataset = _build_dataset([example], dataset_factory)
    injected_evaluator = evaluator is not None
    if injected_evaluator:
        evaluate_fn = evaluator.evaluate if hasattr(evaluator, "evaluate") else evaluator
    else:
        evaluate_fn = _ragas_evaluator()
    if metrics is None:
        metrics = [] if injected_evaluator else _ragas_metrics()
    if llm_wrapper_factory is not None:
        llm_for_ragas = llm_wrapper_factory(chat_model)
    elif injected_evaluator:
        llm_for_ragas = chat_model
    else:
        try:
            wrapper_cls = importlib.import_module("ragas.llms").LangchainLLMWrapper
        except (ImportError, AttributeError) as error:
            raise MissingDependencyError(
                "RAGAS exige LangchainLLMWrapper para o modelo configurado."
            ) from error
        llm_for_ragas = wrapper_cls(chat_model)
    resultado = evaluate_fn(
        dataset,
        metrics=list(metrics),
        llm=llm_for_ragas,
        embeddings=embedding_model,
    )
    return {
        "status": "ok",
        "metrics": _ragas_records(resultado),
        "execution": example.as_dict(),
    }


def main() -> int:
    try:
        config = configurar()
        embedding_model = criar_embeddings(config)
    except PipelineError as error:
        print(f"Configuração indisponível: {error}")
        return 1
    print(
        f"Ollama Cloud | chat: {config.ollama_model} | "
        f"embeddings locais: {config.embedding_model}"
    )
    for label, operation in (
        ("chunking", lambda: demo_semantic_chunker(embedding_model)),
        ("ParentDocumentRetriever", lambda: demo_parent_retriever(embedding_model)),
        ("reranker", lambda: demo_reranker(embedding_model)),
    ):
        try:
            operation()
        except Exception as error:
            print(f"{label} indisponível: {error}")
    try:
        resultado = avaliar_com_ragas(embedding_model=embedding_model)
    except Exception as error:
        print(f"RAGAS indisponível: {error}")
    else:
        print("Métricas RAGAS:")
        print(resultado["metrics"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
