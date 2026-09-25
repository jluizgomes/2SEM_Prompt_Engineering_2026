import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, ToolMessage

import server
from agente import (
    _avaliar_expressao,
    calcular,
    criar_agente,
    criar_busca_web,
    executar_perguntas,
    extrair_resultado,
)


class AgenteTests(unittest.TestCase):
    def test_calculadora_prioriza_operadores(self):
        self.assertEqual(_avaliar_expressao("27 * 43 + 2"), 1163)
        self.assertEqual(_avaliar_expressao("(10 + 5) / 3"), 5.0)

    def test_calculadora_rejeita_conteudo_fora_da_allowlist(self):
        expressoes = [
            "__import__('os').system('echo inseguro')",
            "valor_segredo",
            "2 ** 1000",
            "[1, 2, 3]",
            "1e309",
        ]

        for expressao in expressoes:
            with self.subTest(expressao=expressao), self.assertRaises(ValueError):
                _avaliar_expressao(expressao)

    def test_tool_calculadora_formata_resultado(self):
        resultado = calcular.invoke({"expressao": "13 * 17"})

        self.assertEqual(resultado, "Resultado: 221")

    def test_busca_com_double_nao_acessa_rede(self):
        backend = Mock(return_value=[
            {"title": "Resultado", "body": "Resumo", "href": "https://exemplo.test"}
        ])

        busca = criar_busca_web(backend)
        resultado = busca.invoke({"query": "FIAP"})

        self.assertIn("Resultado", resultado)
        backend.assert_called_once_with("FIAP")

    def test_falha_de_busca_retorna_mensagem_sem_excecao(self):
        backend = Mock(side_effect=RuntimeError("indisponível"))

        busca = criar_busca_web(backend)
        resultado = busca.invoke({"query": "FIAP"})

        self.assertIn("não foi possível", resultado.lower())
        self.assertIn("FIAP", resultado)

    def test_criar_agente_usa_api_atual_injetada(self):
        agent_factory = Mock(return_value="agente")
        model = object()
        tools = [calcular]

        agente = criar_agente(model, tools, agent_factory=agent_factory)

        self.assertEqual(agente, "agente")
        self.assertEqual(agent_factory.call_args.args, (model, tools))
        self.assertIn("ReAct", agent_factory.call_args.kwargs["system_prompt"])

    def test_criar_agente_compila_com_api_instalada(self):
        model = GenericFakeChatModel(messages=iter([]))

        agente = criar_agente(model, [calcular])

        self.assertEqual(type(agente).__name__, "CompiledStateGraph")

    def test_falha_em_uma_pergunta_nao_interrompe_proxima(self):
        executor = Mock()
        executor.invoke.side_effect = [RuntimeError("falha"), {"output": "segunda resposta"}]
        saida = []

        resultados = executar_perguntas(executor, ["primeira", "segunda"], output=saida.append)

        self.assertEqual(executor.invoke.call_count, 2)
        self.assertEqual(
            executor.invoke.call_args_list[0].args[0],
            {"messages": [{"role": "user", "content": "primeira"}]},
        )
        self.assertIn("falha", resultados[0]["erro"])
        self.assertEqual(resultados[1]["saida"], "segunda resposta")
        self.assertTrue(any("falha" in linha.lower() for linha in saida))

    def test_extrai_resposta_final_sem_tratar_tool_call_como_resposta(self):
        resultado = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[{"name": "busca_na_web", "args": {}, "id": "1"}],
                ),
                ToolMessage(
                    content="observação",
                    tool_call_id="1",
                    name="busca_na_web",
                ),
                AIMessage(content="resposta final"),
            ]
        }

        self.assertEqual(extrair_resultado(resultado), "resposta final")

    def test_falha_transitoria_de_carregar_exercicio_permite_retry(self):
        exercicio = object()
        server._EXERCICIO = None
        server._ERRO_CARGA = None
        self.addCleanup(setattr, server, "_EXERCICIO", None)
        self.addCleanup(setattr, server, "_ERRO_CARGA", None)

        with patch.object(
            server,
            "_carregar_main",
            side_effect=[RuntimeError("falha transitória"), exercicio],
        ) as carregar:
            with self.assertRaises(HTTPException):
                server._get_exercicio()
            resultado = server._get_exercicio()

        self.assertIs(resultado, exercicio)
        self.assertEqual(carregar.call_count, 2)
        self.assertIsNone(server._ERRO_CARGA)


if __name__ == "__main__":
    unittest.main()
