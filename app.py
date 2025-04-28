import streamlit as st
import pandas as pd
import altair as alt
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Configuração do Google Sheets
SPREADSHEET_ID = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
RANGE_NAME = 'Vendas!A:D'

# Função para ler os dados da planilha do Google
def read_google_sheet():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_credentials"], 
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    
    service = build("sheets", "v4", credentials=credentials)
    sheet = service.spreadsheets()

    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get("values", [])
    
    if not values:
        st.error("Nenhum dado encontrado.")
        return pd.DataFrame()
    
    # Convertendo para DataFrame
    df = pd.DataFrame(values[1:], columns=values[0])
    df['Data'] = pd.to_datetime(df['Data'], format="%d/%m/%Y")
    
    return df

# Função para cadastrar novos dados
def create_form():
    with st.form(key="form"):
        data = st.date_input("Data")
        cartao = st.number_input("Cartão", min_value=0)
        dinheiro = st.number_input("Dinheiro", min_value=0)
        pix = st.number_input("Pix", min_value=0)

        submit_button = st.form_submit_button("Cadastrar")
        
        if submit_button:
            # Adicionar os dados no Google Sheets
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["google_credentials"],
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            service = build("sheets", "v4", credentials=credentials)
            sheet = service.spreadsheets()
            
            data_list = [[data.strftime("%d/%m/%Y"), cartao, dinheiro, pix]]
            sheet.values().append(
                spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME, 
                valueInputOption="RAW", body={"values": data_list}
            ).execute()

            st.success("Dados cadastrados com sucesso!")

# Funções para criar os gráficos com Altair
def create_payment_distribution_graph(df):
    df_melted = df.melt(id_vars=['Data'], value_vars=['Cartao', 'Dinheiro', 'Pix'], 
                        var_name='Metodo de Pagamento', value_name='Valor')

    chart = alt.Chart(df_melted).mark_bar().encode(
        x='Data:T',
        y='sum(Valor):Q',
        color='Metodo de Pagamento:N',
        tooltip=['Data:T', 'Metodo de Pagamento:N', 'sum(Valor):Q']
    ).properties(
        title='Distribuição das Vendas por Método de Pagamento'
    )
    
    return chart

def create_monthly_sales_graph(df):
    df['Ano-Mes'] = df['Data'].dt.to_period('M')
    df_melted = df.melt(id_vars=['Ano-Mes'], value_vars=['Cartao', 'Dinheiro', 'Pix'], 
                        var_name='Metodo de Pagamento', value_name='Valor')

    chart = alt.Chart(df_melted).mark_bar().encode(
        x='Ano-Mes:N',
        y='sum(Valor):Q',
        color='Metodo de Pagamento:N',
        tooltip=['Ano-Mes:N', 'Metodo de Pagamento:N', 'sum(Valor):Q']
    ).properties(
        title='Vendas Totais por Mês'
    ).configure_axis(
        labelAngle=-45
    )

    return chart

def create_payment_comparison_graph(df):
    df_total = df[['Cartao', 'Dinheiro', 'Pix']].sum().reset_index()
    df_total.columns = ['Metodo de Pagamento', 'Valor Total']

    chart = alt.Chart(df_total).mark_bar().encode(
        x='Valor Total:Q',
        y='Metodo de Pagamento:N',
        tooltip=['Metodo de Pagamento:N', 'Valor Total:Q']
    ).properties(
        title='Comparação de Métodos de Pagamento'
    )

    return chart

def create_sales_over_time_graph(df):
    df_melted = df.melt(id_vars=['Data'], value_vars=['Cartao', 'Dinheiro', 'Pix'], 
                        var_name='Metodo de Pagamento', value_name='Valor')

    chart = alt.Chart(df_melted).mark_line().encode(
        x='Data:T',
        y='sum(Valor):Q',
        color='Metodo de Pagamento:N',
        tooltip=['Data:T', 'Metodo de Pagamento:N', 'sum(Valor):Q']
    ).properties(
        title='Vendas por Método de Pagamento ao Longo do Tempo'
    )

    return chart

def create_accumulated_sales_graph(df):
    df['capital_acumulado'] = df['Cartao'] + df['Dinheiro'] + df['Pix']
    df['capital_acumulado'] = df.groupby('Data')['capital_acumulado'].cumsum()

    chart = alt.Chart(df).mark_line().encode(
        x='Data:T',
        y='capital_acumulado:Q',
        tooltip=['Data:T', 'capital_acumulado:Q']
    ).properties(
        title='Capital Acumulado'
    )

    return chart

def create_payment_revenue_graph(df):
    df_melted = df.melt(id_vars=['Data'], value_vars=['Cartao', 'Dinheiro', 'Pix'], 
                        var_name='Metodo de Pagamento', value_name='Valor')

    chart = alt.Chart(df_melted).mark_area().encode(
        x='Data:T',
        y='sum(Valor):Q',
        color='Metodo de Pagamento:N',
        tooltip=['Data:T', 'Metodo de Pagamento:N', 'sum(Valor):Q']
    ).properties(
        title='Receita por Método de Pagamento'
    ).configure_mark(
        opacity=0.5
    )

    return chart

# Função principal para mostrar a interface
def main():
    st.title("Controle de Vendas")
    
    # Seleção de Mês e Ano
    st.sidebar.header("Filtrar por Data")
    mes = st.sidebar.selectbox("Mês", range(1, 13))
    ano = st.sidebar.selectbox("Ano", range(2020, 2031))
    
    # Armazenando mês e ano em variáveis de sessão
    st.session_state.mes = mes
    st.session_state.ano = ano

    # Formulário de Cadastro
    create_form()
    
    # Lendo os dados da planilha
    df = read_google_sheet()

    if not df.empty:
        # Mostrar os gráficos
        st.subheader(f"Gráfico de Vendas - {mes}/{ano}")
        
        # Gráficos
        st.altair_chart(create_payment_distribution_graph(df), use_container_width=True)
        st.altair_chart(create_monthly_sales_graph(df), use_container_width=True)
        st.altair_chart(create_payment_comparison_graph(df), use_container_width=True)
        st.altair_chart(create_sales_over_time_graph(df), use_container_width=True)
        st.altair_chart(create_accumulated_sales_graph(df), use_container_width=True)
        st.altair_chart(create_payment_revenue_graph(df), use_container_width=True)

if __name__ == "__main__":
    main()
