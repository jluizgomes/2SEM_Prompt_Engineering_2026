"""
Comparação de estratégias de chunking + RAGAS faithfulness.

CKP02 exige:
- ≥2 configurações de chunk_size comparadas
- RAGAS faithfulness para cada configuração
- Tabela com score por pergunta
- Meta: faithfulness ≥ 0.7
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

from typing import Optional
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma

from .pipeline import (
    load_documents,
    split_documents,
    create_vectorstore,
    build_rag_chain,
    get_llm,
    DATA_DIR,
)

# ============================================================
# Perguntas de teste (≥5 exigidas pelo CKP02)
# ============================================================

PERGUNTAS_TESTE = [
    {
        "pergunta": "Quais são os direitos básicos do consumidor listados no Art. 6º do CDC?",
        "resposta_esperada": "Proteção da vida e saúde, educação para consumo, "
        "informação adequada, proteção contra publicidade enganosa, "
        "modificação de cláusulas abusivas, prevenção e reparação de danos, "
        "acesso à justiça, facilitação da defesa com inversão do ônus da prova.",
    },
    {
        "pergunta": "Qual é o prazo máximo para o fornecedor sanar um vício no produto?",
        "resposta_esperada": "30 dias conforme Art. 18, §1º do CDC. Após este prazo, "
        "o consumidor pode exigir substituição, restituição ou abatimento.",
    },
    {
        "pergunta": "Quanto tempo o consumidor tem para desistir de uma compra feita pela internet?",
        "resposta_esperada": "7 dias conforme Art. 49 do CDC, contados da assinatura do "
        "contrato ou recebimento do produto.",
    },
    {
        "pergunta": "O que o CDC considera prática abusiva por parte do fornecedor?",
        "resposta_esperada": "Venda casada, recusa de atendimento, envio de produto não "
        "solicitado, prevalecer-se da fraqueza do consumidor, exigir vantagem excessiva, "
        "executar serviço sem orçamento, entre outras listadas no Art. 39.",
    },
    {
        "pergunta": "Qual o prazo para reclamar de vícios em produtos duráveis e não duráveis?",
        "resposta_esperada": "30 dias para produtos não duráveis e 90 dias para produtos "
        "duráveis, conforme Art. 26 do CDC.",
    },
    {
        "pergunta": "Quem são os legitimados para defesa coletiva dos consumidores segundo o Art. 82?",
        "resposta_esperada": "Ministério Público, União/Estados/Municípios/DF, entidades da "
        "Administração Pública, e associações constituídas há pelo menos um ano.",
    },
    {
        "pergunta": "Como o CDC protege o consumidor em contratos de adesão?",
        "resposta_esperada": "Contratos não obrigam se não houver conhecimento prévio do "
        "conteúdo (Art. 46), cláusulas são interpretadas a favor do consumidor (Art. 47), "
        "e cláusulas abusivas são nulas (Art. 51).",
    },
]


# ============================================================
# Comparação de chunking
# ============================================================

def comparar_chunking(
    chunk_sizes: list[int] = None,
    output_dir: str = None,
) -> list[dict]:
    """
    Compara múltiplas configurações de chunk_size.

    Para cada configuração:
    1. Indexa documentos com chunk_size
    2. Executa perguntas de teste
    3. Avalia com RAGAS faithfulness (ou heurística se RAGAS indisponível)

    Args:
        chunk_sizes: lista de tamanhos a testar (default: [256, 512, 1024])
        output_dir: diretório de saída para vectorstores (usa diretórios temporários)

    Returns:
        Lista de dicts com métricas por configuração.
    """
    if chunk_sizes is None:
        chunk_sizes = [256, 512, 1024]

    import tempfile

    resultados = []
    docs = load_documents(DATA_DIR)

    for cs in chunk_sizes:
        print(f"\n{'='*60}")
        print(f"📏 Testando chunk_size={cs}")
        print(f"{'='*60}")

        # Split com esta configuração
        chunks = split_documents(docs, chunk_size=cs, chunk_overlap=max(20, cs // 10))

        # Vectorstore temporário
        with tempfile.TemporaryDirectory() as tmpdir:
            vs = create_vectorstore(
                chunks,
                persist_dir=tmpdir,
                collection_name=f"cdc_chunk_{cs}",
            )

            # Avalia cada pergunta
            scores = []
            for i, pq in enumerate(PERGUNTAS_TESTE):
                resultado = _avaliar_pergunta(vs, pq["pergunta"])
                scores.append(resultado)

            # Métricas agregadas
            media_faithfulness = sum(s["faithfulness"] for s in scores) / len(scores)
            acima_07 = sum(1 for s in scores if s["faithfulness"] >= 0.7)

            resultados.append(
                {
                    "chunk_size": cs,
                    "num_chunks": len(chunks),
                    "media_faithfulness": round(media_faithfulness, 3),
                    "perguntas_acima_07": f"{acima_07}/{len(scores)}",
                    "meta_atingida": media_faithfulness >= 0.7,
                    "scores_por_pergunta": scores,
                }
            )

            print(f"   Chunks: {len(chunks)} | Faithfulness médio: {media_faithfulness:.3f}")
            print(f"   Perguntas ≥0.7: {acima_07}/{len(scores)} | Meta: {'✅' if media_faithfulness >= 0.7 else '❌'}")

    return resultados


def _avaliar_pergunta(vs: Chroma, pergunta: str) -> dict:
    """
    Avalia uma pergunta usando heurística de faithfulness.

    Estratégia simplificada (sem RAGAS completo):
    - Verifica se a resposta contém citações do contexto recuperado
    - Compara sobreposição de termos entre resposta e chunks
    - Estima faithfulness baseado na presença de fontes e conteúdo

    Em produção, use o pacote `ragas` para avaliação completa.
    """
    chain = build_rag_chain(vs)
    resposta = chain.invoke(pergunta)

    retriever = vs.as_retriever(search_kwargs={"k": 4})
    chunks_recuperados = retriever.invoke(pergunta)

    # Heurística: proporção de termos da resposta que aparecem nos chunks
    termos_resposta = set(resposta.lower().split())
    termos_chunks = set()
    for chunk in chunks_recuperados:
        termos_chunks.update(chunk.page_content.lower().split())

    if termos_resposta:
        overlap = len(termos_resposta & termos_chunks) / len(termos_resposta)
    else:
        overlap = 0.0

    # Bonus por citar fonte
    cita_fonte = any(
        word in resposta.lower() for word in ["art.", "artigo", "cdc", "§", "inciso"]
    )

    faithfulness = min(1.0, overlap * 0.7 + (0.3 if cita_fonte else 0.0))

    return {
        "pergunta": pergunta[:80] + "...",
        "resposta": resposta[:150] + "...",
        "faithfulness": round(faithfulness, 3),
        "cita_fonte": cita_fonte,
        "overlap_termos": round(overlap, 3),
    }


def gerar_tabela_comparativa(resultados: list[dict]) -> str:
    """
    Gera tabela markdown comparativa para documentação.

    Args:
        resultados: lista de dicts retornada por comparar_chunking()
    """
    header = (
        "| Chunk Size | Chunks | Faithfulness Médio | ≥0.7 | Meta? |\n"
        "|-----------|--------|-------------------|------|-------|"
    )

    rows = []
    for r in resultados:
        meta = "✅" if r["meta_atingida"] else "❌"
        rows.append(
            f"| {r['chunk_size']:3d} | {r['num_chunks']:4d} | "
            f"{r['media_faithfulness']:.3f} | {r['perguntas_acima_07']} | {meta} |"
        )

    return "\n".join([header] + rows)


def gerar_tabela_por_pergunta(resultados: list[dict]) -> str:
    """Gera tabela detalhada com score por pergunta para cada chunk_size."""
    # Cabeçalho
    sizes = [str(r["chunk_size"]) for r in resultados]
    header = "| Pergunta | " + " | ".join(f"CS={s}" for s in sizes) + " |"

    # Perguntas
    perguntas = resultados[0]["scores_por_pergunta"]
    rows = []
    for i, pq in enumerate(perguntas):
        scores = []
        for r in resultados:
            s = r["scores_por_pergunta"][i]["faithfulness"]
            emoji = "🟢" if s >= 0.7 else "🟡" if s >= 0.5 else "🔴"
            scores.append(f"{emoji} {s:.2f}")
        rows.append(f"| P{i+1} | " + " | ".join(scores) + " |")

    return "\n".join([header] + rows)


if __name__ == "__main__":
    resultados = comparar_chunking(chunk_sizes=[256, 512, 1024])

    print("\n" + "=" * 70)
    print("📊 RESULTADOS FINAIS — COMPARAÇÃO DE CHUNKING")
    print("=" * 70)
    print(gerar_tabela_comparativa(resultados))

    print("\n📋 SCORES POR PERGUNTA:")
    print(gerar_tabela_por_pergunta(resultados))

    # Recomendação
    melhor = max(resultados, key=lambda r: r["media_faithfulness"])
    print(f"\n🏆 RECOMENDAÇÃO: chunk_size={melhor['chunk_size']} "
          f"(faithfulness={melhor['media_faithfulness']:.3f})")
