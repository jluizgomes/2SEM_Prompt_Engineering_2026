"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 06 — Pipeline RAG Completo
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8006     (ou: ./run_web.sh)
"""
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import importlib.util
import inspect
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

app = FastAPI(
    title="Aula 06 — Pipeline RAG Completo",
    description="Interface web do exercício de pipeline RAG de ponta a ponta.",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DIST = Path(__file__).resolve().parent / "frontend" / "dist"

# ─────────────────────────────────────────────────────────────
# Carga do exercício (main.py)
# ─────────────────────────────────────────────────────────────
_EXERCICIO = None
_ERRO_CARGA = None


def _carregar_main():
    caminho = Path(__file__).resolve().parent / "main.py"
    spec = importlib.util.spec_from_file_location("exercicio_main", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _get_exercicio():
    global _EXERCICIO, _ERRO_CARGA
    if _EXERCICIO is None and _ERRO_CARGA is None:
        try:
            _EXERCICIO = _carregar_main()
        except Exception as e:  # noqa: BLE001
            _ERRO_CARGA = str(e)
    if _ERRO_CARGA is not None:
        raise HTTPException(502, f"Não foi possível carregar o exercício:\n{_ERRO_CARGA}")
    return _EXERCICIO

def _get_exercicio_lenient():
    """Versão tolerante: devolve None se o main.py não puder ser importado."""
    try:
        return _get_exercicio()
    except HTTPException:
        return None


def _info_falha(erro):
    return {
        "nome": app.title,
        "modulo": "—",
        "descricao": "Não foi possível carregar o main.py deste exercício (ver pendentes).",
        "modo": "acoes",
        "implementado": False,
        "pendentes": [f"main.py não pôde ser importado: {erro}"],
        "parametros": [],
        "acoes": [],
    }



def _eh_stub(funcao) -> bool:
    if funcao is None:
        return True
    try:
        fonte = inspect.getsource(funcao)
    except (OSError, TypeError, IOError):
        return False
    fonte = re.sub(r'""".*?"""', "", fonte, flags=re.S)
    return bool(re.search(r"^\s*pass\s*$", fonte, flags=re.M))


def _pendentes(ex, nomes: dict) -> list:
    return [rotulo for nome, rotulo in nomes.items() if _eh_stub(getattr(ex, nome, None))]


# ─────────────────────────────────────────────────────────────
# Pipeline RAG (cache em processo; replica do gabarito quando o
# main.py do aluno ainda tem TODOs)
# ─────────────────────────────────────────────────────────────
_PIPELINE = None  # {"chain": ..., "n_chunks": int}


def _construir_pipeline(ex):
    """Carrega/divide/indexa/monta a chain RAG usando os objetos do main.py."""
    doc_exemplo = [
        "A FIAP é uma instituição de ensino superior localizada na Avenida Paulista, em São Paulo.",
        "O curso de Ciência da Computação forma profissionais para atuar com tecnologia e inovação.",
        "Prompt engineering é escrever instruções claras para modelos de linguagem.",
        "RAG significa Retrieval-Augmented Generation: buscar contexto e gerar resposta com base nele.",
    ]

    if not _eh_stub(getattr(ex, "carregar_documentos", None)):
        docs = ex.carregar_documentos()
    else:
        carregador = getattr(ex, "PyMuPDFLoader", None)
        data_dir = getattr(ex, "DATA_DIR", None)
        pdfs = sorted(data_dir.glob("*.pdf")) if data_dir is not None and data_dir.exists() else []
        if pdfs and carregador is not None:
            docs = []
            for pdf in pdfs:
                docs.extend(carregador(str(pdf)).load())
        else:
            docs = [getattr(ex, "Document", object)(page_content=t) for t in doc_exemplo]

    if not _eh_stub(getattr(ex, "dividir", None)):
        chunks = ex.dividir(docs)
    else:
        splitter = getattr(ex, "RecursiveCharacterTextSplitter", None)
        if splitter is None:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter
        chunks = splitter(chunk_size=500, chunk_overlap=100).split_documents(docs)

    if not _eh_stub(getattr(ex, "indexar", None)):
        vectorstore = ex.indexar(chunks)
    else:
        chromadb = getattr(ex, "chromadb", None) or __import__("chromadb")
        embeddings = getattr(ex, "OllamaEmbeddings", None)
        if embeddings is None:
            from langchain_ollama import OllamaEmbeddings
            embeddings = OllamaEmbeddings
        chroma_cls = getattr(ex, "Chroma", None)
        if chroma_cls is None:
            from langchain_community.vectorstores import Chroma as chroma_cls
        client = chromadb.PersistentClient(path="./chroma_db")
        embedding_host = getattr(
            ex, "EMBEDDING_OLLAMA_HOST", "http://localhost:11434"
        )
        vectorstore = chroma_cls(
            client=client,
            collection_name="aula06",
            embedding_function=embeddings(
                model=getattr(ex, "EMBEDDING_MODEL", "nomic-embed-text"),
                base_url=embedding_host,
            ),
        )
        vectorstore.add_documents(chunks)

    if not _eh_stub(getattr(ex, "montar_chain", None)):
        chain = ex.montar_chain(vectorstore)
    else:
        chat = getattr(ex, "ChatOllama", None)
        if chat is None:
            from langchain_ollama import ChatOllama as chat
        prompt_cls = getattr(ex, "ChatPromptTemplate", None)
        if prompt_cls is None:
            from langchain_core.prompts import ChatPromptTemplate as prompt_cls
        parser = getattr(ex, "StrOutputParser", None)
        if parser is None:
            from langchain_core.output_parsers import StrOutputParser as parser
        passthrough = getattr(ex, "RunnablePassthrough", None)
        if passthrough is None:
            from langchain_core.runnables import RunnablePassthrough as passthrough
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        prompt = prompt_cls.from_messages([
            ("system", "Responda a pergunta APENAS com base no contexto abaixo. "
                       "Se não houver informação, diga que não sabe.\n\nContexto:\n{contexto}"),
            ("human", "Pergunta: {pergunta}"),
        ])
        llm = chat(model=getattr(ex, "OLLAMA_MODEL", "gpt-oss:120b"),
                   base_url=getattr(ex, "OLLAMA_HOST", "https://ollama.com"), temperature=0.2)
        chain = (
            {"contexto": retriever, "pergunta": passthrough()}
            | prompt | llm | parser()
        )

    return {"chain": chain, "n_chunks": len(chunks)}


def _get_pipeline(ex):
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = _construir_pipeline(ex)
    return _PIPELINE



def _envelope_erro(mensagem: str, **extra) -> dict:
    return {"tipo": "erro", "conteudo": mensagem, **extra}

def _erro_embeddings(erro, acao: str) -> dict:
    msg = str(erro).lower()
    if any(marca in msg for marca in ("connection", "connect", "unreachable", "11434")):
        return _envelope_erro(
            f"Não foi possível {acao}: verifique o Ollama local em EMBEDDING_OLLAMA_HOST, "
            "o modelo de embeddings e a OLLAMA_API_KEY usada pelo Ollama Cloud."
        )
    return _envelope_erro(f"Erro ao {acao}: {erro}")


# ─────────────────────────────────────────────────────────────
# Modelos de requisição
# ─────────────────────────────────────────────────────────────
class PerguntaBody(BaseModel):
    mensagem: str


# ─────────────────────────────────────────────────────────────
# Endpoints da API
# ─────────────────────────────────────────────────────────────
@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        return _info_falha(_ERRO_CARGA)
    pendentes = _pendentes(ex, {
        "carregar_documentos": "carregar_documentos()",
        "dividir": "dividir()",
        "indexar": "indexar()",
        "montar_chain": "montar_chain()",
    })
    return {
        "nome": "Aula 06 — Pipeline RAG Completo",
        "modulo": "Módulo 2 · RAG / Embeddings",
        "descricao": (
            "RAG de ponta a ponta: carrega PDFs de ./data/ (ou texto de exemplo), divide "
            "em chunks, indexa no ChromaDB e responde perguntas citando o contexto. "
            "Perguntas fora do contexto devem resultar em 'não sei'."
        ),
        "modo": "chat",
        "chat_endpoint": "/api/perguntar",
        "implementado": not pendentes,
        "pendentes": pendentes,
        "avisos": [
            "O pipeline usa embeddings locais em EMBEDDING_OLLAMA_HOST e chat no Ollama Cloud. "
            "Você também pode colocar PDFs em ./data/ para o pipeline indexá-los."
        ],
        "parametros": [],
        "acoes": [
            {"endpoint": "/api/indexar", "titulo": "Indexar pipeline RAG",
             "descricao": "Carrega documentos, divide em chunks e indexa no ChromaDB (uma vez; depois fica em cache).",
             "metodo": "POST", "params": []},
        ],
    }


@app.post("/api/indexar")
def indexar():
    ex = _get_exercicio()
    try:
        pipeline = _get_pipeline(ex)
        return {"tipo": "texto",
                "conteudo": f"Pipeline pronto: {pipeline['n_chunks']} chunks indexados."}
    except Exception as e:  # noqa: BLE001
        return _erro_embeddings(e, "montar o pipeline")


@app.post("/api/perguntar")
def perguntar(corpo: PerguntaBody):
    ex = _get_exercicio()
    try:
        pipeline = _get_pipeline(ex)
        resposta = pipeline["chain"].invoke(corpo.mensagem)
        return {"tipo": "texto", "conteudo": str(resposta)}
    except Exception as e:  # noqa: BLE001
        return _erro_embeddings(e, "perguntar ao RAG")


# ─────────────────────────────────────────────────────────────
# Frontend estático (React) — se já estiver compilado
# ─────────────────────────────────────────────────────────────
if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
else:
    @app.get("/")
    def sem_frontend():
        return {"tipo": "erro",
                "conteudo": "Frontend não compilado. Rode: cd frontend && npm install && npm run build"}