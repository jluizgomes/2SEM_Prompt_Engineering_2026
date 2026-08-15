"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 14 — Spec-Driven Development e Encerramento

Projeto local: consolidar o semestre com o padrão spec-driven — escrever a
ESPECIFICAÇÃO primeiro e deixar o modelo gerar o artefato conforme o spec.
Serve de ponte entre o que foi visto (LCEL, RAG, agentes) e a carreira.

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py
"""
import os

from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

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

llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0.3)


# ─────────────────────────────────────────────────────────────
# Spec-driven: a especificação é o prompt. O modelo gera o artefato.
# ─────────────────────────────────────────────────────────────
SPEC = """
Objetivo: gerar o plano de um mini chatbot de suporte acadêmico.

Formato de saída (obrigatório):
1. Nome do produto
2. Público-alvo
3. Funcionalidades (mínimo 3, em bullets)
4. Stack sugerida (uma linha)
5. Riscos principais (mínimo 2)

Restrições:
- Português do Brasil
- Sem jargão desnecessário
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", "Você é um engenheiro de produto sênior. Siga a especificação à risca."),
    ("human", "{spec}"),
])

chain = prompt | llm | StrOutputParser()


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}\n")
    print("== Especificação (spec) ==")
    print(SPEC)
    print("\n== Artefato gerado a partir do spec ==")
    print(chain.invoke({"spec": SPEC}))


if __name__ == "__main__":
    main()
