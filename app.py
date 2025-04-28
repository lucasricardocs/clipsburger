import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

# Título do app
st.title("📄 Visualizador de Vendas - PitDog")

# 1. Ler credenciais do st.secrets
creds_info = st.secrets["google_credentials"]

# 2. Criar credenciais com google.oauth2
credentials = service_account.Credentials.from_service_account_info(
    creds_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
)

# 3. Conectar ao Google Sheets
service = build("sheets", "v4", credentials=credentials)
sheet = service.spreadsheets()

# 4. ID da planilha (só o ID do link)
SPREADSHEET_ID = "1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg"
RANGE_NAME = "Vendas"  # Nome da aba

# 5. Buscar os dados
try:
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get("values", [])

    if not values:
        st.warning("Nenhum dado encontrado na planilha.")
    else:
        # Transformar em DataFrame
        df = pd.DataFrame(values[1:], columns=values[0])
        st.dataframe(df)

except Exception as e:
    st.error(f"Ocorreu um erro ao acessar a planilha: {e}")
