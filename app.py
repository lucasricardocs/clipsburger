import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

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

    # Exibindo as linhas
    st.write(rows)

def main():
    st.title("Leitura de Planilha Google")
    
    # Botão para carregar dados da planilha
    if st.button("Carregar dados"):
        read_google_sheet()

if __name__ == "__main__":
    main()
