import importlib.util
import os
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from langchain_core.messages import AIMessage

RAIZ = Path(__file__).resolve().parents[1]


class ChatOllamaStub:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def invoke(self, mensagens):
        raise AssertionError("O modelo real não deve ser chamado no teste")


class DuckDuckGoSearchRunStub:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def invoke(self, consulta):
        raise AssertionError("A busca real não deve ser chamada no teste")


def carregar_main():
    modulo_chat = ModuleType("langchain_ollama")
    modulo_chat.ChatOllama = ChatOllamaStub
    modulo_comunidade = ModuleType("langchain_community")
    modulo_comunidade.__path__ = []
    modulo_tools = ModuleType("langchain_community.tools")
    modulo_tools.DuckDuckGoSearchRun = DuckDuckGoSearchRunStub
    nome = "aula13_main_teste"
    sys.modules.pop(nome, None)
    with (
        patch.dict(
            sys.modules,
            {
                "langchain_ollama": modulo_chat,
                "langchain_community": modulo_comunidade,
                "langchain_community.tools": modulo_tools,
            },
        ),
        patch.dict(
            os.environ,
            {
                "OLLAMA_API_KEY": "chave-de-teste",
                "OLLAMA_HOST": "http://modelo-invalido.test",
                "OLLAMA_MODEL": "modelo-de-teste",
            },
            clear=True,
        ),
        patch("dotenv.load_dotenv", return_value=False),
    ):
        spec = importlib.util.spec_from_file_location(nome, RAIZ / "main.py")
        modulo = importlib.util.module_from_spec(spec)
        sys.modules[nome] = modulo
        spec.loader.exec_module(modulo)
    return modulo


class BuscaFake:
    def __init__(self, resultado):
        self.resultado = resultado
        self.consultas = []

    def invoke(self, consulta):
        self.consultas.append(consulta)
        return self.resultado


class LlmFake:
    def __init__(self, resposta="resposta aprovada"):
        self.resposta = resposta
        self.entradas = []

    def invoke(self, mensagens):
        self.entradas.append(mensagens)
        return AIMessage(content=self.resposta)


class GrafoHitlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = carregar_main()

    def setUp(self):
        busca_original = self.main.busca_web
        llm_original = self.main.llm
        self.addCleanup(setattr, self.main, "busca_web", busca_original)
        self.addCleanup(setattr, self.main, "llm", llm_original)

    def test_mapa_condicional_inclui_end(self):
        mapa = self.main.mapa_decisao()
        self.assertEqual(set(mapa), {"responder", self.main.END})
        self.assertIs(mapa[self.main.END], self.main.END)

    def test_pausa_retorna_resultados_e_so_aprova_com_pausa(self):
        busca = BuscaFake("Fontes selecionadas para revisão")
        llm = LlmFake()
        self.main.busca_web = busca
        self.main.llm = llm
        thread_id, config = self.main.configuracao_thread("requisicao-a")
        grafo = self.main.criar_grafo(self.main.MemorySaver())

        grafo.invoke(
            {"mensagens": [self.main.HumanMessage(content="O que houve?")]},
            config=config,
        )
        pausado = grafo.get_state(config)
        revisao = self.main.resposta_revisao(pausado, thread_id)

        self.assertTrue(self.main.aguardando_revisao(pausado))
        self.assertIn(busca.resultado, revisao["conteudo"])
        self.assertEqual(revisao["extra"]["resultados_busca"], busca.resultado)
        self.assertTrue(revisao["aprovacao_pendente"])
        self.assertEqual(llm.entradas, [])

        final = self.main.retomar_grafo(grafo, config)
        self.assertFalse(self.main.aguardando_revisao(final))
        self.assertEqual(final.values["mensagens"][-1].content, llm.resposta)

    def test_retomada_sem_pausa_real_falha(self):
        grafo = self.main.criar_grafo(self.main.MemorySaver())
        _, config = self.main.configuracao_thread("requisicao-b")

        with self.assertRaises(self.main.AprovacaoInvalida):
            self.main.retomar_grafo(grafo, config)

    def test_busca_vazia_termina_sem_pausa(self):
        self.main.busca_web = BuscaFake("")
        self.main.llm = LlmFake()
        grafo = self.main.criar_grafo(self.main.MemorySaver())
        _, config = self.main.configuracao_thread("requisicao-c")

        grafo.invoke(
            {"mensagens": [self.main.HumanMessage(content="Sem resultados")]},
            config=config,
        )
        estado = grafo.get_state(config)

        self.assertFalse(self.main.aguardando_revisao(estado))
        self.assertEqual(tuple(estado.next or ()), ())

    def test_thread_id_padrao_e_unico_por_requisicao(self):
        primeiro_id, primeiro_config = self.main.configuracao_thread()
        segundo_id, segundo_config = self.main.configuracao_thread()

        self.assertNotEqual(primeiro_id, segundo_id)
        self.assertNotEqual(primeiro_config, segundo_config)


if __name__ == "__main__":
    unittest.main()
