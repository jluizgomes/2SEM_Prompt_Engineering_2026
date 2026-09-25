# Aula 02 — Memória Conversacional

**Disciplina:** Prompt Engineering and Artificial Intelligence — FIAP · 2º Semestre 2026
**Professor:** Jorge Luiz Gomes

Três tipos de memória (Buffer, Summary, TokenBuffer) com ConversationChain, mais prompt customizado por domínio.

---

## Requisitos

- Python 3.10+
- Chave da Ollama Cloud (`OLLAMA_API_KEY`)

## Como rodar

```bash
cd Aula_02_Memoria_Conversacional
python -m venv .venv && source .venv/bin/activate   # recomendado (macOS/Linux)
pip install -r requirements.txt
cp .env.example .env                                 # se ainda não tiver .env
# edite .env e preencha OLLAMA_API_KEY (a mesma chave já está no .env da pasta 2SEM)
python main.py
```



## Arquivos

- `main.py` — código principal da aula
- `requirements.txt` — dependências do projeto
- `.env` — variáveis de ambiente (chave da API; NÃO versionar)
- `.env.example` — modelo do `.env`
- `.gitignore` — ignora `.env`, `chroma_db/`, `data/`, venv, etc.

## Usar Ollama LOCAL (gratuito, FIAP AI Lab)

Por padrão o projeto usa o Ollama Cloud (`https://ollama.com`). Para usar o
Ollama local do Docker (modelo `gpt-oss:120b`, sem custo):

1. No `.env`, comente as linhas `OLLAMA_HOST`/`OLLAMA_API_KEY` atuais e descomente as alternativas;
2. Ajuste `OLLAMA_MODEL` para `gpt-oss:120b`;
3. Suba o lab: `cd ../../fiap-ai-lab-complete && make up` (ou `make up-minimum`).

---

*Copyright © 2026 Prof. Jorge Luiz Gomes · FIAP · Todos os direitos reservados.*

## Interface web (React + FastAPI)

Além do CLI, este projeto tem uma interface web mínima:

```bash
./rodar.sh          # prepara o ambiente e sobe em http://127.0.0.1:8002
# (Windows: .\rodar.ps1) — passo a passo manual:
#   python3 -m venv .venv && source .venv/bin/activate
#   pip install -r requirements.txt
#   cd frontend && npm install && npm run build
#   python -m uvicorn server:app --port 8002
```

- `server.py` — backend FastAPI: expõe a lógica do exercício em `/api/*` e serve o frontend React (`frontend/dist`).
- `rodar.sh` / `rodar.ps1` — na primeira execução preparam o ambiente (criam o `.venv`, instalam as libs Python, compilam o frontend e criam o `.env` se faltar) e sobem o servidor.
- `frontend/` — app React mínimo (Vite); hot reload com `cd frontend && npm install && npm run dev`.
- 📘 **Manual completo** (portas, notas de ambiente, solução de problemas): veja `../README.md`.
