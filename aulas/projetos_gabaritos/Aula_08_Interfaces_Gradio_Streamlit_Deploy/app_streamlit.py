"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 08 — Interfaces: variante Streamlit

Rode com:
    streamlit run app_streamlit.py
"""
import uuid

from rag import responder


def garantir_session_id(estado) -> str:
    session_id = estado.get("memoria_session_id")
    if not session_id:
        session_id = uuid.uuid4().hex
        estado["memoria_session_id"] = session_id
    return session_id


def responder_streamlit(mensagem, session_id, responder_rag=None):
    executor = responder_rag or responder
    return executor(mensagem, session_id)


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Assistente FIAP — Aula 08", page_icon="🤖")
    st.title("Assistente FIAP — Aula 08 (Streamlit)")
    st.caption("RAG local com memória isolada por sessão")

    session_id = garantir_session_id(st.session_state)
    if "mensagens" not in st.session_state:
        st.session_state.mensagens = []

    for msg in st.session_state.mensagens:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if pergunta := st.chat_input("Digite sua mensagem..."):
        st.session_state.mensagens.append({"role": "user", "content": pergunta})
        with st.chat_message("user"):
            st.markdown(pergunta)

        with st.chat_message("assistant"):
            try:
                resposta = responder_streamlit(pergunta, session_id)
            except Exception:
                resposta = "Não foi possível consultar o assistente agora. Verifique o modelo e o corpus local."
            st.markdown(resposta)

        st.session_state.mensagens.append({"role": "assistant", "content": resposta})


if __name__ == "__main__":
    main()
