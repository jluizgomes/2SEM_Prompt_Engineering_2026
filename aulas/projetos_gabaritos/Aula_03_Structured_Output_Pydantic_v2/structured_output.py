from typing import Any

from pydantic import BaseModel, Field


class Receita(BaseModel):
    nome: str = Field(min_length=1, description="Nome do prato")
    ingredientes: list[str] = Field(min_length=1, description="Lista de ingredientes")
    modo_preparo: str = Field(min_length=1, description="Passo a passo resumido")
    tempo_minutos: int = Field(ge=0, description="Tempo total de preparo em minutos")


def _conteudo_bruto(resultado: Any) -> Any:
    if hasattr(resultado, "content"):
        return resultado.content
    return resultado


def validar_receita(resultado: Any, modelo: type[BaseModel] = Receita) -> BaseModel:
    if modelo is None:
        raise ValueError("Modelo Pydantic de saída não configurado.")
    if isinstance(resultado, modelo):
        return resultado
    conteudo = _conteudo_bruto(resultado)
    if isinstance(conteudo, dict) and "parsed" in conteudo:
        if conteudo["parsed"] is None:
            erro = conteudo.get("parsing_error")
            if erro is not None:
                raise erro
            raise ValueError("O modelo não produziu uma receita parseável.")
        conteudo = conteudo["parsed"]
    if isinstance(conteudo, modelo):
        return conteudo
    if isinstance(conteudo, str):
        return modelo.model_validate_json(conteudo)
    if isinstance(conteudo, dict):
        return modelo.model_validate(conteudo)
    if hasattr(conteudo, "model_dump"):
        return modelo.model_validate(conteudo.model_dump())
    raise TypeError("A saída do modelo não é JSON, dicionário ou Receita.")


def executar_com_retry(
    prato: str,
    runnable,
    modelo: type[BaseModel] = Receita,
    tentativas: int = 2,
) -> BaseModel:
    ultimo_erro = None
    total = max(1, int(tentativas))
    for _ in range(total):
        try:
            return validar_receita(runnable.invoke({"prato": prato}), modelo)
        except Exception as e:
            ultimo_erro = e
    raise ValueError(
        f"Saída estruturada inválida após {total} tentativas: {ultimo_erro}"
    ) from ultimo_erro
