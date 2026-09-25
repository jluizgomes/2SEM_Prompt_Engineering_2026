# Aula 10 — Context Engineering e Agentes MCP

**Disciplina:** Prompt Engineering and Artificial Intelligence — FIAP · 2º Semestre 2026
**Professor:** Jorge Luiz Gomes

Controle de contexto com trim_messages e conexão de tools externas via MCP.

---

## Requisitos

- Python 3.10+
- O fluxo local desta demonstração não exige Ollama; a chave só é necessária se você adicionar uma chamada de modelo.

## Como rodar

```bash
cd Aula_10_ContextEngineering_Agentes_MCP
python -m venv .venv && source .venv/bin/activate   # recomendado (macOS/Linux)
pip install -r requirements.txt
cp .env.example .env                                 # se ainda não tiver .env
python main.py
```


Por padrão, `MCP_ENABLED=false`: o fluxo de `trim_messages` e a tool local continuam funcionando sem servidor externo.

Para MCP remoto, habilite e configure:

```bash
MCP_ENABLED=true
MCP_TRANSPORT=streamable_http
MCP_SERVER_URL=http://localhost:8000/mcp
MCP_TIMEOUT=10
```

`MCP_TRANSPORT=http` é aceito como alias de `streamable_http`; `sse` também é suportado. Para servidor local por stdio, use `MCP_TRANSPORT=stdio` e `MCP_SERVER_COMMAND="python servidor_mcp.py"`. A conexão só é aberta quando a ação de carregar tools é executada. Falhas de conexão são exibidas sem interromper o fluxo local.

## Arquivos

- `main.py` — código principal da aula
- `contexto.py` — roles, trim, configuração e carga lazy de tools MCP
- `tests/test_contexto.py` — testes focados com doubles, sem servidor externo
- `requirements.txt` — dependências do projeto
- `.env` — configuração local; não versionar
- `.env.example` — modelo do `.env`
- `.gitignore` — ignora `.env`, `chroma_db/`, `data/`, venv, etc.

## Ollama local

O `.env.example` aponta para `http://localhost:11434` e define `OLLAMA_API_KEY=ollama`.

1. Inicie o serviço com `ollama serve`.
2. Baixe o modelo com `ollama pull gpt-oss:120b`.
3. Mantenha `MCP_ENABLED=false` quando não houver servidor MCP.

---

*Copyright © 2026 Prof. Jorge Luiz Gomes · FIAP · Todos os direitos reservados.*

## Interface web (React + FastAPI)

Além do CLI, este projeto tem uma interface web mínima:

```bash
./rodar.sh          # prepara o ambiente e sobe em http://127.0.0.1:8110
# (Windows: .\rodar.ps1) — passo a passo manual:
#   python3 -m venv .venv && source .venv/bin/activate
#   pip install -r requirements.txt
#   cd frontend && npm install && npm run build
#   python -m uvicorn server:app --port 8110
```

- `server.py` — backend FastAPI: expõe a lógica do exercício em `/api/*` e serve o frontend React (`frontend/dist`).
- `rodar.sh` / `rodar.ps1` — na primeira execução preparam o ambiente (criam o `.venv`, instalam as libs Python, compilam o frontend e criam o `.env` se faltar) e sobem o servidor.
- `frontend/` — app React mínimo (Vite); hot reload com `cd frontend && npm install && npm run dev`.
- 📘 **Manual completo** (portas, notas de ambiente, solução de problemas): veja `../README.md`.
