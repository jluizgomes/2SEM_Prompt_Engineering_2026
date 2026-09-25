# Aula 06 — Pipeline RAG Completo

**Disciplina:** Prompt Engineering and Artificial Intelligence — FIAP · 2º Semestre 2026
**Professor:** Jorge Luiz Gomes

RAG de ponta a ponta: carrega PDF (PyMuPDF), divide em chunks, indexa e responde citando o contexto.

---

## Requisitos

- Python 3.10+
- Chave da Ollama Cloud (`OLLAMA_API_KEY`)
- Ollama local com `nomic-embed-text`

## Como rodar

```bash
cd Aula_06_Pipeline_RAG_Completo
python -m venv .venv && source .venv/bin/activate   # recomendado (macOS/Linux)
pip install -r requirements.txt
cp .env.example .env                                 # se ainda não tiver .env
# preencha OLLAMA_API_KEY e suba o Ollama local para embeddings
python main.py
```


Opcional: coloque um PDF em ./data/ para indexar. Sem PDF, usa texto de exemplo embutido.

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

## Interface web (React + FastAPI)

Além do CLI, este projeto tem uma interface web mínima:

```bash
./rodar.sh          # prepara o ambiente e sobe em http://127.0.0.1:8006
# (Windows: .\rodar.ps1) — passo a passo manual:
#   python3 -m venv .venv && source .venv/bin/activate
#   pip install -r requirements.txt
#   cd frontend && npm install && npm run build
#   python -m uvicorn server:app --port 8006
```

- `server.py` — backend FastAPI: expõe a lógica do exercício em `/api/*` e serve o frontend React (`frontend/dist`).
- `rodar.sh` / `rodar.ps1` — na primeira execução preparam o ambiente (criam o `.venv`, instalam as libs Python, compilam o frontend e criam o `.env` se faltar) e sobem o servidor.
- `frontend/` — app React mínimo (Vite); hot reload com `cd frontend && npm install && npm run dev`.
- 📘 **Manual completo** (portas, notas de ambiente, solução de problemas): veja `../README.md`.
