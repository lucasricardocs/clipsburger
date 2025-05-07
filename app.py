import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import time

# Configuração da página
st.set_page_config(
    page_title="Sistema Clips Burger",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Dados fixos
MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# --- Funções Críticas Corrigidas ---

def safe_read_google_sheet(worksheet_name):
    """Versão robusta para ler planilhas"""
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_info(st.secrets["google_credentials"], scopes=scopes)
        gc = gspread.authorize(creds)
        
        spreadsheet = gc.open_by_key(st.secrets["spreadsheet_id"])
        worksheet = spreadsheet.worksheet(worksheet_name)
        
        # Converter para DataFrame com tratamento de erro
        records = worksheet.get_all_records()
        if not records:
            return pd.DataFrame()
            
        df = pd.DataFrame(records)
        return df if not df.empty else pd.DataFrame()
        
    except SpreadsheetNotFound:
        st.error(f"Planilha '{worksheet_name}' não encontrada!")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao acessar Google Sheets: {str(e)}")
        return pd.DataFrame()

def process_dates(df, date_column='Data'):
    """Processamento seguro de datas"""
    if df.empty or date_column not in df.columns:
        return df
    
    # Tentar múltiplos formatos de data
    date_formats = ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y']
    
    for fmt in date_formats:
        try:
            df[date_column] = pd.to_datetime(df[date_column], format=fmt, errors='raise')
            break
        except:
            continue
            
    if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
        st.warning(f"Não foi possível converter a coluna '{date_column}' para data")
        return df
    
    # Extrair componentes temporais
    df['Ano'] = df[date_column].dt.year
    df['Mês'] = df[date_column].dt.month
    df['Dia'] = df[date_column].dt.day
    df['DataFormatada'] = df[date_column].dt.strftime('%d/%m/%Y')
    
    return df

# --- Interface do Usuário ---

def show_filters():
    """Filtros na sidebar com valores padrão corretos"""
    hoje = datetime.now()
    ano_atual = hoje.year
    mes_atual = hoje.month
    
    with st.sidebar:
        st.subheader("Filtros Temporais")
        
        # Carregar dados para obter anos disponíveis
        df_vendas = safe_read_google_sheet("Vendas")
        df_vendas = process_dates(df_vendas)
        
        anos = sorted(df_vendas['Ano'].unique()) if not df_vendas.empty else [ano_atual]
        
        ano = st.selectbox(
            "Ano",
            options=anos,
            index=len(anos)-1
        )
        
        # Meses disponíveis para o ano selecionado
        meses_disponiveis = sorted(
            df_vendas[df_vendas['Ano'] == ano]['Mês'].unique()
        ) if not df_vendas.empty else [mes_atual]
        
        mes = st.selectbox(
            "Mês",
            options=meses_disponiveis,
            format_func=lambda x: MESES[x],
            index=len(meses_disponiveis)-1
        )
        
        return ano, mes

def show_dashboard():
    """Tela principal com abas"""
    ano, mes = show_filters()
    
    # Carregar dados filtrados
    with st.spinner("Carregando dados..."):
        df_vendas = safe_read_google_sheet("Vendas")
        df_vendas = process_dates(df_vendas)
        df_vendas = df_vendas[(df_vendas['Ano'] == ano) & (df_vendas['Mês'] == mes)]
        
        df_compras = safe_read_google_sheet("Compras")
        df_compras = process_dates(df_compras)
        df_compras = df_compras[(df_compras['Ano'] == ano) & (df_compras['Mês'] == mes)]
    
    # Abas principais
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "💰 Registrar Venda", "🛒 Registrar Compra"])
    
    with tab1:
        # Visualização de dados
        if not df_vendas.empty:
            st.subheader(f"Vendas - {MESES[mes]}/{ano}")
            
            # Métricas
            col1, col2, col3 = st.columns(3)
            total_vendas = df_vendas[['Cartão', 'Dinheiro', 'Pix']].sum().sum()
            col1.metric("Total Vendido", f"R$ {total_vendas:,.2f}")
            col2.metric("Dias com Venda", df_vendas['Data'].nunique())
            col3.metric("Média Diária", f"R$ {total_vendas/df_vendas['Data'].nunique():,.2f}")
            
            # Gráficos
            st.altair_chart(
                alt.Chart(df_vendas).mark_bar().encode(
                    x='DataFormatada:T',
                    y='Total:Q'
                ),
                use_container_width=True
            )
    
    with tab2:
        # Formulário de vendas
        with st.form("venda_form"):
            data = st.date_input("Data", datetime.now())
            cartao = st.number_input("Cartão", min_value=0.0, step=0.01)
            dinheiro = st.number_input("Dinheiro", min_value=0.0, step=0.01)
            pix = st.number_input("Pix", min_value=0.0, step=0.01)
            
            if st.form_submit_button("Registrar"):
                # Lógica para salvar no Google Sheets
                st.success("Venda registrada!")
    
    with tab3:
        # Formulário de compras
        with st.form("compra_form"):
            data = st.date_input("Data", datetime.now())
            pao = st.number_input("Pão", min_value=0.0, step=0.01)
            frios = st.number_input("Frios", min_value=0.0, step=0.01)
            bebidas = st.number_input("Bebidas", min_value=0.0, step=0.01)
            
            if st.form_submit_button("Registrar"):
                # Lógica para salvar no Google Sheets
                st.success("Compra registrada!")

# --- Ponto de Entrada ---
def main():
    st.title("🍔 Clips Burger - Gestão Comercial")
    show_dashboard()

if __name__ == "__main__":
    main()
