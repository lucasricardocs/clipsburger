import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Função para obter credenciais do arquivo secreto
def get_credentials():
    credentials = service_account.Credentials.from_service_account_file(
        '/etc/secrets/credentials.json',  # Caminho no Render
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )
    return credentials

# Função para ler os dados da planilha
def read_sheet_data():
    credentials = get_credentials()
    service = build('sheets', 'v4', credentials=credentials)

    # Definir o ID da planilha e a aba/range
    SPREADSHEET_ID = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'  # Seu ID
    RANGE_NAME = 'Vendas!A:D'  # A aba se chama "Vendas" e vai de A até D

    # Ler os dados
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        return pd.DataFrame()  # Retorna vazio se não tiver dados

    # Transformar em DataFrame
    df = pd.DataFrame(values[1:], columns=values[0])  # Primeira linha vira cabeçalho
    return df

# Streamlit App
def main():
    st.title("📄 Visualizador de Vendas - Pit Dog")

    try:
        df = read_sheet_data()

        if df.empty:
            st.warning("Nenhum dado encontrado na planilha!")
        else:
            st.success("Dados carregados com sucesso!")
            st.dataframe(df)

    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    main()
