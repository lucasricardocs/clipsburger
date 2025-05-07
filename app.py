import streamlit as st
import pandas as pd
import datetime
import altair as alt
from PIL import Image
from google.oauth2 import service_account
import gspread

# Autenticação com Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope)

client = gspread.authorize(credentials)
SHEET_URL = st.secrets["private_gsheets_url"]
sheet = client.open_by_url(SHEET_URL)

# Função para carregar dados
def load_data(worksheet_name):
    worksheet = sheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# Função para salvar dados
def save_data(worksheet_name, data):
    worksheet = sheet.worksheet(worksheet_name)
    worksheet.append_row(data)

# Processamento de datas
def process_data(df):
    if df.empty or 'data' not in df.columns:
        return df
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['Ano'] = df['data'].dt.year
    df['Mês'] = df['data'].dt.month
    df['Dia'] = df['data'].dt.day
    df['Dia da Semana'] = df['data'].dt.day_name()
    return df

# Função principal
def main():
    st.set_page_config(page_title="Clip's Burger - Sistema de Cadastro", layout="wide")

    # Topo com logo
    col1, col2 = st.columns([1, 8])
    with col1:
        st.image("logo.png", width=80)
    with col2:
        st.title("Clip's Burger - Sistema de Cadastro")

    # Carregar dados
    df_vendas = load_data("Vendas")
    df_compras = load_data("Compras")

    df_vendas = process_data(df_vendas)
    df_compras = process_data(df_compras)

    # Sidebar com filtros
    anos = sorted(set(df_vendas['Ano'].dropna().unique()).union(df_compras['Ano'].dropna().unique()))
    meses = sorted(set(df_vendas['Mês'].dropna().unique()).union(df_compras['Mês'].dropna().unique()))

    st.sidebar.header("Filtros")
    ano_selecionado = st.sidebar.selectbox("Selecione o Ano", anos)
    mes_selecionado = st.sidebar.selectbox("Selecione o Mês", meses)

    # Aplicar filtro
    df_vendas_filtrado = df_vendas[(df_vendas['Ano'] == ano_selecionado) & (df_vendas['Mês'] == mes_selecionado)]
    df_compras_filtrado = df_compras[(df_compras['Ano'] == ano_selecionado) & (df_compras['Mês'] == mes_selecionado)]

    aba = st.tabs(["Cadastro", "Análise de Vendas", "Análise de Compras", "Estatísticas"])

    # Aba Cadastro
    with aba[0]:
        st.subheader("Registrar Nova Venda")
        with st.form("venda_form"):
            data_venda = st.date_input("Data da Venda", value=datetime.date.today(), key="venda_data")
            produto = st.text_input("Produto")
            valor = st.number_input("Valor", min_value=0.0, step=0.01)
            forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Cartão", "Pix"])
            submit_venda = st.form_submit_button("Registrar Venda")
            if submit_venda:
                save_data("Vendas", [str(data_venda), produto, valor, forma_pagamento])
                st.success("Venda registrada com sucesso!")

        st.subheader("Registrar Nova Compra")
        with st.form("compra_form"):
            data_compra = st.date_input("Data da Compra", value=datetime.date.today(), key="compra_data")
            pao = st.number_input("Pão", min_value=0.0, step=0.01)
            frios = st.number_input("Frios", min_value=0.0, step=0.01)
            bebidas = st.number_input("Bebidas", min_value=0.0, step=0.01)
            submit_compra = st.form_submit_button("Registrar Compra")
            if submit_compra:
                save_data("Compras", [str(data_compra), pao, frios, bebidas])
                st.success("Compra registrada com sucesso!")

    # Aba Análise de Vendas
    with aba[1]:
        st.subheader("Gráficos de Vendas")
        if not df_vendas_filtrado.empty:
            chart = alt.Chart(df_vendas_filtrado).mark_bar().encode(
                x='forma_pagamento:N',
                y='valor:Q',
                color='forma_pagamento:N'
            ).properties(width=600)
            st.altair_chart(chart)

            linha = alt.Chart(df_vendas_filtrado).mark_line(point=True).encode(
                x='data:T', y='valor:Q'
            ).properties(width=600)
            st.altair_chart(linha)
        else:
            st.warning("Nenhuma venda registrada no período.")

    # Aba Análise de Compras
    with aba[2]:
        st.subheader("Gráficos de Compras")
        if not df_compras_filtrado.empty:
            df_long = df_compras_filtrado.melt(id_vars=['data'], value_vars=['pao', 'frios', 'bebidas'],
                                               var_name='categoria', value_name='valor')
            chart = alt.Chart(df_long).mark_bar().encode(
                x='categoria:N',
                y='valor:Q',
                color='categoria:N'
            ).properties(width=600)
            st.altair_chart(chart)

            linha = alt.Chart(df_long).mark_line(point=True).encode(
                x='data:T', y='valor:Q', color='categoria:N'
            ).properties(width=600)
            st.altair_chart(linha)
        else:
            st.warning("Nenhuma compra registrada no período.")

    # Aba Estatísticas
    with aba[3]:
        st.subheader("Estatísticas Gerais")
        if not df_vendas_filtrado.empty:
            dias_ativos = df_vendas_filtrado['data'].dt.date.nunique()
            dia_mais_vendas = df_vendas_filtrado.groupby('Dia da Semana')['valor'].mean().idxmax()
            dia_menos_vendas = df_vendas_filtrado.groupby('Dia da Semana')['valor'].mean().idxmin()
            st.markdown(f"- **Dias trabalhados:** {dias_ativos}")
            st.markdown(f"- **Dia com mais vendas (em média):** {dia_mais_vendas}")
            st.markdown(f"- **Dia com menos vendas (em média):** {dia_menos_vendas}")

            total_vendas = df_vendas_filtrado['valor'].sum()
            media_vendas = df_vendas_filtrado['valor'].mean()
            st.markdown(f"- **Total vendido:** R$ {total_vendas:.2f}")
            st.markdown(f"- **Média por venda:** R$ {media_vendas:.2f}")
        else:
            st.info("Nenhuma estatística de vendas disponível no período.")

if __name__ == '__main__':
    main()
