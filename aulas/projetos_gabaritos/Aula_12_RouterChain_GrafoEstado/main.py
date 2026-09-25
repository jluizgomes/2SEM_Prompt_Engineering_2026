"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 12 — Router Chain e Grafo de Estado

Projeto local: rotear uma pergunta para a chain correta conforme a
intenção (com Pydantic + RunnableLambda) e introduzir o conceito de
grafo de estado que será aprofundado no LangGraph (Aula 13).
"""
from __future__ import annotations

import os
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda


@dataclass(frozen=True)
class Configuracao:
    host: str
    api_key: str
    model: str
    embedding_host: str
    embedding_model: str


class Intencao(BaseModel):
    """Classifica a intenção da pergunta do usuário."""

    categoria: str = Field(description="Uma de: 'documentos', 'calculo' ou 'geral'")


CATEGORIAS = ("documentos", "calculo", "geral")
configuracao: Configuracao | None = None
llm = None
vectorstore = None
classificador = None
chain_documentos = None
chain_calculo = None
chain_geral = None
chains = None

INICIALIZACAO_LOCK = threading.RLock()
CHROMA_PATH = Path(__file__).resolve().parent / "chroma_db"
DOCUMENTOS = (
    ("a12-endereco", "A FIAP fica na Avenida Paulista, em São Paulo."),
    ("a12-vestibular", "O vestibular da FIAP acontece duas vezes por ano."),
)
classificador_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Classifique a pergunta do usuário. Responda SOMENTE em JSON "
            "com a chave 'categoria', cujo valor é 'documentos', 'calculo' ou 'geral'.",
        ),
        ("human", "{pergunta}"),
    ]
)


def obter_configuracao() -> Configuracao:
    global configuracao
    if configuracao is not None:
        return configuracao
    with INICIALIZACAO_LOCK:
        if configuracao is None:
            from dotenv import load_dotenv

            load_dotenv(Path(__file__).with_name(".env"))
            api_key = os.getenv("OLLAMA_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError(
                    "OLLAMA_API_KEY não encontrada. Copie .env.example para .env e preencha a chave."
                )
            host = os.getenv("OLLAMA_HOST", "https://ollama.com").strip()
            model = os.getenv("OLLAMA_MODEL", "gpt-oss:120b").strip()
            embedding_host = os.getenv(
                "EMBEDDING_OLLAMA_HOST", "http://localhost:11434"
            ).strip()
            embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text").strip()
            os.environ["OLLAMA_HOST"] = host
            os.environ["OLLAMA_API_KEY"] = api_key
            os.environ["EMBEDDING_OLLAMA_HOST"] = embedding_host
            configuracao = Configuracao(
                host,
                api_key,
                model,
                embedding_host,
                embedding_model,
            )
    return configuracao


def normalizar_categoria(categoria: object) -> str:
    if not isinstance(categoria, str):
        raise ValueError("categoria deve ser um texto")
    sem_acento = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", categoria.strip().casefold())
        if not unicodedata.combining(caractere)
    )
    if sem_acento not in CATEGORIAS:
        raise ValueError(f"categoria inválida: {categoria!r}")
    return sem_acento


def obter_llm():
    global llm
    if llm is not None:
        return llm
    with INICIALIZACAO_LOCK:
        if llm is None:
            from langchain_ollama import ChatOllama

            config = obter_configuracao()
            llm = ChatOllama(
                model=config.model,
                base_url=config.host,
                temperature=0,
            )
    return llm


def criar_embeddings(config: Configuracao):
    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(
        model=config.embedding_model,
        base_url=config.embedding_host,
    )


def garantir_documentos(vectorstore_atual) -> None:
    ids = [identificador for identificador, _ in DOCUMENTOS]
    resultado = vectorstore_atual.get(ids=ids)
    ids_existentes = set(resultado.get("ids") or []) if isinstance(resultado, dict) else set()
    faltantes = [
        (identificador, conteudo)
        for identificador, conteudo in DOCUMENTOS
        if identificador not in ids_existentes
    ]
    if not faltantes:
        return
    from langchain_core.documents import Document

    vectorstore_atual.add_documents(
        [Document(page_content=conteudo) for _, conteudo in faltantes],
        ids=[identificador for identificador, _ in faltantes],
    )


def obter_vectorstore():
    global vectorstore
    if vectorstore is not None:
        return vectorstore
    with INICIALIZACAO_LOCK:
        if vectorstore is None:
            import chromadb
            from langchain_chroma import Chroma

            config = obter_configuracao()
            client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            store_atual = Chroma(
                client=client,
                collection_name="aula12",
                embedding_function=criar_embeddings(config),
            )
            garantir_documentos(store_atual)
            vectorstore = store_atual
    return vectorstore


def criar_classificador(model):
    return classificador_prompt | model.with_structured_output(Intencao)


def obter_classificador():
    global classificador
    if classificador is None:
        classificador = criar_classificador(obter_llm())
    return classificador


def criar_chains(retriever, model):
    chain_documentos_atual = (
        {
            "contexto": retriever,
            "pergunta": RunnableLambda(lambda entrada: entrada["pergunta"]),
        }
        | ChatPromptTemplate.from_messages(
            [
                ("system", "Responda com base no contexto:\n{contexto}"),
                ("human", "{pergunta}"),
            ]
        )
        | model
        | StrOutputParser()
    )
    chain_calculo_atual = (
        ChatPromptTemplate.from_messages(
            [
                ("system", "Você é uma calculadora. Resolva a conta e responda só o número."),
                ("human", "{pergunta}"),
            ]
        )
        | model
        | StrOutputParser()
    )
    chain_geral_atual = (
        ChatPromptTemplate.from_messages(
            [
                ("system", "Responda de forma geral e objetiva."),
                ("human", "{pergunta}"),
            ]
        )
        | model
        | StrOutputParser()
    )
    return chain_documentos_atual, chain_calculo_atual, chain_geral_atual


def obter_chains():
    global chain_documentos, chain_calculo, chain_geral, chains
    if chains is None:
        chain_documentos, chain_calculo, chain_geral = criar_chains(
            obter_vectorstore().as_retriever(search_kwargs={"k": 2}),
            obter_llm(),
        )
        chains = (chain_documentos, chain_calculo, chain_geral)
    return chains


def _categoria_da_intencao(intencao: Any) -> str:
    if isinstance(intencao, dict):
        valor = intencao.get("categoria")
    else:
        valor = getattr(intencao, "categoria", None)
    return normalizar_categoria(valor)


def rotear(entrada: dict[str, Any]) -> dict[str, str]:
    if not isinstance(entrada, dict):
        raise TypeError("entrada deve ser um dicionário")
    pergunta = entrada.get("pergunta")
    if not isinstance(pergunta, str) or not pergunta.strip():
        raise ValueError("pergunta inválida")
    categoria = _categoria_da_intencao(obter_classificador().invoke(entrada))
    chain_por_categoria = dict(zip(CATEGORIAS, obter_chains()))
    resposta = chain_por_categoria[categoria].invoke(entrada)
    return {"categoria": categoria, "resposta": str(resposta)}


router = RunnableLambda(rotear)


def main() -> None:
    config = obter_configuracao()
    print(
        f"Ollama Cloud | modelo: {config.model} | "
        f"embeddings locais: {config.embedding_model}\n"
    )
    for pergunta in [
        "Onde fica a FIAP?",
        "Quanto é 12 vezes 8?",
        "Me dê uma dica para estudar melhor.",
    ]:
        resultado = router.invoke({"pergunta": pergunta})
        print(f"P: {pergunta}")
        print(f"R: {resultado['resposta']}\n")


if __name__ == "__main__":
    main()
