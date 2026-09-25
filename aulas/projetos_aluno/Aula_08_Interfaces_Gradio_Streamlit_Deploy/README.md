# Aula 08 — Interfaces (Gradio e Streamlit)

**Disciplina:** Prompt Engineering and Artificial Intelligence — FIAP · 2º Semestre 2026
**Professor:** Jorge Luiz Gomes

Expõe uma chain com memória por sessão em Gradio (main.py) e Streamlit (app_streamlit.py).

---

## Requisitos

- Python 3.10+
- Chave da Ollama Cloud (`OLLAMA_API_KEY`)

## Como rodar

```bash
cd Aula_08_Interfaces_Gradio_Streamlit_Deploy
python -m venv .venv && source .venv/bin/activate   # recomendado (macOS/Linux)
pip install -r requirements.txt
cp .env.example .env                                 # se ainda não tiver .env
# edite .env e preencha OLLAMA_API_KEY (a mesma chave já está no .env da pasta 2SEM)
python main.py
```


Gradio: python main.py (porta 7860). Streamlit: streamlit run app_streamlit.py.

## Arquivos

- `main.py` — código principal da aula
- `app_streamlit.py` — variante da interface
- `requirements.txt` — dependências do projeto
- `.env` — configuração (NÃO versionar)
- `.env.example` — modelo do `.env`
- `.gitignore` — ignora `.env`, `chroma_db/`, `data/`, venv, etc.

## Backend do chat

O chat usa Ollama Cloud. O `.env.example` também separa a configuração de
embeddings em `EMBEDDING_OLLAMA_HOST` para as atividades de RAG, que devem usar
o Ollama local com `nomic-embed-text`.

---

*Copyright © 2026 Prof. Jorge Luiz Gomes · FIAP · Todos os direitos reservados.*
