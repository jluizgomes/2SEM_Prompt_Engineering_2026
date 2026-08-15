# Projetos Locais — LangChain · 2º Semestre 2026

Projetos Python/LangChain **prontos para rodar localmente**, um por aula do
2º semestre da disciplina **Prompt Engineering and Artificial Intelligence**
(FIAP · Ciência da Computação · 2026).

Cada pasta é o "projetinho completo" da aula correspondente: tem `.env`,
`.env.example`, `requirements.txt`, `main.py` e `README.md` próprios.

## Lista de projetos

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

## Padrões comuns a todos

- **Backend:** Ollama Cloud (`https://ollama.com`, modelo `gpt-oss:120b`).
- **Configuração:** variáveis de ambiente lidas do `.env` via `python-dotenv`
  (`OLLAMA_HOST`, `OLLAMA_API_KEY`, `OLLAMA_MODEL` e, nas aulas de RAG, `EMBEDDING_MODEL`).
- **Ollama local (gratuito):** troque no `.env` para `http://localhost:11434`
  e `qwen3.5:0.8b` (instruções em cada `README.md`).
- **Custo zero de API:** a alternativa local usa o Docker do
  [`fiap-ai-lab-complete`](../fiap-ai-lab-complete/README.md).

## Executando um projeto (exemplo)

### macOS / Linux

```bash
cd Aula_01_Revisao_LangChain_LCEL_ChatOllama
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Ou use o script de setup automático:

```bash
cd Aula_01_Revisao_LangChain_LCEL_ChatOllama
chmod +x ../setup.sh && ../setup.sh
```

### Windows (PowerShell)

```powershell
cd Aula_01_Revisao_LangChain_LCEL_ChatOllama
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Ou use o script de setup automático:

```powershell
cd Aula_01_Revisao_LangChain_LCEL_ChatOllama
..\setup.ps1
```

> **Nota:** Se o PowerShell bloquear a execução de scripts, execute:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

A chave `OLLAMA_API_KEY` já está preenchida em cada `.env` (herdada do
`.env` da pasta `2SEM`). O `.env` é ignorado pelo git (ver `.gitignore`).

---

*Copyright © 2026 Prof. Jorge Luiz Gomes · FIAP · Todos os direitos reservados.*
