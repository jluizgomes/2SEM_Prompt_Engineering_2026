#!/usr/bin/env python3
"""
FIAP AI Lab — bootstrap Langfuse ↔ Ollama (connection + score configs)
======================================================================

Para o Playground, o LLM-as-a-judge e os experimentos do Langfuse falarem
com o Ollama do lab são precisas DUAS coisas — e elas são independentes:

1. PERMISSÃO DE REDE (env var, já no compose):
   LANGFUSE_LLM_CONNECTION_WHITELISTED_HOST=ollama
   O Langfuse bloqueia por segurança todo host de rede privada — e
   `ollama` (rede interna do Docker) é um deles. Sem esta variável a
   conexão é recusada "Blocked IP address detected".

2. A LLM CONNECTION EM SI (dado no projeto, no Postgres):
   é ela que diz "adapter openai, baseURL http://ollama:11434/v1,
   estes modelos". Ela NÃO tem variável de ambiente de bootstrap no
   Langfuse: sem criar, o Playground simplesmente não tem nenhum
   modelo disponível, mesmo com a permissão de rede em ordem.

Este script faz o passo 2 de forma idempotente (o upsert é por
`provider`, então rodar de novo só atualiza) e também semeia os
SCORE CONFIGS usados na avaliação das aulas (idempotente por nome):

  1. espera o langfuse-web responder /api/public/health
     (só responde DEPOIS das migrações de Postgres e ClickHouse);
  2. lista os modelos instalados no Ollama (os de embedding são
     filtrados — eles não servem para chat);
  3. faz o upsert da connection `ollama` pela API pública;
  4. cria (se ainda não existirem) os score configs da disciplina.

Só usa a biblioteca padrão do Python — nada para instalar.

Uso:
    make langfuse-ollama                          # atalho
    python3 scripts/langfuse_ollama_setup.py      # até 300s de espera
    python3 scripts/langfuse_ollama_setup.py --espera 60

Rode de novo depois de `make pull M=...` para o modelo novo aparecer
no Playground.

Códigos de saída:
    0 = connection criada/atualizada (+ score configs se aplicável)
    1 = erro (chaves ausentes, Ollama fora, API recusou)
    2 = Langfuse não respondeu dentro do prazo (ainda migrando?)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

# URL interna: o hostname é o NOME DO SERVIÇO no compose, sempre
# alcançável de dentro da rede fiap-ai-net. `localhost` aqui apontaria
# para o próprio container do Langfuse, não para o Ollama.
OLLAMA_BASE_URL = "http://ollama:11434/v1"
PROVIDER = "ollama"

# Score configs da disciplina — avaliação de qualidade das respostas
# nas aulas de Prompt Engineering e RAG. Idempotente: só cria se
# ainda não houver config ATIVO com o mesmo nome.
SCORE_CONFIGS = [
    {
        "name": "qualidade-resposta",
        "type": "NUMERIC",
        "dataType": "NUMERIC",
        "minValue": 1,
        "maxValue": 5,
        "description": "Qualidade geral da resposta do modelo (1=péssima, 5=excelente).",
    },
    {
        "name": "aderencia-instrucao",
        "type": "NUMERIC",
        "dataType": "NUMERIC",
        "minValue": 0,
        "maxValue": 1,
        "description": "A resposta seguiu a instrução do prompt? (0=não, 1=totalmente).",
    },
    {
        "name": "classificacao-aula",
        "type": "CATEGORICAL",
        "dataType": "CATEGORICAL",
        "categories": [
            {"label": "correta", "value": 1},
            {"label": "parcial", "value": 0.5},
            {"label": "incorreta", "value": 0},
        ],
        "description": "Julgamento rápido do professor durante a aula.",
    },
]

REQUIRED_LANGFUSE_ENV = {
    "LANGFUSE_SALT": 32,
    "LANGFUSE_ENCRYPTION_KEY": 32,
    "LANGFUSE_NEXTAUTH_SECRET": 32,
    "LANGFUSE_PUBLIC_KEY": 20,
    "LANGFUSE_SECRET_KEY": 20,
    "LANGFUSE_ADMIN_EMAIL": 5,
    "LANGFUSE_ADMIN_PASSWORD": 8,
    "LANGFUSE_CLICKHOUSE_PASSWORD": 8,
    "LANGFUSE_REDIS_AUTH": 8,
    "LANGFUSE_MINIO_USER": 3,
    "LANGFUSE_MINIO_PASSWORD": 12,
    "LANGFUSE_S3_BUCKET": 3,
    "LANGFUSE_INIT_ORG_ID": 2,
    "LANGFUSE_INIT_PROJECT_ID": 2,
}
PLACEHOLDER_MARKERS = ("troque", "changeme", "altere", "example", "your-", "xxx")
LANGFUSE_PORTS = (
    "OLLAMA_PORT",
    "WEBUI_PORT",
    "LANGFUSE_PORT",
    "LANGFUSE_MINIO_PORT",
    "LANGFUSE_MINIO_CONSOLE_PORT",
)


def env(nome: str, padrao: str = "") -> str:
    return os.getenv(nome, "").strip() or padrao


def load_dotenv() -> None:
    """Lê o .env do projeto sem depender de python-dotenv.

    Só preenche o que ainda não veio do ambiente (o Makefile já
    exporta o .env inteiro antes de chamar este script).
    """
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    caminho = os.path.join(raiz, ".env")
    if not os.path.isfile(caminho):
        return
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            os.environ.setdefault(chave.strip(), valor.strip())


def validar_configuracao_langfuse() -> bool:
    erros = []
    valores = {}

    for nome, tamanho_minimo in REQUIRED_LANGFUSE_ENV.items():
        valor = env(nome)
        valores[nome] = valor
        if not valor:
            erros.append(f"{nome}: ausente")
            continue
        if len(valor) < tamanho_minimo:
            erros.append(f"{nome}: valor curto demais")
            continue
        if any(marcador in valor.lower() for marcador in PLACEHOLDER_MARKERS):
            erros.append(f"{nome}: placeholder ainda presente")

    if valores.get("LANGFUSE_PUBLIC_KEY") and not valores["LANGFUSE_PUBLIC_KEY"].startswith("pk-lf-"):
        erros.append("LANGFUSE_PUBLIC_KEY: prefixo pk-lf- ausente")
    if valores.get("LANGFUSE_SECRET_KEY") and not valores["LANGFUSE_SECRET_KEY"].startswith("sk-lf-"):
        erros.append("LANGFUSE_SECRET_KEY: prefixo sk-lf- ausente")
    if valores.get("LANGFUSE_ADMIN_EMAIL") and "@" not in valores["LANGFUSE_ADMIN_EMAIL"]:
        erros.append("LANGFUSE_ADMIN_EMAIL: e-mail inválido")

    portas = {}
    for nome in LANGFUSE_PORTS:
        valor = env(nome)
        try:
            numero = int(valor)
            if not 1 <= numero <= 65535:
                raise ValueError
        except ValueError:
            erros.append(f"{nome}: porta inválida")
            continue
        portas[nome] = numero

    if portas.get("WEBUI_PORT") == portas.get("LANGFUSE_PORT"):
        erros.append("WEBUI_PORT e LANGFUSE_PORT não podem ser iguais")
    if portas.get("LANGFUSE_MINIO_PORT") == portas.get("LANGFUSE_MINIO_CONSOLE_PORT"):
        erros.append("LANGFUSE_MINIO_PORT e LANGFUSE_MINIO_CONSOLE_PORT não podem ser iguais")
    if env("LANGFUSE_WHITELISTED_HOST") != "ollama":
        erros.append("LANGFUSE_WHITELISTED_HOST: deve ser ollama")
    if env("WEBUI_OTEL", "true").lower() not in {"1", "true", "yes"}:
        erros.append("WEBUI_OTEL: deve estar habilitado para integração completa")

    if erros:
        print("ERRO: configuração Langfuse incompleta:")
        for erro in erros:
            print(f"  - {erro}")
        print("Rode 'make setup' em uma instalação nova ou corrija somente as variáveis indicadas.")
        return False

    print("Langfuse: secrets, portas, whitelist e OTEL validados.")
    return True


def http(url: str, metodo: str = "GET", payload=None, auth=None, timeout: int = 15):
    dados = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo)
    req.add_header("Content-Type", "application/json")
    if auth:
        token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            corpo = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(corpo)
            except json.JSONDecodeError:
                return resp.status, corpo
    except urllib.error.HTTPError as exc:
        corpo = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(corpo)
        except json.JSONDecodeError:
            return exc.code, corpo


def esperar_langfuse(url: str, segundos: int) -> bool:
    """Espera o /api/public/health — ele só responde com as migrações prontas."""
    print(f"Aguardando o Langfuse ficar de pé (até {segundos}s)...", flush=True)
    limite = time.time() + segundos
    proximo_aviso = 30
    while time.time() < limite:
        try:
            status, _ = http(f"{url}/api/public/health", timeout=5)
            if status == 200:
                print("Langfuse OK (migrações concluídas).")
                return True
        except Exception:  # noqa: BLE001
            pass
        decorrido = int(segundos - (limite - time.time()))
        if decorrido >= proximo_aviso:
            print(f"  ... ainda subindo ({decorrido}s)", flush=True)
            proximo_aviso += 30
        time.sleep(3)
    return False


def modelos_do_ollama() -> list[str]:
    """Modelos de CHAT instalados no Ollama (embedding filtrado)."""
    porta = env("OLLAMA_PORT", "11434")
    status, dados = http(f"http://localhost:{porta}/api/tags", timeout=10)
    if status != 200 or not isinstance(dados, dict):
        raise RuntimeError(f"Ollama não respondeu em localhost:{porta} (HTTP {status})")
    nomes = [
        model["name"]
        for model in dados.get("models", [])
        if model.get("name")
        and "embedding" not in {str(capacidade).lower() for capacidade in model.get("capabilities", [])}
        and "embed" not in model["name"].lower()
    ]
    # O modelo do .env vem primeiro no seletor do Playground. O Ollama
    # grava modelo sem tag explícita como 'nome:latest', então a
    # comparação ignora a tag implícita (mesma regra do integration_test).
    chat = env("CHAT_MODEL")
    if chat:
        encontrado = next(
            (n for n in nomes if n == chat or n.removesuffix(":latest") == chat.removesuffix(":latest")),
            None,
        )
        if encontrado:
            nomes.remove(encontrado)
            nomes.insert(0, encontrado)
    return nomes


def semear_score_configs(langfuse: str, auth: tuple[str, str]) -> int:
    status, lista = http(f"{langfuse}/api/public/score-configs?limit=100", auth=auth)
    if status != 200 or not isinstance(lista, dict):
        raise RuntimeError(f"GET de score configs falhou (HTTP {status})")

    existentes = {
        config.get("name")
        for config in lista.get("data", [])
        if config.get("name") and not config.get("isArchived")
    }
    criados = 0
    for config in SCORE_CONFIGS:
        if config["name"] in existentes:
            continue
        status, resposta = http(
            f"{langfuse}/api/public/score-configs",
            metodo="POST",
            payload=config,
            auth=auth,
        )
        if status not in (200, 201):
            raise RuntimeError(
                f"score config '{config['name']}' recusado (HTTP {status}): "
                f"{json.dumps(resposta)[:200]}"
            )
        criados += 1
        print(f"  score config criado: {config['name']}")

    status, lista = http(f"{langfuse}/api/public/score-configs?limit=100", auth=auth)
    if status != 200 or not isinstance(lista, dict):
        raise RuntimeError(f"GET final de score configs falhou (HTTP {status})")
    confirmados = {
        config.get("name")
        for config in lista.get("data", [])
        if config.get("name") and not config.get("isArchived")
    }
    faltantes = {config["name"] for config in SCORE_CONFIGS} - confirmados
    if faltantes:
        raise RuntimeError(f"score configs ausentes após o bootstrap: {sorted(faltantes)}")
    return criados


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cria a LLM connection Ollama ↔ Langfuse e os score configs"
    )
    parser.add_argument("--espera", type=int, default=300, help="segundos de espera pelo Langfuse")
    parser.add_argument("--check-env", action="store_true", help="valida somente a configuração local")
    args = parser.parse_args()

    load_dotenv()

    if not validar_configuracao_langfuse():
        return 1
    if args.check_env:
        return 0

    pk, sk = env("LANGFUSE_PUBLIC_KEY"), env("LANGFUSE_SECRET_KEY")
    if not pk or not sk:
        print("ERRO: LANGFUSE_PUBLIC_KEY/SECRET_KEY ausentes no .env (rode: make setup).")
        return 1

    langfuse = f"http://localhost:{env('LANGFUSE_PORT', '3001')}"

    if not esperar_langfuse(langfuse, args.espera):
        print(
            "ERRO: o Langfuse não respondeu no prazo. As migrações do primeiro boot\n"
            "      podem estar longas — acompanhe com 'make logs-langfuse' e rode\n"
            "      de novo:  make langfuse-ollama"
        )
        return 2

    try:
        modelos = modelos_do_ollama()
    except Exception as exc:  # noqa: BLE001
        print(f"ERRO: {exc}")
        print("      O Ollama precisa estar no ar (ele sobe junto em TODOS os perfis).")
        return 1

    if not modelos:
        print("ERRO: o Ollama não tem nenhum modelo de chat ainda (make logs-ollama).")
        return 1

    payload = {
        "provider": PROVIDER,
        "adapter": "openai",
        "secretKey": "ollama",
        "baseURL": OLLAMA_BASE_URL,
        "customModels": modelos,
        "withDefaultModels": False,
    }

    status, resposta = http(
        f"{langfuse}/api/public/llm-connections",
        metodo="PUT",
        payload=payload,
        auth=(pk, sk),
    )
    if status not in (200, 201):
        print(f"ERRO: a API do Langfuse recusou a connection (HTTP {status}):")
        print(f"      {json.dumps(resposta)[:400]}")
        print(
            "      Se aparecer 'Blocked IP', a permissão de rede não valeu —\n"
            "      confira LANGFUSE_WHITELISTED_HOST no .env e reinicie o Langfuse."
        )
        return 1

    # Confirmação via GET: prova que a connection ficou gravada no projeto.
    status, lista = http(
        f"{langfuse}/api/public/llm-connections", auth=(pk, sk)
    )
    conexoes = lista.get("data", []) if isinstance(lista, dict) else []
    confirmada = any(
        "ollama" in (c.get("baseURL") or "").lower() for c in conexoes
    )
    if not confirmada:
        print("ERRO: a connection não apareceu no GET de confirmação.")
        return 1

    print(f"LLM connection '{PROVIDER}' pronta em {OLLAMA_BASE_URL}")
    print(f"  {len(modelos)} modelos no Playground: {', '.join(modelos)}")
    print("  Vale para o Playground, o LLM-as-a-judge e os experimentos.")

    try:
        criados = semear_score_configs(langfuse, (pk, sk))
    except Exception as exc:  # noqa: BLE001
        print(f"ERRO: score configs não foram validados: {exc}")
        return 1
    if criados:
        print(f"  {criados} score config(s) de avaliação criados.")
    else:
        print("  score configs já em ordem (ou nenhum novo necessário).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
