import streamlit as st
import gspread
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials

# Configuração da página
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="wide")

def read_google_sheet():
    """Função para ler os dados da planilha Google Sheets"""
    # Carregando as credenciais do secrets do Streamlit
    credentials_dict = st.secrets["google_credentials"]
    
    # Crie as credenciais a partir do dicionário do secrets
    creds = Credentials.from_service_account_info(credentials_dict)
    
    # Autenticação com o Google Sheets
    gc = gspread.authorize(creds)
    
    # ID da planilha e nome da aba
    spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
    worksheet_name = 'Vendas'
    
    # Abrindo a planilha e a aba
    worksheet = gc.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    
    # Lendo os dados da planilha
    rows = worksheet.get_all_records()
    
    # Convertendo para DataFrame
    df = pd.DataFrame(rows)
    
    return df, worksheet

def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet):
    """Função para adicionar dados à planilha Google Sheets"""
    # Preparar os dados para inserção
    new_row = [date, float(cartao), float(dinheiro), float(pix)]
    
    # Adicionar a nova linha à planilha
    worksheet.append_row(new_row)
    
    # Mostrar mensagem de sucesso
    st.success("Dados registrados com sucesso!")

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
                    try:
                        # Formatar a data para string
                        formatted_date = data.strftime('%d/%m/%Y')
                        
                        # Ler a planilha para obter o objeto worksheet
                        _, worksheet = read_google_sheet()
                        
                        # Adicionar os dados à planilha
                        add_data_to_sheet(formatted_date, cartao, dinheiro, pix, worksheet)
                    except Exception as e:
                        st.error(f"Erro ao registrar venda: {e}")
                else:
                    st.warning("Pelo menos um valor de venda deve ser maior que zero.")
    
    with tab2:
        st.header("Histórico de Vendas")
        
        # Botão para atualizar os dados
        if st.button("Atualizar Dados"):
            with st.spinner("Carregando dados..."):
                try:
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
                        chart = {
                            'mark': {'type': 'arc', 'innerRadius': 50},
                            'encoding': {
                                'theta': {'field': 'Valor', 'type': 'quantitative'},
                                'color': {'field': 'Método', 'type': 'nominal'}
                            }
                        }
                        st.vega_lite_chart(payment_df, chart, use_container_width=True)
                        
                    else:
                        st.info("Não há dados para exibir.")
                
                except Exception as e:
                    st.error(f"Erro ao carregar dados: {e}")

if __name__ == "__main__":
    main()
