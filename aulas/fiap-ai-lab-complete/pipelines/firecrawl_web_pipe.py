"""
title: Firecrawl Web (FIAP AI Lab)
author: Prof. Jorge Luiz Gomes
version: 1.0.0
license: MIT
description: >
  Pipe pipeline que aparece como um "modelo" na lista do Open WebUI.
  Recebe uma URL, extrai a página em markdown limpo com o Firecrawl
  self-hosted do lab e manda esse markdown para o LLM do Ollama
  responder a pergunta do aluno.

  É o RAG mais curto possível: um documento, sem vector store —
  exatamente o que serve para mostrar grounding em aula antes de
  introduzir embeddings.

  Uso no chat:
      https://exemplo.com                 (resumo padrão)
      https://exemplo.com  quais os preços?
      /map https://exemplo.com            (lista as URLs do site)
"""

from typing import Generator, Iterator, List, Union

import requests
from pydantic import BaseModel, Field


class Pipeline:
    class Valves(BaseModel):
        FIRECRAWL_BASE_URL: str = Field(
            default="http://firecrawl-api:3002",
            description="URL da API do Firecrawl na rede fiap-ai-net.",
        )
        OLLAMA_BASE_URL: str = Field(
            default="http://ollama:11434",
            description="URL do Ollama que vai responder sobre a página.",
        )
        MODEL: str = Field(
            default="qwen3.5:0.8b",
            description="Modelo usado para responder. Precisa já estar baixado.",
        )
        MAX_CHARS: int = Field(
            default=12000,
            description="Corte do markdown antes de ir para o prompt. Modelos pequenos têm context window curto.",
        )
        ONLY_MAIN_CONTENT: bool = Field(
            default=True,
            description="Descarta menu, rodapé e banners, mantendo só o conteúdo.",
        )
        TIMEOUT: int = Field(default=180)

    def __init__(self):
        # 'pipe' = vira um modelo selecionável no seletor do Open WebUI.
        self.type = "pipe"
        self.id = "firecrawl_web"
        self.name = "Firecrawl Web"
        self.valves = self.Valves()

    async def on_startup(self):
        print(f"[firecrawl] pipeline iniciada — API {self.valves.FIRECRAWL_BASE_URL}")

    async def on_shutdown(self):
        pass

    # ------------------------------------------------------------
    # Firecrawl
    # ------------------------------------------------------------
    def _scrape(self, url: str) -> str:
        response = requests.post(
            f"{self.valves.FIRECRAWL_BASE_URL}/v2/scrape",
            json={
                "url": url,
                "formats": ["markdown"],
                "onlyMainContent": self.valves.ONLY_MAIN_CONTENT,
            },
            timeout=self.valves.TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success", False):
            raise RuntimeError(payload.get("error", "resposta sem success=true"))
        return payload.get("data", {}).get("markdown", "")

    def _map(self, url: str) -> List[str]:
        response = requests.post(
            f"{self.valves.FIRECRAWL_BASE_URL}/v2/map",
            json={"url": url},
            timeout=self.valves.TIMEOUT,
        )
        response.raise_for_status()
        links = response.json().get("links", [])
        # /v2/map devolve objetos {url, title, description}; versões
        # antigas devolviam strings puras.
        return [item.get("url", "") if isinstance(item, dict) else item for item in links]

    # ------------------------------------------------------------
    # Entrada da pipeline
    # ------------------------------------------------------------
    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict,
    ) -> Union[str, Generator, Iterator]:
        texto = (user_message or "").strip()
        if not texto:
            return "Envie uma URL. Exemplo: `https://ollama.com quais modelos existem?`"

        modo_map = texto.startswith("/map")
        if modo_map:
            texto = texto[len("/map"):].strip()

        partes = texto.split(maxsplit=1)
        url = partes[0]
        pergunta = partes[1] if len(partes) > 1 else "Resuma o conteúdo desta página em português."

        if not url.startswith(("http://", "https://")):
            return f"`{url}` não é uma URL. Comece com http:// ou https://"

        if modo_map:
            try:
                links = self._map(url)
            except Exception as exc:  # noqa: BLE001
                return f"**Falha no /map do Firecrawl:** `{exc}`"
            listagem = "\n".join(f"- {link}" for link in links[:100])
            return f"**{len(links)} URLs encontradas em {url}** (mostrando até 100)\n\n{listagem}"

        try:
            markdown = self._scrape(url)
        except Exception as exc:  # noqa: BLE001
            return (
                f"**Falha ao extrair `{url}`:** `{exc}`\n\n"
                "Confira se a stack do Firecrawl está no ar: `make up-crawl` ou `make up-complete`."
            )

        if not markdown.strip():
            return f"O Firecrawl abriu `{url}` mas não achou conteúdo textual."

        recortado = markdown[: self.valves.MAX_CHARS]
        aviso_corte = (
            f"\n\n[conteúdo cortado em {self.valves.MAX_CHARS} caracteres]"
            if len(markdown) > self.valves.MAX_CHARS
            else ""
        )

        prompt = (
            "Você responde SOMENTE com base no conteúdo da página abaixo. "
            "Se a resposta não estiver no conteúdo, diga que a página não informa.\n\n"
            f"### Fonte\n{url}\n\n"
            f"### Conteúdo\n{recortado}{aviso_corte}\n\n"
            f"### Pergunta\n{pergunta}"
        )

        try:
            resposta = requests.post(
                f"{self.valves.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self.valves.MODEL,
                    "prompt": prompt,
                    "stream": False,
                    # Qwen3 e DeepSeek-R vêm com thinking ligado: em CPU
                    # isso gera páginas de raciocínio e trava a demo.
                    "think": False,
                },
                timeout=self.valves.TIMEOUT,
            )
            resposta.raise_for_status()
            saida = resposta.json().get("response", "").strip()
        except Exception as exc:  # noqa: BLE001
            return f"Página extraída, mas o modelo falhou: `{exc}`"

        return f"{saida}\n\n---\n_Fonte extraída com Firecrawl: {url}_"
