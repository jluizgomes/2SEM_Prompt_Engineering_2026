#!/usr/bin/env python3
"""Mede a performance real do Ollama configurado no projeto.

Uso:
    python3 scripts/bench_ollama.py                 # porta e modelo do .env
    python3 scripts/bench_ollama.py --port 11434 --model nome
    python3 scripts/bench_ollama.py --threads 4,6,8 # varre num_thread

Mede, para cada configuracao:
  - latencia da PRIMEIRA resposta (modelo sendo carregado do disco)
  - latencia com o modelo QUENTE (ja residente na memoria)
  - tokens/s de geracao (decode) e de leitura do prompt (prefill)
"""

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request

PROMPT = (
    "Explique em detalhes, em portugues, o que e context engineering em LLMs "
    "e por que ele importa para sistemas de RAG, citando os principais "
    "trade-offs de janela de contexto, chunking e reranking."
)


def post(base, path, payload, timeout=900):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def gerar(base, model, num_thread=None, num_predict=128, num_ctx=4096):
    options = {"num_predict": num_predict, "num_ctx": num_ctx,
               "temperature": 0, "seed": 42}
    if num_thread:
        options["num_thread"] = num_thread
    t0 = time.time()
    out = post(base, "/api/generate", {
        "model": model, "prompt": PROMPT, "stream": False,
        "keep_alive": "10m", "options": options,
    })
    total = time.time() - t0
    ec, ed = out.get("eval_count", 0), out.get("eval_duration", 1) / 1e9
    pc, pd = out.get("prompt_eval_count", 0), out.get("prompt_eval_duration", 1) / 1e9
    return {
        "total": total,
        "load": out.get("load_duration", 0) / 1e9,
        "decode": ec / ed if ed else 0,
        "prefill": pc / pd if pd else 0,
        "tokens": ec,
    }


def descarregar(base, model):
    try:
        post(base, "/api/generate", {"model": model, "keep_alive": 0}, timeout=120)
    except urllib.error.URLError:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://localhost")
    ap.add_argument("--port", type=int, default=11434)
    ap.add_argument("--model", required=True)
    ap.add_argument("--threads", default="",
                    help="lista separada por virgula; vazio usa a config do servidor")
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()

    base = f"{args.host}:{args.port}"

    try:
        info = json.load(urllib.request.urlopen(base + "/api/version", timeout=5))
        print(f"  Ollama {info.get('version', '?')} em {base}")
    except Exception as exc:  # noqa: BLE001
        print(f"  ERRO: nao consegui falar com o Ollama em {base}: {exc}")
        return 1

    print(f"  Modelo: {args.model}")
    print()

    # --- latencia frio x quente -------------------------------------------------
    descarregar(base, args.model)
    time.sleep(2)
    frio = gerar(base, args.model, num_predict=32)
    quente = [gerar(base, args.model, num_predict=32) for _ in range(2)]

    print("  Latencia (modelo frio x quente)")
    print(f"    primeira resposta (carregando do disco) : {frio['total']:.2f}s "
          f"(load {frio['load']:.2f}s)")
    print(f"    respostas seguintes (residente)         : "
          f"{statistics.median(q['total'] for q in quente):.2f}s "
          f"(load {statistics.median(q['load'] for q in quente):.2f}s)")
    print()

    # --- throughput ------------------------------------------------------------
    threads = [int(t) for t in args.threads.split(",") if t.strip()] or [None]
    print("  Throughput")
    print(f"    {'threads':>8} {'decode tok/s':>13} {'prefill tok/s':>14}")
    print("    " + "-" * 38)
    for t in threads:
        descarregar(base, args.model)
        time.sleep(1)
        gerar(base, args.model, num_thread=t, num_predict=16)  # warmup
        valores = []
        for _ in range(args.runs):
            valores.append(gerar(base, args.model, num_thread=t))
            descarregar(base, args.model)
            time.sleep(1)
        dec = statistics.median(v["decode"] for v in valores)
        pre = statistics.median(v["prefill"] for v in valores)
        rotulo = str(t) if t else "servidor"
        print(f"    {rotulo:>8} {dec:>13.2f} {pre:>14.1f}")

    print()
    print("  Dica: use o valor com melhor decode. Em CPU hibrida (P-cores +")
    print("  E-cores), poucos threads nos P-cores costumam ganhar de todos os")
    print("  threads. Ajuste OLLAMA_NUM_THREADS no .env e rode 'make restart'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
