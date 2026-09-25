# Projetos Locais — LangChain · 2º Semestre 2026 · Gabaritos

Versões resolvidas dos projetos de **Prompt Engineering and Artificial Intelligence** (FIAP, Ciência da Computação, 2º semestre de 2026) para estudo, demonstração e aula.

Cada pasta contém o exercício correspondente, seus testes e os arquivos necessários para executar a aplicação. Os scripts não sobrescrevem um `.env` existente.

## Pré-requisitos

- Python 3.10 ou superior.
- Node.js 20 ou superior e npm.
- PowerShell 5.1 ou superior no Windows.
- Bash no Linux/macOS.
- Ollama local em execução.

Prepare o Ollama local antes de iniciar os exemplos que usam modelo:

```bash
ollama serve
ollama pull gpt-oss:120b
```

Para as aulas de RAG, instale também o modelo de embeddings:

```bash
ollama pull nomic-embed-text
```

Os 15 arquivos `.env.example` usam o padrão local:

```dotenv
OLLAMA_HOST=http://localhost:11434
OLLAMA_API_KEY=ollama
OLLAMA_MODEL=gpt-oss:120b
```

`OLLAMA_API_KEY=ollama` é o valor convencional do Ollama local, não uma credencial secreta. As variáveis específicas de cada aula, como `EMBEDDING_MODEL` e as variáveis da Aula 10 para MCP, permanecem no respectivo exemplo.

A Aula 10 funciona localmente sem servidor MCP. Para habilitar tools MCP, configure `MCP_ENABLED=true` e `MCP_SERVER_URL` no `.env` da aula.

## Execução no Windows

O `setup.ps1` e o `rodar.ps1` resolvem o próprio diretório, portanto podem ser chamados por caminho absoluto. A seleção pela raiz mostra os 15 projetos e executa o `setup.ps1` do projeto escolhido:

```powershell
Set-Location <caminho>\projetos_gabaritos
.\setup.ps1
.\setup.ps1 -Projeto Aula_05_Embeddings_Busca_Semantica_ChromaDB
```

Para um projeto específico:

```powershell
Set-Location <caminho>\projetos_gabaritos\Aula_05_Embeddings_Busca_Semantica_ChromaDB
.\setup.ps1
.\rodar.ps1
```

O `rodar.ps1` valida Python, Node.js e npm, instala as dependências, executa o build e inicia o Uvicorn. Também pode ser aberto com a opção de execução única do Windows; para observar mensagens e erros, use uma janela do PowerShell.

Se a política de execução bloquear o script, autorize o usuário atual:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Execução no Linux/macOS

O `rodar.sh` cria o ambiente quando necessário, instala as dependências, compila o frontend e inicia o servidor:

```bash
cd /caminho/projetos_gabaritos/Aula_05_Embeddings_Busca_Semantica_ChromaDB
./rodar.sh
```

Uma porta diferente pode ser informada como argumento:

```bash
./rodar.sh 9000
```

## Aulas 08 e 11

As Aulas 08 e 11 usam Gradio/Streamlit e não possuem frontend React nem `rodar.sh` de servidor FastAPI.

### Linux/macOS

```bash
cd Aula_08_Interfaces_Gradio_Streamlit_Deploy
./setup.sh
./.venv/bin/python main.py
```

Para a variante Streamlit da Aula 08:

```bash
./.venv/bin/streamlit run app_streamlit.py
```

A Aula 11 usa Gradio:

```bash
cd Aula_11_Integradora_Agente_RAG_Gradio
./setup.sh
./.venv/bin/python main.py
```

### Windows

```powershell
Set-Location <caminho>\projetos_gabaritos\Aula_08_Interfaces_Gradio_Streamlit_Deploy
.\setup.ps1
.\.venv\Scripts\python.exe main.py
```

Para a variante Streamlit:

```powershell
.\.venv\Scripts\streamlit.exe run app_streamlit.py
```

A Aula 11:

```powershell
Set-Location <caminho>\projetos_gabaritos\Aula_11_Integradora_Agente_RAG_Gradio
.\setup.ps1
.\.venv\Scripts\python.exe main.py
```

As interfaces Gradio usam a porta 7860 por padrão; a interface Streamlit usa a porta 8501 por padrão.

## Portas das interfaces React + FastAPI

Os scripts e os proxies Vite usam estas portas da aula:

| Projeto | URL |
|---|---|
| `Aula_01_Revisao_LangChain_LCEL_ChatOllama` | http://127.0.0.1:8101 |
| `Aula_02_Memoria_Conversacional` | http://127.0.0.1:8102 |
| `Aula_03_Structured_Output_Pydantic_v2` | http://127.0.0.1:8103 |
| `Aula_04_Context_Engineering` | http://127.0.0.1:8104 |
| `Aula_05_Embeddings_Busca_Semantica_ChromaDB` | http://127.0.0.1:8105 |
| `Aula_06_Pipeline_RAG_Completo` | http://127.0.0.1:8106 |
| `Aula_07_RAG_Avancado_Chunking_RAGAS` | http://127.0.0.1:8107 |
| `Aula_09_Agentes_ReAct_Tools_FunctionCalling` | http://127.0.0.1:8109 |
| `Aula_10_ContextEngineering_Agentes_MCP` | http://127.0.0.1:8110 |
| `Aula_12_RouterChain_GrafoEstado` | http://127.0.0.1:8112 |
| `Aula_13_LangGraph_StateGraph_HITL` | http://127.0.0.1:8113 |
| `Aula_14_SpecDrivenDevelopment_Encerramento` | http://127.0.0.1:8114 |
| `Bonus_MultiChains_MultiModelos` | http://127.0.0.1:8199 |

O Vite usa 5173 em desenvolvimento e 4173 em preview. Para apontar o proxy para outra porta local, use `API_PORT`:

```bash
cd frontend
API_PORT=8105 npm run dev
API_PORT=8105 npm run preview
```

No Windows PowerShell:

```powershell
cd frontend
$env:API_PORT = "8105"
npm run dev
```

## Testes

Execute os testes dentro da pasta do projeto, depois de configurar o ambiente:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

No Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

A Aula 01 também possui testes do cliente JavaScript do streaming:

```bash
node --test tests/test_api.mjs
```

Para uma verificação rápida de sintaxe Python:

```bash
.venv/bin/python -m compileall -q main.py server.py tests
```

## Lista de projetos

| Pasta | Conteúdo |
|---|---|
| `Aula_01_Revisao_LangChain_LCEL_ChatOllama` | Chain LCEL com ChatOllama e streaming |
| `Aula_02_Memoria_Conversacional` | Buffer, Summary e TokenBuffer |
| `Aula_03_Structured_Output_Pydantic_v2` | Saída estruturada com Pydantic v2 |
| `Aula_04_Context_Engineering` | Tokens, histórico e orçamento de contexto |
| `Aula_05_Embeddings_Busca_Semantica_ChromaDB` | Embeddings e busca semântica com ChromaDB |
| `Aula_06_Pipeline_RAG_Completo` | Pipeline RAG de ponta a ponta |
| `Aula_07_RAG_Avancado_Chunking_RAGAS` | Chunking, reranking e RAGAS |
| `Aula_08_Interfaces_Gradio_Streamlit_Deploy` | Interfaces Gradio e Streamlit |
| `Aula_09_Agentes_ReAct_Tools_FunctionCalling` | Agente ReAct com tools |
| `Aula_10_ContextEngineering_Agentes_MCP` | Contexto, tools e MCP |
| `Aula_11_Integradora_Agente_RAG_Gradio` | Agente com RAG e Gradio |
| `Aula_12_RouterChain_GrafoEstado` | Router e grafo de estado |
| `Aula_13_LangGraph_StateGraph_HITL` | StateGraph, checkpoint e HITL |
| `Aula_14_SpecDrivenDevelopment_Encerramento` | Spec-driven development |
| `Bonus_MultiChains_MultiModelos` | RunnableParallel e múltiplos modelos |

## Solução de problemas

- **Porta ocupada:** execute o script com outra porta, por exemplo `./rodar.sh 9000` ou `.\rodar.ps1 9000`.
- **Modelo não encontrado:** baixe `gpt-oss:120b` com `ollama pull`; para RAG, baixe também `nomic-embed-text`.
- **Ollama indisponível:** confirme `ollama serve` e `http://localhost:11434`.
- **Node/npm ausente:** instale Node.js 20 ou superior e repita o script.
- **MCP indisponível:** mantenha `MCP_ENABLED=false` para usar o fluxo local ou informe um servidor MCP acessível.

---

*Copyright © 2026 Prof. Jorge Luiz Gomes · FIAP · Todos os direitos reservados.*
