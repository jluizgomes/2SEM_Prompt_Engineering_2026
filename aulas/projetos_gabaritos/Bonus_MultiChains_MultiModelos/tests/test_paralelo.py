import importlib.util
import os
import sys
import threading
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from langchain_core.runnables import Runnable

RAIZ = Path(__file__).resolve().parents[1]


class ChatOllamaStub(Runnable):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def invoke(self, mensagens, config=None, **kwargs):
        raise AssertionError("O modelo real não deve ser chamado no teste")


def carregar_main():
    modulo_chat = ModuleType("langchain_ollama")
    modulo_chat.ChatOllama = ChatOllamaStub
    nome = "bonus_main_teste"
    sys.modules.pop(nome, None)
    with (
        patch.dict(sys.modules, {"langchain_ollama": modulo_chat}),
        patch.dict(
            os.environ,
            {
                "OLLAMA_API_KEY": "chave-de-teste",
                "OLLAMA_HOST": "http://modelo-invalido.test",
                "OLLAMA_MODEL": "modelo-primario-de-teste",
                "OLLAMA_MODEL_SECUNDARIO": "modelo-secundario-de-teste",
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


class ChainFake:
    def __init__(self, resposta=None, erro=None, barreira=None):
        self.resposta = resposta
        self.erro = erro
        self.barreira = barreira
        self.entradas = []

    def invoke(self, entrada):
        self.entradas.append(entrada)
        if self.barreira is not None:
            self.barreira.wait(timeout=2)
        if self.erro is not None:
            raise self.erro
        return self.resposta


class SinteseFake:
    def __init__(self):
        self.entradas = []

    def invoke(self, entrada):
        self.entradas.append(entrada)
        respostas = entrada["respostas"]
        return "Síntese: " + " | ".join(respostas.values())


class ExecucaoParalelaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = carregar_main()

    def test_personas_mantem_runnable_parallel_e_sobrepoem_execucao(self):
        barreira = threading.Barrier(3)
        mapa = {
            "resumo": ChainFake("resumo", barreira=barreira),
            "pratica": ChainFake("prática", barreira=barreira),
            "critica": ChainFake("crítica", barreira=barreira),
        }

        resultado = self.main.executar_personas("O que é RAG?", mapa_personas=mapa)

        self.assertEqual(resultado, {"resumo": "resumo", "pratica": "prática", "critica": "crítica"})

    def test_modelos_configuraveis_rodam_em_paralelo_e_sao_sintetizados(self):
        barreira = threading.Barrier(2)
        sintetizador = SinteseFake()

        def fabrica_modelo(modelo):
            return ChainFake(f"resposta de {modelo}", barreira=barreira)

        resultado = self.main.executar_multi_modelos(
            "Explique RAG",
            modelo_primario="primario-configurado",
            modelo_secundario="secundario-configurado",
            fabrica_chain=fabrica_modelo,
            fabrica_sintese=lambda modelo: sintetizador,
        )

        self.assertFalse(resultado["degradado"])
        self.assertEqual(resultado["avisos"], [])
        self.assertEqual(resultado["respostas"]["primario"]["modelo"], "primario-configurado")
        self.assertEqual(resultado["respostas"]["secundario"]["modelo"], "secundario-configurado")
        self.assertIn("resposta de secundario-configurado", resultado["sintese"])
        self.assertEqual(sintetizador.entradas[0]["modelos_indisponiveis"], [])

    def test_falha_do_secundario_degrada_sem_descartar_o_primario(self):
        sintetizador = SinteseFake()

        def fabrica_modelo(modelo):
            if modelo == "secundario-indisponivel":
                return ChainFake(erro=RuntimeError("modelo offline"))
            return ChainFake("resposta primária válida")

        resultado = self.main.executar_multi_modelos(
            "Explique RAG",
            modelo_primario="primario-valido",
            modelo_secundario="secundario-indisponivel",
            fabrica_chain=fabrica_modelo,
            fabrica_sintese=lambda modelo: sintetizador,
        )

        self.assertTrue(resultado["degradado"])
        self.assertIsNone(resultado["respostas"]["primario"]["erro"])
        self.assertIn("modelo offline", resultado["respostas"]["secundario"]["erro"])
        self.assertTrue(any("secundário" in aviso for aviso in resultado["avisos"]))
        self.assertEqual(
            sintetizador.entradas[0]["respostas"],
            {"primario": "resposta primária válida"},
        )
        self.assertIn("resposta primária válida", resultado["sintese"])

    def test_defaults_documentam_e_instruem_os_dois_modelos(self):
        configuracao = (RAIZ / ".env.example").read_text(encoding="utf-8")
        readme = (RAIZ / "README.md").read_text(encoding="utf-8")

        self.assertIn("OLLAMA_MODEL_SECUNDARIO=gpt-oss:20b", configuracao)
        self.assertIn("gpt-oss:120b", readme)
        self.assertIn("gpt-oss:20b", readme)
        self.assertIn("ollama pull gpt-oss:120b", readme)
        self.assertIn("ollama pull gpt-oss:20b", readme)


if __name__ == "__main__":
    unittest.main()
