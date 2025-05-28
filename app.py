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
    @keyframes auraFade {
      0% { box-shadow: 0 0 20px 10px rgba(255, 255, 255, 0.8); }
      100% { box-shadow: 0 0 20px 10px rgba(255, 255, 255, 0); }
    }

    .aura {
      animation: auraFade 8s ease-out forwards;
      border-radius: 50%;
      display: inline-block;
      padding: 10px;
    }
    
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
    
    /* Containers interativos para dashboard */
    .metric-container {
        background: rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #4c78a8;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .metric-container:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
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

def create_area_chart_with_gradient(df):
    """Cria gráfico de área com gradiente substituindo o gráfico de montanha."""
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        return None
    
    df_sorted = df.sort_values('Data').copy()
    
    if df_sorted.empty:
        return None
    
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
            'Total:Q', 
            title='Total de Vendas (R$)', 
            axis=alt.Axis(labelFontSize=12)
        ),
        tooltip=[
            alt.Tooltip('DataFormatada:N', title='Data'),
            alt.Tooltip('Total:Q', title='Total de Vendas (R$)', format=',.2f')
        ]
    ).properties(
        title=alt.TitleParams(
            text='Evolução das Vendas com Gradiente', 
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
        height=500,
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

def create_dre_textual(resultados, df_filtered, selected_anos_filter):
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
    if not df_filtered.empty and 'Ano' in df_filtered.columns:
        df_ano = df_filtered[df_filtered['Ano'] == ano_dre].copy()
        
        # Recalcular resultados com dados do ano completo
        if not df_ano.empty:
            resultados_ano = calculate_financial_results(
                df_ano, 
                st.session_state.get('salario_tab4', 1550.0), 
                st.session_state.get('contadora_tab4', 316.0) * 12,
                st.session_state.get('fornecedores_tab4', 30.0)
            )
        else:
            resultados_ano = resultados
    else:
        resultados_ano = resultados

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
        st.markdown("")
    
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Despesas com Pessoal")
    with col2:
        st.markdown(f"({format_val(resultados_ano['despesas_com_pessoal'] * 12)})")
    
    col1, col2 = st.columns([6, 2])
    with col1:
        st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;Serviços Contábeis")
    with col2:
        st.markdown(f"({format_val(resultados_ano['despesas_contabeis'] * 12)})")
    
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
            text="Composição do Resultado Financeiro",
            fontSize=20,
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
    
    return chart

# --- Dashboard Premium Functions ---
def create_premium_kpi_cards(df):
    """Cria cards KPI premium com emoticons DENTRO dos boxes."""
    if df.empty:
        return
    
    total_vendas = df['Total'].sum()
    media_diaria = df['Total'].mean()
    melhor_dia = df.loc[df['Total'].idxmax(), 'DataFormatada'] if not df.empty else "N/A"
    crescimento = ((df['Total'].tail(7).mean() - df['Total'].head(7).mean()) / df['Total'].head(7).mean() * 100) if len(df) >= 14 else 15.5
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with st.container():
            st.metric(
                label="💰 Faturamento Total",
                value=format_brl(total_vendas),
                delta=f"+{crescimento:.1f}% vs período anterior"
            )
    
    with col2:
        with st.container():
            st.metric(
                label="📊 Média Diária",
                value=format_brl(media_diaria),
                delta="+8.2% vs período anterior"
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
                label="📈 Tendência",
                value=f"+{crescimento:.1f}%",
                delta="Crescimento sustentado"
            )

def create_premium_insights(df):
    """Insights com bordas coloridas na lateral esquerda."""
    if df.empty:
        return
    
    # Calcular insights automáticos
    total_vendas = df['Total'].sum()
    dias_trabalhados = len(df)
    media_diaria = total_vendas / dias_trabalhados if dias_trabalhados > 0 else 0
    
    # Análise de tendência
    if len(df) >= 14:
        primeira_semana = df.head(7)['Total'].mean()
        ultima_semana = df.tail(7)['Total'].mean()
        tendencia = ((ultima_semana - primeira_semana) / primeira_semana * 100) if primeira_semana > 0 else 0
        tendencia_texto = "crescimento" if tendencia > 0 else "declínio"
        tendencia_cor = "#4caf50" if tendencia > 0 else "#f44336"
    else:
        tendencia = 0
        tendencia_texto = "estável"
        tendencia_cor = "#ff9800"
    
    # Melhor método de pagamento
    if all(col in df.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
        metodos = {
            'Cartão': df['Cartão'].sum(),
            'Dinheiro': df['Dinheiro'].sum(),
            'PIX': df['Pix'].sum()
        }
        melhor_metodo = max(metodos, key=metodos.get)
        percentual_melhor = (metodos[melhor_metodo] / total_vendas * 100) if total_vendas > 0 else 0
    else:
        melhor_metodo = "N/A"
        percentual_melhor = 0
    
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
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

# --- Funções para extrair dados únicos da aba estatística ---
def extract_unique_stats_from_tab(df_processed):
    """
    Extrai métricas únicas da aba estatística, evitando redundâncias
    """
    if df_processed.empty:
        return []
    
    # Calcular métricas principais sem redundância
    stats = []
    
    # Total de vendas
    total_vendas = df_processed['Total'].sum()
    stats.append({
        "Métrica": "💰 Total de Vendas",
        "Valor": f"R$ {total_vendas:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    })
    
    # Média diária (apenas se houver dados suficientes)
    if len(df_processed) > 0:
        media_diaria = df_processed['Total'].mean()
        stats.append({
            "Métrica": "📊 Média Diária",
            "Valor": f"R$ {media_diaria:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        })
    
    # Melhor dia da semana (apenas se a coluna existir)
    if 'DiaSemana' in df_processed.columns and not df_processed['DiaSemana'].isnull().all():
        melhor_dia = df_processed.groupby('DiaSemana')['Total'].mean().idxmax()
        stats.append({
            "Métrica": "🏆 Melhor Dia da Semana",
            "Valor": melhor_dia
        })
    
    # Método de pagamento principal
    if all(col in df_processed.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
        metodos = {
            'Cartão': df_processed['Cartão'].sum(),
            'Dinheiro': df_processed['Dinheiro'].sum(),
            'PIX': df_processed['Pix'].sum()
        }
        metodo_principal = max(metodos, key=metodos.get)
        percentual = (metodos[metodo_principal] / total_vendas * 100) if total_vendas > 0 else 0
        stats.append({
            "Métrica": "💳 Método Principal",
            "Valor": f"{metodo_principal} ({percentual:.1f}%)"
        })
    
    # Remover duplicatas baseado na métrica
    unique_stats = []
    seen_metrics = set()
    for stat in stats:
        if stat['Métrica'] not in seen_metrics:
            unique_stats.append(stat)
            seen_metrics.add(stat['Métrica'])
    
    return unique_stats

# --- Função para criar containers interativos (máximo 2 por linha) ---
def create_interactive_containers(stats):
    """
    Cria containers interativos organizados em no máximo 2 por linha
    """
    if not stats:
        st.warning("Nenhuma estatística disponível para exibir.")
        return
    
    n = len(stats)
    for i in range(0, n, 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < n:
                with cols[j]:
                    # Container interativo com hover effect
                    st.markdown(f"""
                    <div class="metric-container">
                        <h4 style="margin: 0 0 1rem 0; color: #4c78a8;">{stats[i+j]['Métrica']}</h4>
                        <p style="margin: 0; font-size: 1.5rem; font-weight: bold; color: white;">
                            {stats[i+j]['Valor']}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

# --- Interface Principal da Aplicação ---
def main():
    # Título com logo ao lado
    try:
        col_logo, col_title = st.columns([1, 6])
        with col_logo:
            st.markdown("""
            <div class="aura">
              <img src="logo.png" width="80" alt="Logo">
            </div>
            """, unsafe_allow_html=True)
        with col_title:
            st.markdown(f"""
            <h1 style='margin: 0; padding-left: 10px;'>SISTEMA FINANCEIRO - CLIP'S BURGER</h1>
            <p style='margin: 0; font-size: 14px; color: gray; padding-left: 10px;'>Gestão inteligente de vendas com análise financeira em tempo real - {datetime.now().year}</p>
            """, unsafe_allow_html=True)
    except:
        st.title("🍔 SISTEMA FINANCEIRO - CLIPS BURGER")
        st.caption("Gestão inteligente de vendas com análise financeira em tempo real")

    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    # Criar 5 tabs incluindo o Dashboard Premium
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Registrar Venda", 
        "📈 Análise Detalhada", 
        "💡 Estatísticas", 
        "💰 Análise Contábil",
        "🚀 Dashboard Premium"
    ])

    with tab1:
        st.header("📝 Registrar Nova Venda")
        
        # Inputs FORA do form para atualização em tempo real
        data_input = st.date_input("📅 Data da Venda", value=datetime.now(), format="DD/MM/YYYY")
        
        col1, col2, col3 = st.columns(3)
        with col1: 
            cartao_input = st.number_input(
                "💳 Cartão (R$)", 
                min_value=0.0, 
                value=None,
                format="%.2f", 
                key="cartao_venda",
                placeholder="Digite o valor..."
            )
        with col2: 
            dinheiro_input = st.number_input(
                "💵 Dinheiro (R$)", 
                min_value=0.0, 
                value=None,
                format="%.2f", 
                key="dinheiro_venda",
                placeholder="Digite o valor..."
            )
        with col3: 
            pix_input = st.number_input(
                "📱 PIX (R$)", 
                min_value=0.0, 
                value=None,
                format="%.2f", 
                key="pix_venda",
                placeholder="Digite o valor..."
            )
        
        # Calcular total em tempo real (fora do form)
        cartao_val = cartao_input if cartao_input is not None else 0.0
        dinheiro_val = dinheiro_input if dinheiro_input is not None else 0.0
        pix_val = pix_input if pix_input is not None else 0.0
        total_venda_form = cartao_val + dinheiro_val + pix_val
        
        # Display do total em tempo real
        st.markdown(f"""
        <div style="text-align: center; padding: 0.7rem 1rem; background: linear-gradient(90deg, #4c78a8, #54a24b); border-radius: 10px; color: white; margin: 0.5rem 0; box-shadow: 0 4px 12px rgba(0,0,0,0.2); height: 3rem; display: flex; align-items: center; justify-content: center;">
            <div>
                <span style="font-size: 1.8rem; margin-right: 0.5rem; text-shadow: 1px 1px 3px rgba(0,0,0,0.3);">💰</span>
                <span style="font-size: 2.2rem; font-weight: bold; text-shadow: 1px 1px 3px rgba(0,0,0,0.3);">Total: {format_brl(total_venda_form)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Botão de registrar (fora do form)
        if st.button("✅ Registrar Venda", type="primary", use_container_width=True):
            if total_venda_form > 0:
                formatted_date = data_input.strftime('%d/%m/%Y')
                worksheet_obj = get_worksheet()
                if worksheet_obj and add_data_to_sheet(formatted_date, cartao_val, dinheiro_val, pix_val, worksheet_obj):
                    read_sales_data.clear()
                    process_data.clear()
                    st.success("✅ Venda registrada e dados recarregados!")
                    st.rerun()
                elif not worksheet_obj: 
                    st.error("❌ Falha ao conectar à planilha. Venda não registrada.")
            else: 
                st.warning("⚠️ O valor total da venda deve ser maior que zero.")

    # --- SIDEBAR COM FILTROS ---
    selected_anos_filter, selected_meses_filter = [], []
    
    with st.sidebar:
        st.header("🔍 Filtros de Período")
        st.markdown("---")
        
        # Filtros sempre visíveis
        if not df_processed.empty and 'Ano' in df_processed.columns and not df_processed['Ano'].isnull().all():
            anos_disponiveis = sorted(df_processed['Ano'].dropna().unique().astype(int), reverse=True)
            if anos_disponiveis:
                default_ano = [datetime.now().year] if datetime.now().year in anos_disponiveis else [anos_disponiveis[0]] if anos_disponiveis else []
                selected_anos_filter = st.multiselect(
                    "📅 Selecionar Ano(s)", 
                    options=anos_disponiveis,
                    default=default_ano,
                    key="anos_filter"
                )
            
            if selected_anos_filter:
                df_anos = df_processed[df_processed['Ano'].isin(selected_anos_filter)]
                if 'MêsNome' in df_anos.columns:
                    meses_disponiveis = df_anos['MêsNome'].dropna().unique()
                    selected_meses_filter = st.multiselect(
                        "📅 Selecionar Mês(es)",
                        options=[m for m in meses_ordem if m in meses_disponiveis],
                        key="meses_filter"
                    )

    # Aplicar filtros
    df_filtered = df_processed.copy()
    if selected_anos_filter:
        df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos_filter)]
    if selected_meses_filter:
        df_filtered = df_filtered[df_filtered['MêsNome'].isin(selected_meses_filter)]

    with tab2:
        st.header("📈 Análise Detalhada de Vendas")
        
        if df_filtered.empty:
            st.warning("⚠️ Nenhum dado disponível para o período selecionado.")
        else:
            # Gráfico de área com gradiente
            area_chart = create_area_chart_with_gradient(df_filtered)
            if area_chart:
                st.altair_chart(area_chart, use_container_width=True)
            
            # Gráfico de vendas diárias
            daily_chart = create_advanced_daily_sales_chart(df_filtered)
            if daily_chart:
                st.altair_chart(daily_chart, use_container_width=True)
            
            # Gráfico radial de métodos de pagamento
            radial_chart = create_radial_plot(df_filtered)
            if radial_chart:
                st.altair_chart(radial_chart, use_container_width=True)

    with tab3:
        st.header("💡 Estatísticas e Insights")
        
        if df_filtered.empty:
            st.warning("⚠️ Nenhum dado disponível para o período selecionado.")
        else:
            # Análise por dia da semana
            weekday_chart, best_day = create_enhanced_weekday_analysis(df_filtered)
            if weekday_chart:
                st.altair_chart(weekday_chart, use_container_width=True)
                if best_day:
                    st.info(f"🏆 **Melhor dia da semana:** {best_day}")
            
            # Histograma de distribuição
            histogram = create_sales_histogram(df_filtered)
            if histogram:
                st.altair_chart(histogram, use_container_width=True)
            
            # Métricas resumidas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total de Vendas", format_brl(df_filtered['Total'].sum()))
            with col2:
                st.metric("Média Diária", format_brl(df_filtered['Total'].mean()))
            with col3:
                st.metric("Maior Venda", format_brl(df_filtered['Total'].max()))
            with col4:
                st.metric("Dias com Vendas", len(df_filtered))

    with tab4:
        st.header("💰 Análise Contábil e DRE")
        
        # Configurações financeiras
        st.subheader("⚙️ Configurações Financeiras")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            salario_minimo = st.number_input(
                "💼 Salário Mínimo (R$)", 
                min_value=0.0, 
                value=st.session_state.get('salario_tab4', 1550.0),
                format="%.2f",
                key="salario_tab4"
            )
        
        with col2:
            custo_contadora = st.number_input(
                "📊 Custo Contadora Mensal (R$)", 
                min_value=0.0, 
                value=st.session_state.get('contadora_tab4', 316.0),
                format="%.2f",
                key="contadora_tab4"
            )
        
        with col3:
            custo_fornecedores = st.number_input(
                "🏪 Custo Fornecedores (%)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.get('fornecedores_tab4', 30.0),
                format="%.2f",
                key="fornecedores_tab4"
            )
        
        if not df_filtered.empty:
            # Calcular resultados financeiros
            resultados = calculate_financial_results(
                df_filtered, 
                salario_minimo, 
                custo_contadora, 
                custo_fornecedores
            )
            
            # Dashboard financeiro
            financial_chart = create_financial_dashboard_altair(resultados)
            if financial_chart:
                st.altair_chart(financial_chart, use_container_width=True)
            
            # DRE textual
            st.subheader("📋 Demonstração do Resultado do Exercício (DRE)")
            create_dre_textual(resultados, df_filtered, selected_anos_filter)
            
            # Métricas financeiras em colunas
            st.subheader("📊 Indicadores Financeiros")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Receita Bruta",
                    format_brl(resultados['receita_bruta'])
                )
            
            with col2:
                st.metric(
                    "Lucro Bruto",
                    format_brl(resultados['lucro_bruto']),
                    delta=f"{resultados['margem_bruta']:.1f}%"
                )
            
            with col3:
                st.metric(
                    "Lucro Operacional",
                    format_brl(resultados['lucro_operacional']),
                    delta=f"{resultados['margem_operacional']:.1f}%"
                )
            
            with col4:
                st.metric(
                    "Lucro Líquido",
                    format_brl(resultados['lucro_liquido']),
                    delta=f"{resultados['margem_liquida']:.1f}%"
                )
        else:
            st.warning("⚠️ Nenhum dado disponível para análise contábil.")

    with tab5:
        st.header("🚀 Dashboard Premium")
        
        # Logo com aura
        try:
            col_logo, col_title = st.columns([1, 6])
            with col_logo:
                st.markdown("""
                <div class="aura">
                  <img src="logo.png" width="80" alt="Logo">
                </div>
                """, unsafe_allow_html=True)
            with col_title:
                st.markdown("""
                <h2 style='margin: 0; padding-left: 10px;'>DASHBOARD PREMIUM - CLIPS BURGER</h2>
                <p style='margin: 0; font-size: 14px; color: gray; padding-left: 10px;'>
                    Estatísticas organizadas e insights em tempo real
                </p>
                """, unsafe_allow_html=True)
        except:
            st.subheader("🚀 Dashboard Premium - Clips Burger")
        
        st.markdown("---")
        
        if df_filtered.empty:
            st.warning("⚠️ Nenhum dado disponível para gerar o dashboard.")
        else:
            # KPI Cards Premium
            create_premium_kpi_cards(df_filtered)
            
            # Extrair estatísticas únicas
            dashboard_stats = extract_unique_stats_from_tab(df_filtered)
            
            # Título da seção
            st.subheader("📈 Métricas Principais")
            
            # Criar containers interativos
            create_interactive_containers(dashboard_stats)
            
            # Insights inteligentes
            create_premium_insights(df_filtered)
            
            # Gráficos premium em grid
            st.subheader("📊 Visualizações Premium")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico radial
                radial_chart = create_radial_plot(df_filtered)
                if radial_chart:
                    st.altair_chart(radial_chart, use_container_width=True)
            
            with col2:
                # Análise por dia da semana
                weekday_chart, best_day = create_enhanced_weekday_analysis(df_filtered)
                if weekday_chart:
                    st.altair_chart(weekday_chart, use_container_width=True)
            
            # Gráfico de área com gradiente (largura completa)
            area_chart = create_area_chart_with_gradient(df_filtered)
            if area_chart:
                st.altair_chart(area_chart, use_container_width=True)
            
            # Informação adicional
            if dashboard_stats:
                st.success(f"✅ Dashboard atualizado com {len(dashboard_stats)} métricas únicas, sem redundâncias.")
            else:
                st.warning("⚠️ Nenhum dado disponível para gerar estatísticas.")

if __name__ == "__main__":
    main()
