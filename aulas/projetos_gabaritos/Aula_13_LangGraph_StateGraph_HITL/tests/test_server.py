import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]


class HTTPExceptionFake(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class FastAPIFake:
    def __init__(self, **kwargs):
        self.title = kwargs.get("title", "")

    def add_middleware(self, *args, **kwargs):
        return None

    def get(self, *args, **kwargs):
        return lambda funcao: funcao

    post = get

    def mount(self, *args, **kwargs):
        return None


class StaticFilesFake:
    def __init__(self, *args, **kwargs):
        pass


def carregar_server():
    fastapi = ModuleType("fastapi")
    fastapi.__path__ = []
    fastapi.FastAPI = FastAPIFake
    fastapi.HTTPException = HTTPExceptionFake
    middleware = ModuleType("fastapi.middleware")
    middleware.__path__ = []
    cors = ModuleType("fastapi.middleware.cors")
    cors.CORSMiddleware = object
    staticfiles = ModuleType("fastapi.staticfiles")
    staticfiles.StaticFiles = StaticFilesFake
    nome = "aula13_server_teste"
    sys.modules.pop(nome, None)
    with patch.dict(
        sys.modules,
        {
            "fastapi": fastapi,
            "fastapi.middleware": middleware,
            "fastapi.middleware.cors": cors,
            "fastapi.staticfiles": staticfiles,
        },
    ):
        spec = importlib.util.spec_from_file_location(nome, RAIZ / "server.py")
        modulo = importlib.util.module_from_spec(spec)
        sys.modules[nome] = modulo
        spec.loader.exec_module(modulo)
    return modulo


class MensagemFake:
    def __init__(self, content):
        self.content = content


class CheckpointFake:
    def __init__(self):
        self.deleted = []

    def delete_thread(self, thread_id):
        self.deleted.append(thread_id)


class GrafoFake:
    def __init__(self, checkpointer):
        self.checkpointer = checkpointer
        self.invocations = []

    def invoke(self, entrada, config=None):
        self.invocations.append((entrada, config))
        return {}

    def get_state(self, config):
        return SimpleNamespace(
            values={"resultados_busca": "resultados"},
            next=("responder",),
        )


class AprovacaoInvalidaFake(Exception):
    pass


class ExercicioFake:
    MemorySaver = CheckpointFake
    HumanMessage = MensagemFake
    AprovacaoInvalida = AprovacaoInvalidaFake

    def __init__(self):
        self.savers = []
        self.erro = None

    def configuracao_thread(self, thread_id=None):
        return thread_id, {"configurable": {"thread_id": thread_id}}

    def criar_grafo(self, checkpointer):
        self.savers.append(checkpointer)
        return GrafoFake(checkpointer)

    def resposta_revisao(self, estado, thread_id):
        return {
            "tipo": "texto",
            "conteudo": "revisão",
            "extra": {"thread_id": thread_id},
            "aprovacao_pendente": True,
        }

    def retomar_grafo(self, grafo, config):
        if self.erro is not None:
            raise self.erro
        return SimpleNamespace(
            values={"mensagens": [MensagemFake("resposta final")]},
            next=(),
        )


class CicloHitlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = carregar_server()

    def setUp(self):
        self.server._GRAFOS.clear()
        self.exercicio = ExercicioFake()

    def tearDown(self):
        self.server._GRAFOS.clear()

    def iniciar(self, thread_id):
        with patch.object(self.server, "_get_exercicio", return_value=self.exercicio):
            return self.server.iniciar(
                self.server.IniciarBody(pergunta="O que houve?", thread_id=thread_id)
            )

    def test_mantem_grafo_e_checkpoint_Enquanto_hitl_esta_pendente(self):
        self.iniciar("thread-pendente")

        self.assertIn("thread-pendente", self.server._GRAFOS)
        self.assertEqual(self.exercicio.savers[-1].deleted, [])

    def test_remove_grafo_e_checkpoint_apos_conclusao(self):
        self.iniciar("thread-conclusao")
        with patch.object(self.server, "_get_exercicio", return_value=self.exercicio):
            resultado = self.server.aprovar(self.server.ThreadBody(thread_id="thread-conclusao"))

        self.assertEqual(resultado["conteudo"], "resposta final")
        self.assertNotIn("thread-conclusao", self.server._GRAFOS)
        self.assertEqual(self.exercicio.savers[-1].deleted, ["thread-conclusao"])

    def test_remove_grafo_e_checkpoint_apos_erro_de_retomada(self):
        self.iniciar("thread-erro")
        self.exercicio.erro = AprovacaoInvalidaFake("pausa inválida")
        with patch.object(self.server, "_get_exercicio", return_value=self.exercicio):
            with self.assertRaises(self.server.HTTPException) as contexto:
                self.server.aprovar(self.server.ThreadBody(thread_id="thread-erro"))

        self.assertEqual(contexto.exception.status_code, 409)
        self.assertNotIn("thread-erro", self.server._GRAFOS)
        self.assertEqual(self.exercicio.savers[-1].deleted, ["thread-erro"])

    def test_limita_threads_pendentes_sem_descartar_estado_existente(self):
        with patch.object(self.server, "MAX_GRAFOS_PENDENTES", 1, create=True):
            self.server._get_grafo(self.exercicio, "thread-1")
            with self.assertRaises(self.server.HTTPException) as contexto:
                self.server._get_grafo(self.exercicio, "thread-2")

        self.assertEqual(contexto.exception.status_code, 503)
        self.assertIn("thread-1", self.server._GRAFOS)
        self.assertNotIn("thread-2", self.server._GRAFOS)


if __name__ == "__main__":
    unittest.main()
