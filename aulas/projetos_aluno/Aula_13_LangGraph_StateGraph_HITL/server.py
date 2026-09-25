"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 13 — LangGraph: StateGraph e Human-in-the-Loop
Interface web mínima (FastAPI) para o exercício.

Como rodar (a partir DESTA pasta):
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8013     (ou: ./run_web.sh)
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
# Estado do grafo (um grafo por thread, em memória)
# ─────────────────────────────────────────────────────────────
_GRAFOS = {}  # thread_id -> {"grafo": ..., "config": ...}


def _nos_implementados(ex):
    return not any(
        _eh_stub(getattr(ex, n, None))
        for n in ("node_buscar", "node_responder", "decidir_continuar")
    )


def _montar_grafo(ex, thread_id: str):
    builder = ex.StateGraph(ex.Estado)
    builder.add_node("buscar", ex.node_buscar)
    builder.add_node("responder", ex.node_responder)
    builder.add_edge(ex.START, "buscar")
    builder.add_conditional_edges("buscar", ex.decidir_continuar, {"responder": "responder"})
    builder.add_edge("responder", ex.END)
    checkpointer = ex.MemorySaver()
    grafo = builder.compile(checkpointer=checkpointer, interrupt_before=["responder"])
    config = {"configurable": {"thread_id": thread_id}}
    return grafo, config


def _get_grafo(ex, thread_id: str):
    if thread_id not in _GRAFOS:
        _GRAFOS[thread_id] = _montar_grafo(ex, thread_id)
    return _GRAFOS[thread_id]


# ─────────────────────────────────────────────────────────────
# Modelos de requisição
# ─────────────────────────────────────────────────────────────
class IniciarBody(BaseModel):
    pergunta: str
    thread_id: str = "web_demo"


class ThreadBody(BaseModel):
    thread_id: str = "web_demo"


# ─────────────────────────────────────────────────────────────
# Endpoints da API
# ─────────────────────────────────────────────────────────────
@app.get("/api/info")
def info():
    ex = _get_exercicio_lenient()
    if ex is None:
        return _info_falha(_ERRO_CARGA)
    pendentes = _pendentes(ex, {
        "node_buscar": "node_buscar()",
        "node_responder": "node_responder()",
        "decidir_continuar": "decidir_continuar()",
    })
    return {
        "nome": "Aula 13 — LangGraph: StateGraph e Human-in-the-Loop",
        "modulo": "Módulo 4 · LangGraph / Spec-Driven",
        "descricao": (
            "Grafo de estado com LangGraph: o nó 'buscar' consulta a web e o grafo "
            "PAUSA antes de 'responder' (HITL). Você revisa e aprova para o grafo "
            "concluir a resposta."
        ),
        "modo": "acoes",
        "implementado": not pendentes,
        "pendentes": pendentes,
        "parametros": [],
        "acoes": [
            {"endpoint": "/api/iniciar", "titulo": "Iniciar pesquisa (HITL)",
             "descricao": "Executa o grafo até pausar antes do nó 'responder'.",
             "metodo": "POST",
             "params": [{"nome": "pergunta", "label": "Pergunta", "tipo": "texto",
                         "padrao": "Quais são as novidades de IA em 2026?"}]},
            {"endpoint": "/api/estado", "titulo": "Ver estado atual",
             "descricao": "Mostra o checkpoint atual do grafo (thread web_demo).",
             "metodo": "POST", "params": []},
            {"endpoint": "/api/mermaid", "titulo": "Grafo (mermaid)",
             "descricao": "Desenho do grafo compilado em sintaxe Mermaid.",
             "metodo": "POST", "params": []},
        ],
        "aprovacao_endpoint": "/api/aprovar",
    }


@app.post("/api/iniciar")
def iniciar(corpo: IniciarBody):
    ex = _get_exercicio()
    if not _nos_implementados(ex):
        return {"tipo": "erro",
                "conteudo": ("TODO não implementado: complete node_buscar(), "
                             "node_responder() e decidir_continuar() no main.py "
                             "para habilitar o HITL.")}
    try:
        grafo, config = _get_grafo(ex, corpo.thread_id)
        grafo.invoke({"mensagens": [ex.HumanMessage(content=corpo.pergunta)]}, config=config)
        estado = grafo.get_state(config)
        return {
            "tipo": "texto",
            "conteudo": (f"Grafo pausado em {list(estado.next)} — aguardando sua "
                         "aprovação antes de gerar a resposta (HITL)."),
            "extra": {"proximo": list(estado.next), "thread_id": corpo.thread_id},
            "aprovacao_pendente": True,
            "aprovacao_titulo": "Aprovar resposta (HITL)",
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao iniciar o grafo: {e}")


@app.post("/api/aprovar")
def aprovar(corpo: ThreadBody):
    ex = _get_exercicio()
    if not _nos_implementados(ex):
        return {"tipo": "erro",
                "conteudo": "TODO não implementado: complete os nós do grafo no main.py."}
    try:
        grafo, config = _get_grafo(ex, corpo.thread_id)
        grafo.invoke(None, config=config)  # None = continua do checkpoint
        estado = grafo.get_state(config)
        mensagens = estado.values.get("mensagens", [])
        ultima = mensagens[-1] if mensagens else None
        return {"tipo": "texto", "conteudo": str(getattr(ultima, "content", "(sem resposta)"))}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao aprovar/retomar: {e}")


@app.post("/api/estado")
def estado(corpo: ThreadBody):
    ex = _get_exercicio()
    if not _nos_implementados(ex):
        return {"tipo": "erro", "conteudo": "TODO não implementado: complete os nós do grafo no main.py."}
    try:
        grafo, config = _get_grafo(ex, corpo.thread_id)
        estado = grafo.get_state(config)
        valores = dict(estado.values)
        # não expor mensagens inteiras; mostra resumo
        resumo = {}
        for k, v in valores.items():
            if k == "mensagens" and isinstance(v, list):
                resumo[k] = [str(m.content) for m in v]
            else:
                resumo[k] = str(v)
        return {"tipo": "json", "conteudo": {"proximo": list(estado.next), "valores": resumo}}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao ler estado: {e}")


@app.post("/api/mermaid")
def mermaid(corpo: ThreadBody):
    ex = _get_exercicio()
    if not _nos_implementados(ex):
        return {"tipo": "erro", "conteudo": "TODO não implementado: complete os nós do grafo no main.py."}
    try:
        builder = ex.StateGraph(ex.Estado)
        builder.add_node("buscar", ex.node_buscar)
        builder.add_node("responder", ex.node_responder)
        builder.add_edge(ex.START, "buscar")
        builder.add_conditional_edges("buscar", ex.decidir_continuar, {"responder": "responder"})
        builder.add_edge("responder", ex.END)
        grafo = builder.compile(checkpointer=ex.MemorySaver(), interrupt_before=["responder"])
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