import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

import app_streamlit
import main as gradio_main
import rag


class RagTests(unittest.TestCase):
    def test_carrega_corpus_local(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "corpus.txt"
            caminho.write_text(
                "Primeiro documento sobre RAG.\n\nSegundo documento sobre memória.",
                encoding="utf-8",
            )

            documentos = rag.carregar_corpus(caminho)

        self.assertEqual(len(documentos), 2)
        self.assertIn("RAG", documentos[0])

    def test_memoria_e_isolada_por_sessao(self):
        factory = Mock(side_effect=lambda session_id: {"session_id": session_id})
        memoria = rag.MemoriaPorSessao(factory)

        primeira = memoria.obter("sessao-a")
        segunda = memoria.obter("sessao-b")

        self.assertIsNot(primeira, segunda)
        self.assertIs(primeira, memoria.obter("sessao-a"))
        self.assertEqual(factory.call_count, 2)

    def test_chain_rag_recupera_contexto_sem_rede(self):
        configuracao = Mock(side_effect=AssertionError("não deve carregar ambiente"))
        store = SimpleNamespace(
            as_retriever=lambda search_kwargs: RunnableLambda(
                lambda pergunta: [SimpleNamespace(page_content="contexto recuperado local")]
            )
        )
        modelo = RunnableLambda(lambda prompt: AIMessage(content=str(prompt)))
        memoria = rag.MemoriaPorSessao()

        with unittest.mock.patch.object(rag, "configuracao_modelo", configuracao):
            chain = rag.criar_chain_rag(
                config={},
                store=store,
                llm=modelo,
                memoria=memoria,
            )
        resposta = chain.invoke(
            {"pergunta": "O que é RAG?"},
            config={"configurable": {"session_id": "sessao-a"}},
        )

        self.assertIn("contexto recuperado local", resposta)
        self.assertEqual(len(memoria.obter("sessao-a").messages), 2)

    def test_configuracao_separa_chat_cloud_e_embeddings_locais(self):
        configuracao = rag.configuracao_modelo({
            "OLLAMA_HOST": "https://ollama.com",
            "OLLAMA_API_KEY": "chave-de-teste",
            "OLLAMA_MODEL": "gpt-oss:120b",
            "EMBEDDING_OLLAMA_HOST": "http://localhost:11434",
            "EMBEDDING_MODEL": "nomic-embed-text",
        })

        self.assertEqual(configuracao["host"], "https://ollama.com")
        self.assertEqual(
            configuracao["embedding_host"], "http://localhost:11434"
        )
        self.assertEqual(configuracao["embedding_model"], "nomic-embed-text")

    def test_clientes_recebem_urls_e_autenticacao_corretas(self):
        configuracao = {
            "host": "https://ollama.com",
            "api_key": "chave-de-teste",
            "model": "gpt-oss:120b",
            "embedding_host": "http://localhost:11434",
            "embedding_model": "nomic-embed-text",
        }
        embeddings = object()
        modelo = object()
        store = Mock()
        store.get.return_value = {"ids": ["documento"]}
        fabrica_embeddings = Mock(return_value=embeddings)
        fabrica_chat = Mock(return_value=modelo)
        fabrica_chroma = Mock(return_value=store)

        modulo_chroma = SimpleNamespace(Chroma=fabrica_chroma)
        with patch("langchain_ollama.OllamaEmbeddings", fabrica_embeddings), patch(
            "langchain_ollama.ChatOllama", fabrica_chat
        ), patch.dict(sys.modules, {"langchain_chroma": modulo_chroma}):
            rag._criar_store(configuracao, ["texto"])
            rag._criar_llm(configuracao)

        fabrica_embeddings.assert_called_once_with(
            model="nomic-embed-text",
            base_url="http://localhost:11434",
        )
        fabrica_chat.assert_called_once_with(
            model="gpt-oss:120b",
            base_url="https://ollama.com",
            temperature=0.2,
            client_kwargs={
                "headers": {"Authorization": "Bearer chave-de-teste"}
            },
        )

    def test_responder_usa_invoke_injetado_e_session_id(self):
        invoke = Mock(return_value="resposta do RAG")

        resposta = rag.responder("O que é RAG?", "sessao-a", invoke=invoke)

        self.assertEqual(resposta, "resposta do RAG")
        invoke.assert_called_once()
        self.assertEqual(invoke.call_args.kwargs["config"], {
            "configurable": {"session_id": "sessao-a"}
        })

    def test_responder_rejeita_mensagem_vazia(self):
        with self.assertRaises(ValueError):
            rag.responder("   ", "sessao-a", invoke=Mock())


class InterfaceTests(unittest.TestCase):
    def test_gradio_mantem_historico_e_session_id(self):
        responder_rag = Mock(return_value="resposta")

        historico, session_id = gradio_main.responder_gradio(
            "pergunta",
            [],
            "sessao-a",
            responder_rag=responder_rag,
        )

        self.assertEqual(session_id, "sessao-a")
        self.assertEqual([mensagem["role"] for mensagem in historico], ["user", "assistant"])
        responder_rag.assert_called_once_with("pergunta", "sessao-a")

    def test_streamlit_gera_ids_isolados_por_sessao(self):
        primeira = {}
        segunda = {}

        primeiro_id = app_streamlit.garantir_session_id(primeira)
        segundo_id = app_streamlit.garantir_session_id(segunda)

        self.assertNotEqual(primeiro_id, segundo_id)
        self.assertEqual(app_streamlit.garantir_session_id(primeira), primeiro_id)


if __name__ == "__main__":
    unittest.main()
