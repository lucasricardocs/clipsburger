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

# Suprimir warnings específicos do pandas
warnings.filterwarnings('ignore', category=FutureWarning, message='.*observed=False.*')

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
WORKSHEET_NAME = 'Vendas'
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/clipsburger/refs/heads/main/logo.png"

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema Financeiro - Clips Burger", layout="wide", page_icon="🍔")

# Configuração de tema para gráficos mais bonitos
alt.data_transformers.enable('json')

# Paleta de cores otimizada para modo escuro
CORES_MODO_ESCURO = ['#4c78a8', '#54a24b', '#f58518', '#e45756', '#72b7b2', '#ff9da6', '#9d755d', '#bab0ac']

# Define a ordem correta dos dias da semana e meses
dias_semana_ordem = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# CSS para melhorar a aparência e adicionar logo/aura
def inject_css():
    st.markdown(f"""
    <style>
    /* Estilos Gerais (Originais) */
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
    
    /* Dashboard Premium Styles (Originais) */
    .stApp {{
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
    }}
    
    /* Grid para gráficos do dashboard premium (Originais) */
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

    /* --- NOVOS ESTILOS PARA LOGO/TÍTULO/AURA --- */
    .title-logo-container {{
        display: flex;
        align-items: center; /* Alinha verticalmente logo e título */
        margin-bottom: 1rem; /* Espaço abaixo do título/logo */
    }}

    .logo-wrapper {{
        position: relative; /* Para posicionar a aura */
        margin-right: 1.5rem; /* Espaço entre logo e título */
        width: 200px; /* Largura fixa da logo */
        height: auto; /* Altura automática */
        flex-shrink: 0; /* Impede que a logo encolha */
    }}

    .logo-image {{
        display: block; /* Remove espaço extra abaixo da imagem */
        width: 100%; /* Faz a imagem preencher o wrapper */
        height: auto;
        position: relative; /* Garante que a imagem fique sobre a aura */
        z-index: 1;
    }}

    .logo-aura {{
        position: absolute;
        width: 110%; /* Um pouco maior que a logo */
        height: 110%;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        border-radius: 50%; /* Forma da aura */
        z-index: 0; /* Atrás da logo */
        animation: pulse-aura 2.5s infinite ease-in-out;
        pointer-events: none; /* Impede que a aura interfira com cliques */
    }}

    .main-title {{
         /* Estilos para replicar st.title aproximadamente */
        font-size: 2.25rem; 
        font-weight: 600;
        color: #ffffff; /* Cor do título no tema escuro */
        padding: 0.5rem 0rem;
        margin: 0;
        line-height: 1.4;
    }}

    @keyframes pulse-aura {{
        0% {{
            box-shadow: 0 0 10px 3px rgba(255, 255, 255, 0.25), 
                        0 0 20px 10px rgba(255, 255, 255, 0.15), 
                        0 0 35px 20px rgba(255, 255, 255, 0.05);
            opacity: 0.6;
        }}
        50% {{
            box-shadow: 0 0 20px 7px rgba(255, 255, 255, 0.45), 
                        0 0 40px 20px rgba(255, 255, 255, 0.25), 
                        0 0 60px 35px rgba(255, 255, 255, 0.1);
            opacity: 1;
        }}
        100% {{
            box-shadow: 0 0 10px 3px rgba(255, 255, 255, 0.25), 
                        0 0 20px 10px rgba(255, 255, 255, 0.15), 
                        0 0 35px 20px rgba(255, 255, 255, 0.05);
            opacity: 0.6;
        }}
    }}
    /* --- FIM DOS NOVOS ESTILOS --- */

    </style>
    """, unsafe_allow_html=True)

# --- Funções de Cache para Acesso ao Google Sheets ---
@st.cache_resource
def get_google_auth():
    """Autoriza o acesso ao Google Sheets e retorna o cliente gspread."""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/spreadsheets.readonly',
              'https://www.googleapis.com/auth/drive.readonly']
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
            
            # Garantir que colunas de pagamento existam e sejam numéricas
            for col in ['Cartão', 'Dinheiro', 'Pix']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                else:
                    df[col] = 0 # Cria a coluna com zeros se não existir
            
            # Garantir que a coluna 'Data' exista
            if 'Data' not in df.columns:
                # Se não existir, tenta criar a partir de alguma coluna de data conhecida ou retorna erro/aviso
                # Neste caso, vamos criar vazia para evitar erros posteriores, mas idealmente deveria tratar
                df['Data'] = pd.NaT 
                st.warning("Coluna 'Data' não encontrada na planilha. As análises de data podem falhar.")

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
    
    # Colunas numéricas e de data esperadas/criadas
    cols_to_ensure_numeric = ['Cartão', 'Dinheiro', 'Pix', 'Total']
    cols_to_ensure_date_derived = ['Ano', 'Mês', 'MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana', 'DiaDoMes']
    
    # Se o DataFrame de entrada estiver vazio, retorna um DataFrame vazio com a estrutura esperada
    if df.empty:
        all_expected_cols = ['Data'] + cols_to_ensure_numeric + cols_to_ensure_date_derived
        empty_df = pd.DataFrame(columns=all_expected_cols)
        # Define tipos de dados para evitar erros
        for col in cols_to_ensure_numeric:
            empty_df[col] = pd.Series(dtype='float')
        for col in cols_to_ensure_date_derived:
            # Define tipos apropriados para colunas derivadas de data
            empty_df[col] = pd.Series(dtype='object' if col in ['MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana'] else 'float')
        empty_df['Data'] = pd.Series(dtype='datetime64[ns]')
        return empty_df

    # Garante que as colunas de pagamento são numéricas
    for col in ['Cartão', 'Dinheiro', 'Pix']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0

    # Calcula o Total
    df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']

    # Processamento da coluna 'Data'
    if 'Data' in df.columns and not df['Data'].isnull().all():
        try:
            # Tenta converter string para datetime (prioriza dia primeiro)
            if pd.api.types.is_string_dtype(df['Data']):
                df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
                # Se falhar, tenta formato padrão
                if df['Data'].isnull().all():
                    df['Data'] = pd.to_datetime(df_input['Data'], errors='coerce')
            elif not pd.api.types.is_datetime64_any_dtype(df['Data']):
                 df['Data'] = pd.to_datetime(df['Data'], errors='coerce') # Converte outros tipos se não for datetime
            
            df.dropna(subset=['Data'], inplace=True) # Remove linhas onde a data não pôde ser convertida

            # Cria colunas derivadas se houver datas válidas
            if not df.empty:
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month

                # Mapeamento seguro para nomes de meses
                try:
                    # Tenta usar strftime, mas verifica se o resultado é texto
                    df['MêsNome'] = df['Data'].dt.strftime('%B').str.capitalize()
                    if not df['MêsNome'].dtype == 'object' or df['MêsNome'].str.isnumeric().any():
                         # Fallback para mapeamento manual se strftime falhar
                         df['MêsNome'] = df['Mês'].map(lambda x: meses_ordem[int(x)-1] if pd.notna(x) and 1 <= int(x) <= 12 else "Inválido")
                except Exception:
                     # Fallback em caso de erro no strftime
                    df['MêsNome'] = df['Mês'].map(lambda x: meses_ordem[int(x)-1] if pd.notna(x) and 1 <= int(x) <= 12 else "Inválido")

                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                
                # Mapeamento para dias da semana
                day_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
                df['DiaSemana'] = df['Data'].dt.dayofweek.map(day_map)
                df['DiaDoMes'] = df['Data'].dt.day

                # Ordenar dias da semana
                df['DiaSemana'] = pd.Categorical(df['DiaSemana'], categories=[d for d in dias_semana_ordem if d in df['DiaSemana'].unique()], ordered=True)
            else:
                # Se o DataFrame ficar vazio após dropna, cria colunas vazias
                for col in cols_to_ensure_date_derived:
                    df[col] = pd.Series(dtype='object' if col in ['MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana'] else 'float')
        except Exception as e:
            st.error(f"Erro crítico ao processar a coluna 'Data': {e}. Verifique o formato das datas na planilha.")
            # Cria colunas vazias em caso de erro
            for col in cols_to_ensure_date_derived:
                df[col] = pd.Series(dtype='object' if col in ['MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana'] else 'float')
    else:
        # Se a coluna 'Data' não existe ou está toda nula
        if 'Data' not in df.columns:
            st.warning("Coluna 'Data' não encontrada no DataFrame. Algumas análises temporais não estarão disponíveis.")
            df['Data'] = pd.NaT # Adiciona coluna Data vazia se não existir
        # Cria colunas derivadas vazias
        for col in cols_to_ensure_date_derived:
            df[col] = pd.Series(dtype='object' if col in ['MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana'] else 'float')
            
    return df

# --- Funções de Gráficos Interativos em Altair ---
def create_radial_plot(df):
    """Cria um gráfico radial plot substituindo o gráfico de pizza."""
    if df.empty or not any(col in df.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
        return None
    
    payment_data = pd.DataFrame({
        'Método': ['Cartão', 'Dinheiro', 'PIX'],
        'Valor': [df['Cartão'].sum(), df['Dinheiro'].sum(), df['Pix'].sum()]
    })
    payment_data = payment_data[payment_data['Valor'] > 0]
    
    if payment_data.empty:
        return None

    # Criar gráfico radial plot usando Altair
    base = alt.Chart(payment_data).encode(
        theta=alt.Theta('Valor:Q', stack=True),
        radius=alt.Radius('Valor:Q', scale=alt.Scale(type='sqrt', zero=True, rangeMin=20)),
        color=alt.Color(
            'Método:N', 
            scale=alt.Scale(range=CORES_MODO_ESCURO[:3]),
            legend=alt.Legend(
                title="Método de Pagamento",
                orient='bottom',
                direction='horizontal',
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
            alt.Tooltip('Método:N', title='Método'),
            alt.Tooltip('Valor:Q', title='Valor (R$)', format=',.2f')
        ]
    )

    radial_plot = base.mark_arc(
        innerRadius=20, 
        stroke='white', 
        strokeWidth=2
    ).properties(
        title=alt.TitleParams(
            text='Gráfico Radial de Métodos de Pagamento', 
            fontSize=16,
            anchor='start'
        ),
        width=500,
        height=500,
        padding={'bottom': 100}
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )

    return radial_plot

# --- MODIFICADO: Gráfico de Área Acumulado ---
def create_cumulative_area_chart(df):
    """Cria gráfico de área ACUMULADO com gradiente."""
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        return None
    
    df_sorted = df.sort_values('Data').copy()
    
    if df_sorted.empty:
        return None

    # Calcula o total acumulado
    df_sorted['Total_Acumulado'] = df_sorted['Total'].cumsum()
    
    area_chart = alt.Chart(df_sorted).mark_area(
        interpolate='monotone',
        line={'color': CORES_MODO_ESCURO[0], 'strokeWidth': 3},
        color=alt.Gradient(
            gradient='linear',
            stops=[
                alt.GradientStop(color=CORES_MODO_ESCURO[0], offset=0),
                alt.GradientStop(color=CORES_MODO_ESCURO[4], offset=1)
            ],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X(
            'Data:T', 
            title='Data', 
            axis=alt.Axis(format='%d/%m', labelAngle=-45, labelFontSize=12)
        ),
        y=alt.Y(
            'Total_Acumulado:Q', # Modificado para usar o acumulado
            title='Total de Vendas Acumulado (R$)', # Modificado
            axis=alt.Axis(labelFontSize=12)
        ),
        tooltip=[
            alt.Tooltip('DataFormatada:N', title='Data'),
            alt.Tooltip('Total:Q', title='Venda do Dia (R$)', format=',.2f'), # Tooltip ainda mostra venda do dia
            alt.Tooltip('Total_Acumulado:Q', title='Total Acumulado (R$)', format=',.2f') # Tooltip mostra acumulado
        ]
    ).properties(
        title=alt.TitleParams(
            text='Evolução Acumulada das Vendas', # Modificado
            fontSize=18,
            anchor='start'
        ),
        height=500,
        width=1000 # Mantido, mas será ajustado pelo container no layout
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    return area_chart
# --- FIM DA MODIFICAÇÃO DO GRÁFICO ---

def create_advanced_daily_sales_chart(df):
    """Cria um gráfico de vendas diárias sem animação."""
    if df.empty or 'Data' not in df.columns:
        return None
    
    df_sorted = df.sort_values('Data').copy()
    
    if df_sorted.empty:
        return None
    
    df_melted = df_sorted.melt(
        id_vars=['Data', 'DataFormatada', 'Total'],
        value_vars=['Cartão', 'Dinheiro', 'Pix'],
        var_name='Método',
        value_name='Valor'
    )
    
    df_melted = df_melted[df_melted['Valor'] > 0]
    
    if df_melted.empty:
        return None
    
    bars = alt.Chart(df_melted).mark_bar(
        size=20 # Tamanho das barras
    ).encode(
        x=alt.X(
            'Data:T',
            title='Data',
            axis=alt.Axis(format='%d/%m', labelAngle=-45, labelFontSize=12)
        ),
        y=alt.Y(
            'Valor:Q',
            title='Valor (R$)',
            stack='zero', # Empilha as barras
            axis=alt.Axis(labelFontSize=12)
        ),
        color=alt.Color(
            'Método:N',
            scale=alt.Scale(range=CORES_MODO_ESCURO[:3]),
            legend=alt.Legend(
                title="Método de Pagamento",
                orient='bottom',
                direction='horizontal',
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
            alt.Tooltip('DataFormatada:N', title='Data'),
            alt.Tooltip('Método:N', title='Método'),
            alt.Tooltip('Valor:Q', title='Valor (R$)', format=',.2f')
        ]
    ).properties(
        title=alt.TitleParams(
            text="Vendas Diárias por Método de Pagamento",
            fontSize=16,
            anchor='start'
        ),
        height=500,
        width=1000, # Mantido, mas será ajustado pelo container
        padding={'bottom': 100} # Espaço para legenda
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    return bars

def create_enhanced_weekday_analysis(df):
    """Cria análise de vendas por dia da semana sem animação."""
    if df.empty or 'DiaSemana' not in df.columns or 'Total' not in df.columns:
        return None, None
    
    df_copy = df.copy()
    df_copy['Total'] = pd.to_numeric(df_copy['Total'], errors='coerce')
    df_copy.dropna(subset=['Total', 'DiaSemana'], inplace=True)
    
    if df_copy.empty:
        return None, None
    
    # Agrupa e calcula média, soma e contagem
    weekday_stats = df_copy.groupby('DiaSemana', observed=True).agg(
        Total_Sum=('Total', 'sum'),
        Total_Mean=('Total', 'mean'),
        Count=('Total', 'count')
    ).round(2)
    
    # Renomeia colunas de forma mais clara
    weekday_stats.rename(columns={'Total_Sum': 'Total', 'Total_Mean': 'Média', 'Count': 'Dias_Vendas'}, inplace=True)
    
    # Reordena de acordo com dias_semana_ordem e remove dias não presentes nos dados
    weekday_stats = weekday_stats.reindex([d for d in dias_semana_ordem if d in weekday_stats.index])
    weekday_stats.reset_index(inplace=True) # Transforma o índice 'DiaSemana' em coluna
    
    if weekday_stats.empty:
        return None, None

    # Cria o gráfico de barras
    chart = alt.Chart(weekday_stats).mark_bar(
        color=CORES_MODO_ESCURO[1], # Cor verde
        opacity=0.9,
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5
    ).encode(
        x=alt.X(
            'DiaSemana:O',
            title='Dia da Semana',
            sort=dias_semana_ordem, # Garante a ordem correta no eixo
            axis=alt.Axis(labelAngle=-45, labelFontSize=12)
        ),
        y=alt.Y(
            'Média:Q',
            title='Média de Vendas (R$)',
            axis=alt.Axis(labelFontSize=12)
        ),
        tooltip=[
            alt.Tooltip('DiaSemana:N', title='Dia da Semana'),
            alt.Tooltip('Média:Q', title='Média (R$)', format=',.2f'),
            alt.Tooltip('Total:Q', title='Total Vendas (R$)', format=',.2f'),
            alt.Tooltip('Dias_Vendas:Q', title='Nº Dias com Vendas')
        ]
    ).properties(
        title=alt.TitleParams(
            text="Média de Vendas por Dia da Semana",
            fontSize=18,
            anchor='start'
        ),
        height=600,
        width=1000, # Será ajustado pelo container
        padding={'bottom': 100} # Espaço para eixo X rotacionado
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    # Encontra o dia com a maior média
    best_day = weekday_stats.loc[weekday_stats['Média'].idxmax(), 'DiaSemana'] if not weekday_stats.empty else "N/A"
    
    return chart, best_day

def create_sales_histogram(df, title="Distribuição dos Valores de Venda Diários"):
    """Histograma sem animação."""
    if df.empty or 'Total' not in df.columns or df['Total'].isnull().all():
        return None
    
    # Filtra vendas com valor > 0 para o histograma
    df_filtered_hist = df[df['Total'] > 0].copy()
    if df_filtered_hist.empty:
        return None
    
    histogram = alt.Chart(df_filtered_hist).mark_bar(
        color=CORES_MODO_ESCURO[0], # Cor azul
        opacity=0.8,
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5
    ).encode(
        x=alt.X(
            "Total:Q",
            bin=alt.Bin(maxbins=20), # Agrupa em até 20 faixas
            title="Faixa de Valor da Venda Diária (R$)",
            axis=alt.Axis(labelFontSize=12)
        ),
        y=alt.Y(
            'count():Q',
            title='Número de Dias (Frequência)',
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
            anchor='start'
        ),
        height=600,
        width=1000, # Será ajustado pelo container
        padding={'bottom': 100} # Espaço para eixo X
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    return histogram

def analyze_sales_by_weekday(df):
    """Analisa vendas por dia da semana (Função auxiliar, pode ser redundante com create_enhanced_weekday_analysis)."""
    # Esta função parece calcular apenas a média e o melhor dia, 
    # create_enhanced_weekday_analysis já faz isso e gera o gráfico.
    # Pode ser removida ou mantida se usada em outro lugar.
    if df.empty or 'DiaSemana' not in df.columns or 'Total' not in df.columns or df['DiaSemana'].isnull().all() or df['Total'].isnull().all():
        return None, None
    
    try:
        df_copy = df.copy()
        df_copy['Total'] = pd.to_numeric(df_copy['Total'], errors='coerce')
        df_copy.dropna(subset=['Total', 'DiaSemana'], inplace=True)
        
        if df_copy.empty:
            return None, None
        
        # Calcula a média e reordena
        avg_sales_weekday = df_copy.groupby('DiaSemana', observed=True)['Total'].mean().reindex(dias_semana_ordem).dropna()
        
        if not avg_sales_weekday.empty:
            best_day = avg_sales_weekday.idxmax()
            return best_day, avg_sales_weekday
        else:
            return None, avg_sales_weekday
    except Exception as e:
        st.error(f"Erro ao analisar vendas por dia da semana: {e}")
        return None, None

# --- Funções de Cálculos Financeiros ---
def calculate_financial_results(df, salario_minimo, custo_contadora, custo_fornecedores_percentual):
    """Calcula os resultados financeiros com base nos dados de vendas seguindo normas contábeis."""
    results = {
        'receita_bruta': 0, 'receita_tributavel': 0, 'receita_nao_tributavel': 0,
        'impostos_sobre_vendas': 0, 'receita_liquida': 0, 'custo_produtos_vendidos': 0,
        'lucro_bruto': 0, 'margem_bruta': 0, 'despesas_administrativas': 0,
        'despesas_com_pessoal': 0, 'despesas_contabeis': 0, # Inicializa zerado
        'total_despesas_operacionais': 0, 'lucro_operacional': 0, 'margem_operacional': 0,
        'lucro_antes_ir': 0, 'lucro_liquido': 0, 'margem_liquida': 0,
        'diferenca_tributavel_nao_tributavel': 0
    }
    
    if df.empty: 
        return results
    
    # Cálculos baseados no DataFrame filtrado
    results['receita_bruta'] = df['Total'].sum()
    results['receita_tributavel'] = df['Cartão'].sum() + df['Pix'].sum()
    results['receita_nao_tributavel'] = df['Dinheiro'].sum()
    results['impostos_sobre_vendas'] = results['receita_tributavel'] * 0.06 # Exemplo Simples Nacional
    results['receita_liquida'] = results['receita_bruta'] - results['impostos_sobre_vendas']
    results['custo_produtos_vendidos'] = results['receita_bruta'] * (custo_fornecedores_percentual / 100)
    results['lucro_bruto'] = results['receita_liquida'] - results['custo_produtos_vendidos']
    
    if results['receita_liquida'] > 0:
        results['margem_bruta'] = (results['lucro_bruto'] / results['receita_liquida']) * 100
    
    # Calcula o número de meses únicos no período filtrado para ajustar despesas fixas
    num_months = 1 # Default
    if not df.empty and 'AnoMês' in df.columns and df['AnoMês'].nunique() > 0:
        num_months = df['AnoMês'].nunique()
        
    results['despesas_com_pessoal'] = (salario_minimo * 1.55) * num_months # Ajustado para período
    results['despesas_contabeis'] = custo_contadora * num_months # Ajustado para período
    results['despesas_administrativas'] = 0 # Adicionar outras despesas aqui se houver
    results['total_despesas_operacionais'] = (
        results['despesas_com_pessoal'] + 
        results['despesas_contabeis'] + 
        results['despesas_administrativas']
    )
    
    results['lucro_operacional'] = results['lucro_bruto'] - results['total_despesas_operacionais']
    if results['receita_liquida'] > 0:
        results['margem_operacional'] = (results['lucro_operacional'] / results['receita_liquida']) * 100
    
    results['lucro_antes_ir'] = results['lucro_operacional'] # Simplificado (sem juros, etc.)
    # Imposto de Renda (simplificado, considerar regime tributário)
    # results['imposto_renda'] = results['lucro_antes_ir'] * 0.15 # Exemplo
    # results['lucro_liquido'] = results['lucro_antes_ir'] - results['imposto_renda']
    results['lucro_liquido'] = results['lucro_antes_ir'] # Simplificado: Lucro líquido = Lucro antes IR
    
    if results['receita_liquida'] > 0:
        results['margem_liquida'] = (results['lucro_liquido'] / results['receita_liquida']) * 100
    
    results['diferenca_tributavel_nao_tributavel'] = results['receita_nao_tributavel'] # Pode ser usado para análise fiscal
    
    return results

def create_dre_textual(resultados, df_processed, selected_anos_filter):
    """Cria uma apresentação textual do DRE no estilo tradicional contábil usando dados anuais."""
    def format_val(value):
        # Formata como inteiro com separador de milhar
        return f"{value:,.0f}".replace(",", ".")

    # Determinar o ano para o DRE
    if selected_anos_filter and len(selected_anos_filter) == 1:
        # Se um único ano foi selecionado no filtro principal, usa ele
        ano_dre = selected_anos_filter[0]
    elif not df_processed.empty and 'Ano' in df_processed.columns and not df_processed['Ano'].isnull().all():
        # Se múltiplos anos ou nenhum selecionado, pega o último ano dos dados GERAIS
        ano_dre = int(df_processed['Ano'].max()) 
    else:
        # Fallback para o ano atual se não houver dados
        ano_dre = datetime.now().year 

    # Filtrar dados GERAIS (df_processed) APENAS pelo ano do DRE
    if not df_processed.empty and 'Ano' in df_processed.columns:
        df_ano = df_processed[df_processed['Ano'] == ano_dre].copy()
        
        # Recalcular resultados com dados do ano completo
        if not df_ano.empty:
            # Usa valores MENSAIS das configurações para cálculo base
            salario_mensal = st.session_state.get('salario_tab4', 1550.0)
            contadora_mensal = st.session_state.get('contadora_tab4', 316.0)
            fornecedores_perc = st.session_state.get('fornecedores_tab4', 30.0)
            
            # Recalcula resultados ANUAIS (a função calculate_financial_results ajusta despesas para o período do df_ano)
            resultados_ano = calculate_financial_results(
                df_ano, 
                salario_mensal, 
                contadora_mensal, 
                fornecedores_perc
            )
            # IMPORTANTE: A função calculate_financial_results já multiplica pelo número de meses (12 neste caso).
            # Não é necessário multiplicar novamente aqui.

        else:
            # Se não houver dados para o ano, ZERAR os resultados para evitar confusão
            resultados_ano = {key: 0 for key in resultados.keys()}
            st.warning(f"⚠️ Não há dados de vendas registrados para o ano {ano_dre}. O DRE está zerado.")
    else:
        # Se df_processed estiver vazio, ZERAR os resultados
        resultados_ano = {key: 0 for key in resultados.keys()}
        st.warning(f"⚠️ Não há dados de vendas disponíveis para gerar o DRE do ano {ano_dre}.")

    # --- Montagem do DRE Textual ---
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 30px;">
        <h3 style="margin: 0; font-weight: normal;">DEMONSTRAÇÃO DO RESULTADO DO EXERCÍCIO</h3>
        <p style="margin: 5px 0; font-style: italic;">Clips Burger - Exercício {ano_dre}</p>
    </div>
    <div style="text-align: right; margin-bottom: 20px;">
        <p style="margin: 0; font-size: 14px; font-weight: bold;">Em R$</p>
    </div>
    """, unsafe_allow_html=True)

    # Usar colunas para alinhar descrição e valor
    col1, col2 = st.columns([6, 2])
    
    with col1: st.markdown("**RECEITA BRUTA**")
    with col2: st.markdown(f"**{format_val(resultados_ano['receita_bruta'])}**", unsafe_allow_html=True)
    
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**(-) DEDUÇÕES**")
    with col2: st.markdown("") # Linha de título para deduções
    
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Simples Nacional (s/ Cartão e Pix)")
    with col2: st.markdown(f"({format_val(resultados_ano['impostos_sobre_vendas'])})", unsafe_allow_html=True)
    
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**= RECEITA LÍQUIDA**")
    with col2: st.markdown(f"**{format_val(resultados_ano['receita_liquida'])}**", unsafe_allow_html=True)
    
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**(-) CUSTO DOS PRODUTOS VENDIDOS**")
    with col2: st.markdown(f"**({format_val(resultados_ano['custo_produtos_vendidos'])})**", unsafe_allow_html=True)
    
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**= LUCRO BRUTO**")
    with col2: st.markdown(f"**{format_val(resultados_ano['lucro_bruto'])}**", unsafe_allow_html=True)
    
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**(-) DESPESAS OPERACIONAIS**")
    # Exibe o total das despesas operacionais na linha principal
    with col2: st.markdown(f"**({format_val(resultados_ano['total_despesas_operacionais'])})**", unsafe_allow_html=True)
    
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Despesas com Pessoal (Salário Base x 1.55 x 12)")
    with col2: st.markdown(f"({format_val(resultados_ano['despesas_com_pessoal'])})", unsafe_allow_html=True) 
    
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Serviços Contábeis (Custo Mensal x 12)")
    with col2: st.markdown(f"({format_val(resultados_ano['despesas_contabeis'])})", unsafe_allow_html=True)
    
    # Adicionar outras despesas administrativas se houver
    # col1, col2 = st.columns([6, 2])
    # with col1: st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Outras Despesas Adm.")
    # with col2: st.markdown(f"({format_val(resultados_ano['despesas_administrativas'])})", unsafe_allow_html=True)

    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**= LUCRO OPERACIONAL**")
    with col2: st.markdown(f"**{format_val(resultados_ano['lucro_operacional'])}**", unsafe_allow_html=True)
    
    # Resultado Financeiro (Simplificado)
    # col1, col2 = st.columns([6, 2])
    # with col1: st.markdown("(+/-) Resultado Financeiro")
    # with col2: st.markdown("0") # Adicionar se houver

    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**= LUCRO ANTES DO IMPOSTO DE RENDA (LAIR)**")
    with col2: st.markdown(f"**{format_val(resultados_ano['lucro_antes_ir'])}**", unsafe_allow_html=True)
    
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("**(-) Provisão para Imposto de Renda e CSLL**")
    with col2: st.markdown("**-**") # Assumindo que não há IR/CSLL para Simples nesse exemplo
    
    # Linha de separação
    st.markdown("---")
    
    # RESULTADO LÍQUIDO - destacado
    col1, col2 = st.columns([6, 2])
    with col1: st.markdown("### **= RESULTADO LÍQUIDO DO EXERCÍCIO**")
    with col2: st.markdown(f"### **{format_val(resultados_ano['lucro_liquido'])}**", unsafe_allow_html=True)
    
    # Nota explicativa
    st.info(f"📅 **Nota:** Este DRE apresenta os resultados consolidados do exercício de {ano_dre}, calculado com base nos custos definidos e nas vendas totais do ano.")

def create_financial_dashboard_altair(resultados):
    """Dashboard financeiro com barras horizontais para composição do resultado."""
    # Prepara os dados para o gráfico de cascata/composição
    financial_data = pd.DataFrame({
        'Categoria': [
            'Receita Bruta',
            'Impostos s/ Vendas',
            'Custo Produtos',
            'Despesas Pessoal',
            'Serviços Contábeis',
            # Adicionar outras despesas aqui se houver
            'Lucro Líquido' # O lucro líquido é o resultado final
        ],
        'Valor': [
            resultados['receita_bruta'],
            -resultados['impostos_sobre_vendas'], # Negativo pois é dedução
            -resultados['custo_produtos_vendidos'], # Negativo
            -resultados['despesas_com_pessoal'], # Negativo
            -resultados['despesas_contabeis'], # Negativo
            # Adicionar outras despesas negativas
            resultados['lucro_liquido'] # Positivo ou negativo, conforme o resultado
        ],
        'Tipo': [
            'Receita',
            'Dedução',
            'CPV',
            'Despesa',
            'Despesa',
            # 'Despesa' para outras
            'Resultado' # Tipo para o lucro líquido
        ]
    })
    
    # Filtrar categorias com valor zero para não poluir o gráfico
    financial_data = financial_data[financial_data['Valor'] != 0]

    if financial_data.empty:
        st.info("Sem dados financeiros para exibir o gráfico de composição no período selecionado.")
        return None

    # Define a ordem das categorias no gráfico
    category_order = [
        'Receita Bruta', 'Impostos s/ Vendas', 'Custo Produtos', 
        'Despesas Pessoal', 'Serviços Contábeis', 'Lucro Líquido'
    ]
    # Filtra a ordem para incluir apenas categorias presentes nos dados
    filtered_order = [cat for cat in category_order if cat in financial_data['Categoria'].tolist()]

    # Cria o gráfico de barras horizontais
    chart = alt.Chart(financial_data).mark_bar(
        cornerRadiusTopRight=8,
        cornerRadiusBottomRight=8
    ).encode(
        x=alt.X(
            'Valor:Q',
            title='Valor (R$)',
            axis=alt.Axis(format=',.0f', labelFontSize=12) # Formato inteiro
        ),
        y=alt.Y(
            'Categoria:O',
            title=None, # Sem título no eixo Y
            sort=filtered_order, # Ordena as barras conforme definido
            axis=alt.Axis(labelFontSize=12)
        ),
        color=alt.Color(
            'Tipo:N',
            scale=alt.Scale(
                # Define cores para cada tipo
                domain=['Receita', 'Dedução', 'CPV', 'Despesa', 'Resultado'],
                range=[CORES_MODO_ESCURO[1], CORES_MODO_ESCURO[3], CORES_MODO_ESCURO[2], CORES_MODO_ESCURO[4], CORES_MODO_ESCURO[0]]
            ),
            legend=alt.Legend(
                title="Tipo",
                orient='bottom',
                direction='horizontal',
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
            alt.Tooltip('Categoria:N', title='Categoria'),
            alt.Tooltip('Valor:Q', title='Valor (R$)', format=',.2f'),
            alt.Tooltip('Tipo:N', title='Tipo')
        ]
    ).properties(
        title=alt.TitleParams(
            text="Composição do Resultado Financeiro (Período Filtrado)", 
            fontSize=20,
            anchor='start'
        ),
        # Altura dinâmica baseada no número de barras para evitar sobreposição
        height=alt.Step(40 * len(filtered_order)), 
        width=1000, # Será ajustado pelo container
        padding={'bottom': 100} # Espaço para legenda
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    return chart

# --- Funções Auxiliares ---
def format_brl(value):
    """Formata um valor numérico como moeda brasileira (BRL)."""
    try:
        # Garante que o valor é numérico antes de formatar
        numeric_value = pd.to_numeric(value, errors='coerce')
        if pd.isna(numeric_value):
            return "R$ 0,00"
        return f"R$ {numeric_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        # Retorna um valor padrão em caso de erro inesperado
        return "R$ 0,00"

# --- Dashboard Premium Functions ---
def create_premium_kpi_cards(df):
    """Cria cards KPI premium com emoticons DENTRO dos boxes."""
    # Define valores padrão caso o DataFrame esteja vazio
    if df.empty:
        total_vendas = 0
        media_diaria = 0
        melhor_dia_str = "N/A"
        melhor_dia_valor = 0
        crescimento = 0.0
        delta_text = "Dados insuficientes"
    else:
        total_vendas = df['Total'].sum()
        media_diaria = df['Total'].mean()
        
        # Encontra o melhor dia (data e valor)
        if not df.empty and 'Data' in df.columns and not df['Total'].empty:
            best_day_idx = df['Total'].idxmax()
            melhor_dia_data = df.loc[best_day_idx, 'Data']
            melhor_dia_str = melhor_dia_data.strftime('%d/%m/%Y') if pd.notna(melhor_dia_data) else "N/A"
            melhor_dia_valor = df.loc[best_day_idx, 'Total']
        else:
            melhor_dia_str = "N/A"
            melhor_dia_valor = 0

        # Cálculo de tendência (últimos 7 dias vs 7 dias anteriores)
        crescimento = 0.0
        delta_text = None
        df_sorted = df.sort_values('Data') # Garante ordenação por data
        if len(df_sorted) >= 14:
            ultimos_7_dias = df_sorted['Total'].tail(7).mean()
            anteriores_7_dias = df_sorted['Total'].iloc[-14:-7].mean()
            if anteriores_7_dias > 0:
                crescimento = ((ultimos_7_dias - anteriores_7_dias) / anteriores_7_dias) * 100
                delta_text = f"{crescimento:+.1f}% vs 7 dias ant."
            elif ultimos_7_dias > 0:
                 delta_text = "↑ Apenas últimos 7 dias"
                 crescimento = np.inf # Indica crescimento a partir de zero
            else:
                 delta_text = "Sem vendas recentes"
        elif len(df_sorted) >= 7:
             delta_text = "Dados insuficientes (<14 dias)"
        else:
             delta_text = "Dados insuficientes (<7 dias)"

    # Exibe os KPIs em colunas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 Faturamento Total (Período)",
            value=format_brl(total_vendas),
        )
    
    with col2:
        st.metric(
            label="📊 Média Diária (Período)",
            value=format_brl(media_diaria),
        )
    
    with col3:
        st.metric(
            label=f"🏆 Melhor Dia ({melhor_dia_str})",
            value=format_brl(melhor_dia_valor) if melhor_dia_str != "N/A" else "N/A",
            delta="Maior faturamento" if melhor_dia_str != "N/A" else None
        )
    
    with col4:
        # Define a cor do delta baseado no crescimento
        delta_color = "normal" # Padrão
        if crescimento > 0: delta_color = "inverse"
        elif crescimento < 0: delta_color = "normal" # Streamlit usa vermelho por padrão para negativo
        
        st.metric(
            label="📈 Tendência (Últimos 7 dias)",
            value=f"{crescimento:.1f}%" if delta_text and '%' in delta_text else "--",
            delta=delta_text,
            delta_color=delta_color
        )

# --- NOVA FUNÇÃO: Gráfico Heatmap de Atividade ---
def create_activity_heatmap(df_input):
    """Cria um gráfico de heatmap estilo GitHub para a atividade de vendas."""
    if df_input.empty or 'Data' not in df_input.columns or 'Total' not in df_input.columns:
        st.info("Dados insuficientes para gerar o heatmap de atividade.")
        return None

    df = df_input.copy()
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    df.dropna(subset=['Data'], inplace=True)
    
    if df.empty:
        st.info("Dados insuficientes após processamento para gerar o heatmap de atividade.")
        return None

    # Determinar o ano (ou anos) a ser exibido - Pega o ano mais recente dos dados filtrados
    current_year = df['Data'].dt.year.max()
    if pd.isna(current_year):
         st.info("Não foi possível determinar o ano para o heatmap.")
         return None
    current_year = int(current_year)
    df = df[df['Data'].dt.year == current_year].copy() # Filtra pelo ano mais recente

    if df.empty:
        st.info(f"Sem dados para o ano {current_year} para gerar o heatmap.")
        return None

    # Criar todas as datas do ano selecionado
    start_date = datetime(current_year, 1, 1)
    end_date = datetime(current_year, 12, 31)
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')

    # Agrupa vendas por dia (caso haja múltiplas entradas no mesmo dia)
    daily_sales = df.groupby(df['Data'].dt.date)['Total'].sum().reset_index()
    daily_sales['Data'] = pd.to_datetime(daily_sales['Data'])

    # Merge com todas as datas do ano, preenchendo dias sem venda com 0
    full_df = pd.DataFrame({'Data': all_dates})
    full_df = pd.merge(full_df, daily_sales, on='Data', how='left').fillna(0)

    # Calcular semana do ano e dia da semana (Segunda=0, Domingo=6)
    full_df['week'] = full_df['Data'].dt.isocalendar().week
    full_df['weekday'] = full_df['Data'].dt.dayofweek # Segunda=0, Domingo=6

    # Ajustar semanas que podem pertencer ao ano anterior/seguinte no início/fim do ano
    # Semana 53 que pertence ao início do ano -> Semana 0
    full_df.loc[(full_df['Data'].dt.month == 1) & (full_df['week'] >= 52), 'week'] = 0
    # Semana 1 que pertence ao final do ano -> Semana 53 (ou max_week + 1)
    max_week = full_df['week'].max()
    full_df.loc[(full_df['Data'].dt.month == 12) & (full_df['week'] == 1), 'week'] = max_week + 1
    
    # Mapear nomes dos meses e formatar data para tooltip
    full_df['MesNome'] = full_df['Data'].dt.strftime('%B').str.capitalize()
    full_df['DataStr'] = full_df['Data'].dt.strftime('%d/%m/%Y')

    # Criar o heatmap
    heatmap = alt.Chart(full_df).mark_rect(
        stroke='rgba(255, 255, 255, 0.1)', # Borda sutil entre os quadrados
        strokeWidth=0.5
    ).encode(
        x=alt.X('week:O', title='Semana do Ano', axis=None), # Oculta eixo X (número da semana)
        y=alt.Y('weekday:O', title=None, sort=np.arange(7), axis=alt.Axis(labels=True, ticks=False, domain=False, title=None, labelExpr="['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'][datum.value]")), # Eixo Y com dias da semana abreviados
        color=alt.Color('Total:Q', 
                        scale=alt.Scale(range=['#2a2a3a', CORES_MODO_ESCURO[1]], type='log', base=10, clamp=True), # Escala log para melhor visualização de variações, cores do tema
                        legend=alt.Legend(title="Vendas (R$)", orient='bottom', direction='horizontal', padding=10, titlePadding=10)),
        tooltip=[
            alt.Tooltip('DataStr:N', title='Data'),
            alt.Tooltip('Total:Q', title='Vendas (R$)', format=',.2f')
        ]
    ).properties(
        title=alt.TitleParams(f"Heatmap de Atividade de Vendas - {current_year}", fontSize=18, anchor='start'),
        width=1000, # Será ajustado pelo container
        height=150 # Altura fixa para visualização compacta estilo GitHub
    ).configure_view(
        stroke=None # Remove borda ao redor do gráfico
    ).configure(
        background='transparent'
    )

    return heatmap

# --- Layout Principal do Streamlit ---

# Injeta o CSS (incluindo estilos da logo/aura)
inject_css()

# --- MODIFICADO: Título Principal com Logo e Aura ---
st.markdown(f"""
<div class="title-logo-container">
    <div class="logo-wrapper">
        <div class="logo-aura"></div>
        <img src="{LOGO_URL}" alt="Clips Burger Logo" class="logo-image">
    </div>
    <h1 class="main-title">📊 Dashboard Financeiro - Clips Burger</h1>
</div>
""", unsafe_allow_html=True)
# st.title("📊 Dashboard Financeiro - Clips Burger") # Linha original substituída
st.markdown("--- ") # Linha separadora mantida
# --- FIM DA MODIFICAÇÃO DO TÍTULO ---

# --- Abas Principais ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 Dashboard Geral", "📅 Registro de Vendas", "🔍 Análise Detalhada", "⚙️ Configurações & DRE"])

# --- Aba 1: Dashboard Geral ---
with tab1:
    st.header("Visão Geral do Desempenho")

    # Carregar e processar dados
    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    # Filtros de Data (Ano e Mês)
    if not df_processed.empty and 'Ano' in df_processed.columns and not df_processed['Ano'].isnull().all():
        available_years = sorted(df_processed['Ano'].dropna().unique().astype(int), reverse=True)
        # Garante que meses_ordem contenha apenas meses presentes nos dados
        available_months_data = df_processed['MêsNome'].dropna().unique()
        available_months = sorted([m for m in meses_ordem if m in available_months_data], key=lambda m: meses_ordem.index(m))
        
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            # Seleciona o último ano por padrão se houver anos disponíveis
            default_year = [available_years[0]] if available_years else None
            selected_anos = st.multiselect("Selecione o(s) Ano(s)", available_years, default=default_year)
        with col_filter2:
            # Seleciona todos os meses disponíveis por padrão
            selected_meses = st.multiselect("Selecione o(s) Mês(es)", available_months, default=available_months)

        # Aplicar filtros ao DataFrame processado
        df_filtered = df_processed.copy()
        if selected_anos:
            df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos)]
        if selected_meses:
             df_filtered = df_filtered[df_filtered['MêsNome'].isin(selected_meses)]
            
    else:
        st.warning("Não há dados ou colunas de data suficientes para aplicar filtros.")
        df_filtered = df_processed.copy() # Usa dados brutos processados se filtros falharem
        selected_anos = []
        selected_meses = []

    st.markdown("### KPIs Principais (Período Selecionado)")
    # Exibe KPIs mesmo se df_filtered estiver vazio (mostrará N/A ou 0)
    create_premium_kpi_cards(df_filtered)
    # Removido o if/else que mostrava info, a função create_premium_kpi_cards já lida com df vazio.

    st.markdown("--- ")
    st.markdown("### Análises Visuais (Período Selecionado)")

    if not df_filtered.empty:
        # Layout em Grid para os gráficos principais
        st.markdown('<div class="premium-charts-grid">', unsafe_allow_html=True)
        
        # Coluna 1: Gráfico Acumulado e Heatmap
        with st.container():
            # --- MODIFICADO: Chama a função do gráfico acumulado --- 
            cumulative_chart = create_cumulative_area_chart(df_filtered)
            if cumulative_chart:
                st.altair_chart(cumulative_chart, use_container_width=True)
            else:
                st.info("Sem dados suficientes para o gráfico de evolução acumulada.")
            # --- FIM DA MODIFICAÇÃO DA CHAMADA DO GRÁFICO ---
            
            # Heatmap de Atividade (mostra para o último ano selecionado, se houver)
            if selected_anos:
                # Pega dados GERAIS do último ano selecionado para heatmap completo do ano
                last_selected_year_df = df_processed[df_processed['Ano'] == max(selected_anos)].copy()
                # Não filtra por mês aqui para mostrar o ano inteiro no heatmap
                # if selected_meses:
                #      last_selected_year_df = last_selected_year_df[last_selected_year_df['MêsNome'].isin(selected_meses)]
                heatmap = create_activity_heatmap(last_selected_year_df)
                if heatmap:
                    st.altair_chart(heatmap, use_container_width=True)
                # Removido o else para não poluir com 'sem dados suficientes'
            else:
                 st.info("Selecione um ano para ver o heatmap de atividade.")

        # Coluna 2: Gráfico Radial e Análise por Dia da Semana
        with st.container():
            # Gráfico Radial de Pagamentos
            radial_chart = create_radial_plot(df_filtered)
            if radial_chart:
                st.altair_chart(radial_chart, use_container_width=True)
            else:
                st.info("Sem dados suficientes para o gráfico radial de pagamentos.")
            
            # Análise por Dia da Semana (Gráfico)
            weekday_chart, best_sales_day = create_enhanced_weekday_analysis(df_filtered)
            if weekday_chart:
                st.altair_chart(weekday_chart, use_container_width=True)
                if best_sales_day and best_sales_day != "N/A":
                    st.success(f"💡 **Melhor dia em média:** {best_sales_day}")
            else:
                st.info("Sem dados suficientes para a análise por dia da semana.")

        st.markdown('</div>', unsafe_allow_html=True) # Fecha a grid

        # Gráfico de Barras Empilhadas Diário (Largura Completa)
        st.markdown('<div class="premium-chart-full">', unsafe_allow_html=True)
        daily_stacked_bar = create_advanced_daily_sales_chart(df_filtered)
        if daily_stacked_bar:
            st.altair_chart(daily_stacked_bar, use_container_width=True)
        else:
            st.info("Sem dados suficientes para o gráfico de vendas diárias por método.")
        st.markdown('</div>', unsafe_allow_html=True) # Fecha a div full-width

    else:
        st.info("Não há dados para exibir os gráficos no período selecionado.")

# --- Aba 2: Registro de Vendas ---
with tab2:
    st.header("📝 Registrar Nova Venda")
    worksheet = get_worksheet() # Tenta obter a worksheet aqui

    if worksheet:
        with st.form("sales_form", clear_on_submit=True):
            col_form1, col_form2 = st.columns([1, 3]) # Ajusta proporção se necessário
            with col_form1:
                # Define a data de hoje como padrão
                sale_date = st.date_input("Data da Venda", value=datetime.today())
            # col_form2 fica vazia ou pode ter outra informação
            
            col_form3, col_form4, col_form5 = st.columns(3)
            with col_form3:
                cartao_input = st.number_input("Valor Cartão (R$)", min_value=0.0, value=None, format="%.2f", step=10.0, placeholder="Ex: 150.00", help="Valor total recebido via cartão.")
            with col_form4:
                dinheiro_input = st.number_input("Valor Dinheiro (R$)", min_value=0.0, value=None, format="%.2f", step=10.0, placeholder="Ex: 50.50", help="Valor total recebido em dinheiro.")
            with col_form5:
                pix_input = st.number_input("Valor PIX (R$)", min_value=0.0, value=None, format="%.2f", step=10.0, placeholder="Ex: 75.00", help="Valor total recebido via PIX.")

            submitted = st.form_submit_button("💾 Registrar Venda")
            
            if submitted:
                # Verifica se pelo menos um valor foi inserido
                if not cartao_input and not dinheiro_input and not pix_input:
                    st.warning("🚨 Por favor, insira um valor em pelo menos um método de pagamento.")
                else:
                    # Formata a data para dd/mm/yyyy
                    sale_date_str = sale_date.strftime("%d/%m/%Y")
                    # Chama a função para adicionar à planilha
                    success = add_data_to_sheet(sale_date_str, cartao_input, dinheiro_input, pix_input, worksheet)
                    if success:
                        # Limpar cache para forçar releitura dos dados na próxima vez
                        st.cache_data.clear()
                        st.rerun() # Recarrega a página para atualizar os dados exibidos
                    # Mensagens de erro/sucesso já são tratadas dentro de add_data_to_sheet
    else:
        st.error("❌ Conexão com a planilha Google Sheets falhou. Não é possível registrar vendas no momento. Verifique as credenciais em st.secrets e a conexão com a internet.")

    st.markdown("--- ")
    st.header("🗓️ Histórico de Vendas Recentes")
    if not df_processed.empty:
        # Exibe as últimas 15 vendas registradas, ordenadas pela data original
        st.dataframe(df_processed.sort_values(by='Data', ascending=False).head(15)[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']], use_container_width=True)
    else:
        st.info("Nenhum registro de venda encontrado.")

# --- Aba 3: Análise Detalhada ---
with tab3:
    st.header("🔬 Análise Detalhada das Vendas")
    
    # Usa df_filtered da Aba 1
    if not df_filtered.empty:
        st.markdown("### Distribuição dos Valores de Venda (Histograma)")
        sales_hist = create_sales_histogram(df_filtered)
        if sales_hist:
            st.altair_chart(sales_hist, use_container_width=True)
        else:
            st.info("Sem dados suficientes para gerar o histograma de vendas.")
        
        st.markdown("--- ")
        st.markdown("### Comparativo Mensal (Ano Selecionado)")
        # Comparativo mensal apenas se UM ano for selecionado na Aba 1
        if selected_anos and len(selected_anos) == 1:
            # Filtra os dados GERAIS pelo ano selecionado
            df_year_comp = df_processed[df_processed['Ano'] == selected_anos[0]].copy()
            if not df_year_comp.empty:
                # Agrupa por mês e soma o total
                monthly_sales = df_year_comp.groupby('MêsNome', observed=False)['Total'].sum().reset_index()
                # Ordenar pela ordem correta dos meses
                monthly_sales['MêsNome'] = pd.Categorical(monthly_sales['MêsNome'], categories=meses_ordem, ordered=True)
                monthly_sales = monthly_sales.sort_values('MêsNome')

                # Cria o gráfico de linha mensal
                monthly_chart = alt.Chart(monthly_sales).mark_line(point=True, strokeWidth=3).encode(
                    x=alt.X('MêsNome', title='Mês', sort=meses_ordem, axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y('Total', title='Total de Vendas (R$)', axis=alt.Axis(format='~s')), # Formato resumido (k, M)
                    tooltip=[
                        alt.Tooltip('MêsNome', title='Mês'),
                        alt.Tooltip('Total', title='Vendas (R$)', format=',.2f')
                    ],
                    color=alt.value(CORES_MODO_ESCURO[2]) # Cor laranja
                ).properties(
                    title=f"Vendas Mensais - {selected_anos[0]}",
                    width=1000, # Será ajustado pelo container
                    height=400
                ).configure_view(stroke=None).configure(background='transparent')
                st.altair_chart(monthly_chart, use_container_width=True)
            else:
                st.info(f"Sem dados de vendas para o ano {selected_anos[0]} para análise mensal.")
        elif selected_anos and len(selected_anos) > 1:
            st.info("Selecione apenas um ano no filtro da Aba 'Dashboard Geral' para ver o comparativo mensal.")
        else:
             st.info("Selecione um ano no filtro da Aba 'Dashboard Geral' para ver o comparativo mensal.")

    else:
        st.info("Selecione um período com dados na Aba 'Dashboard Geral' para realizar análises detalhadas.")

# --- Aba 4: Configurações & DRE ---
with tab4:
    st.header("⚙️ Configurações de Custos e DRE")

    st.subheader("Definição de Custos Fixos e Variáveis")
    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    with col_cfg1:
        # Usar st.session_state para persistir os valores entre interações
        if 'salario_tab4' not in st.session_state: st.session_state.salario_tab4 = 1550.00
        if 'contadora_tab4' not in st.session_state: st.session_state.contadora_tab4 = 316.00
        if 'fornecedores_tab4' not in st.session_state: st.session_state.fornecedores_tab4 = 30.0
        
        salario = st.number_input(
            "Salário Mínimo Base (R$)", 
            min_value=0.0, 
            value=st.session_state.salario_tab4, 
            format="%.2f", 
            key='salario_tab4_input',
            on_change=lambda: setattr(st.session_state, 'salario_tab4', st.session_state.salario_tab4_input),
            help="Valor base do salário mínimo para cálculo de despesa com pessoal (será multiplicado por 1.55 para encargos)."
        )
    with col_cfg2:
        contadora = st.number_input(
            "Custo Mensal Contadora (R$)", 
            min_value=0.0, 
            value=st.session_state.contadora_tab4, 
            format="%.2f", 
            key='contadora_tab4_input',
            on_change=lambda: setattr(st.session_state, 'contadora_tab4', st.session_state.contadora_tab4_input),
            help="Valor mensal pago pelos serviços contábeis."
        )
    with col_cfg3:
        fornecedores_perc = st.number_input(
            "Custo Fornecedores (% da Receita Bruta)", 
            min_value=0.0, 
            max_value=100.0, 
            value=st.session_state.fornecedores_tab4, 
            format="%.1f", 
            key='fornecedores_tab4_input',
            on_change=lambda: setattr(st.session_state, 'fornecedores_tab4', st.session_state.fornecedores_tab4_input),
            help="Percentual estimado do custo dos produtos vendidos (fornecedores) sobre a receita bruta."
        )

    st.markdown("--- ")
    st.subheader("📊 Demonstração do Resultado do Exercício (DRE) - Anual")

    # Usa df_processed (dados gerais) e selected_anos (da Aba 1) para o DRE
    if not df_processed.empty:
        # Calcula resultados financeiros com base nos dados FILTRADOS (para o gráfico abaixo)
        # Usa os valores das configurações atuais (do st.session_state)
        resultados_filtrados = calculate_financial_results(df_filtered, st.session_state.salario_tab4, st.session_state.contadora_tab4, st.session_state.fornecedores_tab4)
        
        # Gera o DRE textual ANUAL (usa a função que filtra por ano internamente)
        create_dre_textual(resultados_filtrados, df_processed, selected_anos)
        
        st.markdown("--- ")
        st.subheader("Visualização Financeira (Período Filtrado)")
        # Gera o gráfico de barras financeiro com base nos dados FILTRADOS
        financial_chart = create_financial_dashboard_altair(resultados_filtrados)
        if financial_chart:
            st.altair_chart(financial_chart, use_container_width=True)
        # Removido o else para não poluir
            
    else:
        st.info("Não há dados de vendas disponíveis para gerar o DRE e a análise financeira.")


