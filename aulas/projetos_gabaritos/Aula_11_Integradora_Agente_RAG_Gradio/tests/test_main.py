import ast
import inspect
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main


class MensagemFalsa:
    def __init__(self, content):
        self.content = content


class AgenteFalso:
    def __init__(self):
        self.entrada = None

    def invoke(self, entrada):
        self.entrada = entrada
        return {"messages": [MensagemFalsa("resposta do agente")]}


class ChatInterfaceFalso:
    instancias = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.lancado = False
        self.launch_kwargs = None
        self.__class__.instancias.append(self)

    def launch(self, **kwargs):
        self.lancado = True
        self.launch_kwargs = kwargs


class VectorstoreFalso:
    def __init__(self):
        self.documentos = {}
        self.adicoes = 0

    def get(self, ids):
        return {"ids": [identificador for identificador in ids if identificador in self.documentos]}

    def add_documents(self, documents, ids):
        self.adicoes += 1
        for identificador, documento in zip(ids, documents):
            self.documentos[identificador] = documento


class MainA11Test(unittest.TestCase):
    def tearDown(self):
        main.agent = None
        main.llm = None

    def test_calculadora_aceita_aritmetica_e_recusa_execucao(self):
        self.assertEqual(main.calcular.invoke({"expressao": "2 + 3 * 4"}), "Resultado: 14")
        resultado = main.calcular.invoke({"expressao": "__import__('os').getcwd()"})
        self.assertTrue(resultado.startswith("Erro:"))
        self.assertNotIn("getcwd", resultado)

    def test_responder_envia_historico_como_mensagens(self):
        agente = AgenteFalso()
        main.agent = agente
        historico = [
            {"role": "user", "content": "primeira pergunta"},
            {"role": "assistant", "content": "primeira resposta"},
        ]
        original = [mensagem.copy() for mensagem in historico]

        resultado = main.responder("nova pergunta", historico)

        self.assertEqual(resultado, "resposta do agente")
        self.assertEqual(
            agente.entrada,
            {
                "messages": [
                    *original,
                    {"role": "user", "content": "nova pergunta"},
                ]
            },
        )
        self.assertEqual(historico, original)

    def test_responder_rejeita_historico_em_tuplas(self):
        with self.assertRaises(TypeError):
            main.responder("nova pergunta", [("pergunta", "resposta")])

    def test_responder_aceita_historico_estruturado_do_gradio_6(self):
        agente = AgenteFalso()
        main.agent = agente
        historico = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "pergunta anterior"}],
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "resposta anterior"}],
            },
        ]

        main.responder("nova pergunta", historico)

        self.assertEqual(
            agente.entrada["messages"],
            [
                {"role": "user", "content": "pergunta anterior"},
                {"role": "assistant", "content": "resposta anterior"},
                {"role": "user", "content": "nova pergunta"},
            ],
        )

    def test_construtor_chat_interface_nao_usa_type_e_preserva_assinatura(self):
        ChatInterfaceFalso.instancias.clear()
        configuracao = SimpleNamespace(model="modelo", embedding_model="embedding")
        with patch.object(main, "obter_configuracao", return_value=configuracao), patch.object(
            main, "obter_agente", return_value=object()
        ), patch.dict(sys.modules, {"gradio": SimpleNamespace(ChatInterface=ChatInterfaceFalso)}):
            main.main()

        demo = ChatInterfaceFalso.instancias[-1]
        assinatura = inspect.signature(main.responder)
        arvore = ast.parse(Path(main.__file__).read_text(encoding="utf-8"))
        chamadas_chat = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
            and isinstance(no.func, ast.Attribute)
            and no.func.attr == "ChatInterface"
        ]

        self.assertEqual(list(assinatura.parameters), ["mensagem", "history"])
        self.assertIs(demo.kwargs["fn"], main.responder)
        self.assertNotIn("type", demo.kwargs)
        self.assertNotIn("theme", demo.kwargs)
        self.assertTrue(chamadas_chat)
        self.assertFalse(
            any(
                keyword.arg == "type"
                for chamada in chamadas_chat
                for keyword in chamada.keywords
            )
        )
        self.assertTrue(demo.lancado)

    def test_chat_cloud_e_embeddings_locais_usam_hosts_separados(self):
        configuracao = main.Configuracao(
            host="https://ollama.com",
            api_key="chave-de-teste",
            model="gpt-oss:120b",
            embedding_host="http://localhost:11434",
            embedding_model="nomic-embed-text",
        )
        fabrica_embeddings = Mock(return_value=object())
        fabrica_chat = Mock(return_value=object())

        with patch.object(
            main, "obter_configuracao", return_value=configuracao
        ), patch("langchain_ollama.ChatOllama", fabrica_chat), patch(
            "langchain_ollama.OllamaEmbeddings", fabrica_embeddings
        ):
            main.llm = None
            main.obter_llm()
            main.criar_embeddings(configuracao)

        fabrica_chat.assert_called_once_with(
            model="gpt-oss:120b",
            base_url="https://ollama.com",
            temperature=0,
        )
        fabrica_embeddings.assert_called_once_with(
            model="nomic-embed-text",
            base_url="http://localhost:11434",
        )

    def test_chroma_e_idempotente(self):
        vectorstore = VectorstoreFalso()

        main.garantir_documentos(vectorstore)
        main.garantir_documentos(vectorstore)

        self.assertEqual(vectorstore.adicoes, 1)
        self.assertEqual(set(vectorstore.documentos), {item[0] for item in main.DOCUMENTOS})

    def test_criar_agente_usa_create_agent(self):
        modelo = object()
        ferramentas = [object()]
        agente = object()
        main.agent = None
        with patch.object(main, "obter_llm", return_value=modelo), patch.object(
            main, "obter_tools", return_value=ferramentas
        ), patch.object(main, "create_agent", return_value=agente) as factory:
            resultado = main.obter_agente()

        self.assertIs(resultado, agente)
        factory.assert_called_once()
        self.assertEqual(factory.call_args.kwargs["model"], modelo)
        self.assertEqual(factory.call_args.kwargs["tools"], ferramentas)


if __name__ == "__main__":
    unittest.main()
