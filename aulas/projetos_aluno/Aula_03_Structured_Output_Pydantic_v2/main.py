"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Esqueleto para alunos — complete os TODOs abaixo.
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

from pydantic import BaseModel, Field

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

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

llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0.2)


# ─────────────────────────────────────────────────────────────
# 1. Schema — contrato de saída com Pydantic v2
# ─────────────────────────────────────────────────────────────
class Receita(BaseModel):
    """Saída estruturada de uma receita."""
    nome: str = Field(description="Nome do prato")
    ingredientes: list[str] = Field(description="Lista de ingredientes")
    modo_preparo: str = Field(description="Passo a passo resumido")
    tempo_minutos: int = Field(description="Tempo total de preparo em minutos")


# ─────────────────────────────────────────────────────────────
# 2. Parser — gera as instruções de formato e converte a resposta
# ─────────────────────────────────────────────────────────────
parser = PydanticOutputParser(pydantic_object=Receita)

prompt = ChatPromptTemplate.from_messages([
    ("system", "Você é um chef. Responda SOMENTE em JSON válido, sem texto extra."),
    ("human", "Me dê a receita de {prato}.\n\n{instrucoes_formato}"),
]).partial(instrucoes_formato=parser.get_format_instructions())

chain = prompt | llm | parser


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}\n")
    # TODO: Imprima as instruções de formato (parser.get_format_instructions())
    # TODO: Invoke a chain com um prato e receba o objeto Pydantic
    # TODO: Imprima nome, ingredientes e tempo_minutos do resultado
    # TODO: Converta para dict/JSON com model_dump_json() e imprima


if __name__ == "__main__":
    main()
