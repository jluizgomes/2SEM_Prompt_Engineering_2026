# Aula 11 — Integradora: Agente + RAG + Gradio

**Disciplina:** Prompt Engineering and Artificial Intelligence — FIAP · 2º Semestre 2026
**Professor:** Jorge Luiz Gomes

RAG como tool nativa (create_retriever_tool) + busca web + calculadora, tudo num agente com interface Gradio.

---

## Requisitos

- Python 3.10+
- Ollama local em `http://localhost:11434` (modelo `gpt-oss:120b`; embeddings: `nomic-embed-text`)

## Como rodar

```bash
cd Aula_11_Integradora_Agente_RAG_Gradio
python -m venv .venv && source .venv/bin/activate   # recomendado (macOS/Linux)
pip install -r requirements.txt
cp .env.example .env                                 # se ainda não tiver .env
python main.py
```


Gradio: python main.py (porta 7860).

## Arquivos

- `main.py` — código principal da aula
- `requirements.txt` — dependências do projeto
- `.env` — configuração local; não versionar
- `.env.example` — modelo do `.env`
- `.gitignore` — ignora `.env`, `chroma_db/`, `data/`, venv, etc.

## Ollama local

O `.env.example` aponta para `http://localhost:11434` e define `OLLAMA_API_KEY=ollama`.

1. Inicie o serviço com `ollama serve`.
2. Baixe o modelo com `ollama pull gpt-oss:120b`.
3. Baixe `nomic-embed-text` para os embeddings do RAG.

---

*Copyright © 2026 Prof. Jorge Luiz Gomes · FIAP · Todos os direitos reservados.*
