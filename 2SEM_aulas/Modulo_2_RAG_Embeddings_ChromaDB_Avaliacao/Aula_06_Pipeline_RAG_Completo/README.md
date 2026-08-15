# Aula 06 — Pipeline RAG Completo

**Disciplina:** Prompt Engineering and Artificial Intelligence — FIAP · 2º Semestre 2026
**Professor:** Jorge Luiz Gomes

RAG de ponta a ponta: carrega PDF (PyMuPDF), divide em chunks, indexa e responde citando o contexto.

---

## Requisitos

- Python 3.10+
- Chave da Ollama Cloud (`OLLAMA_API_KEY`)

## Como rodar

```bash
cd Aula_06_Pipeline_RAG_Completo
python -m venv .venv && source .venv/bin/activate   # recomendado (macOS/Linux)
pip install -r requirements.txt
cp .env.example .env                                 # se ainda não tiver .env
# edite .env e preencha OLLAMA_API_KEY (a mesma chave já está no .env da pasta 2SEM)
python main.py
```


Opcional: coloque um PDF em ./data/ para indexar. Sem PDF, usa texto de exemplo embutido.

## Arquivos

- `main.py` — código principal da aula
- `requirements.txt` — dependências do projeto
- `.env` — variáveis de ambiente (chave da API; NÃO versionar)
- `.env.example` — modelo do `.env`
- `.gitignore` — ignora `.env`, `chroma_db/`, `data/`, venv, etc.

## Usar Ollama LOCAL (gratuito, FIAP AI Lab)

Por padrão o projeto usa o Ollama Cloud (`https://ollama.com`). Para usar o
Ollama local do Docker (modelo `qwen3.5:0.8b`, sem custo):

1. No `.env`, comente as linhas `OLLAMA_HOST`/`OLLAMA_API_KEY` atuais e descomente as alternativas;
2. Ajuste `OLLAMA_MODEL` para `qwen3.5:0.8b`;
3. Suba o lab: `cd ../../fiap-ai-lab-complete && make up` (ou `make up-minimum`).

---

*Copyright © 2026 Prof. Jorge Luiz Gomes · FIAP · Todos os direitos reservados.*
