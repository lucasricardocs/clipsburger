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
import plotly.graph_objects as go # Importar plotly
import calendar # Importar calendar

# Suprimir warnings específicos do pandas
warnings.filterwarnings("ignore", category=FutureWarning, message=".*observed=False.*")

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = "1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg"
WORKSHEET_NAME = "Vendas"
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/clipsburger/main/logo.png" # URL da logo

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema Financeiro - Clips Burger", layout="wide", page_icon="🍔")

# Configuração de tema para gráficos mais bonitos
alt.data_transformers.enable("json")

# Paleta de cores otimizada para modo escuro
CORES_MODO_ESCURO = ["#4c78a8", "#54a24b", "#f58518", "#e45756", "#72b7b2", "#ff9da6", "#9d755d", "#bab0ac"]
COR_TEXTO_PRINCIPAL = "#ffffff"
COR_TEXTO_SECUNDARIO = "#b0bec5"
COR_SEPARADOR = "#455a64"

# Define a ordem correta dos dias da semana e meses
dias_semana_ordem = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# CSS para melhorar a aparência (Incluindo Logo com Aura Branca/Azul e Rodapé)
def inject_css():
    st.markdown(f"""
    <style>
    /* Estilos Gerais do Código Original */
    .stSelectbox label, .stNumberInput label {{
        font-weight: bold;
        color: #4c78a8;
    }}
    
    .stNumberInput input::placeholder {{
        color: #888;
        font-style: italic;
    }}
    
    .stButton > button {{
        height: 3rem;
        font-size: 1.2rem;
        font-weight: bold;
        width: 100%;
    }}
    
    .element-container {{
        margin-bottom: 0.5rem;
    }}
    
    .stMetric {{
        background-color: rgba(255, 255, 255, 0.05);
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}
    
    .stApp {{
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
        color: {COR_TEXTO_PRINCIPAL}; /* Adicionado para texto branco geral */
    }}
    
    .premium-charts-grid {{
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 2rem;
        margin: 2rem 0;
    }}
    
    .premium-chart-full {{
        grid-column: 1 / -1;
        margin: 2rem 0;
    }}

    /* Estilos para Logo Grande com Aura Branca/Azul Celestial */
    .sidebar .stImage {{
        text-align: center; /* Centraliza a imagem no sidebar */
        margin-bottom: 1rem;
    }}
    .logo-sidebar-image {{
        width: 230px; /* Tamanho grande para a logo */
        height: auto;
        animation: celestialPulseSidebar 5s ease-in-out infinite;
    }}

    @keyframes celestialPulseSidebar {{
        0%, 100% {{
            filter: drop-shadow(0 0 12px rgba(255, 255, 255, 0.7)) drop-shadow(0 0 25px rgba(255, 255, 255, 0.5)); /* Branco */
        }}
        50% {{
            filter: drop-shadow(0 0 15px rgba(135, 206, 250, 0.8)) drop-shadow(0 0 30px rgba(135, 206, 250, 0.6)); /* Azul Celestial (LightSkyBlue) */
        }}
    }}

    /* --- Rodapé --- ADICIONADO */
    .footer {{
        margin-top: 3rem;
        padding: 1.5rem 0;
        border-top: 1px solid {COR_SEPARADOR};
        text-align: center;
        font-size: 0.9rem;
        color: {COR_TEXTO_SECUNDARIO};
    }}
    .footer a {{
        color: {CORES_MODO_ESCURO[0]}; /* Cor primária da paleta */
        text-decoration: none;
        transition: color 0.3s ease;
    }}
    .footer a:hover {{
        color: {CORES_MODO_ESCURO[1]}; /* Cor secundária no hover */
        text-decoration: underline;
    }}

    /* Outros estilos necessários */
    h1, h2, h3, h4, h5, h6 {{
        color: {COR_TEXTO_PRINCIPAL};
    }}
    hr {{
        border-top: 1px solid {COR_SEPARADOR};
    }}

    </style>
    """, unsafe_allow_html=True)

inject_css()

# --- Funções de Cache para Acesso ao Google Sheets (Original) ---
@st.cache_resource
def get_google_auth():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/spreadsheets.readonly",
              "https://www.googleapis.com/auth/drive.readonly"]
    try:
        if "google_credentials" not in st.secrets:
            st.error("Credenciais do Google ('google_credentials') não encontradas em st.secrets.")
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

@st.cache_data
def read_sales_data():
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records()
            if not rows:
                st.info("A planilha de vendas está vazia.")
                # Retornar DataFrame vazio com colunas esperadas
                return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix"])

            df = pd.DataFrame(rows)
            
            for col in ["Cartão", "Dinheiro", "Pix"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    df[col] = 0
            
            if "Data" not in df.columns:
                 st.warning("Coluna 'Data' não encontrada. Criando coluna vazia.")
                 df["Data"] = pd.NaT
            else:
                 # Tentar converter Data para datetime
                 try:
                     df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
                 except ValueError:
                     df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
                 df.dropna(subset=["Data"], inplace=True)

            # Calcular Total
            df["Total"] = df["Cartão"] + df["Dinheiro"] + df["Pix"]
            return df
        except Exception as e:
            st.error(f"Erro ao ler dados da planilha: {e}")
            return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix", "Total"])
    return pd.DataFrame(columns=["Data", "Cartão", "Dinheiro", "Pix", "Total"])

# --- Funções de Manipulação de Dados (Original) ---
def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet_obj):
    if worksheet_obj is None:
        st.error("Não foi possível acessar a planilha para adicionar dados.")
        return False
    try:
        cartao_val = float(cartao) if cartao else 0.0
        dinheiro_val = float(dinheiro) if dinheiro else 0.0
        pix_val = float(pix) if pix else 0.0
        # Formatar data para string DD/MM/YYYY
        formatted_date_str = date.strftime("%d/%m/%Y")
        new_row = [formatted_date_str, cartao_val, dinheiro_val, pix_val]
        worksheet_obj.append_row(new_row)
        st.cache_data.clear() # Limpar cache após adicionar
        st.success("Dados registrados com sucesso! ✅")
        return True
    except ValueError as ve:
        st.error(f"Erro ao converter valores para número: {ve}.")
        return False
    except Exception as e:
        st.error(f"Erro ao adicionar dados na planilha: {e}")
        return False

@st.cache_data
def process_data(df_input):
    df = df_input.copy()
    
    cols_to_ensure_numeric = ["Cartão", "Dinheiro", "Pix", "Total"]
    cols_to_ensure_date_derived = ["Ano", "Mês", "MêsNome", "AnoMês", "DataFormatada", "DiaSemana", "DiaDoMes"]
    
    if df.empty:
        all_expected_cols = ["Data"] + cols_to_ensure_numeric + cols_to_ensure_date_derived
        empty_df = pd.DataFrame(columns=all_expected_cols)
        for col in cols_to_ensure_numeric:
            empty_df[col] = pd.Series(dtype="float")
        for col in cols_to_ensure_date_derived:
            empty_df[col] = pd.Series(dtype="object" if col in ["MêsNome", "AnoMês", "DataFormatada", "DiaSemana"] else "float")
        empty_df["Data"] = pd.Series(dtype="datetime64[ns]")
        return empty_df

    for col in ["Cartão", "Dinheiro", "Pix"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    if "Total" not in df.columns:
        df["Total"] = df["Cartão"] + df["Dinheiro"] + df["Pix"]

    if "Data" in df.columns and not df["Data"].isnull().all():
        try:
            if not pd.api.types.is_datetime64_any_dtype(df["Data"]):
                 try:
                     df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
                 except ValueError:
                     df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
            
            df.dropna(subset=["Data"], inplace=True)

            if not df.empty:
                df["Ano"] = df["Data"].dt.year
                df["Mês"] = df["Data"].dt.month
                df["MêsNome"] = df["Mês"].map(lambda x: meses_ordem[int(x)-1] if pd.notna(x) and 1 <= int(x) <= 12 else "Inválido")
                df["AnoMês"] = df["Data"].dt.strftime("%Y-%m")
                df["DataFormatada"] = df["Data"].dt.strftime("%d/%m/%Y")
                day_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
                df["DiaSemana"] = df["Data"].dt.dayofweek.map(day_map)
                df["DiaDoMes"] = df["Data"].dt.day

                if "DiaSemana" in df.columns and not df["DiaSemana"].empty:
                     df["DiaSemana"] = pd.Categorical(df["DiaSemana"], categories=dias_semana_ordem, ordered=True)
                if "MêsNome" in df.columns and not df["MêsNome"].empty:
                     df["MêsNome"] = pd.Categorical(df["MêsNome"], categories=meses_ordem, ordered=True)
            else:
                for col in cols_to_ensure_date_derived:
                    df[col] = pd.Series(dtype="object" if col in ["MêsNome", "AnoMês", "DataFormatada", "DiaSemana"] else "float")
        except Exception as e:
            st.error(f"Erro ao processar coluna 'Data': {e}.")
            for col in cols_to_ensure_date_derived:
                df[col] = pd.Series(dtype="object" if col in ["MêsNome", "AnoMês", "DataFormatada", "DiaSemana"] else "float")
    else:
        if "Data" not in df.columns:
            df["Data"] = pd.NaT
        for col in cols_to_ensure_date_derived:
            df[col] = pd.Series(dtype="object" if col in ["MêsNome", "AnoMês", "DataFormatada", "DiaSemana"] else "float")
            
    return df

# --- Funções de Formatação ---
def format_brl(value):
    try:
        if pd.isna(value) or np.isinf(value):
            return "R$ -"
        return f"R$ {value:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")
    except (ValueError, TypeError):
        return "R$ -"

# --- Funções de Gráficos Interativos em Altair (Original) ---
def create_radial_plot(df):
    if df.empty or not any(col in df.columns for col in ["Cartão", "Dinheiro", "Pix"]):
        return alt.Chart(pd.DataFrame({"A": []})).mark_text(text="Dados insuficientes").properties(height=500)
    payment_data = pd.DataFrame({
        "Método": ["Cartão", "Dinheiro", "PIX"],
        "Valor": [df["Cartão"].sum(), df["Dinheiro"].sum(), df["Pix"].sum()]
    })
    payment_data = payment_data[payment_data["Valor"] > 0]
    if payment_data.empty:
        return alt.Chart(pd.DataFrame({"A": []})).mark_text(text="Sem dados de pagamento").properties(height=500)
    base = alt.Chart(payment_data).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        radius=alt.Radius("Valor:Q", scale=alt.Scale(type="sqrt", zero=True, rangeMin=20)),
        color=alt.Color("Método:N", scale=alt.Scale(range=CORES_MODO_ESCURO[:len(payment_data)])),
        order=alt.Order("Valor:Q", sort="descending"),
        tooltip=["Método:N", alt.Tooltip("Valor:Q", format=",.2f")]
    )
    radial_plot = base.mark_arc(innerRadius=20, stroke="#fff", strokeWidth=1).properties(height=500)
    return radial_plot

def create_area_chart_with_gradient(df):
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        return alt.Chart(pd.DataFrame({"A": []})).mark_text(text="Dados insuficientes").properties(height=500)
    df_sorted = df.sort_values("Data").copy()
    if df_sorted.empty:
        return alt.Chart(pd.DataFrame({"A": []})).mark_text(text="Sem dados para evolução").properties(height=500)
    area_chart = alt.Chart(df_sorted).mark_area(
        interpolate="monotone",
        line={"color": CORES_MODO_ESCURO[0]},
        color=alt.Gradient(
            gradient="linear",
            stops=[alt.GradientStop(color="white", offset=0), alt.GradientStop(color=CORES_MODO_ESCURO[0], offset=1)],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X("Data:T", title="Data", axis=alt.Axis(format="%d/%m")),
        y=alt.Y("Total:Q", title="Total Vendas (R$)"),
        tooltip=["DataFormatada:N", alt.Tooltip("Total:Q", format=",.2f")]
    ).properties(height=500)
    return area_chart

def create_advanced_daily_sales_chart(df):
    if df.empty or "Data" not in df.columns:
        return alt.Chart(pd.DataFrame({"A": []})).mark_text(text="Dados insuficientes").properties(height=500)
    df_sorted = df.sort_values("Data").copy()
    if df_sorted.empty:
        return alt.Chart(pd.DataFrame({"A": []})).mark_text(text="Sem dados de vendas diárias").properties(height=500)
    df_melted = df_sorted.melt(id_vars=["Data", "DataFormatada", "Total"], value_vars=["Cartão", "Dinheiro", "Pix"], var_name="Método", value_name="Valor")
    df_melted = df_melted[df_melted["Valor"] > 0]
    if df_melted.empty:
        return alt.Chart(pd.DataFrame({"A": []})).mark_text(text="Sem vendas registradas").properties(height=500)
    bars = alt.Chart(df_melted).mark_bar().encode(
        x=alt.X("Data:T", title="Data", axis=alt.Axis(format="%d/%m")),
        y=alt.Y("Valor:Q", title="Valor (R$)", stack="zero"),
        color=alt.Color("Método:N", scale=alt.Scale(range=CORES_MODO_ESCURO[:3])),
        tooltip=["DataFormatada:N", "Método:N", alt.Tooltip("Valor:Q", format=",.2f")]
    ).properties(height=500)
    return bars

def create_enhanced_weekday_analysis(df):
    if df.empty or "DiaSemana" not in df.columns or "Total" not in df.columns:
        return None, None
    df_copy = df.copy()
    df_copy["Total"] = pd.to_numeric(df_copy["Total"], errors="coerce")
    df_copy.dropna(subset=["Total", "DiaSemana"], inplace=True)
    if df_copy.empty:
        return None, None
    weekday_stats = df_copy.groupby("DiaSemana", observed=True).agg({"Total": ["mean", "sum", "count"]}).round(2)
    weekday_stats.columns = ["Média", "Total", "Dias_Vendas"]
    # Reindexar para garantir a ordem correta e incluir dias sem vendas
    weekday_stats = weekday_stats.reindex(dias_semana_ordem, fill_value=0)
    weekday_stats.reset_index(inplace=True)
    
    chart = alt.Chart(weekday_stats).mark_bar().encode(
        x=alt.X("DiaSemana:O", title="Dia da Semana", sort=dias_semana_ordem),
        y=alt.Y("Média:Q", title="Média de Vendas (R$)"),
        color=alt.Color("DiaSemana:N", legend=None, scale=alt.Scale(range=CORES_MODO_ESCURO)),
        tooltip=["DiaSemana:O", alt.Tooltip("Média:Q", format=",.2f"), "Total:Q", "Dias_Vendas:Q"]
    ).properties(height=500)
    return chart, weekday_stats

# --- Funções Heatmap Plotly (ADICIONADAS) ---
def criar_calendario_anual_heatmap(df, ano):
    empty_fig = go.Figure().update_layout(height=300, title=f"Sem dados para o calendário de {ano}", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=COR_TEXTO_PRINCIPAL)
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        return empty_fig

    df_ano = df[df["Data"].dt.year == ano].copy()
    if df_ano.empty:
        return empty_fig

    dates_completo = pd.date_range(f"{ano}-01-01", f"{ano}-12-31", freq="D")
    df_ano_completo = pd.DataFrame(index=dates_completo)

    vendas_diarias = df_ano.groupby(df_ano["Data"].dt.date)["Total"].sum()
    vendas_diarias.index = pd.to_datetime(vendas_diarias.index)

    df_ano_completo["Total_Vendas"] = df_ano_completo.index.map(vendas_diarias).fillna(0)
    # Adicionar detalhes para hover se existirem colunas
    for col in ["Cartão", "Dinheiro", "Pix"]:
         if col in df_ano.columns:
             df_ano_completo[col] = df_ano_completo.index.map(df_ano.set_index("Data")[col]).fillna(0)
         else:
             df_ano_completo[col] = 0

    df_ano_completo["Data"] = df_ano_completo.index
    df_ano_completo["data_str"] = df_ano_completo["Data"].dt.strftime("%d/%m/%Y")
    df_ano_completo["dia_semana"] = df_ano_completo["Data"].dt.dayofweek

    primeiro_dia = datetime(ano, 1, 1).date()
    primeiro_dia_semana = primeiro_dia.weekday()

    x_positions, y_positions, valores, hover_texts = [], [], [], []

    for _, row in df_ano_completo.iterrows():
        dias_desde_inicio = (row["Data"].date() - primeiro_dia).days
        semana = (dias_desde_inicio + primeiro_dia_semana) // 7
        dia_semana = (dias_desde_inicio + primeiro_dia_semana) % 7
        x_positions.append(semana)
        y_positions.append(dia_semana)

        total_vendas = row["Total_Vendas"]
        if total_vendas == 0: categoria = 0
        elif total_vendas < 1500: categoria = 1
        elif total_vendas < 2500: categoria = 2
        elif total_vendas < 3000: categoria = 3
        else: categoria = 4
        valores.append(categoria)

        hover_text = f"📅 {row['data_str']}<br>"
        if total_vendas > 0:
            hover_text += f"💰 Total: {format_brl(total_vendas)}<br>"
            if 'Cartão' in row: hover_text += f"💳 Cartão: {format_brl(row['Cartão'])}<br>"
            if 'Dinheiro' in row: hover_text += f"💵 Dinheiro: {format_brl(row['Dinheiro'])}<br>"
            if 'Pix' in row: hover_text += f"📱 Pix: {format_brl(row['Pix'])}"
        else:
            hover_text += "❌ Sem vendas"
        hover_texts.append(hover_text)

    max_semana = max(x_positions) + 1 if x_positions else 0
    matriz_vendas = np.full((7, max_semana), 0.0)
    matriz_hover = np.full((7, max_semana), "", dtype=object)

    for x, y, valor, hover in zip(x_positions, y_positions, valores, hover_texts):
        if 0 <= y < 7 and 0 <= x < max_semana:
            matriz_vendas[y, x] = valor
            matriz_hover[y, x] = hover

    escala_cores = [
        [0.0, "#161b22"], [0.001, "#39D353"], [0.25, "#39D353"],
        [0.251, "#37AB4B"], [0.5, "#37AB4B"], [0.501, "#006D31"],
        [0.75, "#006D31"], [0.751, "#0D4428"], [1.0, "#0D4428"]
    ]

    fig = go.Figure(data=go.Heatmap(
        z=matriz_vendas, text=matriz_hover, hovertemplate="%{text}<extra></extra>",
        colorscale=escala_cores, showscale=False, zmin=0, zmax=4,
        xgap=3, ygap=3, hoverongaps=False
    ))

    meses_posicoes = []
    meses_nomes_plotly = []
    for mes in range(1, 13):
        primeiro_dia_mes = datetime(ano, mes, 1).date()
        dias_desde_inicio = (primeiro_dia_mes - primeiro_dia).days
        semana_mes = (dias_desde_inicio + primeiro_dia_semana) // 7
        meses_posicoes.append(semana_mes)
        meses_nomes_plotly.append(calendar.month_abbr[mes].replace(".", ""))

    fig.update_layout(
        title=f"Heatmap Anual de Vendas - {ano}",
        height=300, # Altura ajustada
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COR_TEXTO_PRINCIPAL, family="Arial"),
        xaxis=dict(title="", showgrid=False, zeroline=False, tickmode="array", tickvals=meses_posicoes, ticktext=meses_nomes_plotly, tickfont=dict(size=10), side="top", tickangle=0),
        yaxis=dict(title="", showgrid=False, zeroline=False, tickmode="array", tickvals=[0, 1, 2, 3, 4, 5, 6], ticktext=["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"], tickfont=dict(size=10), ticklen=0),
        title_x=0.5, title_font=dict(size=16), margin=dict(l=30, r=10, t=60, b=10)
    )
    return fig

def criar_heatmap_vendas_mensais(df, ano):
    empty_fig = go.Figure().update_layout(height=150, title=f"Sem dados para o heatmap mensal de {ano}", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=COR_TEXTO_PRINCIPAL)
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        return empty_fig

    df_ano = df[df["Data"].dt.year == ano].copy()
    if df_ano.empty:
        return empty_fig

    df_ano["Mes"] = df_ano["Data"].dt.month
    vendas_mensais = df_ano.groupby("Mes").agg({"Total": "sum", "Cartão": "sum", "Dinheiro": "sum", "Pix": "sum"}).reindex(range(1, 13), fill_value=0).reset_index()
    meses_nomes_plotly = [calendar.month_abbr[m].replace(".", "") for m in range(1, 13)]
    vendas_mensais["Mes_Nome"] = vendas_mensais["Mes"].map(lambda x: meses_nomes_plotly[x-1])

    matriz_mensal = np.zeros((1, 12))
    matriz_hover_mensal = np.full((1, 12), "", dtype=object)

    max_venda_mensal = vendas_mensais["Total"].max()
    if max_venda_mensal > 0:
        bins = [0, max_venda_mensal * 0.25, max_venda_mensal * 0.5, max_venda_mensal * 0.75, max_venda_mensal + 1]
        labels = [1, 2, 3, 4]
        vendas_mensais["Categoria"] = pd.cut(vendas_mensais["Total"], bins=bins, labels=labels, right=False, include_lowest=True).fillna(0).astype(int)
    else:
        vendas_mensais["Categoria"] = 0

    for mes_idx in range(12):
        mes_num = mes_idx + 1
        dados_mes = vendas_mensais[vendas_mensais["Mes"] == mes_num]
        if not dados_mes.empty:
            row = dados_mes.iloc[0]
            total_mes, categoria = row["Total"], row["Categoria"]
            matriz_mensal[0, mes_idx] = categoria if total_mes > 0 else 0
            hover_text = f"📅 {row['Mes_Nome']} {ano}<br>"
            if total_mes > 0:
                hover_text += f"💰 Total: {format_brl(total_mes)}<br>"
                if 'Cartão' in row: hover_text += f"💳 Cartão: {format_brl(row['Cartão'])}<br>"
                if 'Dinheiro' in row: hover_text += f"💵 Dinheiro: {format_brl(row['Dinheiro'])}<br>"
                if 'Pix' in row: hover_text += f"📱 Pix: {format_brl(row['Pix'])}"
            else:
                hover_text += "❌ Sem vendas"
        else:
            matriz_mensal[0, mes_idx] = 0
            hover_text = f"📅 {meses_nomes_plotly[mes_idx]} {ano}<br>❌ Sem vendas"
        matriz_hover_mensal[0, mes_idx] = hover_text

    escala_cores = [
        [0.0, "#161b22"], [0.001, "#39D353"], [0.25, "#39D353"],
        [0.251, "#37AB4B"], [0.5, "#37AB4B"], [0.501, "#006D31"],
        [0.75, "#006D31"], [0.751, "#0D4428"], [1.0, "#0D4428"]
    ]

    fig = go.Figure(data=go.Heatmap(
        z=matriz_mensal, text=matriz_hover_mensal, hovertemplate="%{text}<extra></extra>",
        colorscale=escala_cores, showscale=False, zmin=0, zmax=4,
        xgap=5, ygap=5, hoverongaps=False
    ))
    fig.update_layout(
        title=f"Heatmap Mensal de Vendas - {ano}",
        height=150, # Altura ajustada
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COR_TEXTO_PRINCIPAL, family="Arial"),
        xaxis=dict(title="", showgrid=False, zeroline=False, tickmode="array", tickvals=list(range(12)), ticktext=meses_nomes_plotly, tickfont=dict(size=10), side="bottom"),
        yaxis=dict(title="", showgrid=False, zeroline=False, showticklabels=False),
        title_x=0.5, title_font=dict(size=16), margin=dict(l=10, r=10, t=50, b=30)
    )
    return fig

# --- Função Principal da Aplicação (Original com Modificações) ---
def main():
    # --- Sidebar (Original com Logo Adicionada) --- #
    st.sidebar.title("🍔 Clips Burger Financeiro")
    # Adicionar Logo Grande com Aura via HTML/CSS
    st.sidebar.markdown(f'<div style="text-align: center;"><img src="{LOGO_URL}" class="logo-sidebar-image"></div>', unsafe_allow_html=True)
    st.sidebar.markdown("---")

    # Leitura e processamento inicial
    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    # Filtros na Sidebar (Original)
    st.sidebar.header("Filtros")
    # Garantir que anos sejam inteiros e tratar NaNs
    anos_disponiveis = df_processed["Ano"].dropna().unique()
    if not anos_disponiveis.size > 0:
        all_years = ["Todos", datetime.now().year] # Fallback se não houver anos
    else:
        all_years = ["Todos"] + sorted(anos_disponiveis.astype(int), reverse=True)
    
    selected_year = st.sidebar.selectbox("Ano", all_years)

    all_months = ["Todos"] + list(meses_ordem)
    selected_month_name = st.sidebar.selectbox("Mês", all_months)

    # Aplicar filtros
    df_filtered = df_processed.copy()
    if selected_year != "Todos":
        df_filtered = df_filtered[df_filtered["Ano"] == selected_year]
    
    if selected_month_name != "Todos":
        month_map = {name: i+1 for i, name in enumerate(meses_ordem)}
        selected_month_num = month_map.get(selected_month_name)
        if selected_month_num:
            df_filtered = df_filtered[df_filtered["Mês"] == selected_month_num]

    st.sidebar.markdown("---")
    st.sidebar.header("Registrar Nova Venda")
    with st.sidebar.form(key="sales_form", clear_on_submit=True):
        selected_date = st.date_input("Data da Venda", datetime.now())
        valor_cartao = st.number_input("Valor Cartão (R$)", min_value=0.0, format="%.2f", step=10.0, key="cartao")
        valor_dinheiro = st.number_input("Valor Dinheiro (R$)", min_value=0.0, format="%.2f", step=10.0, key="dinheiro")
        valor_pix = st.number_input("Valor PIX (R$)", min_value=0.0, format="%.2f", step=10.0, key="pix")
        submit_button = st.form_submit_button(label="Registrar Venda")

        if submit_button:
            worksheet = get_worksheet()
            if worksheet:
                add_data_to_sheet(selected_date, valor_cartao, valor_dinheiro, valor_pix, worksheet)
            else:
                st.error("Erro de conexão com a planilha.")

    # --- Conteúdo Principal (Original com Heatmaps Adicionados) --- #
    st.title("Dashboard Financeiro")

    if df_filtered.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados ou a planilha está vazia.")
    else:
        # Métricas (Original)
        st.header("Resumo Financeiro")
        total_revenue = df_filtered["Total"].sum()
        # Calcular média apenas sobre dias com vendas > 0
        daily_sales = df_filtered.groupby(df_filtered["Data"].dt.date)["Total"].sum()
        avg_daily_sales = daily_sales[daily_sales > 0].mean() if not daily_sales[daily_sales > 0].empty else 0
        days_with_sales = df_filtered["Data"].nunique()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Faturamento Total", format_brl(total_revenue))
        col2.metric("📅 Média Diária (Dias c/ Venda)", format_brl(avg_daily_sales))
        col3.metric("🗓️ Dias com Vendas", f"{days_with_sales} dias")

        st.markdown("---")

        # --- Heatmaps (ADICIONADOS) --- #
        heatmap_year_to_display = selected_year if selected_year != "Todos" else datetime.now().year
        st.header(f"Heatmaps de Vendas - {heatmap_year_to_display}")
        # Passar df_processed (todos os dados) para os heatmaps poderem filtrar o ano correto
        heatmap_anual = criar_calendario_anual_heatmap(df_processed, heatmap_year_to_display)
        st.plotly_chart(heatmap_anual, use_container_width=True)
        
        heatmap_mensal = criar_heatmap_vendas_mensais(df_processed, heatmap_year_to_display)
        st.plotly_chart(heatmap_mensal, use_container_width=True)
        # --- Fim Heatmaps --- #

        st.markdown("---")

        # Gráficos (Original)
        st.header("Análise Gráfica")
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.subheader("Vendas Diárias por Método")
            daily_sales_chart = create_advanced_daily_sales_chart(df_filtered)
            if daily_sales_chart:
                st.altair_chart(daily_sales_chart, use_container_width=True)
            else:
                st.info("Dados insuficientes para o gráfico de vendas diárias.")

        with col_chart2:
            st.subheader("Distribuição por Pagamento")
            radial_chart = create_radial_plot(df_filtered)
            if radial_chart:
                st.altair_chart(radial_chart, use_container_width=True)
            else:
                st.info("Dados insuficientes para o gráfico radial.")

        st.subheader("Evolução das Vendas")
        area_chart = create_area_chart_with_gradient(df_filtered)
        if area_chart:
            st.altair_chart(area_chart, use_container_width=True)
        else:
            st.info("Dados insuficientes para o gráfico de evolução.")

        st.markdown("---")

        # Análise por Dia da Semana (Original)
        st.header("Análise por Dia da Semana")
        weekday_chart, weekday_table = create_enhanced_weekday_analysis(df_filtered)
        if weekday_chart is not None and weekday_table is not None:
            col_wd1, col_wd2 = st.columns([2, 1])
            with col_wd1:
                st.altair_chart(weekday_chart, use_container_width=True)
            with col_wd2:
                st.dataframe(weekday_table.set_index("DiaSemana"), use_container_width=True)
        else:
            st.info("Dados insuficientes para a análise por dia da semana.")

    # --- Rodapé Criativo (ADICIONADO) --- #
    st.markdown("---")
    year = datetime.now().year
    st.markdown(f"""
    <div class="footer">
        🍔 Clips Burger &copy; {year} | Feito com <a href="https://streamlit.io" target="_blank">Streamlit</a> & muito sabor! ✨
        <br>
        Análises geradas por Manus AI
    </div>
    """, unsafe_allow_html=True)
    # --- Fim Rodapé --- #

# --- Execução Principal (Original) --- #
if __name__ == "__main__":
    main()

