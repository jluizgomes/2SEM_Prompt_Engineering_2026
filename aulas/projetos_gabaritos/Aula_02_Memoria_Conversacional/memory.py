from langchain_core.language_models.llms import LLM


def contar_tokens(texto: str) -> int:
    if not texto:
        return 0
    return max(1, (len(texto) + 3) // 4)


def ids_tokens(texto: str) -> list[int]:
    return list(range(contar_tokens(texto)))


class ContadorTokens(LLM):
    @property
    def _llm_type(self) -> str:
        return "contador_tokens"

    def _call(self, prompt: str, stop: list[str] | None = None, run_manager=None, **kwargs) -> str:
        raise RuntimeError("O contador de tokens não gera respostas.")

    def get_token_ids(self, texto: str) -> list[int]:
        return ids_tokens(texto)


def criar_contador_tokens() -> ContadorTokens:
    return ContadorTokens()
