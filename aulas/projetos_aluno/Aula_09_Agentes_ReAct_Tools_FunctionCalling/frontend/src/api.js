async function chamar(url, corpo) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(corpo || {}),
  });
  const texto = await res.text();
  try {
    return JSON.parse(texto);
  } catch {
    return { tipo: 'erro', conteudo: texto || `HTTP ${res.status}` };
  }
}

export const api = {
  info: () => fetch('/api/info').then((r) => r.json()),
  post: (endpoint, corpo) => chamar(endpoint, corpo),
};