import importlib.util
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "main.py"
SPEC = importlib.util.spec_from_file_location("aula05_main", MODULE_PATH)
main = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(main)

SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
SERVER_SPEC = importlib.util.spec_from_file_location("aula05_server", SERVER_PATH)
server = importlib.util.module_from_spec(SERVER_SPEC)
SERVER_SPEC.loader.exec_module(server)


class FakeEmbeddings:
    def __init__(self):
        self.calls = 0

    def embed_documents(self, textos):
        self.calls += 1
        return [[float(len(texto))] for texto in textos]


class FakeVectorStore:
    def __init__(self):
        self.records = {}
        self.embeddings = FakeEmbeddings()
        self.ids_adicionados = []

    def add_documents(self, documents, ids=None):
        identificadores = ids or [document.id for document in documents]
        self.ids_adicionados.append(list(identificadores))
        self.embeddings.embed_documents([document.page_content for document in documents])
        for identificador, document in zip(identificadores, documents):
            self.records[identificador] = document

    def get(self, include=None):
        identificadores = list(self.records)
        return {
            "ids": identificadores,
            "documents": [self.records[identificador].page_content for identificador in identificadores],
            "metadatas": [self.records[identificador].metadata for identificador in identificadores],
        }

    def similarity_search(self, consulta, k=2):
        self.ultima_consulta = consulta
        return list(self.records.values())[:k]


class BuscaTests(unittest.TestCase):
    def test_indexacao_repetida_nao_duplica_e_usa_ids_estaveis(self):
        store = FakeVectorStore()
        ids_primeira = main._ids_documentos(main.DOCUMENTOS)
        self.assertEqual(ids_primeira, main._ids_documentos(main.DOCUMENTOS))
        self.assertEqual(len(set(ids_primeira)), len(ids_primeira))

        self.assertEqual(main.indexar(store=store), len(main.DOCUMENTOS))
        self.assertEqual(main.indexar(store=store), len(main.DOCUMENTOS))

        self.assertEqual(len(store.records), len(main.DOCUMENTOS))
        self.assertEqual(store.ids_adicionados[0], store.ids_adicionados[1])
        self.assertGreaterEqual(store.embeddings.calls, 2)

    def test_documentos_refletem_a_colecao_real(self):
        store = FakeVectorStore()
        main.indexar(store=store)
        store.records["externo"] = main.Document(
            page_content="Documento acrescentado diretamente à coleção",
            metadata={"fonte": "fonte externa"},
        )

        documentos = main.documentos_indexados(store=store)
        self.assertIn("Documento acrescentado diretamente à coleção", [doc.page_content for doc in documentos])
        self.assertEqual(
            [doc.page_content for doc in documentos],
            [store.records[identificador].page_content for identificador in store.records],
        )

    def test_busca_antes_da_indexacao_retorna_estado_claro(self):
        store = FakeVectorStore()
        with self.assertRaisesRegex(LookupError, "index"):
            main.buscar("qualquer consulta", store=store)

    def test_busca_usa_documentos_indexados(self):
        store = FakeVectorStore()
        main.indexar(store=store)
        resultados = main.buscar("onde fica a faculdade?", k=2, store=store)
        self.assertEqual(len(resultados), 2)
        self.assertEqual(store.ultima_consulta, "onde fica a faculdade?")

    def test_embeddings_usam_ollama_local_sem_exigir_chave_cloud(self):
        fabrica = Mock(return_value=object())
        ambiente = {
            "OLLAMA_HOST": "https://ollama.com",
            "EMBEDDING_OLLAMA_HOST": "http://localhost:11434",
            "EMBEDDING_MODEL": "nomic-embed-text",
        }
        modulo = SimpleNamespace(OllamaEmbeddings=fabrica)
        main.embeddings = None
        self.addCleanup(setattr, main, "embeddings", None)

        with patch.dict(os.environ, ambiente, clear=True), patch.object(
            main, "load_dotenv"
        ), patch.dict(sys.modules, {"langchain_ollama": modulo}):
            main._obter_embeddings()

        fabrica.assert_called_once_with(
            model="nomic-embed-text",
            base_url="http://localhost:11434",
        )

    def test_endpoint_documentos_usa_a_colecao_do_exercicio(self):
        exercicio = SimpleNamespace(
            documentos_indexados=lambda: [
                main.Document(page_content="documento real", metadata={"fonte": "colecao"})
            ]
        )
        server._EXERCICIO = exercicio
        resposta = server.documentos()
        self.assertEqual(resposta["conteudo"][0]["texto"], "documento real")
        self.assertEqual(resposta["conteudo"][0]["fonte"], "colecao")

    def test_endpoint_busca_propaga_estado_sem_indexar(self):
        exercicio = SimpleNamespace(
            buscar=lambda consulta, k=2: (_ for _ in ()).throw(
                LookupError("Nenhum documento indexado. Execute a indexação antes de fazer uma busca.")
            )
        )
        server._EXERCICIO = exercicio
        resposta = server.buscar(server.BuscaBody(consulta="pergunta", k="2"))
        self.assertEqual(resposta["tipo"], "erro")
        self.assertIn("Nenhum documento indexado", resposta["conteudo"])


if __name__ == "__main__":
    unittest.main()
