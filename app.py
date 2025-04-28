import streamlit as st
import pandas as pd
import json
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

# Função para pegar as credenciais
def get_google_credentials():
    credentials_json = os.getenv('GOOGLE_CREDENTIALS')
    if not credentials_json:
        raise ValueError("A variável de ambiente GOOGLE_CREDENTIALS não está definida!")

    # Carrega a variável de ambiente como dicionário
    credentials_info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(credentials_info)

    return credentials

# Função para ler a planilha
def read_google_sheet():
    credentials = get_google_credentials()
    
    service = build('sheets', 'v4', credentials=credentials)
    
    # Seu ID da planilha
    spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
    range_name = 'Vendas!A1:D'  # Nome da aba e intervalo de colunas
    
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])

    # Converter os dados para DataFrame, se tiver dados
    if not values:
        return pd.DataFrame()
    
    headers = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=headers)

    return df

# Função principal do Streamlit
def main():
    st.title("Leitura da Planilha de Vendas - PitDog")

    try:
        df = read_google_sheet()
        if df.empty:
            st.warning("Nenhum dado encontrado na planilha.")
        else:
            st.dataframe(df)
    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    main()
