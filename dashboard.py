# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings
import json # Para carregar o manifest

# Suprimir warnings específicos do pandas
warnings.filterwarnings("ignore", category=FutureWarning, message=".*observed=False.*")

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = "1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg"
WORKSHEET_NAME = "Vendas"
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/clipsburger/refs/heads/main/logo.png"

# Configuração da página Streamlit
st.set_page_config(
    page_title="Clips Burger Dashboard",
    layout="wide",
    page_icon=LOGO_URL, # Usar logo como ícone
    initial_sidebar_state="expanded" # Manter sidebar para filtros
)

# Configuração de tema para gráficos mais bonitos
alt.data_transformers.enable("json")

# Paleta de cores otimizada para modo escuro
CORES_MODO_ESCURO = ["#4c78a8", "#54a24b", "#f58518", "#e45756", "#72b7b2", "#ff9da6", "#9d755d", "#bab0ac"]

# Define a ordem correta dos dias da semana e meses
dias_semana_ordem = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# --- CSS Customizado para App-Like --- #
def inject_custom_css():
    st.markdown("""
    <style>
        /* Remove Streamlit header/footer */
        /* Note: This might be fragile and break with Streamlit updates */
        #MainMenu {visibility: hidden;} /* Hide hamburger menu */
        footer {visibility: hidden;} /* Hide "Made with Streamlit" footer */
        header {visibility: hidden;} /* Hide Streamlit's default header */

        /* Body/App Background */
        .stApp {
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
            color: #e0e0e0; /* Light text color for dark background */
        }

        /* Main content padding */
        .main .block-container {
            padding-top: 2rem; /* Adjust top padding */
            padding-bottom: 2rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
        }

        /* Sidebar styling */
        .stSidebar {
            background-color: rgba(26, 26, 46, 0.8); /* Slightly transparent dark background */
        }

        /* Input field styling */
        .stSelectbox label, .stNumberInput label, .stDateInput label {
            font-weight: bold;
            color: #a0a0e0; /* Lighter color for labels */
        }
        .stNumberInput input::placeholder {
            color: #888;
            font-style: italic;
        }

        /* Button styling */
        .stButton > button {
            height: 3rem;
            font-size: 1.2rem;
            font-weight: bold;
            width: 100%;
            border-radius: 0.5rem;
            background-color: #4c78a8;
            color: white;
            border: none;
        }
        .stButton > button:hover {
            background-color: #5a8bb8;
        }

        /* Metric card styling */
        .stMetric {
            background-color: rgba(255, 255, 255, 0.08); /* Slightly more visible background */
            padding: 1.2rem;
            border-radius: 0.75rem;
            margin-bottom: 1rem;
            min-height: 130px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }
        .stMetric > label {
            color: #b0b0d0; /* Lighter label color */
            font-size: 1rem;
        }
        .stMetric > div[data-testid="stMetricValue"] {
            color: #ffffff; /* White value */
            font-size: 1.8rem;
            font-weight: bold;
        }
        .stMetric > div[data-testid="stMetricDelta"] {
            font-size: 0.9rem;
        }

        /* Payment summary card styling */
        .payment-card {
            text-align: center;
            padding: 1rem;
            border-radius: 10px;
            color: white;
            margin-bottom: 1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .payment-card h3 {
            margin: 0; font-size: 1.5rem;
        }
        .payment-card h2 {
            margin: 0.5rem 0; font-size: 1.8rem; font-weight: bold;
        }
        .payment-card p {
            margin: 0; font-size: 1.2rem; opacity: 0.9;
        }

        /* Chart container styling */
        .chart-container {
            background-color: rgba(255, 255, 255, 0.05);
            padding: 1.5rem;
            border-radius: 0.75rem;
            margin-top: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* Title styling */
        .title-main {
            margin: 0; padding: 0; line-height: 1.2; color: #ffffff;
        }
        .title-sub {
            margin: 0; font-size: 14px; color: #a0a0b0; padding: 0; line-height: 1.2;
        }
        .logo-container {
            display: flex;
            align-items: center;
            margin-bottom: 2rem; /* More space below logo/title */
        }
        .logo-image {
            width: 60px; /* Smaller logo */
            height: auto;
            margin-right: 15px;
            border-radius: 5px;
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .stMetric {
                min-height: 110px;
            }
            .stMetric > div[data-testid="stMetricValue"] {
                font-size: 1.5rem;
            }
            .payment-card h2 {
                font-size: 1.5rem;
            }
            .payment-card p {
                font-size: 1rem;
            }
            .logo-container {
                flex-direction: column;
                align-items: flex-start;
            }
            .logo-image {
                margin-bottom: 10px;
            }
        }

    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- Funções de Cache para Acesso ao Google Sheets (sem alterações) ---
@st.cache_resource
def get_google_auth():
    """Autoriza o acesso ao Google Sheets e retorna o cliente gspread."""
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/spreadsheets.readonly",
              "https://www.googleapis.com/auth/drive.readonly"]
    try:
        # Tenta carregar do st.secrets primeiro
        if "google_credentials" in st.secrets:
            credentials_dict = st.secrets["google_credentials"]
            if credentials_dict:
                creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
                gc = gspread.authorize(creds)
                return gc
            else:
                st.warning("Credenciais do Google em st.secrets estão vazias. Tentando carregar de 'credentials.json'.")
        
        # Fallback para arquivo local (útil para desenvolvimento local)
        try:
            creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
            gc = gspread.authorize(creds)
            st.info("Credenciais carregadas de 'credentials.json'.")
            return gc
        except FileNotFoundError:
            st.error("Erro: Arquivo 'credentials.json' não encontrado E credenciais não configuradas em st.secrets.")
            st.info("Para configurar: 1) Crie um arquivo .streamlit/secrets.toml com suas credenciais do Google OU 2) Coloque o arquivo credentials.json na raiz do projeto.")
            return None
        except Exception as e_file:
            st.error(f"Erro ao carregar 'credentials.json': {e_file}")
            return None

    except Exception as e_auth:
        st.error(f"Erro geral de autenticação com Google: {e_auth}")
        return None

@st.cache_resource
def get_worksheet(_gc): # Passa o cliente autorizado
    """Retorna o objeto worksheet da planilha especificada."""
    # gc = get_google_auth() # Não chama mais aqui para evitar loop
    if _gc:
        try:
            spreadsheet = _gc.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
            return worksheet
        except SpreadsheetNotFound:
            st.error(f"Planilha com ID '{SPREADSHEET_ID}' não encontrada.")
            return None
        except Exception as e:
            st.error(f"Erro ao acessar a planilha '{WORKSHEET_NAME}': {e}")
            return None
    return None

# Modificado para aceitar o worksheet como argumento
@st.cache_data
def read_sales_data(_worksheet):
    """Lê todos os registros da planilha de vendas e retorna como DataFrame."""
    # worksheet = get_worksheet() # Não chama mais aqui
    if _worksheet:
        try:
            rows = _worksheet.get_all_records()
            if not rows:
                # st.info("A planilha de vendas está vazia.") # Removido info daqui
                return pd.DataFrame()

            df = pd.DataFrame(rows)

            for col in ["Cartão", "Dinheiro", "Pix"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    df[col] = 0

            if "Data" not in df.columns:
                df["Data"] = pd.NaT
            else:
                 # Tentativa robusta de converter Data
                try:
                    # Tenta formato brasileiro primeiro
                    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
                    # Se falhar, tenta formato padrão
                    if df['Data'].isnull().any():
                        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
                except Exception:
                     df['Data'] = pd.to_datetime(df['Data'], errors='coerce')

            return df
        except Exception as e:
            st.error(f"Erro ao ler dados da planilha: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- Funções de Manipulação de Dados (sem alterações) ---
def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet_obj):
    """Adiciona uma nova linha de dados à planilha Google Sheets."""
    if worksheet_obj is None:
        st.error("Não foi possível acessar a planilha para adicionar dados.")
        return False
    try:
        cartao_val = float(cartao) if cartao else 0.0
        dinheiro_val = float(dinheiro) if dinheiro else 0.0
        pix_val = float(pix) if pix else 0.0

        new_row = [date, cartao_val, dinheiro_val, pix_val]
        worksheet_obj.append_row(new_row)
        # st.success("Dados registrados com sucesso! ✅") # Sucesso será mostrado no main
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
    if df_input is None or df_input.empty:
        # Retorna um DataFrame vazio com a estrutura esperada
        cols = ["Data", "Cartão", "Dinheiro", "Pix", "Total", "Ano", "Mês", "MêsNome", "AnoMês", "DataFormatada", "DiaSemana", "DiaDoMes"]
        empty_df = pd.DataFrame(columns=cols)
        # Definir tipos de dados para evitar problemas posteriores
        empty_df["Data"] = pd.to_datetime(empty_df["Data"])
        for col in ["Cartão", "Dinheiro", "Pix", "Total", "Ano", "Mês", "DiaDoMes"]:
             empty_df[col] = pd.to_numeric(empty_df[col])
        return empty_df

    df = df_input.copy()

    # Garantir colunas numéricas e preencher NaNs
    for col in ["Cartão", "Dinheiro", "Pix"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    df["Total"] = df["Cartão"] + df["Dinheiro"] + df["Pix"]

    # Processamento robusto da coluna 'Data'
    if "Data" in df.columns:
        # Tenta converter para datetime, lidando com diferentes formatos possíveis
        try:
            # Tenta formato brasileiro primeiro
            df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
            # Se muitos NaNs, tenta formato padrão
            if df['Data'].isnull().sum() > len(df) / 2:
                 original_data = df_input['Data'].copy()
                 df['Data'] = pd.to_datetime(original_data, errors='coerce')
        except Exception:
             df['Data'] = pd.to_datetime(df['Data'], errors='coerce')

        df.dropna(subset=["Data"], inplace=True) # Remove linhas onde a data não pôde ser convertida

        if not df.empty:
            df["Ano"] = df["Data"].dt.year
            df["Mês"] = df["Data"].dt.month
            df["MêsNome"] = df["Mês"].apply(lambda x: meses_ordem[int(x)-1] if pd.notna(x) and 1 <= int(x) <= 12 else "Inválido")
            df["AnoMês"] = df["Data"].dt.strftime("%Y-%m")
            df["DataFormatada"] = df["Data"].dt.strftime("%d/%m/%Y")
            day_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
            df["DiaSemana"] = df["Data"].dt.dayofweek.map(day_map)
            df["DiaDoMes"] = df["Data"].dt.day

            # Define DiaSemana como categórico ordenado
            df["DiaSemana"] = pd.Categorical(df["DiaSemana"], categories=[d for d in dias_semana_ordem if d in df["DiaSemana"].unique()], ordered=True)
        else:
            # Se o DataFrame ficou vazio após tratar datas, retorna estrutura vazia
            return process_data(pd.DataFrame()) # Chama recursivamente com df vazio
    else:
        st.warning("Coluna 'Data' não encontrada. Análises temporais podem ser afetadas.")
        # Adiciona colunas de data vazias se 'Data' não existir
        for col in ["Ano", "Mês", "MêsNome", "AnoMês", "DataFormatada", "DiaSemana", "DiaDoMes"]:
            df[col] = pd.NA
        df["Data"] = pd.NaT

    return df

# --- Funções de Gráficos Interativos em Altair (com ajuste de altura) ---

def create_cumulative_area_chart(df):
    """Cria gráfico de área ACUMULADO com gradiente e altura ajustada."""
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        # st.warning("Dados insuficientes para gráfico acumulado.")
        return None

    df_copy = df.copy()
    try:
        df_copy["Data"] = pd.to_datetime(df_copy["Data"])
    except Exception:
        return None # Falha na conversão da data

    df_sorted = df_copy.sort_values("Data")
    if df_sorted.empty:
        return None

    df_sorted["Total_Acumulado"] = df_sorted["Total"].cumsum()

    area_chart = alt.Chart(df_sorted).mark_area(
        interpolate="monotone",
        line={"color": CORES_MODO_ESCURO[0], "strokeWidth": 2},
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color=CORES_MODO_ESCURO[0], offset=0),
                alt.GradientStop(color=CORES_MODO_ESCURO[4], offset=1)
            ],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X("Data:T", axis=alt.Axis(format="%d/%m", labelAngle=-45, labelFontSize=12, title=None)),
        y=alt.Y("Total_Acumulado:Q", axis=alt.Axis(labelFontSize=12, title="Acumulado (R$)")),
        tooltip=[
            alt.Tooltip("Data:T", title="Data", format="%d/%m/%Y"),
            alt.Tooltip("Total:Q", title="Venda Dia (R$)", format=",.2f"),
            alt.Tooltip("Total_Acumulado:Q", title="Acumulado (R$)", format=",.2f")
        ]
    ).properties(
        height=700, # Altura mínima definida
        title=alt.TitleParams("Evolução do Faturamento Acumulado", anchor="start", fontSize=16, dy=-10)
    ).configure_view(stroke=None).configure(background="transparent")

    return area_chart

def create_advanced_daily_sales_chart(df):
    """Cria um gráfico de vendas diárias com altura ajustada."""
    if df.empty or "Data" not in df.columns:
        # st.warning("Dados insuficientes para gráfico diário.")
        return None

    df_sorted = df.sort_values("Data").copy()
    if df_sorted.empty:
        return None

    df_melted = df_sorted.melt(
        id_vars=["Data", "DataFormatada", "Total"],
        value_vars=["Cartão", "Dinheiro", "Pix"],
        var_name="Método",
        value_name="Valor"
    )
    df_melted = df_melted[df_melted["Valor"] > 0]
    if df_melted.empty:
        return None

    bars = alt.Chart(df_melted).mark_bar(
        size=20,
        stroke="white",
        strokeWidth=1 # Borda mais fina
    ).encode(
        x=alt.X("Data:T", axis=alt.Axis(format="%d/%m", labelAngle=-45, labelFontSize=12, title=None)),
        y=alt.Y("Valor:Q", title="Valor (R$)", stack="zero", axis=alt.Axis(labelFontSize=12)),
        color=alt.Color("Método:N", scale=alt.Scale(range=CORES_MODO_ESCURO[:3]), legend=alt.Legend(title="Método", orient="top")),
        tooltip=[
            alt.Tooltip("DataFormatada:N", title="Data"),
            alt.Tooltip("Método:N", title="Método"),
            alt.Tooltip("Valor:Q", title="Valor (R$)", format=",.2f")
        ]
    ).properties(
        height=700, # Altura mínima definida
        title=alt.TitleParams("Vendas Diárias por Método de Pagamento", anchor="start", fontSize=16, dy=-10)
    ).configure_view(stroke=None).configure(background="transparent")

    return bars

# --- Funções de Análise e Financeiras (sem alterações na lógica interna) ---
# ... (create_radial_plot, create_enhanced_weekday_analysis, create_sales_histogram, analyze_sales_by_weekday, calculate_financial_results, create_dre_textual, create_financial_dashboard_altair, create_premium_kpi_cards, create_activity_heatmap) ...
# Nota: As funções de gráfico chamadas DENTRO destas podem precisar ter a altura ajustada se forem usadas no dashboard principal.
# Por exemplo, create_radial_plot não está no dashboard principal, então não precisa de ajuste de altura aqui.

# Função para formatar valores em moeda brasileira (sem alterações)
def format_brl(value):
    if value is None or not isinstance(value, (int, float)):
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

# --- Interface Principal Refatorada para Dashboard --- #
def main():
    # --- Conexão Inicial --- #
    gc = get_google_auth()
    worksheet = get_worksheet(gc) if gc else None
    df_raw = read_sales_data(worksheet) if worksheet else pd.DataFrame()
    df_processed = process_data(df_raw)

    # --- Sidebar para Filtros e Registro --- #
    with st.sidebar:
        st.image(LOGO_URL, width=80)
        st.header("Filtros")
        st.markdown("---")

        selected_anos_filter, selected_meses_filter = [], []
        if not df_processed.empty and "Ano" in df_processed.columns and not df_processed["Ano"].isnull().all():
            anos_disponiveis = sorted(df_processed["Ano"].dropna().unique().astype(int), reverse=True)
            if anos_disponiveis:
                default_ano = [datetime.now().year] if datetime.now().year in anos_disponiveis else ([anos_disponiveis[0]] if anos_disponiveis else [])
                selected_anos_filter = st.multiselect("Ano(s):", options=anos_disponiveis, default=default_ano)

                if selected_anos_filter:
                    df_para_filtro_mes = df_processed[df_processed["Ano"].isin(selected_anos_filter)]
                    if not df_para_filtro_mes.empty and "Mês" in df_para_filtro_mes.columns and not df_para_filtro_mes["Mês"].isnull().all():
                        meses_numeros_disponiveis = sorted(df_para_filtro_mes["Mês"].dropna().unique().astype(int))
                        meses_opcoes_dict = {m_num: meses_ordem[m_num-1] for m_num in meses_numeros_disponiveis if 1 <= m_num <= 12}
                        meses_opcoes_display = [f"{m_num} - {m_nome}" for m_num, m_nome in meses_opcoes_dict.items()]

                        default_meses_selecionados = meses_opcoes_display # Seleciona todos por padrão
                        ano_atual = datetime.now().year
                        mes_atual = datetime.now().month
                        if ano_atual in selected_anos_filter:
                             mes_atual_str = f"{mes_atual} - {meses_ordem[mes_atual-1]}"
                             if mes_atual_str in meses_opcoes_display:
                                 default_meses_selecionados = [mes_atual_str]
                             # Se o mês atual não tem dados, ainda assim o oferece como opção
                             elif f"{mes_atual} - {meses_ordem[mes_atual-1]}" not in meses_opcoes_display:
                                  meses_opcoes_display.append(f"{mes_atual} - {meses_ordem[mes_atual-1]}")
                                  meses_opcoes_display = sorted(meses_opcoes_display, key=lambda x: int(x.split(" - ")[0]))
                                  default_meses_selecionados = [f"{mes_atual} - {meses_ordem[mes_atual-1]}"]

                        selected_meses_str = st.multiselect("Mês(es):", options=meses_opcoes_display, default=default_meses_selecionados)
                        selected_meses_filter = [int(m.split(" - ")[0]) for m in selected_meses_str]
            else:
                st.info("Nenhum ano disponível.")
        else:
            st.info("Carregando dados ou planilha vazia...")

        st.markdown("---")
        st.header("Registrar Venda")
        data_input = st.date_input("Data", value=datetime.now(), format="DD/MM/YYYY", key="reg_data")
        cartao_input = st.number_input("Cartão (R$)", min_value=0.0, value=None, format="%.2f", key="reg_cartao", placeholder="0.00")
        dinheiro_input = st.number_input("Dinheiro (R$)", min_value=0.0, value=None, format="%.2f", key="reg_dinheiro", placeholder="0.00")
        pix_input = st.number_input("PIX (R$)", min_value=0.0, value=None, format="%.2f", key="reg_pix", placeholder="0.00")

        cartao_val = cartao_input if cartao_input is not None else 0.0
        dinheiro_val = dinheiro_input if dinheiro_input is not None else 0.0
        pix_val = pix_input if pix_input is not None else 0.0
        total_venda_form = cartao_val + dinheiro_val + pix_val

        st.markdown(f"**Total: {format_brl(total_venda_form)}**")

        if st.button("✅ Registrar", type="primary", use_container_width=True):
            if total_venda_form > 0:
                formatted_date = data_input.strftime("%d/%m/%Y")
                if worksheet and add_data_to_sheet(formatted_date, cartao_val, dinheiro_val, pix_val, worksheet):
                    st.success("Venda registrada!")
                    # Limpar caches para forçar recarregamento
                    read_sales_data.clear()
                    process_data.clear()
                    st.rerun() # Recarrega a página para mostrar dados atualizados
                elif not worksheet:
                    st.error("Falha ao conectar à planilha.")
            else:
                st.warning("Valor total deve ser maior que zero.")

    # --- Aplicação dos Filtros --- #
    df_filtered = df_processed.copy()
    if not df_filtered.empty:
        if selected_anos_filter and "Ano" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Ano"].isin(selected_anos_filter)]
        if selected_meses_filter and "Mês" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Mês"].isin(selected_meses_filter)]

    # --- Layout Principal do Dashboard --- #

    # Cabeçalho
    st.markdown(f"""
    <div class="logo-container">
        <img src="{LOGO_URL}" class="logo-image" alt="Clips Burger Logo">
        <div>
            <h1 class="title-main">CLIP'S BURGER DASHBOARD</h1>
            <p class="title-sub">Análise de Vendas - {datetime.now().strftime('%d/%m/%Y')}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if df_filtered.empty:
        st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados. Ajuste os filtros na barra lateral ou registre novas vendas.")
    else:
        # KPIs Principais
        st.subheader("🚀 Indicadores Principais")
        total_vendas = df_filtered["Total"].sum()
        media_diaria = df_filtered["Total"].mean()
        melhor_dia_valor = df_filtered["Total"].max()
        melhor_dia_data = df_filtered.loc[df_filtered["Total"].idxmax(), "DataFormatada"] if not df_filtered.empty and "DataFormatada" in df_filtered.columns else "N/A"

        kpi_cols = st.columns(3)
        with kpi_cols[0]:
            st.metric(label="💰 Faturamento Total", value=format_brl(total_vendas))
        with kpi_cols[1]:
            st.metric(label="📊 Média Diária", value=format_brl(media_diaria))
        with kpi_cols[2]:
            st.metric(label=f"🏆 Melhor Dia ({melhor_dia_data})", value=format_brl(melhor_dia_valor))

        st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)

        # Resumo de Pagamentos
        st.subheader("💳 Resumo por Método de Pagamento")
        cartao_total = df_filtered["Cartão"].sum()
        dinheiro_total = df_filtered["Dinheiro"].sum()
        pix_total = df_filtered["Pix"].sum()
        total_pagamentos_geral = cartao_total + dinheiro_total + pix_total

        if total_pagamentos_geral > 0:
            cartao_pct = (cartao_total / total_pagamentos_geral * 100)
            dinheiro_pct = (dinheiro_total / total_pagamentos_geral * 100)
            pix_pct = (pix_total / total_pagamentos_geral * 100)

            payment_cols = st.columns(3)
            with payment_cols[0]:
                st.markdown(f"""
                <div class="payment-card" style="background: linear-gradient(135deg, #4c78a8, #5a8bb8);">
                    <h3>💳 Cartão</h3>
                    <h2>{format_brl(cartao_total)}</h2>
                    <p>{cartao_pct:.1f}%</p>
                </div>
                """, unsafe_allow_html=True)
            with payment_cols[1]:
                st.markdown(f"""
                <div class="payment-card" style="background: linear-gradient(135deg, #54a24b, #64b25b);">
                    <h3>💵 Dinheiro</h3>
                    <h2>{format_brl(dinheiro_total)}</h2>
                    <p>{dinheiro_pct:.1f}%</p>
                </div>
                """, unsafe_allow_html=True)
            with payment_cols[2]:
                st.markdown(f"""
                <div class="payment-card" style="background: linear-gradient(135deg, #f58518, #ff9528);">
                    <h3>📱 PIX</h3>
                    <h2>{format_brl(pix_total)}</h2>
                    <p>{pix_pct:.1f}%</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Sem dados de pagamento para o período.")

        # Gráficos Principais
        st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)
        st.subheader("📈 Gráficos de Vendas")

        with st.container(): # Usar container para agrupar os gráficos
            # Gráfico Acumulado
            with st.container(border=True):
                cumulative_chart = create_cumulative_area_chart(df_filtered)
                if cumulative_chart:
                    st.altair_chart(cumulative_chart, use_container_width=True)
                else:
                    st.info("Gráfico de evolução acumulada indisponível para o período.")

            # Gráfico Diário
            with st.container(border=True):
                daily_chart = create_advanced_daily_sales_chart(df_filtered)
                if daily_chart:
                    st.altair_chart(daily_chart, use_container_width=True)
                else:
                    st.info("Gráfico de vendas diárias indisponível para o período.")

    # Adicionar link para o manifest (melhor prática é configurar no servidor web, mas isso ajuda)
    # st.markdown('<link rel="manifest" href="/app/static/manifest.json">', unsafe_allow_html=True)
    # Nota: Streamlit Cloud e Community Cloud podem não servir o manifest.json corretamente desta forma.
    # A melhor abordagem é configurar o PWA durante o deploy (ex: Nginx, Docker). Apenas fornecer o manifest.json.

# --- Ponto de Entrada da Aplicação --- #
if __name__ == "__main__":
    main()

