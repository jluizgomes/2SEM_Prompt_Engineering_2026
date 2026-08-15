"""
FIAP · Prompt Engineering & AI — 2º Semestre 2026
Aula 08 — Interfaces: variante Streamlit

Rode com:
    streamlit run app_streamlit.py
"""
import os

from dotenv import load_dotenv

import streamlit as st

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ─────────────────────────────────────────────────────────────
# Configuração via .env
# ─────────────────────────────────────────────────────────────
load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")

if not OLLAMA_API_KEY:
    st.error("OLLAMA_API_KEY não encontrada. Copie .env.example para .env.")
    st.stop()

os.environ["OLLAMA_HOST"] = OLLAMA_HOST
os.environ["OLLAMA_API_KEY"] = OLLAMA_API_KEY

llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0.5)

prompt = ChatPromptTemplate.from_messages([
    ("system", "Você é um assistente prestativo. Responda em português do Brasil."),
    ("human", "{pergunta}"),
])
chain = prompt | llm | StrOutputParser()

st.set_page_config(page_title="Assistente FIAP — Aula 08", page_icon="🤖")
st.title("Assistente FIAP — Aula 08 (Streamlit)")
st.caption(f"Modelo: {OLLAMA_MODEL}")

# Histórico na sessão do Streamlit
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
        resposta = chain.invoke({"pergunta": pergunta})
        st.markdown(resposta)

    st.session_state.mensagens.append({"role": "assistant", "content": resposta})
