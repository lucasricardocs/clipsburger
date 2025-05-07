import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
st.set_page_config(layout="wide", page_title="Sistema de Registro do Clips Burger")

# Logo e título
col_logo, col_titulo = st.columns([1, 6])
with col_logo:
    st.image("logo.png", width=100)
with col_titulo:
    st.title("Sistema de Registro do Clips Burger")

# Autenticação com Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
gc = gspread.authorize(credentials)
spreadsheet_id = "VendasPitDog"

# Funções auxiliares
def read_worksheet(sheet_name):
    try:
        spreadsheet = gc.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data), worksheet
    except Exception as e:
        st.error(f"Erro ao acessar a planilha: {e}")
        return pd.DataFrame(), None

def append_row(sheet_name, row):
    try:
        spreadsheet = gc.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.append_row(row)
    except Exception as e:
        st.error(f"Erro ao adicionar linha na planilha: {e}")

def process_vendas(df):
    if not df.empty:
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        df['Ano'] = df['Data'].dt.year
        df['Mês'] = df['Data'].dt.month
        df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
    return df

def process_compras(df):
    if not df.empty:
        for col in ['Pão', 'Frios', 'Bebidas']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df['Total'] = df[['Pão', 'Frios', 'Bebidas']].sum(axis=1)
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
            df['Ano'] = df['Data'].dt.year
            df['Mês'] = df['Data'].dt.month
            df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
    return df

# Tabs
aba1, aba2, aba3 = st.tabs(["📋 Registro", "📊 Análise de Vendas", "🛒 Análise de Compras"])

with aba1:
    st.subheader("Registro de Vendas")
    with st.form("form_vendas"):
        data_venda = st.date_input("Data da Venda", value=datetime.today())
        col1, col2, col3 = st.columns(3)
        with col1:
            cartao = st.number_input("Cartão", min_value=0.0, step=0.01)
        with col2:
            dinheiro = st.number_input("Dinheiro", min_value=0.0, step=0.01)
        with col3:
            pix = st.number_input("PIX", min_value=0.0, step=0.01)
        total = cartao + dinheiro + pix
        st.write(f"**Total: R${total:.2f}**")
        enviar_venda = st.form_submit_button("Registrar Venda")
        if enviar_venda:
            append_row("Vendas", [data_venda.strftime('%d/%m/%Y'), cartao, dinheiro, pix, total])
            st.success("Venda registrada com sucesso!")

    st.subheader("Registro de Compras")
    with st.form("form_compras"):
        data_compra = st.date_input("Data da Compra", value=datetime.today())
        col1, col2, col3 = st.columns(3)
        with col1:
            pao = st.number_input("Pão", min_value=0.0, step=0.01)
        with col2:
            frios = st.number_input("Frios", min_value=0.0, step=0.01)
        with col3:
            bebidas = st.number_input("Bebidas", min_value=0.0, step=0.01)
        enviar_compra = st.form_submit_button("Registrar Compra")
        if enviar_compra:
            append_row("Compras", [data_compra.strftime('%d/%m/%Y'), pao, frios, bebidas])
            st.success("Compra registrada com sucesso!")

with aba2:
    st.header("Análise de Vendas")
    df_vendas, _ = read_worksheet("Vendas")
    df_vendas = process_vendas(df_vendas)

    if not df_vendas.empty:
        current_month = datetime.now().month
        current_year = datetime.now().year
        anos = sorted(df_vendas['Ano'].unique())
        selected_anos = st.sidebar.multiselect("Ano(s):", anos, default=[current_year])
        meses_disponiveis = sorted(df_vendas[df_vendas['Ano'].isin(selected_anos)]['Mês'].unique())
        meses_nomes = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
        selected_meses_str = st.sidebar.multiselect("Mês(es):", [f"{m} - {meses_nomes[m]}" for m in meses_disponiveis], default=[f"{current_month} - {meses_nomes[current_month]}"])
        selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]

        df_filtered = df_vendas[df_vendas['Ano'].isin(selected_anos)]
        df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)]

        st.subheader("Resumo das Vendas")
        st.dataframe(df_filtered[['DataFormatada', 'Cartão', 'Dinheiro', 'PIX', 'Total']], use_container_width=True)

        st.subheader("Gráfico de Totais por Categoria")
        melted_df = df_filtered.melt(id_vars=['DataFormatada'], value_vars=['Cartão', 'Dinheiro', 'PIX'], var_name='Meio', value_name='Valor')
        chart = alt.Chart(melted_df).mark_bar().encode(
            x=alt.X('DataFormatada:N', title='Data', axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('Valor:Q', title='Valor (R$)'),
            color='Meio:N',
            tooltip=['DataFormatada', 'Meio', 'Valor']
        ).properties(width=700, height=400)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Nenhuma venda encontrada.")

with aba3:
    st.header("Análise Detalhada de Compras")
    df_compras, _ = read_worksheet("Compras")
    df_compras = process_compras(df_compras)

    if not df_compras.empty:
        current_month = datetime.now().month
        current_year = datetime.now().year
        anos = sorted(df_compras['Ano'].unique())
        selected_anos = st.sidebar.multiselect("Ano(s):", anos, default=[current_year])
        meses_disponiveis = sorted(df_compras[df_compras['Ano'].isin(selected_anos)]['Mês'].unique())
        meses_nomes = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
        selected_meses_str = st.sidebar.multiselect("Mês(es):", [f"{m} - {meses_nomes[m]}" for m in meses_disponiveis], default=[f"{current_month} - {meses_nomes[current_month]}"])
        selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]

        df_filtered = df_compras[df_compras['Ano'].isin(selected_anos)]
        df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)]

        st.subheader("Compras Filtradas")
        st.dataframe(df_filtered[['DataFormatada', 'Pão', 'Frios', 'Bebidas']], use_container_width=True, height=300)

        st.subheader("Distribuição de Compras por Categoria")
        compras_sum = {
            'Categoria': ['Pão', 'Frios', 'Bebidas'],
            'Valor': [
                df_filtered['Pão'].sum(),
                df_filtered['Frios'].sum(),
                df_filtered['Bebidas'].sum()
            ]
        }
        compras_df = pd.DataFrame(compras_sum)

        chart = alt.Chart(compras_df).mark_arc(innerRadius=50).encode(
            theta=alt.Theta("Valor:Q", stack=True),
            color=alt.Color("Categoria:N"),
            tooltip=["Categoria", "Valor"]
        ).properties(width=700, height=500)
        text = chart.mark_text(radius=120, size=16).encode(text="Valor:Q")
        st.altair_chart(chart + text, use_container_width=True)

        st.subheader("Compras Diárias por Categoria")
        daily_compras = df_filtered.melt(
            id_vars=['DataFormatada'],
            value_vars=['Pão', 'Frios', 'Bebidas'],
            var_name='Categoria',
            value_name='Valor'
        )

        chart2 = alt.Chart(daily_compras).mark_bar(size=30).encode(
            x=alt.X('DataFormatada:N', title='Data', axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('Valor:Q', title='Valor (R$)'),
            color='Categoria:N',
            tooltip=['DataFormatada', 'Categoria', 'Valor']
        ).properties(width=700, height=500)
        st.altair_chart(chart2, use_container_width=True)
    else:
        st.info("Não há dados de compras para exibir.")

# Rodapé
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: small;'>
        © 2025 Clips Burger - Sistema de Gestão | Desenvolvido com ❤️ e Streamlit
    </div>
    """,
    unsafe_allow_html=True
)
