"""
Gestão de memória conversacional.

Compara 3 estratégias:
- ConversationBufferMemory (guarda tudo — mais caro, mais preciso)
- ConversationBufferWindowMemory (janela de N turnos — intermediário)
- ConversationSummaryMemory (resumo — mais barato, menos preciso)

CKP01 exige: 1 tipo de memória, justificada, demonstrada em ≥5 turnos.
"""

from langchain_classic.memory import (
    ConversationBufferMemory,
    ConversationBufferWindowMemory,
    ConversationSummaryMemory,
)
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage


def create_buffer_memory() -> ConversationBufferMemory:
    """
    Memória completa — guarda todas as mensagens.
    Vantagem: precisão máxima.
    Desvantagem: custo de tokens cresce a cada turno.
    Uso: consultas curtas (≤10 turnos) onde precisão é crítica.
    """
    return ConversationBufferMemory(
        return_messages=True,
        memory_key="history",
        input_key="input",
    )


def create_window_memory(k: int = 6) -> ConversationBufferWindowMemory:
    """
    Janela deslizante — guarda apenas os últimos k turnos.
    Vantagem: custo de tokens constante após k turnos.
    Desvantagem: perde contexto de conversas muito longas.
    Uso: recomendado para este domínio (consultas jurídicas de 5-10 turnos).

    Args:
        k: número de interações (pares user-assistant) a manter
    """
    return ConversationBufferWindowMemory(
        k=k,
        return_messages=True,
        memory_key="history",
        input_key="input",
    )


def create_summary_memory(llm: ChatOllama) -> ConversationSummaryMemory:
    """
    Memória com sumarização — resume conversas anteriores.
    Vantagem: custo de tokens mínimo.
    Desvantagem: perda de detalhes específicos (ex: números de artigo).
    Uso: consultas muito longas (>15 turnos) ou quando custo é prioridade.

    Args:
        llm: modelo usado para gerar o resumo
    """
    return ConversationSummaryMemory(
        llm=llm,
        return_messages=True,
        memory_key="history",
        input_key="input",
    )


def get_recommended_memory():
    """
    Retorna a memória recomendada para o domínio CDC.

    Justificativa:
    Consultas jurídicas típicas duram 5-8 turnos.
    Window(k=6) mantém custo constante sem perder contexto relevante —
    um consultor não precisa lembrar o que foi dito há 15 turnos atrás
    para responder a pergunta atual.
    """
    return create_window_memory(k=6)
