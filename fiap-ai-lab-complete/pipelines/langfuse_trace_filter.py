"""
title: Langfuse Trace (FIAP AI Lab)
author: Prof. Jorge Luiz Gomes
version: 1.0.0
license: MIT
description: >
  Filter pipeline que grava cada GERAÇÃO de chat do Open WebUI no
  Langfuse como observação GENERATION — modelo, entrada/saída,
  tokens de uso, chat_id, session_id e usuário.

  Complementa o OTEL do backend (ENABLE_OTEL=true), que traceja a
  infra (HTTP/DB/Redis e as chamadas ao Ollama). Aqui o que entra é
  o nível de negócio que a interface tem: o prompt do aluno, a
  resposta do modelo e o usage retornado pelo Ollama.

  outlet → depois da resposta: envia OTLP/JSON para
           http://langfuse-web:3000/api/public/otel/v1/traces
           (Langfuse v4 events_only; auth Basic pk:sk).

  Ativação: Admin Panel → Settings → Pipelines → Langfuse Trace →
  Valves. A valve `pipelines` já vem como ["*"] (todos os modelos).
  Desligue ENABLED ou remova o filtro do modelo para parar.
"""

import base64
import json
import time
import uuid
from typing import List, Optional

import requests
from pydantic import BaseModel, Field


class Pipeline:
    class Valves(BaseModel):
        pipelines: List[str] = Field(default=["*"])
        priority: int = Field(default=50)

        ENABLED: bool = Field(
            default=True,
            description="Grava gerações no Langfuse. false = pipeline inofensiva.",
        )
        LANGFUSE_BASE_URL: str = Field(
            default="http://langfuse-web:3000",
            description="URL interna do Langfuse na rede fiap-ai-net.",
        )
        LANGFUSE_PUBLIC_KEY: str = Field(
            default="",
            description="pk-lf-… do .env (LANGFUSE_PUBLIC_KEY).",
        )
        LANGFUSE_SECRET_KEY: str = Field(
            default="",
            description="sk-lf-… do .env (LANGFUSE_SECRET_KEY).",
        )
        SERVICE_NAME: str = Field(
            default="open-webui",
            description="service.name dos traces (aparece no Langfuse).",
        )
        TIMEOUT: int = Field(default=10, description="Timeout (s) do POST OTLP.")

    def __init__(self):
        self.type = "filter"
        self.name = "Langfuse Trace"
        self.valves = self.Valves()
        # Lê as chaves do ambiente do container de pipelines se as
        # valves estiverem vazias (deploy sem clicar na UI).
        import os

        if not self.valves.LANGFUSE_PUBLIC_KEY:
            self.valves.LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        if not self.valves.LANGFUSE_SECRET_KEY:
            self.valves.LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")

    async def on_startup(self):
        pk = "ok" if self.valves.LANGFUSE_PUBLIC_KEY else "VAZIA"
        print(
            f"[langfuse] pipeline iniciada — {self.valves.LANGFUSE_BASE_URL} "
            f"(pk {pk}, enabled={self.valves.ENABLED})"
        )

    async def on_shutdown(self):
        pass

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _auth_header(self) -> Optional[dict]:
        pk, sk = self.valves.LANGFUSE_PUBLIC_KEY, self.valves.LANGFUSE_SECRET_KEY
        if not pk or not sk:
            return None
        token = base64.b64encode(f"{pk}:{sk}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    def _user_id(self, user: Optional[dict]) -> str:
        if not user:
            return "anonymous"
        return str(user.get("id") or user.get("email") or "anonymous")

    def _last_user_message(self, messages: List[dict]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user":
                content = message.get("content")
                if isinstance(content, list):
                    return " ".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict) and part.get("type") == "text"
                    ).strip()
                return content or ""
        return ""

    def _last_assistant_message(self, messages: List[dict]) -> str:
        for message in reversed(messages):
            if message.get("role") == "assistant":
                content = message.get("content")
                if isinstance(content, list):
                    return " ".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict)
                    ).strip()
                return content or ""
        return ""

    def _extract_usage(self, messages: List[dict]) -> tuple[Optional[int], Optional[int]]:
        """Usage do Ollama costura na mensagem de assistant do outlet."""
        for message in reversed(messages):
            usage = message.get("usage") or {}
            if not usage:
                continue
            entrada = usage.get("prompt_tokens") or usage.get("input_tokens")
            saida = usage.get("completion_tokens") or usage.get("output_tokens")
            if entrada is not None or saida is not None:
                return (
                    int(entrada) if entrada is not None else None,
                    int(saida) if saida is not None else None,
                )
        return None, None

    def _otlp_payload(self, body: dict, user: Optional[dict]) -> dict:
        agora_ns = str(int(time.time() * 1e9))
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]

        messages = body.get("messages") or []
        model = body.get("model") or "desconhecido"
        entrada = self._last_user_message(messages)
        saida = self._last_assistant_message(messages)
        usage_in, usage_out = self._extract_usage(messages)
        session_id = body.get("session_id") or body.get("chat_id") or ""
        chat_id = body.get("chat_id") or ""

        atributos = [
            {"key": "langfuse.observation.type", "value": {"stringValue": "GENERATION"}},
            {"key": "langfuse.observation.input", "value": {"stringValue": json.dumps(
                [{"role": "user", "content": entrada}], ensure_ascii=False
            )[:8000]}},
            {"key": "langfuse.observation.output", "value": {"stringValue": json.dumps(
                {"content": saida}, ensure_ascii=False
            )[:8000]}},
            {"key": "gen_ai.request.model", "value": {"stringValue": model}},
            {"key": "langfuse.observation.model_name", "value": {"stringValue": model}},
            {"key": "user.id", "value": {"stringValue": self._user_id(user)}},
            {"key": "langfuse.trace.metadata", "value": {"stringValue": json.dumps(
                {"source": "open-webui", "chat_id": chat_id}, ensure_ascii=False
            )}},
        ]
        if session_id:
            atributos.append(
                {"key": "langfuse.session.id", "value": {"stringValue": str(session_id)}}
            )
        if usage_in is not None:
            atributos.append(
                {"key": "gen_ai.usage.input_tokens", "value": {"intValue": str(usage_in)}}
            )
            atributos.append(
                {"key": "langfuse.usage.input", "value": {"intValue": str(usage_in)}}
            )
        if usage_out is not None:
            atributos.append(
                {"key": "gen_ai.usage.output_tokens", "value": {"intValue": str(usage_out)}}
            )
            atributos.append(
                {"key": "langfuse.usage.output", "value": {"intValue": str(usage_out)}}
            )

        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {
                                "key": "service.name",
                                "value": {"stringValue": self.valves.SERVICE_NAME},
                            },
                            {
                                "key": "service.namespace",
                                "value": {"stringValue": "fiap-ai-lab"},
                            },
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "open-webui.pipelines"},
                            "spans": [
                                {
                                    "traceId": trace_id,
                                    "spanId": span_id,
                                    "name": f"chat.completion {model}",
                                    "kind": 1,
                                    "startTimeUnixNano": agora_ns,
                                    "endTimeUnixNano": agora_ns,
                                    "attributes": atributos,
                                }
                            ],
                        }
                    ],
                }
            ]
        }

    def _enviar(self, payload: dict) -> None:
        headers = self._auth_header()
        if not headers:
            print("[langfuse] chaves vazias — defina LANGFUSE_PUBLIC_KEY/SECRET_KEY nas valves")
            return
        headers["Content-Type"] = "application/json"
        url = f"{self.valves.LANGFUSE_BASE_URL}/api/public/otel/v1/traces"
        try:
            resp = requests.post(
                url,
                data=json.dumps(payload),
                headers=headers,
                timeout=self.valves.TIMEOUT,
            )
            if resp.status_code not in (200, 202, 207):
                print(f"[langfuse] OTLP recusado (HTTP {resp.status_code}): {resp.text[:200]}")
        except Exception as exc:  # noqa: BLE001
            # Observabilidade nunca derruba o chat (mesma regra do mem0).
            print(f"[langfuse] falha ao exportar geração: {exc}")

    # ------------------------------------------------------------
    # outlet — grava a geração DEPOIS da resposta do modelo
    # ------------------------------------------------------------
    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        if not self.valves.ENABLED:
            return body
        try:
            self._enviar(self._otlp_payload(body, user))
        except Exception as exc:  # noqa: BLE001
            print(f"[langfuse] erro inesperado no outlet: {exc}")
        return body
