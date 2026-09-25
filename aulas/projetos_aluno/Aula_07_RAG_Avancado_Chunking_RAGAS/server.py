"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 07 — RAG Avançado: Chunking, Reranking e RAGAS
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8007     (ou: ./run_web.sh)
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
    title="Aula 07 — RAG Avançado: Chunking, Reranking e RAGAS",
    description="Interface web do exercício de RAG avançado.",
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
# Modelos de requisição
# ─────────────────────────────────────────────────────────────
class TextoBody(BaseModel):
    texto: str


class ConsultaBody(BaseModel):
    consulta: str


# ─────────────────────────────────────────────────────────────
# Endpoints da API
# ─────────────────────────────────────────────────────────────
@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        base = _info_falha(_ERRO_CARGA)
        base["pendentes"].append("Dica: " + "langchain.retrievers/langchain.storage não existem no LangChain 1.x; use LangChain 0.3.x (ex.: pip install langchain==0.3.29) ou o ambiente FIAP AI Lab para esta aula.")
        return base
    pendentes = _pendentes(ex, {
        "demo_semantic_chunker": "demo_semantic_chunker()",
        "demo_parent_retriever": "demo_parent_retriever()",
        "demo_reranker": "demo_reranker()",
        "avaliar_com_ragas": "avaliar_com_ragas()",
    })
    return {
        "nome": "Aula 07 — RAG Avançado: Chunking, Reranking e RAGAS",
        "modulo": "Módulo 2 · RAG / Embeddings",
        "descricao": (
            "Melhore a qualidade do RAG com chunking semântico (SemanticChunker), "
            "recuperação em dois níveis (ParentDocumentRetriever), reranking com "
            "cross-encoder e avaliação com RAGAS.\n\nObs.: reranker exige "
            "sentence-transformers; RAGAS exige ragas/datasets."
        ),
        "modo": "acoes",
        "implementado": not pendentes,
        "pendentes": pendentes,
        "parametros": [],
        "acoes": [
            {"endpoint": "/api/semantic_chunker", "titulo": "Chunking semântico",
             "descricao": "Divide o texto por similaridade de significado (não por tamanho fixo).",
             "metodo": "POST",
             "params": [{"nome": "texto", "label": "Texto", "tipo": "textarea", "linhas": 3,
                         "padrao": "Aprendizado de máquina é um subcampo da inteligência artificial. Modelos de linguagem são treinados em grandes volumes de texto. Prompt engineering é a arte de escrever boas instruções. RAG adiciona contexto externo para melhorar as respostas."}]},
            {"endpoint": "/api/parent_retriever", "titulo": "ParentDocumentRetriever",
             "descricao": "Chunks pequenos recuperam o bloco-pai (mais contexto).",
             "metodo": "POST",
             "params": [{"nome": "consulta", "label": "Consulta", "tipo": "texto", "padrao": "como evitar alucinações?"}]},
            {"endpoint": "/api/reranker", "titulo": "Reranking (cross-encoder)",
             "descricao": "Reordena os documentos recuperados por relevância (opcional).",
             "metodo": "POST",
             "params": [{"nome": "consulta", "label": "Consulta", "tipo": "texto", "padrao": "o que é LangGraph?"}]},
            {"endpoint": "/api/avaliar_ragas", "titulo": "Avaliar com RAGAS",
             "descricao": "Avalia faithfulness e answer_relevancy num dataset de exemplo (opcional).",
             "metodo": "POST", "params": []},
        ],
    }


@app.post("/api/semantic_chunker")
def semantic_chunker(corpo: TextoBody):
    ex = _get_exercicio()
    try:
        chunker = ex.SemanticChunker(ex.embeddings)
        chunks = chunker.split_text(corpo.texto)
        return {"tipo": "lista",
                "conteudo": [{"titulo": f"chunk {i}", "texto": c.strip()} for i, c in enumerate(chunks, 1)]}
    except ImportError as e:
        return {"tipo": "erro", "conteudo": f"Dependência ausente ({e}). Instale: pip install langchain-experimental"}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro no chunking semântico: {e}")


@app.post("/api/parent_retriever")
def parent_retriever(corpo: ConsultaBody):
    ex = _get_exercicio()
    try:
        splitter_pai = ex.RecursiveCharacterTextSplitter(chunk_size=1000)
        splitter_filho = ex.RecursiveCharacterTextSplitter(chunk_size=200)
        client = ex.chromadb.PersistentClient(path="./chroma_db")
        vectorstore = ex.Chroma(client=client, collection_name="aula07_parent",
                                embedding_function=ex.embeddings)
        retriever = ex.ParentDocumentRetriever(
            vectorstore=vectorstore,
            docstore=ex.InMemoryStore(),
            child_splitter=splitter_filho,
            parent_splitter=splitter_pai,
        )
        retriever.add_documents(ex.DOCUMENTOS)
        resultados = retriever.invoke(corpo.consulta)
        return {"tipo": "lista",
                "conteudo": [{"titulo": f"Resultado {i}", "texto": d.page_content}
                             for i, d in enumerate(resultados, 1)]}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro no ParentDocumentRetriever: {e}")


@app.post("/api/reranker")
def reranker(corpo: ConsultaBody):
    ex = _get_exercicio()
    try:
        from langchain_community.cross_encoders import HuggingFaceCrossEncoder
        from langchain.retrievers.document_compressors import CrossEncoderReranker
        from langchain.retrievers import ContextualCompressionRetriever

        client = ex.chromadb.PersistentClient(path="./chroma_db")
        vectorstore = ex.Chroma(client=client, collection_name="aula07_rerank",
                                embedding_function=ex.embeddings)
        vectorstore.add_documents(ex.DOCUMENTOS)

        modelo = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
        compressor = CrossEncoderReranker(model=modelo, top_n=3)
        retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
        )
        resultados = retriever.invoke(corpo.consulta)
        return {"tipo": "lista",
                "conteudo": [{"titulo": f"Resultado {i}", "texto": d.page_content}
                             for i, d in enumerate(resultados, 1)]}
    except ImportError as e:
        return {"tipo": "erro",
                "conteudo": f"Dependência ausente ({e}). Instale: pip install sentence-transformers"}
    except Exception as e:  # noqa: BLE001
        return {"tipo": "erro", "conteudo": f"Falha no reranking: {e}"}


@app.post("/api/avaliar_ragas")
def avaliar_ragas():
    ex = _get_exercicio()
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy
        from ragas.llms import LangchainLLMWrapper

        llm = ex.ChatOllama(model=ex.OLLAMA_MODEL, base_url=ex.OLLAMA_HOST, temperature=0)
        llm_avaliador = LangchainLLMWrapper(llm)

        dataset = Dataset.from_dict({
            "question": ["O que é RAG?"],
            "answer": ["RAG combina recuperação de documentos com geração de texto."],
            "contexts": [["RAG combina recuperação de documentos com geração de texto."]],
            "ground_truth": ["RAG é retrieval-augmented generation."],
        })

        resultado = evaluate(dataset, metrics=[faithfulness, answer_relevancy],
                             llm=llm_avaliador, embeddings=ex.embeddings)
        df = resultado.to_pandas()
        return {"tipo": "json", "conteudo": df.to_dict(orient="records")}
    except ImportError as e:
        return {"tipo": "erro",
                "conteudo": f"Dependência ausente ({e}). Instale: pip install ragas datasets"}
    except Exception as e:  # noqa: BLE001
        return {"tipo": "erro",
                "conteudo": f"Avaliação RAGAS pulada: {e}. Confira a versão do ragas instalada."}


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