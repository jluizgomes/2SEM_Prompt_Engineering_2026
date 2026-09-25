import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api } from './api.js';
import './styles.css';

/**
 * Interface web mínima e genérica para os exercícios de LangChain.
 *
 * A UI é dirigida por dados: o backend expõe GET /api/info descrevendo
 * parâmetros, modo (chat / ações) e endpoints; o frontend renderiza os
 * widgets conforme essa descrição. Assim o MESMO frontend serve todos os
 * exercícios (aluno e gabarito) sem alteração.
 *
 * Contrato esperado de POST (todos os endpoints de ação):
 *   { "tipo": "texto"|"json"|"lista"|"erro",
 *     "conteudo": <string|object|array>,
 *     "extra": { ... },                     // opcional
 *     "aprovacao_pendente": <bool>,         // opcional (HITL)
 *     "aprovacao_titulo": <string> }        // opcional (HITL)
 */
const TIPOS = ['texto', 'json', 'lista', 'erro'];

/** Renderiza o texto do LLM como Markdown (tabelas, listas, código, negrito…). */
function Markdown({ children }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: (props) => <a {...props} target="_blank" rel="noreferrer" />,
        table: (props) => (
          <div className="md-tabela">
            <table {...props} />
          </div>
        ),
        code({ inline, className, children, ...props }) {
          if (inline) {
            return <code className="md-code-inline" {...props}>{children}</code>;
          }
          return (
            <pre className="md-code-bloco">
              <code {...props}>{children}</code>
            </pre>
          );
        },
      }}
    >
      {children}
    </ReactMarkdown>
  );
}

export default function App() {
  const [info, setInfo] = useState(null);
  const [erroInfo, setErroInfo] = useState(null);
  const [parametros, setParametros] = useState({});   // params topo (persistem)
  const [mensagens, setMensagens] = useState([]);     // chat
  const [textoChat, setTextoChat] = useState('');
  const [resultados, setResultados] = useState([]);   // log de ações
  const [carregando, setCarregando] = useState(false);
  const [aprovacao, setAprovacao] = useState(null);   // HITL pendente
  const fimDaLista = useRef(null);

  useEffect(() => {
    api.info()
      .then((dados) => {
        setInfo(dados);
        const iniciais = {};
        (dados.parametros || []).forEach((p) => {
          iniciais[p.nome] = p.padrao ?? '';
        });
        setParametros(iniciais);
      })
      .catch((e) => setErroInfo(String(e)));
  }, []);

  useEffect(() => {
    fimDaLista.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [mensagens, resultados, carregando]);

  if (erroInfo) {
    return (
      <div className="app erro-tela">
        <h1>Não foi possível carregar a interface</h1>
        <pre>{erroInfo}</pre>
        <p>Confirme que o servidor FastAPI está rodando e acessível em /api/info.</p>
      </div>
    );
  }
  if (!info) return <div className="app carregando">Carregando exercício…</div>;

  const topParams = info.parametros || [];
  const acoes = info.acoes || [];
  const ehChat = info.modo === 'chat';

  async function executar(endpoint, corpo, rotulo) {
    setCarregando(true);
    try {
      const resposta = await api.post(endpoint, corpo);
      const item = {
        id: Date.now(),
        rotulo: rotulo || endpoint,
        resposta: respostaTipo(resposta),
      };
      setResultados((r) => [...r, item]);
      if (resposta && resposta.aprovacao_pendente) {
        setAprovacao({
          endpoint: info.aprovacao_endpoint || '/api/aprovar',
          titulo: resposta.aprovacao_titulo || 'Aprovar e continuar',
          detalhe: resposta.conteudo || '',
        });
      } else {
        setAprovacao(null);
      }
      return resposta;
    } catch (e) {
      setResultados((r) => [...r, { id: Date.now(), rotulo, resposta: { tipo: 'erro', conteudo: String(e) } }]);
      return null;
    } finally {
      setCarregando(false);
    }
  }

  async function enviarChat(ev) {
    ev.preventDefault();
    const mensagem = textoChat.trim();
    if (!mensagem || carregando) return;
    setMensagens((m) => [...m, { papel: 'usuario', texto: mensagem }]);
    setTextoChat('');
    const corpo = { ...parametros, mensagem };
    setCarregando(true);
    try {
      const resposta = await api.post(info.chat_endpoint || '/api/conversar', corpo);
      if (resposta && resposta.tipo === 'erro') {
        setMensagens((m) => [...m, { papel: 'sistema', texto: resposta.conteudo }]);
      } else {
        const texto = extrairTexto(resposta);
        const passos = (resposta && resposta.extra && resposta.extra.passos) || null;
        setMensagens((m) => [...m, { papel: 'assistente', texto, passos }]);
      }
      if (resposta && resposta.aprovacao_pendente) {
        setAprovacao({
          endpoint: info.aprovacao_endpoint || '/api/aprovar',
          titulo: resposta.aprovacao_titulo || 'Aprovar e continuar',
          detalhe: resposta.conteudo || '',
        });
      }
    } catch (e) {
      setMensagens((m) => [...m, { papel: 'sistema', texto: 'Erro de rede: ' + String(e) }]);
    } finally {
      setCarregando(false);
    }
  }

  async function aprovar() {
    if (!aprovacao) return;
    await executar(aprovacao.endpoint, {}, 'Aprovação (HITL)');
  }

  function submitAcao(ev, acao) {
    ev.preventDefault();
    const dados = new FormData(ev.currentTarget);
    const corpo = { ...parametros };
    (acao.params || []).forEach((p) => {
      const valor = dados.get(p.nome);
      corpo[p.nome] = p.tipo === 'json'
        ? tentarJson(valor)
        : p.tipo === 'numero'
          ? Number(valor)
          : valor;
    });
    executar(acao.endpoint, corpo, acao.titulo || acao.endpoint);
  }

  return (
    <div className="app">
      <header className="cabecalho">
        <div>
          <h1>{info.nome || 'Exercício'}</h1>
          <p className="descricao">{info.descricao || ''}</p>
        </div>
        <span className="badge">{info.modulo || ''}</span>
      </header>

      {info.implementado === false && (
        <div className="banner incompleto">
          ⚠️ O backend não está disponível. Confira a inicialização e as variáveis de ambiente.
        </div>
      )}
      {(info.avisos || []).map((a, i) => (
        <div key={i} className="banner aviso">{a}</div>
      ))}
      {(info.env || []).map((a, i) => (
        <div key={i} className="banner env">{a}</div>
      ))}

      {topParams.length > 0 && (
        <section className="painel">
          <h2>Parâmetros</h2>
          <div className="grade-params">
            {topParams.map((p) => (
              <label key={p.nome} className="campo">
                <span>{p.label || p.nome}</span>
                {p.tipo === 'select' ? (
                  <select value={parametros[p.nome] ?? ''} onChange={(e) => setParametros({ ...parametros, [p.nome]: e.target.value })}>
                    {(p.opcoes || []).map((o) => (
                      <option key={o} value={o}>{o}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={parametros[p.nome] ?? ''}
                    placeholder={p.padrao ? '' : p.nome}
                    onChange={(e) => setParametros({ ...parametros, [p.nome]: e.target.value })}
                  />
                )}
              </label>
            ))}
          </div>
        </section>
      )}

      {ehChat && (
        <section className="painel chat-painel">
          <h2>Conversa</h2>
          <div className="chat-logs">
            {mensagens.length === 0 && <div className="chat-vazio">Digite uma mensagem para começar.</div>}
            {mensagens.map((m, i) => (
              <div key={i} className={`chat-item ${m.papel}`}>
                <div className="quem">{m.papel === 'usuario' ? 'Você' : m.papel === 'assistente' ? info.nome || 'Assistente' : 'Sistema'}</div>
                <div className="texto-chat">
                  {m.papel === 'sistema' ? m.texto : <Markdown>{limparFenceMarkdown(m.texto)}</Markdown>}
                  {m.passos && m.passos.length > 0 && (
                    <details className="md-passos">
                      <summary>Passos (Thought → Action → Observation)</summary>
                      {m.passos.map((p, j) => (
                        <div key={j} className="passo">{p}</div>
                      ))}
                    </details>
                  )}
                </div>
              </div>
            ))}
            {carregando && <div className="chat-item sistema"><div className="texto-chat">Pensando…</div></div>}
            <div ref={fimDaLista} />
          </div>
          <form className="linha-entrada" onSubmit={enviarChat}>
            <input
              value={textoChat}
              onChange={(e) => setTextoChat(e.target.value)}
              placeholder="Digite sua mensagem…"
              disabled={carregando}
            />
            <button type="submit" disabled={carregando || !textoChat.trim()}>Enviar</button>
          </form>
        </section>
      )}

      {acoes.length > 0 && (
        <section className="painel">
          <h2>Ações</h2>
          <div className="grade-acoes">
            {acoes.map((acao) => (
              <form key={acao.endpoint} className="cartao-acao" onSubmit={(ev) => submitAcao(ev, acao)}>
                <h3>{acao.titulo || acao.endpoint}</h3>
                {(acao.descricao || '') && <p className="cartao-desc">{acao.descricao}</p>}
                {(acao.params || []).map((p) => (
                  <label key={p.nome} className="campo">
                    <span>{p.label || p.nome}</span>
                    {p.tipo === 'textarea' ? (
                      <textarea name={p.nome} defaultValue={p.padrao ?? ''} rows={p.linhas || 4} />
                    ) : p.tipo === 'select' ? (
                      <select name={p.nome} defaultValue={p.padrao ?? ''}>
                        {(p.opcoes || []).map((o) => (
                          <option key={o} value={o}>{o}</option>
                        ))}
                      </select>
                    ) : (
                      <input name={p.nome} type="text" defaultValue={p.padrao ?? ''} placeholder={p.nome} />
                    )}
                  </label>
                ))}
                <button type="submit" disabled={carregando}>Executar</button>
              </form>
            ))}
          </div>
        </section>
      )}

      {aprovacao && (
        <div className="banner hitl">
          <strong>{aprovacao.titulo}</strong>
          {aprovacao.detalhe && <pre>{aprovacao.detalhe}</pre>}
          <button onClick={aprovar} disabled={carregando}>✅ Aprovar e continuar</button>
        </div>
      )}

      {resultados.length > 0 && (
        <section className="painel">
          <h2>Resultados</h2>
          {resultados.map((r) => (
            <div key={r.id} className="resultado">
              <div className="resultado-cab">{r.rotulo}</div>
              <ResultadoView dados={r.resposta} />
            </div>
          ))}
        </section>
      )}

      <footer className="rodape">
        Interface mínima em React · dados servidos por FastAPI · FIAP Prompt Engineering & AI 2026
      </footer>
    </div>
  );
}

/** Remove um fence ```markdown ... ``` que envolva a resposta inteira (comum em LLMs). */
function limparFenceMarkdown(texto) {
  const t = String(texto).trim();
  const m = t.match(/^```(?:markdown|md)\s*([\s\S]*?)```\s*$/);
  return m ? m[1] : t;
}

function tentarJson(valor) {
  if (valor == null || valor === '') return valor;
  try { return JSON.parse(valor); } catch { return valor; }
}

function respostaTipo(resposta) {
  if (!resposta) return { tipo: 'erro', conteudo: 'Resposta vazia do servidor.' };
  if (TIPOS.includes(resposta.tipo)) return resposta;
  return { tipo: 'json', conteudo: resposta };
}

function extrairTexto(resposta) {
  if (!resposta) return '(sem resposta)';
  if (resposta.tipo === 'texto') return String(resposta.conteudo ?? '');
  if (resposta.tipo === 'erro') return resposta.conteudo || 'Erro.';
  return JSON.stringify(resposta.conteudo ?? resposta, null, 2);
}

function ResultadoView({ dados }) {
  if (!dados) return <pre>Sem dados.</pre>;
  if (dados.tipo === 'texto') return (
    <div className="saida-texto">
      <Markdown>{limparFenceMarkdown(dados.conteudo ?? '')}</Markdown>
    </div>
  );
  if (dados.tipo === 'json') return <pre className="saida-json">{JSON.stringify(dados.conteudo, null, 2)}</pre>;
  if (dados.tipo === 'lista') {
    const itens = Array.isArray(dados.conteudo) ? dados.conteudo : [];
    return (
      <ol className="saida-lista">
        {itens.map((it, i) => (
          <li key={i}>
            {it.titulo ? <strong>{it.titulo}</strong> : null}
            {it.titulo && it.texto ? ' — ' : ''}
            {it.texto ? <span>{it.texto}</span> : null}
          </li>
        ))}
      </ol>
    );
  }
  if (dados.tipo === 'erro') return <div className="erro-inline">{dados.conteudo || 'Erro.'}</div>;
  return <pre>{JSON.stringify(dados, null, 2)}</pre>;
}