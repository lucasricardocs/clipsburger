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
from io import StringIO
import calendar

# Suprimir warnings específicos do pandas
warnings.filterwarnings("ignore", category=FutureWarning, message=".*observed=False.*")

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = "1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg"
WORKSHEET_NAME = "Vendas"
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/clipsburger/main/logo.png" # URL da logo no GitHub

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema Financeiro - Clips Burger", layout="wide", page_icon="🍔")

# Configuração de tema para gráficos mais bonitos
alt.data_transformers.enable("json")

# Paleta de cores otimizada para modo escuro (ajustada para melhor contraste)
CORES_MODO_ESCURO = ["#57a3f2", "#63d2b4", "#f5b041", "#ec7063", "#85c1e9", "#f7dc6f", "#af7ac5", "#aab7b8"]
COR_FUNDO_CONTAINER = "rgba(40, 45, 55, 0.7)" # Fundo ligeiramente mais claro para containers
COR_BORDA_INSIGHT = "#57a3f2" # Azul claro para borda de insights
COR_TEXTO_PRINCIPAL = "#ffffff"
COR_TEXTO_SECUNDARIO = "#b0bec5"
COR_SEPARADOR = "#455a64"

# Define a ordem correta dos dias da semana e meses
dias_semana_ordem = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# CSS para melhorar a aparência (Com logo maior e aura pulsante multicolorida)
def inject_css():
    st.markdown(f"""
    <style>
    /* --- Geral --- */
    .stApp {{
        background: linear-gradient(135deg, #1e2a4a 0%, #2a3a5f 50%, #2d2a5a 100%); /* Background azulado/arroxeado menos escuro */
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

    /* Ajuste para st.metric ser mais responsivo e interativo */
    div[data-testid="stMetric"] {{
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
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }}
    div[data-testid="stMetric"]:hover {{
         transform: scale(1.03);
         box-shadow: 0 4px 10px rgba(0,0,0,0.25);
    }}

    div[data-testid="stMetric"] label {{
        color: {COR_TEXTO_SECUNDARIO} !important;
        font-size: 0.95rem !important;
    }}
    div[data-testid="stMetric"] > div > div {{
        font-size: 1.8rem !important;
        font-weight: 600;
        color: {COR_TEXTO_PRINCIPAL} !important;
        white-space: normal; /* Permite quebra de linha se necessário */
        overflow-wrap: break-word; /* Quebra palavras longas */
    }}
    div[data-testid="stMetric"] .stMetricDelta {{ 
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
        min-height: 120px; /* Reduzido um pouco */
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 0 3px 7px rgba(0,0,0,0.2);
        transition: background-color 0.3s ease, transform 0.2s ease;
    }}
    .insight-container:hover {{
        background-color: rgba(50, 55, 65, 0.8);
        transform: translateY(-3px);
    }}
    .insight-container h4 {{
        color: {COR_BORDA_INSIGHT};
        margin: 0 0 0.8rem 0; /* Espaço menor abaixo do título */
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
        justify-content: center; /* Centraliza horizontalmente */
        align-items: center;
        margin-bottom: 25px;
        padding-bottom: 15px;
        border-bottom: 1px solid {COR_SEPARADOR};
    }}
    
    .logo-container {{
        display: flex;
        align-items: center;
        gap: 5px; /* Espaço reduzido entre logo e título */
        margin-bottom: 5px;
        padding-bottom: 5px;
    }}
    
    .logo-image {{
        width: 210px; /* Logo maior conforme solicitado */
        height: auto;
        /* Animação da aura com cores celestiais variadas */
        animation: celestialPulse 8s ease-in-out infinite;
    }}

    /* Keyframes para a aura pulsante celestial multicolorida */
    @keyframes celestialPulse {{
        0%, 100% {{
            filter: drop-shadow(0 0 15px rgba(100, 149, 237, 0.8)) drop-shadow(0 0 30px rgba(100, 149, 237, 0.6)); /* Azul celestial */
        }}
        20% {{
            filter: drop-shadow(0 0 15px rgba(147, 112, 219, 0.8)) drop-shadow(0 0 30px rgba(147, 112, 219, 0.6)); /* Roxo */
        }}
        40% {{
            filter: drop-shadow(0 0 15px rgba(255, 215, 0, 0.8)) drop-shadow(0 0 30px rgba(255, 215, 0, 0.6)); /* Amarelo dourado */
        }}
        60% {{
            filter: drop-shadow(0 0 15px rgba(255, 69, 0, 0.8)) drop-shadow(0 0 30px rgba(255, 69, 0, 0.6)); /* Vermelho */
        }}
        80% {{
            filter: drop-shadow(0 0 15px rgba(138, 43, 226, 0.8)) drop-shadow(0 0 30px rgba(138, 43, 226, 0.6)); /* Roxo azulado */
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
        padding: 0.8rem 1.5rem;
        font-weight: 600;
        border-radius: 8px 8px 0 0;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {COR_FUNDO_CONTAINER};
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
    .dre-table table {{
        width: 100%;
        border-collapse: collapse;
    }}
    .dre-table th, .dre-table td {{
        padding: 8px 12px;
        text-align: left;
        border-bottom: 1px solid {COR_SEPARADOR};
        vertical-align: middle; /* Alinha verticalmente */
    }}
    .dre-table td:nth-child(2) {{ 
        text-align: right;
        font-family: 'Courier New', Courier, monospace;
        white-space: pre;
        padding-right: 12px; /* Adiciona padding para alinhar com header */
    }}
    .dre-table th:nth-child(2) {{ 
        text-align: right;
        padding-right: 12px; /* Garante mesmo padding do td */
    }}

    /* --- Responsividade --- */
    @media (max-width: 992px) {{ 
        .logo-image {{ width: 180px; }} /* Ajustar logo em tablet */
        .logo-container h1 {{ font-size: 2rem; }}
        div[data-testid="stMetric"] {{ padding: 1rem; min-height: 100px; }}
        .insight-container {{ padding: 1.2rem; min-height: 110px; }}
        /* Força colunas a empilhar mais cedo se necessário */
        .st-emotion-cache-1l269bu > div {{ 
             flex-direction: column;
        }}
    }}

    @media (max-width: 768px) {{ 
        .logo-image {{ width: 150px; }} /* Ajustar logo em mobile */
        .logo-container {{ gap: 10px; flex-direction: column; text-align: center; }}
        .logo-container h1 {{ font-size: 1.6rem; padding-left: 0; }}
        .logo-container p {{ font-size: 0.9rem; padding-left: 0; }}
        div[data-testid="stMetric"] {{ min-height: 90px; padding: 0.8rem; }}
        div[data-testid="stMetric"] > div > div {{ font-size: 1.5rem !important; }}
        .stTabs [role="tab"] {{ padding: 0.6rem 1rem; }}
        .stDateInput, .stNumberInput, .stSelectbox, .stMultiselect {{ margin-bottom: 1rem; }}
        .insight-container {{ padding: 1rem; min-height: auto; }}
        .insight-container h4 {{ font-size: 1rem; }}
        .insight-container p {{ font-size: 0.9rem; }}
        .dre-table td, .dre-table th {{ padding: 6px 8px; font-size: 13px; }}
        .dre-table td:nth-child(2), .dre-table th:nth-child(2) {{ padding-right: 8px; }}
    }}

    @media (max-width: 480px) {{ 
        .logo-image {{ width: 120px; }} /* Ajustar logo em mobile pequeno */
        .logo-container h1 {{ font-size: 1.4rem; }}
        div[data-testid="stMetric"] > div > div {{ font-size: 1.3rem !important; }}
        div[data-testid="stMetric"] label {{ font-size: 0.85rem !important; }}
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
            st.error("Credenciais do Google ('google_credentials') não encontradas em st.secrets. Configure o arquivo .streamlit/secrets.toml")
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
            st.error(f"Planilha com ID '{SPREADSHEET_ID}' não encontrada.")
            return None
        except Exception as e:
            st.error(f"Erro ao acessar a planilha '{WORKSHEET_NAME}': {e}")
            return None
    return None

# --- Funções de Manipulação de Dados ---
@st.cache_data(ttl=600) # Aumentar TTL para reduzir recargas
def read_sales_data():
    """Lê todos os registros da planilha de vendas e retorna como DataFrame."""
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records()
            if not rows:
                # Retorna DataFrame vazio com colunas esperadas para evitar erros posteriores
                return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix"])

            df = pd.DataFrame(rows)

            # Garantir que colunas de pagamento existam e sejam numéricas
            for col in ["Cartão", "Dinheiro", "Pix"]:
                if col in df.columns:
                    # Tenta converter para numérico, força erros para NaN, preenche NaN com 0
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    df[col] = 0 # Cria a coluna se não existir

            # Garantir que a coluna "Data" existe
            if "Data" not in df.columns:
                 st.warning("Coluna 'Data' não encontrada na planilha. Criando coluna vazia.")
                 df["Data"] = pd.NaT # Cria coluna de data vazia
            else:
                # Tentar converter "Data" para datetime (múltiplos formatos)
                try:
                    # Tenta formato DD/MM/YYYY primeiro
                    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
                except ValueError:
                    # Tenta outros formatos comuns se o primeiro falhar
                    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

            # Remover linhas onde a data não pôde ser convertida
            df.dropna(subset=["Data"], inplace=True)

            # Calcular Total antes de retornar
            df["Total"] = df["Cartão"] + df["Dinheiro"] + df["Pix"]

            return df
        except Exception as e:
            st.error(f"Erro ao ler dados da planilha: {e}")
            return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix", "Total"])
    return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix", "Total"])

def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet_obj):
    """Adiciona uma nova linha de dados à planilha Google Sheets."""
    if worksheet_obj is None:
        st.error("Não foi possível acessar a planilha para adicionar dados.")
        return False
    try:
        cartao_val = float(cartao) if cartao else 0.0
        dinheiro_val = float(dinheiro) if dinheiro else 0.0
        pix_val = float(pix) if pix else 0.0

        # Formata a data como string DD/MM/YYYY para consistência na planilha
        formatted_date_str = date.strftime("%d/%m/%Y")

        new_row = [formatted_date_str, cartao_val, dinheiro_val, pix_val]
        worksheet_obj.append_row(new_row)
        # Limpar caches relevantes após adicionar dados
        st.cache_data.clear() # Limpa cache de dados (read_sales_data, process_data)
        # st.cache_resource.clear() # Descomentar se necessário limpar cache de recursos (conexão)
        return True # Indica sucesso
    except ValueError as ve:
        st.error(f"Erro ao converter valores para número: {ve}. Verifique os dados de entrada.")
        return False
    except Exception as e:
        st.error(f"Erro ao adicionar dados na planilha: {e}")
        return False

@st.cache_data
def process_data(df_input):
    """Processa e prepara os dados de vendas para análise."""
    if df_input.empty or "Data" not in df_input.columns:
        # Retorna um DataFrame vazio estruturado para evitar erros downstream
        cols = ["Data", "Cartão", "Dinheiro", "Pix", "Total", "Ano", "Mês", "MêsNome", "AnoMês", "DataFormatada", "DiaSemana", "DiaDoMes"]
        empty_df = pd.DataFrame(columns=cols)
        for col in ["Cartão", "Dinheiro", "Pix", "Total", "Ano", "Mês", "DiaDoMes"]:
             empty_df[col] = pd.Series(dtype="float")
        empty_df["Data"] = pd.Series(dtype="datetime64[ns]")
        for col in ["MêsNome", "AnoMês", "DataFormatada", "DiaSemana"]:
             empty_df[col] = pd.Series(dtype="object")
        return empty_df

    df = df_input.copy()

    # Garantir que "Data" é datetime (pode já ter sido convertido em read_sales_data)
    if not pd.api.types.is_datetime64_any_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df.dropna(subset=["Data"], inplace=True) # Remove linhas onde a conversão falhou

    # Garantir colunas numéricas e preencher NaNs
    for col in ["Cartão", "Dinheiro", "Pix"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    # Calcular Total se não existir (já calculado em read_sales_data, mas garante)
    if "Total" not in df.columns:
        df["Total"] = df["Cartão"] + df["Dinheiro"] + df["Pix"]

    # Derivar colunas de data
    df["Ano"] = df["Data"].dt.year
    df["Mês"] = df["Data"].dt.month
    df["MêsNome"] = df["Mês"].apply(lambda x: meses_ordem[x-1] if pd.notna(x) and 1 <= x <= 12 else None)
    df["AnoMês"] = df["Data"].dt.strftime("%Y-%m")
    df["DataFormatada"] = df["Data"].dt.strftime("%d/%m/%Y")
    day_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
    df["DiaSemana"] = df["Data"].dt.dayofweek.map(day_map)
    df["DiaDoMes"] = df["Data"].dt.day

    # Ordenar por data para garantir consistência temporal
    df = df.sort_values(by="Data").reset_index(drop=True)

    # Definir tipos categóricos para ordenação correta em gráficos
    if "DiaSemana" in df.columns:
        df["DiaSemana"] = pd.Categorical(df["DiaSemana"], categories=dias_semana_ordem, ordered=True)
    if "MêsNome" in df.columns:
        df["MêsNome"] = pd.Categorical(df["MêsNome"], categories=meses_ordem, ordered=True)

    return df

# --- Funções de Formatação ---
def format_brl(value):
    """Formata valor numérico como moeda brasileira (R$)."""
    try:
        return f"R$ {value:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")
    except (ValueError, TypeError):
        return "R$ -"

# --- Funções de Gráficos Interativos (AJUSTADAS E NOVAS) ---

# Gráfico Radial (Altura Fixa 500px)
def create_radial_plot(df):
    """Cria um gráfico radial de métodos de pagamento."""
    if df.empty or not any(col in df.columns for col in ["Cartão", "Dinheiro", "Pix"]):
        return alt.Chart(pd.DataFrame({'A': []})).mark_text(text='Dados insuficientes').properties(height=500)

    payment_data = pd.DataFrame({
        "Método": ["Cartão", "Dinheiro", "PIX"],
        "Valor": [df["Cartão"].sum(), df["Dinheiro"].sum(), df["Pix"].sum()]
    })
    payment_data = payment_data[payment_data["Valor"] > 0]

    if payment_data.empty:
        return alt.Chart(pd.DataFrame({'A': []})).mark_text(text='Sem dados de pagamento').properties(height=500)

    base = alt.Chart(payment_data).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        radius=alt.Radius("Valor:Q", scale=alt.Scale(type="sqrt", zero=True, rangeMin=20)),
        color=alt.Color("Método:N",
                        scale=alt.Scale(range=CORES_MODO_ESCURO[:len(payment_data)]),
                        legend=alt.Legend(title="Método", orient="bottom", titleColor=COR_TEXTO_PRINCIPAL, labelColor=COR_TEXTO_SECUNDARIO)),
        order=alt.Order("Valor:Q", sort="descending"), # Ordena fatias
        tooltip=[
            alt.Tooltip("Método:N", title="Método"),
            alt.Tooltip("Valor:Q", title="Valor", format=",.2f")
        ]
    )

    radial_plot = base.mark_arc(innerRadius=30, stroke=COR_FUNDO_CONTAINER, strokeWidth=3).properties(
        height=500, # Altura fixa
        # Largura será definida por use_container_width=True
    ).configure_view(
        stroke=None,
        strokeOpacity=0
    ).configure_axis(
        labelColor=COR_TEXTO_SECUNDARIO,
        titleColor=COR_TEXTO_PRINCIPAL,
        grid=False
    ).configure_legend(
        titleColor=COR_TEXTO_PRINCIPAL,
        labelColor=COR_TEXTO_SECUNDARIO
    )

    return radial_plot

# Gráfico de Vendas Diárias (Altura Fixa 500px)
def create_advanced_daily_sales_chart(df):
    """Cria gráfico de barras arredondadas de vendas diárias com linha de média móvel."""
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        return alt.Chart(pd.DataFrame({'A': []})).mark_text(text='Dados insuficientes').properties(height=500)

    df_chart = df.copy()
    df_chart.dropna(subset=["Data", "Total"], inplace=True)
    if df_chart.empty:
        return alt.Chart(pd.DataFrame({'A': []})).mark_text(text='Sem dados de vendas diárias').properties(height=500)

    # Agrupar por dia caso haja múltiplas entradas
    df_daily = df_chart.groupby(pd.Grouper(key="Data", freq="D"))["Total"].sum().reset_index()
    df_daily = df_daily[df_daily["Total"] > 0] # Mostrar apenas dias com vendas

    if df_daily.empty:
        return alt.Chart(pd.DataFrame({'A': []})).mark_text(text='Sem vendas registradas').properties(height=500)

    # Calcular média móvel (ex: 7 dias)
    df_daily["Média Móvel (7 dias)"] = df_daily["Total"].rolling(window=7, center=True, min_periods=1).mean()

    base = alt.Chart(df_daily).encode(
        x=alt.X("Data:T", title="Data", axis=alt.Axis(
            format="%d/%m", 
            labelAngle=-45, 
            labelColor=COR_TEXTO_SECUNDARIO, 
            titleColor=COR_TEXTO_PRINCIPAL,
            grid=False
        ))
    )

    # Barras arredondadas e mais grossas
    bars = base.mark_bar(
        cornerRadiusTopLeft=8,
        cornerRadiusTopRight=8,
        size=20, # Barras mais grossas
        opacity=0.9
    ).encode(
        y=alt.Y("Total:Q", title="Vendas Diárias (R$)", axis=alt.Axis(
            labelColor=COR_TEXTO_SECUNDARIO, 
            titleColor=COR_TEXTO_PRINCIPAL,
            grid=False
        )),
        color=alt.value(CORES_MODO_ESCURO[0]), # Cor azul principal
        tooltip=[
            alt.Tooltip("Data:T", title="Data", format="%d/%m/%Y"),
            alt.Tooltip("Total:Q", title="Vendas", format=",.2f")
        ]
    )

    line = base.mark_line(color=CORES_MODO_ESCURO[1], strokeWidth=3).encode(
        y=alt.Y("Média Móvel (7 dias):Q", title="Média Móvel", axis=alt.Axis(
            labelColor=COR_TEXTO_SECUNDARIO, 
            titleColor=COR_TEXTO_PRINCIPAL,
            grid=False
        )),
        tooltip=[
            alt.Tooltip("Data:T", title="Data", format="%d/%m/%Y"),
            alt.Tooltip("Média Móvel (7 dias):Q", title="Média Móvel (7d)", format=",.2f")
        ]
    )

    chart = alt.layer(bars, line).resolve_scale(
        y="independent" # Escalas Y independentes
    ).properties(
        height=500 # Altura fixa
        # Largura será definida por use_container_width=True
    ).configure_view(
        strokeOpacity=0 # Remove borda
    ).interactive() # Habilita zoom e pan

    return chart

# Gráfico de Média de Vendas por Dia da Semana (Altura Fixa 500px)
def create_weekday_sales_chart(df):
    """Cria gráfico de barras da média de vendas por dia da semana."""
    if df.empty or "DiaSemana" not in df.columns or "Total" not in df.columns:
        return alt.Chart(pd.DataFrame({'A': []})).mark_text(text='Dados insuficientes').properties(height=500)

    # Usar observed=False é importante com CategoricalDtype
    weekday_avg = df.groupby("DiaSemana", observed=False)["Total"].mean().reset_index()
    weekday_avg = weekday_avg.dropna() # Remove dias sem dados

    if weekday_avg.empty:
        return alt.Chart(pd.DataFrame({'A': []})).mark_text(text='Sem dados de média semanal').properties(height=500)

    chart = alt.Chart(weekday_avg).mark_bar(
        cornerRadius=8, # Bordas arredondadas
        size=30 # Barras mais grossas
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
            grid=False
        )),
        color=alt.Color("DiaSemana:N", legend=None, scale=alt.Scale(range=CORES_MODO_ESCURO)), # Cores diferentes por dia
        tooltip=[
            alt.Tooltip("DiaSemana:O", title="Dia"),
            alt.Tooltip("Total:Q", title="Média (R$)", format=",.2f")
        ]
    ).properties(
        height=500 # Altura fixa
        # Largura será definida por use_container_width=True
    ).configure_view(
        strokeOpacity=0 # Remove borda
    )
    return chart

# Gráfico de Evolução Patrimonial Acumulado (Altura Fixa 500px)
def create_cumulative_evolution_chart(df):
    """Cria gráfico de área da evolução acumulada de vendas com destaque no último valor."""
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        return alt.Chart(pd.DataFrame({'A': []})).mark_text(text='Dados insuficientes').properties(height=500)

    df_sorted = df.sort_values("Data").copy()
    df_sorted.dropna(subset=["Data", "Total"], inplace=True)
    if df_sorted.empty:
        return alt.Chart(pd.DataFrame({'A': []})).mark_text(text='Sem dados para evolução').properties(height=500)

    df_sorted["Total_Acumulado"] = df_sorted["Total"].cumsum()

    # Cores solicitadas
    cor_linha = "darkgreen"
    cor_inicio_grad = "white"
    cor_fim_grad = "darkgreen"

    # Obter o último valor para destacar
    ultimo_valor = df_sorted["Total_Acumulado"].iloc[-1] if not df_sorted.empty else 0
    ultimo_data = df_sorted["Data"].iloc[-1] if not df_sorted.empty else None

    base = alt.Chart(df_sorted).encode(
        x=alt.X("Data:T", title="Data", axis=alt.Axis(
            format="%d/%m/%Y", 
            labelAngle=-45, 
            labelColor=COR_TEXTO_SECUNDARIO, 
            titleColor=COR_TEXTO_PRINCIPAL,
            grid=False
        ))
    )

    area = base.mark_area(
        line={"color": cor_linha, "strokeWidth": 2.5},
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color=cor_inicio_grad, offset=0),
                alt.GradientStop(color=cor_fim_grad, offset=1)
            ],
            x1=1, x2=1, y1=1, y2=0 # Gradiente vertical
        ),
        opacity=0.7
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

    # Adicionar ponto para destacar o último valor
    if ultimo_data is not None:
        point_data = pd.DataFrame({
            "Data": [ultimo_data],
            "Total_Acumulado": [ultimo_valor],
            "Label": [f"Total: {format_brl(ultimo_valor)}"]
        })
        
        point = alt.Chart(point_data).mark_circle(
            size=100,
            color="red",
            opacity=0.8
        ).encode(
            x="Data:T",
            y="Total_Acumulado:Q",
            tooltip=[
                alt.Tooltip("Data:T", title="Data", format="%d/%m/%Y"),
                alt.Tooltip("Total_Acumulado:Q", title="Total Acumulado", format=",.2f")
            ]
        )
        
        text = alt.Chart(point_data).mark_text(
            align="left",
            baseline="middle",
            dx=15,
            dy=-15,
            fontSize=14,
            fontWeight="bold",
            color="white"
        ).encode(
            x="Data:T",
            y="Total_Acumulado:Q",
            text="Label:N"
        )
        
        chart = alt.layer(area, point, text).properties(
            height=500 # Altura fixa
            # Largura será definida por use_container_width=True
        ).configure_view(
            strokeOpacity=0 # Remove borda
        ).interactive()
    else:
        chart = area.properties(
            height=500 # Altura fixa
            # Largura será definida por use_container_width=True
        ).configure_view(
            strokeOpacity=0 # Remove borda
        ).interactive()

    return chart

# --- Funções Heatmap Plotly (Integradas e Adaptadas) ---

def criar_calendario_anual_heatmap(df, ano):
    """Cria calendário anual Plotly com dados do DataFrame e altura fixa 500px."""
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        return go.Figure().update_layout(height=500, title=f"Sem dados para o calendário de {ano}")

    df_ano = df[df['Data'].dt.year == ano].copy()
    if df_ano.empty:
        return go.Figure().update_layout(height=500, title=f"Sem dados para o calendário de {ano}")

    # Criar range completo do ano
    dates_completo = pd.date_range(f'{ano}-01-01', f'{ano}-12-31', freq='D')
    df_ano_completo = pd.DataFrame(index=dates_completo)

    # Agrupar vendas por dia (caso haja múltiplas entradas para o mesmo dia)
    vendas_diarias = df_ano.groupby(df_ano['Data'].dt.date)['Total'].sum()
    vendas_diarias.index = pd.to_datetime(vendas_diarias.index)

    # Mapear vendas para o calendário completo
    df_ano_completo['Total_Vendas'] = df_ano_completo.index.map(vendas_diarias).fillna(0)

    # Adicionar detalhes para hover (se disponíveis no df original)
    df_ano_completo['Cartão'] = df_ano_completo.index.map(df_ano.set_index('Data')['Cartão']).fillna(0)
    df_ano_completo['Dinheiro'] = df_ano_completo.index.map(df_ano.set_index('Data')['Dinheiro']).fillna(0)
    df_ano_completo['Pix'] = df_ano_completo.index.map(df_ano.set_index('Data')['Pix']).fillna(0)

    df_ano_completo['Data'] = df_ano_completo.index
    df_ano_completo['data_str'] = df_ano_completo['Data'].dt.strftime('%d/%m/%Y')
    df_ano_completo['dia_semana'] = df_ano_completo['Data'].dt.dayofweek  # 0=Monday

    primeiro_dia = datetime(ano, 1, 1).date()
    primeiro_dia_semana = primeiro_dia.weekday()

    x_positions = []
    y_positions = []
    valores = []
    hover_texts = []

    for _, row in df_ano_completo.iterrows():
        dias_desde_inicio = (row['Data'].date() - primeiro_dia).days
        semana = (dias_desde_inicio + primeiro_dia_semana) // 7
        dia_semana = (dias_desde_inicio + primeiro_dia_semana) % 7

        x_positions.append(semana)
        y_positions.append(dia_semana)

        total_vendas = row['Total_Vendas']
        if total_vendas == 0:
            categoria = 0
        elif total_vendas < 1500:
            categoria = 1
        elif total_vendas < 2500:
            categoria = 2
        elif total_vendas < 3000:
            categoria = 3
        else:
            categoria = 4
        valores.append(categoria)

        if total_vendas > 0:
            hover_text = (f"📅 {row['data_str']}<br>"
                         f"💰 Total: {format_brl(total_vendas)}<br>"
                         f"💳 Cartão: {format_brl(row['Cartão'])}<br>"
                         f"💵 Dinheiro: {format_brl(row['Dinheiro'])}<br>"
                         f"📱 Pix: {format_brl(row['Pix'])}")
        else:
            hover_text = f"📅 {row['data_str']}<br>❌ Sem vendas"
        hover_texts.append(hover_text)

    max_semana = max(x_positions) + 1
    matriz_vendas = np.full((7, max_semana), 0.0)
    matriz_hover = np.full((7, max_semana), '', dtype=object)

    for x, y, valor, hover in zip(x_positions, y_positions, valores, hover_texts):
        if 0 <= y < 7 and 0 <= x < max_semana:
            matriz_vendas[y, x] = valor
            matriz_hover[y, x] = hover

    escala_4_tons = [
        [0.0, '#161b22'], [0.001, '#39D353'], [0.25, '#39D353'],
        [0.251, '#37AB4B'], [0.5, '#37AB4B'], [0.501, '#006D31'],
        [0.75, '#006D31'], [0.751, '#0D4428'], [1.0, '#0D4428']
    ]

    fig = go.Figure(data=go.Heatmap(
        z=matriz_vendas,
        text=matriz_hover,
        hovertemplate='%{text}<extra></extra>',
        colorscale=escala_4_tons,
        showscale=False,
        zmin=0,
        zmax=4,
        xgap=3,
        ygap=3,
        hoverongaps=False
    ))

    meses_posicoes = []
    meses_nomes_plotly = []
    for mes in range(1, 13):
        primeiro_dia_mes = datetime(ano, mes, 1).date()
        dias_desde_inicio = (primeiro_dia_mes - primeiro_dia).days
        semana_mes = (dias_desde_inicio + primeiro_dia_semana) // 7
        meses_posicoes.append(semana_mes)
        meses_nomes_plotly.append(calendar.month_abbr[mes].replace('.', '')) # Nomes curtos PT-BR

    fig.update_layout(
        title=f"Heatmap Anual de Vendas - {ano}",
        height=500, # Altura fixa
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COR_TEXTO_PRINCIPAL, family="Arial"),
        xaxis=dict(
            title="", showgrid=False, zeroline=False, tickmode='array',
            tickvals=meses_posicoes, ticktext=meses_nomes_plotly,
            tickfont=dict(color=COR_TEXTO_PRINCIPAL, size=12),
            side='top', tickangle=0, ticklabelstandoff=5
        ),
        yaxis=dict(
            title="", showgrid=False, zeroline=False, tickmode='array',
            tickvals=[0, 1, 2, 3, 4, 5, 6],
            ticktext=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
            tickfont=dict(color=COR_TEXTO_PRINCIPAL, size=12),
            ticklen=0, ticklabelstandoff=10 # Aumenta distância do eixo Y
        ),
        title_x=0.5,
        title_font=dict(size=18, color=COR_TEXTO_PRINCIPAL),
        margin=dict(l=50, r=20, t=80, b=20) # Ajuste de margens
    )
    return fig

def criar_heatmap_vendas_mensais(df, ano):
    """Cria heatmap mensal horizontal Plotly com dados do DataFrame e altura fixa 500px."""
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        return go.Figure().update_layout(height=500, title=f"Sem dados para o heatmap mensal de {ano}")

    df_ano = df[df['Data'].dt.year == ano].copy()
    if df_ano.empty:
        return go.Figure().update_layout(height=500, title=f"Sem dados para o heatmap mensal de {ano}")

    df_ano['Mes'] = df_ano['Data'].dt.month
    vendas_mensais = df_ano.groupby('Mes').agg({
        'Total': 'sum',
        'Cartão': 'sum',
        'Dinheiro': 'sum',
        'Pix': 'sum'
    }).reindex(range(1, 13), fill_value=0).reset_index()

    meses_nomes_plotly = [calendar.month_abbr[m].replace('.', '') for m in range(1, 13)]
    vendas_mensais['Mes_Nome'] = vendas_mensais['Mes'].map(lambda x: meses_nomes_plotly[x-1])

    matriz_mensal = np.zeros((1, 12))
    matriz_hover_mensal = np.full((1, 12), '', dtype=object)

    # Categorizar valores mensais (exemplo, ajustar conforme necessidade)
    max_venda_mensal = vendas_mensais['Total'].max()
    bins = [0, max_venda_mensal * 0.25, max_venda_mensal * 0.5, max_venda_mensal * 0.75, max_venda_mensal + 1]
    labels = [1, 2, 3, 4]
    vendas_mensais['Categoria'] = pd.cut(vendas_mensais['Total'], bins=bins, labels=labels, right=False, include_lowest=True).fillna(0).astype(int)

    for mes_idx in range(12):
        mes_num = mes_idx + 1
        dados_mes = vendas_mensais[vendas_mensais['Mes'] == mes_num]
        if not dados_mes.empty:
            row = dados_mes.iloc[0]
            total_mes = row['Total']
            categoria = row['Categoria']
            matriz_mensal[0, mes_idx] = categoria if total_mes > 0 else 0

            if total_mes > 0:
                hover_text = (f"📅 {row['Mes_Nome']} {ano}<br>"
                             f"💰 Total: {format_brl(total_mes)}<br>"
                             f"💳 Cartão: {format_brl(row['Cartão'])}<br>"
                             f"💵 Dinheiro: {format_brl(row['Dinheiro'])}<br>"
                             f"📱 Pix: {format_brl(row['Pix'])}")
            else:
                 hover_text = f"📅 {row['Mes_Nome']} {ano}<br>❌ Sem vendas"
        else:
            matriz_mensal[0, mes_idx] = 0
            hover_text = f"📅 {meses_nomes_plotly[mes_idx]} {ano}<br>❌ Sem vendas"

        matriz_hover_mensal[0, mes_idx] = hover_text

    escala_4_tons = [
        [0.0, '#161b22'], [0.001, '#39D353'], [0.25, '#39D353'],
        [0.251, '#37AB4B'], [0.5, '#37AB4B'], [0.501, '#006D31'],
        [0.75, '#006D31'], [0.751, '#0D4428'], [1.0, '#0D4428']
    ]

    fig = go.Figure(data=go.Heatmap(
        z=matriz_mensal,
        text=matriz_hover_mensal,
        hovertemplate='%{text}<extra></extra>',
        colorscale=escala_4_tons,
        showscale=False,
        zmin=0,
        zmax=4,
        xgap=5,
        ygap=5,
        hoverongaps=False
    ))

    fig.update_layout(
        title=f'Heatmap Mensal de Vendas - {ano}',
        height=250, # Altura menor para o mensal
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COR_TEXTO_PRINCIPAL, family="Arial"),
        xaxis=dict(
            title="", showgrid=False, zeroline=False, tickmode='array',
            tickvals=list(range(12)), ticktext=meses_nomes_plotly,
            tickfont=dict(color=COR_TEXTO_PRINCIPAL, size=12),
            side='bottom'
        ),
        yaxis=dict(
            title="", showgrid=False, zeroline=False, showticklabels=False
        ),
        title_x=0.5,
        title_font=dict(size=18, color=COR_TEXTO_PRINCIPAL),
        margin=dict(l=50, r=20, t=50, b=30) # Ajuste de margens
    )
    return fig

# --- Função Principal da Aplicação ---
def main():
    # --- Header --- #
    col1_header, col2_header = st.columns([1, 5])
    with col1_header:
        st.image(LOGO_URL, width=210) # Logo com tamanho ajustado no CSS
    with col2_header:
        st.title("Sistema Financeiro - Clips Burger")
        st.caption("Gestão de vendas e análise de desempenho")
    st.markdown("<hr style='margin-top: 0;'>", unsafe_allow_html=True)

    # --- Leitura e Processamento Inicial dos Dados --- #
    df_raw = read_sales_data()
    if df_raw is None or df_raw.empty:
        st.warning("Não foi possível carregar os dados de vendas. Verifique a conexão ou a planilha.")
        st.stop() # Interrompe a execução se não houver dados

    df_processed = process_data(df_raw)
    if df_processed.empty:
        st.info("Não há dados processados para exibir. Comece registrando vendas.")
        # Ainda permite o cadastro

    # --- Inicialização do Estado da Sessão --- #
    if 'registro_sucesso' not in st.session_state:
        st.session_state.registro_sucesso = False
    if 'last_registered_date' not in st.session_state:
        st.session_state.last_registered_date = None

    # --- Definição das Tabs --- # 
    # Removidas: "Análise Detalhada", "Estatísticas"
    tab_cadastro, tab_dashboard, tab_analise_contabil = st.tabs([
        "📝 Cadastro",
        "📊 Dashboard",
        "🧾 Análise Contábil"
    ])

    # --- Tab: Cadastro --- #
    with tab_cadastro:
        st.header("Registro de Vendas Diárias")
        worksheet = get_worksheet() # Obter a worksheet para passar para a função

        with st.form(key="sales_form", clear_on_submit=True):
            col1_form, col2_form, col3_form, col4_form = st.columns(4)
            with col1_form:
                selected_date = st.date_input("Data da Venda", datetime.now())
            with col2_form:
                valor_cartao = st.number_input("Valor Cartão (R$)", min_value=0.0, format="%.2f", step=10.0, key="cartao")
            with col3_form:
                valor_dinheiro = st.number_input("Valor Dinheiro (R$)", min_value=0.0, format="%.2f", step=10.0, key="dinheiro")
            with col4_form:
                valor_pix = st.number_input("Valor PIX (R$)", min_value=0.0, format="%.2f", step=10.0, key="pix")

            submit_button = st.form_submit_button(label="Registrar Venda")

            if submit_button:
                if worksheet:
                    success = add_data_to_sheet(selected_date, valor_cartao, valor_dinheiro, valor_pix, worksheet)
                    if success:
                        st.session_state.registro_sucesso = True
                        st.session_state.last_registered_date = selected_date
                        # Mensagem de sucesso será exibida fora do form
                    else:
                        st.error("Falha ao registrar a venda.")
                        st.session_state.registro_sucesso = False
                else:
                    st.error("Erro de conexão com a planilha. Não foi possível registrar.")
                    st.session_state.registro_sucesso = False

        # Exibir mensagem de sucesso e tabela filtrada FORA do form, se o registro foi bem-sucedido
        if st.session_state.get('registro_sucesso', False):
            st.success("✅ Registro adicionado com sucesso!")
            st.divider()
            st.subheader("Últimos Registros")

            # Recarrega e processa os dados após o registro
            df_raw_updated = read_sales_data()
            df_processed_updated = process_data(df_raw_updated)

            if not df_processed_updated.empty:
                # Filtra para mostrar talvez os últimos 7 dias ou registros recentes
                seven_days_ago = datetime.now() - timedelta(days=7)
                df_recent = df_processed_updated[df_processed_updated['Data'] >= seven_days_ago]
                
                # Ou filtra pelo dia registrado (se houver poucos dados)
                # if st.session_state.last_registered_date:
                #    df_recent = df_processed_updated[df_processed_updated['Data'].dt.date == st.session_state.last_registered_date.date()]
                # else:
                #    df_recent = df_processed_updated.tail(5) # Fallback

                if not df_recent.empty:
                    st.dataframe(df_recent[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']].rename(columns={'DataFormatada': 'Data'}), use_container_width=True)
                else:
                    # Se o filtro de 7 dias não retornar nada, mostra os últimos 5
                    st.dataframe(df_processed_updated.tail(5)[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']].rename(columns={'DataFormatada': 'Data'}), use_container_width=True)
            else:
                st.info("Ainda não há registros para exibir.")
            
            # Resetar o estado para não mostrar a tabela novamente sem novo registro
            # st.session_state.registro_sucesso = False # Comentar se quiser manter visível até sair da tab

    # --- Tab: Dashboard --- #
    with tab_dashboard:
        st.header("Visão Geral do Desempenho")

        if df_processed.empty:
            st.warning("Não há dados suficientes para gerar o dashboard.")
        else:
            # --- Filtros (Opcional, pode ser adicionado se necessário) ---
            # Exemplo: year_filter = st.selectbox("Selecionar Ano", options=df_processed['Ano'].unique(), index=len(df_processed['Ano'].unique())-1)
            # df_filtered = df_processed[df_processed['Ano'] == year_filter]
            df_filtered = df_processed # Usar todos os dados por enquanto
            current_year = datetime.now().year
            available_years = sorted(df_processed['Ano'].unique(), reverse=True)
            selected_year = st.selectbox("Selecione o Ano para Análise Detalhada", options=available_years, index=0)
            df_year_filtered = df_processed[df_processed['Ano'] == selected_year]

            # --- Resumo Financeiro (Movido de Estatísticas) --- #
            st.subheader("Resumo Financeiro")
            total_revenue = df_filtered["Total"].sum()
            avg_daily_sales = df_filtered.groupby(df_filtered['Data'].dt.date)["Total"].sum().mean()
            max_daily_sale = df_filtered.groupby(df_filtered['Data'].dt.date)["Total"].sum().max()
            min_daily_sale = df_filtered[df_filtered['Total'] > 0].groupby(df_filtered['Data'].dt.date)["Total"].sum().min()

            col_res1, col_res2, col_res3, col_res4 = st.columns(4)
            with col_res1:
                st.metric(label="💰 Faturamento Total", value=format_brl(total_revenue))
            with col_res2:
                st.metric(label="📅 Média Diária", value=format_brl(avg_daily_sales))
            with col_res3:
                st.metric(label="📈 Maior Venda Diária", value=format_brl(max_daily_sale))
            with col_res4:
                st.metric(label="📉 Menor Venda Diária (com vendas)", value=format_brl(min_daily_sale))

            # --- Heatmaps (Item 9) --- #
            st.divider()
            st.subheader(f"Calendário de Atividade ({selected_year})")
            heatmap_anual = criar_calendario_anual_heatmap(df_processed, selected_year)
            st.plotly_chart(heatmap_anual, use_container_width=True)
            
            heatmap_mensal = criar_heatmap_vendas_mensais(df_processed, selected_year)
            st.plotly_chart(heatmap_mensal, use_container_width=True)

            # --- Assiduidade (Movido de Estatísticas) --- #
            st.divider()
            st.subheader("Assiduidade (Frequência de Trabalho)")
            total_days_period = (df_filtered["Data"].max() - df_filtered["Data"].min()).days + 1
            days_worked = df_filtered["Data"].nunique()
            work_frequency_perc = (days_worked / total_days_period) * 100 if total_days_period > 0 else 0

            col_assid1, col_assid2, col_assid3 = st.columns(3)
            with col_assid1:
                st.metric(label="🗓️ Dias Trabalhados", value=f"{days_worked} dias")
            with col_assid2:
                st.metric(label="⏳ Período Analisado", value=f"{total_days_period} dias")
            with col_assid3:
                st.metric(label="⏱️ Frequência", value=f"{work_frequency_perc:.1f}%")
            # Análise de Frequência (Texto/Tabela) - Item 6 (parte inferior)
            # (Será adicionado mais abaixo conforme layout) 

            # --- Métodos de Pagamento (Métricas - Movido de Estatísticas) --- #
            st.divider()
            st.subheader("Métodos de Pagamento (Valores Totais)")
            total_cartao = df_filtered["Cartão"].sum()
            total_dinheiro = df_filtered["Dinheiro"].sum()
            total_pix = df_filtered["Pix"].sum()

            col_pay1, col_pay2, col_pay3 = st.columns(3)
            with col_pay1:
                st.metric(label="💳 Cartão", value=format_brl(total_cartao))
            with col_pay2:
                st.metric(label="💵 Dinheiro", value=format_brl(total_dinheiro))
            with col_pay3:
                st.metric(label="📱 PIX", value=format_brl(total_pix))

            # --- Gráficos Principais (Item 5) --- #
            st.divider()
            st.subheader("Análise de Vendas")
            col_chart1, col_chart2 = st.columns([2, 1]) # 2/3 para vendas diárias, 1/3 para radial
            with col_chart1:
                st.write("**Vendas Diárias e Média Móvel**")
                daily_sales_chart = create_advanced_daily_sales_chart(df_year_filtered) # Usar dados do ano selecionado
                st.altair_chart(daily_sales_chart, use_container_width=True)
            with col_chart2:
                st.write("**Distribuição por Pagamento**")
                radial_chart = create_radial_plot(df_year_filtered) # Usar dados do ano selecionado
                st.altair_chart(radial_chart, use_container_width=True)

            st.write("**Média de Vendas por Dia da Semana**")
            weekday_sales_chart = create_weekday_sales_chart(df_year_filtered) # Usar dados do ano selecionado
            st.altair_chart(weekday_sales_chart, use_container_width=True)

            # --- Ranking e Análise de Frequência (Item 6) --- #
            st.divider()
            col_rank, col_freq_analysis = st.columns(2)
            with col_rank:
                st.subheader("🏆 Ranking - Dias da Semana (Média Vendas)")
                weekday_avg_rank = df_year_filtered.groupby("DiaSemana", observed=False)["Total"].mean().reset_index()
                weekday_avg_rank = weekday_avg_rank.dropna().sort_values(by="Total", ascending=False)
                weekday_avg_rank["Média (R$)"] = weekday_avg_rank["Total"].apply(format_brl)
                st.dataframe(weekday_avg_rank[['DiaSemana', 'Média (R$)']].reset_index(drop=True), use_container_width=True)
            
            with col_freq_analysis:
                st.subheader("⏱️ Análise de Frequência de Trabalho")
                # Tabela de frequência por dia da semana
                work_freq_weekday = df_year_filtered['DiaSemana'].value_counts(sort=False).reset_index()
                work_freq_weekday.columns = ['DiaSemana', 'Dias Trabalhados']
                # Garantir a ordem correta e preencher dias não trabalhados
                work_freq_weekday['DiaSemana'] = pd.Categorical(work_freq_weekday['DiaSemana'], categories=dias_semana_ordem, ordered=True)
                work_freq_weekday = work_freq_weekday.set_index('DiaSemana').reindex(dias_semana_ordem, fill_value=0).reset_index()
                st.dataframe(work_freq_weekday, use_container_width=True)

            # --- Insights (Item 7) --- #
            st.divider()
            st.subheader("💡 Insights e Recomendações")
            
            # Insight 1: Custo vs Conveniência (Cartão)
            perc_cartao = (total_cartao / total_revenue) * 100 if total_revenue > 0 else 0
            st.markdown(f"""
            <div class="insight-container">
                <h4>💳 Análise de Pagamentos com Cartão</h4>
                <p>
                As vendas via cartão representam <strong>{perc_cartao:.1f}%</strong> do faturamento total ({format_brl(total_cartao)}).
                Embora conveniente para o cliente, é crucial analisar as taxas associadas (crédito, débito, antecipação).
                Avalie o impacto líquido dessas taxas na lucratividade. Considere estratégias para incentivar sutilmente métodos mais vantajosos como PIX ou dinheiro, como pequenos descontos ou programas de fidelidade associados a esses métodos.
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Insight 2: Dias de Maior e Menor Movimento
            if not weekday_avg_rank.empty:
                best_day = weekday_avg_rank.iloc[0]['DiaSemana']
                worst_day = weekday_avg_rank.iloc[-1]['DiaSemana']
                avg_best = weekday_avg_rank.iloc[0]['Total']
                avg_worst = weekday_avg_rank.iloc[-1]['Total']
                st.markdown(f"""
                <div class="insight-container">
                    <h4>📅 Desempenho Semanal</h4>
                    <p>
                    Seu dia de maior movimento em média é <strong>{best_day}</strong> (média de {format_brl(avg_best)}), enquanto <strong>{worst_day}</strong> apresenta a menor média ({format_brl(avg_worst)}).
                    Analise os fatores que contribuem para o sucesso de {best_day} (promoções, fluxo de clientes, eventos locais) e veja se podem ser replicados.
                    Para {worst_day}, considere ações específicas como promoções direcionadas, combos especiais ou ajuste de horário/equipe para otimizar custos ou impulsionar vendas.
                    </p>
                </div>
                """, unsafe_allow_html=True)

            # Insight 3: Frequência de Trabalho
            st.markdown(f"""
            <div class="insight-container">
                <h4>⏱️ Consistência Operacional</h4>
                <p>
                A frequência de trabalho registrada no período foi de <strong>{work_frequency_perc:.1f}%</strong> ({days_worked} de {total_days_period} dias).
                Uma alta frequência sugere consistência, mas analise se os dias não trabalhados foram planejados (folgas, feriados) ou imprevistos.
                Dias parados inesperadamente representam perda de receita potencial. Monitore a regularidade para garantir a maximização das oportunidades de venda.
                </p>
            </div>
            """, unsafe_allow_html=True)

    # --- Tab: Análise Contábil --- #
    with tab_analise_contabil:
        st.header("Análise Contábil Simplificada")

        if df_processed.empty:
            st.warning("Não há dados suficientes para a análise contábil.")
        else:
            # Filtro de período para DRE (Exemplo: último mês)
            today = datetime.now()
            first_day_current_month = today.replace(day=1)
            last_day_last_month = first_day_current_month - timedelta(days=1)
            first_day_last_month = last_day_last_month.replace(day=1)

            start_date_default = first_day_last_month
            end_date_default = last_day_last_month

            col_dre_filter1, col_dre_filter2 = st.columns(2)
            with col_dre_filter1:
                start_date_dre = st.date_input("Data Inicial DRE", start_date_default)
            with col_dre_filter2:
                end_date_dre = st.date_input("Data Final DRE", end_date_default)

            if start_date_dre > end_date_dre:
                st.error("Data inicial não pode ser maior que a data final.")
            else:
                # Filtrar dados para o período selecionado
                mask_dre = (df_processed['Data'].dt.date >= start_date_dre) & (df_processed['Data'].dt.date <= end_date_dre)
                df_dre_filtered = df_processed.loc[mask_dre]

                if df_dre_filtered.empty:
                    st.info(f"Sem dados de vendas entre {start_date_dre.strftime('%d/%m/%Y')} e {end_date_dre.strftime('%d/%m/%Y')}.")
                else:
                    # --- DRE Simplificada --- #
                    st.subheader("Demonstrativo de Resultado do Exercício (DRE) - Simplificado")

                    receita_bruta = df_dre_filtered['Total'].sum()
                    # Simulações de custos e impostos (AJUSTAR CONFORME REALIDADE DO NEGÓCIO)
                    perc_custo_mercadoria = 0.35 # Ex: 35% CMV
                    perc_impostos_sobre_venda = 0.06 # Ex: 6% Simples Nacional
                    custos_operacionais_fixos = 1500 # Ex: Aluguel, salários base, etc. (Mensal estimado para o período)
                    taxas_cartao_estimada = df_dre_filtered['Cartão'].sum() * 0.035 # Ex: 3.5% taxa média cartão

                    custo_mercadoria_vendida = receita_bruta * perc_custo_mercadoria
                    impostos_sobre_venda = receita_bruta * perc_impostos_sobre_venda
                    receita_liquida = receita_bruta - impostos_sobre_venda
                    lucro_bruto = receita_liquida - custo_mercadoria_vendida
                    despesas_operacionais = custos_operacionais_fixos + taxas_cartao_estimada
                    lucro_operacional = lucro_bruto - despesas_operacionais

                    # Criação da tabela DRE com HTML para garantir alinhamento
                    dre_data = {
                        "Descrição": [
                            "(+) Receita Bruta de Vendas",
                            "(-) Impostos sobre Vendas (Simples Nacional)",
                            "(=) Receita Líquida",
                            "(-) Custo da Mercadoria Vendida (CMV)",
                            "(=) Lucro Bruto",
                            "(-) Despesas Operacionais",
                            "   - Custos Fixos Estimados",
                            "   - Taxas de Cartão Estimadas",
                            "(=) Lucro Operacional (Antes IR/CSLL)"
                        ],
                        "Valor (R$)": [
                            format_brl(receita_bruta),
                            format_brl(impostos_sobre_venda),
                            format_brl(receita_liquida),
                            format_brl(custo_mercadoria_vendida),
                            format_brl(lucro_bruto),
                            "", # Linha de título para despesas
                            format_brl(custos_operacionais_fixos),
                            format_brl(taxas_cartao_estimada),
                            format_brl(lucro_operacional)
                        ]
                    }
                    
                    # Montar HTML da tabela DRE
                    html_dre = "<div class='dre-table'><table><thead><tr><th>Descrição</th><th>Em R$</th></tr></thead><tbody>"
                    for i, desc in enumerate(dre_data["Descrição"]):
                        valor = dre_data["Valor (R$) "][i]
                        style = "font-weight: bold;" if "(=)" in desc else ""
                        padding_left = "padding-left: 20px;" if desc.strip().startswith("-") else ""
                        html_dre += f"<tr><td style='{style}{padding_left}'>{desc}</td><td style='{style}'>{valor}</td></tr>"
                    html_dre += "</tbody></table></div>"

                    st.markdown(html_dre, unsafe_allow_html=True)
                    st.caption("Valores de custos, impostos e taxas são *estimativas* para demonstração.")

                    # --- Gráfico de Evolução Patrimonial --- #
                    st.divider()
                    st.subheader("Evolução do Faturamento Acumulado (Todo Período)")
                    cumulative_chart = create_cumulative_evolution_chart(df_processed) # Usar dados totais
                    st.altair_chart(cumulative_chart, use_container_width=True)

# --- Execução Principal --- #
if __name__ == "__main__":
    main()
