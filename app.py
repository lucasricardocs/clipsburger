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

# CSS para melhorar a aparência (Com aura celestial ajustada)
def inject_css():
    st.markdown(f"""
    <style>
    /* --- Geral --- */
    .stApp {{
        background: linear-gradient(135deg, #1e2a4a 0%, #2a3a5f 50%, #2d2a5a 100%);
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
        white-space: normal;
        overflow-wrap: break-word;
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
        min-height: 120px;
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
        margin: 0 0 0.8rem 0;
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
        /* Animação da aura celestial ajustada */
        animation: celestialPulseNew 6s ease-in-out infinite;
    }}

    /* Keyframes para a aura pulsante celestial (Branco, Azul, Roxo) */
    @keyframes celestialPulseNew {{
        0%, 100% {{
            filter: drop-shadow(0 0 12px rgba(255, 255, 255, 0.7)) drop-shadow(0 0 25px rgba(255, 255, 255, 0.5)); /* Branco */
        }}
        33% {{
            filter: drop-shadow(0 0 15px rgba(135, 206, 250, 0.8)) drop-shadow(0 0 30px rgba(135, 206, 250, 0.6)); /* Azul Celestial (LightSkyBlue) */
        }}
        66% {{
            filter: drop-shadow(0 0 15px rgba(186, 85, 211, 0.8)) drop-shadow(0 0 30px rgba(186, 85, 211, 0.6)); /* Roxo Celestial (MediumOrchid) */
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
        vertical-align: middle;
    }}
    .dre-table td:nth-child(2) {{ 
        text-align: right;
        font-family: 'Courier New', Courier, monospace;
        white-space: pre;
        padding-right: 12px;
    }}
    .dre-table th:nth-child(2) {{ 
        text-align: right;
        padding-right: 12px;
    }}

    /* --- Rodapé --- */
    .footer {{
        margin-top: 3rem;
        padding: 1.5rem 0;
        border-top: 1px solid {COR_SEPARADOR};
        text-align: center;
        font-size: 0.9rem;
        color: {COR_TEXTO_SECUNDARIO};
    }}
    .footer a {{
        color: {CORES_MODO_ESCURO[0]};
        text-decoration: none;
        transition: color 0.3s ease;
    }}
    .footer a:hover {{
        color: {CORES_MODO_ESCURO[1]};
        text-decoration: underline;
    }}

    /* --- Responsividade --- */
    @media (max-width: 992px) {{ 
        .logo-image {{ width: 180px; }}
        .logo-container h1 {{ font-size: 2rem; }}
        div[data-testid="stMetric"] {{ padding: 1rem; min-height: 100px; }}
        .insight-container {{ padding: 1.2rem; min-height: 110px; }}
        .st-emotion-cache-1l269bu > div {{ 
             flex-direction: column;
        }}
    }}

    @media (max-width: 768px) {{ 
        .logo-image {{ width: 150px; }}
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
        .logo-image {{ width: 120px; }}
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
        # Tenta carregar credenciais do Streamlit Secrets
        if "google_credentials" in st.secrets:
            credentials_dict = st.secrets["google_credentials"]
            if credentials_dict:
                creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
                gc = gspread.authorize(creds)
                return gc
            else:
                st.error("As credenciais do Google em st.secrets estão vazias.")
                return None
        else:
            st.error("Credenciais do Google ('google_credentials') não encontradas em st.secrets. Configure o arquivo .streamlit/secrets.toml")
            return None
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
@st.cache_data(ttl=600)
def read_sales_data():
    """Lê todos os registros da planilha de vendas e retorna como DataFrame."""
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records()
            if not rows:
                return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix"])

            df = pd.DataFrame(rows)

            for col in ["Cartão", "Dinheiro", "Pix"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    df[col] = 0

            if "Data" not in df.columns:
                 st.warning("Coluna 'Data' não encontrada na planilha. Criando coluna vazia.")
                 df["Data"] = pd.NaT
            else:
                try:
                    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
                except ValueError:
                    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

            df.dropna(subset=["Data"], inplace=True)
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
        formatted_date_str = date.strftime("%d/%m/%Y")
        new_row = [formatted_date_str, cartao_val, dinheiro_val, pix_val]
        worksheet_obj.append_row(new_row)
        st.cache_data.clear()
        return True
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
        cols = ["Data", "Cartão", "Dinheiro", "Pix", "Total", "Ano", "Mês", "MêsNome", "AnoMês", "DataFormatada", "DiaSemana", "DiaDoMes"]
        empty_df = pd.DataFrame(columns=cols)
        for col in ["Cartão", "Dinheiro", "Pix", "Total", "Ano", "Mês", "DiaDoMes"]:
             empty_df[col] = pd.Series(dtype="float")
        empty_df["Data"] = pd.Series(dtype="datetime64[ns]")
        for col in ["MêsNome", "AnoMês", "DataFormatada", "DiaSemana"]:
             empty_df[col] = pd.Series(dtype="object")
        return empty_df

    df = df_input.copy()

    if not pd.api.types.is_datetime64_any_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df.dropna(subset=["Data"], inplace=True)

    for col in ["Cartão", "Dinheiro", "Pix"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    if "Total" not in df.columns:
        df["Total"] = df["Cartão"] + df["Dinheiro"] + df["Pix"]

    df["Ano"] = df["Data"].dt.year
    df["Mês"] = df["Data"].dt.month
    df["MêsNome"] = df["Mês"].apply(lambda x: meses_ordem[x-1] if pd.notna(x) and 1 <= x <= 12 else None)
    df["AnoMês"] = df["Data"].dt.strftime("%Y-%m")
    df["DataFormatada"] = df["Data"].dt.strftime("%d/%m/%Y")
    day_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
    df["DiaSemana"] = df["Data"].dt.dayofweek.map(day_map)
    df["DiaDoMes"] = df["Data"].dt.day

    df = df.sort_values(by="Data").reset_index(drop=True)

    if "DiaSemana" in df.columns and not df["DiaSemana"].empty:
        df["DiaSemana"] = pd.Categorical(df["DiaSemana"], categories=dias_semana_ordem, ordered=True)
    if "MêsNome" in df.columns and not df["MêsNome"].empty:
        df["MêsNome"] = pd.Categorical(df["MêsNome"], categories=meses_ordem, ordered=True)

    return df

# --- Funções de Formatação ---
def format_brl(value):
    """Formata valor numérico como moeda brasileira (R$)."""
    try:
        # Verifica se é NaN ou Infinito antes de formatar
        if pd.isna(value) or np.isinf(value):
            return "R$ -"
        return f"R$ {value:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")
    except (ValueError, TypeError):
        return "R$ -"

# --- Funções de Gráficos Interativos (AJUSTADAS E NOVAS) ---

# Gráfico Radial (Altura Fixa 500px, Fundo Transparente)
def create_radial_plot(df):
    """Cria um gráfico radial de métodos de pagamento."""
    # Retorna gráfico vazio se dados insuficientes
    empty_chart = alt.Chart(pd.DataFrame({'value': [1]})).mark_text(text='').properties(height=500).configure_view(fill='transparent')
    
    if df.empty or not any(col in df.columns for col in ["Cartão", "Dinheiro", "Pix"]):
        return empty_chart

    payment_data = pd.DataFrame({
        "Método": ["Cartão", "Dinheiro", "PIX"],
        "Valor": [df["Cartão"].sum(), df["Dinheiro"].sum(), df["Pix"].sum()]
    })
    payment_data = payment_data[payment_data["Valor"] > 0]

    if payment_data.empty:
        return empty_chart

    base = alt.Chart(payment_data).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        radius=alt.Radius("Valor:Q", scale=alt.Scale(type="sqrt", zero=True, rangeMin=20)),
        color=alt.Color("Método:N",
                        scale=alt.Scale(range=CORES_MODO_ESCURO[:len(payment_data)]),
                        legend=alt.Legend(title="Método", orient="bottom", titleColor=COR_TEXTO_PRINCIPAL, labelColor=COR_TEXTO_SECUNDARIO)),
        order=alt.Order("Valor:Q", sort="descending"),
        tooltip=[
            alt.Tooltip("Método:N", title="Método"),
            alt.Tooltip("Valor:Q", title="Valor", format=",.2f")
        ]
    )

    radial_plot = base.mark_arc(innerRadius=30, stroke=COR_FUNDO_CONTAINER, strokeWidth=3).properties(
        height=500,
    ).configure_view(
        stroke=None,
        strokeOpacity=0,
        fill='transparent' # Garante fundo transparente
    ).configure_axis(
        labelColor=COR_TEXTO_SECUNDARIO,
        titleColor=COR_TEXTO_PRINCIPAL,
        grid=False
    ).configure_legend(
        titleColor=COR_TEXTO_PRINCIPAL,
        labelColor=COR_TEXTO_SECUNDARIO
    )

    return radial_plot

# Gráfico de Vendas Diárias (Altura Fixa 500px, Fundo Transparente)
def create_advanced_daily_sales_chart(df):
    """Cria gráfico de barras arredondadas de vendas diárias com linha de média móvel."""
    empty_chart = alt.Chart(pd.DataFrame({'value': [1]})).mark_text(text='').properties(height=500).configure_view(fill='transparent')

    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        return empty_chart

    df_chart = df.copy()
    df_chart.dropna(subset=["Data", "Total"], inplace=True)
    if df_chart.empty:
        return empty_chart

    df_daily = df_chart.groupby(pd.Grouper(key="Data", freq="D"))["Total"].sum().reset_index()
    df_daily = df_daily[df_daily["Total"] > 0]

    if df_daily.empty:
        return empty_chart

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

    bars = base.mark_bar(
        cornerRadiusTopLeft=8,
        cornerRadiusTopRight=8,
        size=20,
        opacity=0.9
    ).encode(
        y=alt.Y("Total:Q", title="Vendas Diárias (R$)", axis=alt.Axis(
            labelColor=COR_TEXTO_SECUNDARIO, 
            titleColor=COR_TEXTO_PRINCIPAL,
            grid=False
        )),
        color=alt.value(CORES_MODO_ESCURO[0]),
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
        y="independent"
    ).properties(
        height=500
    ).configure_view(
        strokeOpacity=0,
        fill='transparent' # Garante fundo transparente
    ).interactive()

    return chart

# Gráfico de Média de Vendas por Dia da Semana (Altura Fixa 500px, Fundo Transparente)
def create_weekday_sales_chart(df):
    """Cria gráfico de barras da média de vendas por dia da semana."""
    empty_chart = alt.Chart(pd.DataFrame({'value': [1]})).mark_text(text='').properties(height=500).configure_view(fill='transparent')

    if df.empty or "DiaSemana" not in df.columns or "Total" not in df.columns:
        return empty_chart

    weekday_avg = df.groupby("DiaSemana", observed=False)["Total"].mean().reset_index()
    weekday_avg = weekday_avg.dropna()

    if weekday_avg.empty:
        return empty_chart

    chart = alt.Chart(weekday_avg).mark_bar(
        cornerRadius=8,
        size=30
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
        color=alt.Color("DiaSemana:N", legend=None, scale=alt.Scale(range=CORES_MODO_ESCURO)),
        tooltip=[
            alt.Tooltip("DiaSemana:O", title="Dia"),
            alt.Tooltip("Total:Q", title="Média (R$)", format=",.2f")
        ]
    ).properties(
        height=500
    ).configure_view(
        strokeOpacity=0,
        fill='transparent' # Garante fundo transparente
    )
    return chart

# Gráfico de Evolução Patrimonial Acumulado (Altura Fixa 500px, Fundo Transparente)
def create_cumulative_evolution_chart(df):
    """Cria gráfico de área da evolução acumulada de vendas com destaque no último valor."""
    empty_chart = alt.Chart(pd.DataFrame({'value': [1]})).mark_text(text='').properties(height=500).configure_view(fill='transparent')

    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        return empty_chart

    df_sorted = df.sort_values("Data").copy()
    df_sorted.dropna(subset=["Data", "Total"], inplace=True)
    if df_sorted.empty:
        return empty_chart

    df_sorted["Total_Acumulado"] = df_sorted["Total"].cumsum()

    cor_linha = "darkgreen"
    cor_inicio_grad = "white"
    cor_fim_grad = "darkgreen"

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
            x1=1, x2=1, y1=1, y2=0
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

    if ultimo_data is not None:
        point_data = pd.DataFrame({
            "Data": [ultimo_data],
            "Total_Acumulado": [ultimo_valor],
            "Label": [f"Último: {format_brl(ultimo_valor)}"] # Texto mais conciso
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
            height=500
        ).configure_view(
            strokeOpacity=0,
            fill='transparent' # Garante fundo transparente
        ).interactive()
    else:
        chart = area.properties(
            height=500
        ).configure_view(
            strokeOpacity=0,
            fill='transparent' # Garante fundo transparente
        ).interactive()

    return chart

# --- Funções Heatmap Plotly (Integradas e Adaptadas) ---

def criar_calendario_anual_heatmap(df, ano):
    """Cria calendário anual Plotly com dados do DataFrame e altura fixa 500px."""
    empty_fig = go.Figure().update_layout(height=500, title=f"Sem dados para o calendário de {ano}", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        return empty_fig

    df_ano = df[df['Data'].dt.year == ano].copy()
    if df_ano.empty:
        return empty_fig

    dates_completo = pd.date_range(f'{ano}-01-01', f'{ano}-12-31', freq='D')
    df_ano_completo = pd.DataFrame(index=dates_completo)

    vendas_diarias = df_ano.groupby(df_ano['Data'].dt.date)['Total'].sum()
    vendas_diarias.index = pd.to_datetime(vendas_diarias.index)

    df_ano_completo['Total_Vendas'] = df_ano_completo.index.map(vendas_diarias).fillna(0)
    df_ano_completo['Cartão'] = df_ano_completo.index.map(df_ano.set_index('Data')['Cartão']).fillna(0)
    df_ano_completo['Dinheiro'] = df_ano_completo.index.map(df_ano.set_index('Data')['Dinheiro']).fillna(0)
    df_ano_completo['Pix'] = df_ano_completo.index.map(df_ano.set_index('Data')['Pix']).fillna(0)

    df_ano_completo['Data'] = df_ano_completo.index
    df_ano_completo['data_str'] = df_ano_completo['Data'].dt.strftime('%d/%m/%Y')
    df_ano_completo['dia_semana'] = df_ano_completo['Data'].dt.dayofweek

    primeiro_dia = datetime(ano, 1, 1).date()
    primeiro_dia_semana = primeiro_dia.weekday()

    x_positions, y_positions, valores, hover_texts = [], [], [], []

    for _, row in df_ano_completo.iterrows():
        dias_desde_inicio = (row['Data'].date() - primeiro_dia).days
        semana = (dias_desde_inicio + primeiro_dia_semana) // 7
        dia_semana = (dias_desde_inicio + primeiro_dia_semana) % 7

        x_positions.append(semana)
        y_positions.append(dia_semana)

        total_vendas = row['Total_Vendas']
        if total_vendas == 0: categoria = 0
        elif total_vendas < 1500: categoria = 1
        elif total_vendas < 2500: categoria = 2
        elif total_vendas < 3000: categoria = 3
        else: categoria = 4
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
        z=matriz_vendas, text=matriz_hover, hovertemplate='%{text}<extra></extra>',
        colorscale=escala_4_tons, showscale=False, zmin=0, zmax=4,
        xgap=3, ygap=3, hoverongaps=False
    ))

    meses_posicoes = []
    meses_nomes_plotly = []
    for mes in range(1, 13):
        primeiro_dia_mes = datetime(ano, mes, 1).date()
        dias_desde_inicio = (primeiro_dia_mes - primeiro_dia).days
        semana_mes = (dias_desde_inicio + primeiro_dia_semana) // 7
        meses_posicoes.append(semana_mes)
        meses_nomes_plotly.append(calendar.month_abbr[mes].replace('.', ''))

    fig.update_layout(
        title=f"Heatmap Anual de Vendas - {ano}",
        height=500,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
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
            ticklen=0, ticklabelstandoff=10
        ),
        title_x=0.5, title_font=dict(size=18, color=COR_TEXTO_PRINCIPAL),
        margin=dict(l=50, r=20, t=80, b=20)
    )
    return fig

def criar_heatmap_vendas_mensais(df, ano):
    """Cria heatmap mensal horizontal Plotly com dados do DataFrame e altura fixa."""
    empty_fig = go.Figure().update_layout(height=250, title=f"Sem dados para o heatmap mensal de {ano}", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        return empty_fig

    df_ano = df[df['Data'].dt.year == ano].copy()
    if df_ano.empty:
        return empty_fig

    df_ano['Mes'] = df_ano['Data'].dt.month
    vendas_mensais = df_ano.groupby('Mes').agg({
        'Total': 'sum', 'Cartão': 'sum', 'Dinheiro': 'sum', 'Pix': 'sum'
    }).reindex(range(1, 13), fill_value=0).reset_index()

    meses_nomes_plotly = [calendar.month_abbr[m].replace('.', '') for m in range(1, 13)]
    vendas_mensais['Mes_Nome'] = vendas_mensais['Mes'].map(lambda x: meses_nomes_plotly[x-1])

    matriz_mensal = np.zeros((1, 12))
    matriz_hover_mensal = np.full((1, 12), '', dtype=object)

    max_venda_mensal = vendas_mensais['Total'].max()
    if max_venda_mensal > 0:
        bins = [0, max_venda_mensal * 0.25, max_venda_mensal * 0.5, max_venda_mensal * 0.75, max_venda_mensal + 1]
        labels = [1, 2, 3, 4]
        vendas_mensais['Categoria'] = pd.cut(vendas_mensais['Total'], bins=bins, labels=labels, right=False, include_lowest=True).fillna(0).astype(int)
    else:
        vendas_mensais['Categoria'] = 0 # Se não houver vendas, categoria é 0

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
        z=matriz_mensal, text=matriz_hover_mensal, hovertemplate='%{text}<extra></extra>',
        colorscale=escala_4_tons, showscale=False, zmin=0, zmax=4,
        xgap=5, ygap=5, hoverongaps=False
    ))

    fig.update_layout(
        title=f'Heatmap Mensal de Vendas - {ano}',
        height=250,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
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
        title_x=0.5, title_font=dict(size=18, color=COR_TEXTO_PRINCIPAL),
        margin=dict(l=50, r=20, t=50, b=30)
    )
    return fig

# --- Função Principal da Aplicação ---
def main():
    # --- Header --- #
    # Usar colunas para centralizar melhor o logo e título
    _, mid_col, _ = st.columns([1,3,1])
    with mid_col:
        st.markdown("""
        <div class="header-container">
            <div class="logo-container">
                <img src="https://raw.githubusercontent.com/lucasricardocs/clipsburger/main/logo.png" class="logo-image">
                <div>
                    <h1>Clips Burger</h1>
                    <p>Sistema Financeiro</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    # st.markdown("<hr style='margin-top: 0;'>", unsafe_allow_html=True) # Remover a linha abaixo do header

    # --- Leitura e Processamento Inicial dos Dados --- #
    df_raw = read_sales_data()
    # Não interromper se vazio, permitir cadastro
    # if df_raw is None or df_raw.empty:
    #     st.warning("Não foi possível carregar os dados de vendas. Verifique a conexão ou a planilha.")
    #     # st.stop() # Não parar aqui

    df_processed = process_data(df_raw)
    # A verificação se df_processed está vazio será feita dentro das tabs

    # --- Inicialização do Estado da Sessão --- #
    if 'registro_sucesso' not in st.session_state:
        st.session_state.registro_sucesso = False
    if 'last_registered_date' not in st.session_state:
        st.session_state.last_registered_date = None

    # --- Definição das Tabs --- #
    tab_cadastro, tab_dashboard, tab_analise_contabil = st.tabs([
        "📝 Cadastro",
        "📊 Dashboard",
        "🧾 Análise Contábil"
    ])

    # --- Tab: Cadastro --- #
    with tab_cadastro:
        st.header("Registro de Vendas Diárias")
        worksheet = get_worksheet()

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
                        # Mensagem será exibida fora do form
                    else:
                        st.error("Falha ao registrar a venda.")
                        st.session_state.registro_sucesso = False
                else:
                    st.error("Erro de conexão com a planilha. Não foi possível registrar.")
                    st.session_state.registro_sucesso = False

        if st.session_state.get('registro_sucesso', False):
            st.success("✅ Registro adicionado com sucesso!")
            st.divider()
            st.subheader("Últimos Registros")

            # Recarrega e processa os dados APÓS o registro bem-sucedido
            df_raw_updated = read_sales_data()
            df_processed_updated = process_data(df_raw_updated)

            if not df_processed_updated.empty:
                # Mostra os últimos 5 registros para simplicidade
                df_display = df_processed_updated.tail(5)[["DataFormatada", "Cartão", "Dinheiro", "Pix", "Total"]].rename(columns={"DataFormatada": "Data"})
                st.dataframe(df_display, use_container_width=True)
            else:
                st.info("Ainda não há registros para exibir.")
            
            # Resetar estado para não mostrar sempre (opcional, pode manter visível)
            # st.session_state.registro_sucesso = False 

    # --- Tab: Dashboard --- #
    with tab_dashboard:
        st.header("Visão Geral do Desempenho")

        if df_processed.empty:
            st.warning("Não há dados registrados para gerar o dashboard. Registre vendas na aba 'Cadastro'.")
        else:
            # --- Filtro de Ano --- #
            available_years = sorted(df_processed['Ano'].unique(), reverse=True)
            # Garantir que anos sejam inteiros
            available_years = [int(y) for y in available_years if pd.notna(y)]
            if not available_years:
                 st.warning("Não foi possível determinar os anos disponíveis nos dados.")
                 selected_year = datetime.now().year # Fallback
            else:
                selected_year = st.selectbox("Selecione o Ano para Análise Detalhada", options=available_years, index=0)
            
            df_year_filtered = df_processed[df_processed['Ano'] == selected_year].copy()
            df_filtered = df_processed # Para métricas gerais (todo período)

            # --- Resumo Financeiro (Todo Período) --- #
            st.subheader("Resumo Financeiro (Geral)")
            if not df_filtered.empty:
                total_revenue = df_filtered["Total"].sum()
                # Calcular média apenas sobre dias com vendas > 0
                daily_sales = df_filtered.groupby(df_filtered['Data'].dt.date)["Total"].sum()
                avg_daily_sales = daily_sales[daily_sales > 0].mean()
                max_daily_sale = daily_sales.max()
                min_daily_sale_positive = daily_sales[daily_sales > 0].min()
            else:
                total_revenue, avg_daily_sales, max_daily_sale, min_daily_sale_positive = 0, 0, 0, 0

            col_res1, col_res2, col_res3, col_res4 = st.columns(4)
            with col_res1:
                st.metric(label="💰 Faturamento Total", value=format_brl(total_revenue))
            with col_res2:
                st.metric(label="📅 Média Diária (Dias c/ Venda)", value=format_brl(avg_daily_sales))
            with col_res3:
                st.metric(label="📈 Maior Venda Diária", value=format_brl(max_daily_sale))
            with col_res4:
                st.metric(label="📉 Menor Venda Diária (>0)", value=format_brl(min_daily_sale_positive))

            # --- Heatmaps (Ano Selecionado) --- #
            st.divider()
            st.subheader(f"Calendário de Atividade ({selected_year})")
            # Passar df_processed (todos os dados) para os heatmaps poderem filtrar o ano
            heatmap_anual = criar_calendario_anual_heatmap(df_processed, selected_year)
            st.plotly_chart(heatmap_anual, use_container_width=True)
            
            heatmap_mensal = criar_heatmap_vendas_mensais(df_processed, selected_year)
            st.plotly_chart(heatmap_mensal, use_container_width=True)

            # --- Assiduidade (Todo Período) --- #
            st.divider()
            st.subheader("Assiduidade (Geral)")
            if not df_filtered.empty:
                total_days_period = (df_filtered["Data"].max() - df_filtered["Data"].min()).days + 1
                days_worked = df_filtered["Data"].nunique()
                work_frequency_perc = (days_worked / total_days_period) * 100 if total_days_period > 0 else 0
            else:
                total_days_period, days_worked, work_frequency_perc = 0, 0, 0

            col_assid1, col_assid2, col_assid3 = st.columns(3)
            with col_assid1:
                st.metric(label="🗓️ Dias Trabalhados", value=f"{days_worked} dias")
            with col_assid2:
                st.metric(label="⏳ Período Analisado", value=f"{total_days_period} dias")
            with col_assid3:
                st.metric(label="⏱️ Frequência", value=f"{work_frequency_perc:.1f}%")

            # --- Métodos de Pagamento (Ano Selecionado) --- #
            st.divider()
            st.subheader(f"Métodos de Pagamento ({selected_year})")
            if not df_year_filtered.empty:
                total_cartao = df_year_filtered["Cartão"].sum()
                total_dinheiro = df_year_filtered["Dinheiro"].sum()
                total_pix = df_year_filtered["Pix"].sum()
            else:
                total_cartao, total_dinheiro, total_pix = 0, 0, 0

            col_pay1, col_pay2, col_pay3 = st.columns(3)
            with col_pay1:
                st.metric(label="💳 Cartão", value=format_brl(total_cartao))
            with col_pay2:
                st.metric(label="💵 Dinheiro", value=format_brl(total_dinheiro))
            with col_pay3:
                st.metric(label="📱 PIX", value=format_brl(total_pix))

            # --- Gráficos Principais (Ano Selecionado) --- #
            st.divider()
            st.subheader(f"Análise de Vendas ({selected_year})")
            col_chart1, col_chart2 = st.columns([2, 1])
            with col_chart1:
                st.write("**Vendas Diárias e Média Móvel**")
                daily_sales_chart = create_advanced_daily_sales_chart(df_year_filtered)
                st.altair_chart(daily_sales_chart, use_container_width=True)
            with col_chart2:
                st.write("**Distribuição por Pagamento**")
                radial_chart = create_radial_plot(df_year_filtered)
                st.altair_chart(radial_chart, use_container_width=True)

            st.write("**Média de Vendas por Dia da Semana**")
            weekday_sales_chart = create_weekday_sales_chart(df_year_filtered)
            st.altair_chart(weekday_sales_chart, use_container_width=True)

            # --- Ranking e Análise de Frequência (Ano Selecionado) --- #
            st.divider()
            col_rank, col_freq_analysis = st.columns(2)
            
            # Inicializar DataFrames vazios para evitar erros se df_year_filtered for vazio
            weekday_avg_rank_display = pd.DataFrame(columns=['DiaSemana', 'Média (R$)'])
            work_freq_weekday_display = pd.DataFrame(columns=['DiaSemana', 'Dias Trabalhados'])
            weekday_avg_rank = pd.DataFrame() # Para usar nos insights

            if not df_year_filtered.empty:
                # Calcular Ranking
                weekday_avg_rank = df_year_filtered.groupby("DiaSemana", observed=False)["Total"].mean().reset_index()
                if not weekday_avg_rank.empty:
                    weekday_avg_rank = weekday_avg_rank.dropna().sort_values(by="Total", ascending=False)
                    weekday_avg_rank_display = weekday_avg_rank.copy()
                    weekday_avg_rank_display["Média (R$)"] = weekday_avg_rank_display["Total"].apply(format_brl)
                    weekday_avg_rank_display = weekday_avg_rank_display[['DiaSemana', 'Média (R$)']].reset_index(drop=True)
                
                # Calcular Frequência
                if 'DiaSemana' in df_year_filtered.columns:
                    work_freq_weekday = df_year_filtered['DiaSemana'].value_counts(sort=False).reset_index()
                    if not work_freq_weekday.empty:
                        work_freq_weekday.columns = ['DiaSemana', 'Dias Trabalhados']
                        work_freq_weekday['DiaSemana'] = pd.Categorical(work_freq_weekday['DiaSemana'], categories=dias_semana_ordem, ordered=True)
                        work_freq_weekday_display = work_freq_weekday.set_index('DiaSemana').reindex(dias_semana_ordem, fill_value=0).reset_index()
            
            with col_rank:
                st.subheader(f"🏆 Ranking - Dias da Semana ({selected_year})")
                st.dataframe(weekday_avg_rank_display, use_container_width=True, hide_index=True)
            
            with col_freq_analysis:
                st.subheader(f"⏱️ Análise de Frequência ({selected_year})")
                st.dataframe(work_freq_weekday_display, use_container_width=True, hide_index=True)

            # --- Insights (Baseado no Ano Selecionado e Geral) --- #
            st.divider()
            st.subheader("💡 Insights e Recomendações")
            
            # Insight 1: Custo vs Conveniência (Cartão - Ano Selecionado)
            total_revenue_year = total_cartao + total_dinheiro + total_pix
            perc_cartao_year = (total_cartao / total_revenue_year) * 100 if total_revenue_year > 0 else 0
            st.markdown(f"""
            <div class="insight-container">
                <h4>💳 Análise de Pagamentos com Cartão ({selected_year})</h4>
                <p>
                As vendas via cartão representaram <strong>{perc_cartao_year:.1f}%</strong> do faturamento em {selected_year} ({format_brl(total_cartao)}).
                Embora conveniente para o cliente, é crucial analisar as taxas associadas (crédito, débito, antecipação).
                Avalie o impacto líquido dessas taxas na lucratividade. Considere estratégias para incentivar sutilmente métodos mais vantajosos como PIX ou dinheiro, como pequenos descontos ou programas de fidelidade associados a esses métodos.
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Insight 2: Dias de Maior e Menor Movimento (Ano Selecionado)
            # CORREÇÃO: Verificar se weekday_avg_rank não está vazio antes de acessar iloc
            if not weekday_avg_rank.empty:
                best_day = weekday_avg_rank.iloc[0]['DiaSemana']
                worst_day = weekday_avg_rank.iloc[-1]['DiaSemana']
                avg_best = weekday_avg_rank.iloc[0]['Total']
                avg_worst = weekday_avg_rank.iloc[-1]['Total']
                st.markdown(f"""
                <div class="insight-container">
                    <h4>📅 Desempenho Semanal ({selected_year})</h4>
                    <p>
                    Seu dia de maior movimento em média em {selected_year} foi <strong>{best_day}</strong> (média de {format_brl(avg_best)}), enquanto <strong>{worst_day}</strong> apresentou a menor média ({format_brl(avg_worst)}).
                    Analise os fatores que contribuem para o sucesso de {best_day} e veja se podem ser replicados.
                    Para {worst_day}, considere ações específicas como promoções direcionadas ou ajuste de custos.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                 st.markdown(f"""
                <div class="insight-container">
                    <h4>📅 Desempenho Semanal ({selected_year})</h4>
                    <p>Não há dados suficientes para analisar o desempenho médio por dia da semana em {selected_year}.</p>
                </div>
                """, unsafe_allow_html=True)

            # Insight 3: Frequência de Trabalho (Geral)
            st.markdown(f"""
            <div class="insight-container">
                <h4>⏱️ Consistência Operacional (Geral)</h4>
                <p>
                A frequência geral de trabalho registrada foi de <strong>{work_frequency_perc:.1f}%</strong> ({days_worked} de {total_days_period} dias).
                Uma alta frequência sugere consistência, mas analise se os dias não trabalhados foram planejados ou imprevistos.
                Dias parados inesperadamente representam perda de receita potencial.
                </p>
            </div>
            """, unsafe_allow_html=True)

    # --- Tab: Análise Contábil --- #
    with tab_analise_contabil:
        st.header("Análise Contábil Simplificada")

        if df_processed.empty:
            st.warning("Não há dados registrados para gerar a análise contábil.")
        else:
            today = datetime.now().date()
            first_day_current_month = today.replace(day=1)
            last_day_last_month = first_day_current_month - timedelta(days=1)
            first_day_last_month = last_day_last_month.replace(day=1)

            # Datas padrão: último mês completo
            start_date_default = first_day_last_month
            end_date_default = last_day_last_month
            
            # Datas mín e máx dos dados
            min_data = df_processed['Data'].min().date()
            max_data = df_processed['Data'].max().date()

            col_dre_filter1, col_dre_filter2 = st.columns(2)
            with col_dre_filter1:
                start_date_dre = st.date_input("Data Inicial DRE", start_date_default, min_value=min_data, max_value=max_data)
            with col_dre_filter2:
                end_date_dre = st.date_input("Data Final DRE", end_date_default, min_value=min_data, max_value=max_data)

            if start_date_dre > end_date_dre:
                st.error("Data inicial não pode ser maior que a data final.")
            else:
                mask_dre = (df_processed['Data'].dt.date >= start_date_dre) & (df_processed['Data'].dt.date <= end_date_dre)
                df_dre_filtered = df_processed.loc[mask_dre]

                if df_dre_filtered.empty:
                    st.info(f"Sem dados de vendas entre {start_date_dre.strftime('%d/%m/%Y')} e {end_date_dre.strftime('%d/%m/%Y')}.")
                else:
                    st.subheader("Demonstrativo de Resultado (DRE) - Simplificado")

                    receita_bruta = df_dre_filtered['Total'].sum()
                    perc_custo_mercadoria = 0.35
                    perc_impostos_sobre_venda = 0.06
                    custos_operacionais_fixos = 1500 # Estimativa mensal - ajustar se período for diferente
                    taxas_cartao_estimada = df_dre_filtered['Cartão'].sum() * 0.035

                    custo_mercadoria_vendida = receita_bruta * perc_custo_mercadoria
                    impostos_sobre_venda = receita_bruta * perc_impostos_sobre_venda
                    receita_liquida = receita_bruta - impostos_sobre_venda
                    lucro_bruto = receita_liquida - custo_mercadoria_vendida
                    despesas_operacionais = custos_operacionais_fixos + taxas_cartao_estimada
                    lucro_operacional = lucro_bruto - despesas_operacionais

                    dre_data = {
                        "Descrição": [
                            "(+) Receita Bruta de Vendas",
                            "(-) Impostos sobre Vendas (Estimado)",
                            "(=) Receita Líquida",
                            "(-) Custo da Mercadoria Vendida (CMV Estimado)",
                            "(=) Lucro Bruto",
                            "(-) Despesas Operacionais Estimadas",
                            "   - Custos Fixos",
                            "   - Taxas de Cartão",
                            "(=) Lucro Operacional (Estimado)"
                        ],
                        "Valor (R$)": [
                            format_brl(receita_bruta),
                            f"({format_brl(impostos_sobre_venda)})",
                            format_brl(receita_liquida),
                            f"({format_brl(custo_mercadoria_vendida)})",
                            format_brl(lucro_bruto),
                            "",
                            f"({format_brl(custos_operacionais_fixos)})",
                            f"({format_brl(taxas_cartao_estimada)})",
                            format_brl(lucro_operacional)
                        ]
                    }
                    
                    html_dre = "<div class='dre-table'><table><thead><tr><th>Descrição</th><th>Em R$</th></tr></thead><tbody>"
                    for i, desc in enumerate(dre_data["Descrição"]):
                        valor = dre_data["Valor (R$) "][i]
                        style = "font-weight: bold;" if "(=)" in desc else ""
                        padding_left = "padding-left: 20px;" if desc.strip().startswith("-") or desc.strip().startswith(" ") else ""
                        html_dre += f"<tr><td style='{style}{padding_left}'>{desc}</td><td style='{style}'>{valor}</td></tr>"
                    html_dre += "</tbody></table></div>"

                    st.markdown(html_dre, unsafe_allow_html=True)
                    st.caption("Valores de custos, impostos e taxas são *estimativas* para demonstração.")

                    st.divider()
                    st.subheader("Evolução do Faturamento Acumulado (Todo Período)")
                    cumulative_chart = create_cumulative_evolution_chart(df_processed)
                    st.altair_chart(cumulative_chart, use_container_width=True)

    # --- Rodapé Criativo --- #
    st.markdown("--- ")
    year = datetime.now().year
    st.markdown(f"""
    <div class="footer">
        🍔 Clips Burger &copy; {year} | Feito com <a href="https://streamlit.io" target="_blank">Streamlit</a> & muito sabor! ✨
        <br>
        Análises geradas por Manus AI
    </div>
    """, unsafe_allow_html=True)

# --- Execução Principal --- #
if __name__ == "__main__":
    main()
