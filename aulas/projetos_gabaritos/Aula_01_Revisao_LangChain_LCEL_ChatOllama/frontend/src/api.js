async function erroHttp(res, texto) {
  let detalhe = texto;
  try {
    const dados = JSON.parse(texto);
    detalhe = dados.detail || dados.conteudo || texto;
  } catch {
    detalhe = texto;
  }
  return new Error(`HTTP ${res.status}${detalhe ? `: ${detalhe}` : ''}`);
}

async function chamar(url, corpo) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(corpo || {}),
  });
  const texto = await res.text();
  if (!res.ok) throw await erroHttp(res, texto);
  try {
    return JSON.parse(texto);
  } catch {
    return { tipo: 'erro', conteudo: texto || `HTTP ${res.status}` };
  }
}

async function stream(url, corpo, aoReceber) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(corpo || {}),
  });
  if (!res.ok) throw await erroHttp(res, await res.text());
  if (!res.body) throw new Error('Resposta sem stream disponível.');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let ultimo = null;

  const processar = (bloco) => {
    const linhas = bloco.split(/\r?\n/);
    let evento = 'message';
    const dados = [];
    linhas.forEach((linha) => {
      if (linha.startsWith('event:')) evento = linha.slice(6).trim();
      if (linha.startsWith('data:')) dados.push(linha.slice(5).trimStart());
    });
    if (dados.length === 0) return;
    let conteudo;
    try {
      conteudo = JSON.parse(dados.join('\n'));
    } catch {
      throw new Error('Resposta de streaming inválida.');
    }
    if (evento === 'error' || conteudo.tipo === 'erro') {
      throw new Error(conteudo.conteudo || 'Erro no streaming.');
    }
    if (conteudo.tipo === 'chunk') {
      ultimo = conteudo;
      if (aoReceber) aoReceber(conteudo);
    } else if (conteudo.tipo === 'done') {
      ultimo = conteudo;
    }
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        buffer += decoder.decode();
        if (buffer.trim()) processar(buffer);
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const blocos = buffer.split(/\r?\n\r?\n/);
      buffer = blocos.pop() || '';
      blocos.forEach(processar);
    }
  } finally {
    reader.releaseLock();
  }

  if (!ultimo || ultimo.tipo !== 'done') {
    throw new Error('O stream terminou sem um resultado final.');
  }
  return ultimo;
}

export const api = {
  info: async () => {
    const res = await fetch('/api/info');
    const texto = await res.text();
    if (!res.ok) throw await erroHttp(res, texto);
    try {
      return JSON.parse(texto);
    } catch {
      throw new Error('Resposta inválida de /api/info.');
    }
  },
  post: chamar,
  stream,
};
