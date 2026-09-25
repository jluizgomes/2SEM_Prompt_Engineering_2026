"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 08 — Interfaces: Gradio e Streamlit

Projeto local: expor uma chain RAG (com memória por sessão) através de
duas interfaces — Gradio (main.py) e Streamlit (app_streamlit.py).

Como rodar:
    1. pip install -r requirements.txt
    2. confirme o .env
    3. Gradio:    python main.py          -> abre em http://localhost:7860
    4. Streamlit: streamlit run app_streamlit.py
"""
import uuid

from rag import responder


def responder_gradio(mensagem, historico, session_id, responder_rag=None):
    """Callback da interface Gradio: mantém o histórico da sessão atual."""
    mensagens = list(historico or [])
    sessao = str(session_id or uuid.uuid4().hex)
    mensagens.append({"role": "user", "content": mensagem})
    try:
        executor = responder_rag or responder
        resposta = executor(mensagem, sessao)
    except Exception:
        resposta = "Não foi possível consultar o assistente agora. Verifique o modelo e o corpus local."
    mensagens.append({"role": "assistant", "content": resposta})
    return mensagens, sessao


def main() -> None:
    import gradio as gr

    print("Abrindo interface Gradio em http://localhost:7860 ...")

    with gr.Blocks(title="Assistente FIAP — Aula 08") as demo:
        session_id = gr.State(value=None)
        chat = gr.Chatbot(
            label="Conversa",
            placeholder="Faça uma pergunta sobre o corpus da aula...",
        )
        mensagem = gr.Textbox(label="Mensagem", placeholder="Digite sua mensagem...")
        enviar = gr.Button("Enviar", variant="primary")

        evento = enviar.click(responder_gradio, [mensagem, chat, session_id], [chat, session_id])
        evento.then(lambda: "", None, mensagem)

    demo.queue().launch()


if __name__ == "__main__":
    main()
