import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
from langchain_core.runnables import RunnableLambda


class ClassificadorFalso:
    def __init__(self, categoria):
        self.categoria = categoria
        self.entrada = None

    def invoke(self, entrada):
        self.entrada = entrada
        return SimpleNamespace(categoria=self.categoria)


class ChainFalsa:
    def __init__(self, resposta):
        self.resposta = resposta
        self.entrada = None

    def invoke(self, entrada):
        self.entrada = entrada
        return self.resposta


class RetrieverFalso:
    def __init__(self):
        self.consultas = []

    def invoke(self, consulta):
        self.consultas.append(consulta)
        if not isinstance(consulta, str):
            raise AssertionError("o retriever recebeu a entrada completa")
        return ["contexto recuperado"]


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


class MainA12Test(unittest.TestCase):
    def tearDown(self):
        main.llm = None
        main.classificador = None
        main.chains = None
        main.chain_documentos = None
        main.chain_calculo = None
        main.chain_geral = None

    def test_normaliza_categorias_com_espacos_e_acento(self):
        self.assertEqual(main.normalizar_categoria(" CÁLCULO "), "calculo")
        self.assertEqual(main.normalizar_categoria("documentos"), "documentos")
        self.assertEqual(main.normalizar_categoria("GERAL"), "geral")

    def test_rotear_rejeita_categoria_desconhecida(self):
        classificador = ClassificadorFalso("outra")
        chain = ChainFalsa("não deve responder")
        with patch.object(main, "obter_classificador", return_value=classificador), patch.object(
            main, "obter_chains", return_value=(chain, chain, chain)
        ):
            with self.assertRaises(ValueError):
                main.rotear({"pergunta": "pergunta"})

    def test_rotear_normaliza_e_chama_chain_categorizada(self):
        classificador = ClassificadorFalso(" CÁLCULO ")
        documentos = ChainFalsa("resposta documentos")
        calculo = ChainFalsa("resposta cálculo")
        geral = ChainFalsa("resposta geral")
        with patch.object(main, "obter_classificador", return_value=classificador), patch.object(
            main, "obter_chains", return_value=(documentos, calculo, geral)
        ):
            resultado = main.rotear({"pergunta": "Quanto é 12 vezes 8?"})

        self.assertEqual(resultado, {"categoria": "calculo", "resposta": "resposta cálculo"})
        self.assertEqual(calculo.entrada, {"pergunta": "Quanto é 12 vezes 8?"})
        self.assertIsNone(documentos.entrada)
        self.assertIsNone(geral.entrada)

    def test_criar_chains_aceita_modelo_e_retriever_falsos(self):
        retriever = RunnableLambda(lambda _: [])
        modelo = RunnableLambda(lambda _: "resposta falsa")

        chains = main.criar_chains(retriever, modelo)

        self.assertEqual(len(chains), 3)
        self.assertTrue(all(chain is not None for chain in chains))

    def test_ramo_documental_extrai_pergunta_antes_do_retriever(self):
        retriever = RetrieverFalso()
        modelo = RunnableLambda(lambda _: "resposta documental")
        chain_documentos, _, _ = main.criar_chains(
            RunnableLambda(retriever.invoke), modelo
        )

        resultado = chain_documentos.invoke({"pergunta": "Onde fica a FIAP?"})

        self.assertEqual(retriever.consultas, ["Onde fica a FIAP?"])
        self.assertEqual(resultado, "resposta documental")

    def test_escopo_documentado_nao_promete_stategraph(self):
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
        servidor = (Path(__file__).resolve().parents[1] / "server.py").read_text(encoding="utf-8")

        self.assertIn("não é executado nesta aula", readme)
        self.assertIn("StateGraph", servidor)

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


if __name__ == "__main__":
    unittest.main()
