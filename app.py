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

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = "1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg" # MANTENHA O SEU ID CORRETO
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
        .st-emotion-cache-1l269bu > div {{ 
             flex-direction: column;
        }}
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
@st.cache_resource
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
        if not credentials_dict:
            st.error("As credenciais do Google em st.secrets estão vazias.")
            return None

        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Erro de autenticação com Google: {e}")
        return None

@st.cache_resource
def get_worksheet():
    """Retorna o objeto worksheet da planilha especificada."""
    gc = get_google_auth()
    if gc:
        try:
            spreadsheet = gc.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
            return worksheet
        except SpreadsheetNotFound:
            st.error(f"Planilha com ID \'{SPREADSHEET_ID}\' não encontrada.")
            return None
        except Exception as e:
            st.error(f"Erro ao acessar a planilha \'{WORKSHEET_NAME}\': {e}")
            return None
    return None

# --- Funções de Manipulação de Dados ---
@st.cache_data(ttl=600) # Cache de 10 minutos
def read_sales_data():
    """Lê todos os registros da planilha de vendas e retorna como DataFrame."""
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records()
            if not rows:
                st.info("A planilha de vendas está vazia.")
                return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix"])

            df = pd.DataFrame(rows)

            # Garantir que as colunas de valor existam e sejam numéricas
            for col in ["Cartão", "Dinheiro", "Pix"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    df[col] = 0 # Adiciona a coluna com zeros se não existir

            # Tratar coluna 'Data'
            if "Data" not in df.columns:
                 st.warning("Coluna \'Data\' não encontrada na planilha. Criando coluna vazia.")
                 df["Data"] = pd.NaT # Cria coluna de data vazia
            else:
                # Tentar múltiplos formatos de data
                try:
                    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
                except ValueError: # Se o formato acima falhar, tenta inferir
                    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

            # Remover linhas onde a data não pôde ser convertida
            df.dropna(subset=["Data"], inplace=True)

            return df
        except Exception as e:
            st.error(f"Erro ao ler dados da planilha: {e}")
            return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix"]) # Retorna DF vazio em caso de erro
    return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix"]) # Retorna DF vazio se worksheet for None

def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet_obj):
    """Adiciona uma nova linha de dados à planilha Google Sheets."""
    if worksheet_obj is None:
        st.error("Não foi possível acessar a planilha para adicionar dados.")
        return False
    try:
        # Garantir que os valores são float
        cartao_val = float(cartao) if cartao else 0.0
        dinheiro_val = float(dinheiro) if dinheiro else 0.0
        pix_val = float(pix) if pix else 0.0

        # Formata a data como string DD/MM/YYYY para consistência na planilha
        formatted_date_str = date.strftime("%d/%m/%Y")

        new_row = [formatted_date_str, cartao_val, dinheiro_val, pix_val]
        worksheet_obj.append_row(new_row)
        # Limpar caches relevantes após adicionar dados
        st.cache_data.clear() # Limpa cache de dados (read_sales_data, process_data)
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
        st.warning("DataFrame de entrada vazio ou sem coluna \'Data\' para processamento.")
        # Define colunas esperadas para um DataFrame vazio estruturado
        cols = ["Data", "Cartão", "Dinheiro", "Pix", "Total", "Ano", "Mês", "MêsNome", "AnoMês", "DataFormatada", "DiaSemana", "DiaDoMes"]
        empty_df = pd.DataFrame(columns=cols)
        # Define tipos para colunas numéricas e de data para evitar erros posteriores
        for col in ["Cartão", "Dinheiro", "Pix", "Total", "Ano", "Mês", "DiaDoMes"]:
             empty_df[col] = pd.Series(dtype="float")
        empty_df["Data"] = pd.Series(dtype="datetime64[ns]")
        for col in ["MêsNome", "AnoMês", "DataFormatada", "DiaSemana"]:
             empty_df[col] = pd.Series(dtype="object")
        return empty_df

    df = df_input.copy()

    # Garantir que 'Data' é datetime
    if not pd.api.types.is_datetime64_any_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df.dropna(subset=["Data"], inplace=True) # Remove linhas onde Data não pôde ser convertida

    # Garantir que colunas de valor são numéricas
    for col in ["Cartão", "Dinheiro", "Pix"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0 # Adiciona coluna com zeros se não existir

    df["Total"] = df["Cartão"] + df["Dinheiro"] + df["Pix"]

    # Extrair informações de data
    df["Ano"] = df["Data"].dt.year
    df["Mês"] = df["Data"].dt.month
    df["MêsNome"] = df["Mês"].apply(lambda x: meses_ordem[x-1] if pd.notna(x) and 1 <= x <= 12 else None)
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
        return f"R$ {value:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")
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
    """Cria um gráfico de vendas diárias empilhadas com visual limpo e profissional."""
    if df.empty or 'Data' not in df.columns:
        st.info("DataFrame vazio ou sem coluna 'Data' para gráfico de vendas diárias.")
        return None
    
    required_cols = ['Cartão', 'Dinheiro', 'Pix']
    if not all(col in df.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df.columns]
        st.info(f"Colunas ausentes para gráfico de vendas diárias: {missing}")
        return None
    
    df_sorted = df.sort_values('Data').copy()
    df_sorted.dropna(subset=['Data'] + required_cols, inplace=True) # Remove NAs nas colunas relevantes
    
    if df_sorted.empty:
        st.info("Sem dados válidos após limpeza para gráfico de vendas diárias.")
        return None
    
    # Agrupar por data para evitar duplicatas e somar valores diários
    df_grouped = df_sorted.groupby('Data')[required_cols].sum().reset_index()
    
    # Criar DataFormatada para labels do eixo X
    df_grouped['DataFormatada'] = df_grouped['Data'].dt.strftime('%d/%m')
    
    # Transformar dados para formato longo (ideal para empilhamento no Altair)
    df_melted = df_grouped.melt(
        id_vars=['Data', 'DataFormatada'],
        value_vars=required_cols,
        var_name='Método',
        value_name='Valor'
    )
    
    # Filtrar apenas valores positivos para não poluir o gráfico
    df_melted = df_melted[df_melted['Valor'] > 0]
    
    if df_melted.empty:
        st.info("Sem valores de venda positivos para exibir no gráfico diário.")
        return None
    
    # Cores específicas para os métodos (pode ajustar conforme preferência)
    cores_metodos = {
        'Dinheiro': '#FF8C00', # Laranja escuro
        'Pix': '#70AD47',      # Verde
        'Cartão': '#5B9BD5'    # Azul acinzentado
    }
    
    # Ordem dos métodos para empilhamento (de baixo para cima no gráfico)
    ordem_metodos = ['Dinheiro', 'Pix', 'Cartão']
    
    # Criar o gráfico de barras empilhadas
    chart = alt.Chart(df_melted).mark_bar(
        size=30,                # Largura das barras
        stroke='white',         # Linha de separação entre segmentos da barra
        strokeWidth=1.5         # Espessura da linha de separação
    ).encode(
        x=alt.X(
            'DataFormatada:O',    # 'O' para ordinal (categórico ordenado)
            title='Data',         # Título do eixo X
            axis=alt.Axis(
                labelAngle=0,     # Labels do eixo X retos
                labelFontSize=10,
                labelColor='#666666', # Cor dos labels
                grid=False,       # Sem grid vertical
                ticks=False,      # Sem marcas de tick
                domain=False      # Sem linha do eixo X
            )
        ),
        y=alt.Y(
            'Valor:Q',            # 'Q' para quantitativo
            title='Vendas (R$)',  # Título do eixo Y
            stack='zero',         # Empilhamento a partir do zero
            axis=alt.Axis(
                labelFontSize=10,
                labelColor='#666666',
                grid=True,        # Grid horizontal
                gridColor='#E0E0E0', # Cor do grid (mais suave)
                gridOpacity=0.7,  # Opacidade do grid
                ticks=False,      # Sem marcas de tick
                domain=False      # Sem linha do eixo Y
            )
        ),
        color=alt.Color(
            'Método:N',           # 'N' para nominal (categórico não ordenado)
            scale=alt.Scale(
                domain=ordem_metodos, # Garante a ordem das cores na legenda e barras
                range=[cores_metodos.get(m, "#CCCCCC") for m in ordem_metodos] # Mapeia cores
            ),
            legend=alt.Legend(
                title=None,       # Sem título na legenda
                orient='bottom',  # Posição da legenda
                direction='horizontal',
                labelFontSize=11,
                labelColor=COR_TEXTO_PRINCIPAL if st.get_option("theme.base") == "dark" else "#333333", # Adapta cor da legenda ao tema
                symbolSize=100,   # Tamanho dos símbolos na legenda
                symbolType='square' # Formato dos símbolos
            )
        ),
        order=alt.Order( # Controla a ordem de empilhamento dos segmentos
            'Método:N',
            sort=ordem_metodos 
        ),
        tooltip=[ # Informações ao passar o mouse
            alt.Tooltip('DataFormatada:O', title='Data'),
            alt.Tooltip('Método:N', title='Método'),
            alt.Tooltip('Valor:Q', title='Valor (R$)', format=',.2f')
        ]
    ).properties(
        height=350,
        title=alt.TitleParams(
            text='Vendas Diárias por Método de Pagamento',
            color=COR_TEXTO_PRINCIPAL if st.get_option("theme.base") == "dark" else "#333333",
            fontSize=16,
            anchor='middle'
        )
    ).configure_view( # Configurações da área de plotagem
        stroke=None # Remove qualquer borda da área de plotagem
    ).configure_axis( # Configurações globais dos eixos
        labelColor=COR_TEXTO_SECUNDARIO,
        titleColor=COR_TEXTO_PRINCIPAL
    ).configure_title( # Configurações globais do título do gráfico
         color=COR_TEXTO_PRINCIPAL,
         fontSize=16
    ).configure_legend( # Configurações globais da legenda
        titleColor=COR_TEXTO_PRINCIPAL,
        labelColor=COR_TEXTO_SECUNDARIO
    ).resolve_scale( # Garante que a escala de cores é independente se houver múltiplas camadas (boa prática)
        color='independent'
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
        # stroke=cor_linha, # stroke na área pode ser redundante com line
        # strokeWidth=3
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
        
        text = alt.Chart(point_data).mark_text(
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
        
        chart = alt.layer(area, point, text).properties( # Combina área, ponto e texto
            height=500,
            background="transparent"
        ).configure_view(
            strokeOpacity=0
        ).interactive() # Permite zoom e pan
    else:
        chart = area.properties(
            height=500,
            background="transparent"
        ).configure_view(
            strokeOpacity=0
        ).interactive()

    return chart

# --- Funções do Heatmap de Calendário ---
def criar_calendario_anual_espacamento_correto(df, ano):
    """Cria calendário anual com maior distância entre nomes dos dias e o gráfico"""
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        st.warning(f"Dados insuficientes para gerar o heatmap de calendário para {ano}.")
        return None, None

    # CORREÇÃO: Converter ano para int Python nativo
    ano = int(ano) # Garante que 'ano' é um int Python
    
    df_year = df[df["Data"].dt.year == ano].copy()
    if df_year.empty:
        st.info(f"Sem dados de vendas para o ano {ano}.")
        return None, None

    # Criar range completo do ano CORRETO (usando int para ano)
    dates_completo = pd.date_range(start=f'{ano}-01-01', end=f'{ano}-12-31', freq='D')

    # Criar DataFrame completo para o ano todo, preenchendo dias sem vendas
    dados_ano_completo = []
    for date_obj in dates_completo:
        # Verificar se a data existe no DataFrame filtrado do ano
        if date_obj in df_year['Data'].values:
            row = df_year[df_year['Data'] == date_obj].iloc[0]
            dados_ano_completo.append({
                'Data': date_obj,
                'Cartão': row.get('Cartão', 0), # Usar .get com default para segurança
                'Dinheiro': row.get('Dinheiro', 0),
                'Pix': row.get('Pix', 0),
                'Total_Vendas': row.get('Total', 0)
            })
        else: # Dia sem vendas registradas
            dados_ano_completo.append({
                'Data': date_obj,
                'Cartão': 0,
                'Dinheiro': 0,
                'Pix': 0,
                'Total_Vendas': 0
            })

    df_ano_completo = pd.DataFrame(dados_ano_completo)
    df_ano_completo['Data'] = pd.to_datetime(df_ano_completo['Data']) # Garante tipo datetime

    # Informações de data para posicionamento e hover
    df_ano_completo['data_str'] = df_ano_completo['Data'].dt.strftime('%d/%m/%Y')
    df_ano_completo['dia_semana_num'] = df_ano_completo['Data'].dt.dayofweek # 0=Segunda, ..., 6=Domingo

    # CORREÇÃO: Usar datetime.date com int Python para o primeiro dia do ano
    primeiro_dia_ano_obj = dt.date(ano, 1, 1) # Objeto date
    primeiro_dia_semana_ano = primeiro_dia_ano_obj.weekday() # Dia da semana do primeiro dia do ano

    # Listas para armazenar dados para o heatmap
    x_positions = [] # Posição da semana no ano (coluna do heatmap)
    y_positions = [] # Dia da semana (linha do heatmap)
    valores_categoria = [] # Categoria de valor para a cor
    hover_texts = [] # Texto para tooltip

    for _, row in df_ano_completo.iterrows():
        data_atual_obj = row['Data'].date() # Converte para objeto date para cálculo de dias
        
        # Calcular dias desde o início do ano
        dias_desde_inicio_ano = (data_atual_obj - primeiro_dia_ano_obj).days

        # Calcular posição da semana (x) e dia da semana (y) no grid do heatmap
        # Adiciona o weekday do primeiro dia do ano para alinhar corretamente
        semana_no_ano = (dias_desde_inicio_ano + primeiro_dia_semana_ano) // 7
        dia_da_semana_grid = (dias_desde_inicio_ano + primeiro_dia_semana_ano) % 7

        x_positions.append(semana_no_ano)
        y_positions.append(dia_da_semana_grid) # 0-6 representando Seg-Dom

        # Classificar valores em categorias para as cores do heatmap
        total_vendas_dia = row['Total_Vendas']
        if total_vendas_dia == 0:
            categoria = 0 # Sem vendas
        elif total_vendas_dia < 1500:
            categoria = 1 # Faixa 1
        elif total_vendas_dia < 2500:
            categoria = 2 # Faixa 2
        elif total_vendas_dia < 3000:
            categoria = 3 # Faixa 3
        else:
            categoria = 4 # Faixa 4 (mais alta)

        valores_categoria.append(categoria)

        # Criar texto do hover
        if total_vendas_dia > 0:
            hover_text = (f"📅 {row['data_str']}<br>"
                         f"💰 Total: {format_brl(total_vendas_dia)}<br>"
                         f"💳 Cartão: {format_brl(row['Cartão'])}<br>"
                         f"💵 Dinheiro: {format_brl(row['Dinheiro'])}<br>"
                         f"📱 Pix: {format_brl(row['Pix'])}")
        else:
            hover_text = f"📅 {row['data_str']}<br>❌ Sem vendas"
        hover_texts.append(hover_text)

    # Criar matriz para o heatmap
    max_semana_heatmap = max(x_positions) + 1 # Número de colunas
    matriz_vendas_heatmap = np.full((7, max_semana_heatmap), np.nan) # 7 dias, nan para gaps
    matriz_hover_heatmap = np.full((7, max_semana_heatmap), '', dtype=object)

    for x, y, valor_cat, hover_txt in zip(x_positions, y_positions, valores_categoria, hover_texts):
        if 0 <= y < 7 and 0 <= x < max_semana_heatmap: # Segurança
            matriz_vendas_heatmap[y, x] = valor_cat
            matriz_hover_heatmap[y, x] = hover_txt

    # Escala de cores para o heatmap (estilo GitHub contributions)
    escala_cores_heatmap = [
        [0.0, '#161b22'],    # Cor para categoria 0 (sem vendas)
        [0.001, '#39D353'],  # Início da cor para categoria 1
        [0.25, '#39D353'],   # Fim da cor para categoria 1
        [0.251, '#37AB4B'], # Início da cor para categoria 2
        [0.5, '#37AB4B'],    # Fim da cor para categoria 2
        [0.501, '#006D31'], # Início da cor para categoria 3
        [0.75, '#006D31'],   # Fim da cor para categoria 3
        [0.751, '#0D4428'], # Início da cor para categoria 4
        [1.0, '#0D4428']     # Fim da cor para categoria 4
    ]

    # Criar figura do heatmap com Plotly
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=matriz_vendas_heatmap,
        text=matriz_hover_heatmap,
        hovertemplate='%{text}<extra></extra>', # <extra></extra> remove trace info
        colorscale=escala_cores_heatmap,
        showscale=False, # Não mostrar a barra de escala de cores
        zmin=0, # Mínimo para a escala de cores (categoria 0)
        zmax=4, # Máximo para a escala de cores (categoria 4)
        xgap=3, # Espaçamento horizontal entre células
        ygap=3, # Espaçamento vertical entre células
        hoverongaps=False # Não mostrar tooltip em gaps
    ))

    # Calcular posições dos labels dos meses para o eixo X
    nomes_meses_labels = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    posicoes_meses_ticks = []
    for mes_idx in range(1, 13): # Para cada mês de 1 a 12
        primeiro_dia_mes_obj = dt.date(ano, mes_idx, 1)
        dias_desde_inicio_ano_mes = (primeiro_dia_mes_obj - primeiro_dia_ano_obj).days
        semana_mes_tick = (dias_desde_inicio_ano_mes + primeiro_dia_semana_ano) // 7
        posicoes_meses_ticks.append(semana_mes_tick)
    
    # Remove duplicatas e garante ordem (caso meses comecem na mesma semana)
    posicoes_meses_unicas, indices_unicos = np.unique(posicoes_meses_ticks, return_index=True)
    nomes_meses_finais = [nomes_meses_labels[i] for i in indices_unicos]


    # Layout do heatmap
    fig_heatmap.update_layout(
        title=f"📊 Calendário de Vendas {ano}",
        paper_bgcolor='rgba(0,0,0,0)', # Fundo transparente
        plot_bgcolor='rgba(0,0,0,0)',  # Fundo da área de plotagem transparente
        font=dict(color=COR_TEXTO_PRINCIPAL, family="Arial"),

        xaxis=dict(
            title="",
            showgrid=False, # Sem grid vertical
            zeroline=False, # Sem linha zero
            tickmode='array',
            tickvals=posicoes_meses_unicas, # Posições dos ticks dos meses
            ticktext=nomes_meses_finais,    # Nomes dos meses
            tickfont=dict(color=COR_TEXTO_PRINCIPAL, size=14),
            side='top', # Meses no topo
            tickangle=0, # Labels dos meses retos
            ticklabelstandoff=5 # Distância dos labels do eixo
        ),

        yaxis=dict(
            title="",
            showgrid=False, # Sem grid horizontal
            zeroline=False, # Sem linha zero
            tickmode='array',
            tickvals=[0, 1, 2, 3, 4, 5, 6], # Posições dos dias da semana
            ticktext=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'], # Nomes dos dias
            tickfont=dict(color=COR_TEXTO_PRINCIPAL, size=14),
            ticklen=0, # Comprimento dos ticks (0 para remover)
            ticklabelstandoff=15, # Aumenta a distância dos nomes dos dias
            autorange="reversed" # Domigo no topo, Sábado em baixo (se 0=Seg)
        ),

        height=350, # Altura do gráfico
        title_x=0.5, # Centralizar título
        title_font=dict(size=18, color=COR_TEXTO_PRINCIPAL),
        margin=dict(l=70, r=20, t=80, b=20) # Ajustar margens
    )

    return fig_heatmap, df_ano_completo # Retorna a figura e o DataFrame processado para o ano

def criar_heatmap_vendas_mensais_espacamento_correto(df_anual_completo):
    """Função para criar heatmap mensal horizontal com espaçamento correto."""
    if df_anual_completo.empty:
        return None, None

    # Filtra apenas dias com vendas para cálculo mensal (se necessário, mas aqui somamos tudo)
    df_vendas_para_mes = df_anual_completo.copy() # Usar todos os dados, incluindo dias com zero vendas
    df_vendas_para_mes['MesNum'] = df_vendas_para_mes['Data'].dt.month
    
    # Agrupar por mês para somar vendas
    vendas_mensais_agg = df_vendas_para_mes.groupby('MesNum').agg(
        Total_Vendas_Mes=('Total_Vendas', 'sum'),
        Cartao_Mes=('Cartão', 'sum'),
        Dinheiro_Mes=('Dinheiro', 'sum'),
        Pix_Mes=('Pix', 'sum')
    ).reset_index()

    nomes_meses_curto = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    # Preparar dados para o heatmap mensal (1 linha, 12 colunas)
    matriz_valores_mensal = np.zeros((1, 12))
    matriz_textos_hover_mensal = np.full((1, 12), '', dtype=object)

    ano_heatmap = df_anual_completo['Data'].dt.year.iloc[0] if not df_anual_completo.empty else datetime.now().year

    for mes_idx in range(12): # Loop de 0 a 11 (Janeiro a Dezembro)
        mes_atual_num = mes_idx + 1 # Mês de 1 a 12
        nome_mes_atual = nomes_meses_curto[mes_idx]

        dados_do_mes = vendas_mensais_agg[vendas_mensais_agg['MesNum'] == mes_atual_num]

        if not dados_do_mes.empty:
            row_mes = dados_do_mes.iloc[0]
            matriz_valores_mensal[0, mes_idx] = row_mes['Total_Vendas_Mes']

            hover_text_mes = (f"📅 {nome_mes_atual} {ano_heatmap}<br>"
                             f"💰 Total Mês: {format_brl(row_mes['Total_Vendas_Mes'])}<br>"
                             f"💳 Cartão: {format_brl(row_mes['Cartao_Mes'])}<br>"
                             f"💵 Dinheiro: {format_brl(row_mes['Dinheiro_Mes'])}<br>"
                             f"📱 Pix: {format_brl(row_mes['Pix_Mes'])}")
        else: # Mês sem vendas
            matriz_valores_mensal[0, mes_idx] = 0 # Ou np.nan se preferir cor de gap
            hover_text_mes = f"📅 {nome_mes_atual} {ano_heatmap}<br>❌ Sem vendas neste mês"
        
        matriz_textos_hover_mensal[0, mes_idx] = hover_text_mes

    # Escala de cores para o heatmap mensal (pode ser a mesma do anual ou diferente)
    escala_cores_mensal = [
        [0.0, '#161b22'],      # Cor para zero/baixo valor
        [0.001, '#ADD8E6'],    # Azul claro para valores baixos
        [0.25, '#87CEEB'],     # SkyBlue
        [0.5, '#4682B4'],      # SteelBlue
        [0.75, '#0000CD'],     # MediumBlue
        [1.0, '#000080']       # Navy para valores altos
    ]
    max_valor_mensal = np.max(matriz_valores_mensal) if np.any(matriz_valores_mensal > 0) else 1 # Evitar divisão por zero

    # Normalizar z para a escala de cores se os valores forem muito dispersos
    # Aqui, vamos usar os valores diretamente e ajustar a escala de cores se necessário
    # Se usar zmin/zmax na figura, a escala de cores será relativa a eles.

    fig_heatmap_mensal = go.Figure(data=go.Heatmap(
        z=matriz_valores_mensal,
        text=matriz_textos_hover_mensal,
        hovertemplate='%{text}<extra></extra>',
        colorscale=escala_cores_mensal,
        showscale=False, # Opcional: mostrar barra de cores
        xgap=5, # Espaçamento horizontal
        ygap=5  # Espaçamento vertical (relevante se houver mais de uma linha)
    ))

    fig_heatmap_mensal.update_layout(
        title=f'📊 Vendas Totais por Mês ({ano_heatmap})',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COR_TEXTO_PRINCIPAL, family="Arial"),

        xaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            tickmode='array',
            tickvals=list(range(12)), # Posições 0-11
            ticktext=nomes_meses_curto, # Labels Jan-Dez
            tickfont=dict(color=COR_TEXTO_PRINCIPAL, size=14),
            side='bottom' # Ticks na parte de baixo
        ),

        yaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            showticklabels=False # Esconde labels do eixo Y pois é apenas uma linha
        ),

        height=250, # Altura do gráfico mensal
        title_x=0.5,
        title_font=dict(size=18, color=COR_TEXTO_PRINCIPAL),
        margin=dict(l=20, r=20, t=60, b=50) # Ajustar margens
    )

    return fig_heatmap_mensal, vendas_mensais_agg


# --- Funções de Análise e Exibição ---

def display_resumo_financeiro(df):
    """Exibe os cards de resumo financeiro."""
    if df.empty:
        st.info("Não há dados suficientes para o resumo financeiro.")
        return

    total_faturamento = df["Total"].sum()
    media_diaria = df["Total"].mean() if not df.empty else 0
    maior_venda = df["Total"].max() if not df.empty else 0
    # Para menor venda, considerar apenas dias com venda > 0
    df_vendas_positivas = df[df["Total"] > 0]
    menor_venda = df_vendas_positivas["Total"].min() if not df_vendas_positivas.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Faturamento Total", format_brl(total_faturamento))
    with col2:
        st.metric("📊 Média por Dia Trabalhado", format_brl(media_diaria), help="Média considerando apenas dias com vendas registradas.")
    with col3:
        st.metric("🚀 Maior Venda Diária", format_brl(maior_venda))
    with col4:
        st.metric("📉 Menor Venda Diária (positiva)", format_brl(menor_venda))

def display_metodos_pagamento(df):
    """Exibe os cards de métodos de pagamento."""
    if df.empty or not all(col in df.columns for col in ["Cartão", "Dinheiro", "Pix"]):
        st.info("Não há dados suficientes para análise de métodos de pagamento.")
        return

    total_cartao = df["Cartão"].sum()
    total_dinheiro = df["Dinheiro"].sum()
    total_pix = df["Pix"].sum()
    total_geral = total_cartao + total_dinheiro + total_pix

    # Evitar divisão por zero se total_geral for 0
    perc_cartao = (total_cartao / total_geral * 100) if total_geral > 0 else 0
    perc_dinheiro = (total_dinheiro / total_geral * 100) if total_geral > 0 else 0
    perc_pix = (total_pix / total_geral * 100) if total_geral > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💳 Cartão", format_brl(total_cartao), f"{perc_cartao:.1f}% do total")
    with col2:
        st.metric("💵 Dinheiro", format_brl(total_dinheiro), f"{perc_dinheiro:.1f}% do total")
    with col3:
        st.metric("📱 PIX", format_brl(total_pix), f"{perc_pix:.1f}% do total")

def display_ranking_e_frequencia(df_filtered):
    """Exibe o ranking de dias e a análise de frequência."""
    if df_filtered.empty or 'DiaSemana' not in df_filtered.columns or 'Total' not in df_filtered.columns:
        st.info("📊 Dados insuficientes para calcular a análise por dia da semana e frequência.")
        return

    # Calcular médias por dia da semana
    # 'observed=False' é importante para incluir todos os dias da semana, mesmo sem dados
    medias_por_dia = df_filtered.groupby('DiaSemana', observed=False)['Total'].agg(['mean', 'count'])
    medias_por_dia = medias_por_dia.reindex(dias_semana_ordem).dropna(subset=['mean']) # Reordena e remove dias sem média (NaN)
    medias_por_dia = medias_por_dia.sort_values(by='mean', ascending=False)

    if not medias_por_dia.empty:
        st.subheader("📊 Ranking dos Dias da Semana (Média de Faturamento)")
        col_ranking1, col_ranking2 = st.columns(2)

        with col_ranking1:
            st.markdown("#### 🏆 **Melhores Dias**")
            if len(medias_por_dia) >= 1:
                primeiro = medias_por_dia.index[0]
                st.markdown(f"🥇 **1º lugar:** {primeiro} ({format_brl(medias_por_dia.loc[primeiro, 'mean'])})")
                st.caption(f"   {int(medias_por_dia.loc[primeiro, 'count'])} ocorrências")


            if len(medias_por_dia) >= 2:
                segundo = medias_por_dia.index[1]
                st.markdown(f"🥈 **2º lugar:** {segundo} ({format_brl(medias_por_dia.loc[segundo, 'mean'])})")
                st.caption(f"   {int(medias_por_dia.loc[segundo, 'count'])} ocorrências")
            
            if len(medias_por_dia) >= 3: # Adicionando terceiro lugar
                terceiro = medias_por_dia.index[2]
                st.markdown(f"🥉 **3º lugar:** {terceiro} ({format_brl(medias_por_dia.loc[terceiro, 'mean'])})")
                st.caption(f"   {int(medias_por_dia.loc[terceiro, 'count'])} ocorrências")

        with col_ranking2:
            st.markdown("#### 📉 **Piores Dias**")
            # Pega os últimos, mas inverte para mostrar do "menos pior" para o "pior"
            piores_dias = medias_por_dia.tail(3).sort_values(by='mean', ascending=True)
            if len(piores_dias) >= 1:
                ultimo = piores_dias.index[0]
                st.markdown(f"🔻 **Último lugar:** {ultimo} ({format_brl(piores_dias.loc[ultimo, 'mean'])})")
                st.caption(f"   {int(piores_dias.loc[ultimo, 'count'])} ocorrências")

            if len(piores_dias) >= 2:
                penultimo = piores_dias.index[1]
                st.markdown(f"📊 **Penúltimo:** {penultimo} ({format_brl(piores_dias.loc[penultimo, 'mean'])})")
                st.caption(f"   {int(piores_dias.loc[penultimo, 'count'])} ocorrências")
            
            if len(piores_dias) >= 3:
                antepenultimo = piores_dias.index[2]
                st.markdown(f"📊 **Antepenúltimo:** {antepenultimo} ({format_brl(piores_dias.loc[antepenultimo, 'mean'])})")
                st.caption(f"   {int(piores_dias.loc[antepenultimo, 'count'])} ocorrências")


        st.markdown("---")

        # Análise de frequência de trabalho
        st.subheader("📅 Análise de Frequência de Trabalho")

        if not df_filtered.empty and 'Data' in df_filtered.columns:
            data_inicio_periodo = df_filtered['Data'].min()
            data_fim_periodo = df_filtered['Data'].max()

            # Calcular total de dias no período filtrado
            total_dias_no_periodo = (data_fim_periodo - data_inicio_periodo).days + 1

            # Calcular domingos no período (considerados folga padrão)
            domingos_no_periodo = 0
            data_iter = data_inicio_periodo
            while data_iter <= data_fim_periodo:
                if data_iter.weekday() == 6:  # Domingo é 6
                    domingos_no_periodo += 1
                data_iter += timedelta(days=1)

            # Dias úteis esperados (total de dias no período menos domingos)
            dias_uteis_esperados_periodo = total_dias_no_periodo - domingos_no_periodo

            # Dias efetivamente trabalhados (contagem única de datas com vendas)
            dias_realmente_trabalhados = df_filtered['Data'].nunique()

            # Dias de falta (dias úteis esperados menos dias trabalhados)
            dias_de_falta = dias_uteis_esperados_periodo - dias_realmente_trabalhados
            dias_de_falta = max(0, dias_de_falta) # Garante que não seja negativo

            # Exibir métricas de frequência
            col_freq1, col_freq2, col_freq3, col_freq4 = st.columns(4)

            with col_freq1:
                st.metric(
                    "📅 Período Analisado",
                    f"{total_dias_no_periodo} dias",
                    help=f"De {data_inicio_periodo.strftime('%d/%m/%Y')} até {data_fim_periodo.strftime('%d/%m/%Y')}"
                )
            with col_freq2:
                st.metric(
                    "🏢 Dias Trabalhados",
                    f"{dias_realmente_trabalhados} dias",
                    help="Dias com registro de vendas no período."
                )
            with col_freq3:
                st.metric(
                    "🏖️ Domingos (Folga Padrão)",
                    f"{domingos_no_periodo} dias",
                    help="Número de domingos dentro do período analisado."
                )
            with col_freq4:
                delta_falta = f"-{dias_de_falta}" if dias_de_falta > 0 else None
                st.metric(
                    "❌ Dias de Falta (Seg-Sáb)",
                    f"{dias_de_falta} dias",
                    help="Dias de segunda a sábado sem registro de vendas.",
                    delta=delta_falta,
                    delta_color="inverse" if dias_de_falta > 0 else "off"
                )

            # Calcular taxa de frequência
            if dias_uteis_esperados_periodo > 0:
                taxa_frequencia_percentual = (dias_realmente_trabalhados / dias_uteis_esperados_periodo) * 100
                taxa_frequencia_percentual = min(100, taxa_frequencia_percentual) # Cap em 100%

                if taxa_frequencia_percentual >= 95:
                    st.success(f"🎯 **Excelente frequência:** {taxa_frequencia_percentual:.1f}% dos dias úteis (Seg-Sáb) trabalhados!")
                elif taxa_frequencia_percentual >= 80:
                    st.info(f"👍 **Boa frequência:** {taxa_frequencia_percentual:.1f}% dos dias úteis (Seg-Sáb) trabalhados.")
                else:
                    st.warning(f"⚠️ **Atenção à frequência:** {taxa_frequencia_percentual:.1f}% dos dias úteis (Seg-Sáb) trabalhados. Considere analisar os dias de falta.")
            else:
                st.info("Não há dias úteis esperados no período para calcular a taxa de frequência.")
        else:
            st.info("📊 Dados insuficientes para calcular a análise de frequência (período muito curto ou sem dados).")
    else:
        st.info("📊 Dados insuficientes para calcular o ranking de dias da semana.")

def display_insights(df):
    """Exibe insights automáticos com estilo melhorado."""
    if df.empty or len(df) < 2: # Precisa de pelo menos 2 registros para algumas comparações
        st.info("Dados insuficientes para gerar insights automáticos.")
        return

    total_vendas_insight = df["Total"].sum()
    dias_trabalhados_insight = df["Data"].nunique()
    # media_diaria_insight = total_vendas_insight / dias_trabalhados_insight if dias_trabalhados_insight > 0 else 0

    # Insight 1: Melhor dia da semana
    media_por_dia_insight = df.groupby("DiaSemana", observed=False)["Total"].mean().reset_index().dropna()
    melhor_dia_semana_insight = media_por_dia_insight.loc[media_por_dia_insight["Total"].idxmax()] if not media_por_dia_insight.empty else None

    # Insight 2: Método de pagamento predominante
    metodos_total_insight = {
        "Cartão": df["Cartão"].sum(),
        "Dinheiro": df["Dinheiro"].sum(),
        "PIX": df["Pix"].sum() # Usar 'Pix' como no DataFrame
    }
    metodos_total_insight = {k: v for k, v in metodos_total_insight.items() if v > 0} # Remove métodos com zero
    if metodos_total_insight:
        melhor_metodo_insight = max(metodos_total_insight, key=metodos_total_insight.get)
        valor_melhor_metodo_insight = metodos_total_insight[melhor_metodo_insight]
        percentual_melhor_insight = (valor_melhor_metodo_insight / total_vendas_insight * 100) if total_vendas_insight > 0 else 0
        sugestao_taxa_insight = """
        <p style="margin-top: 0.5rem; font-size: 0.9rem; color: #b0bec5;">
        <i>Sugestão: Se Cartão for predominante, avalie as taxas e negocie com adquirentes. Para Dinheiro, garanta troco. Para PIX, promova a facilidade.</i>
        </p>"""
    else:
        melhor_metodo_insight = None
        percentual_melhor_insight = 0
        sugestao_taxa_insight = ""

    # Insight 3: Comparação com período anterior (ex: última semana vs penúltima)
    df_sorted_insight = df.sort_values("Data")
    variacao_semanal_insight = None # Inicializa
    if len(df_sorted_insight) >= 14: # Precisa de pelo menos 2 semanas de dados
        # Considera os últimos 7 dias com dados vs os 7 dias anteriores com dados
        datas_unicas_ordenadas = sorted(df_sorted_insight['Data'].unique())
        if len(datas_unicas_ordenadas) >= 14 : # Verifica se temos pelo menos 14 dias distintos de operação
            ultimas_datas = datas_unicas_ordenadas[-7:]
            penultimas_datas = datas_unicas_ordenadas[-14:-7]

            media_ultima_semana_insight = df_sorted_insight[df_sorted_insight['Data'].isin(ultimas_datas)]["Total"].mean()
            media_penultima_semana_insight = df_sorted_insight[df_sorted_insight['Data'].isin(penultimas_datas)]["Total"].mean()
            
            if media_penultima_semana_insight > 0 : # Evita divisão por zero
                variacao_semanal_insight = ((media_ultima_semana_insight - media_penultima_semana_insight) / media_penultima_semana_insight * 100)
                tendencia_texto_insight = "crescimento" if variacao_semanal_insight > 5 else "queda" if variacao_semanal_insight < -5 else "estabilidade"
                tendencia_cor_insight = "#63d2b4" if variacao_semanal_insight > 5 else "#ec7063" if variacao_semanal_insight < -5 else "#f5b041"
            else: # Não há base para comparação
                tendencia_texto_insight = "base zero na penúltima semana"
                tendencia_cor_insight = COR_TEXTO_SECUNDARIO
        else: # Não há 14 dias distintos de operação
            tendencia_texto_insight = "insuficientes (menos de 14 dias operados)"
            tendencia_cor_insight = COR_TEXTO_SECUNDARIO
    else: # Menos de 14 registros totais
        tendencia_texto_insight = "insuficientes"
        tendencia_cor_insight = COR_TEXTO_SECUNDARIO


    # Exibição dos Insights
    st.subheader("🧠 Insights Automáticos Rápidos")
    col_insight1, col_insight2, col_insight3 = st.columns(3)

    with col_insight1:
        if melhor_dia_semana_insight is not None:
            st.markdown(f"""
            <div class="insight-container" style="border-left-color: {CORES_MODO_ESCURO[0]};">
                <h4 style="color: {CORES_MODO_ESCURO[0]};">🏆 Dia Mais Forte</h4>
                <p>A <strong>{melhor_dia_semana_insight["DiaSemana"]}</strong> apresenta a maior média de faturamento: <strong>{format_brl(melhor_dia_semana_insight["Total"])}</strong>.</p>
                <p style="margin-top: 0.5rem; font-size: 0.9rem; color: #b0bec5;">
                <i>Sugestão: Reforce o marketing ou promoções para este dia.</i>
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
             st.markdown(f"<div class=\"insight-container\" style=\"border-left-color: {COR_TEXTO_SECUNDARIO};\"><h4 style=\"color: {COR_TEXTO_SECUNDARIO};\">🏆 Dia Mais Forte</h4><p><i>Sem dados suficientes para determinar.</i></p></div>", unsafe_allow_html=True)

    with col_insight2:
        if melhor_metodo_insight is not None:
            st.markdown(f"""
            <div class="insight-container" style="border-left-color: {CORES_MODO_ESCURO[1]};">
                <h4 style="color: {CORES_MODO_ESCURO[1]};">💳 Pagamento Preferido</h4>
                <p>O método <strong>{melhor_metodo_insight}</strong> é o mais utilizado, representando <strong>{percentual_melhor_insight:.1f}%</strong> ({format_brl(valor_melhor_metodo_insight)}) do total faturado.</p>
                {sugestao_taxa_insight}
            </div>
            """, unsafe_allow_html=True)
        else:
             st.markdown(f"<div class=\"insight-container\" style=\"border-left-color: {COR_TEXTO_SECUNDARIO};\"><h4 style=\"color: {COR_TEXTO_SECUNDARIO};\">💳 Pagamento Preferido</h4><p><i>Sem dados suficientes para analisar.</i></p></div>", unsafe_allow_html=True)

    with col_insight3:
        if variacao_semanal_insight is not None:
            st.markdown(f"""
            <div class="insight-container" style="border-left-color: {tendencia_cor_insight};">
                <h4 style="color: {tendencia_cor_insight};">📈 Tendência Semanal (Média Diária)</h4>
                <p>Comparando as médias diárias das duas últimas semanas operadas, houve <strong>{tendencia_texto_insight}</strong> de <strong>{abs(variacao_semanal_insight):.1f}%</strong>.</p>
                 <p style="margin-top: 0.5rem; font-size: 0.9rem; color: #b0bec5;">
                <i>Sugestão: Analise os fatores que influenciaram essa variação (promoções, eventos, etc.).</i>
                </p>
            </div>
            """, unsafe_allow_html=True)
        else: # Caso variacao_semanal_insight seja None, mas tendencia_texto_insight tenha uma razão
            st.markdown(f"""
            <div class="insight-container" style="border-left-color: {tendencia_cor_insight};">
                <h4 style="color: {tendencia_cor_insight};">📈 Tendência Semanal</h4>
                <p>Dados <strong>{tendencia_texto_insight}</strong> para calcular a variação entre as últimas duas semanas.</p>
            </div>
            """, unsafe_allow_html=True)

# --- Funções da Análise Contábil ---

def calculate_financial_results(df, salario_base, custo_contadora, cpv_percent):
    """Calcula os resultados financeiros para a DRE."""
    resultados = {} # Dicionário para armazenar os resultados

    # (+) Receita Operacional Bruta (ROB)
    resultados['receita_bruta'] = df['Total'].sum()

    # (-) Deduções da Receita Bruta
    # Considera Simples Nacional (ex: 6% sobre receita tributável - Dinheiro e Pix)
    # Cartão já tem taxas descontadas na fonte ou pagas à operadora (não entra aqui como imposto direto sobre venda)
    resultados['receita_tributavel_direto'] = df['Dinheiro'].sum() + df['Pix'].sum()
    # receitas_cartao = df['Cartão'].sum() # Pode ser usado para outras análises
    # Imposto do Simples Nacional (estimativa, a alíquota real varia)
    aliquota_simples = 0.06 
    resultados['impostos_sobre_vendas'] = resultados['receita_tributavel_direto'] * aliquota_simples

    # (=) Receita Operacional Líquida (ROL)
    resultados['receita_liquida'] = resultados['receita_bruta'] - resultados['impostos_sobre_vendas']

    # (-) Custo dos Produtos Vendidos (CPV) ou Custo das Mercadorias Vendidas (CMV)
    # Estimado como um percentual da Receita Bruta
    resultados['custo_produtos_vendidos'] = resultados['receita_bruta'] * (cpv_percent / 100.0)

    # (=) Lucro Bruto (Resultado Bruto)
    resultados['lucro_bruto'] = resultados['receita_liquida'] - resultados['custo_produtos_vendidos']

    # (-) Despesas Operacionais
    #   (-) Despesas com Pessoal (Salário + Encargos)
    encargos_sociais_percentual = 0.55 # Estimativa de encargos sobre o salário base
    resultados['despesas_com_pessoal'] = salario_base * (1 + encargos_sociais_percentual)
    #   (-) Despesas Administrativas (Ex: Contabilidade)
    resultados['despesas_contabeis'] = custo_contadora
    #   (-) Outras Despesas (Aluguel, Luz, Água, Marketing, Taxas de Cartão, etc. - não incluídas aqui para simplificar)
    # Para uma DRE completa, essas outras despesas seriam subtraídas aqui.
    # Atualmente, as taxas de cartão estão implícitas na receita de cartão (receita já líquida da taxa da maquininha)
    # ou deveriam ser adicionadas como despesa financeira/operacional.
    
    # Somatório das Despesas Operacionais listadas
    resultados['total_despesas_operacionais'] = resultados['despesas_com_pessoal'] + resultados['despesas_contabeis']

    # (=) Lucro Operacional (Resultado Operacional Antes do Resultado Financeiro) - também conhecido como EBIT ou LAJIR
    resultados['lucro_operacional'] = resultados['lucro_bruto'] - resultados['total_despesas_operacionais']

    # (+/-) Resultado Financeiro (Receitas Financeiras - Despesas Financeiras)
    # Ex: Rendimentos de aplicações, Juros pagos. Aqui, simplificado para zero.
    # Taxas de cartão poderiam entrar como despesa financeira se a receita de cartão fosse bruta.
    resultados['resultado_financeiro'] = 0 

    # (=) Lucro Antes do Imposto de Renda e Contribuição Social (LAIR)
    resultados['lucro_antes_ir'] = resultados['lucro_operacional'] + resultados['resultado_financeiro']

    # (-) Imposto de Renda (IRPJ) e Contribuição Social sobre o Lucro Líquido (CSLL)
    # Para Simples Nacional, esses impostos já estão (majoritariamente) inclusos na guia única do Simples.
    # Para Lucro Presumido/Real, seriam calculados aqui sobre o LAIR. Simplificando, zero.
    resultados['ir_csll'] = 0

    # (=) Lucro Líquido do Exercício (Resultado Líquido)
    resultados['lucro_liquido'] = resultados['lucro_antes_ir'] - resultados['ir_csll']

    # Cálculo de Margens (em relação à Receita Líquida)
    resultados['margem_bruta'] = (resultados['lucro_bruto'] / resultados['receita_liquida'] * 100) if resultados['receita_liquida'] > 0 else 0
    resultados['margem_operacional'] = (resultados['lucro_operacional'] / resultados['receita_liquida'] * 100) if resultados['receita_liquida'] > 0 else 0
    resultados['margem_liquida'] = (resultados['lucro_liquido'] / resultados['receita_liquida'] * 100) if resultados['receita_liquida'] > 0 else 0
    
    return resultados

def create_dre_textual(resultados, df_completo_dre, anos_selecionados_dre):
    """Cria a DRE em formato textual com base nos resultados calculados."""
    st.subheader("🧾 Demonstração do Resultado do Exercício (DRE)")

    # Determinar período com base nos dados filtrados e anos selecionados
    periodo_str_dre = "Período não definido"
    if not df_completo_dre.empty and anos_selecionados_dre:
        anos_int_dre = [int(a) for a in anos_selecionados_dre] # Garante que anos são int
        df_periodo_dre = df_completo_dre[df_completo_dre['Ano'].isin(anos_int_dre)]
        if not df_periodo_dre.empty:
            min_date_dre = df_periodo_dre['Data'].min()
            max_date_dre = df_periodo_dre['Data'].max()
            periodo_str_dre = f"Período: {min_date_dre.strftime('%d/%m/%Y')} a {max_date_dre.strftime('%d/%m/%Y')}"
        else:
            periodo_str_dre = f"Período: Ano(s) {', '.join(map(str, anos_selecionados_dre))} (sem dados no filtro específico)"
    elif anos_selecionados_dre:
         periodo_str_dre = f"Período: Ano(s) {', '.join(map(str, anos_selecionados_dre))} (sem dados carregados)"


    st.caption(periodo_str_dre)

    # Estrutura HTML da DRE para melhor formatação
    # Usar parênteses para valores negativos (convenção contábil)
    html_dre = f"""
    <div class="dre-textual-container">
        <table>
            <thead>
                <tr>
                    <th>Descrição</th>
                    <th style="text-align: right;">Valor (R$)</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>(+) Receita Operacional Bruta</td><td style="text-align: right;">{format_brl(resultados['receita_bruta'])}</td></tr>
                <tr><td>(-) Deduções da Receita Bruta (Simples Nacional)</td><td style="text-align: right;">({format_brl(abs(resultados['impostos_sobre_vendas']))})</td></tr>
                <tr><td><strong>(=) Receita Operacional Líquida</strong></td><td style="text-align: right;"><strong>{format_brl(resultados['receita_liquida'])}</strong></td></tr>
                <tr><td>(-) Custo dos Produtos Vendidos (CPV)</td><td style="text-align: right;">({format_brl(abs(resultados['custo_produtos_vendidos']))})</td></tr>
                <tr><td><strong>(=) Lucro Bruto</strong></td><td style="text-align: right;"><strong>{format_brl(resultados['lucro_bruto'])}</strong></td></tr>
                <tr><td>(-) Despesas Operacionais</td><td></td></tr>
                <tr><td>&nbsp;&nbsp;&nbsp;&nbsp;(-) Despesas com Pessoal</td><td style="text-align: right;">({format_brl(abs(resultados['despesas_com_pessoal']))})</td></tr>
                <tr><td>&nbsp;&nbsp;&nbsp;&nbsp;(-) Despesas Administrativas (Contabilidade)</td><td style="text-align: right;">({format_brl(abs(resultados['despesas_contabeis']))})</td></tr>
                <tr><td><strong>(=) Lucro Operacional (EBIT/LAJIR)</strong></td><td style="text-align: right;"><strong>{format_brl(resultados['lucro_operacional'])}</strong></td></tr>
                <tr><td>(+/-) Resultado Financeiro</td><td style="text-align: right;">{format_brl(resultados['resultado_financeiro'])}</td></tr>
                <tr><td><strong>(=) Lucro Antes do Imposto de Renda (LAIR)</strong></td><td style="text-align: right;"><strong>{format_brl(resultados['lucro_antes_ir'])}</strong></td></tr>
                <tr><td>(-) Imposto de Renda e CSLL (já no Simples)</td><td style="text-align: right;">({format_brl(abs(resultados['ir_csll']))})</td></tr>
                <tr><td><strong>(=) Lucro Líquido do Exercício</strong></td><td style="text-align: right;"><strong>{format_brl(resultados['lucro_liquido'])}</strong></td></tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(html_dre, unsafe_allow_html=True)

def create_financial_dashboard_altair(resultados):
    """Cria um dashboard visual simples com os principais resultados financeiros."""
    # Preparar dados para o gráfico
    # Usar valores absolutos para custos e despesas para representação em barras
    # O sinal já está implícito na natureza do componente (ex: Custo é sempre uma dedução)
    data_chart = pd.DataFrame({
        'Componente': [
            'Receita Líquida',
            'Custo Produtos', # CPV
            'Despesas Pessoal',
            'Despesas Contábeis',
            'Lucro Líquido'
        ],
        'Valor': [
            resultados['receita_liquida'],
            abs(resultados['custo_produtos_vendidos']), # CPV é um custo
            abs(resultados['despesas_com_pessoal']),  # Despesa
            abs(resultados['despesas_contabeis']),   # Despesa
            resultados['lucro_liquido'] # Pode ser positivo ou negativo
        ],
        'Tipo': [ # Para colorir as barras
            'Receita',
            'Custo',
            'Despesa',
            'Despesa',
            'Resultado Final' # Lucro ou Prejuízo
        ]
    })
    
    # Filtrar componentes com valor zero para não poluir o gráfico, exceto Lucro Líquido
    data_chart_filtered = data_chart[ (data_chart['Valor'] != 0) | (data_chart['Componente'] == 'Lucro Líquido') ]


    if data_chart_filtered.empty:
        return None

    color_scale = alt.Scale(
        domain=['Receita', 'Custo', 'Despesa', 'Resultado Final'],
        range=['#1f77b4', '#ff7f0e', '#d62728', '#2ca02c' if resultados['lucro_liquido'] >= 0 else '#8c564b'] # Verde para lucro, Marrom para prejuízo
    )

    bars = alt.Chart(data_chart_filtered).mark_bar(cornerRadius=5).encode(
        x=alt.X('Componente:N', sort=None, title=None, axis=alt.Axis(labels=True, labelAngle=-45, labelColor=COR_TEXTO_SECUNDARIO)), # Mostrar labels dos componentes
        y=alt.Y('Valor:Q', title='Valor (R$)', axis=alt.Axis(labelColor=COR_TEXTO_SECUNDARIO, titleColor=COR_TEXTO_PRINCIPAL)),
        color=alt.Color('Tipo:N', scale=color_scale, legend=alt.Legend(title="Tipo de Componente", labelColor=COR_TEXTO_SECUNDARIO, titleColor=COR_TEXTO_PRINCIPAL)),
        tooltip=[
            alt.Tooltip('Componente:N', title='Componente'),
            alt.Tooltip('Valor:Q', title='Valor (R$)', format=',.2f')
        ]
    )

    # Adicionar texto com os valores sobre as barras
    text_chart = bars.mark_text(
        align='center',
        baseline='bottom',
        dy=-7, # Ajuste para posicionar o texto acima da barra
        color=COR_TEXTO_PRINCIPAL
    ).encode(
        text=alt.Text('Valor:Q', format=',.0f') # Formato resumido para o texto
    )

    chart_final = (bars + text_chart).properties(
        title=alt.TitleParams(
            text='Visão Geral: Receita, Custos, Despesas e Lucro',
            color=COR_TEXTO_PRINCIPAL,
            fontSize=16,
            anchor='middle'
            ),
        height=400,
        background="transparent" # Fundo transparente
    ).configure_view(
        strokeOpacity=0 # Remove borda da área de plotagem
    )

    return chart_final

# --- Interface Principal da Aplicação ---
def main():
    # Inicializar estado da sessão para controle da tabela
    if "show_table" not in st.session_state:
        st.session_state.show_table = False
    if "last_registered_data" not in st.session_state:
        st.session_state.last_registered_data = None # Armazenar dados para a tabela

    # Cabeçalho com logo e título
    st.markdown(f"""
    <div class="header-container">
        <div class="logo-container">
            <img src="{LOGO_URL}" class="logo-image" alt="Logo Clips Burger">
            <div>
                <h1>SISTEMA FINANCEIRO - CLIP'S BURGER</h1>
                <p>Gestão inteligente de vendas - {datetime.now().year}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Carregar e processar dados
    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    # Sidebar para filtros
    with st.sidebar:
        st.header("🔍 Filtros de Análise")
        st.markdown("---")

        # Filtro de Ano(s)
        anos_disponiveis_df = sorted(df_processed["Ano"].dropna().unique().astype(int), reverse=True) if not df_processed.empty and "Ano" in df_processed.columns else []
        
        # Default para o ano atual se houver dados, senão o último ano com dados, ou vazio
        default_ano_selecionado = [datetime.now().year] if datetime.now().year in anos_disponiveis_df else ([anos_disponiveis_df[0]] if anos_disponiveis_df else [])
        
        selected_anos_filtro = st.multiselect("Ano(s):", options=anos_disponiveis_df, default=default_ano_selecionado)

        # Filtro de Mês(es) - dinâmico baseado nos anos selecionados
        if selected_anos_filtro:
            meses_ano_filtrado = sorted(df_processed[df_processed["Ano"].isin(selected_anos_filtro)]["Mês"].dropna().unique().astype(int))
            mapa_meses_nomes_filtrados = {m: meses_ordem[m-1] for m in meses_ano_filtrado} # Nomes para exibição
            
            # Default para o mês atual se houver dados nos anos selecionados, senão todos os meses disponíveis nesses anos
            default_mes_selecionado = [datetime.now().month] if datetime.now().month in meses_ano_filtrado else meses_ano_filtrado
            
            selected_meses_num_filtro = st.multiselect("Mês(es):",
                                              options=meses_ano_filtrado,
                                              format_func=lambda m: mapa_meses_nomes_filtrados.get(m, m), # Mostra nome do mês
                                              default=default_mes_selecionado)
        else: # Se nenhum ano selecionado, desabilitar filtro de mês
            selected_meses_num_filtro = []
            st.multiselect("Mês(es):", options=[], disabled=True, help="Selecione um ano primeiro.")

    # Aplicar filtros ao DataFrame processado
    df_filtered_main = df_processed.copy()
    if selected_anos_filtro:
        df_filtered_main = df_filtered_main[df_filtered_main["Ano"].isin(selected_anos_filtro)]
    if selected_meses_num_filtro: # Só filtra por mês se houver meses selecionados
        df_filtered_main = df_filtered_main[df_filtered_main["Mês"].isin(selected_meses_num_filtro)]

    with st.sidebar:
        st.markdown("---")
        st.subheader("Resumo do Período Filtrado")
        if not df_filtered_main.empty:
            st.metric("Total de Registros de Venda", len(df_filtered_main))
            st.metric("Faturamento Bruto no Período", format_brl(df_filtered_main["Total"].sum()))
        else:
            st.info("Nenhum registro encontrado com os filtros selecionados.")
        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)
        st.caption(f"Última atualização dos dados da planilha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Abas da aplicação
    tab_registro, tab_dashboard_geral, tab_analise_contabil = st.tabs([
        "📝 Registrar Nova Venda",
        "📊 Dashboard de Vendas",
        "💰 Análise Contábil (DRE)"
    ])

    # Conteúdo da Aba de Registro de Venda
    with tab_registro:
        st.header("📝 Registrar Nova Venda Diária")
        st.markdown("---")

        with st.form(key="registro_venda_form", clear_on_submit=True): # Limpa o formulário após submissão
            data_venda_input = st.date_input("📅 Data da Venda", value=dt.date.today(), format="DD/MM/YYYY") # Default para hoje
            
            col_form_cartao, col_form_dinheiro, col_form_pix = st.columns(3)
            with col_form_cartao:
                valor_cartao_input = st.number_input("💳 Cartão (R$)", min_value=0.0, value=None, format="%.2f", placeholder="Ex: 150.75")
            with col_form_dinheiro:
                valor_dinheiro_input = st.number_input("💵 Dinheiro (R$)", min_value=0.0, value=None, format="%.2f", placeholder="Ex: 80.00")
            with col_form_pix:
                valor_pix_input = st.number_input("📱 PIX (R$)", min_value=0.0, value=None, format="%.2f", placeholder="Ex: 120.50")

            submit_button_registro = st.form_submit_button("✅ Registrar Venda na Planilha", use_container_width=True, type="primary")

            if submit_button_registro:
                # Coleta valores, tratando None como 0.0
                cartao_submetido = valor_cartao_input if valor_cartao_input is not None else 0.0
                dinheiro_submetido = valor_dinheiro_input if valor_dinheiro_input is not None else 0.0
                pix_submetido = valor_pix_input if valor_pix_input is not None else 0.0
                total_venda_submetida = cartao_submetido + dinheiro_submetido + pix_submetido

                if total_venda_submetida > 0:
                    worksheet_gspread = get_worksheet() # Obter o objeto worksheet
                    if worksheet_gspread:
                        sucesso_registro = add_data_to_sheet(data_venda_input, cartao_submetido, dinheiro_submetido, pix_submetido, worksheet_gspread)
                        if sucesso_registro:
                            st.success(f"✅ Venda de {format_brl(total_venda_submetida)} registrada para {data_venda_input.strftime('%d/%m/%Y')}!")
                            st.session_state.show_table = True # Ativa exibição da tabela
                            # Força recarregamento dos dados para a tabela mostrar a última info
                            df_raw_apos_registro = read_sales_data() 
                            df_processed_apos_registro = process_data(df_raw_apos_registro)
                            
                            # Aplica filtros atuais à tabela de visualização
                            df_filtrado_apos_registro = df_processed_apos_registro.copy()
                            if selected_anos_filtro:
                                df_filtrado_apos_registro = df_filtrado_apos_registro[df_filtrado_apos_registro["Ano"].isin(selected_anos_filtro)]
                            if selected_meses_num_filtro:
                                df_filtrado_apos_registro = df_filtrado_apos_registro[df_filtrado_apos_registro["Mês"].isin(selected_meses_num_filtro)]
                            
                            st.session_state.last_registered_data = df_filtrado_apos_registro # Armazena para exibir
                            st.rerun() # Recarrega o script para atualizar visualizações
                        else:
                            st.error("❌ Falha ao registrar a venda na planilha. Verifique os logs ou tente novamente.")
                    else:
                        st.error("❌ Falha ao conectar à planilha Google Sheets. Venda não registrada.")
                else:
                    st.warning("⚠️ O valor total da venda deve ser maior que zero para registrar.")

        # Exibição da tabela de vendas (após registro ou se show_table for True)
        if st.session_state.show_table and st.session_state.last_registered_data is not None and not st.session_state.last_registered_data.empty:
            st.markdown("---")
            st.subheader("🧾 Tabela de Vendas (Visão Conforme Filtros Atuais)")
            df_para_exibir = st.session_state.last_registered_data
            
            # Colunas desejadas para a tabela e suas configurações
            colunas_tabela = ["DataFormatada", "DiaSemana", "Cartão", "Dinheiro", "Pix", "Total"]
            colunas_existentes_tabela = [col for col in colunas_tabela if col in df_para_exibir.columns]
            
            if colunas_existentes_tabela:
                st.dataframe(df_para_exibir[colunas_existentes_tabela].sort_values(by="DataFormatada", ascending=False), # Ordena pela data mais recente
                               use_container_width=True,
                               height=400, # Altura fixa para a tabela com scroll
                               hide_index=True, # Esconde o índice do DataFrame
                               column_config={ # Configurações específicas das colunas
                                    "DataFormatada": st.column_config.TextColumn("Data", help="Data da venda no formato DD/MM/AAAA"),
                                    "DiaSemana": st.column_config.TextColumn("Dia da Semana"),
                                    "Cartão": st.column_config.NumberColumn("Cartão (R$)", format="R$ %.2f"),
                                    "Dinheiro": st.column_config.NumberColumn("Dinheiro (R$)", format="R$ %.2f"),
                                    "Pix": st.column_config.NumberColumn("PIX (R$)", format="R$ %.2f"),
                                    "Total": st.column_config.NumberColumn("Total Venda (R$)", format="R$ %.2f", help="Soma de Cartão, Dinheiro e PIX")
                                })
            else:
                st.info("Colunas necessárias para a tabela não foram encontradas nos dados processados.")
        elif st.session_state.show_table:
            st.info("Nenhum dado para exibir na tabela com os filtros atuais.")


    # Conteúdo da Aba de Dashboard
    with tab_dashboard_geral:
        st.header("📊 Dashboard Geral de Vendas")
        st.markdown("---")

        if df_filtered_main.empty:
            st.warning("⚠️ Não há dados para exibir no dashboard com os filtros selecionados. Ajuste os filtros na barra lateral ou registre novas vendas.")
        else:
            st.subheader("📈 Resumo Financeiro do Período")
            display_resumo_financeiro(df_filtered_main)
            st.markdown("---")

            st.subheader("🗓️ Calendário de Atividade de Vendas")
            # Determinar o ano para exibir o heatmap (prioriza o primeiro ano selecionado, ou o ano atual se nos filtros)
            ano_para_heatmap = None
            if selected_anos_filtro:
                ano_para_heatmap = selected_anos_filtro[0] # Pega o primeiro ano da lista de filtros
            elif datetime.now().year in anos_disponiveis_df: # Se nenhum filtro de ano, mas ano atual tem dados
                 ano_para_heatmap = datetime.now().year
            
            if ano_para_heatmap:
                try:
                    # Passar o DataFrame já filtrado por ano/mês (df_filtered_main) para o heatmap se fizer sentido,
                    # ou o df_processed se o heatmap deve sempre mostrar o ano inteiro independente do filtro de mês.
                    # Para o calendário anual, faz mais sentido usar df_processed e filtrar apenas pelo ano dentro da função.
                    heatmap_anual_fig, df_dados_ano_heatmap = criar_calendario_anual_espacamento_correto(df_processed, ano_para_heatmap)
                    if heatmap_anual_fig:
                        st.plotly_chart(heatmap_anual_fig, use_container_width=True)

                        # Heatmap Mensal abaixo do Anual, usando os dados processados do ano do heatmap anual
                        if df_dados_ano_heatmap is not None and not df_dados_ano_heatmap.empty:
                            heatmap_mensal_fig, _ = criar_heatmap_vendas_mensais_espacamento_correto(df_dados_ano_heatmap)
                            if heatmap_mensal_fig:
                                st.plotly_chart(heatmap_mensal_fig, use_container_width=True)
                            # else: st.info(f"Não foi possível gerar o heatmap mensal para {ano_para_heatmap}.") # Opcional
                        # else: st.info(f"Dados anuais para heatmap mensal não disponíveis para {ano_para_heatmap}.") # Opcional
                    # else: st.info(f"Não foi possível gerar o heatmap anual para {ano_para_heatmap}.") # Opcional
                except Exception as e_heatmap:
                    st.error(f"Ocorreu um erro ao gerar o heatmap de calendário: {e_heatmap}")
            else:
                st.info("Selecione um ano no filtro ou registre vendas para visualizar o calendário de atividades.")
            st.markdown("---")

            st.subheader("💹 Evolução do Faturamento Acumulado no Período")
            grafico_acumulado = create_cumulative_evolution_chart(df_filtered_main)
            if grafico_acumulado:
                st.altair_chart(grafico_acumulado, use_container_width=True)
            # else: st.info("Não foi possível gerar o gráfico de evolução acumulada.") # Opcional

            st.markdown("---")
            st.subheader("💳 Métodos de Pagamento no Período")
            display_metodos_pagamento(df_filtered_main)
            st.markdown("---")

            st.subheader("📅 Análise Diária e Distribuição por Pagamento")
            col_graf_diario, col_graf_radial = st.columns([3, 2]) # Ajustar proporção se necessário
            with col_graf_diario:
                st.markdown("###### Vendas Diárias por Método (Empilhado)")
                grafico_vendas_diarias_emp = create_advanced_daily_sales_chart(df_filtered_main) # Função corrigida
                if grafico_vendas_diarias_emp:
                    st.altair_chart(grafico_vendas_diarias_emp, use_container_width=True)
                # else: st.info("Sem dados de vendas diárias para exibir em formato empilhado.") # Opcional
            with col_graf_radial:
                st.markdown("###### Distribuição Percentual por Pagamento")
                grafico_radial_pagamentos = create_radial_plot(df_filtered_main)
                if grafico_radial_pagamentos:
                    st.altair_chart(grafico_radial_pagamentos, use_container_width=True)
                # else: st.info("Sem dados para o gráfico de distribuição de pagamentos.") # Opcional
            
            st.markdown("---")
            st.subheader("📊 Média de Vendas por Dia da Semana")
            grafico_media_dia_semana = create_weekday_sales_chart(df_filtered_main)
            if grafico_media_dia_semana:
                st.altair_chart(grafico_media_dia_semana, use_container_width=True)
            # else: st.info("Sem dados para o gráfico de média por dia da semana.") # Opcional
            
            st.markdown("---")
            display_ranking_e_frequencia(df_filtered_main) # Ranking e Frequência
            st.markdown("---")
            display_insights(df_filtered_main) # Insights Automáticos
            st.markdown("---")

    # Conteúdo da Aba de Análise Contábil
    with tab_analise_contabil:
        st.header("💰 Análise Contábil e Financeira (DRE)")
        st.markdown("""
        Esta análise apresenta uma Demonstração do Resultado do Exercício (DRE) simplificada, 
        considerando o regime tributário do **Simples Nacional** (alíquota estimada de 6% sobre a receita tributável de Dinheiro e PIX).
        As premissas de custos e despesas são configuráveis abaixo.
        """)
        st.markdown("---")

        with st.container(border=True): # Container para os parâmetros
            st.subheader("⚙️ Parâmetros para Simulação da DRE")
            col_param_dre1, col_param_dre2, col_param_dre3 = st.columns(3)
            with col_param_dre1:
                salario_base_dre = st.number_input(
                    "💼 Salário Base Funcionário (Mensal R$)",
                    min_value=0.0, value=1550.0, format="%.2f",
                    help="Salário base mensal. Encargos de ~55% são adicionados automaticamente.",
                    key="salario_dre_input"
                )
            with col_param_dre2:
                custo_contadora_dre = st.number_input(
                    "📋 Honorários Contábeis (Mensal R$)",
                    min_value=0.0, value=316.0, format="%.2f",
                    help="Valor mensal dos serviços contábeis.",
                    key="contadora_dre_input"
                )
            with col_param_dre3:
                cpv_percentual_dre = st.number_input(
                    "📦 Custo dos Produtos Vendidos (%)",
                    min_value=0.0, max_value=100.0, value=30.0, format="%.1f",
                    help="Percentual da Receita Bruta destinado à compra de insumos/produtos.",
                    key="cpv_dre_input"
                )

        st.markdown("---")

        if df_filtered_main.empty or 'Total' not in df_filtered_main.columns:
            st.warning("📊 **Não há dados de vendas suficientes no período filtrado para a análise contábil.** Ajuste os filtros ou registre mais vendas.")
        else:
            # Calcula resultados financeiros com base nos parâmetros e dados filtrados
            resultados_dre = calculate_financial_results(
                df_filtered_main, salario_base_dre, custo_contadora_dre, cpv_percentual_dre
            )

            with st.container(border=True): # Container para a DRE textual
                create_dre_textual(resultados_dre, df_filtered_main, selected_anos_filtro)

            st.markdown("---")

            # Gráfico visual da DRE
            grafico_dashboard_dre = create_financial_dashboard_altair(resultados_dre)
            if grafico_dashboard_dre:
                st.altair_chart(grafico_dashboard_dre, use_container_width=True)
            # else: st.info("Não foi possível gerar o dashboard visual da DRE.") # Opcional

            st.markdown("---")

            with st.container(border=True): # Container para margens e indicadores
                st.subheader("📈 Análise de Margens e Indicadores Chave")
                col_margens1, col_margens2, col_margens3 = st.columns(3)

                with col_margens1:
                    st.metric(
                        "📊 Margem Bruta",
                        f"{resultados_dre['margem_bruta']:.2f}%",
                        help="Lucro Bruto / Receita Líquida. Indica a rentabilidade após o CPV."
                    )
                    st.metric(
                        "🏛️ Carga Tributária (Simples s/ Vendas)",
                        f"{(resultados_dre['impostos_sobre_vendas'] / resultados_dre['receita_bruta'] * 100) if resultados_dre['receita_bruta'] > 0 else 0:.2f}%",
                        help="Percentual do Simples Nacional sobre a Receita Bruta."
                    )
                with col_margens2:
                    st.metric(
                        "💼 Margem Operacional",
                        f"{resultados_dre['margem_operacional']:.2f}%",
                        help="Lucro Operacional / Receita Líquida. Eficiência operacional."
                    )
                    st.metric(
                        "👥 Peso Desp. Pessoal",
                        f"{(resultados_dre['despesas_com_pessoal'] / resultados_dre['receita_bruta'] * 100) if resultados_dre['receita_bruta'] > 0 else 0:.2f}%",
                        help="Percentual das Despesas com Pessoal sobre a Receita Bruta."
                    )
                with col_margens3:
                    st.metric(
                        "💰 Margem Líquida",
                        f"{resultados_dre['margem_liquida']:.2f}%",
                        help="Lucro Líquido / Receita Líquida. Rentabilidade final do negócio."
                    )
                    st.metric(
                        "📦 Peso do CPV",
                        f"{(resultados_dre['custo_produtos_vendidos'] / resultados_dre['receita_bruta'] * 100) if resultados_dre['receita_bruta'] > 0 else 0:.2f}%",
                        help="Percentual do Custo dos Produtos Vendidos sobre a Receita Bruta."
                    )
            st.markdown("---")

            with st.expander("📋 Ver Resumo Executivo da DRE", expanded=False):
                col_exec_dre1, col_exec_dre2 = st.columns(2)
                with col_exec_dre1:
                    st.markdown("**💰 Receitas:**")
                    st.write(f"• Receita Bruta Total: {format_brl(resultados_dre['receita_bruta'])}")
                    st.write(f"• Receita Líquida Total: {format_brl(resultados_dre['receita_liquida'])}")
                    st.markdown("**📊 Resultados:**")
                    st.write(f"• Lucro Bruto: {format_brl(resultados_dre['lucro_bruto'])}")
                    st.write(f"• Lucro Operacional (EBIT): {format_brl(resultados_dre['lucro_operacional'])}")
                    st.write(f"• Lucro Líquido Final: {format_brl(resultados_dre['lucro_liquido'])}")
                with col_exec_dre2:
                    st.markdown("**💸 Custos e Despesas Deduzidos:**")
                    st.write(f"• Impostos (Simples s/ Vendas): {format_brl(resultados_dre['impostos_sobre_vendas'])}")
                    st.write(f"• Custo dos Produtos (CPV): {format_brl(resultados_dre['custo_produtos_vendidos'])}")
                    st.write(f"• Despesas com Pessoal: {format_brl(resultados_dre['despesas_com_pessoal'])}")
                    st.write(f"• Serviços Contábeis: {format_brl(resultados_dre['despesas_contabeis'])}")
                    st.markdown("**🎯 Avaliação Rápida do Resultado:**")
                    if resultados_dre['lucro_liquido'] > 0:
                        st.success(f"✅ Resultado POSITIVO de {format_brl(resultados_dre['lucro_liquido'])} no período!")
                    elif resultados_dre['lucro_liquido'] == 0:
                        st.warning(f"⚠️ Resultado NULO (Break-even) no período.")
                    else:
                        st.error(f"❌ Resultado NEGATIVO de {format_brl(resultados_dre['lucro_liquido'])} no período. Atenção!")
            
            st.info("""
            💡 **Nota Importante:** Esta DRE é uma simulação simplificada para fins gerenciais. 
            Taxas de cartão não foram explicitamente deduzidas (considera-se que a receita de cartão já é líquida dessas taxas ou que elas seriam parte de "Outras Despesas").
            Para uma análise contábil formal e decisões fiscais, consulte sempre um contador qualificado.
            """)

if __name__ == "__main__":
    main()
