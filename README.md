# 2SEM — Prompt Engineering and Artificial Intelligence (2026)

Repositório unificado da disciplina **Prompt Engineering and Artificial Intelligence**
do curso de **Ciência da Computação** da **FIAP** — 2º Semestre 2026.

Contém os notebooks das aulas, projetos LangChain (professor e aluno),
infraestrutura Docker para laboratório local e ebooks de referência.

---

## Índice

1. [Visão geral do repositório](#1-visão-geral-do-repositório)
2. [Estrutura de pastas](#2-estrutura-de-pastas)
3. [Plano do semestre](#3-plano-do-semestre)
4. [Notebooks das aulas](#4-notebooks-das-aulas)
5. [Projetos LangChain — Professor vs Aluno](#5-projetos-langchain--professor-vs-aluno)
6. [Infraestrutura Docker](#6-infraestrutura-docker)
7. [Arquivos ignorados](#7-arquivos-ignorados-mantidos-apenas-localmente)
8. [Ebooks de referência](#8-ebooks-de-referência)
9. [Como usar — rápido](#9-como-usar--rápido)
10. [Stack tecnológico aprovado](#10-stack-tecnológico-aprovado)
11. [Modelos proibidos](#11-modelos-proibidos)
12. [Referências acadêmicas](#12-referências-acadêmicas)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Visão geral do repositório

| Componente | Descrição | Público |
|---|---|---|
| `2SEM_notebooks_aulas/` | 31 notebooks Jupyter (14 aulas + 1 bônus) | Professor e aluno |
| `projetos_langchain_local/` | 15 projetos Python completos | Professor (referência) |
| `projetos_langchain_local_aluno/` | 15 projetos Python com esqueletos `# TODO` | Alunos |
| `Ebooks/` | 15 livros em PDF de referência | Professor e aluno |
| `fiap-ai-lab-complete/` | Stack Docker completa (12+ containers) | Professor e aluno |
| `fiap-openwebui-ollama-setup/` | Setup Docker leve (Ollama + Open WebUI) | Aluno |

---

## 2. Estrutura de pastas

```
2SEM_Prompt_Engineering_2026/
├── 2SEM_notebooks_aulas/                    # Notebooks Jupyter das aulas
│   ├── 2Sem_Aula_01_Demo.ipynb              # Demo do professor
│   ├── 2Sem_Aula_01_Aluno.ipynb             # Atividade do aluno
│   ├── 2Sem_Aula_02_Demo.ipynb
│   ├── 2Sem_Aula_02_Demo_Local.ipynb        # Versão local (Ollama)
│   ├── 2Sem_Aula_02_Aluno.ipynb
│   ├── 2Sem_Aula_02_Aluno_Local.ipynb
│   ├── ...
│   ├── 2Sem_Aula_14_Demo.ipynb
│   ├── 2Sem_Aula_14_Aluno.ipynb
│   └── 2Sem_Bonus_MultiChains_MultiModelos.ipynb
│
├── projetos_langchain_local/                # Projetos completos (referência do professor)
│   ├── Aula_01_Revisao_LangChain_LCEL_ChatOllama/
│   ├── Aula_02_Memoria_Conversacional/
│   ├── Aula_03_Structured_Output_Pydantic_v2/
│   ├── Aula_04_Context_Engineering/
│   ├── Aula_05_Embeddings_Busca_Semantica_ChromaDB/
│   ├── Aula_06_Pipeline_RAG_Completo/
│   ├── Aula_07_RAG_Avancado_Chunking_RAGAS/
│   ├── Aula_08_Interfaces_Gradio_Streamlit_Deploy/
│   ├── Aula_09_Agentes_ReAct_Tools_FunctionCalling/
│   ├── Aula_10_ContextEngineering_Agentes_MCP/
│   ├── Aula_11_Integradora_Agente_RAG_Gradio/
│   ├── Aula_12_RouterChain_GrafoEstado/
│   ├── Aula_13_LangGraph_StateGraph_HITL/
│   ├── Aula_14_SpecDrivenDevelopment_Encerramento/
│   └── Bonus_MultiChains_MultiModelos/
│
├── projetos_langchain_local_aluno/          # Esqueletos com TODO para os alunos
│   ├── (mesmas 15 pastas, cada main.py com # TODO)
│   ├── setup.sh                            # Setup automático macOS/Linux
│   └── setup.ps1                           # Setup automático Windows
│
├── fiap-ai-lab-complete/                   # Laboratório Docker completo
│   ├── docker-compose.yml
│   ├── Makefile
│   ├── .env / .env.example
│   ├── ollama/
│   ├── postgres/
│   ├── chromadb/
│   ├── pipelines/
│   ├── searxng/
│   └── mem0/
│
├── fiap-openwebui-ollama-setup/            # Setup Docker leve
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── .env.example
│
├── Ebooks/                                 # Livros de referência (PDF)
│   ├── AI Agents in Action.pdf
│   ├── Agentic Coding with Claude Code.pdf
│   ├── Learning LangChain.pdf
│   ├── Prompt Engineering.pdf
│   ├── RAG with Python Cookbook.pdf
│   └── ... (15 ebooks no total)
│
├── Apostila_LangChain_Basico_Intermediario_LangGraph.html  # Apostila (ignorada pelo git)
├── Plano_2Sem_ComBase_2026.html                             # Plano do semestre (ignorado pelo git)
│
└── .gitignore
```

---

## 3. Plano do semestre

| # | Título | Data | Módulo | CKP |
|---|---|---|---|---|
| 01 | Role prompting, system prompts, parâmetros e reasoning LLMs | 04/Ago | M1 | — |
| 02 | Segurança em LLMs: prompt injection, jailbreak e guardrails | 11/Ago | M1 | — |
| 03 | Ética, viés algorítmico, LGPD e responsabilidade no uso de IA | 18/Ago | M1 | — |
| 04 | Context Engineering, frameworks reutilizáveis e structured output | 25/Ago | M1 | CKP01 |
| 05 | LangChain: LCEL, ChatOllama, chains, templates e memory | 01/Set | M2 | — |
| 06 | Chatbots e assistentes virtuais com gerenciamento de contexto | 08/Set | M2 | — |
| 07 | Embeddings + RAG com ChromaDB e nomic-embed-text via Ollama | 15/Set | M2 | — |
| 08 | RAG avançado: chunking, reranking, RAGAS e synthetic RAG | 22/Set | M2 | CKP02 |
| 09 | Interfaces com Gradio/Streamlit + deploy no Colab com URL pública | 29/Set | M3 | — |
| 10 | Agentes de IA: ReAct, tools e function calling | 06/Out | M3 | — |
| 11 | Context Engineering para agentes: curadoria em loop agêntico | 13/Out | M3 | — |
| 12 | Agente com RAG como tool + interface Gradio ao vivo | 20/Out | M3 | CKP03 |
| 13 | LangGraph, Deep Agents e multiagentes supervisor/worker | 27/Out | M4 | — |
| 14 | Tendências 2026 e o futuro de Prompt & Context Engineering | 03/Nov | M4 | — |

**Módulos:**
- **M1** (Aulas 01–04): Fundamentos de Prompt Engineering
- **M2** (Aulas 05–08): LangChain, RAG e Embeddings
- **M3** (Aulas 09–12): Interfaces, Agentes e Integração
- **M4** (Aulas 13–14): Avançado e Tendências

**Checkpoints (CKP):**
- CKP01 — Obrigatório (Aula 04, 25/Ago)
- CKP02 — Obrigatório (Aula 08, 22/Set)
- CKP03 — Opcional (Aula 12, 20/Out)

---

## 4. Notebooks das aulas

A pasta `2SEM_notebooks_aulas/` contém **31 notebooks** no formato:

| Tipo | Sufixo | Descrição |
|---|---|---|
| Demo | `_Demo.ipynb` | Código demonstrativo do professor durante a aula |
| Aluno | `_Aluno.ipynb` | Atividade prática para o aluno completar |

> Aula 02 possui versões adicionais `_Demo_Local.ipynb` e `_Aluno_Local.ipynb`
> para uso com Ollama local ao invés de API cloud.

### Como usar no Google Colab

1. Acesse [colab.research.google.com](https://colab.research.google.com)
2. File → Upload notebook → selecione o arquivo `.ipynb`
3. Execute as células na ordem

---

## 5. Projetos LangChain — Professor vs Aluno

### `projetos_langchain_local/` (Professor)

Contém os **projetos completos** como referência. Cada pasta tem:

```
Aula_XX_Nome/
├── main.py              # Código completo e funcional
├── requirements.txt     # Dependências Python
├── .env                 # Variáveis de ambiente (chave já preenchida)
├── .env.example         # Template das variáveis
├── .gitignore
└── README.md            # Instruções específicas da aula
```

### `projetos_langchain_local_aluno/` (Aluno)

Contém **esqueletos** com `# TODO` para os alunos completarem:

```python
# TODO: Crie a chain LCEL usando o pipe | combine_prompt
# TODO: Adicione streaming com .stream()
# TODO: Implemente a função para enviar mensagem ao chat
```

Cada arquivo `main.py` mantém toda a infraestrutura (imports, config, LLM setup)
e pede ao aluno para implementar apenas a lógica principal.

### Lista de projetos

| # | Pasta | Tema |
|---|---|---|
| 01 | `Aula_01_Revisao_LangChain_LCEL_ChatOllama` | Chain LCEL: `prompt \| modelo \| parser`, streaming |
| 02 | `Aula_02_Memoria_Conversacional` | Buffer / Summary / TokenBuffer + ConversationChain |
| 03 | `Aula_03_Structured_Output_Pydantic_v2` | Saída estruturada com Pydantic v2 |
| 04 | `Aula_04_Context_Engineering` | Contagem de tokens (tiktoken) e montagem de prompt |
| 05 | `Aula_05_Embeddings_Busca_Semantica_ChromaDB` | Embeddings + ChromaDB + busca semântica |
| 06 | `Aula_06_Pipeline_RAG_Completo` | RAG de ponta a ponta (PDF → chunks → resposta) |
| 07 | `Aula_07_RAG_Avancado_Chunking_RAGAS` | Chunking semântico, reranking e RAGAS |
| 08 | `Aula_08_Interfaces_Gradio_Streamlit_Deploy` | Chat com Gradio e Streamlit |
| 09 | `Aula_09_Agentes_ReAct_Tools_FunctionCalling` | Agente ReAct com tools |
| 10 | `Aula_10_ContextEngineering_Agentes_MCP` | trim_messages + tools via MCP |
| 11 | `Aula_11_Integradora_Agente_RAG_Gradio` | Agente com RAG como tool + Gradio |
| 12 | `Aula_12_RouterChain_GrafoEstado` | Router por intenção + grafo de estado |
| 13 | `Aula_13_LangGraph_StateGraph_HITL` | StateGraph + checkpoint + HITL |
| 14 | `Aula_14_SpecDrivenDevelopment_Encerramento` | Spec-driven development |
| B | `Bonus_MultiChains_MultiModelos` | RunnableParallel + multi-modelos |

---

## 6. Infraestrutura Docker

### 6.1 Setup leve — `fiap-openwebui-ollama-setup/`

Recomendado para máquinas com pouca memória ou para uso rápido.

| Serviço | Container | Porta | Descrição |
|---|---|---|---|
| Ollama | `fiap-ollama` | `11434` | Servidor de modelos (CPU) |
| Open WebUI | `fiap-open-webui` | `3000` | Interface de chat |

**Modelos padrão:** `qwen3.5:0.8b` (chat) + `qwen3-embedding:0.6b` (embeddings)

```bash
cd fiap-openwebui-ollama-setup
cp .env.example .env
docker compose up -d --build
# Acesse http://localhost:3000
```

### 6.2 Stack completa — `fiap-ai-lab-complete/`

Laboratório completo com 12+ containers para todas as aulas.

| Serviço | Container | Porta | Uso nas aulas |
|---|---|---|---|
| Postgres (pgvector) | `fiap-postgres` | `5432` | Banco de dados unificado |
| Ollama | `fiap-ollama` | `11434` | LLM + embeddings |
| Open WebUI | `fiap-open-webui` | `3000` | Interface de chat |
| ChromaDB | `fiap-chromadb` | `8000` | Vector store (Aulas 05–12) |
| SearXNG | `fiap-searxng` | `8080` | Metabuscador web |
| mem0 | `fiap-mem0` | `8100` | Memória de longo prazo |
| Firecrawl | `fiap-firecrawl-api` | `3002` | Scrape/crawl web |
| Langfuse | `fiap-langfuse-web` | `3001` | Observabilidade (perfil separado) |

**Perfis disponíveis:**

| Perfil | Containers | Quando usar |
|---|---|---|
| `minimum` | postgres, ollama, open-webui | Máquina fraca, Aulas 01–04 |
| `complete` | todos (12 containers) | Aula normal, todas as integrações |
| `rag` | base + pipelines + chromadb | Aulas de RAG (07, 08) |
| `search` | base + searxng + valkey | Aulas de busca web |
| `memory` | base + mem0 | Aula de memória (11) |

```bash
cd fiap-ai-lab-complete
cp .env.example .env
# Para uso completo:
make up-profile-complete
# Ou apenas o básico:
make up-profile-minimum
```

---

## 7. Arquivos ignorados (mantidos apenas localmente)

Alguns arquivos grandes ou específicos do professor são mantidos apenas localmente
e **não são commitados** no repositório:

| Arquivo | Descrição |
|---|---|
| `Apostila_LangChain_Basico_Intermediario_LangGraph.html` | Apostila completa de LangChain (básico → intermediário) com foco em LangGraph |
| `Plano_2Sem_ComBase_2026.html` | Plano detalhado do 2º semestre 2026 (HTML interativo) |

> Esses arquivos estão listados no `.gitignore`. Para acessá-los, peça ao professor.

---

## 8. Ebooks de referência

A pasta `Ebooks/` contém **15 livros** em PDF para consulta:

| Título | Autor |
|---|---|
| AI Agents in Action | Micheal Lanham |
| Agentic Artificial Intelligence | Pascal Bornet et al. |
| Agentic Coding with Claude Code | Eden Marco |
| Agentic Design Patterns | Antonio Gullí |
| Architecting AI Software Systems | Richard D. Avila |
| Domain-Specific Small Language Models | Guglielmo Iozzia |
| Effective Conversational AI | Andrew Freed et al. |
| Essential GraphRAG | Tomaž Bratanic, Oskar Hane |
| Learning LangChain | Mayo Oshin, Nuno |
| Prompt Engineering | (hands-on guide) |
| Python Illustrated | Maaike van Putten |
| RAG with Python Cookbook | Dominik Polzer |
| AI-Native LLM Security | Vaibhav Malik et al. |
| A Practical Guide to RLHF | Sandip Kulkarni |
| ChatGPT Business Goldmines | Dr. Ope Banwo |

---

## 9. Como usar — rápido

### Opção 1: Notebooks (Google Colab)

1. Abra o notebook `_Demo.ipynb` da aula desejada no Colab
2. Execute as células para acompanhar a demonstração
3. Abra o notebook `_Aluno.ipynb` para a atividade prática

### Opção 2: Projeto local (com Docker)

1. Suba o Ollama local:
   ```bash
   cd fiap-openwebui-ollama-setup
   cp .env.example .env
   docker compose up -d --build
   ```

2. Acesse o projeto da aula (aluno):
   ```bash
   cd projetos_langchain_local_aluno/Aula_01_Revisao_LangChain_LCEL_ChatOllama
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Configure o `.env` para apontar ao Ollama local:
   ```
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=qwen3.5:0.8b
   ```

4. Implemente os `# TODO` no `main.py` e execute:
   ```bash
   python main.py
   ```

### Opção 3: Projeto local (com Ollama Cloud)

1. Acesse o projeto e configure o `.env` com sua chave da Ollama Cloud
2. Instale dependências e execute:
   ```bash
   cd projetos_langchain_local_aluno/Aula_01_Revisao_LangChain_LCEL_ChatOllama
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   python main.py
   ```

### Setup automático

```bash
# macOS/Linux
cd projetos_langchain_local_aluno/Aula_01_Revisao_LangChain_LCEL_ChatOllama
chmod +x ../setup.sh && ../setup.sh

# Windows PowerShell
cd projetos_langchain_local_aluno/Aula_01_Revisao_LangChain_LCEL_ChatOllama
..\setup.ps1
```

---

## 10. Stack tecnológico aprovado

### Modelos (via Ollama Cloud API)

```
qwen3.6:27b     → principal, maioria das demos
qwen3:8b        → alternativa leve
llama4:scout    → multimodal
gemma4:9b       → alternativa Google
deepseek-r2     → reasoning mode e CoT
devstral-small  → agentes de código
mistral-small   → alternativa europeia
phi4:14b        → alternativa Microsoft
nomic-embed-text → ÚNICO modelo de embeddings aprovado
```

### Frameworks Python

```
LangChain 0.3+  → LCEL, ChatOllama, chains, memory, agents, tools
LangGraph       → StateGraph, nodes, edges, MemorySaver
ChromaDB        → vector store local
RAGAS           → avaliação de RAG
Pydantic v2     → structured output, validação
Gradio          → interfaces web
Streamlit       → apps web com estado
```

### Ambiente

- Google Colab (gratuito) para notebooks
- Docker + Ollama (gratuito) para projetos locais
- Custo zero como requisito de atividade

---

## 11. Modelos proibidos

Os seguintes modelos **não devem ser usados** em código ou exemplos:

```
GPT-3, GPT-3.5, Claude 1, Claude 2, LLaMA 1, LLaMA 2, BERT, GPT-2
```

> Aceitos apenas em citação histórica com contexto explícito.

---

## 12. Referências acadêmicas

### Livros

- Russell, S.; Norvig, P. — *Inteligência Artificial*. 3ª ed. Pearson, 2016
- Goodfellow, I. et al. — *Deep Learning*. Pearson, 2017
- Chollet, F. — *Deep Learning com Python*. Pearson, 2018

### Papers

- Vaswani et al. (2017) — "Attention Is All You Need" — arxiv.org/abs/1706.03762
- Brown et al. (2020) — "Language Models are Few-Shot Learners" — arxiv.org/abs/2005.14165
- Wei et al. (2022) — "Chain-of-Thought Prompting Elicits Reasoning in LLMs"
- Yao et al. (2022) — "ReAct: Synergizing Reasoning and Acting in LLMs" — arxiv.org/abs/2210.03629

### Online

- [promptingguide.ai](https://promptingguide.ai) — guia principal
- [anthropic.com/engineering](https://anthropic.com/engineering) — context engineering
- [python.langchain.com](https://python.langchain.com) — docs LangChain
- [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph) — docs LangGraph
- [ragas.io](https://ragas.io) — docs RAGAS
- [ollama.com](https://ollama.com) — modelos e API

### Legislação

- Lei 13.709/2018 (LGPD) — planalto.gov.br
- PL 2338/2023 (Marco Legal da IA) — senado.leg.br
- EU AI Act — Regulation 2024/1689

---

## 13. Troubleshooting

### Ollama não responde

```bash
# Verificar se o container está rodando
docker compose ps

# Verificar logs
docker compose logs -f ollama

# Reiniciar
docker compose restart ollama
```

### Erro de permissão no PowerShell

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Modelo não encontrado

O download do modelo é automático na primeira execução. Verifique o progresso:

```bash
docker compose logs -f ollama
# Ou
docker exec -it fiap-ollama ollama list
```

### Espaço insuficiente

O setup completo (`fiap-ai-lab-complete`) pode consumir ~15 GB. Use o setup leve (`fiap-openwebui-ollama-setup`) se tiver pouca espaço (~4 GB).

---

## Licença

Conteúdo educacional — FIAP · Ciência da Computação · 2026.

*Copyright © 2026 Prof. Jorge Luiz Gomes · FIAP · Todos os direitos reservados.*
