"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 09 — Agentes ReAct, Tools e Function Calling
Esqueleto para alunos — complete os TODOs abaixo.

Projeto local: montar um agente ReAct que decide QUAL tool usar a cada
passo (busca na web, busca em documentos, calculadora) e executa um loop
Thought → Action → Observation até chegar à resposta final.

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py
"""
import os

from dotenv import load_dotenv

from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain_ollama import ChatOllama
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
# 1. Tools — as "mãos" do agente
# ─────────────────────────────────────────────────────────────
@tool
def calcular(expressao: str) -> str:
    """Calcula uma expressão matemática simples. Ex.: '13 * 17'."""
    # TODO: Implemente o cálculo da expressão usando eval()
    # Dica: use eval(expressao, {"__builtins__": {}}, {}) para limitar o escopo
    # Retorne uma string com o resultado ou mensagem de erro
    pass


busca_web = DuckDuckGoSearchRun(name="busca_na_web",
                                description="Busca na web por informações atuais.")

tools = [calcular, busca_web]


# ─────────────────────────────────────────────────────────────
# 2. Prompt ReAct (tenta baixar do Hub; usa fallback offline)
# ─────────────────────────────────────────────────────────────
def obter_prompt_react():
    # TODO: Tente baixar o prompt "hwchase17/react" do LangChain Hub
    # Em caso de falha (sem internet), crie um PromptTemplate offline
    # O prompt ReAct deve conter: {tools}, {tool_names}, {input}, {agent_scratchpad}
    # O formato deve seguir Thought → Action → Action Input → Observation → Final Answer
    pass


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}\n")

    # TODO: Crie o agente com create_react_agent(llm, tools, prompt)
    # TODO: Crie o executor com AgentExecutor(agent, tools, verbose=True, max_iterations=5)
    # TODO: Para cada pergunta, invoque o executor e imprima a resposta final
    for pergunta in [
        "Quanto é 27 vezes 43?",
        "Quem é o atual presidente do Brasil?",
    ]:
        print(f"\n{'=' * 60}\nPergunta: {pergunta}\n{'=' * 60}")
        # TODO: resposta = executor.invoke({"input": pergunta})
        # TODO: print("Resposta final:", resposta["output"])
        pass


if __name__ == "__main__":
    main()
