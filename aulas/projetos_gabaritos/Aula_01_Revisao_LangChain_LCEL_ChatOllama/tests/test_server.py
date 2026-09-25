import json
import unittest

from fastapi.testclient import TestClient

import server


class FakeTextChain:
    def __init__(self, chunks=("Olá", " mundo"), failure=None):
        self.chunks = chunks
        self.failure = failure
        self.calls = []

    def invoke(self, payload):
        self.calls.append(payload)
        return f"Resposta: {payload['pergunta']}"

    def stream(self, payload):
        self.calls.append(payload)

        def gerar():
            for chunk in self.chunks:
                yield chunk
            if self.failure is not None:
                raise self.failure

        return gerar()


class FakeJsonChain:
    def invoke(self, payload):
        return {"pergunta": payload["pergunta"], "ingredientes": ["cenoura", "farinha"]}


class FakeExercise:
    def __init__(self, chunks=("Olá", " mundo"), failure=None):
        self.chain_texto = FakeTextChain(chunks, failure)
        self.chain_json = FakeJsonChain()


class StreamApiTests(unittest.TestCase):
    def setUp(self):
        self.exercicio_anterior = server._EXERCICIO
        self.erro_anterior = server._ERRO_CARGA
        self.client = TestClient(server.app)
        server._ERRO_CARGA = None

    def tearDown(self):
        server._EXERCICIO = self.exercicio_anterior
        server._ERRO_CARGA = self.erro_anterior

    def eventos(self, texto):
        resultado = []
        for bloco in texto.strip().split("\n\n"):
            if not bloco:
                continue
            linhas = bloco.splitlines()
            evento = next((linha[7:] for linha in linhas if linha.startswith("event: ")), "message")
            dados = json.loads(next(linha[6:] for linha in linhas if linha.startswith("data: ")))
            resultado.append((evento, dados))
        return resultado

    def test_chat_aceita_pergunta_canonica(self):
        exercicio = FakeExercise()
        server._EXERCICIO = exercicio

        response = self.client.post("/api/perguntar", json={"pergunta": "oi"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["conteudo"], "Resposta: oi")
        self.assertEqual(exercicio.chain_texto.calls[0]["pergunta"], "oi")

    def test_chat_aceita_mensagem_enviada_pelo_frontend(self):
        exercicio = FakeExercise()
        server._EXERCICIO = exercicio

        response = self.client.post(
            "/api/perguntar",
            json={
                "persona": "teste",
                "especialidade": "teste",
                "mensagem": "oi pela interface",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["conteudo"], "Resposta: oi pela interface")
        self.assertEqual(
            exercicio.chain_texto.calls[0]["pergunta"],
            "oi pela interface",
        )

    def test_stream_envia_eventos_progressivos_e_final(self):
        server._EXERCICIO = FakeExercise()
        response = self.client.post(
            "/api/stream",
            json={"persona": "teste", "especialidade": "teste", "pergunta": "oi"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        eventos = self.eventos(response.text)
        self.assertEqual([evento for evento, _ in eventos], ["chunk", "chunk", "done"])
        self.assertEqual(eventos[0][1]["conteudo"], "Olá")
        self.assertEqual(eventos[-1][1]["conteudo"], "Olá mundo")
        self.assertEqual(eventos[-1][1]["extra"]["tokens_recebidos"], 2)

    def test_stream_converte_falha_do_modelo_em_evento_de_erro(self):
        server._EXERCICIO = FakeExercise(chunks=("parcial",), failure=RuntimeError("modelo indisponível"))
        response = self.client.post(
            "/api/stream",
            json={"persona": "teste", "especialidade": "teste", "pergunta": "oi"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("event: error", response.text)
        self.assertIn("modelo indisponível", response.text)

    def test_erro_de_carregamento_preserva_status_http(self):
        server._EXERCICIO = None
        server._ERRO_CARGA = "main indisponível"
        response = self.client.post(
            "/api/stream",
            json={"persona": "teste", "especialidade": "teste", "pergunta": "oi"},
        )

        self.assertEqual(response.status_code, 502)
        self.assertIn("main indisponível", response.text)

    def test_modo_json_continua_retornando_o_objeto(self):
        server._EXERCICIO = FakeExercise()
        response = self.client.post(
            "/api/perguntar_json",
            json={"persona": "teste", "especialidade": "teste", "pergunta": "liste"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tipo"], "json")
        self.assertEqual(response.json()["conteudo"]["ingredientes"], ["cenoura", "farinha"])


if __name__ == "__main__":
    unittest.main()
