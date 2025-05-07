import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="centered")

def read_google_sheet():
    """Função para ler os dados da planilha Google Sheets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet_id = st.secrets["spreadsheet_id"]  # Movido para secrets.toml
        worksheet_name = 'Vendas'
        
        try:
            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            rows = worksheet.get_all_records()
            
            # Verificar se há dados
            if not rows:
                return pd.DataFrame(), worksheet
                
            df = pd.DataFrame(rows)
            return df, worksheet
            
        except SpreadsheetNotFound:
            st.error(f"Planilha '{worksheet_name}' não encontrada!")
            return pd.DataFrame(), None
            
    except Exception as e:
        st.error(f"Erro ao acessar Google Sheets: {str(e)}")
        return pd.DataFrame(), None

def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet):
    """Função para adicionar dados à planilha Google Sheets"""
    if worksheet is None:
        st.error("Planilha não disponível")
        return False
        
    try:
        new_row = {
            'Data': date.strftime('%d/%m/%Y') if isinstance(date, datetime) else date,
            'Cartão': float(cartao),
            'Dinheiro': float(dinheiro),
            'Pix': float(pix)
        }
        worksheet.append_row(list(new_row.values()))
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar dados: {str(e)}")
        return False

def process_data(df):
    """Função para processar e preparar os dados"""
    if df.empty:
        return df
    
    # Verificar colunas numéricas
    for col in ['Cartão', 'Dinheiro', 'Pix']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Calcular total
    if all(col in df.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
        df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']
    
    # Processar datas
    if 'Data' in df.columns:
        try:
            # Tentar múltiplos formatos de data
            for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d']:
                try:
                    df['Data'] = pd.to_datetime(df['Data'], format=fmt, errors='raise')
                    break
                except ValueError:
                    continue
            
            if pd.api.types.is_datetime64_any_dtype(df['Data']):
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['MêsNome'] = df['Data'].dt.strftime('%B')
                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
            else:
                st.warning("Formato de data não reconhecido")
                
        except Exception as e:
            st.error(f"Erro ao processar datas: {str(e)}")
    
    return df

def show_register_tab():
    """Aba de registro de vendas"""
    st.header("Registrar Nova Venda")
    
    with st.form("venda_form"):
        data = st.date_input("Data", datetime.now())
        col1, col2, col3 = st.columns(3)
        with col1:
            cartao = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f", step=0.01)
        with col2:
            dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f", step=0.01)
        with col3:
            pix = st.number_input("PIX (R$)", min_value=0.0, format="%.2f", step=0.01)
        
        total = cartao + dinheiro + pix
        st.markdown(f"**Total da venda: R$ {total:.2f}**")
        
        submitted = st.form_submit_button("Registrar Venda")
        if submitted:
            if total > 0:
                df, worksheet = read_google_sheet()
                if add_data_to_sheet(data, cartao, dinheiro, pix, worksheet):
                    st.success("Venda registrada com sucesso!")
                    st.balloons()
                    time.sleep(1)
                    st.experimental_rerun()
            else:
                st.warning("Pelo menos um valor deve ser maior que zero")

def show_analysis_tab():
    """Aba de análise de dados"""
    st.header("Análise Detalhada de Vendas")
    
    with st.spinner("Carregando dados..."):
        df_raw, _ = read_google_sheet()
        df = process_data(df_raw.copy())
    
    if df.empty:
        st.info("Nenhum dado disponível para análise")
        return
    
    # Filtros na sidebar
    with st.sidebar:
        st.subheader("Filtros")
        
        # Filtro de Ano
        available_years = sorted(df['Ano'].unique()) if 'Ano' in df.columns else []
        selected_years = st.multiselect(
            "Ano(s)",
            options=available_years,
            default=available_years[-1:] if available_years else []
        )
        
        # Filtro de Mês
        available_months = []
        if selected_years and 'Mês' in df.columns:
            available_months = sorted(df[df['Ano'].isin(selected_years)]['Mês'].unique())
        
        month_names = {m: datetime(2020, m, 1).strftime('%B') for m in available_months}
        month_options = [f"{m} - {month_names[m]}" for m in available_months]
        
        selected_months_str = st.multiselect(
            "Mês(es)",
            options=month_options,
            default=month_options
        )
        selected_months = [int(m.split(" - ")[0]) for m in selected_months_str]
    
    # Aplicar filtros
    df_filtered = df
    if selected_years and 'Ano' in df.columns:
        df_filtered = df_filtered[df_filtered['Ano'].isin(selected_years)]
    if selected_months and 'Mês' in df.columns:
        df_filtered = df_filtered[df_filtered['Mês'].isin(selected_months)]
    
    # Visualização dos dados
    st.subheader("Dados Filtrados")
    cols_to_show = [c for c in ['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total'] if c in df_filtered.columns]
    st.dataframe(df_filtered[cols_to_show], use_container_width=True, height=300)
    
    # Gráficos
    if not df_filtered.empty:
        st.subheader("Distribuição por Método de Pagamento")
        if all(col in df_filtered.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
            payment_data = pd.DataFrame({
                'Método': ['Cartão', 'Dinheiro', 'PIX'],
                'Valor': [
                    df_filtered['Cartão'].sum(),
                    df_filtered['Dinheiro'].sum(),
                    df_filtered['Pix'].sum()
                ]
            })
            
            pie_chart = alt.Chart(payment_data).mark_arc().encode(
                theta='Valor',
                color='Método',
                tooltip=['Método', 'Valor']
            ).properties(height=300)
            
            st.altair_chart(pie_chart, use_container_width=True)
        
        st.subheader("Vendas Diárias")
        if 'Data' in df_filtered.columns and 'Total' in df_filtered.columns:
            line_chart = alt.Chart(df_filtered).mark_line(point=True).encode(
                x='Data:T',
                y='Total',
                tooltip=['DataFormatada', 'Total']
            ).properties(height=400)
            
            st.altair_chart(line_chart, use_container_width=True)

def main():
    st.title("📊 Sistema de Registro de Vendas")
    
    tab1, tab2 = st.tabs(["Registrar Venda", "Análise Detalhada"])
    
    with tab1:
        show_register_tab()
    
    with tab2:
        show_analysis_tab()

if __name__ == "__main__":
    main()
