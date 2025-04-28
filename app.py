import streamlit as st
import pandas as pd
import altair as alt
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Função para autenticar e acessar o Google Sheets
def authenticate_google_sheets(credentials_file):
    creds = Credentials.from_service_account_file(credentials_file, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    service = build("sheets", "v4", credentials=creds)
    return service

# Função para carregar dados da planilha
def load_data_from_google_sheets(spreadsheet_id, range_name, credentials_file):
    service = authenticate_google_sheets(credentials_file)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])
    
    # Verifique os dados recebidos
    if not values:
        st.error("Não há dados na planilha.")
        return pd.DataFrame()
    
    # Convertendo os dados para DataFrame
    df = pd.DataFrame(values[1:], columns=values[0])
    
    # Verificando se a coluna "Data" existe
    if 'Data' not in df.columns:
        st.error("A coluna 'Data' não foi encontrada na planilha.")
        return pd.DataFrame()

    # Convertendo a coluna 'Data' para datetime
    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
    
    # Verificando se há valores ausentes ou inválidos
    if df['Data'].isnull().any():
        st.warning("Existem valores inválidos na coluna 'Data'.")
    
    return df

# Função para criar gráfico de distribuição de pagamentos
def create_payment_distribution_graph(df):
    if df.empty:
        return alt.Chart().mark_text().encode(
            text="Sem dados disponíveis"
        ).properties(width=800, height=400)

    try:
        df_melted = df.melt(id_vars=['Data'], value_vars=['Cartão', 'Dinheiro', 'Pix'],
                            var_name='Tipo de pagamento', value_name='Valor')

        chart = alt.Chart(df_melted).mark_bar().encode(
            x=alt.X('Data:T', title='Data'),
            y=alt.Y('sum(Valor):Q', title='Valor'),
            color='Tipo de pagamento:N',
            tooltip=['Data:T', 'sum(Valor):Q', 'Tipo de pagamento:N']
        ).properties(width=800, height=400)
        return chart

    except KeyError as e:
        st.error(f"Erro ao criar gráfico de distribuição de pagamentos: {e}")
        return alt.Chart().mark_text().encode(
            text="Erro ao gerar gráfico"
        ).properties(width=800, height=400)

# Função para criar gráfico de capital acumulado
def create_accumulated_capital_graph(df):
    if df.empty:
        return alt.Chart().mark_text().encode(
            text="Sem dados disponíveis"
        ).properties(width=800, height=400)

    try:
        df_melted = df.melt(id_vars=['Data'], value_vars=['Cartão', 'Dinheiro', 'Pix'],
                            var_name='Tipo de pagamento', value_name='Valor')

        df_melted['Acumulado'] = df_melted.groupby('Tipo de pagamento')['Valor'].cumsum()

        chart = alt.Chart(df_melted).mark_line().encode(
            x=alt.X('Data:T', title='Data'),
            y=alt.Y('Acumulado:Q', title='Capital Acumulado'),
            color='Tipo de pagamento:N',
            tooltip=['Data:T', 'Acumulado:Q', 'Tipo de pagamento:N']
        ).properties(width=800, height=400)
        return chart

    except KeyError as e:
        st.error(f"Erro ao criar gráfico de capital acumulado: {e}")
        return alt.Chart().mark_text().encode(
            text="Erro ao gerar gráfico"
        ).properties(width=800, height=400)

# Função principal para exibir o Streamlit app
def main():
    st.title("Controle de Vendas")

    # Seção para seleção de mês e ano
    st.sidebar.header("Filtrar por mês e ano")
    year = st.sidebar.selectbox("Ano", options=[2025, 2026], index=0)
    month = st.sidebar.selectbox("Mês", options=["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                                                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"], index=3)

    # Carregar os dados da planilha
    try:
        df = load_data_from_google_sheets(SPREADSHEET_ID, RANGE_NAME, 'credentials.json')  # O caminho para o credentials.json
        if not df.empty:
            st.write(df)  # Exibe o dataframe
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return

    # Exibição do gráfico de distribuição de pagamentos
    st.subheader("Distribuição de Pagamentos")
    st.altair_chart(create_payment_distribution_graph(df), use_container_width=True)

    # Exibição do gráfico de capital acumulado
    st.subheader("Capital Acumulado")
    st.altair_chart(create_accumulated_capital_graph(df), use_container_width=True)

    # Formulário para cadastrar novos dados
    st.subheader("Cadastrar Nova Venda")

    with st.form(key="data_form"):
        new_date = st.date_input("Data", value=pd.to_datetime("2025-04-29"))
        new_cartao = st.number_input("Cartão", min_value=0, step=1)
        new_dinheiro = st.number_input("Dinheiro", min_value=0, step=1)
        new_pix = st.number_input("Pix", min_value=0, step=1)

        submit_button = st.form_submit_button("Cadastrar")

        if submit_button:
            # Adicionar novo registro ao DataFrame
            new_data = {
                'Data': new_date,
                'Cartão': new_cartao,
                'Dinheiro': new_dinheiro,
                'Pix': new_pix
            }
            new_row = pd.DataFrame([new_data])
            df = pd.concat([df, new_row], ignore_index=True)

            st.success(f"Nova venda registrada para {new_date.strftime('%d/%m/%Y')}.")

    # Exibição da tabela com os dados atualizados
    st.subheader("Tabela de Vendas")
    st.write(df)

if __name__ == "__main__":
    main()
