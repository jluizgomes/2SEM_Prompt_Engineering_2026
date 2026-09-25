import importlib.util
import os
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from langchain_core.runnables import Runnable
from pydantic import ValidationError

RAIZ = Path(__file__).resolve().parents[1]


class ChatOllamaStub(Runnable):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def invoke(self, mensagens, config=None, **kwargs):
        raise AssertionError("O modelo real não deve ser chamado no teste")


def carregar_main():
    modulo_chat = ModuleType("langchain_ollama")
    modulo_chat.ChatOllama = ChatOllamaStub
    nome = "aula14_main_teste"
    sys.modules.pop(nome, None)
    with (
        patch.dict(sys.modules, {"langchain_ollama": modulo_chat}),
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


class SequenciaChain:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.entradas = []

    def invoke(self, entrada):
        self.entradas.append(entrada)
        return self.respostas.pop(0)


RESPOSTA_VALIDA = """
{
  "nome": "CampusIA",
  "publico_alvo": "Alunos da FIAP",
  "funcionalidades": [
    "Consultar horários",
    "Encontrar documentos",
    "Tirar dúvidas"
  ],
  "stack": "Python, FastAPI e PostgreSQL",
  "riscos": [
    "Dados desatualizados",
    "Alucinação acadêmica"
  ]
}
"""


class ContratoSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = carregar_main()

    def test_reprocessa_resposta_invalida_e_retorna_contrato_validado(self):
        cadeia = SequenciaChain(["não é json", RESPOSTA_VALIDA])
        self.main.chain = cadeia

        resultado = self.main.gerar_artefato("Especificação de teste", max_tentativas=2)

        self.assertIsInstance(resultado, self.main.Artefato)
        self.assertEqual(resultado.nome, "CampusIA")
        self.assertEqual(len(cadeia.entradas), 2)

    def test_falha_apos_retry_sem_inventar_saida(self):
        cadeia = SequenciaChain(['{"nome": "CampusIA"}', '{"nome": "CampusIA"}'])
        self.main.chain = cadeia

        with self.assertRaises(self.main.RespostaForaDoContrato) as contexto:
            self.main.gerar_artefato("Especificação inválida", max_tentativas=2)

        self.assertEqual(contexto.exception.tentativas, 2)
        self.assertIn("2 tentativa(s)", str(contexto.exception))
        self.assertEqual(len(cadeia.entradas), 2)

    def test_contrato_exige_listas_com_tamanho_minimo(self):
        with self.assertRaises(ValidationError):
            self.main.Artefato(
                nome="CampusIA",
                publico_alvo="Alunos",
                funcionalidades=["Uma", "Duas"],
                stack="Python",
                riscos=["Só um risco"],
            )

    def test_tentativas_devem_ser_positivas(self):
        cadeia = SequenciaChain([RESPOSTA_VALIDA])
        self.main.chain = cadeia

        with self.assertRaises(ValueError):
            self.main.gerar_artefato("Especificação", max_tentativas=0)

        self.assertEqual(cadeia.entradas, [])


if __name__ == "__main__":
    unittest.main()
