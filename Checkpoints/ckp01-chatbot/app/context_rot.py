"""
Demonstração de Context Rot (degradação de qualidade com contexto crescente).

CKP01 exige: seção mostrando degradação de qualidade com contexto crescente —
mesmo prompt, janelas de tokens diferentes. Apresentar em gráfico ou tabela.

O que é Context Rot:
Quando o histórico de conversa cresce muito, o LLM começa a:
- Perder o foco no system prompt
- Misturar informações de turnos antigos com o atual
- Dar respostas menos relevantes e menos precisas

Esta seção demonstra esse fenômeno com um experimento controlado.
"""

import time
from typing import Optional
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


def simular_context_rot_em_turnos(
    llm: ChatOllama,
    pergunta_teste: str,
    max_turnos: int = 20,
    system_prompt: Optional[str] = None,
) -> list[dict]:
    """
    Simula conversa longa e mede degradação de qualidade ao longo dos turnos.

    Estratégia:
    1. Enche o histórico com mensagens sintéticas (usuário + assistente)
       simulando uma conversa técnica prolongada
    2. A cada 5 turnos, insere a pergunta_teste
    3. Mede latência, tamanho da resposta e (se possível) relevância

    Args:
        llm: modelo configurado
        pergunta_teste: pergunta que será repetida a cada checkpoint
        max_turnos: número total de turnos simulados
        system_prompt: prompt de sistema (se None, usa padrão)

    Returns:
        lista de dicts com métricas por checkpoint
    """
    from .prompts import SYSTEM_PROMPT_CONTEXT_ROT

    system_prompt = system_prompt or SYSTEM_PROMPT_CONTEXT_ROT

    # Histórico sintético simulando conversa densa sobre CDC
    historico_base = [
        (
            "O que diz o Art. 18 do CDC sobre produtos com defeito?",
            "O Art. 18 do CDC estabelece que os fornecedores são solidariamente responsáveis "
            "pelos vícios de qualidade que tornem produtos impróprios ao consumo. O consumidor "
            "pode exigir: substituição do produto, restituição da quantia paga, ou abatimento "
            "proporcional do preço. O prazo para reclamar é de 30 dias para produtos não duráveis "
            "e 90 dias para duráveis, conforme Art. 26."
        ),
        (
            "Qual a diferença entre vício e defeito no CDC?",
            "Vício (Arts. 18-21) é um problema que compromete o funcionamento mas não oferece "
            "risco à segurança. Defeito (Arts. 12-17) é quando o produto ou serviço causa dano "
            "à saúde ou segurança do consumidor — é o 'acidente de consumo'. A diferença está "
            "no dano causado: vício afeta a qualidade; defeito afeta a segurança."
        ),
        (
            "Como funciona o direito de arrependimento?",
            "O Art. 49 do CDC garante 7 dias para o consumidor se arrepender de compras "
            "feitas fora do estabelecimento comercial (internet, telefone, catálogo). "
            "O prazo conta da data da assinatura do contrato ou do recebimento do produto. "
            "O consumidor tem direito à devolução integral dos valores pagos, inclusive frete."
        ),
    ]

    resultados = []

    for checkpoint in range(0, max_turnos + 1, 5):
        # Constrói histórico com N turnos
        messages: list = [SystemMessage(content=system_prompt)]

        for i in range(checkpoint):
            user_q, assistant_a = historico_base[i % len(historico_base)]
            # Adiciona ruído progressivo para simular conversa longa real
            if i > 10:
                user_q += f" (contexto adicional #{i}: discussão sobre jurisprudência do STJ)"
            messages.append(HumanMessage(content=user_q))
            messages.append(AIMessage(content=assistant_a))

        # Adiciona a pergunta de teste
        messages.append(HumanMessage(content=pergunta_teste))

        # Mede latência
        t0 = time.time()
        response = llm.invoke(messages)
        latencia = time.time() - t0

        # Registra métricas
        resultados.append(
            {
                "checkpoint": checkpoint,
                "mensagens_no_contexto": len(messages),
                "tokens_estimados": _estimar_tokens(messages),
                "latencia_segundos": round(latencia, 2),
                "tamanho_resposta": len(response.content),
                "resposta": str(response.content)[:200] + "...",  # truncado para tabela
            }
        )

        print(
            f"  Turno {checkpoint:2d} | "
            f"Msgs: {len(messages):3d} | "
            f"Tokens~: {resultados[-1]['tokens_estimados']:5d} | "
            f"Lat: {latencia:.2f}s | "
            f"Resp: {len(response.content):4d} chars"
        )

    return resultados


def _estimar_tokens(messages: list) -> int:
    """Estimativa rápida: ~4 chars por token (português)"""
    total_chars = sum(len(str(m.content)) for m in messages if hasattr(m, "content"))
    return total_chars // 4


def gerar_tabela_context_rot(resultados: list[dict]) -> str:
    """
    Gera tabela formatada para documentação do context rot.
    """
    header = (
        "| Checkpoint | Msgs Contexto | Tokens Est. | Latência (s) | Tamanho Resp | Observação |\n"
        "|-----------|--------------|------------|-------------|-------------|------------|"
    )

    rows = []
    for r in resultados:
        obs = (
            "🟢 Boa"
            if r["checkpoint"] <= 5
            else "🟡 Aceitável"
            if r["checkpoint"] <= 10
            else "🔴 Degradação visível"
        )
        rows.append(
            f"| {r['checkpoint']:3d} | {r['mensagens_no_contexto']:4d} | "
            f"{r['tokens_estimados']:5d} | {r['latencia_segundos']:7.2f} | "
            f"{r['tamanho_resposta']:5d} | {obs} |"
        )

    return "\n".join([header] + rows)


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv()

    llm = ChatOllama(
        model=os.getenv("CHAT_MODEL", "qwen3.5:0.8b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.3,
    )

    pergunta = "Produto com defeito após 6 meses de uso — quais os prazos legais?"
    resultados = simular_context_rot_em_turnos(llm, pergunta, max_turnos=20)
    print("\n" + "=" * 80)
    print(gerar_tabela_context_rot(resultados))
