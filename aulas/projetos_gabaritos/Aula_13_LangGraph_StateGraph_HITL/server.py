"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 13 — LangGraph: StateGraph e Human-in-the-Loop
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8113
"""
import importlib.util
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

app = FastAPI(
    title="Aula 13 — LangGraph: StateGraph e HITL",
    description="Interface web do exercício de LangGraph com Human-in-the-Loop.",
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
        "descricao": "Não foi possível carregar o main.py deste exercício.",
        "modo": "acoes",
        "implementado": False,
        "pendentes": [f"main.py não pôde ser importado: {erro}"],
        "parametros": [],
        "acoes": [],
    }


# ─────────────────────────────────────────────────────────────
# Estado do grafo (um grafo e um checkpoint por thread)
# ─────────────────────────────────────────────────────────────
_GRAFOS = {}


def _montar_grafo(ex, thread_id: str):
    thread_id, config = ex.configuracao_thread(thread_id)
    grafo = ex.criar_grafo(ex.MemorySaver())
    return grafo, config


def _get_grafo(ex, thread_id: str):
    if thread_id not in _GRAFOS:
        _GRAFOS[thread_id] = _montar_grafo(ex, thread_id)
    return _GRAFOS[thread_id]


def _obter_grafo(ex, thread_id: str):
    if thread_id not in _GRAFOS:
        raise HTTPException(404, f"Thread HITL não encontrada: {thread_id}")
    return _GRAFOS[thread_id]


# ─────────────────────────────────────────────────────────────
# Modelos de requisição
# ─────────────────────────────────────────────────────────────
class IniciarBody(BaseModel):
    pergunta: str
    thread_id: str | None = None


class ThreadBody(BaseModel):
    thread_id: str | None = None


# ─────────────────────────────────────────────────────────────
# Endpoints da API
# ─────────────────────────────────────────────────────────────
@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        return _info_falha(_ERRO_CARGA)
    return {
        "nome": "Aula 13 — LangGraph: StateGraph e Human-in-the-Loop",
        "modulo": "Módulo 4 · LangGraph / Spec-Driven",
        "descricao": (
            "Grafo de estado com LangGraph: o nó 'buscar' consulta a web e o grafo "
            "PAUSA antes de 'responder' (HITL). Você revisa os resultados e aprova "
            "para o grafo concluir a resposta."
        ),
        "modo": "acoes",
        "implementado": True,
        "pendentes": [],
        "parametros": [],
        "acoes": [
            {"endpoint": "/api/iniciar", "titulo": "Iniciar pesquisa (HITL)",
             "descricao": "Cria uma thread isolada e pausa antes de gerar a resposta.",
             "metodo": "POST",
             "params": [{"nome": "pergunta", "label": "Pergunta", "tipo": "texto",
                         "padrao": "Quais são as novidades de IA em 2026?"}]},
            {"endpoint": "/api/estado", "titulo": "Ver estado atual",
             "descricao": "Mostra o checkpoint da thread HITL enviada na requisição.",
             "metodo": "POST", "params": [{"nome": "thread_id", "label": "Thread ID", "tipo": "texto", "padrao": ""}]},
            {"endpoint": "/api/mermaid", "titulo": "Grafo (mermaid)",
             "descricao": "Desenho do grafo compilado em sintaxe Mermaid.",
             "metodo": "POST", "params": []},
        ],
        "aprovacao_endpoint": "/api/aprovar",
    }


@app.post("/api/iniciar")
def iniciar(corpo: IniciarBody):
    ex = _get_exercicio()
    thread_id, _ = ex.configuracao_thread(corpo.thread_id)
    if thread_id in _GRAFOS:
        raise HTTPException(409, "Esta thread já possui uma execução; inicie uma nova thread.")
    try:
        grafo, config = _get_grafo(ex, thread_id)
        grafo.invoke(
            {"mensagens": [ex.HumanMessage(content=corpo.pergunta.strip())]},
            config=config,
        )
        estado = grafo.get_state(config)
        return ex.resposta_revisao(estado, thread_id)
    except ex.AprovacaoInvalida as e:
        _GRAFOS.pop(thread_id, None)
        raise HTTPException(422, str(e))
    except Exception as e:  # noqa: BLE001
        _GRAFOS.pop(thread_id, None)
        raise HTTPException(500, f"Erro ao iniciar o grafo: {e}")


@app.post("/api/aprovar")
def aprovar(corpo: ThreadBody):
    ex = _get_exercicio()
    if not corpo.thread_id:
        raise HTTPException(400, "thread_id é obrigatório para retomar uma pausa HITL.")
    try:
        grafo, config = _obter_grafo(ex, corpo.thread_id)
        estado_final = ex.retomar_grafo(grafo, config)
        ultima = estado_final.values["mensagens"][-1]
        return {
            "tipo": "texto",
            "conteudo": str(getattr(ultima, "content", "")),
            "extra": {"thread_id": corpo.thread_id, "proximo": list(estado_final.next)},
            "aprovacao_pendente": False,
        }
    except HTTPException:
        raise
    except ex.AprovacaoInvalida as e:
        raise HTTPException(409, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao retomar o grafo: {e}")


@app.post("/api/estado")
def estado(corpo: ThreadBody):
    ex = _get_exercicio()
    if not corpo.thread_id:
        raise HTTPException(400, "thread_id é obrigatório para consultar o estado.")
    try:
        grafo, config = _obter_grafo(ex, corpo.thread_id)
        estado_atual = grafo.get_state(config)
        valores = dict(estado_atual.values)
        resumo = {}
        for k, v in valores.items():
            if k == "mensagens" and isinstance(v, list):
                resumo[k] = [str(m.content) for m in v]
            else:
                resumo[k] = str(v)
        return {
            "tipo": "json",
            "conteudo": {
                "thread_id": corpo.thread_id,
                "proximo": list(estado_atual.next),
                "valores": resumo,
            },
        }
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao ler estado: {e}")


@app.post("/api/mermaid")
def mermaid(corpo: ThreadBody):
    ex = _get_exercicio()
    try:
        grafo = ex.criar_grafo(ex.MemorySaver())
        return {"tipo": "texto", "conteudo": grafo.get_graph().draw_mermaid()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao desenhar o grafo: {e}")


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
