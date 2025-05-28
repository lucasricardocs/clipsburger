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
import datetime as dt

# Suprimir warnings específicos do pandas
warnings.filterwarnings("ignore", category=FutureWarning, message=".*observed=False.*")

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = "1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg"
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
@st.cache_data(ttl=600)
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

            for col in ["Cartão", "Dinheiro", "Pix"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    df[col] = 0

            if "Data" not in df.columns:
                 st.warning("Coluna \'Data\' não encontrada na planilha. Criando coluna vazia.")
                 df["Data"] = pd.NaT
            else:
                try:
                    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
                except ValueError:
                    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

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
        st.warning("DataFrame de entrada vazio ou sem coluna \'Data\' para processamento.")
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

# --- Funções de Gráficos Interativos ---

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
        order=alt.Order("Valor:Q", sort="descending"),
        tooltip=[
            alt.Tooltip("Método:N", title="Método"),
            alt.Tooltip("Valor:Q", title="Valor", format=",.2f")
        ]
    )

    radial_plot = base.mark_arc(innerRadius=30, stroke=COR_FUNDO_CONTAINER, strokeWidth=3).properties(
        height=500,
        background="transparent"
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

def create_advanced_daily_sales_chart(df):
    """Cria um gráfico de vendas diárias empilhadas com visual limpo e profissional."""
    if df.empty or 'Data' not in df.columns:
        return None
    
    required_cols = ['Cartão', 'Dinheiro', 'Pix']
    if not all(col in df.columns for col in required_cols):
        return None
    
    df_sorted = df.sort_values('Data').copy()
    df_sorted.dropna(subset=['Data'] + required_cols, inplace=True)
    
    if df_sorted.empty:
        return None
    
    df_grouped = df_sorted.groupby('Data')[required_cols].sum().reset_index()
    
    df_grouped['DataFormatada'] = df_grouped['Data'].dt.strftime('%d/%m')
    
    df_melted = df_grouped.melt(
        id_vars=['Data', 'DataFormatada'],
        value_vars=required_cols,
        var_name='Método',
        value_name='Valor'
    )
    
    df_melted = df_melted[df_melted['Valor'] > 0]
    
    if df_melted.empty:
        return None
    
    cores_exatas = ['#FF8C00', '#70AD47', '#5B9BD5']
    
    ordem_metodos = ['Dinheiro', 'Pix', 'Cartão']
    
    bars = alt.Chart(df_melted).mark_bar(
        size=30,
        stroke='white',
        strokeWidth=1.5
    ).encode(
        x=alt.X(
            'DataFormatada:O',
            title='',
            axis=alt.Axis(
                labelAngle=0,
                labelFontSize=10,
                labelColor='#666666',
                grid=False,
                ticks=False,
                domain=False,
                labelPadding=8
            )
        ),
        y=alt.Y(
            'Valor:Q',
            title='',
            stack='zero',
            axis=alt.Axis(
                labelFontSize=10,
                labelColor='#666666',
                grid=True,
                gridColor='#D0D0D0',
                gridOpacity=1,
                ticks=False,
                domain=False,
                tickCount=6
            )
        ),
        color=alt.Color(
            'Método:N',
            scale=alt.Scale(
                domain=ordem_metodos,
                range=cores_exatas
            ),
            legend=alt.Legend(
                title=None,
                orient='bottom',
                direction='horizontal',
                labelFontSize=11,
                labelColor='#333333',
                symbolSize=100,
                symbolType='square',
                padding=15,
                offset=20,
                columns=3,
                symbolStrokeWidth=0
            )
        ),
        order=alt.Order(
            'Método:N',
            sort=ordem_metodos
        ),
        tooltip=[
            alt.Tooltip('DataFormatada:O', title='Data'),
            alt.Tooltip('Método:N', title='Método'),
            alt.Tooltip('Valor:Q', title='Valor (R$)', format=',.2f')
        ]
    ).properties(
        height=350,
        width=900,
        padding={'top': 10, 'bottom': 80, 'left': 50, 'right': 20}
    ).configure_view(
        stroke=None
    ).configure(
        background='white'
    )
    
    return bars

def create_weekday_sales_chart(df):
    """Cria gráfico de barras da média de vendas por dia da semana."""
    if df.empty or "DiaSemana" not in df.columns or "Total" not in df.columns:
        return None

    weekday_avg = df.groupby("DiaSemana", observed=False)["Total"].mean().reset_index()
    weekday_avg = weekday_avg.dropna()

    if weekday_avg.empty:
        return None

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
        height=500,
        background="transparent"
    ).configure_view(
        strokeOpacity=0
    )
    return chart

def create_cumulative_evolution_chart(df):
    """Cria gráfico de área da evolução acumulada de vendas com destaque no último valor."""
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        return None

    df_sorted = df.sort_values("Data").copy()
    df_sorted.dropna(subset=["Data", "Total"], inplace=True)
    if df_sorted.empty:
        return None

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
        line={"color": cor_linha, "strokeWidth": 3},
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color=cor_inicio_grad, offset=0),
                alt.GradientStop(color=cor_fim_grad, offset=1)
            ],
            x1=1, x2=1, y1=1, y2=0
        ),
        opacity=0.8,
        stroke=cor_linha,
        strokeWidth=3
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
            height=500,
            background="transparent"
        ).configure_view(
            strokeOpacity=0
        ).interactive()
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

    ano = int(ano)
    
    df_year = df[df["Data"].dt.year == ano].copy()
    if df_year.empty:
        st.info(f"Sem dados de vendas para o ano {ano}.")
        return None, None

    dates_completo = pd.date_range(f'{ano}-01-01', f'{ano}-12-31', freq='D')

    dados_ano_completo = []
    for date in dates_completo:
        if date in df_year['Data'].values:
            row = df_year[df_year['Data'] == date].iloc[0]
            dados_ano_completo.append({
                'Data': date,
                'Cartão': row['Cartão'],
                'Dinheiro': row['Dinheiro'],
                'Pix': row['Pix'],
                'Total_Vendas': row['Total']
            })
        else:
            dados_ano_completo.append({
                'Data': date,
                'Cartão': 0,
                'Dinheiro': 0,
                'Pix': 0,
                'Total_Vendas': 0
            })

    df_ano_completo = pd.DataFrame(dados_ano_completo)

    df_ano_completo['data_str'] = df_ano_completo['Data'].dt.strftime('%d/%m/%Y')
    df_ano_completo['dia_semana'] = df_ano_completo['Data'].dt.dayofweek

    primeiro_dia = dt.date(ano, 1, 1)
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

        if row['Total_Vendas'] == 0:
            categoria = 0
        elif row['Total_Vendas'] < 1500:
            categoria = 1
        elif row['Total_Vendas'] < 2500:
            categoria = 2
        elif row['Total_Vendas'] < 3000:
            categoria = 3
        else:
            categoria = 4

        valores.append(categoria)

        if row['Total_Vendas'] > 0:
            hover_text = (f"📅 {row['data_str']}<br>"
                         f"💰 Total: {format_brl(row['Total_Vendas'])}<br>"
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
        [0.0, '#161b22'],
        [0.001, '#39D353'],
        [0.25, '#39D353'],
        [0.251, '#37AB4B'],
        [0.5, '#37AB4B'],
        [0.501, '#006D31'],
        [0.75, '#006D31'],
        [0.751, '#0D4428'],
        [1.0, '#0D4428']
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
    meses_nomes = []
    for mes in range(1, 13):
        primeiro_dia_mes = dt.date(ano, mes, 1)
        dias_desde_inicio = (primeiro_dia_mes - primeiro_dia).days
        semana_mes = (dias_desde_inicio + primeiro_dia_semana) // 7
        meses_posicoes.append(semana_mes)
        meses_nomes.append(['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                           'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][mes-1])

    fig.update_layout(
        title=f"📊 Calendário de Vendas {ano}",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff', family="Arial"),

        xaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            tickmode='array',
            tickvals=meses_posicoes,
            ticktext=meses_nomes,
            tickfont=dict(color='#ffffff', size=14),
            side='top',
            tickangle=0,
            ticklabelstandoff=3
        ),

        yaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            tickmode='array',
            tickvals=[0, 1, 2, 3, 4, 5, 6],
            ticktext=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
            tickfont=dict(color='#ffffff', size=14),
            ticklen=0,
            ticklabelstandoff=15,
            autorange="reversed"
        ),

        height=500,
        title_x=0.5,
        title_font=dict(size=18, color='#ffffff'),
        margin=dict(l=50, r=50, t=100, b=50)
    )

    return fig, df_ano_completo

def criar_heatmap_vendas_mensais_espacamento_correto(df):
    """Função para criar heatmap mensal horizontal com espaçamento correto"""
    if df.empty:
        return None, None

    df_vendas = df[df['Total_Vendas'] > 0].copy()
    df_vendas['Mes'] = df_vendas['Data'].dt.month
    vendas_mensais = df_vendas.groupby('Mes').agg({
        'Total_Vendas': 'sum',
        'Cartão': 'sum',
        'Dinheiro': 'sum',
        'Pix': 'sum'
    }).reset_index()

    meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    vendas_mensais['Mes_Nome'] = vendas_mensais['Mes'].map(
        lambda x: meses_nomes[x-1] if x <= len(meses_nomes) else f'Mês {x}'
    )

    matriz_mensal = np.zeros((1, 12))
    matriz_hover_mensal = np.full((1, 12), '', dtype=object)

    ano_atual = df['Data'].dt.year.iloc[0] if not df.empty else datetime.now().year
    for mes_idx in range(12):
        mes_num = mes_idx + 1
        mes_nome = meses_nomes[mes_idx]

        dados_mes = vendas_mensais[vendas_mensais['Mes'] == mes_num]

        if len(dados_mes) > 0:
            row = dados_mes.iloc[0]
            matriz_mensal[0, mes_idx] = row['Total_Vendas']

            hover_text = (f"📅 {mes_nome} {ano_atual}<br>"
                         f"💰 Total: {format_brl(row['Total_Vendas'])}<br>"
                         f"💳 Cartão: {format_brl(row['Cartão'])}<br>"
                         f"💵 Dinheiro: {format_brl(row['Dinheiro'])}<br>"
                         f"📱 Pix: {format_brl(row['Pix'])}")
        else:
            matriz_mensal[0, mes_idx] = 0
            hover_text = f"📅 {mes_nome} {ano_atual}<br>❌ Sem dados"

        matriz_hover_mensal[0, mes_idx] = hover_text

    fig = go.Figure(data=go.Heatmap(
        z=matriz_mensal,
        text=matriz_hover_mensal,
        hovertemplate='%{text}<extra></extra>',
        colorscale=[
            [0.0, '#161b22'],
            [0.001, '#39D353'],
            [0.25, '#37AB4B'],
            [0.5, '#006D31'],
            [1.0, '#0D4428']
        ],
        showscale=False,
        xgap=5,
        ygap=5,
    ))

    fig.update_layout(
        title=f'📊 Vendas Mensais {ano_atual}',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff', family="Arial"),

        xaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            tickmode='array',
            tickvals=list(range(12)),
            ticktext=meses_nomes,
            tickfont=dict(color='#ffffff', size=14),
            side='bottom'
        ),

        yaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),

        height=250,
        title_x=0.5,
        title_font=dict(size=18, color='#ffffff'),
        margin=dict(l=50, r=50, t=50, b=50)
    )

    return fig, vendas_mensais

# --- Funções de Análise e Exibição ---

def display_resumo_financeiro(df):
    """Exibe os cards de resumo financeiro."""
    if df.empty:
        st.info("Não há dados suficientes para o resumo financeiro.")
        return

    total_faturamento = df["Total"].sum()
    media_diaria = df["Total"].mean() if not df.empty else 0
    maior_venda = df["Total"].max() if not df.empty else 0
    menor_venda = df[df["Total"] > 0]["Total"].min() if not df[df["Total"] > 0].empty else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Faturamento Total", format_brl(total_faturamento))
    with col2:
        st.metric("📊 Média por Dia", format_brl(media_diaria))
    with col3:
        st.metric("🚀 Maior Venda Diária", format_brl(maior_venda))
    with col4:
        st.metric("📉 Menor Venda Diária", format_brl(menor_venda))

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

def display_ranking_e_frequencia(df_filtered):
    """Exibe o ranking de dias e a análise de frequência conforme o formato anterior."""
    if df_filtered.empty or 'DiaSemana' not in df_filtered.columns or 'Total' not in df_filtered.columns:
        st.info("📊 Dados insuficientes para calcular a análise por dia da semana e frequência.")
        return

    medias_por_dia = df_filtered.groupby('DiaSemana', observed=False)['Total'].agg(['mean', 'count'])
    medias_por_dia = medias_por_dia.reindex(dias_semana_ordem).dropna()
    medias_por_dia = medias_por_dia.sort_values(by='mean', ascending=False)

    if not medias_por_dia.empty:
        st.subheader("📊 Ranking dos Dias da Semana")
        col_ranking1, col_ranking2 = st.columns(2)

        with col_ranking1:
            st.markdown("### 🏆 **Melhores Dias**")
            if len(medias_por_dia) >= 1:
                primeiro = medias_por_dia.index[0]
                st.success(f"🥇 **1º lugar:** {primeiro}")
                st.write(f"   Média: {format_brl(medias_por_dia.loc[primeiro, 'mean'])}")
                st.write(f"   Dias trabalhados: {int(medias_por_dia.loc[primeiro, 'count'])}")

            if len(medias_por_dia) >= 2:
                segundo = medias_por_dia.index[1]
                st.info(f"🥈 **2º lugar:** {segundo}")
                st.write(f"   Média: {format_brl(medias_por_dia.loc[segundo, 'mean'])}")
                st.write(f"   Dias trabalhados: {int(medias_por_dia.loc[segundo, 'count'])}")

        with col_ranking2:
            st.markdown("### 📉 **Piores Dias**")
            if len(medias_por_dia) >= 2:
                penultimo = medias_por_dia.index[-2]
                st.warning(f"📊 **Penúltimo:** {penultimo}")
                st.write(f"   Média: {format_brl(medias_por_dia.loc[penultimo, 'mean'])}")
                st.write(f"   Dias trabalhados: {int(medias_por_dia.loc[penultimo, 'count'])}")

            if len(medias_por_dia) >= 1:
                ultimo = medias_por_dia.index[-1]
                st.error(f"🔻 **Último lugar:** {ultimo}")
                st.write(f"   Média: {format_brl(medias_por_dia.loc[ultimo, 'mean'])}")
                st.write(f"   Dias trabalhados: {int(medias_por_dia.loc[ultimo, 'count'])}")

        st.markdown("---")

        st.subheader("📅 Análise de Frequência de Trabalho")

        if not df_filtered.empty and 'Data' in df_filtered.columns:
            data_inicio = df_filtered['Data'].min()
            data_fim = df_filtered['Data'].max()

            total_dias_periodo = (data_fim - data_inicio).days + 1

            domingos_periodo = 0
            data_atual = data_inicio
            while data_atual <= data_fim:
                if data_atual.weekday() == 6:
                    domingos_periodo += 1
                data_atual += timedelta(days=1)

            dias_uteis_esperados = total_dias_periodo - domingos_periodo

            dias_trabalhados = df_filtered['Data'].nunique()

            dias_falta = dias_uteis_esperados - dias_trabalhados

            col_freq1, col_freq2, col_freq3, col_freq4 = st.columns(4)

            with col_freq1:
                st.metric(
                    "📅 Período Analisado",
                    f"{total_dias_periodo} dias",
                    help=f"De {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}"
                )

            with col_freq2:
                st.metric(
                    "🏢 Dias Trabalhados",
                    f"{dias_trabalhados} dias",
                    help="Dias com registro de vendas"
                )

            with col_freq3:
                st.metric(
                    "🏖️ Domingos (Folga)",
                    f"{domingos_periodo} dias",
                    help="Domingos no período (não trabalhamos)"
                )

            with col_freq4:
                if dias_falta > 0:
                    st.metric(
                        "❌ Dias de Falta",
                        f"{dias_falta} dias",
                        help="Dias úteis sem registro de vendas",
                        delta=f"-{dias_falta}",
                        delta_color="inverse"
                    )
                else:
                    st.metric(
                        "✅ Frequência",
                        "100%",
                        help="Todos os dias úteis trabalhados!"
                    )

            if dias_uteis_esperados > 0:
                taxa_frequencia = (dias_trabalhados / dias_uteis_esperados) * 100

                if taxa_frequencia >= 95:
                    st.success(f"🎯 **Excelente frequência:** {taxa_frequencia:.1f}% dos dias úteis trabalhados!")
                elif taxa_frequencia >= 80:
                    st.info(f"👍 **Boa frequência:** {taxa_frequencia:.1f}% dos dias úteis trabalhados")
                else:
                    st.warning(f"⚠️ **Atenção à frequência:** {taxa_frequencia:.1f}% dos dias úteis trabalhados")
        else:
            st.info("📊 Dados insuficientes para calcular a análise de frequência.")
    else:
        st.info("📊 Dados insuficientes para calcular o ranking de dias da semana.")

def display_insights(df):
    """Exibe insights automáticos com estilo melhorado."""
    if df.empty or len(df) < 2:
        st.info("Dados insuficientes para gerar insights automáticos.")
        return

    total_vendas = df["Total"].sum()
    dias_trabalhados = df["Data"].nunique()
    media_diaria = total_vendas / dias_trabalhados if dias_trabalhados > 0 else 0

    media_por_dia = df.groupby("DiaSemana", observed=False)["Total"].mean().reset_index().dropna()
    melhor_dia_semana = media_por_dia.loc[media_por_dia["Total"].idxmax()] if not media_por_dia.empty else None

    metodos_total = {
        "Cartão": df["Cartão"].sum(),
        "Dinheiro": df["Dinheiro"].sum(),
        "PIX": df["Pix"].sum()
    }
    metodos_total = {k: v for k, v in metodos_total.items() if v > 0}
    if metodos_total:
        melhor_metodo = max(metodos_total, key=metodos_total.get)
        valor_melhor_metodo = metodos_total[melhor_metodo]
        percentual_melhor = (valor_melhor_metodo / total_vendas * 100) if total_vendas > 0 else 0
        sugestao_taxa = """
        <p style="margin-top: 0.5rem; font-size: 0.9rem; color: #b0bec5;">
        <i>Sugestão: Avalie as taxas associadas ao Cartão e compare com a margem de lucro para otimizar a rentabilidade.</i>
        </p>""" if melhor_metodo == "Cartão" else ""
    else:
        melhor_metodo = None
        percentual_melhor = 0
        sugestao_taxa = ""

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

    st.subheader("🧠 Insights Automáticos")
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

# --- Funções da Análise Contábil ---

def calculate_financial_results(df, salario_base, custo_contadora, cpv_percent):
    """Calcula os resultados financeiros para a DRE."""
    resultados = {}

    resultados['receita_bruta'] = df['Total'].sum()

    resultados['receita_tributavel'] = df['Dinheiro'].sum() + df['Pix'].sum()
    resultados['receita_nao_tributavel'] = df['Cartão'].sum()
    resultados['impostos_sobre_vendas'] = resultados['receita_tributavel'] * 0.06

    resultados['receita_liquida'] = resultados['receita_bruta'] - resultados['impostos_sobre_vendas']

    resultados['custo_produtos_vendidos'] = resultados['receita_bruta'] * (cpv_percent / 100.0)

    resultados['lucro_bruto'] = resultados['receita_liquida'] - resultados['custo_produtos_vendidos']

    encargos_percent = 0.55
    resultados['despesas_com_pessoal'] = salario_base * (1 + encargos_percent)
    resultados['despesas_contabeis'] = custo_contadora
    resultados['total_despesas_operacionais'] = resultados['despesas_com_pessoal'] + resultados['despesas_contabeis']

    resultados['lucro_operacional'] = resultados['lucro_bruto'] - resultados['total_despesas_operacionais']

    resultados['resultado_financeiro'] = 0

    resultados['lucro_antes_ir'] = resultados['lucro_operacional'] + resultados['resultado_financeiro']

    resultados['ir_csll'] = 0

    resultados['lucro_liquido'] = resultados['lucro_antes_ir'] - resultados['ir_csll']

    resultados['margem_bruta'] = (resultados['lucro_bruto'] / resultados['receita_liquida'] * 100) if resultados['receita_liquida'] > 0 else 0
    resultados['margem_operacional'] = (resultados['lucro_operacional'] / resultados['receita_liquida'] * 100) if resultados['receita_liquida'] > 0 else 0
    resultados['margem_liquida'] = (resultados['lucro_liquido'] / resultados['receita_liquida'] * 100) if resultados['receita_liquida'] > 0 else 0

    return resultados

def create_dre_textual(resultados, df_completo, anos_selecionados):
    """Cria a DRE em formato textual com base nos resultados calculados."""
    st.subheader("🧾 Demonstração do Resultado do Exercício (DRE)")

    if not df_completo.empty and anos_selecionados:
        min_date = df_completo[df_completo['Ano'].isin(anos_selecionados)]['Data'].min()
        max_date = df_completo[df_completo['Ano'].isin(anos_selecionados)]['Data'].max()
        periodo_str = f"Período: {min_date.strftime('%d/%m/%Y')} a {max_date.strftime('%d/%m/%Y')}"
    else:
        periodo_str = "Período não definido (sem dados ou filtro)"

    st.caption(periodo_str)

    html = f"""
    <div class="dre-textual-container">
        <table>
            <thead>
                <tr>
                    <th>Descrição</th>
                    <th>Valor (R$)</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>(+) Receita Operacional Bruta</td><td>{format_brl(resultados['receita_bruta'])}</td></tr>
                <tr><td>(-) Deduções da Receita Bruta (Simples Nacional)</td><td>({format_brl(resultados['impostos_sobre_vendas'])})</td></tr>
                <tr><td><strong>(=) Receita Operacional Líquida</strong></td><td><strong>{format_brl(resultados['receita_liquida'])}</strong></td></tr>
                <tr><td>(-) Custo dos Produtos Vendidos (CPV)</td><td>({format_brl(resultados['custo_produtos_vendidos'])})</td></tr>
                <tr><td><strong>(=) Lucro Bruto</strong></td><td><strong>{format_brl(resultados['lucro_bruto'])}</strong></td></tr>
                <tr><td>(-) Despesas Operacionais</td><td></td></tr>
                <tr><td>&nbsp;&nbsp;&nbsp;&nbsp;(-) Despesas com Pessoal</td><td>({format_brl(resultados['despesas_com_pessoal'])})</td></tr>
                <tr><td>&nbsp;&nbsp;&nbsp;&nbsp;(-) Despesas Administrativas (Contabilidade)</td><td>({format_brl(resultados['despesas_contabeis'])})</td></tr>
                <tr><td><strong>(=) Lucro Operacional (EBIT)</strong></td><td><strong>{format_brl(resultados['lucro_operacional'])}</strong></td></tr>
                <tr><td>(+/-) Resultado Financeiro</td><td>{format_brl(resultados['resultado_financeiro'])}</td></tr>
                <tr><td><strong>(=) Lucro Antes do Imposto de Renda (LAIR)</strong></td><td><strong>{format_brl(resultados['lucro_antes_ir'])}</strong></td></tr>
                <tr><td>(-) Imposto de Renda e CSLL</td><td>({format_brl(resultados['ir_csll'])})</td></tr>
                <tr><td><strong>(=) Lucro Líquido do Exercício</strong></td><td><strong>{format_brl(resultados['lucro_liquido'])}</strong></td></tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def create_financial_dashboard_altair(resultados):
    """Cria um dashboard visual simples com os principais resultados financeiros."""
    data = pd.DataFrame({
        'Componente': [
            'Receita Líquida',
            'Custo Produtos',
            'Despesas Pessoal',
            'Despesas Contábeis',
            'Lucro Líquido'
        ],
        'Valor': [
            resultados['receita_liquida'],
            resultados['custo_produtos_vendidos'],
            resultados['despesas_com_pessoal'],
            resultados['despesas_contabeis'],
            resultados['lucro_liquido']
        ],
        'Tipo': [
            'Receita',
            'Custo',
            'Despesa',
            'Despesa',
            'Resultado'
        ]
    })

    bars = alt.Chart(data).mark_bar(cornerRadius=5).encode(
        x=alt.X('Componente:N', sort='-y', title=None, axis=alt.Axis(labels=False)),
        y=alt.Y('Valor:Q', title='Valor (R$)'),
        color=alt.Color('Tipo:N', scale=alt.Scale(range=['#1f77b4', '#ff7f0e', '#d62728', '#9467bd']), legend=alt.Legend(title="Tipo")),
        tooltip=[
            alt.Tooltip('Componente:N', title='Componente'),
            alt.Tooltip('Valor:Q', title='Valor (R$)', format=',.2f')
        ]
    )

    text = bars.mark_text(
        align='center',
        baseline='bottom',
        dy=-5,
        color='white'
    ).encode(
        text=alt.Text('Valor:Q', format=',.0f')
    )

    chart = (bars + text).properties(
        title='Visão Geral: Receita, Custos, Despesas e Lucro',
        height=400,
        background="transparent"
    ).configure_view(
        strokeOpacity=0
    ).configure_title(
        fontSize=16,
        anchor='middle'
    ).configure_axis(
        labelColor=COR_TEXTO_SECUNDARIO,
        titleColor=COR_TEXTO_PRINCIPAL,
        grid=False
    ).configure_legend(
        titleColor=COR_TEXTO_PRINCIPAL,
        labelColor=COR_TEXTO_SECUNDARIO
    )

    return chart

# --- Interface Principal da Aplicação ---
def main():
    if "show_table" not in st.session_state:
        st.session_state.show_table = False
    if "last_registered_data" not in st.session_state:
        st.session_state.last_registered_data = None

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

    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    with st.sidebar:
        st.header("🔍 Filtros")
        st.markdown("---")

        anos_disponiveis = sorted(df_processed["Ano"].dropna().unique().astype(int), reverse=True) if not df_processed.empty and "Ano" in df_processed.columns else []
        meses_disponiveis = sorted(df_processed["Mês"].dropna().unique().astype(int)) if not df_processed.empty and "Mês" in df_processed.columns else []
        meses_nomes_map = {m: meses_ordem[m-1] for m in meses_disponiveis}

        default_ano = [datetime.now().year] if datetime.now().year in anos_disponiveis else ([anos_disponiveis[0]] if anos_disponiveis else [])
        selected_anos = st.multiselect("Ano(s):", options=anos_disponiveis, default=default_ano)

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

    df_filtered = df_processed.copy()
    if selected_anos:
        df_filtered = df_filtered[df_filtered["Ano"].isin(selected_anos)]
    if selected_meses_num:
        df_filtered = df_filtered[df_filtered["Mês"].isin(selected_meses_num)]

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

    tab1, tab_dashboard, tab_contabil = st.tabs([
        "📝 Registrar Venda",
        "📊 Dashboard",
        "💰 Análise Contábil"
    ])

    with tab1:
        st.header("📝 Registrar Nova Venda")
        st.markdown("---")

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
                        success = add_data_to_sheet(data_input, cartao_val, dinheiro_val, pix_val, worksheet_obj)
                        if success:
                            st.success(f"✅ Venda de {format_brl(total_venda_form)} registrada para {data_input.strftime('%d/%m/%Y')}!")
                            st.session_state.show_table = True
                            df_raw_updated = read_sales_data()
                            df_processed_updated = process_data(df_raw_updated)
                            df_filtered_updated = df_processed_updated.copy()
                            if selected_anos:
                                df_filtered_updated = df_filtered_updated[df_filtered_updated["Ano"].isin(selected_anos)]
                            if selected_meses_num:
                                df_filtered_updated = df_filtered_updated[df_filtered_updated["Mês"].isin(selected_meses_num)]
                            st.session_state.last_registered_data = df_filtered_updated
                            st.rerun()
                        else:
                            st.error("❌ Falha ao registrar a venda na planilha.")
                    else:
                        st.error("❌ Falha ao conectar à planilha. Venda não registrada.")
                else:
                    st.warning("⚠️ O valor total da venda deve ser maior que zero.")

        if st.session_state.show_table and st.session_state.last_registered_data is not None:
            st.markdown("---")
            st.subheader("🧾 Tabela de Vendas (Visão Atual Filtrada)")
            df_to_show = st.session_state.last_registered_data
            cols_to_display = ["DataFormatada", "DiaSemana", "Cartão", "Dinheiro", "Pix", "Total"]
            cols_existentes = [col for col in cols_to_display if col in df_to_show.columns]
            if cols_existentes:
                st.dataframe(df_to_show[cols_existentes].sort_values(by="DataFormatada", ascending=False),
                               use_container_width=True,
                               height=400,
                               hide_index=True,
                               column_config={
                                    "DataFormatada": "Data",
                                    "DiaSemana": "Dia da Semana",
                                    "Cartão": st.column_config.NumberColumn(format="R$ %.2f"),
                                    "Dinheiro": st.column_config.NumberColumn(format="R$ %.2f"),
                                    "Pix": st.column_config.NumberColumn(format="R$ %.2f"),
                                    "Total": st.column_config.NumberColumn(format="R$ %.2f")
                                })
            else:
                st.info("Colunas necessárias para a tabela não encontradas.")

    with tab_dashboard:
        st.header("📊 Dashboard Geral")
        st.markdown("---")

        if df_filtered.empty:
            st.warning("Não há dados para exibir no dashboard com os filtros selecionados. Ajuste os filtros na barra lateral.")
        else:
            st.subheader("📈 Resumo Financeiro")
            display_resumo_financeiro(df_filtered)
            st.markdown("---")

            st.subheader("🗓️ Calendário de Atividade (Vendas Diárias)")
            current_year = datetime.now().year
            year_to_display = current_year if current_year in selected_anos else (selected_anos[0] if selected_anos else None)
            if year_to_display:
                try:
                    year_to_display = int(year_to_display)
                    heatmap_fig_anual, df_ano_completo_heatmap = criar_calendario_anual_espacamento_correto(df_filtered, year_to_display)
                    if heatmap_fig_anual:
                        st.plotly_chart(heatmap_fig_anual, use_container_width=True)

                        if df_ano_completo_heatmap is not None and not df_ano_completo_heatmap.empty:
                            heatmap_fig_mensal, _ = criar_heatmap_vendas_mensais_espacamento_correto(df_ano_completo_heatmap)
                            if heatmap_fig_mensal:
                                st.plotly_chart(heatmap_fig_mensal, use_container_width=True)
                            else:
                                st.info(f"Não foi possível gerar o heatmap mensal para {year_to_display}.")
                        else:
                             st.info(f"Não foi possível gerar o heatmap mensal para {year_to_display} (sem dados processados).")
                    else:
                        st.info(f"Não foi possível gerar o heatmap anual para {year_to_display}.")
                except Exception as e:
                    st.error(f"Erro ao gerar o heatmap de calendário: {e}")
                    st.info("Continuando com os outros gráficos...")
            else:
                st.info("Selecione um ano no filtro para visualizar o calendário.")
            st.markdown("---")

            st.subheader("💹 Evolução do Faturamento Acumulado")
            cumulative_chart = create_cumulative_evolution_chart(df_filtered)
            if cumulative_chart:
                st.altair_chart(cumulative_chart, use_container_width=True)
            else:
                st.info("Não foi possível gerar o gráfico de evolução acumulada.")
            st.markdown("---")

            st.subheader("💳 Métodos de Pagamento")
            display_metodos_pagamento(df_filtered)
            st.markdown("---")

            st.subheader("📅 Análise Diária e Distribuição")
            col_daily, col_radial = st.columns([2, 1])
            with col_daily:
                st.markdown("###### Vendas Diárias por Método (Empilhado)")
                daily_stacked_chart = create_advanced_daily_sales_chart(df_filtered)
                if daily_stacked_chart:
                    st.altair_chart(daily_stacked_chart, use_container_width=True)
                else:
                    st.info("Sem dados de vendas diárias para exibir.")
            with col_radial:
                st.markdown("###### Distribuição por Pagamento")
                radial_chart = create_radial_plot(df_filtered)
                if radial_chart:
                    st.altair_chart(radial_chart, use_container_width=True)
                else:
                    st.info("Sem dados para o gráfico de pagamentos.")
            st.markdown("---")

            st.subheader("📊 Média de Vendas por Dia da Semana")
            weekday_chart = create_weekday_sales_chart(df_filtered)
            if weekday_chart:
                st.altair_chart(weekday_chart, use_container_width=True)
            else:
                st.info("Sem dados para o gráfico de média por dia da semana.")
            st.markdown("---")

            display_ranking_e_frequencia(df_filtered)
            st.markdown("---")

            display_insights(df_filtered)
            st.markdown("---")

    with tab_contabil:
        st.header("📊 Análise Contábil e Financeira Detalhada")

        st.markdown("""
        ### 📋 **Sobre esta Análise**
        Esta análise segue as **normas contábeis brasileiras** com estrutura de DRE conforme:
        - **Lei 6.404/76** (Lei das S.A.) | **NBC TG 26** (Apresentação das Demonstrações Contábeis)
        - **Regime Tributário:** Simples Nacional (6% sobre receita tributável)
        - **Metodologia de Margens:** Margem Bruta = (Lucro Bruto ÷ Receita Líquida) × 100
        """)

        with st.container(border=True):
            st.subheader("⚙️ Parâmetros para Simulação Contábil")

            col_param1, col_param2, col_param3 = st.columns(3)
            with col_param1:
                salario_minimo_input = st.number_input(
                    "💼 Salário Base Funcionário (R$)",
                    min_value=0.0, value=1550.0, format="%.2f",
                    help="Salário base do funcionário. Os encargos (55%) serão calculados automaticamente.",
                    key="salario_tab_contabil"
                )
            with col_param2:
                custo_contadora_input = st.number_input(
                    "📋 Honorários Contábeis (R$)",
                    min_value=0.0, value=316.0, format="%.2f",
                    help="Valor mensal pago pelos serviços contábeis.",
                    key="contadora_tab_contabil"
                )
            with col_param3:
                custo_fornecedores_percentual = st.number_input(
                    "📦 Custo dos Produtos (%)",
                    min_value=0.0, max_value=100.0, value=30.0, format="%.1f",
                    help="Percentual da receita bruta destinado à compra de produtos.",
                    key="fornecedores_tab_contabil"
                )

        st.markdown("---")

        if df_filtered.empty or 'Total' not in df_filtered.columns:
            st.warning("📊 **Não há dados suficientes para análise contábil.** Ajuste os filtros ou registre vendas.")
        else:
            resultados = calculate_financial_results(
                df_filtered, salario_minimo_input, custo_contadora_input, custo_fornecedores_percentual
            )

            with st.container(border=True):
                create_dre_textual(resultados, df_filtered, selected_anos)

            st.markdown("---")

            financial_dashboard = create_financial_dashboard_altair(resultados)
            if financial_dashboard:
                st.altair_chart(financial_dashboard, use_container_width=True)

            st.markdown("---")

            with st.container(border=True):
                st.subheader("📈 Análise de Margens e Indicadores")

                col_margin1, col_margin2, col_margin3 = st.columns(3)

                with col_margin1:
                    st.metric(
                        "📊 Margem Bruta",
                        f"{resultados['margem_bruta']:.2f}%",
                        help="Indica a eficiência na gestão dos custos diretos"
                    )
                    st.metric(
                        "🏛️ Carga Tributária",
                        f"{(resultados['impostos_sobre_vendas'] / resultados['receita_bruta'] * 100) if resultados['receita_bruta'] > 0 else 0:.2f}%",
                        help="Percentual de impostos sobre a receita bruta"
                    )

                with col_margin2:
                    st.metric(
                        "💼 Margem Operacional",
                        f"{resultados['margem_operacional']:.2f}%",
                        help="Indica a eficiência operacional do negócio"
                    )
                    st.metric(
                        "👥 Custo de Pessoal",
                        f"{(resultados['despesas_com_pessoal'] / resultados['receita_bruta'] * 100) if resultados['receita_bruta'] > 0 else 0:.2f}%",
                        help="Percentual das despesas com pessoal sobre receita"
                    )

                with col_margin3:
                    st.metric(
                        "💰 Margem Líquida",
                        f"{resultados['margem_liquida']:.2f}%",
                        help="Rentabilidade final após todos os custos e despesas"
                    )
                    st.metric(
                        "📦 Custo dos Produtos",
                        f"{(resultados['custo_produtos_vendidos'] / resultados['receita_bruta'] * 100) if resultados['receita_bruta'] > 0 else 0:.2f}%",
                        help="Percentual do CPV sobre receita bruta"
                    )

            st.markdown("---")

            with st.container(border=True):
                st.subheader("📋 Resumo Executivo")

                col_exec1, col_exec2 = st.columns(2)

                with col_exec1:
                    st.markdown("**💰 Receitas:**")
                    st.write(f"• Receita Bruta: {format_brl(resultados['receita_bruta'])}")
                    st.write(f"• Receita Líquida: {format_brl(resultados['receita_liquida'])}")
                    st.write(f"• Receita Tributável: {format_brl(resultados['receita_tributavel'])}")
                    st.write(f"• Receita Não Tributável: {format_brl(resultados['receita_nao_tributavel'])}")

                    st.markdown("**📊 Resultados:**")
                    st.write(f"• Lucro Bruto: {format_brl(resultados['lucro_bruto'])}")
                    st.write(f"• Lucro Operacional: {format_brl(resultados['lucro_operacional'])}")
                    st.write(f"• Lucro Líquido: {format_brl(resultados['lucro_liquido'])}")

                with col_exec2:
                    st.markdown("**💸 Custos e Despesas:**")
                    st.write(f"• Impostos s/ Vendas: {format_brl(resultados['impostos_sobre_vendas'])}")
                    st.write(f"• Custo dos Produtos: {format_brl(resultados['custo_produtos_vendidos'])}")
                    st.write(f"• Despesas com Pessoal: {format_brl(resultados['despesas_com_pessoal'])}")
                    st.write(f"• Serviços Contábeis: {format_brl(resultados['despesas_contabeis'])}")

                    st.markdown("**🎯 Indicadores-Chave:**")
                    if resultados['margem_bruta'] >= 50:
                        st.success(f"✅ Margem Bruta Saudável: {resultados['margem_bruta']:.1f}%")
                    elif resultados['margem_bruta'] >= 30:
                        st.warning(f"⚠️ Margem Bruta Moderada: {resultados['margem_bruta']:.1f}%")
                    else:
                        st.error(f"❌ Margem Bruta Baixa: {resultados['margem_bruta']:.1f}%")

                    if resultados['lucro_liquido'] > 0:
                        st.success(f"✅ Resultado Positivo: {format_brl(resultados['lucro_liquido'])}")
                    else:
                        st.error(f"❌ Resultado Negativo: {format_brl(resultados['lucro_liquido'])}")

            st.info("""
            💡 **Nota Importante:** Esta DRE segue a estrutura contábil brasileira oficial.
            Para decisões estratégicas, consulte sempre um contador qualificado.
            """)

if __name__ == "__main__":
    main()

