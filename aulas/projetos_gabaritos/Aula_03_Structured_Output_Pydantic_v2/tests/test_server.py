import unittest

from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

import server


class ReceitaTeste(BaseModel):
    nome: str
    ingredientes: list[str]
    modo_preparo: str
    tempo_minutos: int = Field(ge=0)


class FakeChain:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.calls = 0

    def invoke(self, payload):
        self.calls += 1
        return self.respostas.pop(0)


class FakeParser:
    def get_format_instructions(self):
        return "JSON válido"


class FakeExercise:
    Receita = ReceitaTeste

    def __init__(self, respostas):
        self.chain = FakeChain(respostas)
        self.parser = FakeParser()


class StructuredOutputApiTests(unittest.TestCase):
    def setUp(self):
        self.exercicio_anterior = server._EXERCICIO
        self.erro_anterior = server._ERRO_CARGA
        server._ERRO_CARGA = None
        self.client = TestClient(server.app)

    def tearDown(self):
        server._EXERCICIO = self.exercicio_anterior
        server._ERRO_CARGA = self.erro_anterior

    def test_saida_invalida_e_reprocessada_ate_o_limite(self):
        exercicio = FakeExercise(
            [
                {"nome": "incompleto"},
                {
                    "nome": "bolo de cenoura",
                    "ingredientes": ["cenoura", "farinha"],
                    "modo_preparo": "Misture e asse.",
                    "tempo_minutos": 35,
                },
            ]
        )
        server._EXERCICIO = exercicio
        response = self.client.post("/api/gerar_receita", json={"prato": "bolo de cenoura"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(exercicio.chain.calls, 2)
        self.assertEqual(response.json()["conteudo"]["tempo_minutos"], 35)

    def test_saida_sempre_invalida_retorna_erro_com_tentativas_limitadas(self):
        exercicio = FakeExercise([{"nome": "incompleto"}, {"nome": "incompleto"}])
        server._EXERCICIO = exercicio
        response = self.client.post("/api/gerar_receita", json={"prato": "bolo"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(exercicio.chain.calls, 2)
        self.assertIn("2 tentativas", response.text)
        self.assertIn("Saída estruturada inválida", response.text)

    def test_schema_expoe_contrato_pydantic_v2(self):
        server._EXERCICIO = FakeExercise([])
        response = self.client.post("/api/schema")

        self.assertEqual(response.status_code, 200)
        schema = response.json()["conteudo"]["json_schema"]
        self.assertEqual(schema["title"], "ReceitaTeste")
        self.assertIn("tempo_minutos", schema["properties"])
        self.assertIn("tempo_minutos", schema["required"])


if __name__ == "__main__":
    unittest.main()
