import streamlit as st

st.title("Minha Aplicação Streamlit")

# Exemplo simples de input de dados
nome = st.text_input("Qual seu nome?")
if nome:
    st.write(f"Olá, {nome}!")

# Adicionar mais funcionalidades aqui...
