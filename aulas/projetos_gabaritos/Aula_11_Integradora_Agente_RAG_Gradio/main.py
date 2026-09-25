"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 11 — Integradora: Agente + RAG + Gradio

Projeto local: o agente usa o RAG como UMA tool nativa (create_retriever_tool),
junto com busca na web e calculadora, tudo exposto numa interface Gradio.
"""
from __future__ import annotations

import ast
import math
import operator
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_core.tools import tool


@dataclass(frozen=True)
class Configuracao:
    host: str
    api_key: str
    model: str
    embedding_host: str
    embedding_model: str


configuracao: Configuracao | None = None
llm = None
vectorstore = None
retriever_tool = None
web_tool = None
tools = None
agent = None

INICIALIZACAO_LOCK = threading.RLock()
CHROMA_PATH = Path(__file__).resolve().parent / "chroma_db"
DOCUMENTOS = (
    ("a11-endereco", "A FIAP fica na Avenida Paulista, em São Paulo."),
    ("a11-duracao-curso", "O curso de Ciência da Computação tem 4 anos de duração."),
    ("a11-prompt-engineering", "Prompt engineering é escrever instruções eficazes para LLMs."),
)
OPERACOES = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
MAX_EXPRESSAO = 200
MAX_NUMERO = 10**12
MAX_RESULTADO = 10**24
MAX_EXPONENTE = 10


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
                collection_name="aula11",
                embedding_function=criar_embeddings(config),
            )
            garantir_documentos(store_atual)
            vectorstore = store_atual
    return vectorstore


def criar_busca_documentos(retriever):
    from langchain_core.tools.retriever import create_retriever_tool

    return create_retriever_tool(
        retriever,
        name="buscar_nos_documentos",
        description="Busca em documentos internos da FIAP. Use para perguntas sobre a instituição.",
    )


def obter_retriever_tool():
    global retriever_tool
    if retriever_tool is None:
        retriever = obter_vectorstore().as_retriever(search_kwargs={"k": 2})
        retriever_tool = criar_busca_documentos(retriever)
    return retriever_tool


def _resolver_no(no: ast.AST) -> int | float:
    if isinstance(no, ast.Expression):
        return _resolver_no(no.body)
    if isinstance(no, ast.Constant):
        if type(no.value) not in (int, float) or abs(no.value) > MAX_NUMERO:
            raise ValueError("número inválido")
        if isinstance(no.value, float) and not math.isfinite(no.value):
            raise ValueError("número inválido")
        return no.value
    if isinstance(no, ast.UnaryOp):
        valor = _resolver_no(no.operand)
        if isinstance(no.op, ast.USub):
            return -valor
        if isinstance(no.op, ast.UAdd):
            return +valor
        raise ValueError("operador não permitido")
    if isinstance(no, ast.BinOp):
        operation = OPERACOES.get(type(no.op))
        if operation is None:
            raise ValueError("operador não permitido")
        esquerda = _resolver_no(no.left)
        direita = _resolver_no(no.right)
        if isinstance(no.op, ast.Pow) and abs(direita) > MAX_EXPONENTE:
            raise ValueError("expoente muito grande")
        resultado = operation(esquerda, direita)
        if isinstance(resultado, float) and not math.isfinite(resultado):
            raise ValueError("resultado inválido")
        if abs(resultado) > MAX_RESULTADO:
            raise ValueError("resultado muito grande")
        return resultado
    raise ValueError("expressão não permitida")


@tool
def calcular(expressao: str) -> str:
    """Calcula uma expressão matemática simples."""
    if not isinstance(expressao, str) or not expressao.strip() or len(expressao) > MAX_EXPRESSAO:
        return "Erro: expressão inválida."
    try:
        resultado = _resolver_no(ast.parse(expressao, mode="eval"))
    except (ArithmeticError, SyntaxError, TypeError, ValueError) as erro:
        return f"Erro: {erro}"
    return f"Resultado: {resultado}"


def busca_na_web(consulta: str) -> str:
    from ddgs import DDGS

    resultados = DDGS().text(consulta, max_results=5)
    linhas = [
        f"{item.get('title', '')}: {item.get('body', item.get('description', ''))}"
        for item in resultados
    ]
    return "\n".join(linhas) if linhas else "Nenhum resultado encontrado."


def obter_web_tool():
    global web_tool
    if web_tool is None:
        web_tool = tool(
            busca_na_web,
            name="busca_na_web",
            description="Busca na web por informações atuais.",
        )
    return web_tool


def obter_tools():
    global tools
    if tools is None:
        tools = [obter_retriever_tool(), calcular, obter_web_tool()]
    return tools


def criar_agente(model, ferramentas):
    return create_agent(
        model=model,
        tools=ferramentas,
        system_prompt="Responda em português e use as ferramentas disponíveis quando necessário.",
    )


def obter_agente():
    global agent
    if agent is None:
        agent = criar_agente(obter_llm(), obter_tools())
    return agent


def _validar_historico(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    if history is None:
        return []
    if not isinstance(history, list):
        raise TypeError("histórico deve ser uma lista de mensagens")
    mensagens = []
    for item in history:
        if not isinstance(item, dict):
            raise TypeError("histórico deve usar mensagens no formato de dicionário")
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant", "system"}:
            raise ValueError("papel de mensagem inválido")
        if not isinstance(content, (str, list, dict)):
            raise TypeError("conteúdo de mensagem deve ser texto ou blocos de texto")
        mensagens.append({"role": role, "content": _texto_do_conteudo(content)})
    return mensagens


def _texto_do_conteudo(conteudo: Any) -> str:
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, dict):
        texto = conteudo.get("text") or conteudo.get("content")
        return _texto_do_conteudo(texto) if texto is not None else ""
    if not isinstance(conteudo, list):
        return ""
    partes = []
    for item in conteudo:
        if isinstance(item, (str, list, dict)):
            partes.append(_texto_do_conteudo(item))
    return "".join(partes)


def extrair_resposta(resultado: Any) -> str:
    if not isinstance(resultado, dict) or not isinstance(resultado.get("messages"), list):
        raise ValueError("resposta do agente inválida")
    for mensagem in reversed(resultado["messages"]):
        conteudo = (
            mensagem.get("content")
            if isinstance(mensagem, dict)
            else getattr(mensagem, "content", None)
        )
        texto = _texto_do_conteudo(conteudo)
        if texto:
            return texto
    raise ValueError("agente não retornou texto")


def responder(mensagem: str, history: list[dict[str, Any]] | None) -> str:
    mensagens = _validar_historico(history)
    if not isinstance(mensagem, str) or not mensagem.strip():
        raise ValueError("mensagem inválida")
    mensagens.append({"role": "user", "content": mensagem.strip()})
    resultado = obter_agente().invoke({"messages": mensagens})
    return extrair_resposta(resultado)


def main() -> None:
    config = obter_configuracao()
    obter_agente()
    import gradio as gr

    print(f"Ollama Cloud | modelo: {config.model} | embeddings: {config.embedding_model}")
    print("Abrindo interface Gradio em http://localhost:7860 ...")
    demo = gr.ChatInterface(
        fn=responder,
        title="Agente FIAP — Aula 11 (RAG + Tools)",
        description="Pergunte sobre a FIAP (RAG), peça contas (calculadora) ou algo atual (web).",
    )
    demo.launch(theme="soft")


if __name__ == "__main__":
    main()
