#!/usr/bin/env python3
"""Ajusta o SearXNG para usar apenas buscadores que respondem nesta rede.

Por que isso existe: os engines padrão do SearXNG (DuckDuckGo, Google,
Startpage, Brave) bloqueiam consultas automatizadas com CAPTCHA ou HTTP 429.
Quando o engine padrão falha, o SearXNG responde 200 com `results: []` — a
busca "funciona" mas volta vazia, e o Open WebUI/LangChain recebe zero
resultados. Além disso, cada engine bloqueado gasta o timeout da busca.

Este script deixa ligados só os engines que devolvem resultados e desliga
os bloqueados. É idempotente: rodar de novo não duplica nada.

Uso:
    python3 scripts/searxng_engines.py [caminho/settings.yml]
    make searxng-engines
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

# Engines verificados com ?format=json
CONFIAVEIS = ["bing", "wiby"]
# Bloqueados com CAPTCHA / 429 nesta rede
BLOQUEADOS = [
    "duckduckgo",
    "google",
    "startpage",
    "brave",
    "mojeek",
    "qwant",
    "karmasearch",
    "karmasearch videos",
]

BLOCO = """# ------------------------------------------------------------
# Engines
# ------------------------------------------------------------
# `use_default_settings: true` mantém todos os engines do upstream;
# aqui só ligamos/desligamos pelo nome. Se a sua rede não sofrer
# bloqueio, reative um destes trocando `disabled: true` por `false`.
# Gerado por scripts/searxng_engines.py (make searxng-engines).
engines:
  # Confiáveis nesta rede (verificado com ?format=json)
{confiaveis}
  # Bloqueados com CAPTCHA / HTTP 429 — devolvem 0 resultados e ainda
  # gastam o timeout da busca esperando cada um.
{bloqueados}
"""


def bloco_engines() -> str:
    confiaveis = "\n".join(
        f"  - name: {nome}\n    disabled: false" for nome in CONFIAVEIS
    )
    bloqueados = "\n".join(
        f"  - name: {nome}\n    disabled: true" for nome in BLOQUEADOS
    )
    return BLOCO.format(confiaveis=confiaveis, bloqueados=bloqueados)


def ajustar(caminho: Path) -> int:
    if not caminho.is_file():
        print(f"  ERRO: {caminho} não encontrado.")
        return 1

    texto = caminho.read_text(encoding="utf-8")

    # Remove um bloco `engines:` anterior (gerado por este script)
    texto_sem_bloco = re.sub(
        r"# -+\n# Engines\n# -+\n(?:#[^\n]*\n)*engines:\n(?:[ \t]+[^\n]*\n|\n)*",
        "",
        texto,
    )

    if texto_sem_bloco != texto:
        print("  Bloco de engines anterior removido.")
        texto = texto_sem_bloco

    # Insere o bloco antes de `server:`
    if "\nserver:" not in texto:
        print("  ERRO: não encontrei a seção `server:` para ancorar o bloco.")
        return 1
    texto = texto.replace("\nserver:", "\n" + bloco_engines() + "\nserver:", 1)

    # Autocomplete: usa um engine que responde
    texto = re.sub(
        r'(\n\s*autocomplete:\s*)["\']?[^"\'\n]*["\']?',
        r'\1"bing"',
        texto,
        count=1,
    )

    backup = caminho.with_suffix(caminho.suffix + ".bak")
    if not backup.exists():
        shutil.copy2(caminho, backup)
        print(f"  Backup criado: {backup.name}")

    caminho.write_text(texto, encoding="utf-8")
    print(f"  {caminho} atualizado.")
    print(f"    ligados   : {', '.join(CONFIAVEIS)}")
    print(f"    desligados: {', '.join(BLOQUEADOS)}")
    return 0


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("searxng/settings.yml")
    print("")
    return ajustar(destino)


if __name__ == "__main__":
    sys.exit(main())
