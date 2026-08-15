# CKP02 — DocMind RAG · Consultor CDC

**Prompt Engineering & AI · FIAP · 2º Semestre 2026**
**Peso: 30% da nota · Entrega: Aula 07**

## Projeto 100% standalone

Pipeline RAG completo sobre o Codigo de Defesa do Consumidor (Lei 8.078/90).
Nao depende de nenhum outro CKP.

## Requisitos atendidos

| Requisito | Status | Implementacao |
|---|---|---|
| Base de conhecimento real (≥5 docs) | ✅ | 5 arquivos .txt com trechos reais do CDC |
| RecursiveCharacterTextSplitter | ✅ | `separators=['\n\n','\n','. ',' ']` |
| 2+ estrategias de chunking | ✅ | 256, 512, 1024 comparados em `chunking.py` |
| nomic-embed-text | ✅ | Via Ollama (local ou cloud) |
| ChromaDB local | ✅ | `PersistentClient` em `chromadb_data/` |
| Pipeline end-to-end | ✅ | load → split → embed → store → retrieve → generate |
| RAGAS faithfulness (≥5 perguntas) | ✅ | 7 perguntas com heuristica de faithfulness |
| Metadata filtering | ✅ | Categorizacao por tipo de documento |
| Interface Gradio | ✅ | `python -m app.main` |

## Estrutura

```
ckp02-rag/
├── app/
│   ├── main.py         # Interface Gradio + entry point
│   ├── pipeline.py     # Pipeline RAG completo
│   └── chunking.py     # Comparacao de chunking + RAGAS
├── data/               # 5 documentos TXT do CDC
├── chromadb_data/      # Persistencia (gerado apos indexacao)
├── .env / .env.example
├── requirements.txt
└── README.md
```

## Como executar

```bash
# 1. Configure
cp .env.example .env

# 2. Instale dependencias
pip install -r requirements.txt

# 3. Indexe os documentos
python -m app.main --index

# 4. Compare estrategias de chunking
python -m app.main --compare

# 5. Inicie a interface Gradio
python -m app.main
# Acesse: http://localhost:7860

# 6. Consulta via terminal
python -m app.main --query "Quais os prazos para reclamar de vicios?"
```

## Resultados esperados do chunking

| Chunk Size | Faithfulness Medio | Meta (≥0.7)? |
|---|---|---|
| 256 | ~0.85 | ✅ |
| 512 | ~0.78 | ✅ |
| 1024 | ~0.65 | ❌ |

Recomendacao: `chunk_size=512` — melhor equilibrio entre precisao e contexto.
