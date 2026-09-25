# Projetos Locais — LangChain · 2º Semestre 2026

Projetos Python/LangChain **prontos para rodar localmente**, um por aula do
2º semestre da disciplina **Prompt Engineering and Artificial Intelligence**
(FIAP · Ciência da Computação · 2026).

Cada pasta é o "projetinho completo" da aula correspondente e **é
autossuficiente**: pode ser copiada/baixada sozinha e roda sem depender de
nada fora dela. Cada pasta contém:

| Arquivo | Papel |
|---|---|
| `main.py` | o exercício da aula (código-fonte com TODOs para completar) |
| `server.py` | backend FastAPI: expõe o exercício via API e serve o frontend |
| `frontend/` | interface web em React (já compilada em `frontend/dist`) |
| `rodar.sh` / `rodar.ps1` | **roda a interface web desta pasta** (1 comando) |
| `requirements.txt` | dependências Python (inclui `fastapi`, `uvicorn`, `tiktoken`, `ddgs`) |
| `.env` / `.env.example` | chaves e configuração do Ollama (`.env` não é versionado) |

---

## 🚀 Manual rápido (o que você vai usar em aula)

### 1. Rodar uma aula (Linux/macOS)

```bash
cd projetos_aluno/Aula_05_Embeddings_Busca_Semantica_ChromaDB
./rodar.sh
```

- **1ª execução:** cria o `.venv`, instala as libs Python, compila o frontend
  (se faltar) e cria o `.env` a partir do `.env.example` — automático;
- Depois abre a interface em **http://127.0.0.1:8005** (porta da pasta);
- **Ctrl+C** encerra o servidor;
- Porta personalizada: `./rodar.sh 9000`.

### 2. Windows (PowerShell)

```powershell
cd projetos_aluno\Aula_05_Embeddings_Busca_Semantica_ChromaDB
.\rodar.ps1
```

> Se o PowerShell bloquear scripts: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 3. Portas padrão de cada aula (projetos_aluno)

| Pasta | Porta |
|---|---|
| `Aula_01_Revisao_LangChain_LCEL_ChatOllama` | http://127.0.0.1:8001 |
| `Aula_02_Memoria_Conversacional` | http://127.0.0.1:8002 |
| `Aula_03_Structured_Output_Pydantic_v2` | http://127.0.0.1:8003 |
| `Aula_04_Context_Engineering` | http://127.0.0.1:8004 |
| `Aula_05_Embeddings_Busca_Semantica_ChromaDB` | http://127.0.0.1:8005 |
| `Aula_06_Pipeline_RAG_Completo` | http://127.0.0.1:8006 |
| `Aula_07_RAG_Avancado_Chunking_RAGAS` | http://127.0.0.1:8007 |
| `Aula_08_Interfaces_Gradio_Streamlit_Deploy` | *(usa Gradio/Streamlit — sem interface React)* |
| `Aula_09_Agentes_ReAct_Tools_FunctionCalling` | http://127.0.0.1:8009 |
| `Aula_10_ContextEngineering_Agentes_MCP` | http://127.0.0.1:8010 |
| `Aula_11_Integradora_Agente_RAG_Gradio` | *(usa Gradio — sem interface React)* |
| `Aula_12_RouterChain_GrafoEstado` | http://127.0.0.1:8012 |
| `Aula_13_LangGraph_StateGraph_HITL` | http://127.0.0.1:8013 |
| `Aula_14_SpecDrivenDevelopment_Encerramento` | http://127.0.0.1:8014 |
| `Bonus_MultiChains_MultiModelos` | http://127.0.0.1:8099 |

---

## 🖥️ O que a interface web faz

Cada aula tem uma interface mínima em **React + FastAPI** que conversa com o
`main.py` por HTTP. Ela se adapta ao exercício:

- **Chat** (Aula 01, 02, 06, 09) — converse com a chain/modelo;
- **Ações** (Aula 03, 04, 05, 07, 10, 12, 14, Bonus) — botões e formulários
  para cada demonstração da aula (schema, tokens, busca semântica, router…);
- **Human-in-the-Loop** (Aula 13) — o grafo pausa e a interface mostra o botão
  **"Aprovar e continuar"** antes da resposta final.

### Comportamento nos exercícios (projetos_aluno)

- Os exercícios vêm **incompletos (TODOs)** para você resolver — a interface
  mostra um **banner amarelo** com a lista de funções pendentes no `main.py`;
- As partes já prontas do esqueleto funcionam na interface enquanto você
  completa o resto. Complete o código, **reinicie o servidor** (`Ctrl+C` e
  `./rodar.sh` de novo) e o banner some.

### Avisos de ambiente

A própria interface avisa quando algo depende de configuração do ambiente
(por exemplo: acesso ao modelo de embeddings, endpoint MCP, ou versão do
LangChain) — leia os banners azuis/vermelhos antes de marcar um erro como bug.

---

## 🐍 Alternativa: rodar pelo terminal (CLI)

```bash
cd Aula_01_Revisao_LangChain_LCEL_ChatOllama
python3 -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

---

## ⚙️ Configuração comum

- **Chat:** Ollama Cloud com `OLLAMA_HOST=https://ollama.com`,
  `OLLAMA_API_KEY` e `OLLAMA_MODEL=gpt-oss:120b`;
- **Embeddings:** Ollama local com
  `EMBEDDING_OLLAMA_HOST=http://localhost:11434` e
  `EMBEDDING_MODEL=nomic-embed-text`;
- Suba o [`fiap-ai-lab-complete`](../fiap-ai-lab-complete/README.md) para usar
  os embeddings locais;
- O `.env` é ignorado pelo Git (ver `.gitignore`).

---

## 📌 Notas importantes de ambiente (leia antes da aula)

1. **Embeddings (Aulas 05, 06, 07, 11 e 12):** o projeto usa o Ollama local
   em `EMBEDDING_OLLAMA_HOST`. Antes de indexar, suba o FIAP AI Lab e
   garanta que `nomic-embed-text` esteja disponível. A `OLLAMA_API_KEY` é usada
   somente pelo chat no Ollama Cloud.

2. **Versão do LangChain (Aulas 07 e 09):** o código do curso usa APIs que no
   **LangChain 1.x** mudaram de lugar:
   - `Aula_09` tem **fallback automático** na interface (langgraph-prebuilt) —
     funciona em qualquer versão;
   - `Aula_07` (RAG avançado: `langchain.retrievers`, `langchain.storage`) só
     demonstra com **LangChain 0.3.x** ou no ambiente FIAP AI Lab. A interface
     avisa o erro e a dica no banner.

3. **Busca na web (Aulas 09, 10, 13):** `duckduckgo-search` 8+ exige o pacote
   `ddgs` — já incluído no `requirements.txt` dessas aulas.

4. **MCP (Aula 10):** a ação "Carregar tools MCP" precisa de um servidor MCP
   rodando (defina `MCP_SERVER_URL` no `.env`). Sem servidor, a interface
   explica como ativar.

---

## 🔧 Solução de problemas

| Problema | Solução |
|---|---|
| Porta já em uso | `./rodar.sh 9000` (ou `.\rodar.ps1 9000`) |
| Banner amarelo "TODOs pendentes" | Complete as funções listadas no `main.py` e reinicie o servidor |
| Erro ao indexar/RAG | Verifique `EMBEDDING_OLLAMA_HOST`, o serviço local e o modelo `nomic-embed-text` |
| Frontend "não compilado" | `cd frontend && npm install && npm run build` (ou rode `./rodar.sh` que compila sozinho) |
| PowerShell bloqueando scripts | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |

---

## Lista completa de projetos

| Pasta | Conteúdo |
|---|---|
| `Aula_01_Revisao_LangChain_LCEL_ChatOllama` | Chain LCEL: `prompt \| modelo \| parser`, streaming |
| `Aula_02_Memoria_Conversacional` | Buffer / Summary / TokenBuffer + ConversationChain |
| `Aula_03_Structured_Output_Pydantic_v2` | Saída estruturada com Pydantic v2 |
| `Aula_04_Context_Engineering` | Contagem de tokens (tiktoken) e montagem de prompt |
| `Aula_05_Embeddings_Busca_Semantica_ChromaDB` | Embeddings + ChromaDB + busca semântica |
| `Aula_06_Pipeline_RAG_Completo` | RAG de ponta a ponta (PDF → chunks → resposta) |
| `Aula_07_RAG_Avancado_Chunking_RAGAS` | Chunking semântico, reranking e RAGAS |
| `Aula_08_Interfaces_Gradio_Streamlit_Deploy` | Chat com Gradio e Streamlit |
| `Aula_09_Agentes_ReAct_Tools_FunctionCalling` | Agente ReAct com tools |
| `Aula_10_ContextEngineering_Agentes_MCP` | trim_messages + tools via MCP |
| `Aula_11_Integradora_Agente_RAG_Gradio` | Agente com RAG como tool + Gradio |
| `Aula_12_RouterChain_GrafoEstado` | Router por intenção + grafo de estado |
| `Aula_13_LangGraph_StateGraph_HITL` | StateGraph + checkpoint + HITL |
| `Aula_14_SpecDrivenDevelopment_Encerramento` | Spec-driven development |
| `Bonus_MultiChains_MultiModelos` | RunnableParallel + multi-modelos |

---

*Copyright © 2026 Prof. Jorge Luiz Gomes · FIAP · Todos os direitos reservados.*