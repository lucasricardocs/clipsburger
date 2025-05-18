import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página com layout centered
st.set_page_config(
    page_title="Sistema de Registro de Vendas", 
    layout="centered",
    initial_sidebar_state="expanded"
)

@st.cache_data(ttl=300)
def read_google_sheet():
    """Função para ler os dados da planilha Google Sheets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 
                 'https://www.googleapis.com/auth/spreadsheets.readonly', 
                 'https://www.googleapis.com/auth/drive.readonly']
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
        worksheet_name = 'Vendas'
        try:
            with st.spinner("Conectando à planilha..."):
                spreadsheet = gc.open_by_key(spreadsheet_id)
                worksheet = spreadsheet.worksheet(worksheet_name)
                rows = worksheet.get_all_records()
                df = pd.DataFrame(rows)
                return df, worksheet
        except SpreadsheetNotFound:
            st.error(f"Planilha com ID {spreadsheet_id} não encontrada.")
            return pd.DataFrame(), None
    except Exception as e:
        st.error(f"Erro de autenticação: {e}")
        return pd.DataFrame(), None

def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet):
    """Função para adicionar dados à planilha Google Sheets"""
    if worksheet is None:
        st.error("Não foi possível acessar a planilha.")
        return False
    try:
        with st.spinner("Registrando venda..."):
            new_row = [date, float(cartao), float(dinheiro), float(pix)]
            worksheet.append_row(new_row)
            st.toast("Venda registrada com sucesso!", icon="✅")
            return True
    except Exception as e:
        st.error(f"Erro ao adicionar dados: {e}")
        return False

@st.cache_data(ttl=300)
def process_data(df_raw):
    """Função para processar e preparar os dados"""
    if df_raw.empty:
        return pd.DataFrame()
    
    df = df_raw.copy()
    
    # Processamento dos valores monetários
    for col in ['Cartão', 'Dinheiro', 'Pix']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Cálculo do total
    df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']
    
    # Processamento de datas
    if 'Data' in df.columns:
        try:
            df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
            df = df.dropna(subset=['Data'])
            
            if not df.empty:
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                df['DiaSemana'] = df['Data'].dt.day_name().map({
                    'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
                    'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
                })
        except Exception as e:
            st.warning(f"Erro ao processar datas: {e}")
    
    return df

def create_kpi_metrics(df):
    """Criar métricas KPI a partir do DataFrame"""
    return {
        'total_vendas': len(df),
        'total_faturamento': df['Total'].sum(),
        'media_por_venda': df['Total'].mean() if len(df) > 0 else 0,
        'maior_venda': df['Total'].max() if len(df) > 0 else 0,
    }

def main():
    st.title("📊 Sistema de Registro de Vendas")
    df_raw, worksheet = read_google_sheet()
    df = process_data(df_raw)
    
    tab1, tab2, tab3 = st.tabs(["📝 Registrar Venda", "📈 Análise Detalhada", "📊 Estatísticas"])
    
    with tab1:
        with st.form("venda_form"):
            data = st.date_input("📅 Data da Venda", datetime.now())
            cartao = st.number_input("💳 Cartão (R$)", min_value=0.0, format="%.2f")
            dinheiro = st.number_input("💵 Dinheiro (R$)", min_value=0.0, format="%.2f")
            pix = st.number_input("📱 PIX (R$)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("💾 Registrar Venda"):
                if (total := cartao + dinheiro + pix) > 0:
                    if add_data_to_sheet(data.strftime('%d/%m/%Y'), cartao, dinheiro, pix, worksheet):
                        st.cache_data.clear()
                        st.rerun()
                else:
                    st.warning("O valor total deve ser maior que zero")

    with st.sidebar:
        st.header("🔍 Filtros")
        anos = st.multiselect("Ano(s)", options=df['Ano'].unique())
        df_filtered = df[df['Ano'].isin(anos)] if anos else df

    with tab2:
        if not df_filtered.empty:
            # Gráfico de Acumulação Corrigido
            df_accumulated = df_filtered.sort_values('Data').assign(
                Total_Acumulado=lambda x: x['Total'].cumsum()
            )
            acumulado_chart = alt.Chart(df_accumulated).mark_line().encode(
                x=alt.X('Data:T', title='Data'),
                y=alt.Y('Total_Acumulado:Q', title='Capital Acumulado (R$)'),
                tooltip=['DataFormatada:T', 'Total_Acumulado:Q']
            ).properties(height=400)
            st.altair_chart(acumulado_chart, use_container_width=True)

    with tab3:
        if not df_filtered.empty:
            # Histograma Corrigido
            hist_chart = alt.Chart(df_filtered).mark_bar().encode(
                alt.X("Total:Q", bin=True, title="Valor da Venda"),
                y='count()',
                tooltip=['count()']
            ).properties(height=300, title="Distribuição de Valores")
            st.altair_chart(hist_chart)
            
            # Pizza Corrigido
            payment_data = df_filtered[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
            pizza_chart = alt.Chart(payment_data.rename(columns={'index':'Método', 0:'Total'})).mark_arc().encode(
                theta='Total:Q',
                color='Método:N',
                tooltip=['Método', 'Total']
            ).properties(height=300)
            st.altair_chart(pizza_chart)

if __name__ == "__main__":
    main()
