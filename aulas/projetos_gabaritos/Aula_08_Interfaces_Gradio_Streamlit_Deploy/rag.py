import hashlib
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent
CORPUS_PATH = RAIZ / "data" / "corpus.txt"
CHROMA_PATH = RAIZ / "chroma_db"
_chain: Any = None


def carregar_corpus(caminho: str | Path = CORPUS_PATH) -> list[str]:
    texto = Path(caminho).read_text(encoding="utf-8")
    return [trecho.strip() for trecho in texto.split("\n\n") if trecho.strip()]


class MemoriaPorSessao:
    def __init__(self, factory: Callable[[str], Any] | None = None):
        self._factory = factory
        self._histories: dict[str, Any] = {}

    def obter(self, session_id: str) -> Any:
        chave = str(session_id or "").strip()
        if not chave:
            raise ValueError("session_id não pode ser vazio")
        if chave not in self._histories:
            if self._factory is not None:
                self._histories[chave] = self._factory(chave)
            else:
                from langchain_core.chat_history import InMemoryChatMessageHistory

                self._histories[chave] = InMemoryChatMessageHistory()
        return self._histories[chave]


class ChainComMemoria:
    def __init__(self, chain: Any, memoria: MemoriaPorSessao):
        self._chain = chain
        self._memoria = memoria

    def invoke(self, dados: Mapping[str, Any], config: Mapping[str, Any] | None = None, **kwargs: Any) -> Any:
        from langchain_core.messages import AIMessage, HumanMessage

        configuracao = dict(config or {})
        session_id = str(configuracao.get("configurable", {}).get("session_id") or "").strip()
        if not session_id:
            raise ValueError("session_id não pode ser vazio")
        historico = self._memoria.obter(session_id)
        entrada = dict(dados)
        entrada["history"] = list(historico.messages)
        resposta = self._chain.invoke(entrada, config=configuracao, **kwargs)
        historico.add_messages([
            HumanMessage(content=entrada["pergunta"]),
            AIMessage(content=str(resposta)),
        ])
        return resposta


def configuracao_modelo(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    if environ is None:
        from dotenv import load_dotenv

        load_dotenv()
        environ = os.environ
    api_key = environ.get("OLLAMA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OLLAMA_API_KEY não encontrada. Copie .env.example para .env e preencha a chave."
        )
    return {
        "host": environ.get("OLLAMA_HOST", "https://ollama.com").strip(),
        "api_key": api_key,
        "model": environ.get("OLLAMA_MODEL", "gpt-oss:120b").strip(),
        "embedding_host": environ.get(
            "EMBEDDING_OLLAMA_HOST", "http://localhost:11434"
        ).strip(),
        "embedding_model": environ.get("EMBEDDING_MODEL", "nomic-embed-text").strip(),
    }


def _chat_client_kwargs(config: Mapping[str, str]) -> dict[str, dict[str, str]]:
    host = config.get("host", "")
    if config.get("api_key") and host.startswith(("http://", "https://")):
        return {"headers": {"Authorization": f"Bearer {config['api_key']}"}}
    return {}


def _criar_store(config: Mapping[str, str], textos: list[str]) -> Any:
    from langchain_chroma import Chroma
    from langchain_core.documents import Document
    from langchain_ollama import OllamaEmbeddings

    embeddings = OllamaEmbeddings(
        model=config["embedding_model"],
        base_url=config["embedding_host"],
    )
    digest = hashlib.sha256("\n\n".join(textos).encode("utf-8")).hexdigest()[:12]
    store = Chroma(
        collection_name=f"aula08_{digest}",
        embedding_function=embeddings,
        persist_directory=str(CHROMA_PATH),
    )
    if not store.get().get("ids"):
        documents = [
            Document(
                page_content=texto,
                metadata={"source": CORPUS_PATH.name},
            )
            for texto in textos
        ]
        store.add_documents(documents)
    return store


def _criar_llm(config: Mapping[str, str]) -> Any:
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=config["model"],
        base_url=config["host"],
        temperature=0.2,
        client_kwargs=_chat_client_kwargs(config),
    )


def criar_chain_rag(
    config: Mapping[str, str] | None = None,
    store: Any = None,
    llm: Any = None,
    memoria: MemoriaPorSessao | None = None,
) -> Any:
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.runnables import RunnableLambda, RunnablePassthrough

    configuracao = dict(config if config is not None else configuracao_modelo())
    if configuracao.get("api_key"):
        os.environ["OLLAMA_HOST"] = configuracao["host"]
        os.environ["OLLAMA_API_KEY"] = configuracao["api_key"]
    if configuracao.get("embedding_host"):
        os.environ["EMBEDDING_OLLAMA_HOST"] = configuracao["embedding_host"]
    textos = carregar_corpus() if store is None else []
    vector_store = store if store is not None else _criar_store(configuracao, textos)
    modelo = llm if llm is not None else _criar_llm(configuracao)
    historicos = memoria or MemoriaPorSessao()
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    def preparar(dados: dict[str, Any]) -> dict[str, Any]:
        documentos = retriever.invoke(dados["pergunta"])
        dados["contexto"] = "\n\n".join(documento.page_content for documento in documentos)
        return dados

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Você é um assistente prestativo. Responda em português do Brasil com base no contexto. "
            "Se o contexto não responder à pergunta, diga isso claramente.\n\n"
            "Contexto:\n{contexto}",
        ),
        MessagesPlaceholder(variable_name="history", optional=True),
        ("human", "{pergunta}"),
    ])
    chain = RunnablePassthrough.assign(contexto=RunnableLambda(preparar)) | prompt | modelo | StrOutputParser()
    return ChainComMemoria(chain, historicos)


def get_rag_chain() -> Any:
    global _chain
    if _chain is None:
        _chain = criar_chain_rag()
    return _chain


def responder(mensagem: str, session_id: str, invoke: Callable[..., Any] | None = None) -> str:
    pergunta = str(mensagem or "").strip()
    sessao = str(session_id or "").strip()
    if not pergunta:
        raise ValueError("A pergunta não pode ser vazia")
    if not sessao:
        raise ValueError("session_id não pode ser vazio")
    executor = invoke or get_rag_chain().invoke
    resposta = executor(
        {"pergunta": pergunta},
        config={"configurable": {"session_id": sessao}},
    )
    return str(resposta)
