import os
import google.auth
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

def get_google_credentials():
    # Verifica se a variável de ambiente GOOGLE_CREDENTIALS está definida
    credentials_json = os.getenv('GOOGLE_CREDENTIALS')
    if not credentials_json:
        raise ValueError("A variável de ambiente GOOGLE_CREDENTIALS não está definida!")
    
    # Carrega as credenciais do arquivo de serviço
    credentials = Credentials.from_service_account_info(credentials_json)
    return credentials

def read_google_sheet():
    # Carrega as credenciais
    credentials = get_google_credentials()
    
    # Use as credenciais para acessar a planilha
    service = build('sheets', 'v4', credentials=credentials)
    spreadsheet_id = 'https://docs.google.com/spreadsheets/d/1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg/edit'
    range_ = 'Vendas!A1:D10'  # Alterar o range conforme necessário
    
    # Obter dados da planilha
    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_).execute()
    values = result.get('values', [])
    
    return values
