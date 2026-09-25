# models/ — modelos GGUF locais

Coloque aqui os arquivos `.gguf` baixados manualmente (por exemplo do
Hugging Face). Esta pasta é montada em `/models` (read-only) dentro do
container do Ollama.

A pasta **pode ficar vazia**: o stack sobe do mesmo jeito, o servidor
Ollama funciona e o Open WebUI abre. Sem `.gguf` é só o modelo de chat
local que não aparece — e o `entrypoint.sh` avisa no log o que fazer.
Os alvos `make up*` já criam a pasta (com o seu usuário como dono) antes
do Docker subir, para ela não nascer como `root`.

## Como funciona

No start do container, o `entrypoint.sh`:

1. **importa TODOS os `.gguf` da pasta** — cada arquivo vira um modelo
   do Ollama com o nome do arquivo sem `.gguf` (pula os já existentes);
2. o arquivo definido em `GGUF_FILE` no `.env` (ou, se não houver, o
   primeiro em ordem alfabética) é o **modelo principal** — recebe o
   nome de `GGUF_MODEL` e satisfaz o `CHAT_MODEL`;
3. para cada um, gera um `Modelfile` com `FROM /models/<arquivo>` e
   roda `ollama create <nome>` — **apenas se o modelo ainda não existir**;
4. baixa o modelo de embeddings, cria a variante enxuta `-ctx<N>` usada
   no RAG e baixa os guardrails e extras listados no `.env`;
5. os modelos passam a aparecer no `ollama list` e no Open WebUI.

O `CHAT_MODEL` do `.env` define qual modelo o Open WebUI usa por padrão.

## Modelos que já estão aqui (exemplo do lab)

```
gemma-3-1b-it-heretic-extreme-uncensored-abliterated.i1-Q4_K_M.gguf
LFM2.5-2.6B-Uncensored-Q4_K_M.gguf
MiniCPM5-2B-heretic-abliterated-Q4_K_M.gguf
Qwen3.8-2B-Uncensored-Q4_K_M.gguf
Qwen3-0.6B-heretic-abliterated-uncensored.Q4_K_M.gguf
```

Todos entram no Ollama com o nome do arquivo (sem `.gguf`); o
principal é o `GGUF_FILE` (padrão: `MiniCPM5-...`), com nome de
`GGUF_MODEL` — se este ficar vazio, usa o nome do arquivo.

```bash
make gguf           # o que tem na pasta e o que o .env espera
make models         # o que já está instalado no Ollama
make models-check   # o que o .env exige e ainda falta
```

## Adicionar ou trocar o modelo principal

```bash
# 1. copie o .gguf para cá
cp ~/Downloads/Outro-Modelo-Q4_K_M.gguf models/

# 2. ajuste o .env
#    GGUF_FILE=Outro-Modelo-Q4_K_M.gguf
#    GGUF_MODEL=Outro-Modelo-Q4_K_M
#    CHAT_MODEL=Outro-Modelo-Q4_K_M

# 3. importa sem reiniciar (idempotente)
make gguf-import
```

Com o container parado, `make restart` também importa tudo no boot.

Se o modelo já tiver sido importado com o mesmo nome, o `entrypoint.sh`
pula a importação. Para forçar a reimportação:

```bash
make gguf-import FORCE=1              # reimporta todos
make models-rm M=<nome-do-modelo>     # remove um e importe de novo
```

## Sem `.gguf` na pasta

Nada quebra: o container sobe, o Ollama responde e o Open WebUI abre.
No log você vê o motivo e o que fazer:

```
-> Nenhum arquivo .gguf em /models. Pulando importacao.
-> Modelo de chat 'MiniCPM5-2B-heretic-abliterated-Q4_K_M' NAO esta disponivel:
   o .gguf 'MiniCPM5-2B-heretic-abliterated-Q4_K_M.gguf' nao esta em '/models'...
   Copie o arquivo para a pasta models/ do projeto e rode 'make restart',
   ou aponte GGUF_FILE/GGUF_MODEL/CHAT_MODEL no .env para o arquivo correto.
   Sem CHAT_MODEL_FALLBACK no .env: nada foi baixado. ...
```

Duas saídas então:

- **ter um chat funcionando mesmo assim**: defina no `.env` um modelo
  da biblioteca pública como reserva, que é baixado automaticamente
  quando o `.gguf` não está lá:

  ```bash
  CHAT_MODEL_FALLBACK=qwen3:0.6b
  ```

- **só usar a biblioteca**: aponte `CHAT_MODEL` direto para um modelo
  com tag (`qwen3:0.6b`, `gpt-oss:20b`, ...) e deixe `GGUF_FILE` vazio.

Note que um nome de modelo **sem tag** (`MiniCPM5-2B-...`) nunca existe
na biblioteca do Ollama: ele só pode vir de um `.gguf`. Por isso o
entrypoint não tenta baixá-lo e explica o que fazer.

## Observações

- A pasta é montada como **read-only**: o Ollama nunca altera seus arquivos.
- O Ollama copia o GGUF para o volume `ollama_data`, então o modelo ocupa
  espaço duas vezes (uma no arquivo, outra no blob do Ollama).
- Arquivos `.gguf` são ignorados pelo git (veja `.gitignore`).
- Com o container no ar, para ver os arquivos e modelos:
  `make gguf` (arquivos no host), `make models` (modelos no Ollama) e
  `make test` (testa chat, embeddings e interface de ponta a ponta).
