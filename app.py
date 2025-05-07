import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
st.set_page_config(page_title="Clip's Burger - Sistema de Cadastro", layout="centered")

# Topo com logo e título
col1, col2 = st.columns([1, 6])
with col1:
    st.image("logo.png", width=80)
with col2:
    st.title("Clip's Burger - Sistema de Cadastro")

def read_google_sheet(worksheet_name):
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 
                  'https://www.googleapis.com/auth/spreadsheets.readonly', 
                  'https://www.googleapis.com/auth/drive.readonly']
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
        spreadsheet = gc.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        rows = worksheet.get_all_records()
        df = pd.DataFrame(rows)
        return df, worksheet
    except SpreadsheetNotFound:
        st.error(f"Planilha '{worksheet_name}' não encontrada.")
        return pd.DataFrame(), None
    except Exception as e:
        st.error(f"Erro de autenticação: {e}")
        return pd.DataFrame(), None

def add_data_to_sheet(row, worksheet):
    if worksheet is None:
        st.error("Não foi possível acessar a planilha.")
        return
    try:
        worksheet.append_row(row)
        st.success("Dados registrados com sucesso!")
    except Exception as e:
        st.error(f"Erro ao adicionar dados: {e}")

def process_vendas(df):
    if not df.empty:
        for col in ['Cartão', 'Dinheiro', 'Pix']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['Total'] = df['Cartão'].fillna(0) + df['Dinheiro'].fillna(0) + df['Pix'].fillna(0)
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        df['Ano'] = df['Data'].dt.year
        df['Mês'] = df['Data'].dt.month
        df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
    return df

def process_compras(df):
    if not df.empty:
        for col in ['Pão', 'Frios', 'Bebidas']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['Total'] = df[['Pão', 'Frios', 'Bebidas']].sum(axis=1)
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        df['Ano'] = df['Data'].dt.year
        df['Mês'] = df['Data'].dt.month
        df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
    return df

def main():
    tab1, tab2, tab3, tab4 = st.tabs(["Cadastrar", "Análise de Vendas", "Análise de Compras", "Estatísticas"])

    with st.sidebar:
        st.header("🔍 Filtros")
        df_vendas_raw, _ = read_google_sheet('Vendas')
        df_vendas = process_vendas(df_vendas_raw.copy()) if not df_vendas_raw.empty else pd.DataFrame()
        df_compras_raw, _ = read_google_sheet('Compras')
        df_compras = process_compras(df_compras_raw.copy()) if not df_compras_raw.empty else pd.DataFrame()

        anos_vendas = df_vendas['Ano'].unique() if 'Ano' in df_vendas.columns else []
        anos_compras = df_compras['Ano'].unique() if 'Ano' in df_compras.columns else []
        anos = sorted(set(anos_vendas).union(anos_compras))
        selected_anos = st.multiselect("Ano(s):", anos, default=anos)
        meses = sorted(set(df_vendas['Mês'].unique()).union(df_compras['Mês'].unique()))
        selected_meses = st.multiselect("Mês(es):", meses, default=meses)

    with tab1:
        st.subheader("Registrar Nova Venda")
        with st.form("venda_form"):
            data_venda = st.date_input("Data da Venda", datetime.now())
            c1, c2, c3 = st.columns(3)
            with c1:
                cartao = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f")
            with c2:
                dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f")
            with c3:
                pix = st.number_input("Pix (R$)", min_value=0.0, format="%.2f")
            if st.form_submit_button("Registrar Venda"):
                if cartao + dinheiro + pix > 0:
                    formatted = data_venda.strftime('%d/%m/%Y')
                    _, worksheet = read_google_sheet('Vendas')
                    add_data_to_sheet([formatted, cartao, dinheiro, pix], worksheet)
                else:
                    st.warning("Informe ao menos um valor de venda.")

        st.subheader("Registrar Nova Compra")
        with st.form("compra_form"):
            data_compra = st.date_input("Data da Compra", datetime.now())
            c1, c2, c3 = st.columns(3)
            with c1:
                pao = st.number_input("Pão (R$)", min_value=0.0, format="%.2f")
            with c2:
                frios = st.number_input("Frios (R$)", min_value=0.0, format="%.2f")
            with c3:
                bebidas = st.number_input("Bebidas (R$)", min_value=0.0, format="%.2f")
            if st.form_submit_button("Registrar Compra"):
                if pao + frios + bebidas > 0:
                    formatted = data_compra.strftime('%d/%m/%Y')
                    _, worksheet = read_google_sheet('Compras')
                    add_data_to_sheet([formatted, pao, frios, bebidas], worksheet)
                else:
                    st.warning("Informe ao menos um valor de compra.")

    with tab2:
        st.header("Análise de Vendas")
        df = df_vendas[(df_vendas['Ano'].isin(selected_anos)) & (df_vendas['Mês'].isin(selected_meses))]
        if not df.empty:
            st.dataframe(df[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']], use_container_width=True)
            st.subheader("Métodos de Pagamento")
            pagamento = pd.DataFrame({
                'Método': ['Cartão', 'Dinheiro', 'Pix'],
                'Valor': [df['Cartão'].sum(), df['Dinheiro'].sum(), df['Pix'].sum()]
            })
            st.altair_chart(
                alt.Chart(pagamento).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta("Valor:Q"),
                    color=alt.Color("Método:N"),
                    tooltip=["Método", "Valor"]
                ).properties(width=700, height=400),
                use_container_width=True
            )

            st.subheader("Acúmulo de Capital")
            df = df.sort_values('Data')
            df['Total Acumulado'] = df['Total'].cumsum()
            st.altair_chart(
                alt.Chart(df).mark_line(point=True).encode(
                    x='Data:T',
                    y='Total Acumulado:Q',
                    tooltip=['DataFormatada', 'Total Acumulado']
                ).properties(width=700, height=400),
                use_container_width=True
            )

    with tab3:
        st.header("Análise de Compras")
        df = df_compras[(df_compras['Ano'].isin(selected_anos)) & (df_compras['Mês'].isin(selected_meses))]
        if not df.empty:
            st.dataframe(df[['DataFormatada', 'Pão', 'Frios', 'Bebidas', 'Total']], use_container_width=True)
            st.subheader("Categorias de Compra")
            categorias = pd.DataFrame({
                'Categoria': ['Pão', 'Frios', 'Bebidas'],
                'Valor': [df['Pão'].sum(), df['Frios'].sum(), df['Bebidas'].sum()]
            })
            st.altair_chart(
                alt.Chart(categorias).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta("Valor:Q"),
                    color=alt.Color("Categoria:N"),
                    tooltip=["Categoria", "Valor"]
                ).properties(width=700, height=400),
                use_container_width=True
            )

            st.subheader("Gastos Acumulados")
            df = df.sort_values('Data')
            df['Total Acumulado'] = df['Total'].cumsum()
            st.altair_chart(
                alt.Chart(df).mark_line(point=True).encode(
                    x='Data:T',
                    y='Total Acumulado:Q',
                    tooltip=['DataFormatada', 'Total Acumulado']
                ).properties(width=700, height=400),
                use_container_width=True
            )

    with tab4:
        st.header("📈 Estatísticas Gerais")
        df_v = df_vendas[(df_vendas['Ano'].isin(selected_anos)) & (df_vendas['Mês'].isin(selected_meses))]
        if not df_v.empty:
            df_v['DiaSemana'] = df_v['Data'].dt.day_name()
            dia_mais = df_v.groupby('DiaSemana')['Total'].mean().idxmax()
            dia_menos = df_v.groupby('DiaSemana')['Total'].mean().idxmin()
            dias_trabalhados = df_v['Data'].dt.date.nunique()

            st.markdown(f"**Dia da semana com mais vendas (média):** {dia_mais}")
            st.markdown(f"**Dia da semana com menos vendas (média):** {dia_menos}")
            st.markdown(f"**Dias trabalhados no período:** {dias_trabalhados}")

if __name__ == "__main__":
    main()
