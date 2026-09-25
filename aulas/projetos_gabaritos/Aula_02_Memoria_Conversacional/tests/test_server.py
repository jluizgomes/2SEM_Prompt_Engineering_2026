import unittest

from fastapi.testclient import TestClient
from langchain_classic.memory import ConversationTokenBufferMemory
from langchain_core.messages import AIMessage, HumanMessage

import server


class FakeMemory:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.messages = []

    def load_memory_variables(self, inputs):
        return {"history": list(self.messages)}


class FakeChain:
    def __init__(self, llm=None, memory=None, verbose=False):
        self.memory = memory

    def predict(self, input, **kwargs):
        self.memory.messages.extend(
            [
                HumanMessage(content=input),
                AIMessage(content=f"resposta: {input}"),
            ]
        )
        return f"resposta: {input}"


class FakeExercise:
    llm = object()
    ConversationBufferMemory = FakeMemory
    ConversationSummaryMemory = FakeMemory
    ConversationTokenBufferMemory = FakeMemory
    ConversationChain = FakeChain

    def criar_contador_tokens(self):
        return server.criar_contador_tokens()


class MemoryApiTests(unittest.TestCase):
    def setUp(self):
        self.sessoes_anterior = getattr(server, "_SESSOES", None)
        self.canais_anterior = getattr(server, "_CANAIS", None)
        if hasattr(server, "_SESSOES"):
            server._SESSOES.clear()
        else:
            server._SESSOES = {}
        if hasattr(server, "_CANAIS"):
            server._CANAIS.clear()
        server._EXERCICIO = FakeExercise()
        server._ERRO_CARGA = None
        self.client = TestClient(server.app)

    def tearDown(self):
        if self.sessoes_anterior is None:
            if hasattr(server, "_SESSOES"):
                del server._SESSOES
        else:
            server._SESSOES = self.sessoes_anterior
        if self.canais_anterior is not None:
            server._CANAIS = self.canais_anterior
        server._EXERCICIO = None
        server._ERRO_CARGA = None

    def test_sessoes_com_ids_distintos_nao_compartilham_historico(self):
        primeira = self.client.post(
            "/api/conversar",
            json={"session_id": "sessao-a", "tipo_memoria": "buffer", "mensagem": "Ana"},
        )
        segunda = self.client.post(
            "/api/conversar",
            json={"session_id": "sessao-b", "tipo_memoria": "buffer", "mensagem": "Bruno"},
        )
        estado_a = self.client.post("/api/estado", json={"session_id": "sessao-a"})
        estado_b = self.client.post("/api/estado", json={"session_id": "sessao-b"})

        self.assertEqual(primeira.status_code, 200)
        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(estado_a.status_code, 200)
        self.assertEqual(estado_b.status_code, 200)
        self.assertEqual(estado_a.json()["extra"]["session_id"], "sessao-a")
        self.assertEqual(estado_b.json()["extra"]["session_id"], "sessao-b")
        self.assertIn("Ana", str(estado_a.json()["conteudo"]))
        self.assertNotIn("Bruno", str(estado_a.json()["conteudo"]))
        self.assertIn("Bruno", str(estado_b.json()["conteudo"]))

    def test_estado_retorna_canal_selecionado_e_historico_legivel(self):
        self.client.post(
            "/api/conversar",
            json={"session_id": "sessao-c", "tipo_memoria": "token_buffer", "mensagem": "Olá"},
        )
        estado = self.client.post("/api/estado", json={"session_id": "sessao-c"})

        self.assertEqual(estado.status_code, 200)
        self.assertEqual(estado.json()["extra"]["tipo_memoria"], "token_buffer")
        self.assertEqual(estado.json()["extra"]["canal"], "token_buffer")
        itens = estado.json()["conteudo"]
        self.assertEqual(itens[0]["titulo"], "Usuário")
        self.assertEqual(itens[1]["titulo"], "Assistente")
        self.assertEqual(itens[0]["texto"], "Olá")

    def test_normalizacao_trata_mensagens_do_langchain(self):
        itens = server._normalizar_historico(
            [HumanMessage(content="Oi"), AIMessage(content="Olá")]
        )

        self.assertEqual([item["titulo"] for item in itens], ["Usuário", "Assistente"])
        self.assertEqual([item["texto"] for item in itens], ["Oi", "Olá"])

    def test_contador_explicito_e_compativel_com_token_buffer_memory(self):
        contador = server.criar_contador_tokens()
        memoria = ConversationTokenBufferMemory(
            llm=contador,
            max_token_limit=2,
            memory_key="history",
            return_messages=True,
        )
        memoria.save_context({"input": "a" * 40}, {"response": "b" * 40})

        self.assertGreaterEqual(memoria.llm.get_num_tokens_from_messages([]), 0)
        self.assertIsInstance(memoria.llm, type(contador))

    def test_front_end_generico_reaproveita_cookie_de_sessao(self):
        primeira = self.client.post(
            "/api/conversar",
            json={"tipo_memoria": "buffer", "mensagem": "primeira"},
        )
        segunda = self.client.post(
            "/api/conversar",
            json={"tipo_memoria": "buffer", "mensagem": "segunda"},
        )
        estado = self.client.post("/api/estado", json={})

        self.assertEqual(primeira.status_code, 200)
        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(estado.status_code, 200)
        self.assertEqual(estado.json()["extra"]["session_id"], primeira.json()["extra"]["session_id"])
        self.assertIn("segunda", str(estado.json()["conteudo"]))


if __name__ == "__main__":
    unittest.main()
