import io
import math
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from langchain_core.documents import Document

import main


class FakeSemanticChunker:
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model

    def split_text(self, text):
        return [text[:10], text[10:]]


class FakeSemanticEmbeddings:
    def embed_documents(self, texts):
        return [
            [1.0, 0.0]
            if "Aprendizado" in text or "Modelos" in text
            else [0.0, 1.0]
            for text in texts
        ]


class FakeChromaClient:
    def __init__(self):
        self.deleted = []

    def delete_collection(self, collection_name):
        self.deleted.append(collection_name)


class FakeVectorStore:
    def __init__(self, client, collection_name, embedding_function):
        self.client = client
        self.collection_name = collection_name
        self.embedding_function = embedding_function
        self.documents = []

    def add_documents(self, documents):
        self.documents.extend(documents)

    def as_retriever(self, search_kwargs=None):
        return self


class FakeParentRetriever:
    def __init__(self, vectorstore, docstore, child_splitter, parent_splitter):
        self.vectorstore = vectorstore
        self.docstore = docstore
        self.child_splitter = child_splitter
        self.parent_splitter = parent_splitter
        self.documents = []

    def add_documents(self, documents):
        self.documents.extend(documents)

    def invoke(self, query):
        self.query = query
        return self.documents[:1]


class FakeRetriever:
    def __init__(self, documents):
        self.documents = documents
        self.queries = []

    def invoke(self, query):
        self.queries.append(query)
        return self.documents


class FakeCompressor:
    def __init__(self, model, top_n):
        self.model = model
        self.top_n = top_n


class FakeCompressionRetriever:
    def __init__(self, base_compressor, base_retriever):
        self.base_compressor = base_compressor
        self.base_retriever = base_retriever


class FakeChat:
    def __init__(self, answer):
        self.answer = answer
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return self.answer


class PipelineTests(unittest.TestCase):
    def test_uses_current_langchain_imports(self):
        self.assertTrue(
            main.ParentDocumentRetriever.__module__.startswith("langchain_classic")
        )
        self.assertEqual(main.InMemoryStore.__module__, "langchain_core.stores")

    def test_remote_chat_requires_explicit_credentials(self):
        config = main.Config(
            ollama_host="https://ollama.com",
            ollama_api_key="",
            ollama_model="model",
            embedding_host="http://localhost:11434",
            embedding_model="embedding",
            cross_encoder_model="encoder",
            chroma_path="./chroma_db",
        )
        with self.assertRaises(main.ExternalServiceError):
            main.criar_chat(config)

    def test_chat_cloud_e_embeddings_locais_usam_hosts_separados(self):
        config = main.Config(
            ollama_host="https://ollama.com",
            ollama_api_key="chave-de-teste",
            ollama_model="gpt-oss:120b",
            embedding_host="http://localhost:11434",
            embedding_model="nomic-embed-text",
            cross_encoder_model="encoder",
            chroma_path="./chroma_db",
        )

        class FakeEmbeddings:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeChat:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        embeddings = main.criar_embeddings(config, FakeEmbeddings)
        chat = main.criar_chat(config, FakeChat)

        self.assertEqual(
            embeddings.kwargs,
            {
                "model": "nomic-embed-text",
                "base_url": "http://localhost:11434",
            },
        )
        self.assertEqual(
            chat.kwargs,
            {
                "model": "gpt-oss:120b",
                "base_url": "https://ollama.com",
                "temperature": 0,
            },
        )

    def test_semantic_chunker_accepts_injected_double(self):
        embedding_model = object()
        with redirect_stdout(io.StringIO()):
            chunks = main.demo_semantic_chunker(
                embedding_model=embedding_model,
                texto="texto suficiente para o teste",
                chunker_cls=FakeSemanticChunker,
            )
        self.assertEqual(chunks, ["texto sufi", "ciente para o teste"])
        self.assertEqual(chunks, main.executar_semantic_chunker(
            "texto suficiente para o teste",
            embedding_model,
            FakeSemanticChunker,
        ))

    def test_chroma_collection_is_reset_before_each_indexing(self):
        client = FakeChromaClient()
        first = main.criar_vectorstore(
            object(),
            client=client,
            vectorstore_cls=FakeVectorStore,
            documents=[Document(page_content="primeiro")],
        )
        second = main.criar_vectorstore(
            object(),
            client=client,
            vectorstore_cls=FakeVectorStore,
            documents=[Document(page_content="segundo")],
        )
        self.assertEqual(client.deleted, ["aula07_documents", "aula07_documents"])
        self.assertEqual(len(first.documents), 1)
        self.assertEqual(len(second.documents), 1)
        self.assertEqual(first.collection_name, "aula07_documents")

    def test_parent_retriever_adds_each_document_once(self):
        client = FakeChromaClient()
        retriever = main.criar_parent_retriever(
            object(),
            [Document(page_content="RAG recupera documentos.")],
            client=client,
            vectorstore_cls=FakeVectorStore,
            retriever_cls=FakeParentRetriever,
            docstore=object(),
        )
        self.assertEqual(client.deleted, ["aula07_parent"])
        self.assertEqual(len(retriever.documents), 1)
        self.assertEqual(retriever.invoke("RAG")[0].page_content, "RAG recupera documentos.")

    def test_reranker_accepts_doubles_without_loading_a_model(self):
        client = FakeChromaClient()
        retriever = main.criar_reranker_retriever(
            object(),
            [Document(page_content="documento")],
            client=client,
            vectorstore_cls=FakeVectorStore,
            model=object(),
            compressor_cls=FakeCompressor,
            retriever_cls=FakeCompressionRetriever,
        )
        self.assertEqual(client.deleted, ["aula07_rerank"])
        self.assertIsInstance(retriever, FakeCompressionRetriever)
        self.assertEqual(retriever.base_compressor.top_n, 3)

    def test_ragas_evaluates_the_generated_execution(self):
        retriever = FakeRetriever(
            [Document(page_content="RAG combina recuperação e geração.")]
        )
        chat = FakeChat("RAG usa recuperação de documentos para responder.")
        captured = {}

        def dataset_factory(payload):
            captured["payload"] = payload
            return payload

        def evaluator(dataset, metrics, llm, embeddings):
            captured["dataset"] = dataset
            captured["metrics"] = metrics
            captured["llm"] = llm
            captured["embeddings"] = embeddings
            return {"faithfulness": 0.91, "answer_relevancy": 0.88}

        result = main.avaliar_com_ragas(
            embedding_model=object(),
            chat_model=chat,
            retriever_factory=lambda _: retriever,
            evaluator=evaluator,
            dataset_factory=dataset_factory,
            llm_wrapper_factory=lambda model: ("wrapper", model),
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            result["metrics"],
            [{"faithfulness": 0.91, "answer_relevancy": 0.88}],
        )
        self.assertEqual(result["execution"]["answer"], chat.answer)
        self.assertEqual(
            result["execution"]["contexts"],
            ["RAG combina recuperação e geração."],
        )
        self.assertEqual(captured["payload"]["answer"], [chat.answer])
        self.assertEqual(captured["metrics"], [])
        self.assertEqual(captured["llm"][0], "wrapper")
        self.assertIn("RAG combina recuperação e geração.", chat.prompts[0])

    def test_ragas_does_not_fabricate_empty_metrics(self):
        execution = main.ExemploRag(
            question="pergunta",
            answer="resposta",
            contexts=["contexto"],
            ground_truth="referência",
        )
        with self.assertRaises(main.RagasEvaluationError):
            main.avaliar_com_ragas(
                execution=execution,
                embedding_model=object(),
                evaluator=lambda dataset, **_: {},
                dataset_factory=lambda payload: payload,
            )

    def test_semantic_chunker_integrado_usa_embeddings_locais(self):
        texto = (
            "Aprendizado de máquina estuda padrões em dados. "
            "Modelos de linguagem aprendem representações de texto. "
            "Prompt engineering define instruções para modelos. "
            "RAG recupera documentos antes da geração."
        )

        chunks = main.executar_semantic_chunker(
            texto,
            embedding_model=FakeSemanticEmbeddings(),
        )

        self.assertEqual(len(chunks), 2)
        self.assertIn("Aprendizado", chunks[0])
        self.assertIn("Modelos", chunks[0])
        self.assertIn("Prompt", chunks[1])
        self.assertIn("RAG", chunks[1])

    def test_requirements_remove_pacote_incompativel(self):
        requirements = (Path(__file__).resolve().parents[1] / "requirements.txt").read_text()
        self.assertNotIn("langchain-experimental", requirements)

    def test_vectorstore_normaliza_documents_none_para_corpus_padrao(self):
        client = FakeChromaClient()
        store = main.criar_vectorstore(
            object(),
            client=client,
            vectorstore_cls=FakeVectorStore,
            documents=None,
        )

        self.assertEqual(len(store.documents), len(main.DOCUMENTOS))

    def test_ragas_rejeita_metricas_nao_finitas(self):
        execution = main.ExemploRag(
            question="pergunta",
            answer="resposta",
            contexts=["contexto"],
            ground_truth="referência",
        )
        for valor in (math.nan, math.inf, -math.inf):
            with self.subTest(valor=valor), self.assertRaises(main.RagasEvaluationError):
                main.avaliar_com_ragas(
                    execution=execution,
                    embedding_model=object(),
                    evaluator=lambda dataset, metric=valor, **_: {"metric": metric},
                    dataset_factory=lambda payload: payload,
                )


if __name__ == "__main__":
    unittest.main()
