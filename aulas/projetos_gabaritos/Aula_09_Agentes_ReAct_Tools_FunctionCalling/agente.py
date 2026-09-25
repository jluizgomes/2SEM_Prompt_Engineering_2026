import ast
import math
import os
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from langchain.tools import tool

PROMPT_REACT = (
    "Você é um agente ReAct. Responda em português do Brasil. Use a tool calcular "
    "para contas e a tool busca_na_web quando precisar de informações atuais. "
    "Se uma tool falhar, explique a falha e tente responder com o que estiver disponível."
)


def _avaliar(no: ast.AST) -> int | float:
    if isinstance(no, ast.Constant):
        if isinstance(no.value, bool) or not isinstance(no.value, (int, float)):
            raise ValueError("A expressão aceita apenas números")
        return no.value
    if isinstance(no, ast.UnaryOp):
        valor = _avaliar(no.operand)
        if isinstance(no.op, ast.UAdd):
            return valor
        if isinstance(no.op, ast.USub):
            return -valor
        raise ValueError("Operador unário não permitido")
    if isinstance(no, ast.BinOp):
        esquerda = _avaliar(no.left)
        direita = _avaliar(no.right)
        if isinstance(no.op, ast.Add):
            return esquerda + direita
        if isinstance(no.op, ast.Sub):
            return esquerda - direita
        if isinstance(no.op, ast.Mult):
            return esquerda * direita
        if isinstance(no.op, ast.Div):
            if direita == 0:
                raise ValueError("Divisão por zero não é permitida")
            return esquerda / direita
        if isinstance(no.op, ast.FloorDiv):
            if direita == 0:
                raise ValueError("Divisão por zero não é permitida")
            return esquerda // direita
        if isinstance(no.op, ast.Mod):
            if direita == 0:
                raise ValueError("Módulo por zero não é permitido")
            return esquerda % direita
        if isinstance(no.op, ast.Pow):
            if abs(esquerda) > 1_000_000 or abs(direita) > 16:
                raise ValueError("Potência fora do limite permitido")
            return esquerda ** direita
        raise ValueError("Operador aritmético não permitido")
    raise ValueError("Construção não permitida na expressão")


def _avaliar_expressao(expressao: str) -> int | float:
    texto = str(expressao or "").strip()
    if not texto:
        raise ValueError("Informe uma expressão")
    if len(texto) > 200:
        raise ValueError("A expressão excede o limite de 200 caracteres")
    try:
        arvore = ast.parse(texto, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Expressão matemática inválida") from exc
    resultado = _avaliar(arvore.body)
    if isinstance(resultado, float) and not math.isfinite(resultado):
        raise ValueError("Resultado numérico não é finito")
    return resultado


@tool
def calcular(expressao: str) -> str:
    """Calcula uma expressão aritmética com números e operadores permitidos."""
    try:
        return f"Resultado: {_avaliar_expressao(expressao)}"
    except (ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
        return f"Erro ao calcular: {exc}"


def _busca_padrao(query: str) -> list[dict[str, str]]:
    from ddgs import DDGS

    with DDGS() as buscador:
        return buscador.text(query, max_results=5)


def _formatar_resultados_busca(query: str, resultados: list[dict[str, str]]) -> str:
    if not resultados:
        return f"A busca por {query!r} não retornou resultados."
    linhas = []
    for indice, resultado in enumerate(resultados, start=1):
        titulo = str(resultado.get("title") or resultado.get("body") or "Sem título")
        resumo = str(resultado.get("body") or resultado.get("description") or "")
        link = str(resultado.get("href") or resultado.get("url") or "")
        linhas.append(f"{indice}. {titulo}\n{resumo}\nFonte: {link}")
    return "Resultados da busca:\n" + "\n".join(linhas)


def criar_busca_web(backend: Callable[[str], Sequence[dict[str, str]]] | None = None) -> Any:
    @tool("busca_na_web")
    def busca_na_web(query: str) -> str:
        """Busca informações atuais na web. Use apenas quando a pergunta precisar de atualidade."""
        executor = backend or _busca_padrao
        try:
            resultados = list(executor(query))
            return _formatar_resultados_busca(query, resultados)
        except Exception as exc:
            return f"A busca por {query!r} não foi possível: {exc}. Responda sem essa fonte ou explique a limitação."

    return busca_na_web


def criar_tools(backend: Callable[[str], Sequence[dict[str, str]]] | None = None) -> list[Any]:
    return [calcular, criar_busca_web(backend)]


def configuracao_modelo(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    if environ is None:
        from dotenv import load_dotenv

        load_dotenv()
        environ = os.environ
    api_key = environ.get("OLLAMA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OLLAMA_API_KEY não encontrada. Copie .env.example para .env e preencha a chave."
        )
    return {
        "host": environ.get("OLLAMA_HOST", "https://ollama.com").strip(),
        "api_key": api_key,
        "model": environ.get("OLLAMA_MODEL", "gpt-oss:120b").strip(),
    }


def _client_kwargs(config: Mapping[str, str]) -> dict[str, dict[str, str]]:
    if config.get("api_key") and config.get("host", "").startswith(("http://", "https://")):
        if not config["host"].startswith(("http://localhost", "http://127.0.0.1")):
            return {"headers": {"Authorization": f"Bearer {config['api_key']}"}}
    return {}


def criar_llm(config: Mapping[str, str] | None = None) -> Any:
    from langchain_ollama import ChatOllama

    configuracao = dict(config if config is not None else configuracao_modelo())
    if configuracao.get("api_key"):
        os.environ["OLLAMA_HOST"] = configuracao["host"]
        os.environ["OLLAMA_API_KEY"] = configuracao["api_key"]
    return ChatOllama(
        model=configuracao["model"],
        base_url=configuracao["host"],
        temperature=0,
        client_kwargs=_client_kwargs(configuracao),
    )


def criar_agente(
    model: Any,
    tools: Sequence[Any] | None = None,
    agent_factory: Callable[..., Any] | None = None,
) -> Any:
    fabrica = agent_factory
    if fabrica is None:
        from langchain.agents import create_agent as fabrica
    return fabrica(
        model,
        list(tools) if tools is not None else criar_tools(),
        system_prompt=PROMPT_REACT,
    )


def extrair_resultado(resultado: Mapping[str, Any]) -> str:
    if "output" in resultado and not resultado.get("messages"):
        return str(resultado["output"])
    mensagens = resultado.get("messages", [])
    for mensagem in reversed(mensagens):
        if type(mensagem).__name__ == "AIMessage" and not getattr(mensagem, "tool_calls", None):
            conteudo = getattr(mensagem, "content", "")
            if str(conteudo).strip():
                return str(conteudo)
    return "O agente terminou sem produzir uma resposta final."


def extrair_passos(resultado: Mapping[str, Any]) -> list[str]:
    passos = []
    for mensagem in resultado.get("messages", []):
        nome_tipo = type(mensagem).__name__
        if nome_tipo == "AIMessage":
            for chamada in getattr(mensagem, "tool_calls", []) or []:
                nome = chamada.get("name", "tool") if isinstance(chamada, Mapping) else "tool"
                argumentos = chamada.get("args", {}) if isinstance(chamada, Mapping) else {}
                passos.append(f"Thought → {nome}({argumentos})")
        elif nome_tipo == "ToolMessage":
            nome = getattr(mensagem, "name", None) or "tool"
            observacao = str(getattr(mensagem, "content", ""))[:250]
            passos.append(f"Observation → {nome}: {observacao}")
    return passos


def executar_perguntas(
    executor: Any,
    perguntas: Sequence[str],
    output: Callable[[str], None] = print,
) -> list[dict[str, str | None]]:
    resultados: list[dict[str, str | None]] = []
    for pergunta in perguntas:
        output(f"\n{'=' * 60}\nPergunta: {pergunta}\n{'=' * 60}")
        try:
            resultado = executor.invoke({
                "messages": [{"role": "user", "content": pergunta}]
            })
        except Exception as exc:
            mensagem = f"Falha ao processar esta pergunta: {exc}"
            output(mensagem)
            resultados.append({"pergunta": pergunta, "saida": None, "erro": mensagem})
            continue
        texto = extrair_resultado(resultado)
        output(f"Resposta final: {texto}")
        resultados.append({"pergunta": pergunta, "saida": texto, "erro": None})
    return resultados
