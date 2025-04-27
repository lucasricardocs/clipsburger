import streamlit as st
import sqlite3
import altair as alt
import pandas as pd

# Função para inserir uma venda no banco de dados
def insert_venda(data, valor_cartao, valor_dinheiro, valor_pix):
    try:
        conn = sqlite3.connect('vendas.db')
        conn.execute('INSERT INTO vendas (data, valor_cartao, valor_dinheiro, valor_pix) VALUES (?, ?, ?, ?)', 
                     (data, valor_cartao, valor_dinheiro, valor_pix))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        st.error(f"Erro ao acessar o banco de dados: {e}")

# Função para pegar os dados do banco de dados e convertê-los em um DataFrame
def get_vendas_data():
    conn = sqlite3.connect('vendas.db')
    query = 'SELECT * FROM vendas'
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Layout Streamlit
st.title('Dashboard de Vendas')

# Formulário para inserção de dados
st.header('Cadastrar Nova Venda')
data = st.date_input("Data")
valor_cartao = st.number_input("Valor Cartão", min_value=0.0, step=0.01)
valor_dinheiro = st.number_input("Valor Dinheiro", min_value=0.0, step=0.01)
valor_pix = st.number_input("Valor PIX", min_value=0.0, step=0.01)

if st.button('Cadastrar Venda'):
    if data and valor_cartao >= 0 and valor_dinheiro >= 0 and valor_pix >= 0:
        insert_venda(str(data), valor_cartao, valor_dinheiro, valor_pix)
        st.success('Venda cadastrada com sucesso!')
    else:
        st.error('Por favor, preencha todos os campos corretamente.')

# Exibindo gráfico de vendas por forma de pagamento
st.header('Total de Vendas por Forma de Pagamento')

# Pegando os dados do banco
df = get_vendas_data()

# Gráfico de vendas por forma de pagamento
chart = alt.Chart(df).transform_fold(
    ['valor_cartao', 'valor_dinheiro', 'valor_pix'],
    as_=['Forma de Pagamento', 'Valor']
).mark_bar().encode(
    x='Forma de Pagamento:N',
    y='sum(Valor):Q',
    color='Forma de Pagamento:N',
    tooltip=['Forma de Pagamento:N', 'sum(Valor):Q']
).properties(
    title='Total de Vendas por Forma de Pagamento'
)

st.altair_chart(chart, use_container_width=True)
