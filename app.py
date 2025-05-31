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

# CSS para melhorar a aparência e adicionar animação da aura
def inject_css():
    st.markdown(f"""
    <style>
    /* Estilos Gerais */
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
    
    /* Dashboard Premium Styles */
    .stApp {{
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
    }}
    
    /* Grid para gráficos do dashboard premium */
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

    /* Estilos para Logo e Aura */
    .logo-container {{
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 2rem; /* Espaço abaixo da logo */
        position: relative; /* Necessário para o posicionamento da aura */
    }}

    .logo-image {{
        max-width: 300px; /* Ajuste o tamanho máximo conforme necessário */
        height: auto;
        position: relative; /* Para garantir que a imagem fique sobre a aura */
        z-index: 1;
    }}

    .logo-aura {{
        position: absolute;
        width: 100%; /* Ajuste para cobrir a área da logo */
        height: 100%;
        max-width: 320px; /* Um pouco maior que a logo */
        max-height: 220px; /* Ajuste conforme a proporção da sua logo */
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        border-radius: 50%; /* Para uma aura mais circular, ajuste se necessário */
        z-index: 0; /* Atrás da logo */
        animation: pulse-aura 2.5s infinite ease-in-out;
    }}

    @keyframes pulse-aura {{
        0% {{
            box-shadow: 0 0 15px 5px rgba(255, 255, 255, 0.3), 
                        0 0 30px 15px rgba(255, 255, 255, 0.2), 
                        0 0 50px 25px rgba(255, 255, 255, 0.1);
            opacity: 0.7;
        }}
        50% {{
            box-shadow: 0 0 25px 10px rgba(255, 255, 255, 0.5), 
                        0 0 50px 25px rgba(255, 255, 255, 0.3), 
                        0 0 80px 40px rgba(255, 255, 255, 0.15);
            opacity: 1;
        }}
        100% {{
            box-shadow: 0 0 15px 5px rgba(255, 255, 255, 0.3), 
                        0 0 30px 15px rgba(255, 255, 255, 0.2), 
                        0 0 50px 25px rgba(255, 255, 255, 0.1);
            opacity: 0.7;
        }}
    }}

    </style>
    """, unsafe_allow_html=True)

# --- Função para exibir a Logo com Aura ---
def display_logo_with_aura():
    st.markdown(f"""
    <div class="logo-container">
        <div class="logo-aura"></div>
        <img src="{LOGO_URL}" alt="Clips Burger Logo" class="logo-image">
    </div>
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
            # Tenta converter string para datetime (prioriza dia primeiro)
            if pd.api.types.is_string_dtype(df['Data']):
                df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
                # Se falhar, tenta formato padrão
                if df['Data'].isnull().all():
                    df['Data'] = pd.to_datetime(df_input['Data'], errors='coerce')
            elif not pd.api.types.is_datetime64_any_dtype(df['Data']):
                 df['Data'] = pd.to_datetime(df['Data'], errors='coerce') # Converte outros tipos se não for datetime
            
            df.dropna(subset=['Data'], inplace=True) # Remove linhas onde a data não pôde ser convertida

            if not df.empty:
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month

                # Mapeamento seguro para nomes de meses
                try:
                    df['MêsNome'] = df['Data'].dt.strftime('%B').str.capitalize()
                    # Verificação adicional se strftime falhar ou retornar números
                    if not df['MêsNome'].dtype == 'object' or df['MêsNome'].str.isnumeric().any():
                         df['MêsNome'] = df['Mês'].map(lambda x: meses_ordem[int(x)-1] if pd.notna(x) and 1 <= int(x) <= 12 else "Inválido")
                except Exception:
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
        if 'Data' not in df.columns:
            st.warning("Coluna 'Data' não encontrada no DataFrame. Algumas análises temporais não estarão disponíveis.")
            df['Data'] = pd.NaT # Adiciona coluna Data vazia se não existir
        # Cria colunas derivadas vazias se a coluna Data estiver ausente ou toda nula
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

def create_cumulative_area_chart(df):
    """Cria gráfico de área ACUMULADO com gradiente.""" # Modificado
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
        width=1000
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
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
        size=20
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
        width=1000,
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
    weekday_stats = weekday_stats.reindex([d for d in dias_semana_ordem if d in weekday_stats.index]) # Reordena e mantém apenas dias presentes
    weekday_stats.reset_index(inplace=True)
    
    if weekday_stats.empty:
        return None, None

    chart = alt.Chart(weekday_stats).mark_bar(
        color=CORES_MODO_ESCURO[1],
        opacity=0.9,
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
        width=1000,
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
        width=1000,
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
    results['impostos_sobre_vendas'] = results['receita_tributavel'] * 0.06 # Simples Nacional (exemplo)
    results['receita_liquida'] = results['receita_bruta'] - results['impostos_sobre_vendas']
    results['custo_produtos_vendidos'] = results['receita_bruta'] * (custo_fornecedores_percentual / 100)
    results['lucro_bruto'] = results['receita_liquida'] - results['custo_produtos_vendidos']
    
    if results['receita_liquida'] > 0:
        results['margem_bruta'] = (results['lucro_bruto'] / results['receita_liquida']) * 100
    
    # Despesas Mensais - Ajustar se o período filtrado for diferente de 1 mês
    num_months = 1 # Default para cálculo mensal, ajustar se necessário
    if not df.empty and 'AnoMês' in df.columns:
        num_months = df['AnoMês'].nunique()
        if num_months == 0: num_months = 1 # Evitar divisão por zero
        
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
    
    results['diferenca_tributavel_nao_tributavel'] = results['receita_nao_tributavel']
    
    return results

def create_dre_textual(resultados, df_processed, selected_anos_filter):
    """Cria uma apresentação textual do DRE no estilo tradicional contábil usando dados anuais."""
    def format_val(value):
        return f"{value:,.0f}".replace(",", ".")

    # Determinar o ano para o DRE
    if selected_anos_filter and len(selected_anos_filter) == 1:
        ano_dre = selected_anos_filter[0]
    elif not df_processed.empty and 'Ano' in df_processed.columns and not df_processed['Ano'].isnull().all():
        ano_dre = int(df_processed['Ano'].max()) # Pega o último ano dos dados filtrados se nenhum ano específico for selecionado
    else:
        ano_dre = datetime.now().year # Fallback para o ano atual

    # Filtrar dados APENAS por ano (ignorar filtro de mês)
    if not df_processed.empty and 'Ano' in df_processed.columns:
        df_ano = df_processed[df_processed['Ano'] == ano_dre].copy()
        
        # Recalcular resultados com dados do ano completo
        if not df_ano.empty:
            # Usar valores anuais para despesas fixas
            salario_anual = st.session_state.get('salario_tab4', 1550.0) * 12
            contadora_anual = st.session_state.get('contadora_tab4', 316.0) * 12
            fornecedores_perc = st.session_state.get('fornecedores_tab4', 30.0)
            
            # Recalcula resultados ANUAIS
            resultados_ano = calculate_financial_results(
                df_ano, 
                st.session_state.get('salario_tab4', 1550.0), # Passa o salário mensal para a função
                st.session_state.get('contadora_tab4', 316.0), # Passa a contadora mensal
                fornecedores_perc
            )
            # Ajusta despesas para serem anuais APÓS o cálculo base mensal
            resultados_ano['despesas_com_pessoal'] = (st.session_state.get('salario_tab4', 1550.0) * 1.55) * 12
            resultados_ano['despesas_contabeis'] = st.session_state.get('contadora_tab4', 316.0) * 12
            resultados_ano['total_despesas_operacionais'] = resultados_ano['despesas_com_pessoal'] + resultados_ano['despesas_contabeis'] + resultados_ano['despesas_administrativas']
            resultados_ano['lucro_operacional'] = resultados_ano['lucro_bruto'] - resultados_ano['total_despesas_operacionais']
            resultados_ano['lucro_antes_ir'] = resultados_ano['lucro_operacional']
            resultados_ano['lucro_liquido'] = resultados_ano['lucro_antes_ir']
            # Recalcula margens com valores anuais
            if resultados_ano['receita_liquida'] > 0:
                resultados_ano['margem_operacional'] = (resultados_ano['lucro_operacional'] / resultados_ano['receita_liquida']) * 100
                resultados_ano['margem_liquida'] = (resultados_ano['lucro_liquido'] / resultados_ano['receita_liquida']) * 100
            else:
                 resultados_ano['margem_operacional'] = 0
                 resultados_ano['margem_liquida'] = 0

        else:
            # Se não houver dados para o ano, ZERAR os resultados para evitar confusão
            resultados_ano = {key: 0 for key in resultados.keys()}
            st.warning(f"⚠️ Não há dados de vendas registrados para o ano {ano_dre}. O DRE está zerado.")
    else:
        # Se df_processed estiver vazio, ZERAR os resultados
        resultados_ano = {key: 0 for key in resultados.keys()}
        st.warning(f"⚠️ Não há dados de vendas disponíveis para gerar o DRE do ano {ano_dre}.")

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
        st.markdown(f"**({format_val(resultados_ano['total_despesas_operacionais'])})**") # Valor total das despesas
    
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Despesas com Pessoal")
    with col2:
        st.markdown(f"({format_val(resultados_ano['despesas_com_pessoal'])})") 
    
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Serviços Contábeis")
    with col2:
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
        st.markdown("**-**") # Assumindo que não há IR para Simples nesse exemplo
    
    # Linha de separação
    st.markdown("---")
    
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
    
    # Filtrar categorias com valor zero para não poluir o gráfico
    financial_data = financial_data[financial_data['Valor'] != 0]

    if financial_data.empty:
        st.info("Sem dados financeiros para exibir o gráfico de composição.")
        return None

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
            sort=financial_data['Categoria'].tolist(), # Ordena pela ordem original filtrada
            axis=alt.Axis(labelFontSize=12)
        ),
        color=alt.Color(
            'Tipo:N',
            scale=alt.Scale(
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
            text="Composição do Resultado Financeiro (Período Filtrado)", # Título ajustado
            fontSize=20,
            anchor='start'
        ),
        height=alt.Step(40), # Altura dinâmica baseada no número de barras
        width=1000,
        padding={'bottom': 100}
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
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"

# --- Dashboard Premium Functions ---
def create_premium_kpi_cards(df):
    """Cria cards KPI premium com emoticons DENTRO dos boxes."""
    if df.empty:
        st.metric("💰 Faturamento Total", "R$ 0,00")
        st.metric("📊 Média Diária", "R$ 0,00")
        st.metric("🏆 Melhor Dia", "N/A")
        st.metric("📈 Tendência", "N/A")
        return
    
    total_vendas = df['Total'].sum()
    media_diaria = df['Total'].mean()
    melhor_dia_data = df.loc[df['Total'].idxmax(), 'Data'] if not df.empty and 'Data' in df.columns else None
    melhor_dia_str = melhor_dia_data.strftime('%d/%m/%Y') if melhor_dia_data else "N/A"
    melhor_dia_valor = df['Total'].max()

    # Cálculo de tendência (últimos 7 dias vs 7 dias anteriores)
    crescimento = 0.0
    delta_text = None
    if len(df) >= 14:
        df_sorted = df.sort_values('Data')
        ultimos_7_dias = df_sorted['Total'].tail(7).mean()
        anteriores_7_dias = df_sorted['Total'].iloc[-14:-7].mean()
        if anteriores_7_dias > 0:
            crescimento = ((ultimos_7_dias - anteriores_7_dias) / anteriores_7_dias) * 100
            delta_text = f"{crescimento:+.1f}% vs 7 dias ant."
        elif ultimos_7_dias > 0:
             delta_text = "↑ Apenas últimos 7 dias"
        else:
             delta_text = "Sem dados recentes"
    elif len(df) >= 7:
         delta_text = "Dados insuficientes (<14 dias)"
    else:
         delta_text = "Dados insuficientes (<7 dias)"

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
        st.metric(
            label="📈 Tendência (Últimos 7 dias)",
            value=f"{crescimento:.1f}%" if delta_text and '%' in delta_text else "--",
            delta=delta_text
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

    # DataFrame com todas as datas e vendas diárias (agrupadas caso haja múltiplas entradas por dia)
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
    # Semana 1 que pertence ao final do ano -> Semana 53
    max_week = full_df['week'].max()
    full_df.loc[(full_df['Data'].dt.month == 12) & (full_df['week'] == 1), 'week'] = max_week + 1
    
    # Mapear nomes dos meses para tooltip
    full_df['MesNome'] = full_df['Data'].dt.strftime('%B').str.capitalize()
    full_df['DataStr'] = full_df['Data'].dt.strftime('%d/%m/%Y')

    # Criar o heatmap
    heatmap = alt.Chart(full_df).mark_rect(
        stroke='rgba(255, 255, 255, 0.1)', # Borda sutil
        strokeWidth=0.5
    ).encode(
        x=alt.X('week:O', title='Semana do Ano', axis=None), # Oculta eixo X
        y=alt.Y('weekday:O', title=None, sort=np.arange(7), axis=alt.Axis(labels=True, ticks=False, domain=False, title=None, labelExpr="['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'][datum.value]")), # Eixo Y com dias da semana
        color=alt.Color('Total:Q', 
                        scale=alt.Scale(range=['#2a2a3a', CORES_MODO_ESCURO[1]], type='log', base=10, clamp=True), # Escala log para melhor visualização, cores do tema
                        legend=alt.Legend(title="Vendas (R$)", orient='bottom', direction='horizontal', padding=10, titlePadding=10)),
        tooltip=[
            alt.Tooltip('DataStr:N', title='Data'),
            alt.Tooltip('Total:Q', title='Vendas (R$)', format=',.2f')
        ]
    ).properties(
        title=alt.TitleParams(f"Heatmap de Atividade de Vendas - {current_year}", fontSize=18, anchor='start'),
        width=1000,
        height=150 # Altura fixa para visualização compacta
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )

    return heatmap

# --- Layout Principal do Streamlit ---

# Injeta o CSS
inject_css()

# Exibe a Logo com Aura no topo
display_logo_with_aura()

# Título Principal
st.title("📊 Dashboard Financeiro - Clips Burger")
st.markdown("--- ")

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
        available_months = sorted(df_processed['MêsNome'].dropna().unique(), key=lambda m: meses_ordem.index(m) if m in meses_ordem else -1)
        
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            selected_anos = st.multiselect("Selecione o(s) Ano(s)", available_years, default=available_years[0] if available_years else None)
        with col_filter2:
            selected_meses = st.multiselect("Selecione o(s) Mês(es)", available_months, default=available_months)

        # Aplicar filtros
        if selected_anos:
            df_filtered = df_processed[df_processed['Ano'].isin(selected_anos)].copy()
        else:
            df_filtered = df_processed.copy()
            
        if selected_meses:
            df_filtered = df_filtered[df_filtered['MêsNome'].isin(selected_meses)].copy()
            
    else:
        st.warning("Não há dados suficientes ou a coluna 'Ano' está ausente para aplicar filtros.")
        df_filtered = df_processed.copy()
        selected_anos = []
        selected_meses = []

    st.markdown("### KPIs Principais (Período Selecionado)")
    if not df_filtered.empty:
        create_premium_kpi_cards(df_filtered)
    else:
        st.info("Sem dados para exibir KPIs no período selecionado.")

    st.markdown("--- ")
    st.markdown("### Análises Visuais (Período Selecionado)")

    if not df_filtered.empty:
        # Layout em Grid para os gráficos principais
        st.markdown('<div class="premium-charts-grid">', unsafe_allow_html=True)
        
        # Coluna 1: Gráfico Acumulado e Heatmap
        with st.container():
            # Gráfico de Área Acumulado (Modificado)
            cumulative_chart = create_cumulative_area_chart(df_filtered)
            if cumulative_chart:
                st.altair_chart(cumulative_chart, use_container_width=True)
            else:
                st.info("Sem dados suficientes para o gráfico de evolução acumulada.")
            
            # Heatmap de Atividade (apenas para o último ano selecionado, se houver)
            if selected_anos:
                last_selected_year_df = df_processed[df_processed['Ano'] == max(selected_anos)].copy()
                if selected_meses:
                     last_selected_year_df = last_selected_year_df[last_selected_year_df['MêsNome'].isin(selected_meses)]
                heatmap = create_activity_heatmap(last_selected_year_df)
                if heatmap:
                    st.altair_chart(heatmap, use_container_width=True)
                else:
                    st.info(f"Sem dados suficientes para o heatmap de atividade do ano {max(selected_anos)}.")
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

        st.markdown('</div>', unsafe_allow_html=True)

        # Gráfico de Barras Empilhadas Diário (Largura Completa)
        st.markdown('<div class="premium-chart-full">', unsafe_allow_html=True)
        daily_stacked_bar = create_advanced_daily_sales_chart(df_filtered)
        if daily_stacked_bar:
            st.altair_chart(daily_stacked_bar, use_container_width=True)
        else:
            st.info("Sem dados suficientes para o gráfico de vendas diárias por método.")
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.info("Não há dados para exibir os gráficos no período selecionado.")

# --- Aba 2: Registro de Vendas ---
with tab2:
    st.header("📝 Registrar Nova Venda")
    worksheet = get_worksheet() # Tenta obter a worksheet aqui

    if worksheet:
        with st.form("sales_form", clear_on_submit=True):
            col_form1, col_form2 = st.columns([1, 3])
            with col_form1:
                sale_date = st.date_input("Data da Venda", value=datetime.today())
            
            col_form3, col_form4, col_form5 = st.columns(3)
            with col_form3:
                cartao_input = st.number_input("Valor Cartão (R$)", min_value=0.0, format="%.2f", step=10.0, help="Valor total recebido via cartão.")
            with col_form4:
                dinheiro_input = st.number_input("Valor Dinheiro (R$)", min_value=0.0, format="%.2f", step=10.0, help="Valor total recebido em dinheiro.")
            with col_form5:
                pix_input = st.number_input("Valor PIX (R$)", min_value=0.0, format="%.2f", step=10.0, help="Valor total recebido via PIX.")

            submitted = st.form_submit_button("💾 Registrar Venda")
            
            if submitted:
                if not cartao_input and not dinheiro_input and not pix_input:
                    st.warning("🚨 Por favor, insira um valor em pelo menos um método de pagamento.")
                else:
                    sale_date_str = sale_date.strftime("%d/%m/%Y")
                    success = add_data_to_sheet(sale_date_str, cartao_input, dinheiro_input, pix_input, worksheet)
                    if success:
                        # Limpar cache para forçar releitura dos dados na próxima vez
                        st.cache_data.clear()
                        st.rerun() # Recarrega a página para atualizar os dados exibidos
                    # Mensagens de erro/sucesso já são tratadas dentro de add_data_to_sheet
    else:
        st.error("❌ Conexão com a planilha falhou. Não é possível registrar vendas no momento. Verifique as configurações e a conexão.")

    st.markdown("--- ")
    st.header("🗓️ Histórico de Vendas Recentes")
    if not df_processed.empty:
        # Exibe as últimas 15 vendas registradas
        st.dataframe(df_processed.sort_values(by='Data', ascending=False).head(15)[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']], use_container_width=True)
    else:
        st.info("Nenhum registro de venda encontrado.")

# --- Aba 3: Análise Detalhada ---
with tab3:
    st.header("🔬 Análise Detalhada das Vendas")
    
    if not df_filtered.empty:
        st.markdown("### Distribuição dos Valores de Venda")
        sales_hist = create_sales_histogram(df_filtered)
        if sales_hist:
            st.altair_chart(sales_hist, use_container_width=True)
        else:
            st.info("Sem dados suficientes para gerar o histograma de vendas.")
        
        st.markdown("--- ")
        st.markdown("### Comparativo Mensal (Ano Selecionado)")
        # Comparativo mensal apenas se UM ano for selecionado
        if len(selected_anos) == 1:
            df_year_comp = df_processed[df_processed['Ano'] == selected_anos[0]].copy()
            if not df_year_comp.empty:
                monthly_sales = df_year_comp.groupby('MêsNome', observed=False)['Total'].sum().reset_index()
                # Ordenar pela ordem correta dos meses
                monthly_sales['MêsNome'] = pd.Categorical(monthly_sales['MêsNome'], categories=meses_ordem, ordered=True)
                monthly_sales = monthly_sales.sort_values('MêsNome')

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
                    width=1000,
                    height=400
                ).configure_view(stroke=None).configure(background='transparent')
                st.altair_chart(monthly_chart, use_container_width=True)
            else:
                st.info(f"Sem dados de vendas para o ano {selected_anos[0]} para análise mensal.")
        elif len(selected_anos) > 1:
            st.info("Selecione apenas um ano no filtro acima para ver o comparativo mensal.")
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
        salario = st.number_input(
            "Salário Mínimo Base (R$)", 
            min_value=0.0, 
            value=st.session_state.get('salario_tab4', 1550.00), 
            format="%.2f", 
            key='salario_tab4',
            help="Valor base do salário mínimo para cálculo de despesa com pessoal (será multiplicado por 1.55 para encargos)."
        )
    with col_cfg2:
        contadora = st.number_input(
            "Custo Mensal Contadora (R$)", 
            min_value=0.0, 
            value=st.session_state.get('contadora_tab4', 316.00), 
            format="%.2f", 
            key='contadora_tab4',
            help="Valor mensal pago pelos serviços contábeis."
        )
    with col_cfg3:
        fornecedores_perc = st.number_input(
            "Custo Fornecedores (% da Receita Bruta)", 
            min_value=0.0, 
            max_value=100.0, 
            value=st.session_state.get('fornecedores_tab4', 30.0), 
            format="%.1f", 
            key='fornecedores_tab4',
            help="Percentual estimado do custo dos produtos vendidos (fornecedores) sobre a receita bruta."
        )

    st.markdown("--- ")
    st.subheader("📊 Demonstração do Resultado do Exercício (DRE) - Anual")

    if not df_filtered.empty:
        # Calcula resultados financeiros com base nos dados FILTRADOS (para o gráfico)
        resultados_filtrados = calculate_financial_results(df_filtered, salario, contadora, fornecedores_perc)
        
        # Gera o DRE textual ANUAL (usa a função que filtra por ano internamente)
        create_dre_textual(resultados_filtrados, df_processed, selected_anos)
        
        st.markdown("--- ")
        st.subheader("Visualização Financeira (Período Filtrado)")
        # Gera o gráfico de barras financeiro com base nos dados FILTRADOS
        financial_chart = create_financial_dashboard_altair(resultados_filtrados)
        if financial_chart:
            st.altair_chart(financial_chart, use_container_width=True)
        else:
            st.info("Sem dados financeiros suficientes para exibir o gráfico no período selecionado.")
            
    else:
        st.info("Selecione um período com dados na Aba 'Dashboard Geral' para gerar o DRE e a análise financeira.")
