"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 09 — Agentes ReAct, Tools e Function Calling

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
    try:
        resultado = eval(expressao, {"__builtins__": {}}, {})  # noqa: S307 — didático
        return f"Resultado: {resultado}"
    except Exception as e:  # noqa: BLE001
        return f"Erro ao calcular: {e}"


busca_web = DuckDuckGoSearchRun(name="busca_na_web",
                                description="Busca na web por informações atuais.")

tools = [calcular, busca_web]


# ─────────────────────────────────────────────────────────────
# 2. Prompt ReAct (tenta baixar do Hub; usa fallback offline)
# ─────────────────────────────────────────────────────────────
def obter_prompt_react():
    try:
        return hub.pull("hwchase17/react")
    except Exception:  # noqa: BLE001 — sem internet no Hub
        from langchain_core.prompts import PromptTemplate
        return PromptTemplate.from_template(
            "Answer the following questions as best you can. You have access "
            "to the following tools:\n\n{tools}\n\n"
            "Use the following format:\n\n"
            "Question: the input question you must answer\n"
            "Thought: you should always think about what to do\n"
            "Action: the action to take, should be one of [{tool_names}]\n"
            "Action Input: the input to the action\n"
            "Observation: the result of the action\n"
            "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
            "Thought: I now know the final answer\n"
            "Final Answer: the final answer to the original input question\n\n"
            "Begin!\n\n"
            "Question: {input}\n"
            "Thought:{agent_scratchpad}"
        )


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}\n")

    agent = create_react_agent(llm, tools, obter_prompt_react())
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=5)

    for pergunta in [
        "Quanto é 27 vezes 43?",
        "Quem é o atual presidente do Brasil?",
    ]:
        print(f"\n{'=' * 60}\nPergunta: {pergunta}\n{'=' * 60}")
        resposta = executor.invoke({"input": pergunta})
        print("Resposta final:", resposta["output"])


if __name__ == "__main__":
    main()
