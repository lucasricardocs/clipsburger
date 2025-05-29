import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings
import plotly.graph_objects as go
import datetime as dt # Usado para datetime.date

# Suprimir warnings específicos do pandas
warnings.filterwarnings("ignore", category=FutureWarning, message=".*observed=False.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*Converting to PeriodDtype.*")


# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = "1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg" # SUBSTITUA PELO SEU ID REAL
WORKSHEET_NAME = "Vendas"
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/clipsburger/main/logo.png"

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema Financeiro - Clips Burger", layout="wide", page_icon="🍔")

# Configuração de tema para gráficos mais bonitos
alt.data_transformers.enable("json")

# Paleta de cores otimizada para modo escuro (ajustada para melhor contraste)
CORES_MODO_ESCURO = ["#57a3f2", "#63d2b4", "#f5b041", "#ec7063", "#85c1e9", "#f7dc6f", "#af7ac5", "#aab7b8"]
COR_FUNDO_CONTAINER = "rgba(40, 45, 55, 0.7)"
COR_BORDA_INSIGHT = "#57a3f2"
COR_TEXTO_PRINCIPAL = "#ffffff"
COR_TEXTO_SECUNDARIO = "#b0bec5"
COR_SEPARADOR = "#455a64"

# Define a ordem correta dos dias da semana e meses
dias_semana_ordem = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# CSS para melhorar a aparência
def inject_css():
    st.markdown(f"""
    <style>
    /* --- Geral --- */
    .stApp {{
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
        color: {COR_TEXTO_PRINCIPAL};
    }}

    h1, h2, h3, h4, h5, h6 {{
        color: {COR_TEXTO_PRINCIPAL};
        font-weight: 600;
    }}

    /* --- Separadores --- */
    hr {{
        border-top: 2px solid {COR_SEPARADOR};
        margin: 1.5rem 0;
    }}

    /* --- Inputs e Botões --- */
    .stSelectbox label, .stNumberInput label, .stDateInput label, .stMultiselect label {{
        font-weight: 600;
        color: {CORES_MODO_ESCURO[0]};
        margin-bottom: 0.3rem;
    }}

    .stNumberInput input::placeholder {{
        color: #78909c;
        font-style: italic;
    }}

    .stButton > button {{
        height: 3rem;
        font-size: 1.1rem;
        font-weight: 600;
        width: 100%;
        border-radius: 8px;
        transition: all 0.3s ease;
        border: none;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }}
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3);
    }}

    /* --- Containers e Métricas --- */
    .element-container {{
        margin-bottom: 0.8rem;
    }}

    .stMetric {{
        background-color: {COR_FUNDO_CONTAINER};
        padding: 1.2rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        min-height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        border: 1px solid {COR_SEPARADOR};
        box-shadow: 0 2px 5px rgba(0,0,0,0.15);
        transition: transform 0.2s ease-in-out;
    }}
    .stMetric:hover {{
         transform: scale(1.02);
    }}

    .stMetric label {{
        color: {COR_TEXTO_SECUNDARIO} !important;
        font-size: 0.95rem !important;
    }}
    .stMetric > div > div {{
        font-size: 1.8rem !important;
        font-weight: 600;
        color: {COR_TEXTO_PRINCIPAL} !important;
    }}
    .stMetric .stMetricDelta {{ 
        font-size: 0.9rem !important;
        font-weight: 500;
    }}

    /* --- Containers de Insights --- */
    .insight-container {{
        background: {COR_FUNDO_CONTAINER};
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 5px solid {COR_BORDA_INSIGHT};
        min-height: 150px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 0 3px 7px rgba(0,0,0,0.2);
        transition: background-color 0.3s ease;
    }}
    .insight-container:hover {{
        background-color: rgba(50, 55, 65, 0.8);
    }}
    .insight-container h4 {{
        color: {COR_BORDA_INSIGHT};
        margin: 0 0 1rem 0;
        font-size: 1.1rem;
        font-weight: 600;
    }}
    .insight-container p {{
        margin: 0;
        line-height: 1.6;
        color: {COR_TEXTO_PRINCIPAL};
        font-size: 0.95rem;
    }}

    /* --- Logo e Título --- */
    .header-container {{
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 25px;
        padding-bottom: 15px;
        border-bottom: 1px solid {COR_SEPARADOR};
    }}
    
    .logo-container {{
        display: flex;
        align-items: center;
        gap: 5px;
        margin-bottom: 5px;
        padding-bottom: 5px;
    }}
    
    .logo-image {{
        width: 210px;
        height: auto;
        animation: celestialPulse 8s ease-in-out infinite;
    }}

    @keyframes celestialPulse {{
        0%, 100% {{
            filter: drop-shadow(0 0 15px rgba(100, 149, 237, 0.8)) drop-shadow(0 0 30px rgba(100, 149, 237, 0.6));
        }}
        33% {{
            filter: drop-shadow(0 0 15px rgba(147, 112, 219, 0.8)) drop-shadow(0 0 30px rgba(147, 112, 219, 0.6));
        }}
        66% {{
            filter: drop-shadow(0 0 15px rgba(255, 255, 255, 0.9)) drop-shadow(0 0 30px rgba(255, 255, 255, 0.7));
        }}
    }}

    .logo-container h1 {{
        font-size: 2.4rem;
        margin: 0;
        padding-left: 10px;
        font-weight: 700;
    }}
    .logo-container p {{
        margin: 0;
        font-size: 1rem;
        color: {COR_TEXTO_SECUNDARIO};
        padding-left: 10px;
    }}
    
    /* --- Tabs --- */
    .stTabs [role="tab"] {{
        padding: 1rem 1.8rem;
        font-weight: 600;
        font-size: 1.1rem;
        border-radius: 8px 8px 0 0;
        transition: all 0.3s ease;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {COR_FUNDO_CONTAINER};
        color: {COR_TEXTO_PRINCIPAL};
    }}
    .stTabs [role="tab"]:hover {{
        background-color: rgba(87, 163, 242, 0.1);
    }}

    .stTabs > div > div > div > div:first-child {{
        border-bottom: none !important;
        margin-bottom: 0 !important;
    }}

    /* --- Tabelas --- */
    .stDataFrame {{
        border: 1px solid {COR_SEPARADOR};
        border-radius: 8px;
        overflow: hidden;
    }}
    .stDataFrame thead th {{
        background-color: rgba(76, 120, 168, 0.3);
        color: {COR_TEXTO_PRINCIPAL};
        font-weight: 600;
    }}
    .stDataFrame tbody tr:nth-child(even) {{
        background-color: rgba(255, 255, 255, 0.03);
    }}

    /* --- DRE Alignment --- */
    .dre-textual-container table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 1rem;
    }}
    .dre-textual-container th, .dre-textual-container td {{
        padding: 8px 12px;
        text-align: left;
        border-bottom: 1px solid {COR_SEPARADOR};
    }}
    .dre-textual-container td:nth-child(2) {{ 
        text-align: right;
        font-family: 'Courier New', Courier, monospace;
        white-space: pre;
    }}
    .dre-textual-container th:nth-child(2) {{ 
        text-align: right;
        padding-right: 12px;
    }}

    /* --- Responsividade --- */
    @media (max-width: 992px) {{ 
        .logo-image {{ width: 180px; }}
        .logo-container h1 {{ font-size: 2rem; }}
        .stMetric {{ padding: 1rem; min-height: 100px; }}
        .insight-container {{ padding: 1.2rem; min-height: 140px; }}
        /* Correção para colunas em métricas se necessário */
        /* .st-emotion-cache-1l269bu > div {{  */
        /*      flex-direction: column; */
        /* }} */
    }}

    @media (max-width: 768px) {{ 
        .logo-image {{ width: 150px; }}
        .logo-container {{ gap: 10px; }}
        .logo-container h1 {{ font-size: 1.6rem; }}
        .logo-container p {{ font-size: 0.9rem; }}
        .stMetric {{ min-height: 90px; padding: 0.8rem; }}
        .stMetric > div > div {{ font-size: 1.5rem !important; }}
        .stTabs [role="tab"] {{ padding: 0.6rem 1rem; }}
        .stDateInput, .stNumberInput, .stSelectbox, .stMultiselect {{ margin-bottom: 1rem; }}
        .insight-container {{ padding: 1rem; min-height: auto; }}
        .insight-container h4 {{ font-size: 1rem; }}
        .insight-container p {{ font-size: 0.9rem; }}
        .dre-textual-container td, .dre-textual-container th {{ padding: 6px 8px; font-size: 13px; }}
    }}

    @media (max-width: 480px) {{ 
        .logo-image {{ width: 120px; }}
        .logo-container h1 {{ font-size: 1.4rem; }}
        .stMetric > div > div {{ font-size: 1.3rem !important; }}
        .stMetric label {{ font-size: 0.85rem !important; }}
        .stButton > button {{ font-size: 1rem; height: 2.8rem; }}
    }}
    </style>
    """, unsafe_allow_html=True)

inject_css()

# --- Funções de Cache para Acesso ao Google Sheets ---
@st.cache_resource(ttl=3600) # Cache de 1 hora para o cliente gspread
def get_google_auth():
    """Autoriza o acesso ao Google Sheets e retorna o cliente gspread."""
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/spreadsheets.readonly",
              "https://www.googleapis.com/auth/drive.readonly"]
    try:
        if "google_credentials" not in st.secrets:
            st.error("Credenciais do Google (\"google_credentials\") não encontradas em st.secrets. Configure o arquivo .streamlit/secrets.toml")
            return None

        credentials_dict = st.secrets["google_credentials"]
        if not credentials_dict: # Verifica se o dicionário não está vazio
            st.error("As credenciais do Google em st.secrets estão vazias.")
            return None

        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Erro de autenticação com Google: {e}")
        return None

@st.cache_resource(ttl=3600) # Cache de 1 hora para o objeto worksheet
def get_worksheet():
    """Retorna o objeto worksheet da planilha especificada."""
    gc = get_google_auth()
    if gc:
        try:
            spreadsheet = gc.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
            return worksheet
        except SpreadsheetNotFound:
            st.error(f"Planilha com ID 	'{SPREADSHEET_ID}	' não encontrada. Verifique o ID e as permissões.")
            return None
        except Exception as e:
            st.error(f"Erro ao acessar a planilha 	'{WORKSHEET_NAME}	': {e}")
            return None
    return None

# --- Funções de Manipulação de Dados ---
@st.cache_data(ttl=600) # Cache de 10 minutos para os dados lidos
def read_sales_data():
    """Lê todos os registros da planilha de vendas e retorna como DataFrame."""
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records(numericise_ignore=['all']) # Ler tudo como string inicialmente
            if not rows:
                # st.info("A planilha de vendas está vazia.")
                return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix"])

            df = pd.DataFrame(rows)

            # Garantir que as colunas de valor existam e sejam numéricas
            for col in ["Cartão", "Dinheiro", "Pix"]:
                if col in df.columns:
                    # Tenta converter para numérico, substituindo vírgula por ponto
                    df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    df[col] = 0.0 # Adiciona a coluna com zeros se não existir

            # Tratar coluna 'Data'
            if "Data" not in df.columns:
                 # st.warning("Coluna 	'Data	' não encontrada na planilha. Criando coluna vazia.")
                 df["Data"] = pd.NaT # Cria coluna de data vazia
            else:
                # Tenta converter para datetime, tratando diversos formatos comuns
                df["Data"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)


            # Remover linhas onde a data não pôde ser convertida
            df.dropna(subset=["Data"], inplace=True)

            return df
        except Exception as e:
            st.error(f"Erro ao ler dados da planilha: {e}")
            return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix"]) # Retorna DF vazio em caso de erro
    return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix"]) # Retorna DF vazio se worksheet for None

def add_data_to_sheet(date_obj, cartao_val, dinheiro_val, pix_val, worksheet_obj):
    """Adiciona uma nova linha de dados à planilha Google Sheets."""
    if worksheet_obj is None:
        st.error("Não foi possível acessar a planilha para adicionar dados.")
        return False
    try:
        # Garantir que os valores são float
        cartao_float = float(cartao_val) if cartao_val else 0.0
        dinheiro_float = float(dinheiro_val) if dinheiro_val else 0.0
        pix_float = float(pix_val) if pix_val else 0.0

        # Formata a data como string DD/MM/YYYY para consistência na planilha
        formatted_date_str = date_obj.strftime("%d/%m/%Y")

        new_row = [formatted_date_str, cartao_float, dinheiro_float, pix_float]
        worksheet_obj.append_row(new_row, value_input_option='USER_ENTERED') # USER_ENTERED para formatar como número
        # Limpar caches relevantes após adicionar dados
        st.cache_data.clear() # Limpa cache de dados (read_sales_data, process_data)
        st.cache_resource.clear() # Limpa cache de get_worksheet e get_google_auth se precisar forçar re-autenticação
        return True # Indica sucesso
    except ValueError as ve:
        st.error(f"Erro ao converter valores para número: {ve}. Verifique os dados de entrada.")
        return False
    except Exception as e:
        st.error(f"Erro ao adicionar dados na planilha: {e}")
        return False

@st.cache_data # Cache para processamento de dados
def process_data(df_input):
    """Processa e prepara os dados de vendas para análise."""
    if df_input.empty or "Data" not in df_input.columns:
        # st.warning("DataFrame de entrada vazio ou sem coluna 	'Data	' para processamento.")
        # Define colunas esperadas para um DataFrame vazio estruturado
        cols = ["Data", "Cartão", "Dinheiro", "Pix", "Total", "Ano", "Mês", "MêsNome", "AnoMês", "DataFormatada", "DiaSemana", "DiaDoMes"]
        empty_df = pd.DataFrame(columns=cols)
        # Define tipos para colunas numéricas e de data para evitar erros posteriores
        for col_num in ["Cartão", "Dinheiro", "Pix", "Total", "Ano", "Mês", "DiaDoMes"]:
             empty_df[col_num] = pd.Series(dtype="float64")
        empty_df["Data"] = pd.Series(dtype="datetime64[ns]")
        for col_obj in ["MêsNome", "AnoMês", "DataFormatada", "DiaSemana"]:
             empty_df[col_obj] = pd.Series(dtype="object")
        return empty_df

    df = df_input.copy()

    # Garantir que 'Data' é datetime
    if not pd.api.types.is_datetime64_any_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
        df.dropna(subset=["Data"], inplace=True) # Remove linhas onde Data não pôde ser convertida

    if df.empty: return df # Retorna se ficou vazio após tratamento de data

    # Garantir que colunas de valor são numéricas
    for col_val in ["Cartão", "Dinheiro", "Pix"]:
        if col_val in df.columns:
            df[col_val] = pd.to_numeric(df[col_val], errors="coerce").fillna(0.0)
        else:
            df[col_val] = 0.0 # Adiciona coluna com zeros se não existir

    df["Total"] = df["Cartão"] + df["Dinheiro"] + df["Pix"]

    # Extrair informações de data
    df["Ano"] = df["Data"].dt.year
    df["Mês"] = df["Data"].dt.month
    df["MêsNome"] = df["Mês"].apply(lambda x: meses_ordem[int(x)-1] if pd.notna(x) and 1 <= int(x) <= 12 else None)
    df["AnoMês"] = df["Data"].dt.strftime("%Y-%m") # Para agrupamentos
    df["DataFormatada"] = df["Data"].dt.strftime("%d/%m/%Y")
    day_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
    df["DiaSemana"] = df["Data"].dt.dayofweek.map(day_map)
    df["DiaDoMes"] = df["Data"].dt.day

    df = df.sort_values(by="Data").reset_index(drop=True)

    # Converter para tipos categóricos ordenados para gráficos
    df["DiaSemana"] = pd.Categorical(df["DiaSemana"], categories=dias_semana_ordem, ordered=True)
    df["MêsNome"] = pd.Categorical(df["MêsNome"], categories=meses_ordem, ordered=True)

    return df

# --- Funções de Formatação ---
def format_brl(value):
    """Formata valor numérico como moeda brasileira (R$)."""
    try:
        # Assegura que value é um número antes de formatar
        if pd.isna(value): return "R$ -"
        numeric_value = float(value)
        return f"R$ {numeric_value:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")
    except (ValueError, TypeError):
        return "R$ -" # Retorna um placeholder se a formatação falhar

# --- Funções de Gráficos Interativos ---

def create_radial_plot(df):
    """Cria um gráfico radial de métodos de pagamento."""
    if df.empty or not any(col in df.columns for col in ["Cartão", "Dinheiro", "Pix"]):
        return None

    payment_data = pd.DataFrame({
        "Método": ["Cartão", "Dinheiro", "PIX"], # Mantendo PIX em maiúsculo para consistência com alguns contextos
        "Valor": [df["Cartão"].sum(), df["Dinheiro"].sum(), df["Pix"].sum()]
    })
    payment_data = payment_data[payment_data["Valor"] > 0] # Considerar apenas métodos com valor

    if payment_data.empty:
        return None

    base = alt.Chart(payment_data).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        radius=alt.Radius("Valor:Q", scale=alt.Scale(type="sqrt", zero=True, rangeMin=20)),
        color=alt.Color("Método:N",
                        scale=alt.Scale(range=CORES_MODO_ESCURO[:len(payment_data)]), # Usa cores do tema
                        legend=alt.Legend(title="Método", orient="bottom", titleColor=COR_TEXTO_PRINCIPAL, labelColor=COR_TEXTO_SECUNDARIO)),
        order=alt.Order("Valor:Q", sort="descending"), # Ordena para melhor visualização radial
        tooltip=[
            alt.Tooltip("Método:N", title="Método"),
            alt.Tooltip("Valor:Q", title="Valor", format=",.2f")
        ]
    )

    radial_plot = base.mark_arc(innerRadius=30, stroke=COR_FUNDO_CONTAINER, strokeWidth=3).properties(
        height=500, # Altura ajustável
        background="transparent" # Para integrar com o tema da app
    ).configure_view(
        stroke=None, # Remove borda da visualização
        strokeOpacity=0
    ).configure_axis(
        labelColor=COR_TEXTO_SECUNDARIO,
        titleColor=COR_TEXTO_PRINCIPAL,
        grid=False # Remove grid dos eixos
    ).configure_legend(
        titleColor=COR_TEXTO_PRINCIPAL,
        labelColor=COR_TEXTO_SECUNDARIO
    )

    return radial_plot

def create_advanced_daily_sales_chart(df):
    """Cria um gráfico de vendas diárias empilhadas - versão corrigida para evitar SchemaValidationError."""
    # Validações iniciais
    if df.empty or 'Data' not in df.columns:
        # st.info("DataFrame vazio ou sem coluna 'Data' para gráfico de vendas diárias.") # Adicionado para depuração
        return None

    required_cols = ['Cartão', 'Dinheiro', 'Pix']
    if not all(col in df.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df.columns]
        # st.info(f"Colunas ausentes para gráfico de vendas diárias: {missing}") # Adicionado para depuração
        return None

    # Preparar dados
    df_sorted = df.sort_values('Data').copy()
    df_sorted.dropna(subset=['Data'] + required_cols, inplace=True) # Remove NAs nas colunas relevantes

    if df_sorted.empty:
        # st.info("Sem dados válidos após limpeza para gráfico de vendas diárias.") # Adicionado para depuração
        return None

    # Agrupar por data para evitar duplicatas e somar valores diários
    df_grouped = df_sorted.groupby('Data')[required_cols].sum().reset_index()

    # Verificar se ainda temos dados após agrupamento
    if df_grouped.empty:
        # st.info("DataFrame vazio após agrupamento por data.") # Adicionado para depuração
        return None

    # Criar coluna de data formatada (para tooltip)
    df_grouped['DataFormatada'] = df_grouped['Data'].dt.strftime('%d/%m')

    # Transformar para formato longo
    df_melted = df_grouped.melt(
        id_vars=['Data', 'DataFormatada'], # Manter Data para o eixo X temporal
        value_vars=required_cols,
        var_name='Método',
        value_name='Valor'
    )

    # Filtrar valores positivos
    df_melted = df_melted[df_melted['Valor'] > 0]

    if df_melted.empty:
        # st.info("Sem valores de venda positivos para exibir no gráfico diário.") # Adicionado para depuração
        return None

    # Garantir que os tipos estão corretos
    df_melted['Valor'] = pd.to_numeric(df_melted['Valor'], errors='coerce')
    df_melted = df_melted.dropna(subset=['Valor'])

    if df_melted.empty:
        # st.info("DataFrame vazio após conversão numérica e remoção de NaNs em 'Valor'.") # Adicionado para depuração
        return None

    # Configuração do gráfico Altair
    chart = alt.Chart(df_melted).mark_bar(
        size=25 # Tamanho da barra
    ).encode(
        x=alt.X(
            'Data:T',  # Usar a coluna 'Data' original que é datetime, 'T' para temporal
            title='Data',
            axis=alt.Axis(
                format='%d/%m', # Formato do label do eixo X
                labelAngle=-45,
                labelColor=COR_TEXTO_SECUNDARIO, # Usar constantes globais se definidas
                titleColor=COR_TEXTO_PRINCIPAL
            )
        ),
        y=alt.Y(
            'Valor:Q', # 'Q' para quantitativo
            title='Vendas (R$)',
            stack='zero', # Empilhar barras
            axis=alt.Axis(
                labelColor=COR_TEXTO_SECUNDARIO,
                titleColor=COR_TEXTO_PRINCIPAL
            )
        ),
        color=alt.Color(
            'Método:N', # 'N' para nominal
            scale=alt.Scale(domain=required_cols, range=['#4c78a8', '#54a24b', '#f58518']), # Cores padrão ou do tema
            legend=alt.Legend(
                title="Método de Pagamento",
                orient='bottom',
                labelColor=COR_TEXTO_SECUNDARIO,
                titleColor=COR_TEXTO_PRINCIPAL
                )
        ),
        tooltip=[
            alt.Tooltip('DataFormatada:N', title='Data'), # Usar DataFormatada para tooltip
            alt.Tooltip('Método:N', title='Método'),
            alt.Tooltip('Valor:Q', title='Valor (R$)', format=',.2f')
        ]
    ).properties(
        title=alt.TitleParams(
            text='Vendas Diárias por Método de Pagamento',
            color=COR_TEXTO_PRINCIPAL,
            fontSize=16,
            anchor='middle'
        ),
        height=400,
        background="transparent"
    ).configure_view(
        strokeOpacity=0
    )
    return chart


def create_weekday_sales_chart(df):
    """Cria gráfico de barras da média de vendas por dia da semana."""
    if df.empty or "DiaSemana" not in df.columns or "Total" not in df.columns:
        return None

    weekday_avg = df.groupby("DiaSemana", observed=False)["Total"].mean().reset_index()
    weekday_avg = weekday_avg.dropna() # Remove dias sem dados

    if weekday_avg.empty:
        return None

    chart = alt.Chart(weekday_avg).mark_bar(
        cornerRadius=8, # Bordas arredondadas
        size=30 # Largura das barras
    ).encode(
        x=alt.X("DiaSemana:O", title="Dia da Semana", sort=dias_semana_ordem, axis=alt.Axis(
            labelAngle=-45, 
            labelColor=COR_TEXTO_SECUNDARIO, 
            titleColor=COR_TEXTO_PRINCIPAL,
            grid=False
        )),
        y=alt.Y("Total:Q", title="Média de Vendas (R$)", axis=alt.Axis(
            labelColor=COR_TEXTO_SECUNDARIO, 
            titleColor=COR_TEXTO_PRINCIPAL,
            grid=False # Remove grid horizontal para um visual mais limpo
        )),
        color=alt.Color("DiaSemana:N", legend=None, scale=alt.Scale(range=CORES_MODO_ESCURO)), # Cores do tema, sem legenda de cor
        tooltip=[
            alt.Tooltip("DiaSemana:O", title="Dia"),
            alt.Tooltip("Total:Q", title="Média (R$)", format=",.2f")
        ]
    ).properties(
        height=500,
        background="transparent"
    ).configure_view(
        strokeOpacity=0 # Remove borda da visualização
    )
    return chart

def create_cumulative_evolution_chart(df):
    """Cria gráfico de área da evolução acumulada de vendas com destaque no último valor."""
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        return None

    df_sorted = df.sort_values("Data").copy()
    df_sorted.dropna(subset=["Data", "Total"], inplace=True) # Remove NAs
    if df_sorted.empty:
        return None

    df_sorted["Total_Acumulado"] = df_sorted["Total"].cumsum() # Calcula o acumulado

    # Cores para o gráfico
    cor_linha = "darkgreen"
    cor_inicio_grad = "rgba(144, 238, 144, 0.1)" # Verde claro transparente
    cor_fim_grad = "rgba(0, 100, 0, 0.8)"      # Verde escuro com opacidade

    # Obter o último valor para destacar
    ultimo_valor = df_sorted["Total_Acumulado"].iloc[-1] if not df_sorted.empty else 0
    ultimo_data = df_sorted["Data"].iloc[-1] if not df_sorted.empty else None

    base = alt.Chart(df_sorted).encode(
        x=alt.X("Data:T", title="Data", axis=alt.Axis( # 'T' para temporal
            format="%d/%m/%Y", 
            labelAngle=-45, 
            labelColor=COR_TEXTO_SECUNDARIO, 
            titleColor=COR_TEXTO_PRINCIPAL,
            grid=False
        ))
    )

    area = base.mark_area(
        line={"color": cor_linha, "strokeWidth": 3}, # Configura a linha superior da área
        color=alt.Gradient( # Define o gradiente da área
            gradient="linear",
            stops=[
                alt.GradientStop(color=cor_inicio_grad, offset=0), # Início do gradiente
                alt.GradientStop(color=cor_fim_grad, offset=1)   # Fim do gradiente
            ],
            x1=1, x2=1, y1=1, y2=0 # Direção do gradiente (de baixo para cima)
        ),
        opacity=0.9, # Opacidade da área
    ).encode(
        y=alt.Y("Total_Acumulado:Q", title="Faturamento Acumulado (R$)", axis=alt.Axis(
            labelColor=COR_TEXTO_SECUNDARIO, 
            titleColor=COR_TEXTO_PRINCIPAL,
            grid=False
        )),
        tooltip=[
            alt.Tooltip("Data:T", title="Data", format="%d/%m/%Y"),
            alt.Tooltip("Total_Acumulado:Q", title="Acumulado (R$)", format=",.2f")
        ]
    )

    # Adicionar ponto e texto para destacar o último valor
    if ultimo_data is not None and ultimo_valor > 0:
        point_data = pd.DataFrame({
            "Data": [ultimo_data],
            "Total_Acumulado": [ultimo_valor],
            "Label": [f"Total: {format_brl(ultimo_valor)}"] # Label para o texto
        })
        
        point = alt.Chart(point_data).mark_circle(
            size=100,
            color="red", # Cor do ponto de destaque
            opacity=0.8
        ).encode(
            x="Data:T",
            y="Total_Acumulado:Q",
            tooltip=[ # Tooltip específico para o ponto
                alt.Tooltip("Data:T", title="Última Data", format="%d/%m/%Y"),
                alt.Tooltip("Total_Acumulado:Q", title="Total Acumulado Final", format=",.2f")
            ]
        )
        
        text_highlight = alt.Chart(point_data).mark_text(
            align="left",
            baseline="middle",
            dx=15, # Deslocamento horizontal do texto
            dy=-15, # Deslocamento vertical do texto
            fontSize=14,
            fontWeight="bold",
            color=COR_TEXTO_PRINCIPAL # Cor do texto de destaque
        ).encode(
            x="Data:T",
            y="Total_Acumulado:Q",
            text="Label:N" # Usa a coluna 'Label' para o texto
        )
        
        chart_final = alt.layer(area, point, text_highlight).properties( # Combina área, ponto e texto
            height=500,
            background="transparent"
        ).configure_view(
            strokeOpacity=0
        ).interactive() # Permite zoom e pan
    else:
        chart_final = area.properties(
            height=500,
            background="transparent"
        ).configure_view(
            strokeOpacity=0
        ).interactive()

    return chart_final

# --- Funções do Heatmap de Calendário ---
def criar_calendario_anual_espacamento_correto(df_calendario, ano_calendario):
    """Cria calendário anual com maior distância entre nomes dos dias e o gráfico"""
    if df_calendario.empty or "Data" not in df_calendario.columns or "Total" not in df_calendario.columns:
        # st.warning(f"Dados insuficientes para gerar o heatmap de calendário para {ano_calendario}.")
        return None, None

    ano_calendario_int = int(ano_calendario) 
    
    df_year_calendario = df_calendario[df_calendario["Data"].dt.year == ano_calendario_int].copy()
    if df_year_calendario.empty:
        # st.info(f"Sem dados de vendas para o ano {ano_calendario_int}.")
        return None, None

    dates_completos_calendario = pd.date_range(start=f'{ano_calendario_int}-01-01', end=f'{ano_calendario_int}-12-31', freq='D')

    dados_ano_completo_calendario = []
    for date_obj_cal in dates_completos_calendario:
        if date_obj_cal in df_year_calendario['Data'].values:
            row_cal = df_year_calendario[df_year_calendario['Data'] == date_obj_cal].iloc[0]
            dados_ano_completo_calendario.append({
                'Data': date_obj_cal,
                'Cartão': row_cal.get('Cartão', 0.0), 
                'Dinheiro': row_cal.get('Dinheiro', 0.0),
                'Pix': row_cal.get('Pix', 0.0),
                'Total_Vendas': row_cal.get('Total', 0.0)
            })
        else: 
            dados_ano_completo_calendario.append({
                'Data': date_obj_cal, 'Cartão': 0.0, 'Dinheiro': 0.0, 'Pix': 0.0, 'Total_Vendas': 0.0
            })

    df_ano_completo_calendario = pd.DataFrame(dados_ano_completo_calendario)
    df_ano_completo_calendario['Data'] = pd.to_datetime(df_ano_completo_calendario['Data']) 

    df_ano_completo_calendario['data_str_cal'] = df_ano_completo_calendario['Data'].dt.strftime('%d/%m/%Y')
    
    primeiro_dia_ano_obj_cal = dt.date(ano_calendario_int, 1, 1) 
    primeiro_dia_semana_ano_cal = primeiro_dia_ano_obj_cal.weekday() 

    x_positions_cal, y_positions_cal, valores_categoria_cal, hover_texts_cal = [], [], [], []

    for _, row_cal_iter in df_ano_completo_calendario.iterrows():
        data_atual_obj_cal = row_cal_iter['Data'].date() 
        dias_desde_inicio_ano_cal = (data_atual_obj_cal - primeiro_dia_ano_obj_cal).days
        semana_no_ano_cal = (dias_desde_inicio_ano_cal + primeiro_dia_semana_ano_cal) // 7
        dia_da_semana_grid_cal = (dias_desde_inicio_ano_cal + primeiro_dia_semana_ano_cal) % 7

        x_positions_cal.append(semana_no_ano_cal)
        y_positions_cal.append(dia_da_semana_grid_cal) 

        total_vendas_dia_cal = row_cal_iter['Total_Vendas']
        cat = 0
        if total_vendas_dia_cal == 0: cat = 0
        elif total_vendas_dia_cal < 1500: cat = 1
        elif total_vendas_dia_cal < 2500: cat = 2
        elif total_vendas_dia_cal < 3000: cat = 3
        else: cat = 4
        valores_categoria_cal.append(cat)

        hover_text_cal = f"📅 {row_cal_iter['data_str_cal']}<br>"
        if total_vendas_dia_cal > 0:
            hover_text_cal += (f"💰 Total: {format_brl(total_vendas_dia_cal)}<br>"
                             f"💳 Cartão: {format_brl(row_cal_iter['Cartão'])}<br>"
                             f"💵 Dinheiro: {format_brl(row_cal_iter['Dinheiro'])}<br>"
                             f"📱 Pix: {format_brl(row_cal_iter['Pix'])}")
        else:
            hover_text_cal += "❌ Sem vendas"
        hover_texts_cal.append(hover_text_cal)

    max_semana_heatmap_cal = max(x_positions_cal) + 1 
    matriz_vendas_heatmap_cal = np.full((7, max_semana_heatmap_cal), np.nan) 
    matriz_hover_heatmap_cal = np.full((7, max_semana_heatmap_cal), '', dtype=object)

    for x_cal, y_cal, valor_cat_cal, hover_txt_cal in zip(x_positions_cal, y_positions_cal, valores_categoria_cal, hover_texts_cal):
        if 0 <= y_cal < 7 and 0 <= x_cal < max_semana_heatmap_cal: 
            matriz_vendas_heatmap_cal[y_cal, x_cal] = valor_cat_cal
            matriz_hover_heatmap_cal[y_cal, x_cal] = hover_txt_cal

    escala_cores_heatmap_cal = [
        [0.0, '#202020'], [0.001, '#39D353'], [0.25, '#39D353'], [0.251, '#37AB4B'], [0.5, '#37AB4B'],
        [0.501, '#006D31'], [0.75, '#006D31'], [0.751, '#0D4428'], [1.0, '#0D4428']
    ]

    fig_heatmap_cal = go.Figure(data=go.Heatmap(
        z=matriz_vendas_heatmap_cal, text=matriz_hover_heatmap_cal, hovertemplate='%{text}<extra></extra>',
        colorscale=escala_cores_heatmap_cal, showscale=False, zmin=0, zmax=4, xgap=3, ygap=3, hoverongaps=False
    ))

    nomes_meses_labels_cal = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    posicoes_meses_ticks_cal = []
    for mes_idx_cal in range(1, 13): 
        primeiro_dia_mes_obj_cal = dt.date(ano_calendario_int, mes_idx_cal, 1)
        dias_desde_inicio_ano_mes_cal = (primeiro_dia_mes_obj_cal - primeiro_dia_ano_obj_cal).days
        semana_mes_tick_cal = (dias_desde_inicio_ano_mes_cal + primeiro_dia_semana_ano_cal) // 7
        posicoes_meses_ticks_cal.append(semana_mes_tick_cal)
    
    posicoes_meses_unicas_cal, indices_unicos_cal = np.unique(posicoes_meses_ticks_cal, return_index=True)
    nomes_meses_finais_cal = [nomes_meses_labels_cal[i_cal] for i_cal in indices_unicos_cal]

    fig_heatmap_cal.update_layout(
        title=f"📊 Calendário de Vendas {ano_calendario_int}", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COR_TEXTO_PRINCIPAL, family="Arial"),
        xaxis=dict(title="", showgrid=False, zeroline=False, tickmode='array', tickvals=posicoes_meses_unicas_cal,
                   ticktext=nomes_meses_finais_cal, tickfont=dict(color=COR_TEXTO_PRINCIPAL, size=14),
                   side='top', tickangle=0, ticklabelstandoff=5),
        yaxis=dict(title="", showgrid=False, zeroline=False, tickmode='array', tickvals=[0, 1, 2, 3, 4, 5, 6],
                   ticktext=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
                   tickfont=dict(color=COR_TEXTO_PRINCIPAL, size=14), ticklen=0, ticklabelstandoff=15, autorange="reversed"),
        height=350, title_x=0.5, title_font=dict(size=18, color=COR_TEXTO_PRINCIPAL),
        margin=dict(l=70, r=20, t=80, b=20)
    )
    return fig_heatmap_cal, df_ano_completo_calendario

def criar_heatmap_vendas_mensais_espacamento_correto(df_anual_completo_mensal):
    """Função para criar heatmap mensal horizontal com espaçamento correto."""
    if df_anual_completo_mensal.empty:
        return None, None

    df_vendas_para_mes_mensal = df_anual_completo_mensal.copy() 
    df_vendas_para_mes_mensal['MesNum'] = df_vendas_para_mes_mensal['Data'].dt.month
    
    vendas_mensais_agg_mensal = df_vendas_para_mes_mensal.groupby('MesNum').agg(
        Total_Vendas_Mes=('Total_Vendas', 'sum'), Cartao_Mes=('Cartão', 'sum'),
        Dinheiro_Mes=('Dinheiro', 'sum'), Pix_Mes=('Pix', 'sum')
    ).reset_index()

    nomes_meses_curto_mensal = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    matriz_valores_mensal_hm = np.zeros((1, 12))
    matriz_textos_hover_mensal_hm = np.full((1, 12), '', dtype=object)
    ano_heatmap_mensal = df_anual_completo_mensal['Data'].dt.year.iloc[0] if not df_anual_completo_mensal.empty else datetime.now().year

    for mes_idx_mensal in range(12): 
        mes_atual_num_mensal = mes_idx_mensal + 1 
        nome_mes_atual_mensal = nomes_meses_curto_mensal[mes_idx_mensal]
        dados_do_mes_mensal = vendas_mensais_agg_mensal[vendas_mensais_agg_mensal['MesNum'] == mes_atual_num_mensal]

        if not dados_do_mes_mensal.empty:
            row_mes_mensal = dados_do_mes_mensal.iloc[0]
            matriz_valores_mensal_hm[0, mes_idx_mensal] = row_mes_mensal['Total_Vendas_Mes']
            hover_text_mes_mensal = (f"📅 {nome_mes_atual_mensal} {ano_heatmap_mensal}<br>"
                                     f"💰 Total Mês: {format_brl(row_mes_mensal['Total_Vendas_Mes'])}<br>"
                                     f"💳 Cartão: {format_brl(row_mes_mensal['Cartao_Mes'])}<br>"
                                     f"💵 Dinheiro: {format_brl(row_mes_mensal['Dinheiro_Mes'])}<br>"
                                     f"📱 Pix: {format_brl(row_mes_mensal['Pix_Mes'])}")
        else: 
            matriz_valores_mensal_hm[0, mes_idx_mensal] = 0 
            hover_text_mes_mensal = f"📅 {nome_mes_atual_mensal} {ano_heatmap_mensal}<br>❌ Sem vendas neste mês"
        matriz_textos_hover_mensal_hm[0, mes_idx_mensal] = hover_text_mes_mensal

    escala_cores_mensal_hm = [
        [0.0, '#202020'], [0.001, '#ADD8E6'], [0.25, '#87CEEB'], [0.5, '#4682B4'], [0.75, '#0000CD'], [1.0, '#000080']
    ]
    fig_heatmap_mensal_final = go.Figure(data=go.Heatmap(
        z=matriz_valores_mensal_hm, text=matriz_textos_hover_mensal_hm, hovertemplate='%{text}<extra></extra>',
        colorscale=escala_cores_mensal_hm, showscale=False, xgap=5, ygap=5
    ))
    fig_heatmap_mensal_final.update_layout(
        title=f'📊 Vendas Totais por Mês ({ano_heatmap_mensal})', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COR_TEXTO_PRINCIPAL, family="Arial"),
        xaxis=dict(title="", showgrid=False, zeroline=False, tickmode='array', tickvals=list(range(12)),
                   ticktext=nomes_meses_curto_mensal, tickfont=dict(color=COR_TEXTO_PRINCIPAL, size=14), side='bottom'),
        yaxis=dict(title="", showgrid=False, zeroline=False, showticklabels=False),
        height=250, title_x=0.5, title_font=dict(size=18, color=COR_TEXTO_PRINCIPAL),
        margin=dict(l=20, r=20, t=60, b=50)
    )
    return fig_heatmap_mensal_final, vendas_mensais_agg_mensal

# --- Funções de Análise e Exibição ---

def display_resumo_financeiro(df_resumo):
    """Exibe os cards de resumo financeiro."""
    if df_resumo.empty:
        st.info("Não há dados suficientes para o resumo financeiro.")
        return

    total_faturamento_res = df_resumo["Total"].sum()
    media_diaria_res = df_resumo["Total"].mean() if not df_resumo.empty else 0.0
    maior_venda_res = df_resumo["Total"].max() if not df_resumo.empty else 0.0
    df_vendas_positivas_res = df_resumo[df_resumo["Total"] > 0]
    menor_venda_res = df_vendas_positivas_res["Total"].min() if not df_vendas_positivas_res.empty else 0.0

    col_res1, col_res2, col_res3, col_res4 = st.columns(4)
    with col_res1: st.metric("💰 Faturamento Total", format_brl(total_faturamento_res))
    with col_res2: st.metric("📊 Média por Dia Trabalhado", format_brl(media_diaria_res), help="Média considerando apenas dias com vendas registradas.")
    with col_res3: st.metric("🚀 Maior Venda Diária", format_brl(maior_venda_res))
    with col_res4: st.metric("📉 Menor Venda Diária (>0)", format_brl(menor_venda_res))

def display_metodos_pagamento(df_metodos):
    """Exibe os cards de métodos de pagamento."""
    if df_metodos.empty or not all(col in df_metodos.columns for col in ["Cartão", "Dinheiro", "Pix"]):
        st.info("Não há dados suficientes para análise de métodos de pagamento.")
        return

    total_cartao_met = df_metodos["Cartão"].sum()
    total_dinheiro_met = df_metodos["Dinheiro"].sum()
    total_pix_met = df_metodos["Pix"].sum()
    total_geral_met = total_cartao_met + total_dinheiro_met + total_pix_met

    perc_cartao_met = (total_cartao_met / total_geral_met * 100) if total_geral_met > 0 else 0.0
    perc_dinheiro_met = (total_dinheiro_met / total_geral_met * 100) if total_geral_met > 0 else 0.0
    perc_pix_met = (total_pix_met / total_geral_met * 100) if total_geral_met > 0 else 0.0

    col_met1, col_met2, col_met3 = st.columns(3)
    with col_met1: st.metric("💳 Cartão", format_brl(total_cartao_met), f"{perc_cartao_met:.1f}% do total")
    with col_met2: st.metric("💵 Dinheiro", format_brl(total_dinheiro_met), f"{perc_dinheiro_met:.1f}% do total")
    with col_met3: st.metric("📱 PIX", format_brl(total_pix_met), f"{perc_pix_met:.1f}% do total")

def display_ranking_e_frequencia(df_rank_freq):
    """Exibe o ranking de dias e a análise de frequência."""
    if df_rank_freq.empty or 'DiaSemana' not in df_rank_freq.columns or 'Total' not in df_rank_freq.columns:
        st.info("📊 Dados insuficientes para calcular a análise por dia da semana e frequência.")
        return

    medias_por_dia_rank = df_rank_freq.groupby('DiaSemana', observed=False)['Total'].agg(['mean', 'count'])
    medias_por_dia_rank = medias_por_dia_rank.reindex(dias_semana_ordem).dropna(subset=['mean']) 
    medias_por_dia_rank = medias_por_dia_rank.sort_values(by='mean', ascending=False)

    if not medias_por_dia_rank.empty:
        st.subheader("📊 Ranking dos Dias da Semana (Média de Faturamento)")
        col_rank1, col_rank2 = st.columns(2)
        with col_rank1:
            st.markdown("#### 🏆 **Melhores Dias**")
            if len(medias_por_dia_rank) >= 1:
                p1 = medias_por_dia_rank.index[0]
                st.markdown(f"🥇 **1º:** {p1} ({format_brl(medias_por_dia_rank.loc[p1, 'mean'])}) <small>({int(medias_por_dia_rank.loc[p1, 'count'])} ocorrências)</small>", unsafe_allow_html=True)
            if len(medias_por_dia_rank) >= 2:
                p2 = medias_por_dia_rank.index[1]
                st.markdown(f"🥈 **2º:** {p2} ({format_brl(medias_por_dia_rank.loc[p2, 'mean'])}) <small>({int(medias_por_dia_rank.loc[p2, 'count'])} ocorrências)</small>", unsafe_allow_html=True)
            if len(medias_por_dia_rank) >= 3: 
                p3 = medias_por_dia_rank.index[2]
                st.markdown(f"🥉 **3º:** {p3} ({format_brl(medias_por_dia_rank.loc[p3, 'mean'])}) <small>({int(medias_por_dia_rank.loc[p3, 'count'])} ocorrências)</small>", unsafe_allow_html=True)
        with col_rank2:
            st.markdown("#### 📉 **Piores Dias**")
            piores_dias_rank = medias_por_dia_rank.tail(min(3, len(medias_por_dia_rank))).sort_values(by='mean', ascending=True)
            if len(piores_dias_rank) >= 1:
                u1 = piores_dias_rank.index[0]
                st.markdown(f"🔻 **Último:** {u1} ({format_brl(piores_dias_rank.loc[u1, 'mean'])}) <small>({int(piores_dias_rank.loc[u1, 'count'])} ocorrências)</small>", unsafe_allow_html=True)
            if len(piores_dias_rank) >= 2:
                u2 = piores_dias_rank.index[1]
                st.markdown(f"📊 **Penúltimo:** {u2} ({format_brl(piores_dias_rank.loc[u2, 'mean'])}) <small>({int(piores_dias_rank.loc[u2, 'count'])} ocorrências)</small>", unsafe_allow_html=True)
            if len(piores_dias_rank) >= 3:
                u3 = piores_dias_rank.index[2]
                st.markdown(f"📊 **Antepenúltimo:** {u3} ({format_brl(piores_dias_rank.loc[u3, 'mean'])}) <small>({int(piores_dias_rank.loc[u3, 'count'])} ocorrências)</small>", unsafe_allow_html=True)
        st.markdown("---")

        st.subheader("📅 Análise de Frequência de Trabalho")
        if not df_rank_freq.empty and 'Data' in df_rank_freq.columns:
            data_inicio_freq = df_rank_freq['Data'].min()
            data_fim_freq = df_rank_freq['Data'].max()
            total_dias_periodo_freq = (data_fim_freq - data_inicio_freq).days + 1
            domingos_periodo_freq = sum(1 for i in range(total_dias_periodo_freq) if (data_inicio_freq + timedelta(days=i)).weekday() == 6)
            dias_uteis_esperados_freq = total_dias_periodo_freq - domingos_periodo_freq
            dias_trabalhados_freq = df_rank_freq['Data'].nunique()
            dias_falta_freq = max(0, dias_uteis_esperados_freq - dias_trabalhados_freq)

            col_freq1, col_freq2, col_freq3, col_freq4 = st.columns(4)
            with col_freq1: st.metric("📅 Período Analisado", f"{total_dias_periodo_freq} dias", help=f"De {data_inicio_freq.strftime('%d/%m/%Y')} a {data_fim_freq.strftime('%d/%m/%Y')}")
            with col_freq2: st.metric("🏢 Dias Trabalhados", f"{dias_trabalhados_freq} dias", help="Dias com registro de vendas.")
            with col_freq3: st.metric("🏖️ Domingos (Folga)", f"{domingos_periodo_freq} dias", help="Domingos no período.")
            with col_freq4: st.metric("❌ Faltas (Seg-Sáb)", f"{dias_falta_freq} dias", delta=f"-{dias_falta_freq}" if dias_falta_freq > 0 else None, delta_color="inverse" if dias_falta_freq > 0 else "off")

            if dias_uteis_esperados_freq > 0:
                taxa_freq = min(100, (dias_trabalhados_freq / dias_uteis_esperados_freq) * 100)
                msg_freq, color_freq = ("Excelente", "success") if taxa_freq >= 95 else (("Boa", "info") if taxa_freq >= 80 else ("Atenção", "warning"))
                st.markdown(f"<div style='color: {'green' if color_freq == 'success' else ('blue' if color_freq == 'info' else 'orange')};'>🎯 **{msg_freq} frequência:** {taxa_freq:.1f}% dos dias úteis (Seg-Sáb) trabalhados!</div>", unsafe_allow_html=True)

        else: st.info("📊 Dados insuficientes para frequência (período curto ou sem dados).")
    else: st.info("📊 Dados insuficientes para ranking de dias.")

def display_insights(df_insights):
    """Exibe insights automáticos com estilo melhorado."""
    if df_insights.empty or len(df_insights) < 2: 
        st.info("Dados insuficientes para gerar insights automáticos.")
        return

    total_vendas_ins = df_insights["Total"].sum()
    media_por_dia_ins = df_insights.groupby("DiaSemana", observed=False)["Total"].mean().reset_index().dropna()
    melhor_dia_ins = media_por_dia_ins.loc[media_por_dia_ins["Total"].idxmax()] if not media_por_dia_ins.empty else None
    metodos_total_ins = {"Cartão": df_insights["Cartão"].sum(), "Dinheiro": df_insights["Dinheiro"].sum(), "PIX": df_insights["Pix"].sum()}
    metodos_total_ins = {k: v for k, v in metodos_total_ins.items() if v > 0}
    melhor_metodo_ins, percentual_melhor_ins, sugestao_taxa_ins = None, 0, ""
    if metodos_total_ins:
        melhor_metodo_ins = max(metodos_total_ins, key=metodos_total_ins.get)
        valor_melhor_metodo_ins = metodos_total_ins[melhor_metodo_ins]
        percentual_melhor_ins = (valor_melhor_metodo_ins / total_vendas_ins * 100) if total_vendas_ins > 0 else 0
        sugestao_taxa_ins = "<p style='margin-top:0.5rem;font-size:0.9rem;color:#b0bec5;'><i>Sugestão: Avalie taxas do Cartão, garanta troco para Dinheiro, promova PIX.</i></p>"
    
    df_sorted_ins = df_insights.sort_values("Data")
    variacao_semanal_ins, tendencia_texto_ins, tendencia_cor_ins = None, "insuficientes", COR_TEXTO_SECUNDARIO
    if len(df_sorted_ins) >= 14:
        datas_unicas_ins = sorted(df_sorted_ins['Data'].unique())
        if len(datas_unicas_ins) >= 14:
            media_ultima_ins = df_sorted_ins[df_sorted_ins['Data'].isin(datas_unicas_ins[-7:])]["Total"].mean()
            media_penultima_ins = df_sorted_ins[df_sorted_ins['Data'].isin(datas_unicas_ins[-14:-7])]["Total"].mean()
            if media_penultima_ins > 0:
                variacao_semanal_ins = ((media_ultima_ins - media_penultima_ins) / media_penultima_ins * 100)
                tendencia_texto_ins, tendencia_cor_ins = ("crescimento", "#63d2b4") if variacao_semanal_ins > 5 else (("queda", "#ec7063") if variacao_semanal_ins < -5 else ("estabilidade", "#f5b041"))
            else: tendencia_texto_ins = "base zero na penúltima semana"
        else: tendencia_texto_ins = "menos de 14 dias operados"
    
    st.subheader("🧠 Insights Automáticos Rápidos")
    col_ins1, col_ins2, col_ins3 = st.columns(3)
    with col_ins1:
        if melhor_dia_ins:
            st.markdown(f"<div class='insight-container' style='border-left-color:{CORES_MODO_ESCURO[0]};'><h4 style='color:{CORES_MODO_ESCURO[0]};'>🏆 Dia Mais Forte</h4><p>A <strong>{melhor_dia_ins['DiaSemana']}</strong> tem média de <strong>{format_brl(melhor_dia_ins['Total'])}</strong>.</p><p style='margin-top:0.5rem;font-size:0.9rem;color:#b0bec5;'><i>Sugestão: Reforce marketing/promoções neste dia.</i></p></div>", unsafe_allow_html=True)
        else: st.markdown(f"<div class='insight-container' style='border-left-color:{COR_TEXTO_SECUNDARIO};'><h4 style='color:{COR_TEXTO_SECUNDARIO};'>🏆 Dia Mais Forte</h4><p><i>Sem dados suficientes.</i></p></div>", unsafe_allow_html=True)
    with col_ins2:
        if melhor_metodo_ins:
            st.markdown(f"<div class='insight-container' style='border-left-color:{CORES_MODO_ESCURO[1]};'><h4 style='color:{CORES_MODO_ESCURO[1]};'>💳 Pagamento Preferido</h4><p><strong>{melhor_metodo_ins}</strong> é o mais usado ({percentual_melhor_ins:.1f}% do total).</p>{sugestao_taxa_ins}</div>", unsafe_allow_html=True)
        else: st.markdown(f"<div class='insight-container' style='border-left-color:{COR_TEXTO_SECUNDARIO};'><h4 style='color:{COR_TEXTO_SECUNDARIO};'>💳 Pagamento Preferido</h4><p><i>Sem dados suficientes.</i></p></div>", unsafe_allow_html=True)
    with col_ins3:
        st.markdown(f"<div class='insight-container' style='border-left-color:{tendencia_cor_ins};'><h4 style='color:{tendencia_cor_ins};'>📈 Tendência Semanal</h4><p>Comparando médias diárias, houve <strong>{tendencia_texto_ins}</strong>{' de <strong>' + str(abs(variacao_semanal_ins):.1f) + '%</strong>' if variacao_semanal_ins is not None else ''}.</p><p style='margin-top:0.5rem;font-size:0.9rem;color:#b0bec5;'><i>Sugestão: Analise fatores (promoções, eventos).</i></p></div>", unsafe_allow_html=True)

# --- Funções da Análise Contábil ---

def calculate_financial_results(df_dre_calc, salario_base_dre_calc, custo_contadora_dre_calc, cpv_percent_dre_calc):
    """Calcula os resultados financeiros para a DRE."""
    res = {}
    res['receita_bruta'] = df_dre_calc['Total'].sum()
    res['receita_tributavel_direto'] = df_dre_calc['Dinheiro'].sum() + df_dre_calc['Pix'].sum()
    res['impostos_sobre_vendas'] = res['receita_tributavel_direto'] * 0.06 # Simples Nacional 6%
    res['receita_liquida'] = res['receita_bruta'] - res['impostos_sobre_vendas']
    res['custo_produtos_vendidos'] = res['receita_bruta'] * (cpv_percent_dre_calc / 100.0)
    res['lucro_bruto'] = res['receita_liquida'] - res['custo_produtos_vendidos']
    res['despesas_com_pessoal'] = salario_base_dre_calc * 1.55 # Salário + ~55% encargos
    res['despesas_contabeis'] = custo_contadora_dre_calc
    res['total_despesas_operacionais'] = res['despesas_com_pessoal'] + res['despesas_contabeis']
    res['lucro_operacional'] = res['lucro_bruto'] - res['total_despesas_operacionais']
    res['resultado_financeiro'] = 0 # Simplificado
    res['lucro_antes_ir'] = res['lucro_operacional'] + res['resultado_financeiro']
    res['ir_csll'] = 0 # Já no Simples
    res['lucro_liquido'] = res['lucro_antes_ir'] - res['ir_csll']
    res['margem_bruta'] = (res['lucro_bruto'] / res['receita_liquida'] * 100) if res['receita_liquida'] else 0.0
    res['margem_operacional'] = (res['lucro_operacional'] / res['receita_liquida'] * 100) if res['receita_liquida'] else 0.0
    res['margem_liquida'] = (res['lucro_liquido'] / res['receita_liquida'] * 100) if res['receita_liquida'] else 0.0
    return res

def create_dre_textual(resultados_dre_txt, df_completo_dre_txt, anos_selecionados_dre_txt):
    """Cria a DRE em formato textual com base nos resultados calculados."""
    st.subheader("🧾 Demonstração do Resultado do Exercício (DRE)")
    periodo_str_dre_txt = "Período não definido"
    if not df_completo_dre_txt.empty and anos_selecionados_dre_txt:
        anos_int_dre_txt = [int(a) for a in anos_selecionados_dre_txt]
        df_periodo_dre_txt = df_completo_dre_txt[df_completo_dre_txt['Ano'].isin(anos_int_dre_txt)]
        if not df_periodo_dre_txt.empty:
            periodo_str_dre_txt = f"Período: {df_periodo_dre_txt['Data'].min().strftime('%d/%m/%Y')} a {df_periodo_dre_txt['Data'].max().strftime('%d/%m/%Y')}"
        else: periodo_str_dre_txt = f"Período: Ano(s) {', '.join(map(str, anos_selecionados_dre_txt))} (sem dados no filtro)"
    elif anos_selecionados_dre_txt: periodo_str_dre_txt = f"Período: Ano(s) {', '.join(map(str, anos_selecionados_dre_txt))} (sem dados carregados)"
    st.caption(periodo_str_dre_txt)
    html_dre_txt = f"""
    <div class="dre-textual-container"><table><thead><tr><th>Descrição</th><th style="text-align:right;">Valor (R$)</th></tr></thead><tbody>
    <tr><td>(+) Receita Operacional Bruta</td><td style="text-align:right;">{format_brl(resultados_dre_txt['receita_bruta'])}</td></tr>
    <tr><td>(-) Deduções da Receita Bruta (Simples Nacional)</td><td style="text-align:right;">({format_brl(abs(resultados_dre_txt['impostos_sobre_vendas']))})</td></tr>
    <tr><td><strong>(=) Receita Operacional Líquida</strong></td><td style="text-align:right;"><strong>{format_brl(resultados_dre_txt['receita_liquida'])}</strong></td></tr>
    <tr><td>(-) Custo dos Produtos Vendidos (CPV)</td><td style="text-align:right;">({format_brl(abs(resultados_dre_txt['custo_produtos_vendidos']))})</td></tr>
    <tr><td><strong>(=) Lucro Bruto</strong></td><td style="text-align:right;"><strong>{format_brl(resultados_dre_txt['lucro_bruto'])}</strong></td></tr>
    <tr><td>(-) Despesas Operacionais</td><td></td></tr>
    <tr><td>&nbsp;&nbsp;&nbsp;&nbsp;(-) Despesas com Pessoal</td><td style="text-align:right;">({format_brl(abs(resultados_dre_txt['despesas_com_pessoal']))})</td></tr>
    <tr><td>&nbsp;&nbsp;&nbsp;&nbsp;(-) Despesas Administrativas (Contabilidade)</td><td style="text-align:right;">({format_brl(abs(resultados_dre_txt['despesas_contabeis']))})</td></tr>
    <tr><td><strong>(=) Lucro Operacional (EBIT/LAJIR)</strong></td><td style="text-align:right;"><strong>{format_brl(resultados_dre_txt['lucro_operacional'])}</strong></td></tr>
    <tr><td>(+/-) Resultado Financeiro</td><td style="text-align:right;">{format_brl(resultados_dre_txt['resultado_financeiro'])}</td></tr>
    <tr><td><strong>(=) Lucro Antes do Imposto de Renda (LAIR)</strong></td><td style="text-align:right;"><strong>{format_brl(resultados_dre_txt['lucro_antes_ir'])}</strong></td></tr>
    <tr><td>(-) Imposto de Renda e CSLL (já no Simples)</td><td style="text-align:right;">({format_brl(abs(resultados_dre_txt['ir_csll']))})</td></tr>
    <tr><td><strong>(=) Lucro Líquido do Exercício</strong></td><td style="text-align:right;"><strong>{format_brl(resultados_dre_txt['lucro_liquido'])}</strong></td></tr>
    </tbody></table></div>"""
    st.markdown(html_dre_txt, unsafe_allow_html=True)

def create_financial_dashboard_altair(resultados_fin_dash):
    """Cria um dashboard visual simples com os principais resultados financeiros."""
    data_chart_fin = pd.DataFrame({
        'Componente': ['Receita Líquida', 'Custo Produtos', 'Despesas Pessoal', 'Despesas Contábeis', 'Lucro Líquido'],
        'Valor': [resultados_fin_dash['receita_liquida'], abs(resultados_fin_dash['custo_produtos_vendidos']), abs(resultados_fin_dash['despesas_com_pessoal']), abs(resultados_fin_dash['despesas_contabeis']), resultados_fin_dash['lucro_liquido']],
        'Tipo': ['Receita', 'Custo', 'Despesa', 'Resultado Final']
    })
    data_chart_fin_filt = data_chart_fin[(data_chart_fin['Valor'] != 0) | (data_chart_fin['Componente'] == 'Lucro Líquido')]
    if data_chart_fin_filt.empty: return None
    color_scale_fin = alt.Scale(domain=['Receita', 'Custo', 'Despesa', 'Resultado Final'], range=['#1f77b4', '#ff7f0e', '#d62728', '#2ca02c' if resultados_fin_dash['lucro_liquido'] >= 0 else '#8c564b'])
    bars_fin = alt.Chart(data_chart_fin_filt).mark_bar(cornerRadiusTop=5).encode(
        x=alt.X('Componente:N', sort=None, title=None, axis=alt.Axis(labels=True, labelAngle=-45, labelColor=COR_TEXTO_SECUNDARIO)),
        y=alt.Y('Valor:Q', title='Valor (R$)', axis=alt.Axis(labelColor=COR_TEXTO_SECUNDARIO, titleColor=COR_TEXTO_PRINCIPAL)),
        color=alt.Color('Tipo:N', scale=color_scale_fin, legend=alt.Legend(title="Tipo", labelColor=COR_TEXTO_SECUNDARIO, titleColor=COR_TEXTO_PRINCIPAL, orient="top-left")),
        tooltip=[alt.Tooltip('Componente:N', title='Componente'), alt.Tooltip('Valor:Q', title='Valor (R$)', format=',.2f')]
    )
    text_chart_fin = bars_fin.mark_text(align='center', baseline='bottom', dy=-7, color=COR_TEXTO_PRINCIPAL, fontWeight='bold').encode(text=alt.Text('Valor:Q', format=',.0f'))
    chart_final_fin = (bars_fin + text_chart_fin).properties(
        title=alt.TitleParams(text='Visão Geral: Receita, Custos, Despesas e Lucro', color=COR_TEXTO_PRINCIPAL, fontSize=16, anchor='middle'),
        height=400, background="transparent"
    ).configure_view(strokeOpacity=0)
    return chart_final_fin

# --- Interface Principal da Aplicação ---
def main():
    if "show_table" not in st.session_state: st.session_state.show_table = False
    if "last_registered_data" not in st.session_state: st.session_state.last_registered_data = None

    st.markdown(f"""<div class="header-container"><div class="logo-container">
        <img src="{LOGO_URL}" class="logo-image" alt="Logo Clips Burger">
        <div><h1>SISTEMA FINANCEIRO - CLIP'S BURGER</h1><p>Gestão inteligente de vendas - {datetime.now().year}</p></div>
    </div></div>""", unsafe_allow_html=True)

    df_raw_main = read_sales_data()
    df_processed_main = process_data(df_raw_main)

    with st.sidebar:
        st.header("🔍 Filtros de Análise")
        st.markdown("---")
        anos_disp_main = sorted(df_processed_main["Ano"].dropna().unique().astype(int), reverse=True) if not df_processed_main.empty and "Ano" in df_processed_main.columns else []
        def_ano_main = [datetime.now().year] if datetime.now().year in anos_disp_main else ([anos_disp_main[0]] if anos_disp_main else [])
        sel_anos_main = st.multiselect("Ano(s):", options=anos_disp_main, default=def_ano_main)
        sel_meses_main = []
        if sel_anos_main:
            meses_anos_filt_main = sorted(df_processed_main[df_processed_main["Ano"].isin(sel_anos_main)]["Mês"].dropna().unique().astype(int))
            mapa_meses_main = {m: meses_ordem[m-1] for m in meses_anos_filt_main}
            def_mes_main = [datetime.now().month] if datetime.now().month in meses_anos_filt_main else meses_anos_filt_main
            sel_meses_main = st.multiselect("Mês(es):", options=meses_anos_filt_main, format_func=lambda m: mapa_meses_main.get(m,m), default=def_mes_main)
        else: st.multiselect("Mês(es):", options=[], disabled=True, help="Selecione um ano.")

    df_filt_main = df_processed_main.copy()
    if sel_anos_main: df_filt_main = df_filt_main[df_filt_main["Ano"].isin(sel_anos_main)]
    if sel_meses_main: df_filt_main = df_filt_main[df_filt_main["Mês"].isin(sel_meses_main)]

    with st.sidebar:
        st.markdown("---")
        st.subheader("Resumo do Período Filtrado")
        if not df_filt_main.empty:
            st.metric("Registros de Venda", len(df_filt_main))
            st.metric("Faturamento Bruto", format_brl(df_filt_main["Total"].sum()))
        else: st.info("Nenhum registro com os filtros selecionados.")
        st.markdown("<hr style='margin:1rem 0;'>", unsafe_allow_html=True)
        st.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    tab_reg, tab_dash, tab_cont = st.tabs(["📝 Registrar Venda", "📊 Dashboard", "💰 Análise Contábil"])

    with tab_reg:
        st.header("📝 Registrar Nova Venda Diária")
        st.markdown("---")
        with st.form(key="reg_venda_form", clear_on_submit=True):
            data_venda_reg = st.date_input("📅 Data da Venda", value=dt.date.today(), format="DD/MM/YYYY")
            c1_form, c2_form, c3_form = st.columns(3)
            with c1_form: val_cartao_reg = st.number_input("💳 Cartão (R$)", min_value=0.0, value=None, format="%.2f", placeholder="150.75")
            with c2_form: val_din_reg = st.number_input("💵 Dinheiro (R$)", min_value=0.0, value=None, format="%.2f", placeholder="80.00")
            with c3_form: val_pix_reg = st.number_input("📱 PIX (R$)", min_value=0.0, value=None, format="%.2f", placeholder="120.50")
            submit_reg = st.form_submit_button("✅ Registrar Venda", use_container_width=True, type="primary")
            if submit_reg:
                cart_sub, din_sub, pix_sub = (val_cartao_reg or 0.0), (val_din_reg or 0.0), (val_pix_reg or 0.0)
                total_sub = cart_sub + din_sub + pix_sub
                if total_sub > 0:
                    ws_gspread = get_worksheet()
                    if ws_gspread and add_data_to_sheet(data_venda_reg, cart_sub, din_sub, pix_sub, ws_gspread):
                        st.success(f"✅ Venda de {format_brl(total_sub)} registrada para {data_venda_reg.strftime('%d/%m/%Y')}!")
                        st.session_state.show_table = True
                        df_raw_post_reg = read_sales_data()
                        df_proc_post_reg = process_data(df_raw_post_reg)
                        df_filt_post_reg = df_proc_post_reg.copy()
                        if sel_anos_main: df_filt_post_reg = df_filt_post_reg[df_filt_post_reg["Ano"].isin(sel_anos_main)]
                        if sel_meses_main: df_filt_post_reg = df_filt_post_reg[df_filt_post_reg["Mês"].isin(sel_meses_main)]
                        st.session_state.last_registered_data = df_filt_post_reg
                        st.rerun()
                    elif not ws_gspread: st.error("❌ Falha ao conectar à planilha.")
                    else: st.error("❌ Falha ao registrar na planilha.")
                else: st.warning("⚠️ Valor total da venda deve ser > 0.")
        if st.session_state.show_table and st.session_state.last_registered_data is not None and not st.session_state.last_registered_data.empty:
            st.markdown("---"); st.subheader("🧾 Tabela de Vendas (Conforme Filtros)")
            df_show_reg = st.session_state.last_registered_data
            cols_show_reg = ["DataFormatada", "DiaSemana", "Cartão", "Dinheiro", "Pix", "Total"]
            cols_exist_reg = [c for c in cols_show_reg if c in df_show_reg.columns]
            if cols_exist_reg:
                st.dataframe(df_show_reg[cols_exist_reg].sort_values(by="DataFormatada", ascending=False), use_container_width=True, height=400, hide_index=True,
                               column_config={"DataFormatada": "Data", "DiaSemana": "Dia da Semana",
                                              "Cartão": st.column_config.NumberColumn("Cartão (R$)", format="R$ %.2f"),
                                              "Dinheiro": st.column_config.NumberColumn("Dinheiro (R$)", format="R$ %.2f"),
                                              "Pix": st.column_config.NumberColumn("PIX (R$)", format="R$ %.2f"),
                                              "Total": st.column_config.NumberColumn("Total (R$)", format="R$ %.2f")})
            else: st.info("Colunas para tabela não encontradas.")
        elif st.session_state.show_table: st.info("Nenhum dado para tabela com filtros atuais.")

    with tab_dash:
        st.header("📊 Dashboard Geral de Vendas")
        st.markdown("---")
        if df_filt_main.empty:
            st.warning("⚠️ Sem dados para dashboard com filtros. Ajuste ou registre vendas.")
        else:
            st.subheader("📈 Resumo Financeiro"); display_resumo_financeiro(df_filt_main); st.markdown("---")
            st.subheader("🗓️ Calendário de Atividade"); ano_hm_dash = sel_anos_main[0] if sel_anos_main else (datetime.now().year if datetime.now().year in anos_disp_main else None)
            if ano_hm_dash:
                try:
                    hm_anual_fig, df_ano_hm_dash = criar_calendario_anual_espacamento_correto(df_processed_main, ano_hm_dash)
                    if hm_anual_fig: st.plotly_chart(hm_anual_fig, use_container_width=True)
                    if df_ano_hm_dash is not None and not df_ano_hm_dash.empty:
                        hm_mensal_fig, _ = criar_heatmap_vendas_mensais_espacamento_correto(df_ano_hm_dash)
                        if hm_mensal_fig: st.plotly_chart(hm_mensal_fig, use_container_width=True)
                except Exception as e_hm_dash: st.error(f"Erro ao gerar heatmap: {e_hm_dash}")
            else: st.info("Selecione ano ou registre vendas para calendário.")
            st.markdown("---"); st.subheader("💹 Faturamento Acumulado"); grafico_acum_dash = create_cumulative_evolution_chart(df_filt_main)
            if grafico_acum_dash: st.altair_chart(grafico_acum_dash, use_container_width=True)
            st.markdown("---"); st.subheader("💳 Métodos de Pagamento"); display_metodos_pagamento(df_filt_main); st.markdown("---")
            st.subheader("📅 Análise Diária e Distribuição"); c_daily, c_radial = st.columns([3,2])
            with c_daily:
                st.markdown("###### Vendas Diárias por Método"); grafico_vendas_diarias_emp_dash = create_advanced_daily_sales_chart(df_filt_main)
                if grafico_vendas_diarias_emp_dash: st.altair_chart(grafico_vendas_diarias_emp_dash, use_container_width=True)
            with c_radial:
                st.markdown("###### Distribuição por Pagamento"); grafico_radial_dash = create_radial_plot(df_filt_main)
                if grafico_radial_dash: st.altair_chart(grafico_radial_dash, use_container_width=True)
            st.markdown("---"); st.subheader("📊 Média de Vendas por Dia da Semana"); grafico_wd_dash = create_weekday_sales_chart(df_filt_main)
            if grafico_wd_dash: st.altair_chart(grafico_wd_dash, use_container_width=True)
            st.markdown("---"); display_ranking_e_frequencia(df_filt_main); st.markdown("---")
            display_insights(df_filt_main); st.markdown("---")

    with tab_cont:
        st.header("💰 Análise Contábil e Financeira (DRE)"); st.markdown("""DRE simplificada (Simples Nacional ~6% sobre Dinheiro/PIX). Premissas configuráveis abaixo.""""); st.markdown("---")
        with st.container(border=True):
            st.subheader("⚙️ Parâmetros para Simulação da DRE"); c_p_dre1, c_p_dre2, c_p_dre3 = st.columns(3)
            with c_p_dre1: sal_base_dre = st.number_input("💼 Salário Base (Mensal R$)", min_value=0.0, value=1550.0, format="%.2f", help="Salário base. Encargos (~55%) adicionados.", key="sal_dre")
            with c_p_dre2: cust_cont_dre = st.number_input("📋 Contabilidade (Mensal R$)", min_value=0.0, value=316.0, format="%.2f", key="cont_dre")
            with c_p_dre3: cpv_perc_dre = st.number_input("📦 CPV (%)", min_value=0.0, max_value=100.0, value=30.0, format="%.1f", help="% da Receita Bruta para insumos.", key="cpv_dre")
        st.markdown("---")
        if df_filt_main.empty or 'Total' not in df_filt_main.columns:
            st.warning("📊 Sem dados de vendas para análise contábil. Ajuste filtros ou registre vendas.")
        else:
            res_dre_cont = calculate_financial_results(df_filt_main, sal_base_dre, cust_cont_dre, cpv_perc_dre)
            with st.container(border=True): create_dre_textual(res_dre_cont, df_filt_main, sel_anos_main)
            st.markdown("---"); grafico_dash_dre = create_financial_dashboard_altair(res_dre_cont)
            if grafico_dash_dre: st.altair_chart(grafico_dash_dre, use_container_width=True)
            st.markdown("---")
            with st.container(border=True):
                st.subheader("📈 Margens e Indicadores"); c_m_dre1, c_m_dre2, c_m_dre3 = st.columns(3)
                with c_m_dre1:
                    st.metric("📊 Margem Bruta", f"{res_dre_cont['margem_bruta']:.2f}%", help="Lucro Bruto / Receita Líquida")
                    st.metric("🏛️ Carga Trib. (Simples)", f"{(res_dre_cont['impostos_sobre_vendas']/res_dre_cont['receita_bruta']*100) if res_dre_cont['receita_bruta'] else 0:.2f}%", help="% Simples / Receita Bruta")
                with c_m_dre2:
                    st.metric("💼 Margem Operacional", f"{res_dre_cont['margem_operacional']:.2f}%", help="Lucro Operacional / Receita Líquida")
                    st.metric("👥 Peso Desp. Pessoal", f"{(res_dre_cont['despesas_com_pessoal']/res_dre_cont['receita_bruta']*100) if res_dre_cont['receita_bruta'] else 0:.2f}%", help="% Desp. Pessoal / Receita Bruta")
                with c_m_dre3:
                    st.metric("💰 Margem Líquida", f"{res_dre_cont['margem_liquida']:.2f}%", help="Lucro Líquido / Receita Líquida")
                    st.metric("📦 Peso do CPV", f"{(res_dre_cont['custo_produtos_vendidos']/res_dre_cont['receita_bruta']*100) if res_dre_cont['receita_bruta'] else 0:.2f}%", help="% CPV / Receita Bruta")
            st.markdown("---")
            with st.expander("📋 Ver Resumo Executivo da DRE", expanded=False):
                c_exec_dre1, c_exec_dre2 = st.columns(2)
                with c_exec_dre1:
                    st.markdown("**💰 Receitas:**"); st.write(f"• Receita Bruta: {format_brl(res_dre_cont['receita_bruta'])}"); st.write(f"• Receita Líquida: {format_brl(res_dre_cont['receita_liquida'])}")
                    st.markdown("**📊 Resultados:**"); st.write(f"• Lucro Bruto: {format_brl(res_dre_cont['lucro_bruto'])}"); st.write(f"• Lucro Operacional: {format_brl(res_dre_cont['lucro_operacional'])}"); st.write(f"• Lucro Líquido: {format_brl(res_dre_cont['lucro_liquido'])}")
                with c_exec_dre2:
                    st.markdown("**💸 Custos e Despesas:**"); st.write(f"• Impostos (Simples): {format_brl(res_dre_cont['impostos_sobre_vendas'])}"); st.write(f"• CPV: {format_brl(res_dre_cont['custo_produtos_vendidos'])}"); st.write(f"• Desp. Pessoal: {format_brl(res_dre_cont['despesas_com_pessoal'])}"); st.write(f"• Contabilidade: {format_brl(res_dre_cont['despesas_contabeis'])}")
                    st.markdown("**🎯 Avaliação Rápida:**")
                    if res_dre_cont['lucro_liquido'] > 0: st.success(f"✅ POSITIVO de {format_brl(res_dre_cont['lucro_liquido'])}!")
                    elif res_dre_cont['lucro_liquido'] == 0: st.warning("⚠️ NULO (Break-even).")
                    else: st.error(f"❌ NEGATIVO de {format_brl(res_dre_cont['lucro_liquido'])}. Atenção!")
            st.info("💡 Nota: DRE simplificada. Taxas de cartão não deduzidas explicitamente. Consulte um contador.")

if __name__ == "__main__":
    main()