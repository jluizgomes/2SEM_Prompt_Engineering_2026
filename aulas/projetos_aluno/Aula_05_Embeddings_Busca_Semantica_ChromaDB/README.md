# Aula 05 — Embeddings e Busca Semântica (ChromaDB)

**Disciplina:** Prompt Engineering and Artificial Intelligence — FIAP · 2º Semestre 2026
**Professor:** Jorge Luiz Gomes

Gera embeddings (nomic-embed-text), indexa no ChromaDB e faz busca por similaridade semântica.

---

## Requisitos

- Python 3.10+
- Ollama local com `nomic-embed-text`

## Como rodar

```bash
cd Aula_05_Embeddings_Busca_Semantica_ChromaDB
python -m venv .venv && source .venv/bin/activate   # recomendado (macOS/Linux)
pip install -r requirements.txt
cp .env.example .env                                 # se ainda não tiver .env
# suba o FIAP AI Lab e garanta o modelo nomic-embed-text
python main.py
```


O banco vetorial fica em ./chroma_db. Para usar o ChromaDB do Docker (FIAP AI Lab), troque PersistentClient por HttpClient (veja comentário no main.py).

## Arquivos

- `main.py` — código principal da aula
- `requirements.txt` — dependências do projeto
- `.env` — configuração local (NÃO versionar)
- `.env.example` — modelo do `.env`
- `.gitignore` — ignora `.env`, `chroma_db/`, `data/`, venv, etc.

## Ollama local para embeddings

O projeto usa `EMBEDDING_OLLAMA_HOST=http://localhost:11434` e
`EMBEDDING_MODEL=nomic-embed-text`. Suba o FIAP AI Lab e garanta que o modelo
`nomic-embed-text` esteja disponível no Ollama local.

---

*Copyright © 2026 Prof. Jorge Luiz Gomes · FIAP · Todos os direitos reservados.*

## Interface web (React + FastAPI)

Além do CLI, este projeto tem uma interface web mínima:

```bash
./rodar.sh          # prepara o ambiente e sobe em http://127.0.0.1:8005
# (Windows: .\rodar.ps1) — passo a passo manual:
#   python3 -m venv .venv && source .venv/bin/activate
#   pip install -r requirements.txt
#   cd frontend && npm install && npm run build
#   python -m uvicorn server:app --port 8005
```

- `server.py` — backend FastAPI: expõe a lógica do exercício em `/api/*` e serve o frontend React (`frontend/dist`).
- `rodar.sh` / `rodar.ps1` — na primeira execução preparam o ambiente (criam o `.venv`, instalam as libs Python, compilam o frontend e criam o `.env` se faltar) e sobem o servidor.
- `frontend/` — app React mínimo (Vite); hot reload com `cd frontend && npm install && npm run dev`.
- 📘 **Manual completo** (portas, notas de ambiente, solução de problemas): veja `../README.md`.
