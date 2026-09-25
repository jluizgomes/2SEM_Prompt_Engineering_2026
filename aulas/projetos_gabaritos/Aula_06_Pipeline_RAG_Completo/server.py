"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 06 — Pipeline RAG Completo
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8106
"""
import importlib.util
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
_EXERCICIO = None
_ERRO_CARGA = None
_PIPELINE = None


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
        except Exception as erro:
            _ERRO_CARGA = str(erro)
    if _ERRO_CARGA is not None:
        raise HTTPException(502, f"Não foi possível carregar o exercício:\n{_ERRO_CARGA}")
    return _EXERCICIO


def _get_exercicio_lenient():
    try:
        return _get_exercicio()
    except HTTPException:
        return None


def _info_falha(erro):
    return {
        "nome": app.title,
        "modulo": "—",
        "descricao": "Não foi possível carregar o main.py deste exercício.",
        "modo": "chat",
        "chat_endpoint": "/api/perguntar",
        "implementado": False,
        "pendentes": [f"main.py não pôde ser importado: {erro}"],
        "parametros": [],
        "acoes": [],
    }


def _construir_pipeline(exercicio, forcar_indexacao: bool = False) -> dict:
    try:
        documentos = exercicio.carregar_documentos()
        chunks = exercicio.dividir(documentos)
        store = exercicio.indexar(chunks)
        chain = exercicio.montar_chain(store)
    except AttributeError as erro:
        raise RuntimeError("O exercício não expõe o pipeline RAG completo.") from erro
    if forcar_indexacao:
        invalidar = getattr(exercicio, "invalidar_cache", None)
        if callable(invalidar):
            invalidar()
    versao = getattr(exercicio, "versao_indice", lambda: None)()
    return {
        "chain": chain,
        "n_chunks": len(chunks),
        "vectorstore": store,
        "versao": versao,
    }


def _invalidar_pipeline():
    global _PIPELINE
    _PIPELINE = None


def _get_pipeline(exercicio, forcar_indexacao: bool = False) -> dict:
    global _PIPELINE
    if _PIPELINE is None or forcar_indexacao:
        _PIPELINE = _construir_pipeline(
            exercicio,
            forcar_indexacao=forcar_indexacao,
        )
    return _PIPELINE


def _envelope_erro(mensagem: str, **extra) -> dict:
    return {"tipo": "erro", "conteudo": mensagem, **extra}


def _erro_embeddings(erro, acao: str) -> dict:
    mensagem = str(erro).lower()
    if any(marca in mensagem for marca in ("connection", "connect", "unreachable", "11434")):
        return _envelope_erro(
            f"Não foi possível {acao}: verifique o Ollama local em EMBEDDING_OLLAMA_HOST, "
            "o modelo de embeddings e a OLLAMA_API_KEY usada pelo Ollama Cloud."
        )
    return _envelope_erro(f"Erro ao {acao}: {erro}")


class PerguntaBody(BaseModel):
    mensagem: str


def _executar_rag(pipeline: dict, pergunta: str) -> tuple[str, list[dict]]:
    chain = pipeline["chain"]
    invocar_com_fontes = getattr(chain, "invoke_with_sources", None)
    if callable(invocar_com_fontes):
        resultado = invocar_com_fontes(pergunta)
        if isinstance(resultado, dict):
            return str(resultado.get("resposta", "")), list(resultado.get("fontes") or [])
    resposta = chain.invoke(pergunta)
    return str(resposta), []


@app.get("/api/info")
def info():
    exercicio = _get_exercicio_lenient()
    if exercicio is None:
        return _info_falha(_ERRO_CARGA)
    return {
        "nome": "Aula 06 — Pipeline RAG Completo",
        "modulo": "Módulo 2 · RAG / Embeddings",
        "descricao": (
            "RAG de ponta a ponta: carrega PDFs de ./data/ (ou texto de exemplo), divide "
            "em chunks, indexa no ChromaDB e responde perguntas com as fontes recuperadas."
        ),
        "modo": "chat",
        "chat_endpoint": "/api/perguntar",
        "implementado": True,
        "pendentes": [],
        "avisos": [
            "O pipeline usa embeddings (nomic-embed-text). A indexação pode ser repetida sem "
            "duplicar documentos e a resposta inclui somente as fontes recuperadas."
        ],
        "parametros": [],
        "acoes": [
            {
                "endpoint": "/api/indexar",
                "titulo": "Reindexar pipeline RAG",
                "descricao": "Carrega documentos, divide em chunks e sincroniza o ChromaDB.",
                "metodo": "POST",
                "params": [],
            }
        ],
    }


@app.post("/api/indexar")
def indexar():
    exercicio = _get_exercicio()
    try:
        pipeline = _get_pipeline(exercicio, forcar_indexacao=True)
        return {
            "tipo": "texto",
            "conteudo": f"Pipeline pronto: {pipeline['n_chunks']} chunks indexados.",
            "extra": {"versao": pipeline.get("versao")},
        }
    except Exception as erro:
        return _erro_embeddings(erro, "montar o pipeline")


@app.post("/api/perguntar")
def perguntar(corpo: PerguntaBody):
    exercicio = _get_exercicio()
    mensagem = str(corpo.mensagem or "").strip()
    if not mensagem:
        return _envelope_erro("Informe uma pergunta.")
    try:
        pipeline = _get_pipeline(exercicio)
        resposta, fontes = _executar_rag(pipeline, mensagem)
        return {
            "tipo": "texto",
            "conteudo": resposta,
            "fontes": fontes,
            "extra": {"fontes": fontes},
        }
    except Exception as erro:
        return _erro_embeddings(erro, "perguntar ao RAG")


if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
else:
    @app.get("/")
    def sem_frontend():
        return {
            "tipo": "erro",
            "conteudo": "Frontend não compilado. Rode: cd frontend && npm install && npm run build",
        }
