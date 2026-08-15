"""
Guardrail de Input — CKP03 (Diferencial)

Valida se a pergunta do usuário está dentro do escopo do domínio CDC
antes de gastar tokens do agente.

CKP03 diferencial: rejeitar perguntas fora do domínio com mensagem educada.
"""

# Palavras-chave que indicam escopo de direito do consumidor
PALAVRAS_CONSUMIDOR = [
    # Geral
    "consumidor", "cdc", "código de defesa", "direito do consumidor",
    "procon", "reclamação", "garantia",
    # Produtos
    "produto", "defeito", "vício", "troca", "devolução", "reembolso",
    "celular", "eletrodoméstico", "carro", "veículo", "móvel",
    # Serviços
    "serviço", "serviço", "prestador", "orçamento",
    # Contratos
    "contrato", "adesão", "cláusula", "cancelamento", "fidelidade",
    "arrependimento", "desistência",
    # Práticas
    "abusiva", "abusivo", "venda casada", "enganosa", "publicidade",
    "cobrança", "indevida", "juros", "multa",
    # Prazos
    "prazo", "dias", "meses", "anos", "data", "vencimento",
    # Financeiro de consumo
    "compra", "compra online", "internet", "loja", "fornecedor",
    "nota fiscal", "nf", "pagamento", "boleto", "cartão",
]

# Palavras que indicam FORA do escopo (outros ramos do direito)
FORA_ESCOPO = [
    "penal", "crime", "prisão", "criminal",
    "trabalhista", "trabalho", "clt", "rescisão", "férias", "salário",
    "tributário", "imposto de renda", "irpf", "receita federal",
    "família", "divórcio", "pensão alimentícia", "guarda",
    "trânsito", "multa de trânsito", "cnh", "detran",
    "imobiliário", "aluguel", "inquilino", "locador",  # Exceto relação de consumo
]


def validar_input(pergunta: str) -> tuple[bool, str]:
    """
    Valida se a pergunta está dentro do escopo do domínio CDC.

    Estratégia:
    1. Verifica palavras-chave de direito do consumidor
    2. Verifica palavras fora do escopo (outros ramos do direito)
    3. Perguntas muito curtas ou genéricas passam (o agente decide)

    Args:
        pergunta: texto da pergunta do usuário

    Returns:
        (válido, mensagem) — se válido=True, mensagem=""
    """
    pergunta_lower = pergunta.lower().strip()

    # Perguntas muito curtas: permitir (cumprimentos, etc.)
    if len(pergunta_lower) < 10:
        return True, ""

    # Verifica palavras fora do escopo primeiro
    for palavra in FORA_ESCOPO:
        if palavra in pergunta_lower:
            return False, (
                f"⚠️ Sua pergunta parece ser sobre {palavra}, que está fora "
                f"da minha especialidade.\n\n"
                f"Sou especializado em **Direito do Consumidor** (CDC - Lei 8.078/90). "
                f"Para este assunto, recomendo consultar um advogado especializado "
                f"na área adequada.\n\n"
                f"Posso ajudar com: garantia de produtos, trocas, devoluções, "
                f"práticas abusivas, contratos de consumo, prazos legais, etc."
            )

    # Verifica palavras dentro do escopo
    for palavra in PALAVRAS_CONSUMIDOR:
        if palavra in pergunta_lower:
            return True, ""

    # Se não encontrou palavras de consumo nem de fora do escopo:
    # Permite passar (pode ser pergunta genérica ou conversa informal)
    return True, ""


if __name__ == "__main__":
    testes = [
        "Comprei um celular e veio com defeito",
        "Qual o prazo para trocar um produto?",
        "Fui demitido, quais meus direitos trabalhistas?",  # fora do escopo
        "Oi, tudo bem?",
        "Como calcular imposto de renda?",  # fora do escopo
        "A loja se recusou a trocar o produto",
    ]

    for t in testes:
        ok, msg = validar_input(t)
        status = "✅" if ok else "🚫 BLOQUEADO"
        print(f"{status} | {t[:50]:50s} | {msg[:80] if msg else '-'}")
