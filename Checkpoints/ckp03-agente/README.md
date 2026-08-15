# CKP03 — Agente Inteligente · Consultor CDC

**Prompt Engineering & AI · FIAP · 2º Semestre 2026**
**Peso: 45% da nota · Entrega: Aula 11**

## Projeto 100% standalone

Este projeto nao depende de nenhum outro CKP. O pipeline RAG esta embutido
no proprio agente — basta ter documentos .txt na pasta `data/`.

## Requisitos atendidos

| Requisito | Status | Implementacao |
|---|---|---|
| RAG como tool | ✅ | `consultar_cdc` — pipeline proprio em `tools.py` |
| 2+ tools adicionais | ✅ | `calcular_prazos_cdc`, `classificar_pratica_abusiva`, `orgaos_defesa` |
| AgentExecutor (ReAct) | ✅ | `agent.py` — `create_react_agent + AgentExecutor` |
| Interface Gradio | ✅ | `main.py` — `gr.ChatInterface` |
| URL publica ao vivo | ✅ | `demo.launch(share=True)` |
| 3 interacoes documentadas | ✅ | `--test` com 6 perguntas (2 RAG, 2 tool, 2 sem tool) |
| Guardrail de input | ✅ | `guardrail.py` — rejeita perguntas fora do escopo |
| 4 tools | ✅ | 1 RAG + 3 dominio |

## Estrutura

```
ckp03-agente/
├── app/
│   ├── main.py         # Interface Gradio + entry point
│   ├── agent.py        # Agente ReAct + AgentExecutor
│   ├── tools.py        # 4 tools + pipeline RAG proprio embutido
│   └── guardrail.py    # Validacao de input
├── data/               # Documentos TXT do CDC (5 arquivos)
├── chromadb_data/      # Persistencia (gerado apos primeira execucao)
├── .env / .env.example
├── requirements.txt
└── README.md
```

## Tools disponiveis

| Tool | O que faz |
|---|---|
| `consultar_cdc` | Busca semantica nos documentos do CDC (RAG proprio) |
| `calcular_prazos_cdc` | Calcula prazos legais (7d, 30d, 90d, 5 anos) |
| `classificar_pratica_abusiva` | Analisa conduta de fornecedor (Art. 39) |
| `orgaos_defesa` | Informa onde e como reclamar |

## Como executar

```bash
# 1. Configure
cp .env.example .env

# 2. Instale dependencias
pip install -r requirements.txt

# 3. Execute o agente com URL publica
python -m app.main
# Acesse: http://localhost:7860

# 4. Teste com 6 perguntas
python -m app.main --test

# 5. Testar guardrail
python -m app.main --guardrail
```

Na primeira execucao, o pipeline RAG indexa automaticamente os documentos
da pasta `data/` no ChromaDB.

## Exemplos de interacao

### Com RAG
> "Quais sao as sancoes que uma empresa pode sofrer por violar o CDC?"
> [Usa `consultar_cdc`] Resposta com citacao do Art. 56 e fontes.

### Com calculadora de prazos
> "Comprei um celular em 15/08/2026. Ate quando posso me arrepender?"
> [Usa `calcular_prazos_cdc`] Data limite: 22/08/2026 — Art. 49.

### Sem tool
> "Oi, bom dia! Quem eh voce?"
> [Responde diretamente] Apresentacao do Dr. Consumidor.
