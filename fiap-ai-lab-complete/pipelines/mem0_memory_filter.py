"""
title: Mem0 Memory (FIAP AI Lab)
author: Prof. Jorge Luiz Gomes
version: 1.0.0
license: MIT
description: >
  Filter pipeline que dá memória de longo prazo a QUALQUER modelo do
  Open WebUI usando o serviço mem0 do lab.

  inlet  → antes de chamar o modelo: busca memórias relevantes do usuário
           e injeta como mensagem de sistema.
  outlet → depois da resposta: manda o par (pergunta, resposta) para o
           mem0 extrair e gravar os fatos novos.

  Ativação: Admin Panel → Settings → Pipelines → Mem0 Memory → Valves.
  A valve `pipelines` já vem como ["*"], ou seja, vale para todos os modelos.
"""

from typing import List, Optional

import requests
from pydantic import BaseModel, Field


class Pipeline:
    class Valves(BaseModel):
        # "*" = aplica a todos os modelos. Troque por uma lista de ids
        # (ex.: ["qwen3.5:0.8b"]) para restringir a memória a um modelo.
        pipelines: List[str] = Field(default=["*"])

        # Ordem de execução entre filters. Menor roda primeiro.
        priority: int = Field(default=0)

        MEM0_BASE_URL: str = Field(
            default="http://mem0:8000",
            description="URL do serviço mem0 dentro da rede fiap-ai-net.",
        )
        ENABLED: bool = Field(
            default=True,
            description="Desliga a memória sem remover a pipeline.",
        )
        SEARCH_LIMIT: int = Field(
            default=5,
            description="Quantas memórias são injetadas no contexto por vez.",
        )
        TIMEOUT: int = Field(
            default=60,
            description="Timeout (s) das chamadas ao mem0. A extração usa LLM e é lenta em CPU.",
        )
        STORE_ASSISTANT_REPLY: bool = Field(
            default=True,
            description="Se falso, só a mensagem do usuário vira memória.",
        )

    def __init__(self):
        self.type = "filter"
        self.name = "Mem0 Memory"
        self.valves = self.Valves()

    async def on_startup(self):
        print(f"[mem0] pipeline iniciada — backend {self.valves.MEM0_BASE_URL}")

    async def on_shutdown(self):
        pass

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _user_id(self, user: Optional[dict]) -> str:
        """
        Cada usuário do Open WebUI tem a própria memória. Sem usuário
        identificado (chamada via API), tudo cai em 'anonymous'.
        """
        if not user:
            return "anonymous"
        return str(user.get("id") or user.get("email") or "anonymous")

    def _last_user_message(self, messages: List[dict]) -> Optional[str]:
        for message in reversed(messages):
            if message.get("role") == "user":
                content = message.get("content")
                # Mensagens multimodais chegam como lista de partes.
                if isinstance(content, list):
                    return " ".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict) and part.get("type") == "text"
                    ).strip()
                return content
        return None

    # ------------------------------------------------------------
    # inlet — injeta as memórias antes do modelo responder
    # ------------------------------------------------------------
    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        if not self.valves.ENABLED:
            return body

        messages = body.get("messages", [])
        query = self._last_user_message(messages)
        if not query:
            return body

        try:
            response = requests.post(
                f"{self.valves.MEM0_BASE_URL}/search",
                json={
                    "query": query,
                    "user_id": self._user_id(user),
                    "limit": self.valves.SEARCH_LIMIT,
                },
                timeout=self.valves.TIMEOUT,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
        except Exception as exc:  # noqa: BLE001
            # Memória é um extra: se o serviço estiver fora do ar (perfil
            # sem mem0, por exemplo), o chat continua funcionando normal.
            print(f"[mem0] busca falhou, seguindo sem memória: {exc}")
            return body

        if not results:
            return body

        lembretes = "\n".join(f"- {item.get('memory', '')}" for item in results)
        contexto = (
            "Você tem memória de longo prazo sobre este usuário. "
            "Fatos conhecidos das conversas anteriores:\n"
            f"{lembretes}\n"
            "Use esses fatos apenas quando forem relevantes. "
            "Nunca invente memórias que não estejam na lista."
        )

        # Anexa ao system prompt existente em vez de criar outro: alguns
        # modelos pequenos ignoram a segunda mensagem de sistema.
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = f"{messages[0]['content']}\n\n{contexto}"
        else:
            messages.insert(0, {"role": "system", "content": contexto})

        body["messages"] = messages
        return body

    # ------------------------------------------------------------
    # outlet — grava a conversa como memória depois da resposta
    # ------------------------------------------------------------
    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        if not self.valves.ENABLED:
            return body

        messages = body.get("messages", [])
        pergunta = self._last_user_message(messages)
        if not pergunta:
            return body

        payload_messages = [{"role": "user", "content": pergunta}]

        if self.valves.STORE_ASSISTANT_REPLY and messages:
            ultima = messages[-1]
            if ultima.get("role") == "assistant" and isinstance(ultima.get("content"), str):
                payload_messages.append({"role": "assistant", "content": ultima["content"]})

        try:
            requests.post(
                f"{self.valves.MEM0_BASE_URL}/memories",
                json={
                    "messages": payload_messages,
                    "user_id": self._user_id(user),
                    "metadata": {"origem": "open-webui"},
                },
                timeout=self.valves.TIMEOUT,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[mem0] gravação falhou: {exc}")

        return body
