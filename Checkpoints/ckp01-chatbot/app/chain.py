"""
Pipeline LCEL do Chatbot Consultor CDC.

Usa o operador pipe (|) para compor: template → modelo → parser
"""

import os
from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from .prompts import SYSTEM_PROMPT_CDC

load_dotenv()

# ============================================================
# Configuração do modelo
# ============================================================

def get_llm():
    """Retorna o ChatOllama configurado — cloud ou local."""
    api_key = os.getenv("OLLAMA_API_KEY", "")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("CHAT_MODEL", "qwen3.5:0.8b")

    if api_key:
        # Ollama Cloud (sala de aula)
        return ChatOllama(
            model=model,
            base_url=base_url,
            temperature=0.3,
            client_kwargs={"headers": {"Authorization": f"Bearer {api_key}"}},
        )
    else:
        # Ollama local (Docker)
        return ChatOllama(
            model=model,
            base_url=base_url,
            temperature=0.3,
        )


# ============================================================
# Construção da Chain LCEL
# ============================================================

def build_chain():
    """
    Constrói a chain LCEL com memória conversacional.

    Pipeline:
        input + histórico → ChatPromptTemplate → ChatOllama → StrOutputParser

    Returns:
        chain: Runnable com interface invoke(input, config)
    """
    llm = get_llm()

    # Template com system prompt + histórico + input do usuário
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT_CDC),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    )

    # Chain LCEL usando operador pipe (|)
    chain = prompt | llm | StrOutputParser()

    return chain


if __name__ == "__main__":
    # Teste rápido da chain
    chain = build_chain()
    response = chain.invoke({
        "input": "Comprei um celular e ele veio com defeito. Quais meus direitos?",
        "history": [],
    })
    print("Resposta do chatbot:")
    print(response)
