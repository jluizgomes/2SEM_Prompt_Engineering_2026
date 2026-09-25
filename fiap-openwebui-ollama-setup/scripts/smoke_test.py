#!/usr/bin/env python3
"""Smoke test do stack FIAP AI Lab.

Confere, ponta a ponta, se o que esta configurado no .env realmente
funciona:

  1. a API do Ollama responde (e qual versao);
  2. o modelo de chat responde a uma geracao curta;
  3. o modelo de embeddings do RAG devolve um vetor;
  4. a interface do Open WebUI responde /health.

Uso (normalmente via `make test`):
    python3 scripts/smoke_test.py --port 11434 --webui-port 3000 \
        --chat-model nome --embed-model nome

Saida: 0 quando tudo passou, 1 quando algo falhou.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

OK = "OK     "
FALHA = "FALHOU "


def get(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def post(url, payload, timeout=180):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def tem_modelo(tags, nome):
    if not nome:
        return True
    alvos = {nome, f"{nome}:latest"} if ":" not in nome else {nome}
    for m in tags.get("models", []):
        if m.get("name") in alvos or m.get("model") in alvos:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://localhost")
    ap.add_argument("--port", type=int, default=11434)
    ap.add_argument("--webui-port", type=int, default=0,
                    help="0 = nao checar a interface")
    ap.add_argument("--chat-model", default="")
    ap.add_argument("--embed-model", default="")
    ap.add_argument("--pular-chat", action="store_true")
    ap.add_argument("--pular-embed", action="store_true")
    args = ap.parse_args()

    ollama = f"{args.host}:{args.port}"
    falhas = 0

    print("")
    print(f"  Smoke test do stack (Ollama em {ollama})")
    print("")

    # 1. a API do Ollama responde?
    tags = None
    try:
        versao = json.loads(get(f"{ollama}/api/version", timeout=5)).get("version", "?")
        tags = json.loads(get(f"{ollama}/api/tags", timeout=10))
        print(f"  {OK} API do Ollama respondeu (versao {versao})")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"  {FALHA} API do Ollama: {exc}")
        print("       O servidor esta no ar?  make up-ollama   /   make logs-ollama")
        return 1

    # 2. os modelos exigidos existem?
    for rotulo, nome in (("chat", args.chat_model), ("embeddings", args.embed_model)):
        if not nome:
            continue
        if tem_modelo(tags, nome):
            print(f"  {OK} modelo de {rotulo} presente: {nome}")
        else:
            print(f"  {FALHA} modelo de {rotulo} AUSENTE: {nome}")
            if ":" in nome:
                print("       Baixe com:  make models-pull   (ou  make pull M=%s)" % nome)
            else:
                # Sem tag = modelo local, que vem de um .gguf em models/.
                print("       Nao ha modelo com esse nome na biblioteca do Ollama:")
                print("       ele vem de um .gguf. Coloque o arquivo em models/ e rode")
                print("       'make gguf-import' (ou 'make restart'). Sem o arquivo?")
                print("       Defina CHAT_MODEL_FALLBACK no .env para um modelo de reserva.")
            falhas += 1

    # 3. o modelo de chat gera?
    if args.chat_model and not args.pular_chat:
        try:
            t0 = time.time()
            out = post(f"{ollama}/api/generate", {
                "model": args.chat_model,
                "prompt": "Responda em uma palavra: capital do Brasil?",
                "stream": False,
                "keep_alive": "10m",
                "options": {"num_predict": 16, "temperature": 0, "seed": 42},
            })
            dt = time.time() - t0
            resp = (out.get("response") or "").strip().replace("\n", " ")
            toks = out.get("eval_count", 0)
            vel = out.get("eval_duration", 0) / 1e9
            print(f"  {OK} chat respondeu em {dt:.1f}s "
                  f"({toks} tok, {toks / vel if vel else 0:.1f} tok/s): {resp[:60]!r}")
        except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
            print(f"  {FALHA} chat com '{args.chat_model}': {exc}")
            falhas += 1
    elif not args.chat_model:
        print(f"  --    chat nao conferido (CHAT_MODEL vazio)")

    # 4. o modelo de embeddings devolve vetor?
    if args.embed_model and not args.pular_embed:
        try:
            out = post(f"{ollama}/api/embed", {
                "model": args.embed_model,
                "input": "consulta semantica de teste",
            })
            vetor = out.get("embeddings") or []
            dim = len(vetor[0]) if vetor and isinstance(vetor[0], list) else 0
            if dim:
                print(f"  {OK} embeddings OK: {args.embed_model} (dimensao {dim})")
            else:
                print(f"  {FALHA} embeddings sem vetor: {args.embed_model}")
                falhas += 1
        except (urllib.error.URLError, OSError, ValueError) as exc:
            print(f"  {FALHA} embeddings com '{args.embed_model}': {exc}")
            print("       A variante -ctx<N> e criada no boot. Veja: make models")
            falhas += 1
    elif not args.embed_model:
        print(f"  --    embeddings nao conferido (EMBEDDING_MODEL vazio)")

    # 5. a interface responde?
    if args.webui_port:
        try:
            corpo = get(f"{args.host}:{args.webui_port}/health", timeout=5).strip()
            print(f"  {OK} Open WebUI respondeu /health {corpo[:40]!r}")
        except (urllib.error.URLError, OSError) as exc:
            print(f"  {FALHA} Open WebUI em {args.host}:{args.webui_port}: {exc}")
            print("       Sobe a interface com:  make up-open-webui   (ou  make up)")
            falhas += 1
    else:
        print("  --    interface nao conferida (--webui-port 0)")

    print("")
    if falhas:
        print(f"  {falhas} verificacao(oes) falharam.")
        return 1
    print("  Tudo certo: o stack esta pronto para uso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
