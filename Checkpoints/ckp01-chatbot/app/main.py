"""
CKP01 — Chatbot Profissional · Consultor CDC
=============================================
Interface Gradio + Pipeline LCEL + Memória + Pydantic + Context Rot

Uso:
    python -m app.main          # Interface Gradio (web)
    python -m app.main --demo   # Demo context rot (terminal)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Garante que a raiz do projeto está no path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

import gradio as gr
from langchain_core.messages import HumanMessage, AIMessage

from .chain import build_chain
from .memory_manager import get_recommended_memory
from .schemas import AnaliseConsulta
from .prompts import SYSTEM_PROMPT_CDC


# ============================================================
# Histórico de conversa (mantido entre turnos)
# ============================================================

def criar_chatbot():
    """
    Retorna função de callback para Gradio ChatInterface.

    A função gerencia o histórico de conversa utilizando
    ConversationBufferWindowMemory (k=6), justificada no memory_manager.py.
    """
    chain = build_chain()
    memory = get_recommended_memory()

    # Histórico como lista de dicionários (formato Gradio)
    history_state: list[dict] = []

    def responder(message: str, history: list[dict]) -> str:
        """
        Processa uma mensagem do usuário e retorna a resposta do chatbot.

        Fluxo:
        1. Constrói histórico LangChain a partir do histórico Gradio
        2. Invoca a chain LCEL com input + histórico
        3. Atualiza o histórico e retorna a resposta
        """
        # Constrói histórico em formato LangChain
        lc_history = []
        for msg in history:
            if msg["role"] == "user":
                lc_history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_history.append(AIMessage(content=msg["content"]))

        # Limita ao tamanho da janela (k=6 interações)
        if len(lc_history) > 12:  # 6 pares user+assistant
            lc_history = lc_history[-12:]

        # Invoca a chain
        try:
            response = chain.invoke({"input": message, "history": lc_history})
        except Exception as e:
            response = (
                f"❌ Erro ao processar sua consulta: {str(e)}\n\n"
                "Verifique se o Ollama está rodando e a API key está configurada."
            )

        return response

    return responder


# ============================================================
# Interface Gradio
# ============================================================

def criar_interface() -> gr.Blocks:
    """Constrói a interface Gradio completa."""

    responder = criar_chatbot()

    with gr.Blocks(
        title="Dr. Consumidor — Consultor CDC",
        theme=gr.themes.Soft(primary_hue="red"),
        css="""
        .disclaimer {
            font-size: 0.8em;
            color: #666;
            padding: 8px;
            background: #fff3cd;
            border-radius: 8px;
            margin: 4px 0;
        }
        """,
    ) as demo:
        gr.Markdown(
            """
        # ⚖️ Dr. Consumidor — Consultor CDC

        **Especialista em Direito do Consumidor Brasileiro** (Lei 8.078/90)

        Faça perguntas sobre: garantia, arrependimento, vícios, defeitos,
        práticas abusivas, contratos, cobrança indevida e mais.
        """
        )

        chatbot = gr.ChatInterface(
            fn=responder,
            title="",
            description="",
            examples=[
                "Comprei um celular online e ele veio com defeito. Quais meus direitos?",
                "Qual o prazo para desistir de uma compra feita pela internet?",
                "A loja se recusa a trocar um produto com defeito. O que fazer?",
                "O que é considerado prática abusiva pelo CDC?",
            ],
            chatbot=gr.Chatbot(height=500),
        )

        gr.Markdown(
            """
        <div class="disclaimer">
        ⚠️ <strong>Disclaimer:</strong> Esta é uma orientação informativa baseada no CDC.
        Não substitui consulta com um advogado especializado.
        </div>
        """,
            label=None,
        )

    return demo


# ============================================================
# Demo Context Rot (terminal)
# ============================================================

def demo_context_rot():
    """Executa demonstração de context rot no terminal."""
    from .context_rot import simular_context_rot_em_turnos, gerar_tabela_context_rot
    from .chain import get_llm

    print("\n" + "=" * 70)
    print(" 🔬 EXPERIMENTO: Context Rot — Degradação com Contexto Crescente")
    print("=" * 70)
    print(
        "Pergunta teste: 'Produto com defeito após 6 meses de uso — "
        "quais os prazos legais?'\n"
    )

    llm = get_llm()
    resultados = simular_context_rot_em_turnos(llm, pergunta_teste="", max_turnos=20)

    # Reexecuta com a pergunta certa (na simulação acima usou string vazia)
    resultados = simular_context_rot_em_turnos(
        llm,
        pergunta_teste="Produto com defeito após 6 meses de uso — quais os prazos legais?",
        max_turnos=20,
    )

    print("\n" + gerar_tabela_context_rot(resultados))
    print(
        "\n📊 CONCLUSÃO: A partir de ~15 turnos, a qualidade da resposta começa a "
        "degradar visivelmente — o modelo perde precisão nos artigos e prazos citados."
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo_context_rot()
    else:
        print("🚀 Iniciando Dr. Consumidor — Consultor CDC...")
        print(f"   Modelo: {os.getenv('CHAT_MODEL', 'qwen3.5:0.8b')}")
        print(f"   Ollama: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
        print("   Acesse: http://localhost:7860\n")
        demo = criar_interface()
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,  # True para URL pública (CKP03)
        )
