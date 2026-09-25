# models/ — modelos GGUF locais

Coloque aqui os arquivos `.gguf` baixados manualmente (por exemplo do
Hugging Face). Esta pasta é montada em `/models` (read-only) dentro do
container do Ollama.

## Como funciona

No start do container, o `entrypoint.sh`:

1. **importa TODOS os `.gguf` da pasta** — cada arquivo vira um modelo
   do Ollama com o nome do arquivo sem `.gguf` (pula os já existentes);
2. o arquivo definido em `GGUF_FILE` no `.env` (ou, se não houver, o
   primeiro em ordem alfabética) é o **modelo principal** — recebe o
   nome de `GGUF_MODEL` e satisfaz o `CHAT_MODEL`;
3. para cada um, gera um `Modelfile` com `FROM /models/<arquivo>` e
   roda `ollama create <nome>` — **apenas se o modelo ainda não existir**;
4. os modelos passam a aparecer no `ollama list`, no Open WebUI e,
   após `make langfuse-ollama`, no Playground do Langfuse.

O `CHAT_MODEL` do `.env` define qual modelo o Open WebUI usa por padrão.

## Modelos esperados (exemplo do lab)

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

## Adicionar ou trocar o modelo principal

```bash
# 1. copie o .gguf para cá
cp ~/Downloads/Outro-Modelo-Q4_K_M.gguf models/

# 2. ajuste o .env
#    GGUF_FILE=Outro-Modelo-Q4_K_M.gguf
#    GGUF_MODEL=Outro-Modelo-Q4_K_M
#    CHAT_MODEL=Outro-Modelo-Q4_K_M

# 3. importa sem reiniciar (idempotente) e atualiza o Playground
make gguf-import
make langfuse-ollama
```

Com o container parado, `make restart` também importa tudo no boot.

Se o modelo já tiver sido importado com o mesmo nome, o `entrypoint.sh`
pula a importação. Para forçar a reimportação de um específico:

```bash
docker exec fiap-ollama ollama rm <nome-do-modelo>
make gguf-import
```

## Observações

- A pasta é montada como **read-only**: o Ollama nunca altera seus arquivos.
- O Ollama copia o GGUF para o volume `ollama_data`, então o modelo ocupa
  espaço duas vezes (uma no arquivo, outra no blob do Ollama).
- Arquivos `.gguf` são ignorados pelo git (veja `.gitignore`).
- Com o container no ar, para ver os arquivos e modelos:
  `make gguf` (arquivos no host) e `make models` (modelos no Ollama).
