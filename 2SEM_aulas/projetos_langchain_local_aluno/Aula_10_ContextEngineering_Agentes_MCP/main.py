"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 10 — Context Engineering e Agentes MCP
Esqueleto para alunos — complete os TODOs abaixo.

Projeto local: controlar o contexto do agente com trim_messages (janela
de tokens) e conectar tools externas via MCP (Model Context Protocol).

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py

Para a parte MCP, aponte MCP_SERVER_URL no .env para um servidor MCP
(stdio ou SSE). Sem servidor, a demonstração é pulada com orientação.
"""
import os

from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage, trim_messages
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

# ─────────────────────────────────────────────────────────────
# Configuração via .env
# ─────────────────────────────────────────────────────────────
load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")

if not OLLAMA_API_KEY:
    raise RuntimeError(
        "OLLAMA_API_KEY não encontrada. Copie .env.example para .env e preencha a chave."
    )

os.environ["OLLAMA_HOST"] = OLLAMA_HOST
os.environ["OLLAMA_API_KEY"] = OLLAMA_API_KEY

llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0)


# ─────────────────────────────────────────────────────────────
# 1. Context engineering: trim_messages (janela deslizante de tokens)
# ─────────────────────────────────────────────────────────────
def demo_trim_messages() -> None:
    print("\n== trim_messages (controla o tamanho do contexto) ==")
    mensagens = [
        HumanMessage(content="Olá!"),
        AIMessage(content="Oi! Como posso ajudar?"),
        HumanMessage(content="Me fale sobre LangChain."),
        AIMessage(content="LangChain é um framework para aplicações com LLMs."),
        HumanMessage(content="E sobre memória?"),
    ]
    # TODO: Use trim_messages() para recortar as mensagens
    # Parâmetros: max_tokens=40, strategy="last", token_counter=llm, include_system=True
    # Exiba quantas mensagens foram mantidas e mostre-as
    pass


# ─────────────────────────────────────────────────────────────
# 2. Tools regulares (não precisam de MCP)
# ─────────────────────────────────────────────────────────────
@tool
def contar_palavras(texto: str) -> str:
    """Conta quantas palavras há em um texto."""
    # TODO: Retorne o número de palavras do texto (use len(texto.split()))
    pass


busca_web = DuckDuckGoSearchRun(name="busca_na_web",
                                description="Busca na web por informações atuais.")


# ─────────────────────────────────────────────────────────────
# 3. MCP — carregar tools de um servidor MCP externo
# ─────────────────────────────────────────────────────────────
def demo_mcp_tools() -> None:
    print("\n== MCP (Model Context Protocol) ==")
    mcp_url = os.getenv("MCP_SERVER_URL", "")
    if not mcp_url:
        print("  MCP_SERVER_URL não definida no .env — pulando.")
        print("  Exemplo: MCP_SERVER_URL=http://localhost:8000/sse")
        return

    # TODO: Implemente a conexão com o servidor MCP
    # Use MultiServerMCPClient e load_mcp_tools (langchain_mcp_adapters)
    # Trate ImportError (dependência ausente) e erros de conexão
    # Exiba a quantidade de tools carregadas e seus nomes
    pass


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}")
    demo_trim_messages()
    print("\n== Tool local ==")
    # TODO: invoque a tool contar_palavras com um texto de exemplo
    # print(contar_palavras.invoke("LangChain e MCP em uma frase"))
    demo_mcp_tools()


if __name__ == "__main__":
    main()
