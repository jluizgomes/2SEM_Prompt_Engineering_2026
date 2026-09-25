# Aula 11 — Integradora: Agente + RAG + Gradio

**Disciplina:** Prompt Engineering and Artificial Intelligence — FIAP · 2º Semestre 2026
**Professor:** Jorge Luiz Gomes

RAG como tool nativa (create_retriever_tool) + busca web + calculadora, tudo num agente com interface Gradio.

---

## Requisitos

- Python 3.10+
- Chave da Ollama Cloud (`OLLAMA_API_KEY`)
- Ollama local com `nomic-embed-text`

## Como rodar

```bash
cd Aula_11_Integradora_Agente_RAG_Gradio
python -m venv .venv && source .venv/bin/activate   # recomendado (macOS/Linux)
pip install -r requirements.txt
cp .env.example .env                                 # se ainda não tiver .env
# preencha OLLAMA_API_KEY e suba o Ollama local para embeddings
python main.py
```


Gradio: python main.py (porta 7860).

## Arquivos

- `main.py` — código principal da aula
- `requirements.txt` — dependências do projeto
- `.env` — configuração (NÃO versionar)
- `.env.example` — modelo do `.env`
- `.gitignore` — ignora `.env`, `chroma_db/`, `data/`, venv, etc.

## Ollama Cloud + embeddings locais

O chat usa Ollama Cloud (`OLLAMA_HOST` e `OLLAMA_MODEL`). Os embeddings usam
`EMBEDDING_OLLAMA_HOST=http://localhost:11434` e
`EMBEDDING_MODEL=nomic-embed-text`. Suba o FIAP AI Lab e garanta que o modelo
de embeddings esteja disponível no Ollama local.

---

*Copyright © 2026 Prof. Jorge Luiz Gomes · FIAP · Todos os direitos reservados.*
