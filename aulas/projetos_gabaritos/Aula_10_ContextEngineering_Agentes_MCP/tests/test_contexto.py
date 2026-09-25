import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import main
from contexto import (
    configuracao_mcp,
    criar_conexao_mcp,
    demo_mcp_tools,
    mensagens_de_entrada,
    recortar_mensagens,
)


class ContextoTests(unittest.TestCase):
    def test_preserva_todos_os_roles_reais(self):
        dados = [
            {"role": "system", "content": "regra"},
            {"role": "human", "content": "pergunta"},
            {
                "role": "ai",
                "content": "",
                "tool_calls": [{"name": "busca", "args": {"query": "x"}, "id": "1"}],
            },
            {"role": "tool", "content": "observação", "tool_call_id": "1", "name": "busca"},
        ]

        mensagens = mensagens_de_entrada(dados)
        recortadas = recortar_mensagens(mensagens, 100)

        self.assertEqual([type(mensagem).__name__ for mensagem in recortadas], [
            "SystemMessage",
            "HumanMessage",
            "AIMessage",
            "ToolMessage",
        ])
        self.assertEqual(recortadas[2].tool_calls[0]["id"], "1")
        self.assertEqual(recortadas[3].tool_call_id, "1")

    def test_role_desconhecido_e_rejeitado(self):
        with self.assertRaises(ValueError):
            mensagens_de_entrada([{"role": "desconhecido", "content": "x"}])

    def test_configura_transporte_http_com_url(self):
        configuracao = configuracao_mcp({
            "MCP_TRANSPORT": "streamable_http",
            "MCP_SERVER_URL": "http://localhost:8000/mcp",
        })

        self.assertEqual(configuracao, {
            "transport": "streamable_http",
            "url": "http://localhost:8000/mcp",
            "timeout": 10.0,
        })

    def test_rejeita_transporte_stdio(self):
        with self.assertRaises(ValueError):
            configuracao_mcp({
                "MCP_TRANSPORT": "stdio",
                "MCP_SERVER_COMMAND": "python servidor.py",
            })

    def test_rejeita_url_http_sem_host(self):
        with self.assertRaises(ValueError):
            configuracao_mcp({
                "MCP_TRANSPORT": "streamable_http",
                "MCP_SERVER_URL": "http://",
            })

    def test_rejeita_configuracao_stdio_direta(self):
        with self.assertRaises(ValueError):
            criar_conexao_mcp(
                {"transport": "stdio", "command": "python", "args": ["servidor.py"]},
                client_factory=Mock(),
            )

    def test_transporte_invalido_e_rejeitado(self):
        with self.assertRaises(ValueError):
            configuracao_mcp({
                "MCP_TRANSPORT": "websocket",
                "MCP_SERVER_URL": "http://localhost:8000/mcp",
            })

    def test_criacao_do_cliente_recebe_transporte_e_url(self):
        cliente = SimpleNamespace(connections={})
        factory = Mock(return_value=cliente)
        configuracao = {
            "transport": "sse",
            "url": "http://localhost:8000/sse",
        }

        resultado = criar_conexao_mcp(configuracao, client_factory=factory)

        self.assertIs(resultado, cliente)
        factory.assert_called_once_with({
            "mcp": {
                "transport": "sse",
                "url": "http://localhost:8000/sse",
            }
        })

    def test_sem_servidor_mcp_nao_chama_loader_e_explica_fallback(self):
        loader = Mock()
        saida = []

        ferramentas = demo_mcp_tools({}, loader, saida.append)

        self.assertEqual(ferramentas, [])
        loader.assert_not_called()
        self.assertIn("fluxo local", " ".join(saida).lower())

    def test_loader_sincrono_injetado_e_aceito(self):
        loader = Mock(return_value=[SimpleNamespace(name="busca")])
        saida = []

        ferramentas = demo_mcp_tools(
            {
                "MCP_TRANSPORT": "streamable_http",
                "MCP_SERVER_URL": "http://localhost:8000/mcp",
            },
            loader,
            saida.append,
        )

        self.assertEqual([ferramenta.name for ferramenta in ferramentas], ["busca"])

    def test_falha_do_mcp_nao_interrompe_fluxo_local(self):
        loader = Mock(side_effect=RuntimeError("conexão recusada"))
        saida = []

        ferramentas = demo_mcp_tools(
            {
                "MCP_TRANSPORT": "streamable_http",
                "MCP_SERVER_URL": "http://localhost:8000/mcp",
            },
            loader,
            saida.append,
        )

        self.assertEqual(ferramentas, [])
        self.assertIn("conexão recusada", " ".join(saida))

    def test_fluxo_principal_funciona_sem_servidor_mcp(self):
        loader = Mock()
        saida = []

        main.main(environ={}, carregador=loader, output=saida.append)

        loader.assert_not_called()
        texto = "\n".join(saida)
        self.assertIn("6 palavras", texto)
        self.assertIn("fluxo local", texto.lower())

    def test_trim_remove_tool_sem_chamada_correspondente(self):
        mensagens = mensagens_de_entrada([
            {"role": "system", "content": "regra"},
            {"role": "tool", "content": "órfã", "tool_call_id": "1", "name": "busca"},
        ])

        recortadas = recortar_mensagens(mensagens, 100)

        self.assertFalse(any(type(mensagem).__name__ == "ToolMessage" for mensagem in recortadas))

    def test_trim_remove_tool_call_sem_resultado_correspondente(self):
        mensagens = mensagens_de_entrada([
            {
                "role": "ai",
                "content": "",
                "tool_calls": [{"name": "busca", "args": {}, "id": "1"}],
            },
        ])

        recortadas = recortar_mensagens(mensagens, 100)

        self.assertFalse(any(getattr(mensagem, "tool_calls", None) for mensagem in recortadas))

    def test_documentacao_nao_anuncia_servidor_stdio(self):
        raiz = Path(__file__).resolve().parents[1]
        documentacao = (raiz / "README.md").read_text()
        exemplo = (raiz / ".env.example").read_text()

        self.assertNotIn("MCP_TRANSPORT=stdio", documentacao)
        self.assertNotIn("MCP_SERVER_COMMAND", documentacao)
        self.assertNotIn("MCP_SERVER_COMMAND", exemplo)


if __name__ == "__main__":
    unittest.main()
