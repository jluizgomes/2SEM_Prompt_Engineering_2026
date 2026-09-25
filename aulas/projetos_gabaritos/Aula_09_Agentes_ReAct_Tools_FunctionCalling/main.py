"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 09 — Agentes ReAct, Tools e Function Calling

Projeto local: montar um agente ReAct que decide QUAL tool usar a cada
passo (busca na web, calculadora) e executa um loop
Thought → Action → Observation até chegar à resposta final.

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py
"""
from agente import (
    calcular,
    configuracao_modelo,
    criar_agente,
    criar_busca_web,
    criar_llm,
    criar_tools,
    extrair_passos,
    extrair_resultado,
    executar_perguntas,
)

tools = criar_tools()
busca_web = tools[1]


def main() -> None:
    configuracao = configuracao_modelo()
    llm = criar_llm(configuracao)
    agente = criar_agente(llm, tools)
    print(f"Ollama Cloud | modelo: {configuracao['model']}\n")
    executar_perguntas(
        agente,
        [
            "Quanto é 27 vezes 43?",
            "Quem é o atual presidente do Brasil?",
        ],
    )


if __name__ == "__main__":
    main()
