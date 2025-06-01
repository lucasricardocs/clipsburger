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

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema Financeiro - Clips Burger", layout="wide", page_icon="🍔")

# Configuração de tema para gráficos mais bonitos
alt.data_transformers.enable('json')

# Paleta de cores otimizada para modo escuro
CORES_MODO_ESCURO = ['#4c78a8', '#54a24b', '#f58518', '#e45756', '#72b7b2', '#ff9da6', '#9d755d', '#bab0ac']

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
    
    /* Responsividade para gráficos */
    .stAltairChart {
        width: 100% !important;
    }
    
    .stAltairChart > div {
        width: 100% !important;
    }
    
    /* Media queries para diferentes tamanhos de tela */
    @media (max-width: 768px) {
        .premium-charts-grid {
            grid-template-columns: 1fr;
            gap: 1rem;
        }
        
        .stMetric {
            min-height: 100px;
        }
    }
    
    @media (min-width: 1200px) {
        .premium-charts-grid {
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

inject_css()

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
            
            for col in ['Cartão', 'Dinheiro', 'Pix']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                else:
                    df[col] = 0
            
            if 'Data' not in df.columns:
                df['Data'] = pd.NaT

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
    
    cols_to_ensure_numeric = ['Cartão', 'Dinheiro', 'Pix', 'Total']
    cols_to_ensure_date_derived = ['Ano', 'Mês', 'MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana', 'DiaDoMes']
    
    if df.empty:
        all_expected_cols = ['Data'] + cols_to_ensure_numeric + cols_to_ensure_date_derived
        empty_df = pd.DataFrame(columns=all_expected_cols)
        for col in cols_to_ensure_numeric:
            empty_df[col] = pd.Series(dtype='float')
        for col in cols_to_ensure_date_derived:
            empty_df[col] = pd.Series(dtype='object' if col in ['MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana'] else 'float')
        empty_df['Data'] = pd.Series(dtype='datetime64[ns]')
        return empty_df

    for col in ['Cartão', 'Dinheiro', 'Pix']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0

    df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']

    if 'Data' in df.columns and not df['Data'].isnull().all():
        try:
            if pd.api.types.is_string_dtype(df['Data']):
                df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
                if df['Data'].isnull().all():
                    df['Data'] = pd.to_datetime(df_input['Data'], errors='coerce')
            elif not pd.api.types.is_datetime64_any_dtype(df['Data']):
                df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
            
            df.dropna(subset=['Data'], inplace=True)

            if not df.empty:
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month

                try:
                    df['MêsNome'] = df['Data'].dt.strftime('%B').str.capitalize()
                    if not df['MêsNome'].dtype == 'object' or df['MêsNome'].str.isnumeric().any():
                         df['MêsNome'] = df['Mês'].map(lambda x: meses_ordem[int(x)-1] if pd.notna(x) and 1 <= int(x) <= 12 else "Inválido")
                except Exception:
                    df['MêsNome'] = df['Mês'].map(lambda x: meses_ordem[int(x)-1] if pd.notna(x) and 1 <= int(x) <= 12 else "Inválido")

                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                
                day_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
                df['DiaSemana'] = df['Data'].dt.dayofweek.map(day_map)
                df['DiaDoMes'] = df['Data'].dt.day

                df['DiaSemana'] = pd.Categorical(df['DiaSemana'], categories=[d for d in dias_semana_ordem if d in df['DiaSemana'].unique()], ordered=True)
            else:
                for col in cols_to_ensure_date_derived:
                    df[col] = pd.Series(dtype='object' if col in ['MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana'] else 'float')
        except Exception as e:
            st.error(f"Erro crítico ao processar a coluna 'Data': {e}. Verifique o formato das datas na planilha.")
            for col in cols_to_ensure_date_derived:
                df[col] = pd.Series(dtype='object' if col in ['MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana'] else 'float')
    else:
        if 'Data' not in df.columns:
            st.warning("Coluna 'Data' não encontrada no DataFrame. Algumas análises temporais não estarão disponíveis.")
            df['Data'] = pd.NaT
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
            legend=None
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
        height=500,
        padding={'bottom': 100}
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )

    return radial_plot

def create_cumulative_area_chart(df):
    """Cria gráfico de área ACUMULADO com gradiente.""" # Modificado
    # Validação da entrada: Verifica se o DataFrame está vazio ou se as colunas necessárias estão ausentes
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        st.warning("Dados insuficientes ou colunas 'Data'/'Total' ausentes para gerar o gráfico de evolução acumulada.")
        return None # Retorna None se os dados forem inválidos

    # Garante que a coluna 'Data' esteja no formato datetime
    df_copy = df.copy() # Trabalha em uma cópia para evitar modificar o df original
    try:
        df_copy['Data'] = pd.to_datetime(df_copy['Data'])
    except Exception as e:
        st.error(f"Erro ao converter a coluna 'Data' para datetime: {e}")
        return None

    # Ordena por 'Data' para o cálculo cumulativo correto e renderização do gráfico
    df_sorted = df_copy.sort_values('Data')

    # Esta verificação pode ser redundante se o primeiro df.empty já cobrir, mas é seguro
    if df_sorted.empty:
        st.warning("DataFrame vazio após ordenação para o gráfico de evolução acumulada.")
        return None

    # Calcula o total acumulado
    df_sorted['Total_Acumulado'] = df_sorted['Total'].cumsum()

    # Cria o gráfico Altair
    area_chart = alt.Chart(df_sorted).mark_area(
        interpolate='monotone', # Suaviza a linha da área
        line={'color': CORES_MODO_ESCURO[0], 'strokeWidth': 2}, # Estilo para a linha superior da área
        color=alt.Gradient( # Define o preenchimento em gradiente
            gradient='linear',
            stops=[
                alt.GradientStop(color=CORES_MODO_ESCURO[0], offset=0), # Cor inicial do gradiente
                alt.GradientStop(color=CORES_MODO_ESCURO[4], offset=1)  # Cor final do gradiente
            ],
            x1=1, x2=1, y1=1, y2=0 # Direção do gradiente (vertical de baixo para cima)
        )
    ).encode(
        x=alt.X(
            'Data:T', # 'T' especifica o tipo de dado temporal
            #title='Data',
            axis=alt.Axis(format='%d/%m', labelAngle=-45, labelFontSize=12) # Formata os rótulos do eixo x
        ),
        y=alt.Y(
            'Total_Acumulado:Q', # 'Q' especifica o tipo de dado quantitativo
            #title='Total de Vendas Acumulado (R$)',
            axis=alt.Axis(labelFontSize=12) # Formata os rótulos do eixo y
        ),
        tooltip=[ # Define o que aparece ao passar o mouse
            alt.Tooltip('Data:T', title='Data', format='%d/%m/%Y'), # Formata a data no tooltip
            alt.Tooltip('Total:Q', title='Venda do Dia (R$)', format=',.2f'),
            alt.Tooltip('Total_Acumulado:Q', title='Total Acumulado (R$)', format=',.2f')
        ]
    ).properties(
        title=alt.TitleParams(
            text='Evolução Acumulada das Vendas',
            fontSize=18,
            anchor='start' # Alinha o título ao início (esquerda)
        ),
        height=500
    ).configure_view(
        stroke=None # Remove a borda ao redor da visualização do gráfico
    ).configure(
        background='transparent' # Torna o fundo do gráfico transparente
    )

    return area_chart

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
        size=20,
        stroke='white',     # Cor da borda
        strokeWidth=2     # Espessura da borda
    ).encode(
        x=alt.X(
            'Data:T',
            title='Data',
            axis=alt.Axis(format='%d/%m', labelAngle=-45, labelFontSize=12)
        ),
        y=alt.Y(
            'Valor:Q',
            title='Valor (R$)',
            stack='zero',
            axis=alt.Axis(labelFontSize=12)
        ),
        color=alt.Color(
            'Método:N',
            scale=alt.Scale(range=CORES_MODO_ESCURO[:3]),
            legend=None
        ),
        tooltip=[
            alt.Tooltip('DataFormatada:N', title='Data'),
            alt.Tooltip('Método:N', title='Método'),
            alt.Tooltip('Valor:Q', title='Valor (R$)', format=',.2f')
        ]
    ).properties(
        height=500,
        padding={'bottom': 100}
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
    
    weekday_stats = df_copy.groupby('DiaSemana', observed=True).agg({
        'Total': ['mean', 'sum', 'count']
    }).round(2)
    
    weekday_stats.columns = ['Média', 'Total', 'Dias_Vendas']
    weekday_stats = weekday_stats.reindex([d for d in dias_semana_ordem if d in weekday_stats.index])
    weekday_stats = weekday_stats.reset_index()
    
    total_media_geral = weekday_stats['Média'].sum()
    if total_media_geral > 0:
        weekday_stats['Percentual_Media'] = (weekday_stats['Média'] / total_media_geral * 100).round(1)
    else:
        weekday_stats['Percentual_Media'] = 0
    
    chart = alt.Chart(weekday_stats).mark_bar(
        color=CORES_MODO_ESCURO[0],
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5
    ).encode(
        x=alt.X(
            'DiaSemana:O',
            title='Dia da Semana',
            sort=dias_semana_ordem,
            axis=alt.Axis(labelAngle=-45, labelFontSize=12)
        ),
        y=alt.Y(
            'Média:Q',
            title='Média de Vendas (R$)',
            axis=alt.Axis(labelFontSize=12)
        ),
        tooltip=[
            alt.Tooltip('DiaSemana:N', title='Dia'),
            alt.Tooltip('Média:Q', title='Média (R$)', format=',.2f'),
            alt.Tooltip('Percentual_Media:Q', title='% da Média Total', format='.1f'),
            alt.Tooltip('Dias_Vendas:Q', title='Dias com Vendas')
        ]
    ).properties(
        title=alt.TitleParams(
            text="Média de Vendas por Dia da Semana",
            fontSize=18,
            anchor='start'
        ),
        height=500,
        padding={'bottom': 100}
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    best_day = weekday_stats.loc[weekday_stats['Média'].idxmax(), 'DiaSemana'] if not weekday_stats.empty else "N/A"
    
    return chart, best_day

def create_sales_histogram(df, title="Distribuição dos Valores de Venda Diários"):
    """Histograma sem animação."""
    if df.empty or 'Total' not in df.columns or df['Total'].isnull().all():
        return None
    
    df_filtered_hist = df[df['Total'] > 0].copy()
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
        padding={'bottom': 100}
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    return histogram

def analyze_sales_by_weekday(df):
    """Analisa vendas por dia da semana."""
    if df.empty or 'DiaSemana' not in df.columns or 'Total' not in df.columns or df['DiaSemana'].isnull().all() or df['Total'].isnull().all():
        return None, None
    
    try:
        df_copy = df.copy()
        df_copy['Total'] = pd.to_numeric(df_copy['Total'], errors='coerce')
        df_copy.dropna(subset=['Total', 'DiaSemana'], inplace=True)
        
        if df_copy.empty:
            return None, None
        
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
        'despesas_com_pessoal': 0, 'despesas_contabeis': custo_contadora,
        'total_despesas_operacionais': 0, 'lucro_operacional': 0, 'margem_operacional': 0,
        'lucro_antes_ir': 0, 'lucro_liquido': 0, 'margem_liquida': 0,
        'diferenca_tributavel_nao_tributavel': 0
    }
    
    if df.empty: 
        return results
    
    results['receita_bruta'] = df['Total'].sum()
    results['receita_tributavel'] = df['Cartão'].sum() + df['Pix'].sum()
    results['receita_nao_tributavel'] = df['Dinheiro'].sum()
    results['impostos_sobre_vendas'] = results['receita_tributavel'] * 0.06
    results['receita_liquida'] = results['receita_bruta'] - results['impostos_sobre_vendas']
    results['custo_produtos_vendidos'] = results['receita_bruta'] * (custo_fornecedores_percentual / 100)
    results['lucro_bruto'] = results['receita_liquida'] - results['custo_produtos_vendidos']
    
    if results['receita_liquida'] > 0:
        results['margem_bruta'] = (results['lucro_bruto'] / results['receita_liquida']) * 100
    
    results['despesas_com_pessoal'] = salario_minimo * 1.55
    results['despesas_contabeis'] = custo_contadora
    results['despesas_administrativas'] = 0
    results['total_despesas_operacionais'] = (
        results['despesas_com_pessoal'] + 
        results['despesas_contabeis'] + 
        results['despesas_administrativas']
    )
    
    results['lucro_operacional'] = results['lucro_bruto'] - results['total_despesas_operacionais']
    if results['receita_liquida'] > 0:
        results['margem_operacional'] = (results['lucro_operacional'] / results['receita_liquida']) * 100
    
    results['lucro_antes_ir'] = results['lucro_operacional']
    results['lucro_liquido'] = results['lucro_antes_ir']
    if results['receita_liquida'] > 0:
        results['margem_liquida'] = (results['lucro_liquido'] / results['receita_liquida']) * 100
    
    results['diferenca_tributavel_nao_tributavel'] = results['receita_nao_tributavel']
    
    return results

def create_dre_textual(resultados, df_processed, selected_anos_filter):
    """Cria uma apresentação textual do DRE no estilo tradicional contábil usando dados anuais."""
    def format_val(value):
        return f"{value:,.0f}".replace(",", ".")

    def calc_percent(value, base):
        if base == 0:
            return 0
        return (value / base) * 100

    # Determinar o ano para o DRE
    if selected_anos_filter and len(selected_anos_filter) == 1:
        ano_dre = selected_anos_filter[0]
    else:
        ano_dre = datetime.now().year

    # Filtrar dados APENAS por ano (ignorar filtro de mês)
    if not df_processed.empty and 'Ano' in df_processed.columns:
        df_ano = df_processed[df_processed['Ano'] == ano_dre].copy()
        
        # Recalcular resultados com dados do ano completo
        if not df_ano.empty:
            resultados_ano = calculate_financial_results(
                df_ano, 
                st.session_state.get('salario_tab4', 1550.0), 
                st.session_state.get('contadora_tab4', 316.0) * 12, # Custo anual
                st.session_state.get('fornecedores_tab4', 30.0)
            )
        else:
            # Se não houver dados para o ano, usar os resultados filtrados (pode ser de outro período)
            # Ou zerar? Melhor usar os filtrados para não mostrar tudo zero.
            resultados_ano = resultados # Mantém os resultados do filtro atual se não houver dados do ano
            st.warning(f"⚠️ Não há dados de vendas registrados para o ano {ano_dre}. O DRE abaixo pode refletir um período diferente.")
    else:
        resultados_ano = resultados # Usa resultados filtrados se df_processed estiver vazio

    # Cabeçalho centralizado
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 30px;">
        <h3 style="margin: 0; font-weight: normal;">DEMONSTRAÇÃO DO RESULTADO DO EXERCÍCIO</h3>
        <p style="margin: 5px 0; font-style: italic;">Clips Burger - Exercício {ano_dre}</p>
    """, unsafe_allow_html=True)

    # Criar 2 colunas - descrição e valor
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("")
    with col2:
        st.markdown("**Em R$**")
    
    # RECEITA BRUTA
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("**RECEITA BRUTA**")
    with col2:
        st.markdown(f"**{format_val(resultados_ano['receita_bruta'])}**")
    
    # DEDUÇÕES
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("**(-) DEDUÇÕES**")
    with col2:
        st.markdown("")
    
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Simples Nacional")
    with col2:
        st.markdown(f"({format_val(resultados_ano['impostos_sobre_vendas'])})")
    
    # RECEITA LÍQUIDA
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("**RECEITA LÍQUIDA**")
    with col2:
        st.markdown(f"**{format_val(resultados_ano['receita_liquida'])}**")
    
    # CUSTO DOS PRODUTOS VENDIDOS
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("**(-) CUSTO DOS PRODUTOS VENDIDOS**")
    with col2:
        st.markdown(f"**({format_val(resultados_ano['custo_produtos_vendidos'])})**")
    
    # LUCRO BRUTO
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("**LUCRO BRUTO**")
    with col2:
        st.markdown(f"**{format_val(resultados_ano['lucro_bruto'])}**")
    
    # DESPESAS OPERACIONAIS
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("**(-) DESPESAS OPERACIONAIS**")
    with col2:
        st.markdown("")
    
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Despesas com Pessoal")
    with col2:
        # Ajuste para mostrar despesa anual
        st.markdown(f"({format_val(resultados_ano['despesas_com_pessoal'])})") 
    
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Serviços Contábeis")
    with col2:
         # Ajuste para mostrar despesa anual
        st.markdown(f"({format_val(resultados_ano['despesas_contabeis'])})")
    
    # LUCRO OPERACIONAL
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("**LUCRO OPERACIONAL**")
    with col2:
        st.markdown(f"**{format_val(resultados_ano['lucro_operacional'])}**")
    
    # RESULTADO ANTES DO IMPOSTO DE RENDA
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("**LUCRO ANTES DO IMPOSTO DE RENDA**")
    with col2:
        st.markdown(f"**{format_val(resultados_ano['lucro_antes_ir'])}**")
    
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("**(-) Provisão para Imposto de Renda**")
    with col2:
        st.markdown("**-**")
    
    # Linha de separação
    #st.markdown("---")
    
    # RESULTADO LÍQUIDO - destacado
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("## **RESULTADO LÍQUIDO DO EXERCÍCIO**")
    with col2:
        st.markdown(f"## **{format_val(resultados_ano['lucro_liquido'])}**")
    
    # Nota explicativa
    st.info(f"📅 **Nota:** Este DRE apresenta os resultados consolidados do exercício {ano_dre}, independente do filtro de mês aplicado nas outras análises.")

def create_financial_dashboard_altair(resultados):
    """Dashboard financeiro com legenda corrigida."""
    financial_data = pd.DataFrame({
        'Categoria': [
            'Receita Bruta',
            'Impostos s/ Vendas',
            'Custo Produtos',
            'Despesas Pessoal',
            'Serviços Contábeis',
            'Lucro Líquido'
        ],
        'Valor': [
            resultados['receita_bruta'],
            -resultados['impostos_sobre_vendas'],
            -resultados['custo_produtos_vendidos'],
            -resultados['despesas_com_pessoal'],
            -resultados['despesas_contabeis'],
            resultados['lucro_liquido']
        ],
        'Tipo': [
            'Receita',
            'Dedução',
            'CPV',
            'Despesa',
            'Despesa',
            'Resultado'
        ]
    })
    
    chart = alt.Chart(financial_data).mark_bar(
        cornerRadiusTopRight=8,
        cornerRadiusBottomRight=8
    ).encode(
        x=alt.X(
            'Valor:Q',
            title='Valor (R$)',
            axis=alt.Axis(format=',.0f', labelFontSize=12)
        ),
        y=alt.Y(
            'Categoria:O',
            title=None,
            sort=financial_data['Categoria'].tolist(),
            axis=alt.Axis(labelFontSize=12)
        ),
        color=alt.Color(
            'Tipo:N',
            scale=alt.Scale(
                domain=['Receita', 'Dedução', 'CPV', 'Despesa', 'Resultado'],
                range=[CORES_MODO_ESCURO[1], CORES_MODO_ESCURO[3], CORES_MODO_ESCURO[2], CORES_MODO_ESCURO[4], CORES_MODO_ESCURO[0]]
            ),
            legend=None
        ),
        tooltip=[
            alt.Tooltip('Categoria:N', title='Categoria'),
            alt.Tooltip('Valor:Q', title='Valor (R$)', format=',.2f'),
            alt.Tooltip('Tipo:N', title='Tipo')
        ]
    ).properties(
        title=alt.TitleParams(
            text="Composição do Resultado Financeiro",
            fontSize=20,
            anchor='start'
        ),
        height=500,
        padding={'bottom': 100}
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    return chart

# --- Dashboard Premium Functions ---
def create_premium_kpi_cards(df):
    """Cria cards KPI premium com emoticons DENTRO dos boxes."""
    if df.empty:
        return
    
    total_vendas = df['Total'].sum()
    media_diaria = df['Total'].mean()
    melhor_dia = df.loc[df['Total'].idxmax(), 'DataFormatada'] if not df.empty and 'DataFormatada' in df.columns else "N/A"
    crescimento = ((df['Total'].tail(7).mean() - df['Total'].head(7).mean()) / df['Total'].head(7).mean() * 100) if len(df) >= 14 and df['Total'].head(7).mean() != 0 else 0.0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with st.container():
            st.metric(
                label="💰 Faturamento Total",
                value=format_brl(total_vendas),
                delta=f"{crescimento:+.1f}% vs período anterior" if crescimento != 0 else None
            )
    
    with col2:
        with st.container():
            st.metric(
                label="📊 Média Diária",
                value=format_brl(media_diaria),
                # delta="+8.2% vs período anterior" # Placeholder delta
            )
    
    with col3:
        with st.container():
            st.metric(
                label="🏆 Melhor Dia",
                value=melhor_dia,
                delta="Maior faturamento" if melhor_dia != "N/A" else None
            )
    
    with col4:
        with st.container():
            st.metric(
                label="📈 Tendência (Últimas 2 Semanas)",
                value=f"{crescimento:+.1f}%",
                delta="Crescimento" if crescimento > 0 else "Estável/Declínio" if crescimento == 0 else "Declínio"
            )

# --- NOVA FUNÇÃO: Gráfico Heatmap de Atividade ---
def create_activity_heatmap(df_input):
    """Cria um gráfico de heatmap estilo GitHub para a atividade de vendas - IGNORA FILTRO DE MÊS."""
    if df_input.empty or 'Data' not in df_input.columns or 'Total' not in df_input.columns:
        st.info("Dados insuficientes para gerar o heatmap de atividade.")
        return None

    # MODIFICAÇÃO: Recarregar dados completos ignorando filtros
    df_completo = read_sales_data()  # Busca dados completos da planilha
    if df_completo.empty:
        st.info("Sem dados disponíveis para o heatmap.")
        return None
    
    # Processar os dados completos
    df_completo = process_data(df_completo)
    
    df = df_completo.copy()
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    df.dropna(subset=['Data'], inplace=True)
    
    if df.empty:
        st.info("Dados insuficientes após processamento para gerar o heatmap de atividade.")
        return None

    # Determinar o ano atual ou mais recente dos dados
    current_year = df['Data'].dt.year.max()
    df = df[df['Data'].dt.year == current_year]

    if df.empty:
        st.info(f"Sem dados para o ano {current_year} para gerar o heatmap.")
        return None

    # Criar todas as datas do ano selecionado
    start_date = datetime(current_year, 1, 1)
    end_date = datetime(current_year, 12, 31)
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')

    # DataFrame com todas as datas
    full_df = pd.DataFrame({'Data': all_dates})
    # Certificar que as colunas existem antes de mergear
    cols_to_merge = ['Data', 'Total', 'Cartão', 'Dinheiro', 'Pix']
    cols_present = [col for col in cols_to_merge if col in df.columns]
    full_df = full_df.merge(df[cols_present], on='Data', how='left')
    
    # Preencher NaNs e garantir colunas
    for col in ['Total', 'Cartão', 'Dinheiro', 'Pix']:
        if col not in full_df.columns:
            full_df[col] = 0
        else:
            full_df[col] = full_df[col].fillna(0)

    # Ajuste para o estilo GitHub
    full_df['day_of_week'] = full_df['Data'].dt.dayofweek # Seg=0, Dom=6
    full_df['day_name'] = full_df['Data'].dt.strftime('%a') # Abreviação do dia
    # Mapear para ordem correta no gráfico (Dom=0)
    day_order_map = {'Mon': 1, 'Tue': 2, 'Wed': 3, 'Thu': 4, 'Fri': 5, 'Sat': 6, 'Sun': 0}
    full_df['day_sort_order'] = full_df['Data'].dt.weekday.map(lambda x: (x + 1) % 7) # Dom=0, Seg=1...
    day_name_map = {0: 'Dom', 1: 'Seg', 2: 'Ter', 3: 'Qua', 4: 'Qui', 5: 'Sex', 6: 'Sáb'}
    full_df['day_display_name'] = full_df['day_sort_order'].map(day_name_map)
    
    full_df['week'] = full_df['Data'].dt.isocalendar().week
    full_df['month'] = full_df['Data'].dt.month
    full_df['month_name'] = full_df['Data'].dt.strftime('%b')

    # Corrigir semanas de dezembro que aparecem como 1 no isocalendar
    full_df.loc[(full_df['Data'].dt.month == 12) & (full_df['week'] <= 4), 'week'] = full_df['week'].max() + 1
    # Corrigir semanas de janeiro que aparecem como 52/53
    full_df.loc[(full_df['Data'].dt.month == 1) & (full_df['week'] >= 52), 'week'] = 0
    
    # Recalcular week para garantir ordem correta após ajustes
    first_day_of_year = pd.Timestamp(f'{current_year}-01-01')
    full_df['week_corrected'] = ((full_df['Data'] - first_day_of_year).dt.days // 7)
    
    # Encontrar a primeira semana (corrigida) de cada mês para os rótulos
    month_labels = full_df.groupby('month').agg(
        week_corrected=('week_corrected', 'min'),
        month_name=('month_name', 'first')
    ).reset_index()

    # Labels dos meses
    months_chart = alt.Chart(month_labels).mark_text(
        align='center', # Centralizado acima da semana
        baseline='bottom',
        fontSize=12,
        dy=-1,
        dx=-30, # Espaço acima do heatmap
        color='#A9A9A9' # Cor cinza claro para meses
    ).encode(
        x=alt.X('week_corrected:O', axis=None), # Usar semana corrigida
        text='month_name:N'
    )

    # Gráfico principal (heatmap)
    heatmap = alt.Chart(full_df).mark_rect(
        stroke='#ffffff', # Borda branca fina
        strokeWidth=2,
        cornerRadius=0.5 # Leve arredondamento
    ).encode(
        x=alt.X('week_corrected:O', # Usar semana corrigida
                title=None, 
                axis=None),
        y=alt.Y('day_display_name:N', 
                sort=['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'],
                title=None,
                axis=alt.Axis(labelAngle=0, labelFontSize=12, ticks=False, domain=False, grid=False, labelColor='#A9A9A9')),
        color=alt.Color('Total:Q',
            scale=alt.Scale(
                # Usar cores do tema escuro, adaptadas para heatmap
                range=['#f0f0f0', '#9be9a8', '#40c463', '#30a14e', '#216e39'], # Cinza escuro -> Verdes
                # range=['#f0f0f0', '#9be9a8', '#40c463', '#30a14e', '#216e39'], # Esquema original GitHub claro
                type='threshold',
                domain=[0.01, 1500, 2500, 3500] # Ajustar domínios conforme necessidade
            ),
            legend=None), # Legenda pode ser adicionada separadamente se desejado
        tooltip=[
            alt.Tooltip('Data:T', title='Data', format='%d/%m/%Y'),
            alt.Tooltip('day_display_name:N', title='Dia'),
            alt.Tooltip('Total:Q', title='Total Vendas (R$)', format=',.2f'),
            alt.Tooltip('Cartão:Q', title='Cartão (R$)', format=',.2f'),
            alt.Tooltip('Dinheiro:Q', title='Dinheiro (R$)', format=',.2f'),
            alt.Tooltip('Pix:Q', title='Pix (R$)', format=',.2f')
        ]
    ).properties(
        height=250  # Ajustar altura
    )

    # Combinar gráfico final
    final_chart = alt.vconcat(
        months_chart,
        heatmap,
        spacing=1 # Pequeno espaço entre meses e heatmap
    ).configure_view(
        strokeWidth=0 # Sem borda ao redor do gráfico combinado
    ).configure_concat(
        spacing=5
    ).properties(
        title=alt.TitleParams(
            text=f'Atividade de Vendas - {current_year}',
            fontSize=18,
            anchor='start',
            color='white', # Cor do título para tema escuro
            dy=-10 # Ajustar posição vertical do título
        )
    ).configure(
        background='transparent' # Fundo transparente para integrar ao app
    )

    return final_chart

# Função para formatar valores em moeda brasileira
def format_brl(value):
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

# --- Interface Principal da Aplicação ---
def main():
    # --- MODIFICAÇÃO DO LOGO E TÍTULO ---
    st.markdown("""
    <style>
    .logo-container {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .logo-wrapper {
        position: relative;
        margin-right: 20px;
        width: 240px;
        height: 240px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .logo-background {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 175px;
        height: 175px;
        background-image: url('https://raw.githubusercontent.com/lucasricardocs/clipsburger/refs/heads/main/logo.png');
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        filter: blur(20px) brightness(1.8) saturate(2.5);
        z-index: 1;
        animation: celestialPulse 12s ease-in-out infinite alternate;
    }
    
    .logo-image {
        position: relative;
        width: 200px;
        height: auto;
        z-index: 2;
    }
    
    @keyframes celestialPulse {
        0% { opacity: 0.3; transform: translate(-50%, -50%) scale(0.95); }
        50% { opacity: 0.6; transform: translate(-50%, -50%) scale(1.05); }
        100% { opacity: 0.4; transform: translate(-50%, -50%) scale(1.0); }
    }
    </style>
    
    <div class="logo-container">
        <div class="logo-wrapper">
            <div class="logo-background"></div>
            <img class="logo-image" src="https://raw.githubusercontent.com/lucasricardocs/clipsburger/refs/heads/main/logo.png" alt="Clips Burger Logo">
        </div>
        <div>
            <h1 style="margin: 0; color: #4c78a8; font-size: 3rem;">Sistema Financeiro</h1>
            <h2 style="margin: 0; color: #54a24b; font-size: 2rem;">Clips Burger</h2>
            <p style="margin: 0; color: #888; font-style: italic;">Dashboard Inteligente de Vendas</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Carregar dados
    df = read_sales_data()
    df_processed = process_data(df)

    # Criar abas
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "📈 Análises", "💰 Financeiro", "⚙️ Configurações", "📋 Dados"])

    with tab1:
        st.header("📊 Dashboard Premium")
        
        if not df_processed.empty:
            # KPI Cards
            create_premium_kpi_cards(df_processed)
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                anos_disponiveis = sorted(df_processed['Ano'].dropna().unique()) if 'Ano' in df_processed.columns else []
                selected_anos = st.multiselect("📅 Filtrar por Ano:", anos_disponiveis, default=anos_disponiveis)
            
            with col2:
                meses_disponiveis = sorted(df_processed['Mês'].dropna().unique()) if 'Mês' in df_processed.columns else []
                selected_meses = st.multiselect("📅 Filtrar por Mês:", meses_disponiveis, default=meses_disponiveis)
            
            # Aplicar filtros
            df_filtered = df_processed.copy()
            if selected_anos and 'Ano' in df_filtered.columns:
                df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos)]
            if selected_meses and 'Mês' in df_filtered.columns:
                df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)]
            
            # Gráficos principais
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Gráfico de evolução acumulada
                area_chart = create_cumulative_area_chart(df_filtered)
                if area_chart:
                    st.altair_chart(area_chart, use_container_width=True)
            
            with col2:
                # Gráfico radial de métodos de pagamento
                radial_chart = create_radial_plot(df_filtered)
                if radial_chart:
                    st.altair_chart(radial_chart, use_container_width=True)
            
            # Gráfico de vendas diárias
            daily_chart = create_advanced_daily_sales_chart(df_filtered)
            if daily_chart:
                st.altair_chart(daily_chart, use_container_width=True)
            
            # Heatmap de atividade
            heatmap_chart = create_activity_heatmap(df_filtered)
            if heatmap_chart:
                st.altair_chart(heatmap_chart, use_container_width=True)
        else:
            st.info("📊 Nenhum dado disponível para exibir no dashboard.")

    with tab2:
        st.header("📈 Análises Avançadas")
        
        if not df_processed.empty:
            # Análise por dia da semana
            weekday_chart, best_day = create_enhanced_weekday_analysis(df_processed)
            if weekday_chart:
                st.altair_chart(weekday_chart, use_container_width=True)
                if best_day != "N/A":
                    st.success(f"🏆 **Melhor dia da semana:** {best_day}")
            
            # Histograma de distribuição
            histogram = create_sales_histogram(df_processed)
            if histogram:
                st.altair_chart(histogram, use_container_width=True)
        else:
            st.info("📈 Nenhum dado disponível para análises.")

    with tab3:
        st.header("💰 Análise Financeira")
        
        # Configurações financeiras
        col1, col2, col3 = st.columns(3)
        
        with col1:
            salario_minimo = st.number_input("💼 Salário Mínimo (R$):", value=1550.0, min_value=0.0, key="salario_tab4")
        
        with col2:
            custo_contadora = st.number_input("📊 Custo Contadora Mensal (R$):", value=316.0, min_value=0.0, key="contadora_tab4")
        
        with col3:
            custo_fornecedores = st.number_input("🏪 Custo Fornecedores (%):", value=30.0, min_value=0.0, max_value=100.0, key="fornecedores_tab4")
        
        if not df_processed.empty:
            # Calcular resultados financeiros
            resultados = calculate_financial_results(df_processed, salario_minimo, custo_contadora * 12, custo_fornecedores)
            
            # Dashboard financeiro
            financial_chart = create_financial_dashboard_altair(resultados)
            if financial_chart:
                st.altair_chart(financial_chart, use_container_width=True)
            
            # DRE
            st.subheader("📋 Demonstração do Resultado do Exercício")
            create_dre_textual(resultados, df_processed, [datetime.now().year])
        else:
            st.info("💰 Nenhum dado disponível para análise financeira.")

    with tab4:
        st.header("⚙️ Configurações")
        st.info("🔧 Seção de configurações em desenvolvimento.")

    with tab5:
        st.header("📋 Gestão de Dados")
        
        # Formulário para adicionar dados
        st.subheader("➕ Adicionar Nova Venda")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            data_venda = st.date_input("📅 Data da Venda:", value=datetime.now().date())
        
        with col2:
            valor_cartao = st.number_input("💳 Cartão (R$):", min_value=0.0, value=0.0, step=0.01)
        
        with col3:
            valor_dinheiro = st.number_input("💵 Dinheiro (R$):", min_value=0.0, value=0.0, step=0.01)
        
        with col4:
            valor_pix = st.number_input("📱 PIX (R$):", min_value=0.0, value=0.0, step=0.01)
        
        if st.button("💾 Registrar Venda", type="primary"):
            worksheet = get_worksheet()
            if worksheet:
                data_formatada = data_venda.strftime('%d/%m/%Y')
                sucesso = add_data_to_sheet(data_formatada, valor_cartao, valor_dinheiro, valor_pix, worksheet)
                if sucesso:
                    st.cache_data.clear()
                    st.rerun()
        
        # Exibir dados existentes
        # Exibir dados existentes
        st.subheader("📊 Dados de Vendas Registrados")
        
        if not df_processed.empty:
            # Filtros para visualização dos dados
            col1, col2 = st.columns(2)
            
            with col1:
                if 'Ano' in df_processed.columns:
                    anos_dados = sorted(df_processed['Ano'].dropna().unique())
                    ano_filtro = st.selectbox("📅 Filtrar por Ano:", ["Todos"] + list(anos_dados), key="ano_dados")
                else:
                    ano_filtro = "Todos"
            
            with col2:
                if 'Mês' in df_processed.columns:
                    meses_dados = sorted(df_processed['Mês'].dropna().unique())
                    meses_nomes = [meses_ordem[int(m)-1] for m in meses_dados if 1 <= int(m) <= 12]
                    mes_filtro = st.selectbox("📅 Filtrar por Mês:", ["Todos"] + meses_nomes, key="mes_dados")
                else:
                    mes_filtro = "Todos"
            
            # Aplicar filtros aos dados
            df_exibicao = df_processed.copy()
            
            if ano_filtro != "Todos" and 'Ano' in df_exibicao.columns:
                df_exibicao = df_exibicao[df_exibicao['Ano'] == ano_filtro]
            
            if mes_filtro != "Todos" and 'Mês' in df_exibicao.columns:
                mes_num = meses_ordem.index(mes_filtro) + 1
                df_exibicao = df_exibicao[df_exibicao['Mês'] == mes_num]
            
            # Preparar dados para exibição
            if not df_exibicao.empty:
                # Selecionar colunas relevantes para exibição
                colunas_exibir = ['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']
                colunas_disponiveis = [col for col in colunas_exibir if col in df_exibicao.columns]
                
                if colunas_disponiveis:
                    df_display = df_exibicao[colunas_disponiveis].copy()
                    
                    # Renomear colunas para melhor apresentação
                    rename_dict = {
                        'DataFormatada': 'Data',
                        'Cartão': 'Cartão (R$)',
                        'Dinheiro': 'Dinheiro (R$)',
                        'Pix': 'PIX (R$)',
                        'Total': 'Total (R$)'
                    }
                    
                    df_display = df_display.rename(columns=rename_dict)
                    
                    # Formatar valores monetários
                    for col in df_display.columns:
                        if '(R$)' in col:
                            df_display[col] = df_display[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "_").replace(".", ",").replace("_", "."))
                    
                    # Ordenar por data (mais recente primeiro)
                    if 'Data' in df_display.columns:
                        df_display = df_display.sort_values('Data', ascending=False)
                    
                    # Exibir tabela
                    st.dataframe(
                        df_display,
                        use_container_width=True,
                        hide_index=True,
                        height=400
                    )
                    
                    # Estatísticas resumidas
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        total_vendas = df_exibicao['Total'].sum()
                        st.metric("💰 Total de Vendas", format_brl(total_vendas))
                    
                    with col2:
                        media_vendas = df_exibicao['Total'].mean()
                        st.metric("📊 Média por Dia", format_brl(media_vendas))
                    
                    with col3:
                        num_vendas = len(df_exibicao)
                        st.metric("📅 Dias com Vendas", f"{num_vendas}")
                    
                    with col4:
                        if not df_exibicao.empty:
                            maior_venda = df_exibicao['Total'].max()
                            st.metric("🏆 Maior Venda", format_brl(maior_venda))
                    
                    # Opção para download dos dados
                    st.subheader("📥 Download dos Dados")
                    
                    # Converter para CSV
                    csv_data = df_display.to_csv(index=False, encoding='utf-8-sig')
                    
                    st.download_button(
                        label="📄 Baixar dados em CSV",
                        data=csv_data,
                        file_name=f"vendas_clips_burger_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        help="Baixar os dados filtrados em formato CSV"
                    )
                    
                else:
                    st.warning("⚠️ Colunas necessárias não encontradas nos dados.")
            else:
                st.info("📊 Nenhum dado encontrado para os filtros selecionados.")
        else:
            st.info("📊 Nenhum dado de vendas registrado ainda.")
            st.markdown("""
            ### 🚀 Como começar:
            1. **Registre sua primeira venda** usando o formulário acima
            2. **Preencha os valores** de cartão, dinheiro e/ou PIX
            3. **Clique em 'Registrar Venda'** para salvar
            4. **Visualize os dados** nas abas Dashboard e Análises
            """)

if __name__ == "__main__":
    main()

