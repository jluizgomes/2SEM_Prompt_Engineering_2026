import importlib.util
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "main.py"
SPEC = importlib.util.spec_from_file_location("aula06_main", MODULE_PATH)
main = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(main)

SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
SERVER_SPEC = importlib.util.spec_from_file_location("aula06_server", SERVER_PATH)
server = importlib.util.module_from_spec(SERVER_SPEC)
SERVER_SPEC.loader.exec_module(server)


class FakeLLM:
    def __init__(self):
        self.mensagens = []

    def invoke(self, mensagens):
        self.mensagens = mensagens
        return "resposta baseada no contexto"


class FakeRetriever:
    def __init__(self, documentos):
        self.documentos = documentos
        self.perguntas = []

    def invoke(self, pergunta):
        self.perguntas.append(pergunta)
        return self.documentos


class FakeVectorStore:
    def __init__(self, documentos=None):
        self.records = {}
        self.retriever = FakeRetriever([])
        self.deleted = []
        self.add_calls = []
        self.events = []
        for documento in documentos or []:
            self.add_documents([documento], ids=[documento.id or documento.page_content])

    def add_documents(self, documents, ids=None, fail=False):
        identificadores = ids or [document.id or document.page_content for document in documents]
        self.events.append("add")
        self.add_calls.append(list(identificadores))
        if fail:
            raise RuntimeError("embedding indisponível")
        for identificador, document in zip(identificadores, documents):
            self.records[identificador] = document

    def get(self, include=None):
        return {
            "ids": list(self.records),
            "metadatas": [document.metadata for document in self.records.values()],
        }

    def delete(self, ids=None):
        self.events.append("delete")
        self.deleted.extend(ids or [])
        for identificador in ids or []:
            self.records.pop(identificador, None)

    def as_retriever(self, search_kwargs=None):
        return self.retriever


class RAGTests(unittest.TestCase):
    def test_indexacao_e_idempotente_e_remove_chunks_obsoletos(self):
        primeiro = main.Document(
            page_content="primeiro conteúdo",
            metadata={"source": "manual.pdf", "page": 1},
        )
        store = FakeVectorStore()
        main.indexar([primeiro], store=store)
        main.indexar([primeiro], store=store)
        self.assertEqual(len(store.records), 1)
        self.assertNotEqual(store.add_calls[0], store.add_calls[1])

        segundo = main.Document(
            page_content="segundo conteúdo",
            metadata={"source": "manual.pdf", "page": 2},
        )
        main.indexar([segundo], store=store)
        self.assertEqual(len(store.records), 1)
        self.assertEqual(len(store.deleted), 2)

    def test_chat_cloud_e_embeddings_locais_usam_hosts_separados(self):
        fabrica_embeddings = Mock(return_value=object())
        fabrica_chat = Mock(return_value=object())
        ambiente = {
            "OLLAMA_HOST": "https://ollama.com",
            "OLLAMA_API_KEY": "chave-de-teste",
            "OLLAMA_MODEL": "gpt-oss:120b",
            "EMBEDDING_OLLAMA_HOST": "http://localhost:11434",
            "EMBEDDING_MODEL": "nomic-embed-text",
        }
        modulo = SimpleNamespace(
            OllamaEmbeddings=fabrica_embeddings,
            ChatOllama=fabrica_chat,
        )
        main.embeddings = None
        main.llm = None
        self.addCleanup(setattr, main, "embeddings", None)
        self.addCleanup(setattr, main, "llm", None)

        with patch.dict(os.environ, ambiente, clear=True), patch.object(
            main, "load_dotenv"
        ), patch.dict(sys.modules, {"langchain_ollama": modulo}):
            main._obter_embeddings()
            main._obter_llm()

        fabrica_embeddings.assert_called_once_with(
            model="nomic-embed-text",
            base_url="http://localhost:11434",
        )
        fabrica_chat.assert_called_once_with(
            model="gpt-oss:120b",
            base_url="https://ollama.com",
            temperature=0.2,
            reasoning=False,
        )

    def test_resposta_inclui_fontes_retornadas_e_nao_inventa_fontes(self):
        documento = main.Document(
            page_content="A fonte recuperado está neste trecho.",
            metadata={"source": "manual.pdf", "page": 7},
        )
        store = FakeVectorStore()
        store.retriever = FakeRetriever([documento])
        modelo = FakeLLM()
        rag = main.montar_chain(store, llm=modelo)

        resultado = rag.invoke_with_sources("qual é a fonte?")

        self.assertEqual(resultado["resposta"], "resposta baseada no contexto")
        self.assertEqual(len(resultado["fontes"]), 1)
        self.assertEqual(resultado["fontes"][0]["fonte"], "manual.pdf")
        self.assertEqual(resultado["fontes"][0]["pagina"], 7)
        self.assertIn("A fonte recuperado está neste trecho.", modelo.mensagens[0]["content"])

    def test_sem_documentos_nao_chama_modelo_e_nao_inventa_fontes(self):
        store = FakeVectorStore()
        store.retriever = FakeRetriever([])
        modelo = FakeLLM()
        rag = main.montar_chain(store, llm=modelo)

        resultado = rag.invoke_with_sources("pergunta sem contexto")

        self.assertEqual(resultado["fontes"], [])
        self.assertEqual(modelo.mensagens, [])

    def test_servidor_carrega_exercicio_sem_servico_externo(self):
        server._EXERCICIO = None
        server._ERRO_CARGA = None
        server._PIPELINE = None
        self.assertIsNone(server._EXERCICIO)
        informacao = server.info()
        self.assertTrue(informacao["implementado"])
        self.assertIsNotNone(server._EXERCICIO)

    def test_cache_do_pipeline_e_invalidado_na_reindexacao(self):
        documento = main.Document(page_content="conteúdo", metadata={"source": "local.txt"})
        store = FakeVectorStore()
        chain = SimpleNamespace(
            invoke_with_sources=lambda pergunta: {"resposta": "ok", "fontes": []}
        )
        chamadas = {"indexar": 0, "invalidar": 0}

        def indexar(chunks):
            chamadas["indexar"] += 1
            return store

        def invalidar_cache():
            chamadas["invalidar"] += 1

        exercicio = SimpleNamespace(
            carregar_documentos=lambda: [documento],
            dividir=lambda documentos: documentos,
            indexar=indexar,
            montar_chain=lambda store: chain,
            invalidar_cache=invalidar_cache,
        )
        server._PIPELINE = None
        primeiro = server._get_pipeline(exercicio)
        segundo = server._get_pipeline(exercicio)
        terceiro = server._get_pipeline(exercicio, forcar_indexacao=True)

        self.assertIs(primeiro, segundo)
        self.assertIsNot(primeiro, terceiro)
        self.assertEqual(chamadas["indexar"], 2)
        self.assertEqual(chamadas["invalidar"], 1)

    def test_endpoint_devolve_fontes_do_cadeia_real(self):
        documento = main.Document(
            page_content="trecho recuperado",
            metadata={"source": "fonte-real.pdf", "page": 2},
        )
        store = FakeVectorStore()
        store.retriever = FakeRetriever([documento])
        rag = main.montar_chain(store, llm=FakeLLM())
        server._PIPELINE = {"chain": rag, "n_chunks": 1, "vectorstore": store}
        resposta = server.perguntar(server.PerguntaBody(mensagem="qual é o trecho?"))
        self.assertEqual(resposta["extra"]["fontes"][0]["fonte"], "fonte-real.pdf")
        self.assertEqual(resposta["fontes"], resposta["extra"]["fontes"])

    def test_falha_de_embedding_preserva_indice_valido_anterior(self):
        antigo = main.Document(
            id="antigo",
            page_content="índice válido",
            metadata={"source": "antigo.pdf", "index_version": 1},
        )
        store = FakeVectorStore()
        store.records["antigo"] = antigo
        novo = main.Document(
            page_content="novo conteúdo",
            metadata={"source": "novo.pdf"},
        )

        def falhar_embedding(documents, ids=None):
            store.events.append("add")
            raise RuntimeError("embedding indisponível")

        store.add_documents = falhar_embedding
        with self.assertRaisesRegex(RuntimeError, "embedding indisponível"):
            main.indexar([novo], store=store)

        self.assertEqual(store.events[0], "add")
        self.assertIs(store.records["antigo"], antigo)
        self.assertNotIn("antigo", store.deleted)

    def test_reindexacao_incrementa_versao_e_cache_do_indice(self):
        main._INDEX_VERSION = 0
        documento = main.Document(
            page_content="conteúdo estável",
            metadata={"source": "manual.pdf", "page": 1},
        )
        store = FakeVectorStore()

        main.indexar([documento], store=store)
        primeiro_id = next(iter(store.records))
        main.indexar([documento], store=store)
        segundo_id = next(iter(store.records))

        self.assertNotEqual(primeiro_id, segundo_id)
        self.assertEqual(len(store.records), 1)
        self.assertEqual(
            next(iter(store.records.values())).metadata["index_version"],
            2,
        )

    def test_reindexacao_com_falha_preserva_pipeline_em_cache(self):
        anterior = {"chain": "pipeline-anterior"}
        server._PIPELINE = anterior
        exercicio = SimpleNamespace(
            carregar_documentos=lambda: [],
            dividir=lambda documentos: documentos,
            indexar=lambda chunks: (_ for _ in ()).throw(
                RuntimeError("reindexação falhou")
            ),
            montar_chain=lambda store: {"chain": "pipeline-novo"},
            invalidar_cache=lambda: None,
        )

        with self.assertRaisesRegex(RuntimeError, "reindexação falhou"):
            server._get_pipeline(exercicio, forcar_indexacao=True)

        self.assertIs(server._PIPELINE, anterior)


if __name__ == "__main__":
    unittest.main()
