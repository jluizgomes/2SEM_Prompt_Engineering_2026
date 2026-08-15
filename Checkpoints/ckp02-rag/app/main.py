"""
CKP02 — DocMind RAG · Consultor CDC
====================================
Interface Gradio + Pipeline RAG + Comparação de Chunking

Uso:
    python -m app.main              # Interface Gradio (web)
    python -m app.main --index      # Indexar documentos
    python -m app.main --compare    # Comparar chunking + RAGAS
    python -m app.main --query "..." # Consulta via terminal
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

import gradio as gr
from .pipeline import pipeline_completo, buscar, load_vectorstore, DATA_DIR


# ============================================================
# Interface Gradio
# ============================================================

def criar_interface() -> gr.Blocks:
    """Constrói a interface Gradio do DocMind RAG."""

    vs = None  # lazy load

    def responder(message: str, history: list) -> str:
        nonlocal vs
        if vs is None:
            vs = load_vectorstore()

        try:
            resultado = buscar(message, vs)
            resposta = resultado["resposta"]
            fontes = resultado["fontes"]

            # Formata resposta com fontes
            resposta_formatada = f"{resposta}\n\n---\n📚 **Fontes consultadas:**\n"
            for f in fontes:
                resposta_formatada += f"  • {f}\n"
            return resposta_formatada
        except Exception as e:
            return f"❌ Erro: {str(e)}\n\nCertifique-se de indexar os documentos primeiro:\n`python -m app.main --index`"

    with gr.Blocks(
        title="DocMind CDC — RAG",
        theme=gr.themes.Soft(primary_hue="blue"),
    ) as demo:
        gr.Markdown(
            """
        # 📚 DocMind CDC — Assistente Jurídico com RAG

        **Pipeline RAG sobre o Código de Defesa do Consumidor (Lei 8.078/90)**

        Faça perguntas sobre o CDC. As respostas são baseadas exclusivamente
        nos documentos indexados, com citação de fonte.
        """
        )

        chatbot = gr.ChatInterface(
            fn=responder,
            title="",
            examples=[
                "Quais são os direitos básicos do consumidor?",
                "Qual o prazo para desistir de uma compra online?",
                "O que é considerado prática abusiva pelo CDC?",
                "Como funciona a proteção contratual no CDC?",
            ],
            chatbot=gr.Chatbot(height=500),
        )

        gr.Markdown(
            """
        > ⚠️ **Disclaimer:** Respostas baseadas exclusivamente nos documentos indexados.
        > Não substitui consulta com um advogado especializado.
        """,
        )

    return demo


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    if "--index" in sys.argv:
        # Indexar documentos
        print("📄 Indexando documentos...")
        vs = pipeline_completo(force_reindex=True)
        print("✅ Indexação concluída!")

    elif "--compare" in sys.argv:
        # Comparar chunking strategies
        from .chunking import comparar_chunking, gerar_tabela_comparativa, gerar_tabela_por_pergunta

        print("🔬 Comparando estratégias de chunking...")
        resultados = comparar_chunking(chunk_sizes=[256, 512, 1024])

        print("\n" + gerar_tabela_comparativa(resultados))
        print("\n" + gerar_tabela_por_pergunta(resultados))

        melhor = max(resultados, key=lambda r: r["media_faithfulness"])
        print(f"\n🏆 Melhor configuração: chunk_size={melhor['chunk_size']} "
              f"(faithfulness={melhor['media_faithfulness']:.3f})")

    elif "--query" in sys.argv:
        # Consulta via terminal
        idx = sys.argv.index("--query")
        query = " ".join(sys.argv[idx + 1:]) if idx + 1 < len(sys.argv) else ""
        if query:
            resultado = buscar(query)
            print(f"\n📝 Pergunta: {query}")
            print(f"📚 Fontes: {resultado['fontes']}")
            print(f"\n💬 Resposta:\n{resultado['resposta']}")
        else:
            print("Uso: python -m app.main --query 'sua pergunta aqui'")

    else:
        # Interface Gradio
        print("🚀 Iniciando DocMind CDC — RAG...")
        print(f"   Ollama: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
        print(f"   Modelo: {os.getenv('CHAT_MODEL', 'qwen3.5:0.8b')}")
        print(f"   ChromaDB: {os.getenv('CHROMADB_PERSIST_DIR', './chromadb_data')}")
        print("   ⚠️ Execute '--index' primeiro se for a primeira execução!")
        print("   Acesse: http://localhost:7860\n")
        demo = criar_interface()
        demo.launch(server_name="0.0.0.0", server_port=7860)
