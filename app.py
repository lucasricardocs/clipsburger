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

    /* Keyframes para a aura pulsante celestial (azul, roxo e branco) */
    @keyframes celestialPulse {{
        0%, 100% {{
            filter: drop-shadow(0 0 15px rgba(100, 149, 237, 0.8)) drop-shadow(0 0 30px rgba(100, 149, 237, 0.6)); /* Azul celestial */
        }}
        33% {{
            filter: drop-shadow(0 0 15px rgba(147, 112, 219, 0.8)) drop-shadow(0 0 30px rgba(147, 112, 219, 0.6)); /* Roxo azulado */
        }}
        66% {{
            filter: drop-shadow(0 0 15px rgba(255, 255, 255, 0.9)) drop-shadow(0 0 30px rgba(255, 255, 255, 0.7)); /* Branco */
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
    }}
    .dre-table td:nth-child(2) {{ 
        text-align: right;
        font-family: 'Courier New', Courier, monospace;
        white-space: pre;
    }}
    .dre-table th:nth-child(2) {{ 
        text-align: right;
        padding-right: 12px;
    }}

    /* --- Responsividade --- */
    @media (max-width: 992px) {{ 
        .logo-image {{ width: 180px; }} /* Ajustar logo em tablet */
        .logo-container h1 {{ font-size: 2rem; }}
        .stMetric {{ padding: 1rem; min-height: 100px; }}
        .insight-container {{ padding: 1.2rem; min-height: 140px; }}
        .st-emotion-cache-1l269bu > div {{ 
             flex-direction: column;
        }}
    }}

    @media (max-width: 768px) {{ 
        .logo-image {{ width: 150px; }} /* Ajustar logo em mobile */
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
        .dre-table td, .dre-table th {{ padding: 6px 8px; font-size: 13px; }}
    }}

    @media (max-width: 480px) {{ 
        .logo-image {{ width: 120px; }} /* Ajustar logo em mobile pequeno */
        .logo-container h1 {{ font-size: 1.4rem; }}
        .stMetric > div > div {{ font-size: 1.3rem !important; }}
        .stMetric label {{ font-size: 0.85rem !important; }}
        .stButton > button {{ font-size: 1rem; height: 2.8rem; }}
    }}
    </style>
    """, unsafe_allow_html=True)

inject_css()

# --- Funções de Cache para Acesso ao Google Sheets (SEM ALTERAÇÕES) ---
@st.cache_resource
def get_google_auth():
    """Autoriza o acesso ao Google Sheets e retorna o cliente gspread."""
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/spreadsheets.readonly",
              "https://www.googleapis.com/auth/drive.readonly"]
    try:
        if "google_credentials" not in st.secrets:
            st.error("Credenciais do Google (\'google_credentials\') não encontradas em st.secrets. Configure o arquivo .streamlit/secrets.toml")
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

# --- Funções de Manipulação de Dados (AJUSTADAS) ---
@st.cache_data(ttl=600) # Aumentar TTL para reduzir recargas
def read_sales_data():
    """Lê todos os registros da planilha de vendas e retorna como DataFrame."""
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records()
            if not rows:
                st.info("A planilha de vendas está vazia.")
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
                 st.warning("Coluna \'Data\' não encontrada na planilha. Criando coluna vazia.")
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

            return df
        except Exception as e:
            st.error(f"Erro ao ler dados da planilha: {e}")
            return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix"])
    return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix"])

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
        st.warning("DataFrame de entrada vazio ou sem coluna \'Data\' para processamento.")
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
    df["DiaSemana"] = pd.Categorical(df["DiaSemana"], categories=dias_semana_ordem, ordered=True)
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

# Gráfico Radial (Substitui Pizza)
def create_radial_plot(df):
    """Cria um gráfico radial de métodos de pagamento."""
    if df.empty or not any(col in df.columns for col in ["Cartão", "Dinheiro", "Pix"]):
        return None

    payment_data = pd.DataFrame({
        "Método": ["Cartão", "Dinheiro", "PIX"],
        "Valor": [df["Cartão"].sum(), df["Dinheiro"].sum(), df["Pix"].sum()]
    })
    payment_data = payment_data[payment_data["Valor"] > 0]

    if payment_data.empty:
        return None

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

# Gráfico de Vendas Diárias (Barras Arredondadas + Linha Média)
def create_advanced_daily_sales_chart(df):
    """Cria gráfico de barras arredondadas de vendas diárias com linha de média móvel."""
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        return None
    df_chart = df.copy()
    df_chart.dropna(subset=["Data", "Total"], inplace=True)
    if df_chart.empty:
        return None

    # Agrupar por dia caso haja múltiplas entradas
    df_daily = df_chart.groupby(pd.Grouper(key="Data", freq="D"))["Total"].sum().reset_index()
    df_daily = df_daily[df_daily["Total"] > 0] # Mostrar apenas dias com vendas

    if df_daily.empty:
        return None

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
    ).configure_view(
        strokeOpacity=0 # Remove borda
    ).interactive() # Habilita zoom e pan

    return chart

# Gráfico de Média de Vendas por Dia da Semana
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
    ).configure_view(
        strokeOpacity=0 # Remove borda
    )
    return chart

# Gráfico de Evolução Patrimonial Acumulado (ATUALIZADO)
def create_cumulative_evolution_chart(df):
    """Cria gráfico de área da evolução acumulada de vendas com destaque no último valor."""
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        return None

    df_sorted = df.sort_values("Data").copy()
    df_sorted.dropna(subset=["Data", "Total"], inplace=True)
    if df_sorted.empty:
        return None

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
        ).configure_view(
            strokeOpacity=0 # Remove borda
        ).interactive()
    else:
        chart = area.properties(
            height=500 # Altura fixa
        ).configure_view(
            strokeOpacity=0 # Remove borda
        ).interactive()

    return chart

# Função para criar o Heatmap de Calendário (CORRIGIDA)
def create_calendar_heatmap(df, year):
    """Cria um heatmap de calendário de vendas para um ano específico usando Plotly.
       Utiliza os dados do DataFrame processado e o estilo do exemplo.
    """
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        st.warning(f"Dados insuficientes para gerar o heatmap de calendário para {year}.")
        return None, None

    df_year = df[df["Data"].dt.year == year].copy()
    if df_year.empty:
        st.info(f"Sem dados de vendas para o ano {year}.")
        return None, None

    # Agrupar por data (caso haja múltiplas entradas no mesmo dia)
    daily_sales = df_year.groupby(df_year["Data"].dt.date)["Total"].sum()

    # Criar range completo de datas para o ano
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)
    all_dates = pd.date_range(start_date, end_date, freq="D")

    # Reindexar para incluir todos os dias, preenchendo dias sem vendas com 0
    daily_sales = daily_sales.reindex(all_dates.date, fill_value=0)

    # Preparar dados para Plotly Heatmap (similar ao exemplo)
    dates_list = daily_sales.index
    values = daily_sales.values

    # Mapear valores para categorias de cor (0 a 4)
    def map_value_to_category(value):
        if value <= 0:
            return 0 # Sem vendas
        elif value < 1500:
            return 1 # Faixa 1
        elif value < 2500:
            return 2 # Faixa 2
        elif value < 3000:
            return 3 # Faixa 3
        else:
            return 4 # Faixa 4

    color_categories = [map_value_to_category(v) for v in values]

    # Calcular posições x (semana do ano) e y (dia da semana)
    weekdays = [d.weekday() for d in dates_list] # 0=Segunda ... 6=Domingo
    weeknumbers = [d.isocalendar().week for d in dates_list]

    # Ajuste para semanas que começam no ano anterior ou terminam no próximo
    first_day_weekday = start_date.weekday()
    x_positions = [(d.toordinal() - start_date.toordinal() + first_day_weekday) // 7 for d in dates_list]
    y_positions = weekdays

    # Criar texto do hover (MAIOR)
    hover_texts = []
    df_details = df_year.groupby(df_year["Data"].dt.date).agg(
        Cartao=("Cartão", "sum"),
        Dinheiro=("Dinheiro", "sum"),
        Pix=("Pix", "sum"),
        Total=("Total", "sum")
    ).reindex(all_dates.date, fill_value=0)

    for date, cat, total, cartao, dinheiro, pix in zip(dates_list, color_categories, values, df_details["Cartao"], df_details["Dinheiro"], df_details["Pix"]):
        date_str = date.strftime("%d/%m/%Y")
        if total > 0:
            hover_text = (
                f"<b>📅 {date_str}</b><br><br>"  # Texto maior e mais espaçado
                f"<b>💰 Total:</b> {format_brl(total)}<br>"
                f"<b>💳 Cartão:</b> {format_brl(cartao)}<br>"
                f"<b>💵 Dinheiro:</b> {format_brl(dinheiro)}<br>"
                f"<b>📱 Pix:</b> {format_brl(pix)}"
            )
        else:
            hover_text = f"<b>📅 {date_str}</b><br><br>❌ Sem vendas"
        hover_texts.append(hover_text)

    # Escala de cores (do exemplo)
    colorscale = [
        [0.0, "#161b22"],      # 0: Sem vendas (cor de fundo)
        [0.001, "#39D353"],    # 1: Verde mais claro
        [0.25, "#39D353"],
        [0.251, "#37AB4B"],    # 2: Verde claro
        [0.5, "#37AB4B"],
        [0.501, "#006D31"],    # 3: Verde médio
        [0.75, "#006D31"],
        [0.751, "#0D4428"],    # 4: Verde escuro
        [1.0, "#0D4428"]
    ]

    # Criar a figura Plotly para o calendário anual
    fig_anual = go.Figure(data=go.Heatmap(
        x=x_positions,
        y=y_positions,
        z=color_categories,
        text=hover_texts,
        hovertemplate="%{text}<extra></extra>",
        colorscale=colorscale,
        showscale=False, # Sem barra de cor
        xgap=3,
        ygap=3,
        hoverongaps=False,
        zmin=0,
        zmax=4
    ))

    # Nomes dos meses e suas posições aproximadas em semanas
    month_names = [calendar.month_abbr[i] for i in range(1, 13)]
    month_positions = []
    for month in range(1, 13):
        first_day_of_month = datetime(year, month, 1)
        week_num = (first_day_of_month.toordinal() - start_date.toordinal() + first_day_weekday) // 7
        month_positions.append(week_num)

    # Layout (adaptado do exemplo, com ajustes para modo escuro)
    fig_anual.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COR_TEXTO_PRINCIPAL, family="Arial, sans-serif", size=14), # Fonte maior
        xaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            tickmode="array",
            tickvals=month_positions,
            ticktext=month_names,
            tickfont=dict(color=COR_TEXTO_SECUNDARIO, size=14),
            side="top",
            tickangle=0,
            showline=False,
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            tickmode="array",
            tickvals=[0, 1, 2, 3, 4, 5, 6],
            ticktext=["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"],
            tickfont=dict(color=COR_TEXTO_SECUNDARIO, size=14),
            autorange="reversed", # Domingo no topo se y=6 for domingo
            showline=False,
            ticklen=0,
            ticklabelposition="outside right", # Coloca dias da semana à direita
            ticklabelstandoff=10 # Afasta os labels
        ),
        height=350, # Altura menor para calendário
        margin=dict(l=20, r=80, t=50, b=20) # Ajustar margens
    )
    
    # Criar heatmap mensal (CORRIGIDO)
    # Agrupar dados por mês
    monthly_data = df_year.groupby(df_year["Data"].dt.month)["Total"].sum()
    monthly_data = monthly_data.reindex(range(1, 13), fill_value=0)
    
    # Criar figura para o heatmap mensal
    fig_mensal = go.Figure()
    
    # Adicionar barras para cada mês
    for i, (mes, valor) in enumerate(monthly_data.items()):
        # Determinar cor baseada no valor (verde mais escuro para valores maiores)
        if valor == 0:
            cor = "#161b22"  # Sem vendas
        elif valor < 5000:
            cor = "#39D353"  # Verde mais claro
        elif valor < 10000:
            cor = "#37AB4B"  # Verde claro
        elif valor < 15000:
            cor = "#006D31"  # Verde médio
        else:
            cor = "#0D4428"  # Verde escuro
            
        # Texto do hover
        hover_text = f"<b>{calendar.month_name[mes]} {year}</b><br><br><b>Total:</b> {format_brl(valor)}"
        
        # Adicionar barra
        fig_mensal.add_trace(go.Bar(
            x=[mes],
            y=[valor],
            marker_color=cor,
            width=0.8,
            hovertemplate=hover_text + "<extra></extra>",
            name=calendar.month_name[mes]
        ))
    
    # Configurar layout do gráfico mensal (SIMPLIFICADO para evitar erros)
    try:
        fig_mensal.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=250,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False
        )
        
        # Configurar eixos separadamente para evitar erros
        fig_mensal.update_xaxes(
            title="",
            tickmode="array",
            tickvals=list(range(1, 13)),
            ticktext=[calendar.month_abbr[i] for i in range(1, 13)],
            tickfont=dict(color=COR_TEXTO_SECUNDARIO, size=14),
            showgrid=False,
            zeroline=False,
            showline=False
        )
        
        fig_mensal.update_yaxes(
            title="Vendas Mensais (R$)",
            titlefont=dict(color=COR_TEXTO_PRINCIPAL, size=14),
            tickfont=dict(color=COR_TEXTO_SECUNDARIO, size=14),
            showgrid=False,
            zeroline=False,
            showline=False
        )
    except Exception as e:
        st.warning(f"Aviso: Configuração simplificada do gráfico mensal devido a erro: {e}")
        # Configuração mínima em caso de erro
        fig_mensal.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=250
        )

    return fig_anual, fig_mensal

# --- Funções de Análise e Exibição (MOVIMENTADAS E AJUSTADAS) ---

def display_resumo_financeiro(df):
    """Exibe os cards de resumo financeiro."""
    if df.empty:
        st.info("Não há dados suficientes para o resumo financeiro.")
        return

    total_faturamento = df["Total"].sum()
    media_diaria = df["Total"].mean() if not df.empty else 0
    maior_venda = df["Total"].max() if not df.empty else 0
    menor_venda = df[df["Total"] > 0]["Total"].min() if not df[df["Total"] > 0].empty else 0 # Menor venda > 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Faturamento Total", format_brl(total_faturamento))
    with col2:
        st.metric("📊 Média por Dia", format_brl(media_diaria))
    with col3:
        st.metric("🚀 Maior Venda Diária", format_brl(maior_venda))
    with col4:
        st.metric("📉 Menor Venda Diária", format_brl(menor_venda))

def display_assiduidade(df):
    """Exibe os cards de assiduidade."""
    if df.empty or "Data" not in df.columns:
        st.info("Não há dados suficientes para análise de assiduidade.")
        return

    total_dias_periodo = (df["Data"].max() - df["Data"].min()).days + 1 if not df.empty else 0
    dias_trabalhados = df["Data"].nunique()
    percentual_assiduidade = (dias_trabalhados / total_dias_periodo * 100) if total_dias_periodo > 0 else 0
    # Encontrar a maior sequência de dias trabalhados (mais complexo, simplificado aqui)
    # Simplificação: Média de dias trabalhados por semana
    semanas_no_periodo = total_dias_periodo / 7 if total_dias_periodo > 0 else 0
    media_dias_semana = dias_trabalhados / semanas_no_periodo if semanas_no_periodo > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🗓️ Dias Trabalhados", f"{dias_trabalhados} dias")
    with col2:
        st.metric("💯 Assiduidade", f"{percentual_assiduidade:.1f}%", help=f"Percentual de dias com vendas dentro do período de {total_dias_periodo} dias analisado.")
    with col3:
        st.metric("📅 Média Dias/Semana", f"{media_dias_semana:.1f} dias", help="Média de dias com vendas por semana no período.")

def display_metodos_pagamento(df):
    """Exibe os cards de métodos de pagamento."""
    if df.empty or not any(col in df.columns for col in ["Cartão", "Dinheiro", "Pix"]):
        st.info("Não há dados suficientes para análise de métodos de pagamento.")
        return

    total_cartao = df["Cartão"].sum()
    total_dinheiro = df["Dinheiro"].sum()
    total_pix = df["Pix"].sum()
    total_geral = total_cartao + total_dinheiro + total_pix

    perc_cartao = (total_cartao / total_geral * 100) if total_geral > 0 else 0
    perc_dinheiro = (total_dinheiro / total_geral * 100) if total_geral > 0 else 0
    perc_pix = (total_pix / total_geral * 100) if total_geral > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💳 Cartão", format_brl(total_cartao), f"{perc_cartao:.1f}%")
    with col2:
        st.metric("💵 Dinheiro", format_brl(total_dinheiro), f"{perc_dinheiro:.1f}%")
    with col3:
        st.metric("📱 PIX", format_brl(total_pix), f"{perc_pix:.1f}%")

def display_ranking_dias_semana(df):
    """Exibe o ranking de faturamento médio por dia da semana."""
    if df.empty or "DiaSemana" not in df.columns or "Total" not in df.columns:
        st.info("Não há dados para o ranking de dias da semana.")
        return

    ranking = df.groupby("DiaSemana", observed=False)["Total"].mean().reset_index()
    ranking = ranking.dropna().sort_values(by="Total", ascending=False).reset_index(drop=True)
    ranking["Posição"] = ranking.index + 1
    ranking["Média (R$)"] = ranking["Total"].apply(format_brl)

    st.dataframe(ranking[["Posição", "DiaSemana", "Média (R$)"]],
                   use_container_width=True,
                   hide_index=True,
                   column_config={
                       "Posição": st.column_config.NumberColumn(format="%dº"),
                       "DiaSemana": "Dia da Semana",
                       "Média (R$)": "Faturamento Médio"
                   })

def display_frequencia_trabalho(df):
    """Exibe análise de frequência de trabalho (heatmap simplificado)."""
    if df.empty or "Data" not in df.columns:
        st.info("Não há dados para a análise de frequência.")
        return

    # Cria um DataFrame com todos os dias no período e marca os dias trabalhados
    start_date = df["Data"].min()
    end_date = df["Data"].max()
    all_days = pd.date_range(start=start_date, end=end_date, freq="D")
    df_freq = pd.DataFrame(index=all_days)
    df_freq["Trabalhado"] = 0
    dias_unicos_trabalhados = df["Data"].dt.date.unique()
    
    # Versão corrigida - compatível com todas as versões do pandas
    for data in dias_unicos_trabalhados:
        mask = df_freq.index.date == data
        df_freq.loc[mask, "Trabalhado"] = 1

    # Preparar dados para um gráfico simples (ex: barras mensais de dias trabalhados)
    df_freq["AnoMês"] = df_freq.index.strftime("%Y-%m")
    dias_trabalhados_mes = df_freq.groupby("AnoMês")["Trabalhado"].sum().reset_index()

    chart = alt.Chart(dias_trabalhados_mes).mark_bar(
        cornerRadius=8, # Bordas arredondadas
        size=20 # Barras mais grossas
    ).encode(
        x=alt.X("AnoMês", title="Mês", axis=alt.Axis(
            labelAngle=-45, 
            labelColor=COR_TEXTO_SECUNDARIO, 
            titleColor=COR_TEXTO_PRINCIPAL,
            grid=False
        )),
        y=alt.Y("Trabalhado", title="Dias Trabalhados", axis=alt.Axis(
            labelColor=COR_TEXTO_SECUNDARIO, 
            titleColor=COR_TEXTO_PRINCIPAL,
            grid=False
        )),
        color=alt.value(CORES_MODO_ESCURO[2]), # Cor laranja
        tooltip=[
            alt.Tooltip("AnoMês", title="Mês"),
            alt.Tooltip("Trabalhado", title="Dias Trabalhados")
        ]
    ).properties(
        height=300 # Altura menor para este gráfico
    ).configure_view(
        strokeOpacity=0 # Remove borda
    )
    st.altair_chart(chart, use_container_width=True)

def display_insights(df):
    """Exibe insights automáticos com estilo melhorado."""
    if df.empty or len(df) < 2: # Precisa de pelo menos 2 dias para algumas comparações
        st.info("Dados insuficientes para gerar insights automáticos.")
        return

    total_vendas = df["Total"].sum()
    dias_trabalhados = df["Data"].nunique()
    media_diaria = total_vendas / dias_trabalhados if dias_trabalhados > 0 else 0

    # Insight 1: Melhor dia da semana
    media_por_dia = df.groupby("DiaSemana", observed=False)["Total"].mean().reset_index().dropna()
    melhor_dia_semana = media_por_dia.loc[media_por_dia["Total"].idxmax()] if not media_por_dia.empty else None

    # Insight 2: Método de pagamento predominante e sugestão
    metodos_total = {
        "Cartão": df["Cartão"].sum(),
        "Dinheiro": df["Dinheiro"].sum(),
        "PIX": df["Pix"].sum()
    }
    # Remover métodos com valor zero
    metodos_total = {k: v for k, v in metodos_total.items() if v > 0}
    if metodos_total:
        melhor_metodo = max(metodos_total, key=metodos_total.get)
        valor_melhor_metodo = metodos_total[melhor_metodo]
        percentual_melhor = (valor_melhor_metodo / total_vendas * 100) if total_vendas > 0 else 0
        # Sugestão sobre taxas (exemplo profissionalizado)
        sugestao_taxa = """
        <p style="margin-top: 0.5rem; font-size: 0.9rem; color: #b0bec5;">
        <i>Sugestão: Avalie as taxas associadas ao Cartão e compare com a margem de lucro para otimizar a rentabilidade. Incentivar PIX ou Dinheiro pode reduzir custos.</i>
        </p>""" if melhor_metodo == "Cartão" else ""
    else:
        melhor_metodo = None
        percentual_melhor = 0
        sugestao_taxa = ""

    # Insight 3: Comparação com período anterior (ex: última semana vs penúltima)
    df_sorted = df.sort_values("Data")
    if len(df_sorted) >= 14:
        ultima_semana_df = df_sorted.tail(7)
        penultima_semana_df = df_sorted.iloc[-14:-7]
        media_ultima_semana = ultima_semana_df["Total"].mean()
        media_penultima_semana = penultima_semana_df["Total"].mean()
        variacao_semanal = ((media_ultima_semana - media_penultima_semana) / media_penultima_semana * 100) if media_penultima_semana > 0 else 0
        tendencia_texto = "crescimento" if variacao_semanal > 5 else "queda" if variacao_semanal < -5 else "estabilidade"
        tendencia_cor = "#63d2b4" if variacao_semanal > 5 else "#ec7063" if variacao_semanal < -5 else "#f5b041"
    else:
        variacao_semanal = None
        tendencia_texto = "insuficientes"
        tendencia_cor = COR_TEXTO_SECUNDARIO

    # Exibição dos Insights
    col1, col2, col3 = st.columns(3)

    with col1:
        if melhor_dia_semana is not None:
            st.markdown(f"""
            <div class="insight-container" style="border-left-color: {CORES_MODO_ESCURO[0]};">
                <h4 style="color: {CORES_MODO_ESCURO[0]};">🏆 Dia Mais Forte</h4>
                <p>A <strong>{melhor_dia_semana["DiaSemana"]}</strong> apresenta a maior média de faturamento: <strong>{format_brl(melhor_dia_semana["Total"])}</strong>.</p>
                <p style="margin-top: 0.5rem; font-size: 0.9rem; color: #b0bec5;">
                <i>Sugestão: Considere promoções ou reforço de equipe neste dia para maximizar o potencial.</i>
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
             st.markdown("<div class=\"insight-container\"><p><i>Sem dados suficientes para determinar o dia mais forte.</i></p></div>", unsafe_allow_html=True)

    with col2:
        if melhor_metodo is not None:
            st.markdown(f"""
            <div class="insight-container" style="border-left-color: {CORES_MODO_ESCURO[1]};">
                <h4 style="color: {CORES_MODO_ESCURO[1]};">💳 Pagamento Preferido</h4>
                <p>O método <strong>{melhor_metodo}</strong> é o mais utilizado, representando <strong>{percentual_melhor:.1f}%</strong> ({format_brl(valor_melhor_metodo)}) do total faturado.</p>
                {sugestao_taxa}
            </div>
            """, unsafe_allow_html=True)
        else:
             st.markdown("<div class=\"insight-container\"><p><i>Sem dados suficientes para analisar métodos de pagamento.</i></p></div>", unsafe_allow_html=True)

    with col3:
        if variacao_semanal is not None:
            st.markdown(f"""
            <div class="insight-container" style="border-left-color: {tendencia_cor};">
                <h4 style="color: {tendencia_cor};">📈 Tendência Semanal</h4>
                <p>Comparando as duas últimas semanas, houve <strong>{tendencia_texto}</strong> de <strong>{abs(variacao_semanal):.1f}%</strong> na média diária de vendas.</p>
                 <p style="margin-top: 0.5rem; font-size: 0.9rem; color: #b0bec5;">
                <i>Sugestão: Investigue os fatores por trás dessa variação para replicar sucessos ou corrigir rotas.</i>
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="insight-container" style="border-left-color: {tendencia_cor};">
                <h4 style="color: {tendencia_cor};">📈 Tendência Semanal</h4>
                <p>Dados <strong>{tendencia_texto}</strong> para calcular a variação entre as últimas duas semanas.</p>
            </div>
            """, unsafe_allow_html=True)

# --- Função para DRE (AJUSTADA PARA ALINHAMENTO) ---
def generate_dre_html(df):
    """Gera o HTML da DRE com alinhamento corrigido."""
    if df.empty:
        return "<p>Não há dados suficientes para gerar a DRE.</p>"

    # Cálculos da DRE (exemplo simplificado)
    receita_bruta = df["Total"].sum()
    custo_mercadoria = receita_bruta * 0.4 # Exemplo: CMV 40%
    lucro_bruto = receita_bruta - custo_mercadoria
    despesas_operacionais = receita_bruta * 0.2 # Exemplo: Despesas 20%
    lucro_operacional = lucro_bruto - despesas_operacionais
    impostos = lucro_operacional * 0.15 # Exemplo: Impostos 15%
    lucro_liquido = lucro_operacional - impostos

    # Formatação
    f_receita_bruta = format_brl(receita_bruta)
    f_custo_mercadoria = format_brl(custo_mercadoria)
    f_lucro_bruto = format_brl(lucro_bruto)
    f_despesas_operacionais = format_brl(despesas_operacionais)
    f_lucro_operacional = format_brl(lucro_operacional)
    f_impostos = format_brl(impostos)
    f_lucro_liquido = format_brl(lucro_liquido)

    # Estrutura HTML com classe para CSS e alinhamento
    html = f"""
    <div class="dre-table">
        <h3>Demonstração do Resultado do Exercício (DRE) - Simplificada</h3>
        <p>Período Analisado: {df["Data"].min().strftime("%d/%m/%Y")} a {df["Data"].max().strftime("%d/%m/%Y")}</p>
        <table>
            <thead>
                <tr>
                    <th>Descrição</th>
                    <th>Em R$</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>(+) Receita Bruta de Vendas</td><td>{f_receita_bruta}</td></tr>
                <tr><td>(-) Custo da Mercadoria Vendida (CMV)</td><td>({f_custo_mercadoria})</td></tr>
                <tr><td><strong>(=) Lucro Bruto</strong></td><td><strong>{f_lucro_bruto}</strong></td></tr>
                <tr><td>(-) Despesas Operacionais</td><td>({f_despesas_operacionais})</td></tr>
                <tr><td><strong>(=) Lucro Operacional (EBIT)</strong></td><td><strong>{f_lucro_operacional}</strong></td></tr>
                <tr><td>(-) Impostos sobre Lucro</td><td>({f_impostos})</td></tr>
                <tr><td><strong>(=) Lucro Líquido</strong></td><td><strong>{f_lucro_liquido}</strong></td></tr>
            </tbody>
        </table>
        <p style='font-size: 0.8rem; color: #b0bec5; margin-top: 10px;'><i>Nota: Valores de CMV, Despesas e Impostos são estimativas percentuais para fins de demonstração.</i></p>
    </div>
    """
    return html

# --- Interface Principal da Aplicação (REESTRUTURADA) ---
def main():
    # Inicializar session state para controle da tabela pós-registro
    if "show_table" not in st.session_state:
        st.session_state.show_table = False
    if "last_registered_data" not in st.session_state:
        st.session_state.last_registered_data = None

    # Título com logo centralizada
    st.markdown("""
    <div class="header-container">
        <div class="logo-container">
            <img src="https://raw.githubusercontent.com/lucasricardocs/clipsburger/main/logo.png" class="logo-image" alt="Logo Clips Burger">
            <div>
                <h1>SISTEMA FINANCEIRO - CLIP'S BURGER</h1>
                <p>Gestão inteligente de vendas - 2025</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Carregar e processar dados
    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    # --- SIDEBAR COM FILTROS ---
    with st.sidebar:
        st.header("🔍 Filtros")
        st.markdown("---")

        anos_disponiveis = sorted(df_processed["Ano"].dropna().unique().astype(int), reverse=True) if not df_processed.empty and "Ano" in df_processed.columns else []
        meses_disponiveis = sorted(df_processed["Mês"].dropna().unique().astype(int)) if not df_processed.empty and "Mês" in df_processed.columns else []
        meses_nomes_map = {m: meses_ordem[m-1] for m in meses_disponiveis}

        # Filtro de Ano
        default_ano = [datetime.now().year] if datetime.now().year in anos_disponiveis else ([anos_disponiveis[0]] if anos_disponiveis else [])
        selected_anos = st.multiselect("Ano(s):", options=anos_disponiveis, default=default_ano)

        # Filtro de Mês (dependente do ano)
        if selected_anos:
            meses_filtrados_ano = sorted(df_processed[df_processed["Ano"].isin(selected_anos)]["Mês"].dropna().unique().astype(int))
            meses_nomes_filtrados_map = {m: meses_ordem[m-1] for m in meses_filtrados_ano}
            default_mes = [datetime.now().month] if datetime.now().month in meses_filtrados_ano else meses_filtrados_ano
            selected_meses_num = st.multiselect("Mês(es):",
                                              options=meses_filtrados_ano,
                                              format_func=lambda m: meses_nomes_filtrados_map.get(m, m),
                                              default=default_mes)
        else:
            selected_meses_num = []
            st.multiselect("Mês(es):", options=[], disabled=True)

    # Aplicar filtros
    df_filtered = df_processed.copy()
    if selected_anos:
        df_filtered = df_filtered[df_filtered["Ano"].isin(selected_anos)]
    if selected_meses_num:
        df_filtered = df_filtered[df_filtered["Mês"].isin(selected_meses_num)]

    # Exibir resumo dos filtros na sidebar
    with st.sidebar:
        st.markdown("---")
        st.subheader("Resumo Filtrado")
        if not df_filtered.empty:
            st.metric("Registros", len(df_filtered))
            st.metric("Faturamento", format_brl(df_filtered["Total"].sum()))
        else:
            st.info("Nenhum registro encontrado com os filtros selecionados.")
        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)
        st.caption(f"Última atualização dos dados: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    # --- TABS PRINCIPAIS ---
    tab1, tab_dashboard, tab_contabil = st.tabs([
        "📝 Registrar Venda",
        "📊 Dashboard",
        "💰 Análise Contábil"
    ])

    # --- TAB 1: REGISTRAR VENDA ---
    with tab1:
        st.header("📝 Registrar Nova Venda")
        st.markdown("--- ")

        with st.form(key="registro_venda_form", clear_on_submit=True):
            data_input = st.date_input("📅 Data da Venda", value=datetime.now().date(), format="DD/MM/YYYY")
            col1_form, col2_form, col3_form = st.columns(3)
            with col1_form:
                cartao_input = st.number_input("💳 Cartão (R$)", min_value=0.0, value=None, format="%.2f", placeholder="0.00")
            with col2_form:
                dinheiro_input = st.number_input("💵 Dinheiro (R$)", min_value=0.0, value=None, format="%.2f", placeholder="0.00")
            with col3_form:
                pix_input = st.number_input("📱 PIX (R$)", min_value=0.0, value=None, format="%.2f", placeholder="0.00")

            submitted = st.form_submit_button("✅ Registrar Venda", use_container_width=True, type="primary")

            if submitted:
                cartao_val = cartao_input if cartao_input is not None else 0.0
                dinheiro_val = dinheiro_input if dinheiro_input is not None else 0.0
                pix_val = pix_input if pix_input is not None else 0.0
                total_venda_form = cartao_val + dinheiro_val + pix_val

                if total_venda_form > 0:
                    worksheet_obj = get_worksheet()
                    if worksheet_obj:
                        # Passa o objeto date diretamente
                        success = add_data_to_sheet(data_input, cartao_val, dinheiro_val, pix_val, worksheet_obj)
                        if success:
                            st.success(f"✅ Venda de {format_brl(total_venda_form)} registrada para {data_input.strftime('%d/%m/%Y')}!")
                            st.session_state.show_table = True # Ativa a exibição da tabela
                            st.session_state.last_registered_data = df_filtered.copy() # Salva os dados filtrados no momento do registro
                            st.rerun() # Força o rerun para atualizar a UI e mostrar a tabela
                        else:
                            st.error("❌ Falha ao registrar a venda na planilha.")
                    else:
                        st.error("❌ Falha ao conectar à planilha. Venda não registrada.")
                else:
                    st.warning("⚠️ O valor total da venda deve ser maior que zero.")

        # Exibição condicional da tabela de vendas filtradas
        if st.session_state.show_table and st.session_state.last_registered_data is not None:
            st.markdown("--- ")
            st.subheader("🧾 Tabela de Vendas (Visão Atual Filtrada)")
            df_to_show = st.session_state.last_registered_data
            cols_to_display = ["DataFormatada", "DiaSemana", "Cartão", "Dinheiro", "Pix", "Total"]
            cols_existentes = [col for col in cols_to_display if col in df_to_show.columns]
            if cols_existentes:
                st.dataframe(df_to_show[cols_existentes].sort_values(by="DataFormatada", ascending=False),
                               use_container_width=True,
                               height=400,
                               hide_index=True,
                               column_config={ # Renomear colunas para melhor leitura
                                    "DataFormatada": "Data",
                                    "DiaSemana": "Dia da Semana",
                                    "Cartão": st.column_config.NumberColumn(format="R$ %.2f"),
                                    "Dinheiro": st.column_config.NumberColumn(format="R$ %.2f"),
                                    "Pix": st.column_config.NumberColumn(format="R$ %.2f"),
                                    "Total": st.column_config.NumberColumn(format="R$ %.2f")
                                })
            else:
                st.info("Colunas necessárias para a tabela não encontradas.")

    # --- TAB DASHBOARD ---
    with tab_dashboard:
        st.header("📊 Dashboard Geral")
        st.markdown("--- ")

        if df_filtered.empty:
            st.warning("Não há dados para exibir no dashboard com os filtros selecionados. Ajuste os filtros na barra lateral.")
        else:
            # 1. Resumo Financeiro
            st.subheader("📈 Resumo Financeiro")
            display_resumo_financeiro(df_filtered)
            st.markdown("--- ")

            # 2. Heatmap de Calendário
            st.subheader("🗓️ Calendário de Atividade (Vendas Diárias)")
            current_year = datetime.now().year
            # Tenta gerar para o ano atual ou o último ano com dados
            year_to_display = current_year if current_year in selected_anos else (selected_anos[0] if selected_anos else None)
            if year_to_display:
                try:
                    heatmap_fig_anual, heatmap_fig_mensal = create_calendar_heatmap(df_filtered, year_to_display)
                    if heatmap_fig_anual:
                        st.plotly_chart(heatmap_fig_anual, use_container_width=True)
                        
                        # Adicionar o gráfico mensal abaixo do diário
                        if heatmap_fig_mensal:
                            st.plotly_chart(heatmap_fig_mensal, use_container_width=True)
                    else:
                        st.info(f"Não foi possível gerar o heatmap para {year_to_display}.")
                except Exception as e:
                    st.error(f"Erro ao gerar o heatmap de calendário: {e}")
                    st.info("Continuando com os outros gráficos...")
            else:
                st.info("Selecione um ano no filtro para visualizar o calendário.")
            st.markdown("--- ")

            # 3. Evolução Patrimonial Acumulada
            st.subheader("💹 Evolução do Faturamento Acumulado")
            cumulative_chart = create_cumulative_evolution_chart(df_filtered)
            if cumulative_chart:
                st.altair_chart(cumulative_chart, use_container_width=True)
            else:
                st.info("Não foi possível gerar o gráfico de evolução acumulada.")
            st.markdown("--- ")

            # 4. Métodos de Pagamento (Cards)
            st.subheader("💳 Métodos de Pagamento")
            display_metodos_pagamento(df_filtered)
            st.markdown("--- ")

            # 5. Gráficos Lado a Lado (Vendas Diárias e Radial)
            st.subheader("📅 Análise Diária e Distribuição")
            col_daily, col_radial = st.columns([2, 1]) # 2/3 para diário, 1/3 para radial
            with col_daily:
                st.markdown("###### Vendas Diárias e Média Móvel")
                daily_chart = create_advanced_daily_sales_chart(df_filtered)
                if daily_chart:
                    st.altair_chart(daily_chart, use_container_width=True)
                else:
                    st.info("Sem dados de vendas diárias para exibir.")
            with col_radial:
                st.markdown("###### Distribuição por Pagamento")
                radial_chart = create_radial_plot(df_filtered)
                if radial_chart:
                    st.altair_chart(radial_chart, use_container_width=True)
                else:
                    st.info("Sem dados para o gráfico de pagamentos.")
            st.markdown("--- ")

            # 6. Média de Vendas por Dia da Semana
            st.subheader("📊 Média de Vendas por Dia da Semana")
            weekday_chart = create_weekday_sales_chart(df_filtered)
            if weekday_chart:
                st.altair_chart(weekday_chart, use_container_width=True)
            else:
                st.info("Sem dados para o gráfico de média por dia da semana.")
            st.markdown("--- ")

            # 7. Ranking Dias Semana e Frequência
            col_rank, col_freq = st.columns(2)
            with col_rank:
                st.subheader("🏆 Ranking Dias da Semana (Média R$)")
                display_ranking_dias_semana(df_filtered)
            with col_freq:
                st.subheader("🗓️ Frequência de Trabalho (Dias/Mês)")
                display_frequencia_trabalho(df_filtered)
            st.markdown("--- ")

            # 8. Assiduidade
            st.subheader("⏱️ Assiduidade e Consistência")
            display_assiduidade(df_filtered)
            st.markdown("--- ")

            # 9. Insights
            st.subheader("🧠 Insights Automáticos")
            display_insights(df_filtered)
            st.markdown("--- ")

    # --- TAB ANÁLISE CONTÁBIL ---
    with tab_contabil:
        st.header("💰 Análise Contábil")
        st.markdown("--- ")

        if df_filtered.empty:
            st.warning("Não há dados para exibir a análise contábil com os filtros selecionados.")
        else:
            # Gerar e exibir DRE
            st.subheader("🧾 Demonstração do Resultado (DRE)")
            dre_html_content = generate_dre_html(df_filtered)
            st.markdown(dre_html_content, unsafe_allow_html=True)
            st.markdown("--- ")

# --- Execução Principal ---
if __name__ == "__main__":
    main()
