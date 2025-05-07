import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
st.set_page_config(page_title="Sistema de Registro do Clips Burger", layout="centered")

# Logo e Título
top_col1, top_col2 = st.columns([1, 6])
with top_col1:
    st.image("logo.png", width=80)
with top_col2:
    st.title("Sistema de Registro do Clips Burger")

# Função para autenticação e leitura
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/spreadsheets.readonly', 'https://www.googleapis.com/auth/drive.readonly']
credentials_dict = st.secrets["google_credentials"]
creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
gc = gspread.authorize(creds)
spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'

# Leitura de worksheet
def read_worksheet(name):
    try:
        spreadsheet = gc.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(name)
        rows = worksheet.get_all_records()
        df = pd.DataFrame(rows)
        return df, worksheet
    except SpreadsheetNotFound:
        st.error(f"Aba '{name}' não encontrada na planilha.")
        return pd.DataFrame(), None

# Adicionar dados

def append_row(worksheet, row):
    try:
        worksheet.append_row(row)
        st.success("Dados registrados com sucesso!")
    except Exception as e:
        st.error(f"Erro ao adicionar dados: {e}")

# Processar DataFrame para Data e totais
def process_df(df, cols):
    if not df.empty:
        for col in cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['Total'] = df[cols].sum(axis=1)
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        df['Ano'] = df['Data'].dt.year
        df['Mês'] = df['Data'].dt.month
        df['MêsNome'] = df['Data'].dt.strftime('%B')
        df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
        df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
    return df

# Tabs
tab1, tab2, tab3 = st.tabs(["Registro", "Análise de Vendas", "Análise de Compras"])

# Registro
with tab1:
    with st.expander("Registrar Nova Venda"):
        with st.form("form_venda"):
            data_v = st.date_input("Data da Venda", datetime.now())
            c1, c2, c3 = st.columns(3)
            with c1:
                cartao = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f")
            with c2:
                dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f")
            with c3:
                pix = st.number_input("Pix (R$)", min_value=0.0, format="%.2f")
            submitted_v = st.form_submit_button("Registrar Venda")
            if submitted_v:
                if cartao > 0 or dinheiro > 0 or pix > 0:
                    df_vendas, ws_vendas = read_worksheet("Vendas")
                    append_row(ws_vendas, [data_v.strftime('%d/%m/%Y'), cartao, dinheiro, pix])
                else:
                    st.warning("Informe pelo menos um valor para registrar.")

    with st.expander("Registrar Nova Compra"):
        with st.form("form_compra"):
            data_c = st.date_input("Data da Compra", datetime.now())
            c1, c2, c3 = st.columns(3)
            with c1:
                pao = st.number_input("Pão (R$)", min_value=0.0, format="%.2f")
            with c2:
                frios = st.number_input("Frios (R$)", min_value=0.0, format="%.2f")
            with c3:
                bebidas = st.number_input("Bebidas (R$)", min_value=0.0, format="%.2f")
            submitted_c = st.form_submit_button("Registrar Compra")
            if submitted_c:
                if pao > 0 or frios > 0 or bebidas > 0:
                    df_compras, ws_compras = read_worksheet("Compras")
                    append_row(ws_compras, [data_c.strftime('%d/%m/%Y'), pao, frios, bebidas])
                else:
                    st.warning("Informe pelo menos um valor para registrar.")

# Filtros Sidebar
with st.sidebar:
    st.header("🔍 Filtros")
    aba = st.radio("Analisar:", ["Vendas", "Compras"])

    df_base, _ = read_worksheet(aba)
    df_base = process_df(df_base, ['Cartão', 'Dinheiro', 'Pix'] if aba == "Vendas" else ['Pão', 'Frios', 'Bebidas'])

    anos = sorted(df_base['Ano'].dropna().unique())
    ano_padrao = datetime.now().year
    anos_sel = st.multiselect("Ano(s):", anos, default=[ano_padrao] if ano_padrao in anos else anos)

    meses_disp = sorted(df_base[df_base['Ano'].isin(anos_sel)]['Mês'].unique())
    meses_nomes = {m: datetime(2023, m, 1).strftime('%B') for m in meses_disp}
    meses_opc = [f"{m} - {meses_nomes[m]}" for m in meses_disp]
    meses_sel_str = st.multiselect("Mês(es):", meses_opc, default=meses_opc)
    meses_sel = [int(m.split(" - ")[0]) for m in meses_sel_str]

# Análise de Vendas
def gerar_graficos(df, colunas, label):
    st.subheader(f"{label} Filtradas")
    st.dataframe(df[['DataFormatada'] + colunas + ['Total']], use_container_width=True, height=300)

    st.subheader(f"Distribuição por Categoria")
    df_pie = pd.DataFrame({
        'Categoria': colunas,
        'Valor': [df[c].sum() for c in colunas]
    })
    pie = alt.Chart(df_pie).mark_arc(innerRadius=50).encode(
        theta=alt.Theta("Valor:Q"),
        color=alt.Color("Categoria:N"),
        tooltip=["Categoria", "Valor"]
    )
    st.altair_chart(pie, use_container_width=True)

    st.subheader(f"Total Acumulado")
    df_line = df.sort_values('Data').copy()
    df_line['Total Acumulado'] = df_line['Total'].cumsum()
    line = alt.Chart(df_line).mark_line(point=True).encode(
        x=alt.X('Data:T', title='Data'),
        y=alt.Y('Total Acumulado:Q'),
        tooltip=['DataFormatada', 'Total Acumulado']
    )
    st.altair_chart(line, use_container_width=True)

with tab2:
    df_vendas, _ = read_worksheet("Vendas")
    df_vendas = process_df(df_vendas, ['Cartão', 'Dinheiro', 'Pix'])
    df_filtrado = df_vendas[df_vendas['Ano'].isin(anos_sel) & df_vendas['Mês'].isin(meses_sel)]
    gerar_graficos(df_filtrado, ['Cartão', 'Dinheiro', 'Pix'], "Vendas")

with tab3:
    df_compras, _ = read_worksheet("Compras")
    df_compras = process_df(df_compras, ['Pão', 'Frios', 'Bebidas'])
    df_filtrado = df_compras[df_compras['Ano'].isin(anos_sel) & df_compras['Mês'].isin(meses_sel)]
    gerar_graficos(df_filtrado, ['Pão', 'Frios', 'Bebidas'], "Compras")

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
