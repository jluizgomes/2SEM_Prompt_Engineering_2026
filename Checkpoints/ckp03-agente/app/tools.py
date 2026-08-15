"""
Tools do Agente Consultor CDC — CKP03 (100% standalone)

4 tools independentes, sem dependencia do CKP02:
1. consultar_cdc       — RAG proprio sobre documentos do CDC
2. calcular_prazos_cdc — Calculadora de prazos legais
3. classificar_pratica_abusiva — Analise de conduta
4. orgaos_defesa       — Onde e como reclamar
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

from langchain.tools import tool

# ============================================================
# Configuracoes do RAG proprio (embutido, sem depender do CKP02)
# ============================================================

DATA_DIR = os.getenv("RAG_DATA_DIR", str(Path(__file__).parent.parent / "data"))
CHROMADB_DIR = os.getenv(
    "CHROMADB_PERSIST_DIR", str(Path(__file__).parent.parent / "chromadb_data")
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen3.5:0.8b")
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_KEY = os.getenv("OLLAMA_API_KEY", "")

# Cache do vectorstore (carregado uma vez)
_vectorstore = None


def _get_embeddings():
    """Retorna embeddings configurados (nomic-embed-text)."""
    from langchain_ollama import OllamaEmbeddings

    if OLLAMA_KEY:
        return OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_BASE,
            client_kwargs={"headers": {"Authorization": f"Bearer {OLLAMA_KEY}"}},
        )
    return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE)


def _get_llm():
    """Retorna o LLM configurado."""
    from langchain_ollama import ChatOllama

    if OLLAMA_KEY:
        return ChatOllama(
            model=CHAT_MODEL,
            base_url=OLLAMA_BASE,
            temperature=0.2,
            client_kwargs={"headers": {"Authorization": f"Bearer {OLLAMA_KEY}"}},
        )
    return ChatOllama(model=CHAT_MODEL, base_url=OLLAMA_BASE, temperature=0.2)


def _get_vectorstore(force_reindex: bool = False):
    """
    Carrega ou cria o vectorstore ChromaDB com os documentos do CDC.

    Pipeline completo (embutido):
    load -> split -> embed -> store
    """
    global _vectorstore

    if _vectorstore is not None and not force_reindex:
        return _vectorstore

    from langchain_chroma import Chroma
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import DirectoryLoader, TextLoader

    persist_dir = CHROMADB_DIR
    collection_name = "cdc_consultoria_ckp03"

    # Verifica se ja existe no disco
    if not force_reindex and Path(persist_dir).exists() and Path(persist_dir).is_dir():
        try:
            _vectorstore = Chroma(
                persist_directory=persist_dir,
                embedding_function=_get_embeddings(),
                collection_name=collection_name,
            )
            return _vectorstore
        except Exception:
            pass  # Reindexa se corrompido

    # Pipeline: load
    if not Path(DATA_DIR).exists():
        raise FileNotFoundError(f"Diretorio de dados nao encontrado: {DATA_DIR}")

    loader = DirectoryLoader(
        str(DATA_DIR),
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()
    print(f"[CKP03 RAG] 📄 {len(documents)} documentos carregados")

    # Pipeline: split
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print(f"[CKP03 RAG] ✂️ {len(chunks)} chunks gerados")

    # Pipeline: embed + store
    _vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=_get_embeddings(),
        persist_directory=persist_dir,
        collection_name=collection_name,
    )
    print(f"[CKP03 RAG] 🗄️ Vectorstore criado em {persist_dir}")

    return _vectorstore


def _buscar_rag(pergunta: str, top_k: int = 4) -> dict:
    """
    Busca RAG completa: retrieve -> generate com citacao de fonte.

    Returns:
        dict com 'resposta' e 'fontes'
    """
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough

    vs = _get_vectorstore()
    retriever = vs.as_retriever(search_type="similarity", search_kwargs={"k": top_k})
    chunks = retriever.invoke(pergunta)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Voce eh o Dr. Consumidor, especialista em Direito do Consumidor "
            "Brasileiro (CDC - Lei 8.078/90). Responda com base EXCLUSIVAMENTE "
            "no contexto abaixo. Cite a fonte.\n\n"
            "CONTEXTO:\n{context}",
        ),
        ("human", "{question}"),
    ])

    def _format(docs):
        parts = []
        for i, doc in enumerate(docs, 1):
            src = doc.metadata.get("source", "fonte desconhecida")
            parts.append(f"[Doc {i} — {Path(src).name}]\n{doc.page_content}")
        return "\n---\n".join(parts)

    chain = (
        {"context": retriever | _format, "question": RunnablePassthrough()}
        | prompt
        | _get_llm()
        | StrOutputParser()
    )

    resposta = chain.invoke(pergunta)
    fontes = list(set(Path(doc.metadata.get("source", "?")).name for doc in chunks))

    return {"resposta": resposta, "fontes": fontes}


# ============================================================
# Tool 1: RAG — Consulta ao CDC (OBRIGATORIA)
# ============================================================

@tool
def consultar_cdc(pergunta: str) -> str:
    """
    Consulta o Codigo de Defesa do Consumidor (Lei 8.078/90) usando busca
    semantica nos documentos oficiais do CDC.

    USE quando o usuario perguntar sobre:
    - Direitos do consumidor (garantia, troca, arrependimento, vicios, defeitos)
    - Prazos legais para reclamacao (30 dias, 90 dias, 5 anos, 7 dias)
    - Praticas abusivas de fornecedores (Art. 39 do CDC)
    - Protecao contratual em relacoes de consumo
    - Sancoes e penalidades previstas no CDC
    - Qualquer artigo ou secao especifica do CDC

    NAO USE para:
    - Perguntas sobre outros ramos do direito (penal, trabalhista, tributario)
    - Conversa informal ou cumprimentos
    - Calculos matematicos ou datas (use calcular_prazos_cdc)
    - Classificar condutas especificas (use classificar_pratica_abusiva)

    Args:
        pergunta: pergunta do usuario sobre direito do consumidor
    """
    try:
        resultado = _buscar_rag(pergunta)
        resposta = resultado["resposta"]
        fontes = ", ".join(resultado["fontes"])
        return f"{resposta}\n\n📚 Fontes: {fontes}"
    except FileNotFoundError:
        return (
            "⚠️ Base de conhecimento do CDC nao encontrada. "
            "Coloque documentos .txt na pasta data/ e reinicie.\n\n"
            "Enquanto isso, posso responder com conhecimento geral."
        )
    except Exception as e:
        return f"❌ Erro ao consultar CDC: {str(e)}"


# ============================================================
# Tool 2: Calculadora de prazos do CDC
# ============================================================

@tool
def calcular_prazos_cdc(
    tipo_prazo: str,
    data_evento: str = "",
) -> str:
    """
    Calcula prazos legais do CDC a partir de uma data.

    USE quando o usuario perguntar sobre:
    - "Ate quando posso reclamar de um defeito?"
    - "Qual o prazo para trocar um produto?"
    - "Ainda esta no prazo de arrependimento?"
    - Calculo de datas de vencimento de direitos

    TIPOS DE PRAZO aceitos:
    - 'arrependimento': 7 dias (Art. 49)
    - 'vicios_nao_duraveis': 30 dias (Art. 26, I)
    - 'vicios_duraveis': 90 dias (Art. 26, II)
    - 'reparacao_danos': 5 anos (Art. 27)
    - 'garantia_legal': 90 dias (Art. 26)

    NAO USE para perguntas que nao envolvem calculo de datas.

    Args:
        tipo_prazo: um dos tipos acima
        data_evento: data no formato DD/MM/AAAA (ex: '15/03/2026').
                     Se nao informada, usa a data de hoje.
    """
    prazos = {
        "arrependimento": (7, "Art. 49 — Direito de arrependimento"),
        "vicios_nao_duraveis": (30, "Art. 26, I — Vicios em produtos nao duraveis"),
        "vicios_duraveis": (90, "Art. 26, II — Vicios em produtos duraveis"),
        "reparacao_danos": (5 * 365, "Art. 27 — Reparacao de danos"),
        "garantia_legal": (90, "Art. 26 — Garantia legal (duraveis)"),
    }

    if tipo_prazo not in prazos:
        return (
            f"Tipo de prazo '{tipo_prazo}' nao reconhecido.\n"
            f"Tipos validos: {', '.join(prazos.keys())}"
        )

    if data_evento:
        try:
            data = datetime.strptime(data_evento, "%d/%m/%Y")
        except ValueError:
            return "Formato de data invalido. Use DD/MM/AAAA (ex: 15/03/2026)."
    else:
        data = datetime.now()

    dias, fundamento = prazos[tipo_prazo]
    data_limite = data + timedelta(days=dias)

    return (
        f"📅 Data do evento: {data.strftime('%d/%m/%Y')}\n"
        f"⏱️ Prazo: {dias} dias\n"
        f"📅 Data limite: {data_limite.strftime('%d/%m/%Y')}\n"
        f"📜 Fundamento: {fundamento}"
    )


# ============================================================
# Tool 3: Classificador de pratica abusiva
# ============================================================

@tool
def classificar_pratica_abusiva(descricao: str) -> str:
    """
    Analisa se uma conduta de fornecedor se enquadra como pratica abusiva
    segundo o Art. 39 do CDC.

    USE quando o usuario descrever uma situacao com um fornecedor e perguntar:
    - "Isso eh abusivo?"
    - "O que a loja fez eh legal?"
    - "Posso processar por essa conduta?"
    - "Isso eh venda casada?"

    NAO USE para perguntas genericas sobre o CDC (use consultar_cdc).
    NAO USE se o usuario nao descreveu uma conduta especifica.

    Args:
        descricao: descricao da conduta do fornecedor
    """
    incisos = {
        "venda casada": ("I", "Condicionar fornecimento a outro produto/servico"),
        "recusa": ("II e IX", "Recusar atendimento ou venda sem justa causa"),
        "envio nao solicitado": ("III", "Enviar produto sem solicitacao previa"),
        "fraqueza": ("IV", "Prevalecer-se da fraqueza ou ignorancia do consumidor"),
        "vantagem excessiva": ("V", "Exigir vantagem manifestamente excessiva"),
        "sem orcamento": ("VI", "Executar servicos sem orcamento previo"),
        "normas": ("VIII", "Produto/servico em desacordo com normas oficiais"),
    }

    descricao_lower = descricao.lower()
    encontrados = [
        f"  • Inciso {info[0]}: {info[1]}"
        for chave, info in incisos.items()
        if chave in descricao_lower
    ]

    if encontrados:
        return (
            f"⚠️ Conduta potencialmente ABUSIVA detectada:\n\n"
            f"Descricao: \"{descricao[:200]}\"\n\n"
            f"Possiveis enquadramentos (Art. 39, CDC):\n" +
            "\n".join(encontrados) +
            "\n\n💡 Recomendacao: Registre reclamacao no Procon e documente "
            "todas as evidencias (prints, e-mails, notas fiscais)."
        )
    return (
        f"A conduta descrita nao corresponde diretamente a uma pratica "
        f"abusiva listada no Art. 39 do CDC.\n\n"
        f"Descricao: \"{descricao[:200]}\"\n\n"
        f"💡 Para analise mais precisa, use 'consultar_cdc' ou procure "
        f"um advogado especializado."
    )


# ============================================================
# Tool 4: Orgaos de defesa do consumidor
# ============================================================

@tool
def orgaos_defesa(estado: str = "") -> str:
    """
    Informa os orgaos de defesa do consumidor disponiveis.

    USE quando o usuario perguntar:
    - "Onde posso reclamar?"
    - "Qual o telefone do Procon?"
    - "Como faco uma denuncia?"
    - "Quais orgaos protegem o consumidor?"

    Args:
        estado: sigla do estado (ex: 'SP', 'RJ'). Se vazio, lista todos.
    """
    return (
        "🏛️ ORGAOS DE DEFESA DO CONSUMIDOR:\n\n"
        "  • Senacon: Secretaria Nacional do Consumidor\n"
        "    www.gov.br/mj/pt-br/acesso-a-informacao/consumidor\n\n"
        "  • Procon: Procons estaduais e municipais\n"
        "    Procure 'Procon + sua cidade'\n\n"
        "  • Defensoria Publica: nucleo do consumidor\n\n"
        "  • Juizados Especiais Civeis: causas ate 20 salarios minimos\n\n"
        "  • Ministerio Publico: promotoria de defesa do consumidor\n\n"
        "  • consumidor.gov.br: plataforma oficial de resolucao online\n\n"
        "📞 Disque-Denuncia Procon: 151\n"
        "🌐 Plataforma online: www.consumidor.gov.br\n\n"
        "💡 Dica: Sempre tente resolver diretamente com o fornecedor primeiro. "
        "Documente tudo: protocolos, e-mails, prints e notas fiscais."
    )


# ============================================================
# Lista de tools do agente
# ============================================================

def get_tools() -> list:
    """Retorna as 4 tools do agente (todas independentes)."""
    return [
        calcular_prazos_cdc,
        classificar_pratica_abusiva,
        orgaos_defesa,
        consultar_cdc,
    ]
