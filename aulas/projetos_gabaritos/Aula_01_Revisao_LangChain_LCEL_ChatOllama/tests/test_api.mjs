import assert from 'node:assert/strict';
import test from 'node:test';

import { api } from '../frontend/src/api.js';

function respostaSse(eventos) {
  const corpo = eventos.map((evento) => `event: ${evento.evento}\ndata: ${JSON.stringify(evento.dados)}\n\n`).join('');
  return new Response(corpo, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  });
}

test('post rejeita resposta HTTP com status de erro', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'falha' }), { status: 500 });

  await assert.rejects(() => api.post('/api/testar', {}), /HTTP 500: falha/);
});

test('stream normaliza done para texto Markdown', async () => {
  globalThis.fetch = async () => respostaSse([
    { evento: 'chunk', dados: { tipo: 'chunk', conteudo: 'Olá' } },
    { evento: 'chunk', dados: { tipo: 'chunk', conteudo: ' **mundo**' } },
    { evento: 'done', dados: { tipo: 'done', conteudo: 'Olá **mundo**', extra: { tokens_recebidos: 2 } } },
  ]);
  const recebidos = [];

  const resultado = await api.stream('/api/stream', { pergunta: 'oi' }, (evento) => recebidos.push(evento));

  assert.deepEqual(recebidos.map((evento) => evento.conteudo), ['Olá', ' **mundo**']);
  assert.equal(resultado.tipo, 'texto');
  assert.equal(resultado.conteudo, 'Olá **mundo**');
  assert.equal(resultado.extra.tokens_recebidos, 2);
});

test('stream rejeita evento de erro mesmo com status 200', async () => {
  globalThis.fetch = async () => respostaSse([
    { evento: 'error', dados: { tipo: 'erro', conteudo: 'modelo falhou' } },
  ]);

  await assert.rejects(() => api.stream('/api/stream', {}), /modelo falhou/);
});
