import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings
import matplotlib.pyplot as plt
import calplot
import os # Adicionado para manipulação de caminhos

# Suprimir warnings específicos do pandas
warnings.filterwarnings("ignore", category=FutureWarning, message=".*observed=False.*")

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = "1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg"
WORKSHEET_NAME = "Vendas"
HEATMAP_FILENAME = "/home/ubuntu/sales_heatmap.png" # Caminho para salvar o heatmap

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema Financeiro - Clips Burger", layout="wide", page_icon="🍔")

# Configuração de tema para gráficos mais bonitos
alt.data_transformers.enable("json")

# Paleta de cores otimizada para modo escuro
CORES_MODO_ESCURO = ["#4c78a8", "#54a24b", "#f58518", "#e45756", "#72b7b2", "#ff9da6", "#9d755d", "#bab0ac"]

# Define a ordem correta dos dias da semana e meses
dias_semana_ordem = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# CSS para melhorar a aparência
def inject_css():
    st.markdown("""
    <style>
    .stSelectbox label, .stNumberInput label {
        font-weight: bold;
        color: #4c78a8;
    }
    
    .stNumberInput input::placeholder {
        color: #888;
        font-style: italic;
    }
    
    .stButton > button {
        height: 3rem;
        font-size: 1.2rem;
        font-weight: bold;
        width: 100%;
    }
    
    .element-container {
        margin-bottom: 0.5rem;
    }
    
    .stMetric {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    /* Dashboard Premium Styles */
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    /* Grid para gráficos do dashboard premium */
    .premium-charts-grid {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 2rem;
        margin: 2rem 0;
    }
    
    .premium-chart-full {
        grid-column: 1 / -1;
        margin: 2rem 0;
    }
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
            st.error("Credenciais do Google ("google_credentials") não encontradas em st.secrets. Configure o arquivo .streamlit/secrets.toml")
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
            st.error(f"Planilha com ID ", {SPREADSHEET_ID}, " não encontrada.")
            return None
        except Exception as e:
            st.error(f"Erro ao acessar a planilha ", {WORKSHEET_NAME}, ": {e}")
            return None
    return None

@st.cache_data
def read_sales_data():
    """Lê todos os registros da planilha de vendas e retorna como DataFrame."""
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records()
            if not rows:
                st.info("A planilha de vendas está vazia.")
                return pd.DataFrame()

            df = pd.DataFrame(rows)
            
            for col in ["Cartão", "Dinheiro", "Pix"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    df[col] = 0
            
            if "Data" not in df.columns:
                df["Data"] = pd.NaT

            return df
        except Exception as e:
            st.error(f"Erro ao ler dados da planilha: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- Funções de Manipulação de Dados ---
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
        st.success("Dados registrados com sucesso! ✅")
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

    df["Total"] = df["Cartão"] + df["Dinheiro"] + df["Pix"]

    if "Data" in df.columns and not df["Data"].isnull().all():
        try:
            # Tenta converter string para datetime (formato DD/MM/YYYY primeiro)
            if pd.api.types.is_string_dtype(df["Data"]):
                df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
                # Se falhar, tenta formato padrão
                if df["Data"].isnull().all():
                    df["Data"] = pd.to_datetime(df_input["Data"], errors="coerce")
            # Se já não for datetime, converte
            elif not pd.api.types.is_datetime64_any_dtype(df["Data"]):
                 df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
            
            df.dropna(subset=["Data"], inplace=True)

            if not df.empty:
                df["Ano"] = df["Data"].dt.year
                df["Mês"] = df["Data"].dt.month

                try:
                    # Tenta formatar para nome do mês em português
                    df["MêsNome"] = df["Mês"].map(lambda x: meses_ordem[int(x)-1] if pd.notna(x) and 1 <= int(x) <= 12 else "Inválido")
                except Exception:
                     # Fallback se a formatação falhar
                    df["MêsNome"] = df["Data"].dt.strftime("%B").str.capitalize()

                df["AnoMês"] = df["Data"].dt.strftime("%Y-%m")
                df["DataFormatada"] = df["Data"].dt.strftime("%d/%m/%Y")
                
                day_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
                df["DiaSemana"] = df["Data"].dt.dayofweek.map(day_map)
                df["DiaDoMes"] = df["Data"].dt.day

                # Garante que DiaSemana seja categórico com a ordem correta
                df["DiaSemana"] = pd.Categorical(df["DiaSemana"], categories=[d for d in dias_semana_ordem if d in df["DiaSemana"].unique()], ordered=True)
            else:
                # Se o DataFrame ficar vazio após dropna, preenche colunas derivadas
                for col in cols_to_ensure_date_derived:
                    df[col] = pd.Series(dtype="object" if col in ["MêsNome", "AnoMês", "DataFormatada", "DiaSemana"] else "float")
        except Exception as e:
            st.error(f"Erro crítico ao processar a coluna "Data": {e}. Verifique o formato das datas na planilha.")
            # Preenche colunas derivadas em caso de erro crítico
            for col in cols_to_ensure_date_derived:
                df[col] = pd.Series(dtype="object" if col in ["MêsNome", "AnoMês", "DataFormatada", "DiaSemana"] else "float")
    else:
        # Se a coluna "Data" não existe ou está toda vazia
        if "Data" not in df.columns:
            st.warning("Coluna "Data" não encontrada no DataFrame. Algumas análises temporais não estarão disponíveis.")
            df["Data"] = pd.NaT # Cria a coluna Data vazia
        # Preenche colunas derivadas
        for col in cols_to_ensure_date_derived:
            df[col] = pd.Series(dtype="object" if col in ["MêsNome", "AnoMês", "DataFormatada", "DiaSemana"] else "float")
            
    return df

# --- Funções de Gráficos Interativos em Altair ---
def create_radial_plot(df):
    """Cria um gráfico radial plot substituindo o gráfico de pizza."""
    if df.empty or not any(col in df.columns for col in ["Cartão", "Dinheiro", "Pix"]):
        return None
    
    payment_data = pd.DataFrame({
        "Método": ["Cartão", "Dinheiro", "PIX"],
        "Valor": [df["Cartão"].sum(), df["Dinheiro"].sum(), df["Pix"].sum()]
    })
    payment_data = payment_data[payment_data["Valor"] > 0]
    
    if payment_data.empty:
        return None

    # Criar gráfico radial plot usando Altair
    base = alt.Chart(payment_data).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        radius=alt.Radius("Valor:Q", scale=alt.Scale(type="sqrt", zero=True, rangeMin=20)),
        color=alt.Color(
            "Método:N", 
            scale=alt.Scale(range=CORES_MODO_ESCURO[:3]),
            legend=alt.Legend(
                title="Método de Pagamento",
                orient="bottom",
                direction="horizontal",
                titleFontSize=14,
                labelFontSize=12,
                symbolSize=100,
                symbolStrokeWidth=2,
                titlePadding=10,
                padding=10,
                rowPadding=5,
                columnPadding=15
            )
        ),
        tooltip=[
            alt.Tooltip("Método:N", title="Método"),
            alt.Tooltip("Valor:Q", title="Valor (R$)", format=",.2f")
        ]
    )

    radial_plot = base.mark_arc(
        innerRadius=20, 
        stroke="white", 
        strokeWidth=2
    ).properties(
        title=alt.TitleParams(
            text="Gráfico Radial de Métodos de Pagamento", 
            fontSize=16,
            anchor="start"
        ),
        width=500,
        height=500,
        padding={"bottom": 100}
    ).configure_view(
        stroke=None
    ).configure(
        background="transparent"
    )

    return radial_plot

def create_area_chart_with_gradient(df):
    """Cria gráfico de área com gradiente substituindo o gráfico de montanha."""
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        return None
    
    df_sorted = df.sort_values("Data").copy()
    
    if df_sorted.empty:
        return None
    
    area_chart = alt.Chart(df_sorted).mark_area(
        interpolate="monotone",
        line={"color": CORES_MODO_ESCURO[0], "strokeWidth": 3},
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color=CORES_MODO_ESCURO[0], offset=0),
                alt.GradientStop(color=CORES_MODO_ESCURO[4], offset=1)
            ],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X(
            "Data:T", 
            title="Data", 
            axis=alt.Axis(format="%d/%m", labelAngle=-45, labelFontSize=12)
        ),
        y=alt.Y(
            "Total:Q", 
            title="Total de Vendas (R$)", 
            axis=alt.Axis(labelFontSize=12)
        ),
        tooltip=[
            alt.Tooltip("DataFormatada:N", title="Data"),
            alt.Tooltip("Total:Q", title="Total de Vendas (R$)", format=",.2f")
        ]
    ).properties(
        title=alt.TitleParams(
            text="Evolução das Vendas com Gradiente", 
            fontSize=18,
            anchor="start"
        ),
        height=500,
        width=1000
    ).configure_view(
        stroke=None
    ).configure(
        background="transparent"
    )
    
    return area_chart

def create_advanced_daily_sales_chart(df):
    """Cria um gráfico de vendas diárias sem animação."""
    if df.empty or "Data" not in df.columns:
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
        size=20
    ).encode(
        x=alt.X(
            "Data:T",
            title="Data",
            axis=alt.Axis(format="%d/%m", labelAngle=-45, labelFontSize=12)
        ),
        y=alt.Y(
            "Valor:Q",
            title="Valor (R$)",
            stack="zero",
            axis=alt.Axis(labelFontSize=12)
        ),
        color=alt.Color(
            "Método:N",
            scale=alt.Scale(range=CORES_MODO_ESCURO[:3]),
            legend=alt.Legend(
                title="Método de Pagamento",
                orient="bottom",
                direction="horizontal",
                titleFontSize=14,
                labelFontSize=12,
                symbolSize=100,
                symbolStrokeWidth=2,
                titlePadding=10,
                padding=10,
                rowPadding=5,
                columnPadding=15
            )
        ),
        tooltip=[
            alt.Tooltip("DataFormatada:N", title="Data"),
            alt.Tooltip("Método:N", title="Método"),
            alt.Tooltip("Valor:Q", title="Valor (R$)", format=",.2f")
        ]
    ).properties(
        title=alt.TitleParams(
            text="Vendas Diárias por Método de Pagamento",
            fontSize=16,
            anchor="start"
        ),
        height=500,
        width=1000,
        padding={"bottom": 100}
    ).configure_view(
        stroke=None
    ).configure(
        background="transparent"
    )
    
    return bars

def create_enhanced_weekday_analysis(df):
    """Cria análise de vendas por dia da semana sem animação."""
    if df.empty or "DiaSemana" not in df.columns or "Total" not in df.columns:
        return None, None
    
    df_copy = df.copy()
    df_copy["Total"] = pd.to_numeric(df_copy["Total"], errors="coerce")
    df_copy.dropna(subset=["Total", "DiaSemana"], inplace=True)
    
    if df_copy.empty:
        return None, None
    
    weekday_stats = df_copy.groupby("DiaSemana", observed=True).agg({
        "Total": ["mean", "sum", "count"]
    }).round(2)
    
    weekday_stats.columns = ["Média", "Total", "Dias_Vendas"]
    weekday_stats = weekday_stats.reindex([d for d in dias_semana_ordem if d in weekday_stats.index])
    weekday_stats = weekday_stats.reset_index()
    
    total_media_geral = weekday_stats["Média"].sum()
    if total_media_geral > 0:
        weekday_stats["Percentual_Media"] = (weekday_stats["Média"] / total_media_geral * 100).round(1)
    else:
        weekday_stats["Percentual_Media"] = 0
    
    chart = alt.Chart(weekday_stats).mark_bar(
        color=CORES_MODO_ESCURO[0],
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5
    ).encode(
        x=alt.X(
            "DiaSemana:O",
            title="Dia da Semana",
            sort=dias_semana_ordem,
            axis=alt.Axis(labelAngle=-45, labelFontSize=12)
        ),
        y=alt.Y(
            "Média:Q",
            title="Média de Vendas (R$)",
            axis=alt.Axis(labelFontSize=12)
        ),
        tooltip=[
            alt.Tooltip("DiaSemana:N", title="Dia"),
            alt.Tooltip("Média:Q", title="Média (R$)", format=",.2f"),
            alt.Tooltip("Percentual_Media:Q", title="% da Média Total", format=".1f"),
            alt.Tooltip("Dias_Vendas:Q", title="Dias com Vendas")
        ]
    ).properties(
        title=alt.TitleParams(
            text="Média de Vendas por Dia da Semana",
            fontSize=18,
            anchor="start"
        ),
        height=500,
        width=1000,
        padding={"bottom": 100}
    ).configure_view(
        stroke=None
    ).configure(
        background="transparent"
    )
    
    best_day = weekday_stats.loc[weekday_stats["Média"].idxmax(), "DiaSemana"] if not weekday_stats.empty else "N/A"
    
    return chart, best_day

def create_sales_histogram(df, title="Distribuição dos Valores de Venda Diários"):
    """Histograma sem animação."""
    if df.empty or "Total" not in df.columns or df["Total"].isnull().all():
        return None
    
    df_filtered_hist = df[df["Total"] > 0].copy()
    if df_filtered_hist.empty:
        return None
    
    histogram = alt.Chart(df_filtered_hist).mark_bar(
        color=CORES_MODO_ESCURO[0],
        opacity=0.8,
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5
    ).encode(
        x=alt.X(
            "Total:Q",
            bin=alt.Bin(maxbins=20),
            title="Faixa de Valor da Venda Diária (R$)",
            axis=alt.Axis(labelFontSize=12)
        ),
        y=alt.Y(
            "count():Q",
            title="Número de Dias (Frequência)",
            axis=alt.Axis(labelFontSize=12)
        ),
        tooltip=[
            alt.Tooltip("Total:Q", bin=True, title="Faixa de Valor (R$)", format=",.0f"),
            alt.Tooltip("count():Q", title="Número de Dias")
        ]
    ).properties(
        title=alt.TitleParams(
            text=title,
            fontSize=18,
            anchor="start"
        ),
        height=500,
        width=1000,
        padding={"bottom": 100}
    ).configure_view(
        stroke=None
    ).configure(
        background="transparent"
    )
    
    return histogram

def analyze_sales_by_weekday(df):
    """Analisa vendas por dia da semana."""
    if df.empty or "DiaSemana" not in df.columns or "Total" not in df.columns or df["DiaSemana"].isnull().all() or df["Total"].isnull().all():
        return None, None
    
    try:
        df_copy = df.copy()
        df_copy["Total"] = pd.to_numeric(df_copy["Total"], errors="coerce")
        df_copy.dropna(subset=["Total", "DiaSemana"], inplace=True)
        
        if df_copy.empty:
            return None, None
        
        avg_sales_weekday = df_copy.groupby("DiaSemana", observed=True)["Total"].mean().reindex(dias_semana_ordem).dropna()
        
        if not avg_sales_weekday.empty:
            best_day = avg_sales_weekday.idxmax()
            return best_day, avg_sales_weekday
        else:
            return None, avg_sales_weekday
    except Exception as e:
        st.error(f"Erro ao analisar vendas por dia da semana: {e}")
        return None, None

# --- Função para criar o Heatmap de Vendas --- 
@st.cache_data(ttl=3600) # Cache por 1 hora
def create_sales_heatmap(df, filename=HEATMAP_FILENAME):
    """Cria um heatmap de vendas diárias estilo GitHub e salva como imagem."""
    if df.empty or "Data" not in df.columns or "Total" not in df.columns:
        st.warning("Dados insuficientes para gerar o heatmap de vendas.")
        return None

    df_heatmap = df.copy()
    # Garante que a coluna Data é datetime
    if not pd.api.types.is_datetime64_any_dtype(df_heatmap["Data"]):
        df_heatmap["Data"] = pd.to_datetime(df_heatmap["Data"], errors="coerce")
    
    df_heatmap.dropna(subset=["Data"], inplace=True)
    
    if df_heatmap.empty:
        st.warning("Dados insuficientes após processamento para o heatmap.")
        return None

    # Agrega vendas por dia (caso haja múltiplas entradas no mesmo dia)
    daily_sales = df_heatmap.groupby(df_heatmap["Data"].dt.date)["Total"].sum()
    daily_sales.index = pd.to_datetime(daily_sales.index)
    
    if daily_sales.empty:
        st.warning("Nenhuma venda diária encontrada para o heatmap.")
        return None

    try:
        # Define os níveis e o colormap
        # Cores: Cinza claro -> Azul claro -> Azul médio -> Azul escuro
        cmap_colors = ["#eeeeee", "#c6e48b", "#7bc96f", "#239a3b", "#196127"] # Exemplo de cores verdes (GitHub)
        # cmap_colors = ["#2d333b", "#0969da", "#58a6ff", "#a0d0ff", "#cceaff"] # Exemplo de cores azuis (modo escuro)
        cmap_name = "YlGn" # Colormap sequencial (Amarelo-Verde)
        
        # Ajusta o estilo do matplotlib para fundo escuro
        plt.style.use("dark_background")
        plt.rcParams["figure.facecolor"] = "#0f0f23" # Cor de fundo similar ao app
        plt.rcParams["axes.facecolor"] = "#0f0f23"
        plt.rcParams["savefig.facecolor"] = "#0f0f23"
        plt.rcParams["text.color"] = "white"
        plt.rcParams["axes.labelcolor"] = "white"
        plt.rcParams["xtick.color"] = "white"
        plt.rcParams["ytick.color"] = "white"

        # Cria o plot
        fig, ax = calplot.calplot(daily_sales, 
                                cmap=cmap_name, 
                                figsize=(15, 3), # Ajuste o tamanho conforme necessário
                                colorbar=True,
                                suptitle="Calendário de Vendas Diárias (R$)",
                                yearlabel_kws={"color": "white", "fontsize": 14},
                                monthlabel_kws={"color": "white", "fontsize": 8},
                                daylabel_kws={"color": "white", "fontsize": 8},
                                dayticks=True # Mostra os dias da semana (Seg, Qua, Sex)
                               )
        
        # Salva a figura
        plt.savefig(filename, bbox_inches="tight", dpi=150)
        plt.close(fig) # Fecha a figura para liberar memória
        
        # Restaura o estilo padrão do matplotlib se necessário em outras partes
        # plt.style.use("default") 
        
        return filename
    except Exception as e:
        st.error(f"Erro ao gerar o heatmap: {e}")
        # Tenta limpar a figura em caso de erro
        try:
            plt.close(fig)
        except:
            pass
        return None

# --- Funções de Cálculos Financeiros ---
def calculate_financial_results(df, salario_minimo, custo_contadora, custo_fornecedores_percentual):
    """Calcula os resultados financeiros com base nos dados de vendas seguindo normas contábeis."""
    results = {
        "receita_bruta": 0, "receita_tributavel": 0, "receita_nao_tributavel": 0,
        "impostos_sobre_vendas": 0, "receita_liquida": 0, "custo_produtos_vendidos": 0,
        "lucro_bruto": 0, "margem_bruta": 0, "despesas_administrativas": 0,
        "despesas_com_pessoal": 0, "despesas_contabeis": custo_contadora,
        "total_despesas_operacionais": 0, "lucro_operacional": 0, "margem_operacional": 0,
        "lucro_antes_ir": 0, "lucro_liquido": 0, "margem_liquida": 0,
        "diferenca_tributavel_nao_tributavel": 0
    }
    
    if df.empty: 
        return results
    
    results["receita_bruta"] = df["Total"].sum()
    results["receita_tributavel"] = df["Cartão"].sum() + df["Pix"].sum()
    results["receita_nao_tributavel"] = df["Dinheiro"].sum()
    results["impostos_sobre_vendas"] = results["receita_tributavel"] * 0.06
    results["receita_liquida"] = results["receita_bruta"] - results["impostos_sobre_vendas"]
    results["custo_produtos_vendidos"] = results["receita_bruta"] * (custo_fornecedores_percentual / 100)
    results["lucro_bruto"] = results["receita_liquida"] - results["custo_produtos_vendidos"]
    
    if results["receita_liquida"] > 0:
        results["margem_bruta"] = (results["lucro_bruto"] / results["receita_liquida"]) * 100
    
    # Considera o custo mensal da contadora e o custo mensal do salário + encargos
    num_meses = len(df["AnoMês"].unique()) if "AnoMês" in df and df["AnoMês"].nunique() > 0 else 1
    results["despesas_com_pessoal"] = (salario_minimo * 1.55) * num_meses
    results["despesas_contabeis"] = custo_contadora * num_meses
    results["despesas_administrativas"] = 0 # Assumindo zero por enquanto
    results["total_despesas_operacionais"] = (
        results["despesas_com_pessoal"] + 
        results["despesas_contabeis"] + 
        results["despesas_administrativas"]
    )
    
    results["lucro_operacional"] = results["lucro_bruto"] - results["total_despesas_operacionais"]
    if results["receita_liquida"] > 0:
        results["margem_operacional"] = (results["lucro_operacional"] / results["receita_liquida"]) * 100
    
    results["lucro_antes_ir"] = results["lucro_operacional"] # Simples Nacional não tem IR/CSLL destacado aqui
    results["lucro_liquido"] = results["lucro_antes_ir"]
    if results["receita_liquida"] > 0:
        results["margem_liquida"] = (results["lucro_liquido"] / results["receita_liquida"]) * 100
    
    results["diferenca_tributavel_nao_tributavel"] = results["receita_nao_tributavel"]
    
    return results

def create_dre_textual(resultados, df_processed, selected_anos_filter):
    """Cria uma apresentação textual do DRE no estilo tradicional contábil usando dados anuais."""
    def format_val(value):
        return f"{value:,.0f}".replace(",", ".")

    # Determinar o ano para o DRE
    if selected_anos_filter and len(selected_anos_filter) == 1:
        ano_dre = selected_anos_filter[0]
    elif not df_processed.empty and "Ano" in df_processed.columns and not df_processed["Ano"].isnull().all():
        ano_dre = int(df_processed["Ano"].max()) # Pega o último ano com dados
    else:
        ano_dre = datetime.now().year # Fallback para o ano atual

    # Filtrar dados APENAS por ano (ignorar filtro de mês)
    if not df_processed.empty and "Ano" in df_processed.columns:
        df_ano = df_processed[df_processed["Ano"] == ano_dre].copy()
        
        # Recalcular resultados com dados do ano completo
        if not df_ano.empty:
            # Usa os valores mensais dos inputs e multiplica por 12 para o DRE anual
            salario_anual = st.session_state.get("salario_tab4", 1550.0) # Salário base mensal
            contadora_anual = st.session_state.get("contadora_tab4", 316.0) # Custo mensal
            fornecedores_perc = st.session_state.get("fornecedores_tab4", 30.0)
            
            # Cria um DF temporário apenas com o ano para calcular resultados anuais
            # Passa 0 para salário e contadora, pois serão calculados dentro da função para o ano todo
            resultados_ano = calculate_financial_results(
                df_ano, 
                salario_anual, # Passa o valor mensal base
                contadora_anual, # Passa o valor mensal base
                fornecedores_perc
            )
            # Ajusta despesas para o ano inteiro (12 meses)
            resultados_ano["despesas_com_pessoal"] = (salario_anual * 1.55) * 12
            resultados_ano["despesas_contabeis"] = contadora_anual * 12
            # Recalcula totais e lucros com despesas anuais
            resultados_ano["total_despesas_operacionais"] = resultados_ano["despesas_com_pessoal"] + resultados_ano["despesas_contabeis"]
            resultados_ano["lucro_operacional"] = resultados_ano["lucro_bruto"] - resultados_ano["total_despesas_operacionais"]
            resultados_ano["lucro_antes_ir"] = resultados_ano["lucro_operacional"]
            resultados_ano["lucro_liquido"] = resultados_ano["lucro_antes_ir"]
            # Recalcula margens anuais
            if resultados_ano["receita_liquida"] > 0:
                resultados_ano["margem_operacional"] = (resultados_ano["lucro_operacional"] / resultados_ano["receita_liquida"]) * 100
                resultados_ano["margem_liquida"] = (resultados_ano["lucro_liquido"] / resultados_ano["receita_liquida"]) * 100
            else:
                 resultados_ano["margem_operacional"] = 0
                 resultados_ano["margem_liquida"] = 0

        else:
            # Se não há dados para o ano, zera os resultados anuais
            resultados_ano = {key: 0 for key in resultados.keys()}
            st.warning(f"Não há dados de vendas registrados para o ano {ano_dre} para gerar o DRE.")
    else:
        resultados_ano = {key: 0 for key in resultados.keys()}
        st.warning("Não há dados processados para gerar o DRE anual.")

    # Cabeçalho centralizado
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 30px;">
        <h3 style="margin: 0; font-weight: normal;">DEMONSTRAÇÃO DO RESULTADO DO EXERCÍCIO</h3>
        <p style="margin: 5px 0; font-style: italic;">Clips Burger - Exercício {ano_dre}</p>
    </div>
    <div style="text-align: right; margin-bottom: 20px;">
        <p style="margin: 0; font-size: 14px; font-weight: bold;">Em R$</p>
    </div>
    """, unsafe_allow_html=True)

    # Criar 2 colunas - descrição e valor
    col1, col2 = st.columns([6, 2])
    
    # RECEITA BRUTA
    with col1: st.markdown("**RECEITA BRUTA**")
    with col2: st.markdown(f"**{format_val(resultados_ano["receita_bruta"])}**")
    
    # DEDUÇÕES
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**(-) DEDUÇÕES**")
    with col2: st.markdown("")
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Simples Nacional")
    with col2: st.markdown(f"({format_val(resultados_ano["impostos_sobre_vendas"])})")
    
    # RECEITA LÍQUIDA
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**RECEITA LÍQUIDA**")
    with col2: st.markdown(f"**{format_val(resultados_ano["receita_liquida"])}**")
    
    # CUSTO DOS PRODUTOS VENDIDOS
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**(-) CUSTO DOS PRODUTOS VENDIDOS**")
    with col2: st.markdown(f"**({format_val(resultados_ano["custo_produtos_vendidos"])})**")
    
    # LUCRO BRUTO
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**LUCRO BRUTO**")
    with col2: st.markdown(f"**{format_val(resultados_ano["lucro_bruto"])}**")
    
    # DESPESAS OPERACIONAIS
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**(-) DESPESAS OPERACIONAIS**")
    with col2: st.markdown(f"**({format_val(resultados_ano["total_despesas_operacionais"])})**") # Valor total das despesas
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Despesas com Pessoal")
    with col2: st.markdown(f"({format_val(resultados_ano["despesas_com_pessoal"])})") # Valor anual
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Serviços Contábeis")
    with col2: st.markdown(f"({format_val(resultados_ano["despesas_contabeis"])})") # Valor anual
    
    # LUCRO OPERACIONAL
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**LUCRO OPERACIONAL**")
    with col2: st.markdown(f"**{format_val(resultados_ano["lucro_operacional"])}**")
    
    # RESULTADO ANTES DO IMPOSTO DE RENDA
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**LUCRO ANTES DO IMPOSTO DE RENDA**")
    with col2: st.markdown(f"**{format_val(resultados_ano["lucro_antes_ir"])}**")
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**(-) Provisão para Imposto de Renda**")
    with col2: st.markdown("**-**") # Simples Nacional já deduzido
    
    # Linha de separação
    st.markdown("---")
    
    # RESULTADO LÍQUIDO - destacado
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("## **RESULTADO LÍQUIDO DO EXERCÍCIO**")
    with col2: st.markdown(f"## **{format_val(resultados_ano["lucro_liquido"])}**")
    
    # Nota explicativa
    st.info(f"📅 **Nota:** Este DRE apresenta os resultados consolidados do exercício {ano_dre}, independente do filtro de mês aplicado nas outras análises. As despesas de pessoal e contabilidade foram anualizadas.")

def create_financial_dashboard_altair(resultados):
    """Dashboard financeiro com legenda corrigida para o período filtrado."""
    # Usa os resultados calculados para o período filtrado (não anualizados)
    financial_data = pd.DataFrame({
        "Categoria": [
            "Receita Bruta",
            "Impostos s/ Vendas",
            "Custo Produtos",
            "Despesas Pessoal",
            "Serviços Contábeis",
            "Lucro Líquido"
        ],
        "Valor": [
            resultados["receita_bruta"],
            -resultados["impostos_sobre_vendas"],
            -resultados["custo_produtos_vendidos"],
            -resultados["despesas_com_pessoal"], # Valor do período
            -resultados["despesas_contabeis"], # Valor do período
            resultados["lucro_liquido"]
        ],
        "Tipo": [
            "Receita",
            "Dedução",
            "CPV",
            "Despesa",
            "Despesa",
            "Resultado"
        ]
    })
    
    chart = alt.Chart(financial_data).mark_bar(
        cornerRadiusTopRight=8,
        cornerRadiusBottomRight=8
    ).encode(
        x=alt.X(
            "Valor:Q",
            title="Valor (R$)",
            axis=alt.Axis(format=",.0f", labelFontSize=12)
        ),
        y=alt.Y(
            "Categoria:O",
            title=None,
            sort=financial_data["Categoria"].tolist(),
            axis=alt.Axis(labelFontSize=12)
        ),
        color=alt.Color(
            "Tipo:N",
            scale=alt.Scale(
                domain=["Receita", "Dedução", "CPV", "Despesa", "Resultado"],
                range=[CORES_MODO_ESCURO[1], CORES_MODO_ESCURO[3], CORES_MODO_ESCURO[2], CORES_MODO_ESCURO[4], CORES_MODO_ESCURO[0]]
            ),
            legend=alt.Legend(
                title="Tipo",
                orient="bottom",
                direction="horizontal",
                titleFontSize=14,
                labelFontSize=12,
                symbolSize=100,
                symbolStrokeWidth=2,
                titlePadding=10,
                padding=10,
                rowPadding=5,
                columnPadding=15
            )
        ),
        tooltip=[
            alt.Tooltip("Categoria:N", title="Categoria"),
            alt.Tooltip("Valor:Q", title="Valor (R$)", format=",.2f"),
            alt.Tooltip("Tipo:N", title="Tipo")
        ]
    ).properties(
        title=alt.TitleParams(
            text="Composição do Resultado Financeiro (Período Filtrado)",
            fontSize=20,
            anchor="start"
        ),
        height=500,
        width=1000,
        padding={"bottom": 100}
    ).configure_view(
        stroke=None
    ).configure(
        background="transparent"
    )
    
    return chart

# --- Dashboard Premium Functions ---
def create_premium_kpi_cards(df):
    """Cria cards KPI premium com emoticons DENTRO dos boxes."""
    if df.empty:
        return
    
    total_vendas = df["Total"].sum()
    media_diaria = df["Total"].mean()
    melhor_dia = df.loc[df["Total"].idxmax(), "DataFormatada"] if not df.empty and "DataFormatada" in df.columns and not df["Total"].isnull().all() else "N/A"
    
    # Cálculo de crescimento mais robusto
    crescimento = 0
    if len(df) >= 14:
        media_ultimos_7 = df["Total"].tail(7).mean()
        media_7_anteriores = df["Total"].iloc[-14:-7].mean()
        if media_7_anteriores > 0:
            crescimento = ((media_ultimos_7 - media_7_anteriores) / media_7_anteriores * 100)
        elif media_ultimos_7 > 0:
             crescimento = 100.0 # Crescimento infinito se antes era 0
    elif len(df) >= 7:
         crescimento = 15.5 # Valor placeholder se não há 14 dias

    delta_crescimento_texto = f"{crescimento:+.1f}% vs 7 dias ant." if crescimento != 0 else "Dados insuficientes"
    delta_media_texto = "+8.2% vs período anterior" # Placeholder, idealmente calcular
    delta_tendencia_texto = "Crescimento sustentado" if crescimento > 5 else ("Estável" if crescimento >= -5 else "Declínio acentuado")

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with st.container():
            st.metric(
                label="💰 Faturamento Total",
                value=format_brl(total_vendas),
                delta=delta_crescimento_texto
            )
    
    with col2:
        with st.container():
            st.metric(
                label="📊 Média Diária",
                value=format_brl(media_diaria),
                delta=delta_media_texto # Manter placeholder ou calcular
            )
    
    with col3:
        with st.container():
            st.metric(
                label="🏆 Melhor Dia",
                value=melhor_dia,
                delta="Maior faturamento"
            )
    
    with col4:
        with st.container():
            st.metric(
                label="📈 Tendência (7d)",
                value=f"{crescimento:+.1f}%",
                delta=delta_tendencia_texto
            )

def create_premium_insights(df):
    """Insights com bordas coloridas na lateral esquerda."""
    if df.empty:
        return
    
    # Calcular insights automáticos
    total_vendas = df["Total"].sum()
    dias_trabalhados = len(df)
    media_diaria = total_vendas / dias_trabalhados if dias_trabalhados > 0 else 0
    
    # Análise de tendência (reutiliza cálculo de KPI)
    tendencia = 0
    if len(df) >= 14:
        primeira_semana = df.head(7)["Total"].mean()
        ultima_semana = df.tail(7)["Total"].mean()
        tendencia = ((ultima_semana - primeira_semana) / primeira_semana * 100) if primeira_semana > 0 else (100.0 if ultima_semana > 0 else 0)
    
    tendencia_texto = "crescimento" if tendencia > 5 else ("estável" if tendencia >= -5 else "declínio")
    tendencia_cor = "#4caf50" if tendencia > 5 else ("#ff9800" if tendencia >= -5 else "#f44336")
    
    # Melhor método de pagamento
    melhor_metodo = "N/A"
    percentual_melhor = 0
    if all(col in df.columns for col in ["Cartão", "Dinheiro", "Pix"]):
        metodos = {
            "Cartão": df["Cartão"].sum(),
            "Dinheiro": df["Dinheiro"].sum(),
            "PIX": df["Pix"].sum()
        }
        # Remove métodos com valor 0
        metodos = {k: v for k, v in metodos.items() if v > 0}
        if metodos:
            melhor_metodo = max(metodos, key=metodos.get)
            percentual_melhor = (metodos[melhor_metodo] / total_vendas * 100) if total_vendas > 0 else 0
    
    st.subheader("🧠 Insights Inteligentes Automáticos")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div style="
            background: rgba(255,255,255,0.1); 
            padding: 1.5rem; 
            border-radius: 10px; 
            margin: 1rem 0;
            border-left: 4px solid {tendencia_cor};
            min-height: 150px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            <h4 style="color: {tendencia_cor}; margin: 0 0 1rem 0;">📈 Análise de Tendência</h4>
            <p style="margin: 0; line-height: 1.6; color: white;">
                Suas vendas apresentam uma tendência de <strong>{tendencia_texto}</strong> 
                de <strong style="color: {tendencia_cor};">{abs(tendencia):.1f}%</strong> 
                comparando as últimas duas semanas.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="
            background: rgba(255,255,255,0.1); 
            padding: 1.5rem; 
            border-radius: 10px; 
            margin: 1rem 0;
            border-left: 4px solid #4caf50;
            min-height: 150px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            <h4 style="color: #4caf50; margin: 0 0 1rem 0;">💡 Recomendação Estratégica</h4>
            <p style="margin: 0; line-height: 1.6; color: white;">
                O método <strong>{melhor_metodo}</strong> representa 
                <strong>{percentual_melhor:.1f}%</strong> das vendas. 
                Considere incentivar este meio de pagamento.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="
            background: rgba(255,255,255,0.1); 
            padding: 1.5rem; 
            border-radius: 10px; 
            margin: 1rem 0;
            border-left: 4px solid #e91e63;
            min-height: 150px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            <h4 style="color: #e91e63; margin: 0 0 1rem 0;">🎯 Meta Sugerida</h4>
            <p style="margin: 0; line-height: 1.6; color: white;">
                Com base na média atual de <strong>{format_brl(media_diaria)}</strong> por dia, 
                uma meta de <strong>{format_brl(media_diaria * 1.15)}</strong> 
                representaria um crescimento de 15%.
            </p>
        </div>
        """, unsafe_allow_html=True)

# Função para formatar valores em moeda brasileira
def format_brl(value):
    try:
        return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except (TypeError, ValueError):
        return "R$ 0,00" # Retorna 0 se o valor for inválido

# --- Interface Principal da Aplicação ---
def main():
    # Título com logo ao lado
    try:
        # Tenta carregar o logo localmente
        logo_path = "logo.png"
        if not os.path.exists(logo_path):
             # Se não existir, tenta um caminho absoluto (ajuste se necessário)
             logo_path = "/home/ubuntu/logo.png" 
             if not os.path.exists(logo_path):
                 logo_path = None # Define como None se não encontrar
        
        col_logo, col_title = st.columns([1, 6])
        if logo_path:
            with col_logo:
                st.image(logo_path, width=80)
        else:
             with col_logo:
                 st.markdown("🍔", unsafe_allow_html=True) # Usa emoji se não houver logo
        
        with col_title:
            st.markdown(f"""
            <h1 style="margin: 0; padding-left: 10px;">SISTEMA FINANCEIRO - CLIP"S BURGER</h1>
            <p style="margin: 0; font-size: 14px; color: gray; padding-left: 10px;">Gestão inteligente de vendas com análise financeira em tempo real - {datetime.now().year}</p>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erro ao carregar logo: {e}")
        st.title("🍔 SISTEMA FINANCEIRO - CLIPS BURGER")
        st.caption("Gestão inteligente de vendas com análise financeira em tempo real")

    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    # Criar 6 tabs incluindo o Calendário e o Dashboard Premium
    tab_list = [
        "📝 Registrar Venda", 
        "📅 Calendário Vendas", # Nova tab para o heatmap
        "📈 Análise Detalhada", 
        "💡 Estatísticas", 
        "💰 Análise Contábil",
        "🚀 Dashboard Premium"
    ]
    tabs = st.tabs(tab_list)

    # Mapeia as tabs para variáveis dinamicamente
    tab_registrar, tab_calendario, tab_analise, tab_estatisticas, tab_contabil, tab_premium = tabs

    # --- TAB REGISTRAR VENDA --- 
    with tab_registrar:
        st.header("📝 Registrar Nova Venda")
        
        data_input = st.date_input("📅 Data da Venda", value=datetime.now(), format="DD/MM/YYYY", key="data_venda_reg")
        
        col1, col2, col3 = st.columns(3)
        with col1: 
            cartao_input = st.number_input(
                "💳 Cartão (R$)", min_value=0.0, value=None, format="%.2f", 
                key="cartao_venda", placeholder="Digite o valor..."
            )
        with col2: 
            dinheiro_input = st.number_input(
                "💵 Dinheiro (R$)", min_value=0.0, value=None, format="%.2f", 
                key="dinheiro_venda", placeholder="Digite o valor..."
            )
        with col3: 
            pix_input = st.number_input(
                "📱 PIX (R$)", min_value=0.0, value=None, format="%.2f", 
                key="pix_venda", placeholder="Digite o valor..."
            )
        
        cartao_val = cartao_input if cartao_input is not None else 0.0
        dinheiro_val = dinheiro_input if dinheiro_input is not None else 0.0
        pix_val = pix_input if pix_input is not None else 0.0
        total_venda_form = cartao_val + dinheiro_val + pix_val
        
        st.markdown(f"""
        <div style="text-align: center; padding: 0.7rem 1rem; background: linear-gradient(90deg, #4c78a8, #54a24b); border-radius: 10px; color: white; margin: 0.5rem 0; box-shadow: 0 4px 12px rgba(0,0,0,0.2); height: 3rem; display: flex; align-items: center; justify-content: center;">
            <div>
                <span style="font-size: 1.8rem; margin-right: 0.5rem; text-shadow: 1px 1px 3px rgba(0,0,0,0.3);">💰</span>
                <span style="font-size: 2.2rem; font-weight: bold; text-shadow: 1px 1px 3px rgba(0,0,0,0.3);">Total: {format_brl(total_venda_form)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("✅ Registrar Venda", type="primary", use_container_width=True, key="btn_registrar"):
            if total_venda_form > 0:
                formatted_date = data_input.strftime("%d/%m/%Y")
                worksheet_obj = get_worksheet()
                if worksheet_obj and add_data_to_sheet(formatted_date, cartao_val, dinheiro_val, pix_val, worksheet_obj):
                    # Limpa caches específicos após adicionar dados
                    read_sales_data.clear()
                    process_data.clear()
                    create_sales_heatmap.clear() # Limpa cache do heatmap também
                    st.success("✅ Venda registrada e dados recarregados!")
                    st.rerun()
                elif not worksheet_obj: 
                    st.error("❌ Falha ao conectar à planilha. Venda não registrada.")
            else: 
                st.warning("⚠️ O valor total da venda deve ser maior que zero.")

    # --- SIDEBAR COM FILTROS --- (Movido para fora das tabs para ser global)
    selected_anos_filter, selected_meses_filter = [], []
    with st.sidebar:
        st.header("🔍 Filtros de Período")
        st.markdown("---")
        
        if not df_processed.empty and "Ano" in df_processed.columns and not df_processed["Ano"].isnull().all():
            anos_disponiveis = sorted(df_processed["Ano"].dropna().unique().astype(int), reverse=True)
            if anos_disponiveis:
                default_ano = [datetime.now().year] if datetime.now().year in anos_disponiveis else ([anos_disponiveis[0]] if anos_disponiveis else [])
                selected_anos_filter = st.multiselect("📅 Ano(s):", options=anos_disponiveis, default=default_ano, key="filtro_ano")
                
                if selected_anos_filter:
                    df_para_filtro_mes = df_processed[df_processed["Ano"].isin(selected_anos_filter)]
                    if not df_para_filtro_mes.empty and "Mês" in df_para_filtro_mes.columns and not df_para_filtro_mes["Mês"].isnull().all():
                        meses_numeros_disponiveis = sorted(df_para_filtro_mes["Mês"].dropna().unique().astype(int))
                        meses_opcoes_dict = {m_num: meses_ordem[m_num-1] for m_num in meses_numeros_disponiveis if 1 <= m_num <= 12}
                        meses_opcoes_display = [f"{m_num} - {m_nome}" for m_num, m_nome in meses_opcoes_dict.items()]
                        
                        # Default: Seleciona todos os meses disponíveis para os anos selecionados
                        default_meses_selecionados = meses_opcoes_display 
                        
                        selected_meses_str = st.multiselect("📆 Mês(es):", options=meses_opcoes_display, default=default_meses_selecionados, key="filtro_mes")
                        selected_meses_filter = [int(m.split(" - ")[0]) for m in selected_meses_str]
            else: 
                st.info("📊 Nenhum ano disponível para filtro.")
        else: 
            st.info("📊 Não há dados processados para aplicar filtros.")

    # Aplicar filtros ao DataFrame processado
    df_filtered = df_processed.copy()
    if not df_filtered.empty:
        if selected_anos_filter and "Ano" in df_filtered.columns: 
            df_filtered = df_filtered[df_filtered["Ano"].isin(selected_anos_filter)]
        if selected_meses_filter and "Mês" in df_filtered.columns: 
            df_filtered = df_filtered[df_filtered["Mês"].isin(selected_meses_filter)]

    # Mostrar informações dos filtros aplicados na sidebar
    with st.sidebar:
        if not df_filtered.empty:
            total_registros_filtrados = len(df_filtered)
            total_faturamento_filtrado = df_filtered["Total"].sum()
            st.markdown("---")
            st.markdown("### 📈 Resumo dos Filtros Aplicados")
            st.metric("Registros Filtrados", total_registros_filtrados)
            st.metric("Faturamento Filtrado", format_brl(total_faturamento_filtrado))
        elif not df_processed.empty:
            st.markdown("---")
            st.info("Nenhum registro corresponde aos filtros selecionados.")
        else:
            st.markdown("---")
            st.warning("Nenhum dado carregado da planilha.")

    # --- TAB CALENDÁRIO VENDAS --- 
    with tab_calendario:
        st.header("📅 Calendário de Vendas (Heatmap)")
        st.markdown("Visualize a intensidade das vendas diárias ao longo do tempo.")
        
        # Usa o DataFrame processado completo (df_processed) para o heatmap
        # para mostrar o contexto geral, independente dos filtros.
        # Se quiser que o heatmap respeite os filtros, use df_filtered aqui.
        if not df_processed.empty:
            heatmap_path = create_sales_heatmap(df_processed) # Gera usando todos os dados
            if heatmap_path and os.path.exists(heatmap_path):
                st.image(heatmap_path, use_column_width=True)
            elif heatmap_path is None:
                 st.info("Não foi possível gerar o heatmap com os dados atuais.")
            else:
                 st.error("Arquivo do heatmap não encontrado após a geração.")
        else:
            st.info("Não há dados carregados para gerar o calendário de vendas.")

    # --- TAB ANÁLISE DETALHADA --- 
    with tab_analise:
        st.header("🔎 Análise Detalhada de Vendas")
        if not df_filtered.empty and "DataFormatada" in df_filtered.columns:
            st.subheader("🧾 Tabela de Vendas Filtradas")
            cols_to_display_tab2 = ["DataFormatada", "DiaSemana", "DiaDoMes", "Cartão", "Dinheiro", "Pix", "Total"]
            cols_existentes_tab2 = [col for col in cols_to_display_tab2 if col in df_filtered.columns]
            
            if cols_existentes_tab2: 
                # Ordena pela data mais recente primeiro na tabela
                df_display = df_filtered[cols_existentes_tab2].sort_values(by="Data", ascending=False) if "Data" in df_filtered else df_filtered[cols_existentes_tab2]
                st.dataframe(df_display, use_container_width=True, height=600, hide_index=True)
            else: 
                st.info("Colunas necessárias para a tabela de dados filtrados não estão disponíveis.")

            daily_chart = create_advanced_daily_sales_chart(df_filtered)
            if daily_chart:
                st.altair_chart(daily_chart, use_container_width=True)
            else:
                st.info("Sem dados de vendas diárias para exibir o gráfico nos filtros selecionados.")

            area_chart = create_area_chart_with_gradient(df_filtered)
            if area_chart:
                st.altair_chart(area_chart, use_container_width=True)
            else:
                st.info("Não foi possível gerar o gráfico de área.")
        else:
             if df_processed.empty and df_raw.empty and get_worksheet() is None: 
                 st.warning("Não foi possível carregar os dados. Verifique configurações e credenciais.")
             elif df_processed.empty: 
                 st.info("Não há dados processados para exibir. Verifique a planilha de origem.")
             elif df_filtered.empty: 
                 st.info("Nenhum dado corresponde aos filtros selecionados.")
             else: 
                 st.info("Não há dados para exibir na Análise Detalhada. Pode ser um problema no processamento.")

    # --- TAB ESTATÍSTICAS --- 
    with tab_estatisticas:
        st.header("💡 Estatísticas e Tendências de Vendas")
        if not df_filtered.empty and "Total" in df_filtered.columns and not df_filtered["Total"].isnull().all():
            st.subheader("💰 Resumo Financeiro Agregado (Período Filtrado)")
            total_registros = len(df_filtered)
            total_faturamento = df_filtered["Total"].sum()
            media_por_registro = df_filtered["Total"].mean() if total_registros > 0 else 0
            maior_venda_diaria = df_filtered["Total"].max() if total_registros > 0 else 0
            menor_venda_diaria = df_filtered[df_filtered["Total"] > 0]["Total"].min() if not df_filtered[df_filtered["Total"] > 0].empty else 0
            
            col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
            with col_metrics1: st.metric("🔢 Total de Registros", f"{total_registros}")
            with col_metrics2: st.metric("💵 Faturamento Total", format_brl(total_faturamento))
            with col_metrics3: st.metric("📈 Média por Registro", format_brl(media_por_registro))
            col_metrics4, col_metrics5, _ = st.columns(3)
            with col_metrics4: st.metric("⬆️ Maior Venda Diária", format_brl(maior_venda_diaria))
            with col_metrics5: st.metric("⬇️ Menor Venda Diária (>0)", format_brl(menor_venda_diaria))
            
            st.divider()

            st.subheader("💳 Métodos de Pagamento (Período Filtrado)")
            cartao_total = df_filtered["Cartão"].sum() if "Cartão" in df_filtered else 0
            dinheiro_total = df_filtered["Dinheiro"].sum() if "Dinheiro" in df_filtered else 0
            pix_total = df_filtered["Pix"].sum() if "Pix" in df_filtered else 0
            total_pagamentos_geral = cartao_total + dinheiro_total + pix_total

            if total_pagamentos_geral > 0:
                cartao_pct = (cartao_total / total_pagamentos_geral * 100)
                dinheiro_pct = (dinheiro_total / total_pagamentos_geral * 100)
                pix_pct = (pix_total / total_pagamentos_geral * 100)
                
                payment_cols = st.columns(3)
                with payment_cols[0]:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #4c78a8, #5a8bb8); border-radius: 10px; color: white; margin-bottom: 1rem;">
                        <h3 style="margin: 0; font-size: 1.5rem;">💳 Cartão</h3>
                        <h2 style="margin: 0.5rem 0; font-size: 1.8rem;">{format_brl(cartao_total)}</h2>
                        <p style="margin: 0; font-size: 1.2rem; opacity: 0.9;">{cartao_pct:.1f}% do total</p>
                    </div>
                    """, unsafe_allow_html=True)
                with payment_cols[1]:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #54a24b, #64b25b); border-radius: 10px; color: white; margin-bottom: 1rem;">
                        <h3 style="margin: 0; font-size: 1.5rem;">💵 Dinheiro</h3>
                        <h2 style="margin: 0.5rem 0; font-size: 1.8rem;">{format_brl(dinheiro_total)}</h2>
                        <p style="margin: 0; font-size: 1.2rem; opacity: 0.9;">{dinheiro_pct:.1f}% do total</p>
                    </div>
                    """, unsafe_allow_html=True)
                with payment_cols[2]:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #f58518, #ff9528); border-radius: 10px; color: white; margin-bottom: 1rem;">
                        <h3 style="margin: 0; font-size: 1.5rem;">📱 PIX</h3>
                        <h2 style="margin: 0.5rem 0; font-size: 1.8rem;">{format_brl(pix_total)}</h2>
                        <p style="margin: 0; font-size: 1.2rem; opacity: 0.9;">{pix_pct:.1f}% do total</p>
                    </div>
                    """, unsafe_allow_html=True)
            else: 
                st.info("Sem dados de pagamento para exibir o resumo nesta seção.")
            
            st.divider()

            radial_chart = create_radial_plot(df_filtered)
            if radial_chart:
                st.altair_chart(radial_chart, use_container_width=True)
            else:
                st.info("Sem dados de pagamento para exibir o gráfico radial nos filtros selecionados.")

            st.divider()

            weekday_chart, best_day = create_enhanced_weekday_analysis(df_filtered)
            if weekday_chart:
                st.altair_chart(weekday_chart, use_container_width=True)
                
                if not df_filtered.empty and "DiaSemana" in df_filtered.columns:
                    df_weekday_analysis = df_filtered.copy()
                    df_weekday_analysis["Total"] = pd.to_numeric(df_weekday_analysis["Total"], errors="coerce")
                    df_weekday_analysis = df_weekday_analysis.dropna(subset=["Total", "DiaSemana"])
                    
                    if not df_weekday_analysis.empty:
                        dias_trabalho = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"]
                        df_trabalho = df_weekday_analysis[df_weekday_analysis["DiaSemana"].isin(dias_trabalho)]
                        
                        if not df_trabalho.empty:
                            medias_por_dia = df_trabalho.groupby("DiaSemana", observed=True)["Total"].agg(["mean", "count"]).round(2)
                            medias_por_dia = medias_por_dia.reindex([d for d in dias_trabalho if d in medias_por_dia.index])
                            medias_por_dia = medias_por_dia.sort_values("mean", ascending=False)
                            
                            st.subheader("📊 Ranking dos Dias da Semana (Seg-Sáb)")
                            col_ranking1, col_ranking2 = st.columns(2)
                            with col_ranking1:
                                st.markdown("### 🏆 **Melhores Dias**")
                                if len(medias_por_dia) >= 1: st.success(f"🥇 1º: {medias_por_dia.index[0]} ({format_brl(medias_por_dia.iloc[0, 0])} / {int(medias_por_dia.iloc[0, 1])} dias)")
                                if len(medias_por_dia) >= 2: st.info(f"🥈 2º: {medias_por_dia.index[1]} ({format_brl(medias_por_dia.iloc[1, 0])} / {int(medias_por_dia.iloc[1, 1])} dias)")
                                if len(medias_por_dia) >= 3: st.info(f"🥉 3º: {medias_por_dia.index[2]} ({format_brl(medias_por_dia.iloc[2, 0])} / {int(medias_por_dia.iloc[2, 1])} dias)")
                            with col_ranking2:
                                st.markdown("### 📉 **Piores Dias**")
                                if len(medias_por_dia) >= 3: st.warning(f"📊 Penúltimo: {medias_por_dia.index[-2]} ({format_brl(medias_por_dia.iloc[-2, 0])} / {int(medias_por_dia.iloc[-2, 1])} dias)")
                                if len(medias_por_dia) >= 1: st.error(f"🔻 Último: {medias_por_dia.index[-1]} ({format_brl(medias_por_dia.iloc[-1, 0])} / {int(medias_por_dia.iloc[-1, 1])} dias)")
                            st.divider()
                            
                            st.subheader("📅 Análise de Frequência de Trabalho (Período Filtrado)")
                            if not df_filtered.empty and "Data" in df_filtered.columns and pd.api.types.is_datetime64_any_dtype(df_filtered["Data"]):
                                data_inicio = df_filtered["Data"].min()
                                data_fim = df_filtered["Data"].max()
                                total_dias_periodo = (data_fim - data_inicio).days + 1
                                domingos_periodo = sum(1 for i in range(total_dias_periodo) if (data_inicio + timedelta(days=i)).weekday() == 6)
                                dias_uteis_esperados = total_dias_periodo - domingos_periodo
                                dias_trabalhados = len(df_filtered["Data"].dt.date.unique()) # Conta dias únicos com vendas
                                dias_falta = max(0, dias_uteis_esperados - dias_trabalhados)
                                
                                col_freq1, col_freq2, col_freq3, col_freq4 = st.columns(4)
                                with col_freq1: st.metric("📅 Período", f"{total_dias_periodo} dias", help=f"{data_inicio.strftime("%d/%m/%y")} a {data_fim.strftime("%d/%m/%y")}")
                                with col_freq2: st.metric("🏢 Dias Trabalhados", f"{dias_trabalhados} dias", help="Dias com registro de vendas")
                                with col_freq3: st.metric("🏖️ Domingos (Folga)", f"{domingos_periodo} dias", help="Domingos no período")
                                with col_freq4: st.metric("❌ Dias de Falta", f"{dias_falta} dias", help="Dias úteis s/ registro", delta=f"-{dias_falta}" if dias_falta > 0 else None)
                                
                                if dias_uteis_esperados > 0:
                                    taxa_frequencia = (dias_trabalhados / dias_uteis_esperados) * 100
                                    if taxa_frequencia >= 95: st.success(f"🎯 Excelente frequência: {taxa_frequencia:.1f}%!")
                                    elif taxa_frequencia >= 80: st.info(f"👍 Boa frequência: {taxa_frequencia:.1f}%")
                                    else: st.warning(f"⚠️ Atenção à frequência: {taxa_frequencia:.1f}%")
            else:
                st.info("📊 Dados insuficientes para calcular a análise por dia da semana.")
            
            st.divider()

            sales_histogram_chart = create_sales_histogram(df_filtered)
            if sales_histogram_chart: 
                st.altair_chart(sales_histogram_chart, use_container_width=True)
            else: 
                st.info("Dados insuficientes para o Histograma de Vendas.")
        else:
            # Mensagens de aviso se não houver dados filtrados ou processados
            if df_processed.empty and df_raw.empty and get_worksheet() is None: st.warning("Não foi possível carregar os dados da planilha.")
            elif df_processed.empty: st.info("Não há dados processados para exibir estatísticas.")
            elif df_filtered.empty: st.info("Nenhum dado corresponde aos filtros para exibir estatísticas.")
            else: st.info("Não há dados de "Total" para exibir nas Estatísticas.")

    # --- TAB ANÁLISE CONTÁBIL --- 
    with tab_contabil:
        st.header("📊 Análise Contábil e Financeira Detalhada")
        st.markdown("Esta análise segue as normas contábeis brasileiras (Simples Nacional) e apresenta a DRE anual.")
        
        with st.container(border=True):
            st.subheader("⚙️ Parâmetros para Simulação Contábil (Mensal)")
            col_param1, col_param2, col_param3 = st.columns(3)
            with col_param1: salario_minimo_input = st.number_input("💼 Salário Base Funcionário (R$)", min_value=0.0, value=1550.0, format="%.2f", help="Salário base mensal. Encargos (55%) calculados automaticamente.", key="salario_tab4")
            with col_param2: custo_contadora_input = st.number_input("📋 Honorários Contábeis (R$)", min_value=0.0, value=316.0, format="%.2f", help="Valor mensal.", key="contadora_tab4")
            with col_param3: custo_fornecedores_percentual = st.number_input("📦 Custo dos Produtos (%)", min_value=0.0, max_value=100.0, value=30.0, format="%.1f", help="% da receita bruta destinado a produtos.", key="fornecedores_tab4")

        st.markdown("---")

        if df_filtered.empty or "Total" not in df_filtered.columns:
            st.warning("📊 **Não há dados suficientes para análise contábil.** Ajuste os filtros ou registre vendas.")
        else:
            # Calcula resultados para o período filtrado (usado no dashboard e margens)
            resultados_periodo = calculate_financial_results(df_filtered, salario_minimo_input, custo_contadora_input, custo_fornecedores_percentual)

            # === DRE TEXTUAL ANUAL ===
            with st.container(border=True):
                 # Passa df_processed para ter a visão do ano inteiro
                create_dre_textual(resultados_periodo, df_processed, selected_anos_filter)

            st.markdown("---")

            # === DASHBOARD VISUAL (Período Filtrado) ===
            financial_dashboard = create_financial_dashboard_altair(resultados_periodo)
            if financial_dashboard:
                st.altair_chart(financial_dashboard, use_container_width=True)

            st.markdown("---")

            # === ANÁLISE DE MARGENS (Período Filtrado) ===
            with st.container(border=True):
                st.subheader("📈 Análise de Margens e Indicadores (Período Filtrado)")
                col_margin1, col_margin2, col_margin3 = st.columns(3)
                with col_margin1:
                    st.metric("📊 Margem Bruta", f"{resultados_periodo["margem_bruta"]:.2f}%", help="Eficiência nos custos diretos")
                    st.metric("🏛️ Carga Tributária", f"{(resultados_periodo["impostos_sobre_vendas"] / resultados_periodo["receita_bruta"] * 100) if resultados_periodo["receita_bruta"] > 0 else 0:.2f}%", help="% impostos / receita bruta")
                with col_margin2:
                    st.metric("💼 Margem Operacional", f"{resultados_periodo["margem_operacional"]:.2f}%", help="Eficiência operacional")
                    st.metric("👥 Custo Pessoal", f"{(resultados_periodo["despesas_com_pessoal"] / resultados_periodo["receita_bruta"] * 100) if resultados_periodo["receita_bruta"] > 0 else 0:.2f}%", help="% despesas pessoal / receita")
                with col_margin3:
                    st.metric("💰 Margem Líquida", f"{resultados_periodo["margem_liquida"]:.2f}%", help="Rentabilidade final")
                    st.metric("📦 Custo Produtos", f"{(resultados_periodo["custo_produtos_vendidos"] / resultados_periodo["receita_bruta"] * 100) if resultados_periodo["receita_bruta"] > 0 else 0:.2f}%", help="% CPV / receita bruta")

            st.markdown("---")

            # === RESUMO EXECUTIVO (Período Filtrado) ===
            with st.container(border=True):
                st.subheader("📋 Resumo Executivo (Período Filtrado)")
                col_exec1, col_exec2 = st.columns(2)
                with col_exec1:
                    st.markdown("**💰 Receitas:**")
                    st.write(f"• Receita Bruta: {format_brl(resultados_periodo["receita_bruta"])}")
                    st.write(f"• Receita Líquida: {format_brl(resultados_periodo["receita_liquida"])}")
                    st.markdown("**📊 Resultados:**")
                    st.write(f"• Lucro Bruto: {format_brl(resultados_periodo["lucro_bruto"])}")
                    st.write(f"• Lucro Líquido: {format_brl(resultados_periodo["lucro_liquido"])}")
                with col_exec2:
                    st.markdown("**💸 Custos e Despesas:**")
                    st.write(f"• Impostos: {format_brl(resultados_periodo["impostos_sobre_vendas"])}")
                    st.write(f"• Custo Produtos: {format_brl(resultados_periodo["custo_produtos_vendidos"])}")
                    st.write(f"• Desp. Pessoal: {format_brl(resultados_periodo["despesas_com_pessoal"])}")
                    st.write(f"• Desp. Contábeis: {format_brl(resultados_periodo["despesas_contabeis"])}")
                    st.markdown("**🎯 Indicadores:**")
                    if resultados_periodo["margem_bruta"] >= 50: st.success(f"✅ Margem Bruta: {resultados_periodo["margem_bruta"]:.1f}%")
                    elif resultados_periodo["margem_bruta"] >= 30: st.warning(f"⚠️ Margem Bruta: {resultados_periodo["margem_bruta"]:.1f}%")
                    else: st.error(f"❌ Margem Bruta: {resultados_periodo["margem_bruta"]:.1f}%")
                    if resultados_periodo["lucro_liquido"] > 0: st.success(f"✅ Resultado: {format_brl(resultados_periodo["lucro_liquido"])}")
                    else: st.error(f"❌ Resultado: {format_brl(resultados_periodo["lucro_liquido"])}")

            st.info("💡 **Nota:** DRE é anual. Dashboard, Margens e Resumo referem-se ao período filtrado.")

    # --- TAB DASHBOARD PREMIUM --- 
    with tab_premium:
        st.header("🚀 Dashboard Premium (Período Filtrado)")
        if not df_filtered.empty:
            create_premium_kpi_cards(df_filtered)
            st.markdown("---")
            col_chart1, col_chart2 = st.columns([2, 1])
            with col_chart1:
                daily_chart = create_advanced_daily_sales_chart(df_filtered)
                if daily_chart: st.altair_chart(daily_chart, use_container_width=True)
            with col_chart2:
                radial_chart = create_radial_plot(df_filtered)
                if radial_chart: st.altair_chart(radial_chart, use_container_width=True)
            st.markdown("---")
            area_chart = create_area_chart_with_gradient(df_filtered)
            if area_chart: st.altair_chart(area_chart, use_container_width=True)
            st.markdown("---")
            create_premium_insights(df_filtered)
        else:
            st.warning("⚠️ Sem dados disponíveis no período filtrado para o dashboard premium.")

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    main()