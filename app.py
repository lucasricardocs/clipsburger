import os
import json
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Função para criar o arquivo temporário de credenciais
def create_credentials_file():
    # Recupera o conteúdo do credentials a partir da variável de ambiente
    credentials_content = os.environ.get('GOOGLE_CREDENTIALS')

    if credentials_content:
        # Converte a string JSON para dicionário
        credentials_dict = json.loads(credentials_content)
        
        # Cria o arquivo 'credentials.json' temporário
        with open('credentials.json', 'w') as f:
            json.dump(credentials_dict, f)
    else:
        st.error("A variável de ambiente GOOGLE_CREDENTIALS não está definida!")

# Função para autenticar usando as credenciais do Google
def authenticate_with_google():
    # Cria o arquivo temporário
    create_credentials_file()

    # Carrega as credenciais do arquivo JSON
    credentials = Credentials.from_service_account_file('credentials.json')

    # Conecte-se à API do Google (exemplo: Google Sheets API)
    service = build('sheets', 'v4', credentials=credentials)
    return service

# Função para ler os dados da planilha
def read_google_sheet():
    service = authenticate_with_google()

    # ID da planilha e intervalo
    spreadsheet_id = 'VendasPitDog'  # Nome da planilha, substitua pelo ID correto
    range_ = 'Vendas!A2:D'  # Nome da aba (Vendas) e o intervalo (A2:D)

    # Fazendo a requisição para ler os dados
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_).execute()
    rows = result.get('values', [])

    if not rows:
        st.write("Nenhum dado encontrado.")
    else:
        # Exibir os dados lidos (Data, Cartão, Dinheiro, Pix)
        for row in rows:
            data = row[0]  # Data
            cartao = row[1]  # Cartão
            dinheiro = row[2]  # Dinheiro
            pix = row[3]  # Pix

            st.write(f"Data: {data}, Cartão: {cartao}, Dinheiro: {dinheiro}, Pix: {pix}")

# Exemplo de interface no Streamlit
def main():
    st.title("Leitura de Planilha Google")

    if st.button('Ler Dados'):
        read_google_sheet()

if __name__ == '__main__':
    main()
