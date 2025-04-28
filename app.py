from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_credentials():
    credentials = service_account.Credentials.from_service_account_file(
        '/etc/secrets/credentials.json',
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return credentials

def read_google_sheet():
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)

    sheet = service.spreadsheets()
    spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
    range_ = 'Vendas!A:D'

    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_).execute()
    values = result.get('values', [])
    return values
