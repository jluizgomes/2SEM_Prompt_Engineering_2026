"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 03 — Structured Output com Pydantic v2

Projeto local: forçar o LLM a responder com um schema garantido, usando
PydanticOutputParser + BaseModel — o mesmo padrão que sustenta o CKP01 R3.

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py
"""
import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from structured_output import Receita, executar_com_retry

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

schema = Receita.model_json_schema()
llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_HOST,
    temperature=0.2,
    format=schema,
)
parser = PydanticOutputParser(pydantic_object=Receita)

prompt = ChatPromptTemplate.from_messages([
    ("system", "Você é um chef. Responda SOMENTE em JSON válido, sem texto extra."),
    ("human", "Me dê a receita de {prato}.\n\n{instrucoes_formato}"),
]).partial(instrucoes_formato=parser.get_format_instructions())

chain = prompt | llm.with_structured_output(Receita, method="json_schema")


def gerar_receita(prato: str, runnable=None) -> Receita:
    return executar_com_retry(prato, runnable or chain, modelo=Receita)


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}\n")
    print("== Instruções de formato injetadas no prompt ==\n")
    print(parser.get_format_instructions())

    resultado = gerar_receita("bolo de cenoura")
    print("\n== Resultado validado com Pydantic v2 ==")
    print("tipo:", type(resultado).__name__)
    print("nome:", resultado.nome)
    print("ingredientes:", resultado.ingredientes)
    print("tempo_minutos:", resultado.tempo_minutos)
    print("\n== Como dict/JSON ==")
    print(resultado.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
