"""
Agente ReAct — CKP03

Suporta dois modos:
1. AgentExecutor (LangChain ReAct) — padrão, mais simples
2. LangGraph StateGraph — avançado, com MemorySaver e conditional edges

CKP03 aceita ambos. O padrão é AgentExecutor por simplicidade.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

from .tools import get_tools
from .guardrail import validar_input


# ============================================================
# System Prompt do Agente
# ============================================================

SYSTEM_PROMPT_AGENTE = """Você é o Dr. Consumidor, um agente especializado em Direito do
Consumidor Brasileiro (CDC - Lei 8.078/90). Você tem acesso a ferramentas para
ajudar os consumidores.

REGRAS:
1. Sempre use o português do Brasil, linguagem clara e acessível.
2. Analise a pergunta do usuário e decida qual ferramenta usar:
   - Se for pergunta sobre prazos e datas → use calcular_prazos_cdc
   - Se for descrição de conduta de fornecedor → use classificar_pratica_abusiva
   - Se for sobre onde reclamar → use orgaos_defesa
   - Se for pergunta sobre a lei/CDC → use consultar_cdc
   - Se for conversa informal, responda diretamente sem usar ferramentas
3. Sempre cite os artigos do CDC quando relevante.
4. Inclua disclaimer: "Esta é uma orientação informativa, não substitui consulta com advogado."
5. Se a pergunta estiver FORA do escopo de direito do consumidor, responda educadamente
   que sua especialidade é CDC e sugira consultar profissional adequado.

TOM: Profissional, acolhedor, didático. Use exemplos práticos.
"""

# Prompt ReAct
REACT_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT_AGENTE),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)


# ============================================================
# Factory: criar agente
# ============================================================

def criar_agente_react(verbose: bool = True) -> AgentExecutor:
    """
    Cria um agente ReAct com as tools do CKP03.

    Args:
        verbose: se True, mostra o raciocínio do agente no terminal

    Returns:
        AgentExecutor pronto para invoke()
    """
    api_key = os.getenv("OLLAMA_API_KEY", "")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("CHAT_MODEL", "qwen3.5:0.8b")

    if api_key:
        llm = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=0.3,
            client_kwargs={"headers": {"Authorization": f"Bearer {api_key}"}},
        )
    else:
        llm = ChatOllama(model=model, base_url=base_url, temperature=0.3)

    tools = get_tools()

    agent = create_react_agent(llm=llm, tools=tools, prompt=REACT_PROMPT)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=verbose,
        max_iterations=8,
        handle_parsing_errors=True,
        return_intermediate_steps=False,
    )


# ============================================================
# Função de consulta (com guardrail)
# ============================================================

def consultar_agente(pergunta: str, verbose: bool = False) -> dict:
    """
    Consulta o agente com guardrail de input.

    Fluxo:
    1. Valida o input (guardrail)
    2. Se fora do escopo, retorna mensagem educada
    3. Se válido, passa para o AgentExecutor

    Args:
        pergunta: pergunta do usuário
        verbose: se True, mostra raciocínio do agente

    Returns:
        dict com 'resposta', 'tool_usada', 'bloqueado'
    """
    # Guardrail: validar input
    valido, motivo = validar_input(pergunta)
    if not valido:
        return {
            "resposta": motivo,
            "tool_usada": "guardrail",
            "bloqueado": True,
        }

    agente = criar_agente_react(verbose=verbose)

    try:
        resultado = agente.invoke({"input": pergunta})

        # Extrai a tool usada (se houver) dos intermediate steps
        tool_usada = "nenhuma"
        if hasattr(resultado, "get"):
            output = resultado.get("output", str(resultado))
        else:
            output = str(resultado)

        return {
            "resposta": output,
            "tool_usada": tool_usada,
            "bloqueado": False,
        }
    except Exception as e:
        return {
            "resposta": f"❌ Erro interno do agente: {str(e)}",
            "tool_usada": "erro",
            "bloqueado": False,
        }


if __name__ == "__main__":
    # Teste rápido
    print("🤖 Teste do Agente Consultor CDC\n")

    agente = criar_agente_react(verbose=True)

    perguntas_teste = [
        "Comprei um celular e ele veio com defeito. Quais meus direitos?",
        "Qual o prazo para desistir de uma compra online feita em 10/08/2026?",
        "A loja me obrigou a comprar um seguro junto com o produto. Isso é legal?",
        "Oi, tudo bem?",
    ]

    for p in perguntas_teste:
        print(f"\n{'='*60}")
        print(f"👤 Usuário: {p}")
        resultado = consultar_agente(p, verbose=True)
        print(f"🤖 Agente: {resultado['resposta'][:300]}...")
        print(f"🔧 Tool usada: {resultado['tool_usada']}")
