"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Bônus — Multi-Chains e Multi-Modelos

Projeto local: executar várias chains em PARALELO (RunnableParallel) e
combinar respostas de mais de um modelo sobre a mesma pergunta.

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. python main.py
"""
import os

from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableParallel

# ─────────────────────────────────────────────────────────────
# Configuração via .env
# ─────────────────────────────────────────────────────────────
load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
OLLAMA_MODEL_SECUNDARIO = os.getenv("OLLAMA_MODEL_SECUNDARIO", "gpt-oss:20b")

if not OLLAMA_API_KEY:
    raise RuntimeError(
        "OLLAMA_API_KEY não encontrada. Copie .env.example para .env e preencha a chave."
    )

os.environ["OLLAMA_HOST"] = OLLAMA_HOST
os.environ["OLLAMA_API_KEY"] = OLLAMA_API_KEY

# ─────────────────────────────────────────────────────────────
# 1. Chains especializadas (personas diferentes)
# ─────────────────────────────────────────────────────────────
def chain_persona(persona: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"Você é {persona}. Responda em até 2 frases."),
        ("human", "{pergunta}"),
    ])
    return prompt | ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST,
                               temperature=0.5) | StrOutputParser()


mapa_personas = {
    "resumo": chain_persona("um resumidor técnico objetivo"),
    "pratica": chain_persona("um professor que dá exemplos práticos"),
    "critica": chain_persona("um revisor crítico que aponta limitações"),
}


def executar_personas(pergunta: str, mapa_personas: dict | None = None) -> dict:
    pergunta = str(pergunta).strip()
    if not pergunta:
        raise ValueError("A pergunta não pode estar vazia.")
    chains = mapa_personas if mapa_personas is not None else globals()["mapa_personas"]
    ramos = {
        nome: RunnableLambda(
            lambda entrada, persona_chain=cadeia: persona_chain.invoke(entrada)
        )
        for nome, cadeia in chains.items()
    }
    return RunnableParallel(ramos).invoke({"pergunta": pergunta})


def _modelo_configurado(valor: str | None, padrao: str) -> str:
    modelo = (valor or padrao).strip()
    if not modelo:
        raise ValueError("O nome do modelo não pode estar vazio.")
    return modelo


def chain_modelo(modelo: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Responda de forma precisa e autocontida."),
        ("human", "{pergunta}"),
    ])
    llm = ChatOllama(model=modelo, base_url=OLLAMA_HOST, temperature=0)
    return prompt | llm | StrOutputParser()


def chain_sintese(modelo: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Sintetize as respostas recebidas em uma resposta única, preservando "
            "acertos, divergências e limitações. Não acrescente fatos ausentes."
        )),
        ("human", (
            "Pergunta: {pergunta}\n"
            "Respostas úteis: {respostas}\n"
            "Modelos indisponíveis: {modelos_indisponiveis}"
        )),
    ])
    llm = ChatOllama(model=modelo, base_url=OLLAMA_HOST, temperature=0)
    return prompt | llm | StrOutputParser()


def _executar_modelo(papel: str, modelo: str, pergunta: str, fabrica_chain) -> dict:
    resultado = {
        "papel": papel,
        "modelo": modelo,
        "texto": None,
        "erro": None,
    }
    try:
        texto = fabrica_chain(modelo).invoke({"pergunta": pergunta})
        resultado["texto"] = str(texto).strip()
        if not resultado["texto"]:
            resultado["erro"] = "o modelo retornou resposta vazia"
    except Exception as e:
        resultado["erro"] = f"{type(e).__name__}: {e}"
    return resultado


def executar_multi_modelos(
    pergunta: str,
    modelo_primario: str | None = None,
    modelo_secundario: str | None = None,
    fabrica_chain=None,
    fabrica_sintese=None,
) -> dict:
    pergunta = str(pergunta).strip()
    if not pergunta:
        raise ValueError("A pergunta não pode estar vazia.")

    primario = _modelo_configurado(modelo_primario, OLLAMA_MODEL)
    secundario = _modelo_configurado(modelo_secundario, OLLAMA_MODEL_SECUNDARIO)
    fabrica = fabrica_chain or chain_modelo

    paralelo = RunnableParallel(
        primario=RunnableLambda(
            lambda entrada: _executar_modelo(
                "primario", primario, entrada["pergunta"], fabrica
            )
        ),
        secundario=RunnableLambda(
            lambda entrada: _executar_modelo(
                "secundario", secundario, entrada["pergunta"], fabrica
            )
        ),
    )
    respostas = paralelo.invoke({"pergunta": pergunta})
    disponiveis = {
        papel: item["texto"]
        for papel, item in respostas.items()
        if item["erro"] is None
    }
    if not disponiveis:
        raise RuntimeError("Nenhum modelo respondeu; a saída não pode ser sintetizada.")

    indisponiveis = [
        {"papel": item["papel"], "modelo": item["modelo"], "erro": item["erro"]}
        for item in respostas.values()
        if item["erro"] is not None
    ]
    rotulos = {"primario": "primário", "secundario": "secundário"}
    avisos = [
        f"O modelo {rotulos[item['papel']]} ({item['modelo']}) falhou: {item['erro']}"
        for item in indisponiveis
    ]
    modelo_sintese = respostas["primario"]["modelo"] if "primario" in disponiveis else secundario
    fabrica_sintetizador = fabrica_sintese or chain_sintese

    try:
        sintese = str(fabrica_sintetizador(modelo_sintese).invoke({
            "pergunta": pergunta,
            "respostas": disponiveis,
            "modelos_indisponiveis": indisponiveis,
        })).strip()
        if not sintese:
            raise RuntimeError("o modelo sintetizador retornou resposta vazia")
    except Exception as e:
        sintese = "\n\n".join(
            f"[{papel} · {respostas[papel]['modelo']}]\n{texto}"
            for papel, texto in disponiveis.items()
        )
        avisos.append(
            f"A síntese automática falhou ({type(e).__name__}: {e}); "
            "foi retornada a combinação literal das respostas recebidas."
        )

    return {
        "respostas": respostas,
        "sintese": sintese,
        "degradado": bool(avisos),
        "avisos": avisos,
    }


def demo_parallel() -> None:
    print("\n== RunnableParallel (3 chains ao mesmo tempo) ==")
    resultados = executar_personas("O que é RAG?")
    for chave, texto in resultados.items():
        print(f"\n[{chave}]\n  {texto}")


def demo_multi_modelos() -> None:
    print("\n== Multi-modelos (mesma pergunta, modelos diferentes) ==")
    resultado = executar_multi_modelos("Defina 'embedding' em uma frase.")
    for papel, item in resultado["respostas"].items():
        status = item["texto"] if item["texto"] is not None else f"indisponível: {item['erro']}"
        print(f"  [{papel} · {item['modelo']}] {status}")
    print("\n== Síntese ==")
    print(resultado["sintese"])
    for aviso in resultado["avisos"]:
        print(f"  Aviso: {aviso}")


def main() -> None:
    print(f"Ollama Cloud | modelo primário: {OLLAMA_MODEL}")
    print(f"Modelo secundário: {OLLAMA_MODEL_SECUNDARIO}")
    demo_parallel()
    demo_multi_modelos()


if __name__ == "__main__":
    main()
