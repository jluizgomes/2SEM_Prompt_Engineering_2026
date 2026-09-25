import importlib.util
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "main.py"
SPEC = importlib.util.spec_from_file_location("aula04_main", MODULE_PATH)
main = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(main)


class ContextoTests(unittest.TestCase):
    def test_preparar_mensagens_limita_historico_e_mantem_pergunta(self):
        contador = len
        pergunta = "Como posso respeitar a janela de contexto?"
        recente = "turno recente " * 5
        antigo = "turno antigo " * 30
        orcamento = len(main.SISTEMA) + len(pergunta) + len(recente) + 2

        mensagens = main.preparar_mensagens(
            [{"role": "user", "content": antigo}, {"role": "assistant", "content": recente}],
            pergunta,
            orcamento_tokens=orcamento,
            contador=contador,
        )

        conteudos = [mensagem["content"] for mensagem in mensagens]
        self.assertEqual(mensagens[0]["role"], "system")
        self.assertEqual(mensagens[-1]["content"], pergunta)
        self.assertIn(recente.strip(), conteudos)
        self.assertNotIn(antigo, conteudos)
        self.assertLessEqual(sum(contador(conteudo) for conteudo in conteudos), orcamento)

    def test_trim_texto_respeita_limite_injetado(self):
        trimmed = main.trim_texto("abcdefghij", 4, contador=len)
        self.assertLessEqual(len(trimmed), 4)
        self.assertTrue("abcdefghij".startswith(trimmed))

    def test_chain_chama_modelo_com_historico_ja_limitado(self):
        class FakeLLM:
            def __init__(self):
                self.mensagens = None

            def invoke(self, mensagens):
                self.mensagens = mensagens
                return "resposta"

        fake = FakeLLM()
        anterior = main.llm
        main.llm = fake
        try:
            resposta = main.chain.invoke(
                {
                    "pergunta": "pergunta atual",
                    "historico": [
                        {"role": "user", "content": "pergunta anterior"},
                        {"role": "assistant", "content": "resposta anterior"},
                    ],
                }
            )
        finally:
            main.llm = anterior

        self.assertEqual(resposta, "resposta")
        conteudos = [
            item.content if hasattr(item, "content") else item["content"]
            for item in fake.mensagens
        ]
        self.assertEqual(conteudos[-1], "pergunta atual")
        self.assertIn("resposta anterior", conteudos)

    def test_chain_nao_possui_contexto_global_mutavel(self):
        self.assertFalse(hasattr(main.chain, "ultimo_contexto"))

    def test_chain_isola_contextos_em_chamadas_concorrentes(self):
        class FakeLLM:
            def __init__(self):
                self.barreira = threading.Barrier(2)
                self.mensagens = []
                self.lock = threading.Lock()

            def invoke(self, mensagens):
                self.barreira.wait(timeout=5)
                with self.lock:
                    self.mensagens.append(mensagens)
                return str(mensagens[-1].content)

        fake = FakeLLM()
        anterior = main.llm
        main.llm = fake
        payloads = [
            {
                "pergunta": "pergunta A",
                "historico": [{"role": "assistant", "content": "resposta A"}],
            },
            {
                "pergunta": "pergunta B",
                "historico": [{"role": "assistant", "content": "resposta B"}],
            },
        ]

        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                respostas = list(executor.map(main.chain.invoke, payloads))
        finally:
            main.llm = anterior

        self.assertEqual(respostas, ["pergunta A", "pergunta B"])
        contextos = {
            str(mensagens[-1].content if hasattr(mensagens[-1], "content") else mensagens[-1]["content"]):
            [
                item.content if hasattr(item, "content") else item["content"]
                for item in mensagens
            ]
            for mensagens in fake.mensagens
        }
        self.assertEqual(set(contextos), {"pergunta A", "pergunta B"})
        self.assertIn("resposta A", contextos["pergunta A"])
        self.assertNotIn("resposta B", contextos["pergunta A"])
        self.assertIn("resposta B", contextos["pergunta B"])
        self.assertNotIn("resposta A", contextos["pergunta B"])


if __name__ == "__main__":
    unittest.main()
