# Aula 06 — Pipeline RAG Completo

**Disciplina:** Prompt Engineering and Artificial Intelligence — FIAP · 2º Semestre 2026
**Professor:** Jorge Luiz Gomes

RAG de ponta a ponta: carrega PDF (PyMuPDF), divide em chunks, indexa e responde citando o contexto.

---

## Requisitos

- Python 3.10+
- Ollama local em `http://localhost:11434` (modelo `gpt-oss:120b`; embeddings: `nomic-embed-text`)

## Como rodar

```bash
cd Aula_06_Pipeline_RAG_Completo
python -m venv .venv && source .venv/bin/activate   # recomendado (macOS/Linux)
pip install -r requirements.txt
cp .env.example .env                                 # se ainda não tiver .env
python main.py
```


Opcional: coloque um PDF em ./data/ para indexar. Sem PDF, usa texto de exemplo embutido.

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
3. Nas aulas de RAG, baixe `nomic-embed-text`.

---

*Copyright © 2026 Prof. Jorge Luiz Gomes · FIAP · Todos os direitos reservados.*

## Interface web (React + FastAPI)

Além do CLI, este projeto tem uma interface web mínima:

```bash
./rodar.sh          # prepara o ambiente e sobe em http://127.0.0.1:8106
# (Windows: .\rodar.ps1) — passo a passo manual:
#   python3 -m venv .venv && source .venv/bin/activate
#   pip install -r requirements.txt
#   cd frontend && npm install && npm run build
#   python -m uvicorn server:app --port 8106
```

- `server.py` — backend FastAPI: expõe a lógica do exercício em `/api/*` e serve o frontend React (`frontend/dist`).
- `rodar.sh` / `rodar.ps1` — na primeira execução preparam o ambiente (criam o `.venv`, instalam as libs Python, compilam o frontend e criam o `.env` se faltar) e sobem o servidor.
- `frontend/` — app React mínimo (Vite); hot reload com `cd frontend && npm install && npm run dev`.
- 📘 **Manual completo** (portas, notas de ambiente, solução de problemas): veja `../README.md`.
