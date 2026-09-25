"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 10 — Context Engineering e Agentes MCP

Projeto local: controlar o contexto do agente com trim_messages (janela
de tokens) e conectar tools externas via MCP (Model Context Protocol).

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py

Para a parte MCP, habilite MCP e configure o transporte no .env.
Sem servidor, a demonstração local continua e informa como configurar.
"""
from langchain.tools import tool

from contexto import demo_mcp_tools, mensagens_de_entrada, recortar_mensagens

trim_messages = recortar_mensagens


@tool
def contar_palavras(texto: str) -> str:
    """Conta quantas palavras há em um texto."""
    return f"{len(texto.split())} palavras"


def demo_trim_messages(max_tokens: int = 40, output=print) -> list:
    output("\n== trim_messages (controla o tamanho do contexto) ==")
    mensagens = mensagens_de_entrada([
        {"role": "human", "content": "Olá!"},
        {"role": "ai", "content": "Oi! Como posso ajudar?"},
        {"role": "human", "content": "Me fale sobre LangChain."},
        {"role": "ai", "content": "LangChain é um framework para aplicações com LLMs."},
        {"role": "human", "content": "E sobre memória?"},
    ])
    recortadas = recortar_mensagens(mensagens, max_tokens=max_tokens)
    output(f"De {len(mensagens)} mensagens -> {len(recortadas)} mantidas:")
    for mensagem in recortadas:
        output(f"  [{type(mensagem).__name__}] {str(mensagem.content)[:50]}...")
    return recortadas


def main(environ=None, carregador=None, output=print) -> None:
    demo_trim_messages(output=output)
    output("\n== Tool local ==")
    output(contar_palavras.invoke("LangChain e MCP em uma frase"))
    output("\n== MCP (Model Context Protocol) ==")
    demo_mcp_tools(environ=environ, carregador=carregador, output=output)


if __name__ == "__main__":
    main()
