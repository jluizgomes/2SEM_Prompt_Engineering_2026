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
};
