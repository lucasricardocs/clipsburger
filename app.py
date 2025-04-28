import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
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
                    
                    # Criar gráficos com Altair
                    st.subheader("Visualização dos Dados")
                    
                    # Preparar dados para o gráfico de pizza
                    payment_data = pd.DataFrame({
                        'Método': ['Cartão', 'Dinheiro', 'PIX'],
                        'Valor': [df['Cartão'].sum(), df['Dinheiro'].sum(), df['Pix'].sum()]
                    })
                    
                    # Gráfico de pizza simplificado com Altair
                    st.write("**Distribuição por Método de Pagamento**")
                    
                    # Criando o gráfico de donut com Altair
                    base = alt.Chart(payment_data).encode(
                        theta=alt.Theta("Valor:Q", stack=True),
                        color=alt.Color("Método:N", legend=alt.Legend(title="Método de Pagamento")),
                        tooltip=["Método", "Valor"]
                    )
                    
                    pie = base.mark_arc(innerRadius=50, outerRadius=100)
                    text = base.mark_text(radius=130, size=14).encode(text="Método:N")
                    
                    donut_chart = (pie + text).properties(
                        width=400,
                        height=400,
                        title="Distribuição por Método de Pagamento"
                    )
                    
                    st.altair_chart(donut_chart, use_container_width=True)
                    
                    # Adicionar gráfico de barras com os totais diários
                    if 'Data' in df.columns:
                        st.subheader("Vendas por Data")
                        
                        # Agrupar por data e somar os valores
                        daily_sales = df.groupby('Data').sum().reset_index()
                        
                        # Convertendo para formato longo (tidy) para Altair
                        daily_sales_long = pd.melt(
                            daily_sales, 
                            id_vars=['Data'], 
                            value_vars=['Cartão', 'Dinheiro', 'Pix'],
                            var_name='Método',
                            value_name='Valor'
                        )
                        
                        # Criando o gráfico de barras empilhadas com Altair
                        bar_chart = alt.Chart(daily_sales_long).mark_bar().encode(
                            x=alt.X('Data:N', title='Data', sort=None),
                            y=alt.Y('sum(Valor):Q', title='Valor (R$)'),
                            color=alt.Color('Método:N', legend=alt.Legend(title="Método de Pagamento")),
                            tooltip=['Data', 'Método', 'Valor']
                        ).properties(
                            title='Vendas Diárias por Método de Pagamento'
                        )
                        
                        st.altair_chart(bar_chart, use_container_width=True)
                        
                        # Adicionar gráfico de linha para tendência de vendas totais
                        line_chart = alt.Chart(daily_sales).mark_line(point=True).encode(
                            x=alt.X('Data:N', title='Data', sort=None),
                            y=alt.Y('Total:Q', title='Total de Vendas (R$)'),
                            tooltip=['Data', 'Total']
                        ).properties(
                            title='Tendência de Vendas Totais'
                        )
                        
                        st.altair_chart(line_chart, use_container_width=True)
                    
                else:
                    st.info("Não há dados para exibir ou houve um problema ao carregar a planilha.")

if __name__ == "__main__":
    main()
