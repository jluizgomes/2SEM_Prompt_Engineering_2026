# CKP Projects — Prompt Engineering & AI · FIAP · 2º Semestre 2026

Projetos completos e independentes para os 3 Checkpoints da disciplina.

## Estrutura

```
ckp-projects/
├── ckp01-chatbot/     # Aula 04 — 25% — Chatbot Profissional
├── ckp02-rag/         # Aula 07 — 30% — DocMind RAG
└── ckp03-agente/      # Aula 11 — 45% — Agente Inteligente
```

**Cada projeto eh 100% standalone** — nao depende de nenhum outro.
Todos usam o mesmo dominio (Consultoria CDC) mas com implementacoes independentes.

## Progressao

| CKP | Peso | O que faz |
|---|---|---|
| 01 | 25% | Chatbot com LangChain LCEL + memoria window + Pydantic + context rot |
| 02 | 30% | Pipeline RAG com ChromaDB + 3 estrategias de chunking + RAGAS |
| 03 | 45% | Agente ReAct com 4 tools + RAG proprio + Gradio com URL publica |

## Como executar cada um

```bash
# CKP01 — Chatbot
cd ckp01-chatbot
pip install -r requirements.txt
python -m app.main              # http://localhost:7860
python -m app.main --demo       # Demo context rot no terminal

# CKP02 — RAG
cd ../ckp02-rag
pip install -r requirements.txt
python -m app.main --index       # Indexar documentos
python -m app.main --compare     # Comparar chunking
python -m app.main               # Interface Gradio

# CKP03 — Agente
cd ../ckp03-agente
pip install -r requirements.txt
python -m app.main --test        # Testar 6 perguntas
python -m app.main               # Interface Gradio com URL publica
```

## Pre-requisitos comuns

- Python 3.11+
- Ollama rodando (local ou cloud)
- ChromaDB (local, cada projeto usa sua propria instancia)

Para subir Ollama + ChromaDB via Docker:
```bash
cd ../../fiap-ai-lab-complete
docker compose up -d
```
