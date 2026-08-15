# CKP01 — Chatbot Profissional · Consultor CDC

**Prompt Engineering & AI · FIAP · 2º Semestre 2026**
**Peso: 25% da nota · Entrega: Aula 04**

## Domínio

Consultoria em Direito do Consumidor Brasileiro com base no CDC (Lei 8.078/90).

## Requisitos atendidos

| Requisito | Status | Implementação |
|---|---|---|
| Pipeline LCEL | ✅ | `chain.py` — `prompt \| llm \| StrOutputParser()` |
| ChatOllama | ✅ | `gpt-oss:120b` via Ollama Cloud ou `qwen3.5:0.8b` local |
| Memória gerenciada | ✅ | `ConversationBufferWindowMemory(k=6)` — justificada em `memory_manager.py` |
| Pydantic v2 (≥4 campos) | ✅ | `AnaliseConsulta` com 6 campos + validators em `schemas.py` |
| Context rot | ✅ | `context_rot.py` — tabela com degradação em 0, 5, 10, 15, 20 turnos |
| Domínio documentado | ✅ | Este README + system prompt rico em `prompts.py` |

## Estrutura

```
ckp01-chatbot/
├── app/
│   ├── __init__.py
│   ├── main.py           # Interface Gradio + entry point
│   ├── chain.py          # Pipeline LCEL
│   ├── memory_manager.py # 3 estratégias de memória
│   ├── schemas.py        # Pydantic v2 (AnaliseConsulta, RelatorioSessao)
│   ├── context_rot.py    # Demonstração de degradação
│   └── prompts.py        # System prompts
├── .env.example
├── requirements.txt
└── README.md
```

## Como executar

```bash
# 1. Configure o ambiente
cp .env.example .env
# Edite .env com sua OLLAMA_API_KEY (cloud) ou URL local

# 2. Instale dependências
pip install -r requirements.txt

# 3. Execute a interface Gradio
python -m app.main
# Acesse: http://localhost:7860

# 4. Demo context rot (terminal)
python -m app.main --demo
```

## Justificativa da memória

**Window Buffer (k=6)** — Consultas jurídicas típicas duram 5-8 turnos.
A janela deslizante mantém custo de tokens constante após k turnos
sem perder o contexto relevante da conversa atual.

## Schema Pydantic — AnaliseConsulta

| Campo | Tipo | Descrição |
|---|---|---|
| `categoria` | Literal (8 opções) | Classificação CDC da consulta |
| `artigos_relevantes` | list[str] | Artigos do CDC aplicáveis |
| `urgencia` | Literal (3 níveis) | baixa / média / alta |
| `prazo_aplicavel` | Optional[str] | Prazo legal (ex: "7 dias - Art. 49") |
| `resumo_tecnico` | str (20-300 chars) | Resumo técnico-jurídico |
