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
from typing import Annotated

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from langchain_ollama import ChatOllama
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

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

TextoObrigatorio = Annotated[str, Field(min_length=1)]


class Artefato(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: TextoObrigatorio
    publico_alvo: TextoObrigatorio
    funcionalidades: list[TextoObrigatorio] = Field(min_length=3)
    stack: TextoObrigatorio
    riscos: list[TextoObrigatorio] = Field(min_length=2)


parser = PydanticOutputParser(pydantic_object=Artefato)

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
    ("human", "{spec}\n\nResponda somente com JSON válido:\n{format_instructions}\n\n"
               "Tentativa: {tentativa}\n{feedback}\nResposta anterior: {resposta_anterior}"),
])

chain = prompt | llm | StrOutputParser()


class RespostaForaDoContrato(RuntimeError):
    def __init__(self, tentativas: int, ultimo_erro: str):
        self.tentativas = tentativas
        self.ultimo_erro = ultimo_erro
        super().__init__(
            f"Resposta do modelo inválida após {tentativas} tentativa(s). "
            f"Nenhum artefato foi retornado. Último erro: {ultimo_erro}"
        )


def gerar_artefato(spec: str, max_tentativas: int = 2) -> Artefato:
    if isinstance(max_tentativas, bool) or not isinstance(max_tentativas, int):
        raise ValueError("max_tentativas deve ser um inteiro positivo.")
    if max_tentativas < 1:
        raise ValueError("max_tentativas deve ser um inteiro positivo.")
    especificacao = spec.strip()
    if not especificacao:
        raise ValueError("A especificação não pode estar vazia.")

    ultimo_erro = ""
    resposta_anterior = ""
    feedback = "Gere o artefato seguindo estritamente o contrato JSON."
    for tentativa in range(1, max_tentativas + 1):
        resposta = chain.invoke({
            "spec": especificacao,
            "format_instructions": parser.get_format_instructions(),
            "tentativa": tentativa,
            "feedback": feedback,
            "resposta_anterior": resposta_anterior,
        })
        try:
            return parser.parse(str(resposta))
        except (OutputParserException, ValidationError, ValueError) as erro:
            ultimo_erro = str(erro)
            resposta_anterior = str(resposta)
            feedback = (
                "A resposta anterior violou o contrato. Corrija os campos "
                "obrigatórios e devolva somente um JSON válido."
            )

    raise RespostaForaDoContrato(max_tentativas, ultimo_erro)


def main() -> None:
    print(f"Ollama Cloud | modelo: {OLLAMA_MODEL}\n")
    print("== Especificação (spec) ==")
    print(SPEC)
    print("\n== Artefato validado a partir do spec ==")
    artefato = gerar_artefato(SPEC)
    print(artefato.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
