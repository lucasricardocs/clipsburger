import streamlit as st
import gspread
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="wide")

def read_google_sheet():
    """Função para ler os dados da planilha Google Sheets"""
    try:
        # Definindo os escopos corretos para o Google Sheets
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Carregando as credenciais do secrets do Streamlit
        credentials_dict = st.secrets["google_credentials"]
        
        # Crie as credenciais a partir do dicionário do secrets com os escopos corretos
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        
        # Autenticação com o Google Sheets
        gc = gspread.authorize(creds)
        
        # ID da planilha e nome da aba
        spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
        worksheet_name = 'Vendas'
        
        # Abrindo a planilha e a aba
        try:
            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            
            # Lendo os dados da planilha
            rows = worksheet.get_all_records()
            
            # Convertendo para DataFrame
            df = pd.DataFrame(rows)
            
            return df, worksheet
            
        except SpreadsheetNotFound:
            st.error(f"Planilha com ID {spreadsheet_id} não encontrada. Verifique o ID e as permissões.")
            return pd.DataFrame(), None
            
    except Exception as e:
        st.error(f"Erro de autenticação: {str(e)}")
        return pd.DataFrame(), None

def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet):
    """Função para adicionar dados à planilha Google Sheets"""
    try:
        # Preparar os dados para inserção
        new_row = [date, float(cartao), float(dinheiro), float(pix)]
        
        # Adicionar a nova linha à planilha
        worksheet.append_row(new_row)
        
        # Mostrar mensagem de sucesso
        st.success("Dados registrados com sucesso!")
        
    except Exception as e:
        st.error(f"Erro ao adicionar dados: {str(e)}")

def main():
    st.title("📊 Sistema de Registro de Vendas")
    
    # Criar abas
    tab1, tab2 = st.tabs(["Registrar Venda", "Visualizar Vendas"])
    
    with tab1:
        st.header("Registrar Nova Venda")
        
        # Formulário para inserção de dados
        with st.form("venda_form"):
            # Campo de data
            data = st.date_input("Data", datetime.now())
            
            # Campos para valores financeiros
            col1, col2, col3 = st.columns(3)
            
            with col1:
                cartao = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f")
            
            with col2:
                dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f")
            
            with col3:
                pix = st.number_input("PIX (R$)", min_value=0.0, format="%.2f")
            
            # Calcular e mostrar o total
            total = cartao + dinheiro + pix
            st.markdown(f"**Total da venda: R$ {total:.2f}**")
            
            # Botão para enviar os dados
            submitted = st.form_submit_button("Registrar Venda")
            
            if submitted:
                # Verificar se há pelo menos um valor
                if cartao > 0 or dinheiro > 0 or pix > 0:
                    # Formatar a data para string
                    formatted_date = data.strftime('%d/%m/%Y')
                    
                    # Ler a planilha para obter o objeto worksheet
                    _, worksheet = read_google_sheet()
                    
                    if worksheet:
                        # Adicionar os dados à planilha
                        add_data_to_sheet(formatted_date, cartao, dinheiro, pix, worksheet)
                else:
                    st.warning("Pelo menos um valor de venda deve ser maior que zero.")
    
    with tab2:
        st.header("Histórico de Vendas")
        
        # Botão para atualizar os dados
        if st.button("Atualizar Dados"):
            with st.spinner("Carregando dados..."):
                # Carregar os dados da planilha
                df, _ = read_google_sheet()
                
                if not df.empty:
                    # Converter colunas numéricas
                    for col in ['Cartão', 'Dinheiro', 'Pix']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # Calcular total por linha
                    df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']
                    
                    # Exibir os dados em uma tabela interativa
                    st.dataframe(df, use_container_width=True)
                    
                    # Exibir estatísticas
                    st.subheader("Resumo Financeiro")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Cartão", f"R$ {df['Cartão'].sum():.2f}")
                    
                    with col2:
                        st.metric("Total Dinheiro", f"R$ {df['Dinheiro'].sum():.2f}")
                    
                    with col3:
                        st.metric("Total PIX", f"R$ {df['Pix'].sum():.2f}")
                    
                    with col4:
                        st.metric("Total Geral", f"R$ {df['Total'].sum():.2f}")
                    
                    # Criar gráficos
                    st.subheader("Visualização dos Dados")
                    
                    # Gráfico de pizza para métodos de pagamento
                    payment_data = {
                        'Método': ['Cartão', 'Dinheiro', 'PIX'],
                        'Valor': [df['Cartão'].sum(), df['Dinheiro'].sum(), df['Pix'].sum()]
                    }
                    payment_df = pd.DataFrame(payment_data)
                    
                    st.write("**Distribuição por Método de Pagamento**")
                    
                    # Usando o chart nativo do Streamlit para o gráfico de pizza
                    st.pie_chart(payment_df.set_index('Método'))
                    
                else:
                    st.info("Não há dados para exibir ou houve um problema ao carregar a planilha.")

if __name__ == "__main__":
    main()
