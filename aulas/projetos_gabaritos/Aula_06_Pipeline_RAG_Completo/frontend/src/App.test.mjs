import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

let vite;

before(async () => {
  vite = await createServer({
    root: fileURLToPath(new URL('..', import.meta.url)),
    appType: 'custom',
    logLevel: 'silent',
    server: { middlewareMode: true },
  });
});

after(async () => {
  await vite?.close();
});

test('renderiza as fontes recuperadas junto da resposta do RAG', async () => {
  const { FontesView } = await vite.ssrLoadModule('/src/App.jsx');
  const html = renderToStaticMarkup(createElement(FontesView, {
    fontes: [{
      fonte: 'manual.pdf',
      pagina: 7,
      trecho: 'Trecho recuperado do documento.',
    }],
  }));

  assert.match(html, /manual\.pdf/);
  assert.match(html, /página 7/);
  assert.match(html, /Trecho recuperado do documento\./);
});
