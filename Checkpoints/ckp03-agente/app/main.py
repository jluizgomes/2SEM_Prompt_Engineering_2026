"""
CKP03 — Agente Inteligente · Consultor CDC
===========================================
Agente ReAct com 4 tools + RAG + Gradio com URL pública

Uso:
    python -m app.main              # Interface Gradio (web, URL pública)
    python -m app.main --local      # Interface Gradio (apenas local)
    python -m app.main --test       # Teste rápido com 6 perguntas
    python -m app.main --guardrail  # Testar guardrail de input
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

import gradio as gr
from .agent import consultar_agente, criar_agente_react


# ============================================================
# Interface Gradio
# ============================================================

def criar_interface() -> gr.Blocks:
    """Constrói a interface Gradio do Agente Inteligente."""

    # Estados por sessão
    session_counter = {"count": 0}

    def responder(message: str, history: list) -> str:
        """Callback do Gradio ChatInterface."""
        resultado = consultar_agente(message, verbose=False)
        session_counter["count"] += 1

        if resultado["bloqueado"]:
            return f"🚫 {resultado['resposta']}"

        # Adiciona indicador visual da tool usada (se disponível)
        resposta = resultado["resposta"]
        return resposta

    with gr.Blocks(
        title="Dr. Consumidor — Agente Inteligente",
        theme=gr.themes.Soft(primary_hue="red"),
        css="""
        .disclaimer {
            font-size: 0.8em; color: #666; padding: 8px;
            background: #fff3cd; border-radius: 8px; margin: 4px 0;
        }
        .tool-indicator {
            font-size: 0.7em; color: #888; font-style: italic;
        }
        """,
    ) as demo:
        gr.Markdown(
            """
        # ⚖️ Dr. Consumidor — Agente Inteligente

        **Agente especializado em Direito do Consumidor com 4 ferramentas:**

        | Ferramenta | Quando usar |
        |---|---|
        | 📅 **Calcular prazos** | Datas de garantia, arrependimento, reclamação |
        | ⚠️ **Classificar prática abusiva** | Conduta suspeita de fornecedor |
        | 🏛️ **Órgãos de defesa** | Onde e como reclamar |
        | 📚 **Consultar CDC** | Base completa do Código de Defesa do Consumidor |

        O agente decide **automaticamente** qual ferramenta usar para cada pergunta.
        Se nenhuma ferramenta for necessária, responde diretamente.
        """
        )

        chatbot = gr.ChatInterface(
            fn=responder,
            title="",
            examples=[
                "Comprei um celular em 10/08/2026 e veio com defeito. Até quando posso reclamar?",
                "A loja me obrigou a contratar um seguro junto com o financiamento. Isso é legal?",
                "Onde posso registrar uma reclamação contra uma empresa?",
                "Quais são as sanções que uma empresa pode sofrer por violar o CDC?",
                "Oi, tudo bem? Quanto é 2+2?",  # Sem tool
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
        )

    return demo


# ============================================================
# Teste com 6 perguntas (requisito CKP03)
# ============================================================

def executar_teste():
    """
    Executa 6 perguntas de teste cobrindo todos os cenários:
    - 2 que exigem RAG (consultar_cdc)
    - 2 que exigem outra tool
    - 2 que não exigem tool nenhuma
    """
    perguntas_teste = [
        # 2 com RAG
        ("RAG", "Quais são os direitos básicos do consumidor listados no Art. 6º do CDC?"),
        ("RAG", "O que diz o Art. 39 sobre práticas abusivas?"),
        # 2 com outras tools
        ("Tool", "Comprei um produto online em 15/08/2026. Até quando posso me arrepender?"),
        ("Tool", "A loja se recusou a me vender à vista e exigiu que eu fizesse um crediário. Isso é prática abusiva?"),
        # 2 sem tool
        ("Nenhuma", "Olá, bom dia! Quem é você?"),
        ("Nenhuma", "Obrigado pelas informações!"),
    ]

    print("\n" + "=" * 70)
    print("🧪 TESTE DO AGENTE — 6 PERGUNTAS (requisito CKP03)")
    print("=" * 70)

    for i, (tipo, pergunta) in enumerate(perguntas_teste, 1):
        print(f"\n--- Pergunta {i}/6 [{tipo}] ---")
        print(f"👤 {pergunta}")
        resultado = consultar_agente(pergunta, verbose=False)
        print(f"🤖 {resultado['resposta'][:200]}...")
        print(f"🔧 Tool: {resultado['tool_usada']} | Bloqueado: {resultado['bloqueado']}")

    print("\n" + "=" * 70)
    print("✅ Teste concluído! Verifique acima se o agente usou as tools corretas.")
    print("=" * 70)


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    if "--test" in sys.argv:
        executar_teste()

    elif "--guardrail" in sys.argv:
        from .guardrail import validar_input

        testes = [
            "Comprei um celular com defeito",
            "Fui demitido, quais meus direitos?",
            "Oi, tudo bem?",
            "Como declarar imposto de renda?",
            "Qual o prazo de garantia de uma geladeira?",
        ]
        for t in testes:
            ok, msg = validar_input(t)
            status = "✅ PASSOU" if ok else "🚫 BLOQUEADO"
            print(f"{status} | {t}")

    else:
        share = "--local" not in sys.argv
        share_env = os.getenv("GRADIO_SHARE", "true").lower() == "true"
        usar_share = share and share_env

        print("🤖 Iniciando Dr. Consumidor — Agente Inteligente...")
        print(f"   Modelo: {os.getenv('CHAT_MODEL', 'qwen3.5:0.8b')}")
        print(f"   Tools: calcular_prazos_cdc, classificar_pratica_abusiva, "
              f"orgaos_defesa, consultar_cdc (RAG proprio)")
        print(f"   Guardrail: ativo")
        print(f"   URL publica: {'Sim' if usar_share else 'Nao (--local)'}")
        print("   Acesse: http://localhost:7860\n")

        demo = criar_interface()
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=usar_share,
        )
