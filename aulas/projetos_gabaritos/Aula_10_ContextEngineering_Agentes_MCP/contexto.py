import asyncio
import inspect
import os
import shlex
from collections.abc import Callable, Mapping, Sequence
from typing import Any


def mensagens_de_entrada(dados: Sequence[Mapping[str, Any]]) -> list[Any]:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

    mensagens = []
    for indice, item in enumerate(dados, start=1):
        if not isinstance(item, Mapping):
            raise ValueError(f"Mensagem {indice} não é um objeto")
        role = str(item.get("role") or "").strip().lower()
        content = item.get("content")
        if not isinstance(content, str):
            raise ValueError(f"Mensagem {indice} precisa de conteúdo textual")
        if role == "system":
            mensagens.append(SystemMessage(content=content))
        elif role in {"human", "user"}:
            mensagens.append(HumanMessage(content=content))
        elif role in {"ai", "assistant"}:
            mensagens.append(AIMessage(content=content))
        elif role == "tool":
            tool_call_id = str(item.get("tool_call_id") or "").strip()
            if not tool_call_id:
                raise ValueError(f"Mensagem tool {indice} precisa de tool_call_id")
            argumentos = {"content": content, "tool_call_id": tool_call_id}
            if item.get("name"):
                argumentos["name"] = str(item["name"])
            if item.get("status") in {"success", "error"}:
                argumentos["status"] = item["status"]
            mensagens.append(ToolMessage(**argumentos))
        else:
            raise ValueError(f"Role de mensagem inválido: {role or 'vazio'}")
    return mensagens


def recortar_mensagens(
    mensagens: Sequence[Any],
    max_tokens: int = 40,
    token_counter: Any = "approximate",
) -> list[Any]:
    from langchain_core.messages import trim_messages

    if int(max_tokens) <= 0:
        raise ValueError("max_tokens deve ser maior que zero")
    return trim_messages(
        list(mensagens),
        max_tokens=int(max_tokens),
        strategy="last",
        token_counter=token_counter,
        include_system=True,
    )


def configuracao_mcp(environ: Mapping[str, str] | None = None) -> dict[str, Any] | None:
    if environ is None:
        from dotenv import load_dotenv

        load_dotenv()
        environ = os.environ
    habilitado = str(environ.get("MCP_ENABLED", "true")).strip().lower()
    if habilitado in {"0", "false", "no", "off"}:
        return None
    transporte = str(environ.get("MCP_TRANSPORT", "streamable_http")).strip().lower()
    if transporte == "stdio":
        comando_texto = str(environ.get("MCP_SERVER_COMMAND", "")).strip()
        if not comando_texto:
            return None
        partes = shlex.split(comando_texto)
        if not partes:
            return None
        configuracao: dict[str, Any] = {
            "transport": "stdio",
            "command": partes[0],
            "args": partes[1:],
        }
        return configuracao
    if transporte not in {"streamable_http", "http", "sse"}:
        raise ValueError(f"Transporte MCP não suportado: {transporte}")
    url = str(environ.get("MCP_SERVER_URL", "")).strip()
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        raise ValueError("MCP_SERVER_URL deve usar http:// ou https://")
    normalizado = "streamable_http" if transporte == "http" else transporte
    configuracao = {"transport": normalizado, "url": url}
    try:
        timeout = float(environ.get("MCP_TIMEOUT", "10"))
    except (TypeError, ValueError):
        raise ValueError("MCP_TIMEOUT deve ser numérico")
    if timeout <= 0:
        raise ValueError("MCP_TIMEOUT deve ser maior que zero")
    configuracao["timeout"] = timeout
    return configuracao


def criar_conexao_mcp(
    config: Mapping[str, Any],
    client_factory: Callable[[dict[str, Any]], Any] | None = None,
) -> Any:
    fabrica = client_factory
    if fabrica is None:
        from langchain_mcp_adapters.client import MultiServerMCPClient as fabrica
    conexao: dict[str, Any] = {
        "transport": config["transport"],
    }
    if config["transport"] == "stdio":
        conexao["command"] = config["command"]
        conexao["args"] = list(config.get("args", []))
    else:
        conexao["url"] = config["url"]
    if "timeout" in config:
        conexao["timeout"] = config["timeout"]
    return fabrica({"mcp": conexao})


async def carregar_tools_mcp(
    config: Mapping[str, Any],
    client_factory: Callable[[dict[str, Any]], Any] | None = None,
) -> list[Any]:
    client = criar_conexao_mcp(config, client_factory=client_factory)
    return list(await client.get_tools())


def demo_mcp_tools(
    environ: Mapping[str, str] | None = None,
    carregador: Callable[[Mapping[str, Any]], Any] | None = None,
    output: Callable[[str], None] = print,
) -> list[Any]:
    try:
        configuracao = configuracao_mcp(environ)
    except ValueError as exc:
        output(f"Configuração MCP inválida: {exc}. O fluxo local continua funcional.")
        return []
    if configuracao is None:
        output(
            "MCP não configurado ou desabilitado. O fluxo local de context engineering "
            "e a tool contar_palavras continuam funcionais; habilite MCP_TRANSPORT e "
            "MCP_SERVER_URL, ou informe MCP_SERVER_COMMAND para stdio."
        )
        return []
    loader = carregador or carregar_tools_mcp
    try:
        resultado = loader(configuracao)
        ferramentas = list(asyncio.run(resultado) if inspect.isawaitable(resultado) else resultado)
    except Exception as exc:
        output(
            f"Falha ao conectar ao MCP: {exc}. O fluxo local continua funcional, "
            "sem as tools externas desta conexão."
        )
        return []
    output(f"{len(ferramentas)} tool(s) carregada(s) do servidor MCP:")
    for ferramenta in ferramentas:
        output(f"  - {getattr(ferramenta, 'name', 'tool_sem_nome')}")
    return ferramentas
