import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import altair as alt

# Função para ler a planilha do Google Sheets
def read_google_sheet():
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
    
    return df

# Função para criar o gráfico de acumulação de patrimônio
def create_accumulated_wealth_graph(df):
    # Calculando a acumulação de patrimônio
    df['Total'] = df[['Cartão', 'Dinheiro', 'Pix']].sum(axis=1)
    df['Acumulado'] = df['Total'].cumsum()

    # Gráfico de linha para acumulação de patrimônio
    chart = alt.Chart(df).mark_line().encode(
        x=alt.X('Data:T', title='Data'),
        y=alt.Y('Acumulado:Q', title='Patrimônio Acumulado'),
    ).properties(
        width=800,
        height=400
    )

    return chart

# Função principal do aplicativo
def main():
    st.title("Leitura de Planilha Google e Acumulação de Patrimônio")
    
    # Botão para carregar dados da planilha
    if st.button("Carregar dados da planilha"):
        df = read_google_sheet()
        
        # Exibindo os dados da planilha
        st.write("Dados da planilha:", df)
        
        # Exibindo o gráfico de acumulação de patrimônio
        st.altair_chart(create_accumulated_wealth_graph(df), use_container_width=True)

if __name__ == "__main__":
    main()
