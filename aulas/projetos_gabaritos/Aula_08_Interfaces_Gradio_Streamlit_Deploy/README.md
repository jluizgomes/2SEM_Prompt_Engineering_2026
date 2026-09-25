# Aula 08 — Interfaces (Gradio e Streamlit)

**Disciplina:** Prompt Engineering and Artificial Intelligence — FIAP · 2º Semestre 2026
**Professor:** Jorge Luiz Gomes

Expõe uma chain RAG com corpus local e memória isolada por sessão em Gradio (main.py) e Streamlit (app_streamlit.py).

---

## Requisitos

- Python 3.10+
- Ollama local em `http://localhost:11434` (modelo `gpt-oss:120b`; embeddings: `nomic-embed-text`)

## Como rodar

```bash
cd Aula_08_Interfaces_Gradio_Streamlit_Deploy
python -m venv .venv && source .venv/bin/activate   # recomendado (macOS/Linux)
pip install -r requirements.txt
cp .env.example .env                                 # se ainda não tiver .env
python main.py
```


Gradio: python main.py (porta 7860). Streamlit: streamlit run app_streamlit.py.

Na primeira pergunta, o projeto carrega o corpus de `data/corpus.txt`, cria a coleção local em `chroma_db/` e inicializa o modelo. Os imports das interfaces não inicializam o LLM nem fazem chamadas externas. Cada navegador recebe um identificador de sessão próprio para o histórico do RAG.

## Arquivos

- `main.py` — interface Gradio com estado isolado por sessão
- `app_streamlit.py` — variante da interface Streamlit
- `rag.py` — corpus, vector store, chain RAG e memória por sessão
- `data/corpus.txt` — corpus local usado na recuperação
- `tests/test_rag.py` — testes focados com doubles, sem rede
- `requirements.txt` — dependências do projeto
- `.env` — configuração local; não versionar
- `.env.example` — modelo do `.env`
- `.gitignore` — ignora `.env`, `chroma_db/`, artefatos locais e venv

## Ollama local

O `.env.example` aponta para `http://localhost:11434` e define `OLLAMA_API_KEY=ollama`.

1. Inicie o serviço com `ollama serve`.
2. Baixe o modelo com `ollama pull gpt-oss:120b`.
3. Baixe `nomic-embed-text` para os embeddings do RAG.

---

*Copyright © 2026 Prof. Jorge Luiz Gomes · FIAP · Todos os direitos reservados.*
