"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 04 — Context Engineering

Projeto local: medir e controlar o que entra no contexto do modelo —
contagem de tokens (tiktoken), janela de contexto e montagem de prompt
com instrução de sistema + histórico + pergunta.

Como rodar:
    1. pip install -r requirements.txt
    2. configure o ambiente externo
    3. python main.py
"""
import os
import re
from typing import Any, Iterable

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

try:
    import tiktoken
except ImportError:
    tiktoken = None


def _inteiro_env(nome: str, padrao: int, minimo: int = 1) -> int:
    try:
        return max(minimo, int(os.getenv(nome, str(padrao))))
    except (TypeError, ValueError):
        return padrao


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
CONTEXT_BUDGET = _inteiro_env("CONTEXT_BUDGET", 1200)
CONTEXT_TOKEN_MODEL = "gpt-4o"
llm = None


def contar_tokens(texto: str, modelo: str = CONTEXT_TOKEN_MODEL) -> int:
    """Conta tokens com tiktoken ou uma aproximação local quando ele não existe."""
    texto = "" if texto is None else str(texto)
    if not texto:
        return 0
    if tiktoken is not None:
        try:
            enc = tiktoken.encoding_for_model(modelo)
        except (KeyError, ValueError):
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(texto))
    return len(re.findall(r"\w+|[^\w\s]", texto, flags=re.UNICODE))


def trim_texto(
    texto: str,
    max_tokens: int,
    modelo: str = CONTEXT_TOKEN_MODEL,
    contador=None,
) -> str:
    """Corta um texto para caber no orçamento informado."""
    texto = "" if texto is None else str(texto)
    limite = max(0, int(max_tokens))
    contar = contador or (lambda parte: contar_tokens(parte, modelo))
    if limite == 0 or contar(texto) <= limite:
        return "" if limite == 0 else texto
    inicio, fim = 0, len(texto)
    while inicio < fim:
        meio = (inicio + fim + 1) // 2
        if contar(texto[:meio]) <= limite:
            inicio = meio
        else:
            fim = meio - 1
    resultado = texto[:inicio].rstrip()
    while resultado and contar(resultado) > limite:
        resultado = resultado[:-1].rstrip()
    return resultado


def _texto_historico(item: Any) -> tuple[str, str]:
    if isinstance(item, dict):
        papel = item.get("role", item.get("papel", ""))
        conteudo = item.get("content", item.get("texto", ""))
    elif hasattr(item, "content"):
        papel = getattr(item, "type", getattr(item, "role", ""))
        conteudo = item.content
    elif isinstance(item, (tuple, list)) and len(item) >= 2:
        papel, conteudo = item[0], item[1]
    else:
        return "", ""
    papel = str(papel or "").lower()
    if papel in {"user", "human", "usuario", "usuário"}:
        papel = "user"
    elif papel in {"assistant", "ai", "assistente"}:
        papel = "assistant"
    else:
        return "", ""
    return papel, "" if conteudo is None else str(conteudo).strip()


def _historico_normalizado(historico: Iterable[Any] | None) -> list[dict[str, str]]:
    mensagens = []
    for item in historico or []:
        papel, conteudo = _texto_historico(item)
        if conteudo:
            mensagens.append({"role": papel, "content": conteudo})
    return mensagens


def preparar_mensagens(
    historico: Iterable[Any] | None,
    pergunta: str,
    orcamento_tokens: int = CONTEXT_BUDGET,
    modelo: str = CONTEXT_TOKEN_MODEL,
    contador=None,
) -> list[dict[str, str]]:
    """Monta sistema, histórico recente e pergunta dentro do orçamento."""
    orcamento = max(2, int(orcamento_tokens))
    contar = contador or (lambda parte: contar_tokens(parte, modelo))
    sistema = trim_texto(
        SISTEMA,
        max(1, orcamento - 1),
        modelo=modelo,
        contador=contar,
    )
    pergunta_texto = "" if pergunta is None else str(pergunta).strip()
    pergunta_texto = trim_texto(
        pergunta_texto,
        max(0, orcamento - contar(sistema)),
        modelo=modelo,
        contador=contar,
    )

    mensagens = [{"role": "system", "content": sistema}]
    usados = contar(sistema) + contar(pergunta_texto)
    selecionadas = []
    for mensagem in reversed(_historico_normalizado(historico)):
        custo = contar(mensagem["content"])
        if usados + custo <= orcamento:
            selecionadas.append(mensagem)
            usados += custo
    mensagens.extend(reversed(selecionadas))
    if pergunta_texto:
        mensagens.append({"role": "user", "content": pergunta_texto})
    return mensagens


def montar_contexto(
    historico: Iterable[Any] | None,
    pergunta: str,
    orcamento_tokens: int = CONTEXT_BUDGET,
    modelo: str = CONTEXT_TOKEN_MODEL,
    contador=None,
) -> list[dict[str, str]]:
    return preparar_mensagens(
        historico,
        pergunta,
        orcamento_tokens,
        modelo,
        contador,
    )


def _resposta_texto(resposta: Any) -> str:
    conteudo = getattr(resposta, "content", None)
    if conteudo is not None:
        if isinstance(conteudo, list):
            return "".join(str(item) for item in conteudo)
        return str(conteudo)
    if isinstance(resposta, dict) and "content" in resposta:
        return str(resposta["content"])
    return str(resposta)


def _configuracao() -> tuple[str, str, str]:
    load_dotenv()
    host = os.getenv("OLLAMA_HOST", OLLAMA_HOST)
    chave = os.getenv("OLLAMA_API_KEY", "")
    modelo = os.getenv("OLLAMA_MODEL", OLLAMA_MODEL)
    return host, chave, modelo


def _obter_llm():
    global llm
    if llm is not None:
        return llm
    host, chave, modelo = _configuracao()
    if not chave:
        raise RuntimeError(
            "OLLAMA_API_KEY não encontrada. Copie .env.example para .env e preencha a chave."
        )
    os.environ["OLLAMA_HOST"] = host
    os.environ["OLLAMA_API_KEY"] = chave
    try:
        from langchain_ollama import ChatOllama
    except ImportError as erro:
        raise RuntimeError("langchain-ollama não está instalado.") from erro
    llm = ChatOllama(model=modelo, base_url=host, temperature=0.3)
    return llm


class ContextChain:
    def __init__(self, orcamento_tokens: int = CONTEXT_BUDGET):
        self.orcamento_tokens = orcamento_tokens
        self.ultimo_contexto: list[dict[str, str]] = []

    def invoke(self, payload: Any, config=None) -> str:
        if isinstance(payload, str):
            pergunta = payload
            historico = []
        else:
            dados = payload or {}
            pergunta = str(dados.get("pergunta", ""))
            historico = dados.get("historico", [])
        pergunta = pergunta.strip()
        if not pergunta:
            raise ValueError("Informe uma pergunta.")
        self.ultimo_contexto = preparar_mensagens(
            historico,
            pergunta,
            self.orcamento_tokens,
        )
        if prompt is None:
            mensagens_modelo = self.ultimo_contexto
        else:
            mensagens_modelo = prompt.format_messages(
                sistema=self.ultimo_contexto[0]["content"],
                historico=self.ultimo_contexto[1:-1],
                pergunta=self.ultimo_contexto[-1]["content"],
            )
        resposta = _obter_llm().invoke(mensagens_modelo)
        return _resposta_texto(resposta)


SISTEMA = (
    "Você é um assistente de suporte técnico da FIAP. "
    "Responda de forma objetiva e em português do Brasil. "
    "Se não souber a resposta, diga que não sabe — nunca invente."
)

try:
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{sistema}"),
        MessagesPlaceholder(variable_name="historico", optional=True),
        ("human", "{pergunta}"),
    ])
except (ImportError, TypeError, ValueError):
    prompt = None

chain = ContextChain()


def main() -> None:
    _, _, modelo = _configuracao()
    print(f"Ollama Cloud | modelo: {modelo}\n")

    exemplos = [
        "Olá!",
        "Explique o que é context window em um LLM e por que ele importa.",
        SISTEMA + " " + "Explique o que é context window em um LLM.",
    ]
    print("== Custo de tokens por entrada ==")
    for exemplo in exemplos:
        print(f"  {contar_tokens(exemplo):>5} tokens | {exemplo[:60]}...")

    historico = [
        {"role": "user", "content": "O que é uma janela de contexto?"},
        {"role": "assistant", "content": "É o limite de informações que o modelo processa por chamada."},
    ]
    contexto = preparar_mensagens(historico, "Como posso respeitá-la?")
    print(f"\nContexto montado: {len(contexto)} mensagens | orçamento: {CONTEXT_BUDGET} tokens")
    print("Resposta com histórico e limite de contexto:")
    print(chain.invoke({"pergunta": "Como posso respeitá-la?", "historico": historico}))


if __name__ == "__main__":
    main()
