import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
import plotly.graph_objects as go # Import Plotly
import datetime # Import datetime (needed for heatmap)
from io import StringIO # Import StringIO (needed for heatmap logic if adapted directly, though we'll use the df)
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
    /* Estilo para a aura da logo */
    .logo-container-with-aura img {
        display: block; /* Garante que a imagem seja um bloco para aplicar filtros corretamente */
        margin-left: auto;
        margin-right: auto;
        max-width: 250px; /* Ajuste o tamanho máximo conforme necessário */
        filter: drop-shadow(0 0 10px white) drop-shadow(0 0 25px #87CEEB);
        padding-top: 20px; /* Adiciona espaço acima para a aura */
        padding-bottom: 20px; /* Adiciona espaço abaixo para a aura */
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

# --- Interface Principal da Aplicação ---
def main():
    # Título com logo ao lado
    try:
        col_logo, col_title = st.columns([1, 6])
        with col_logo:
            # Exibir a logo com a aura CSS
    st.markdown("<div class='logo-container-with-aura'><img src='logo.png' alt='Clips Burger Logo'></div>", unsafe_allow_html=True)
    # st.image("logo.png", width=250) # Linha original comentada       with col_title:
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
                selected_anos_filter = st.multiselect("📅 Ano(s):", options=anos_disponiveis, default=default_ano)
                
                if selected_anos_filter:
                    df_para_filtro_mes = df_processed[df_processed['Ano'].isin(selected_anos_filter)]
                    if not df_para_filtro_mes.empty and 'Mês' in df_para_filtro_mes.columns and not df_para_filtro_mes['Mês'].isnull().all():
                        meses_numeros_disponiveis = sorted(df_para_filtro_mes['Mês'].dropna().unique().astype(int))
                        meses_opcoes_dict = {m_num: meses_ordem[m_num-1] for m_num in meses_numeros_disponiveis if 1 <= m_num <= 12}
                        meses_opcoes_display = [f"{m_num} - {m_nome}" for m_num, m_nome in meses_opcoes_dict.items()]
                        default_mes_num = datetime.now().month
                        default_mes_str = f"{default_mes_num} - {meses_ordem[default_mes_num-1]}" if 1 <= default_mes_num <= 12 and meses_opcoes_dict else None
                        default_meses_selecionados = [default_mes_str] if default_mes_str and default_mes_str in meses_opcoes_display else meses_opcoes_display
                        selected_meses_str = st.multiselect("📆 Mês(es):", options=meses_opcoes_display, default=default_meses_selecionados)
                        selected_meses_filter = [int(m.split(" - ")[0]) for m in selected_meses_str]
            else: 
                st.info("📊 Nenhum ano disponível para filtro.")
        else: 
            st.info("📊 Não há dados processados para aplicar filtros.")

    # Aplicar filtros
    df_filtered = df_processed.copy()
    if not df_filtered.empty:
        if selected_anos_filter and 'Ano' in df_filtered.columns: 
            df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos_filter)]
        if selected_meses_filter and 'Mês' in df_filtered.columns: 
            df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses_filter)]

    # Mostrar informações dos filtros aplicados na sidebar
    if not df_filtered.empty:
        total_registros_filtrados = len(df_filtered)
        total_faturamento_filtrado = df_filtered['Total'].sum()
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📈 Resumo dos Filtros Aplicados")
        st.sidebar.metric("Registros Filtrados", total_registros_filtrados)
        st.sidebar.metric("Faturamento Filtrado", format_brl(total_faturamento_filtrado))
    elif not df_processed.empty:
        st.sidebar.markdown("---")
        st.sidebar.info("Nenhum registro corresponde aos filtros selecionados.")
    
    with tab2:
        st.header("🔎 Análise Detalhada de Vendas")
        if not df_filtered.empty and 'DataFormatada' in df_filtered.columns:
            st.subheader("🧾 Tabela de Vendas Filtradas")
            cols_to_display_tab2 = ['DataFormatada', 'DiaSemana', 'DiaDoMes', 'Cartão', 'Dinheiro', 'Pix', 'Total']
            cols_existentes_tab2 = [col for col in cols_to_display_tab2 if col in df_filtered.columns]
            
            if cols_existentes_tab2: 
                st.dataframe(df_filtered[cols_existentes_tab2], use_container_width=True, height=600, hide_index=True)
            else: 
                st.info("Colunas necessárias para a tabela de dados filtrados não estão disponíveis.")

            daily_chart = create_advanced_daily_sales_chart(df_filtered)
            if daily_chart:
                st.altair_chart(daily_chart, use_container_width=True)
            else:
                st.info("Sem dados de vendas diárias para exibir o gráfico nos filtros selecionados.")

            # MUDANÇA: Usar area chart com gradiente em vez de montanha
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

    with tab3:
        st.header("💡 Estatísticas e Tendências de Vendas")
        if not df_filtered.empty and 'Total' in df_filtered.columns and not df_filtered['Total'].isnull().all():
            st.subheader("💰 Resumo Financeiro Agregado")
            total_registros = len(df_filtered)
            total_faturamento = df_filtered['Total'].sum()
            media_por_registro = df_filtered['Total'].mean() if total_registros > 0 else 0
            maior_venda_diaria = df_filtered['Total'].max() if total_registros > 0 else 0
            menor_venda_diaria = df_filtered[df_filtered['Total'] > 0]['Total'].min() if not df_filtered[df_filtered['Total'] > 0].empty else 0
            
            # Layout em colunas para melhor aproveitamento do espaço
            col_metrics1, col_metrics2, col_metrics3 = st.columns(3)

            with col_metrics1:
                st.metric("🔢 Total de Registros", f"{total_registros}")
                st.metric("⬆️ Maior Venda Diária", format_brl(maior_venda_diaria))

            with col_metrics2:
                st.metric("💵 Faturamento Total", format_brl(total_faturamento))
                st.metric("⬇️ Menor Venda Diária (>0)", format_brl(menor_venda_diaria))

            with col_metrics3:
                st.metric("📈 Média por Registro", format_brl(media_por_registro))
            
            st.divider()

            # Seção de métodos de pagamento com cards lado a lado
            st.subheader("💳 Métodos de Pagamento (Visão Geral)")
            cartao_total = df_filtered['Cartão'].sum() if 'Cartão' in df_filtered else 0
            dinheiro_total = df_filtered['Dinheiro'].sum() if 'Dinheiro' in df_filtered else 0
            pix_total = df_filtered['Pix'].sum() if 'Pix' in df_filtered else 0
            total_pagamentos_geral = cartao_total + dinheiro_total + pix_total

            if total_pagamentos_geral > 0:
                cartao_pct = (cartao_total / total_pagamentos_geral * 100)
                dinheiro_pct = (dinheiro_total / total_pagamentos_geral * 100)
                pix_pct = (pix_total / total_pagamentos_geral * 100)
                
                # Layout sempre em 3 colunas lado a lado
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

            # MUDANÇA: Usar gráfico radial em vez de pizza
            radial_chart = create_radial_plot(df_filtered)
            if radial_chart:
                st.altair_chart(radial_chart, use_container_width=True)
            else:
                st.info("Sem dados de pagamento para exibir o gráfico radial nos filtros selecionados.")

            st.divider()

            # --- Heatmap Section ---
            st.subheader("🗓️ Calendário Heatmap de Vendas")
            
            # Determinar o ano para o heatmap (usar o primeiro ano selecionado no filtro, ou o ano atual se nenhum/multiplos selecionados)
            ano_heatmap = selected_anos_filter[0] if selected_anos_filter and len(selected_anos_filter) == 1 else datetime.now().year
            
            st.info(f"Exibindo heatmaps para o ano: {ano_heatmap}")

            # Gerar e exibir heatmap anual
            fig_anual, df_ano_completo_heatmap = criar_calendario_anual_heatmap(df_processed, ano_heatmap) # Usar df_processed para ter dados do ano todo
            if fig_anual:
                st.plotly_chart(fig_anual, use_container_width=True)
            else:
                st.warning(f"Não foi possível gerar o heatmap anual para {ano_heatmap}.")

            # Gerar e exibir heatmap mensal
            fig_mensal, _ = criar_heatmap_vendas_mensais(df_ano_completo_heatmap, ano_heatmap)
            if fig_mensal:
                st.plotly_chart(fig_mensal, use_container_width=True)
            else:
                 st.warning(f"Não foi possível gerar o heatmap mensal para {ano_heatmap}.")
            # --- Fim Heatmap Section ---

            st.divider()

            # Análise melhorada de dias da semana com percentuais
            weekday_chart, best_day = create_enhanced_weekday_analysis(df_filtered)
            if weekday_chart:
                st.altair_chart(weekday_chart, use_container_width=True)
                
                # Análise detalhada dos dias da semana
                if not df_filtered.empty and 'DiaSemana' in df_filtered.columns:
                    df_weekday_analysis = df_filtered.copy()
                    df_weekday_analysis['Total'] = pd.to_numeric(df_weekday_analysis['Total'], errors='coerce')
                    df_weekday_analysis = df_weekday_analysis.dropna(subset=['Total', 'DiaSemana'])
                    
                    if not df_weekday_analysis.empty:
                        # Calcular médias por dia da semana (excluindo domingo)
                        dias_trabalho = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"]
                        df_trabalho = df_weekday_analysis[df_weekday_analysis['DiaSemana'].isin(dias_trabalho)]
                        
                        if not df_trabalho.empty:
                            medias_por_dia = df_trabalho.groupby('DiaSemana', observed=True)['Total'].agg(['mean', 'count']).round(2)
                            medias_por_dia = medias_por_dia.reindex([d for d in dias_trabalho if d in medias_por_dia.index])
                            medias_por_dia = medias_por_dia.sort_values('mean', ascending=False)
                            
                            st.subheader("📊 Ranking dos Dias da Semana")
                            
                            # Criar colunas para o ranking
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
                            
                            st.divider()
                            
                            # Análise de frequência de trabalho
                            st.subheader("📅 Análise de Frequência de Trabalho")
                            
                            # Calcular dias do período filtrado
                            if not df_filtered.empty and 'Data' in df_filtered.columns:
                                data_inicio = df_filtered['Data'].min()
                                data_fim = df_filtered['Data'].max()
                                
                                # Calcular total de dias no período
                                total_dias_periodo = (data_fim - data_inicio).days + 1
                                
                                # Calcular domingos no período
                                domingos_periodo = 0
                                data_atual = data_inicio
                                while data_atual <= data_fim:
                                    if data_atual.weekday() == 6:  # Domingo = 6
                                        domingos_periodo += 1
                                    data_atual += timedelta(days=1)
                                
                                # Dias úteis esperados (excluindo domingos)
                                dias_uteis_esperados = total_dias_periodo - domingos_periodo
                                
                                # Dias efetivamente trabalhados
                                dias_trabalhados = len(df_filtered)
                                
                                # Dias de falta
                                dias_falta = dias_uteis_esperados - dias_trabalhados
                                
                                # Exibir métricas
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
                                            delta=f"-{dias_falta}"
                                        )
                                    else:
                                        st.metric(
                                            "✅ Frequência",
                                            "100%",
                                            help="Todos os dias úteis trabalhados!"
                                        )
                                
                                # Calcular taxa de frequência
                                if dias_uteis_esperados > 0:
                                    taxa_frequencia = (dias_trabalhados / dias_uteis_esperados) * 100
                                    
                                    if taxa_frequencia >= 95:
                                        st.success(f"🎯 **Excelente frequência:** {taxa_frequencia:.1f}% dos dias úteis trabalhados!")
                                    elif taxa_frequencia >= 80:
                                        st.info(f"👍 **Boa frequência:** {taxa_frequencia:.1f}% dos dias úteis trabalhados")
                                    else:
                                        st.warning(f"⚠️ **Atenção à frequência:** {taxa_frequencia:.1f}% dos dias úteis trabalhados")
            else:
                st.info("📊 Dados insuficientes para calcular a análise por dia da semana.")
            
            st.divider()

            sales_histogram_chart = create_sales_histogram(df_filtered)
            if sales_histogram_chart: 
                st.altair_chart(sales_histogram_chart, use_container_width=True)
            else: 
                st.info("Dados insuficientes para o Histograma de Vendas.")
        else:
            if df_processed.empty and df_raw.empty and get_worksheet() is None: 
                st.warning("Não foi possível carregar os dados da planilha.")
            elif df_processed.empty: 
                st.info("Não há dados processados para exibir estatísticas.")
            elif df_filtered.empty: 
                st.info("Nenhum dado corresponde aos filtros para exibir estatísticas.")
            else: 
                st.info("Não há dados de 'Total' para exibir nas Estatísticas.")

    # --- TAB4: ANÁLISE CONTÁBIL COMPLETA ---
    with tab4:
        st.header("📊 Análise Contábil e Financeira Detalhada")
        
        st.markdown("""
        ### 📋 **Sobre esta Análise**
        
        Esta análise segue as **normas contábeis brasileiras** com estrutura de DRE conforme:
        - **Lei 6.404/76** (Lei das S.A.) | **NBC TG 26** (Apresentação das Demonstrações Contábeis)
        - **Regime Tributário:** Simples Nacional (6% sobre receita tributável)
        - **Metodologia de Margens:** Margem Bruta = (Lucro Bruto ÷ Receita Líquida) × 100
        """)
        
        # Parâmetros Financeiros
        with st.container(border=True):
            st.subheader("⚙️ Parâmetros para Simulação Contábil")
            
            col_param1, col_param2, col_param3 = st.columns(3)
            with col_param1:
                salario_minimo_input = st.number_input(
                    "💼 Salário Base Funcionário (R$)",
                    min_value=0.0, value=1550.0, format="%.2f",
                    help="Salário base do funcionário. Os encargos (55%) serão calculados automaticamente.",
                    key="salario_tab4"
                )
            with col_param2:
                custo_contadora_input = st.number_input(
                    "📋 Honorários Contábeis (R$)",
                    min_value=0.0, value=316.0, format="%.2f",
                    help="Valor mensal pago pelos serviços contábeis.",
                    key="contadora_tab4"
                )
            with col_param3:
                custo_fornecedores_percentual = st.number_input(
                    "📦 Custo dos Produtos (%)",
                    min_value=0.0, max_value=100.0, value=30.0, format="%.1f",
                    help="Percentual da receita bruta destinado à compra de produtos.",
                    key="fornecedores_tab4"
                )

        st.markdown("---")

        if df_filtered.empty or 'Total' not in df_filtered.columns:
            st.warning("📊 **Não há dados suficientes para análise contábil.** Ajuste os filtros ou registre vendas.")
        else:
            # Calcular resultados financeiros
            resultados = calculate_financial_results(
                df_filtered, salario_minimo_input, custo_contadora_input, custo_fornecedores_percentual
            )

            # === DRE TEXTUAL ===
            with st.container(border=True):
                create_dre_textual(resultados, df_processed, selected_anos_filter)

            st.markdown("---")

            # === DASHBOARD VISUAL ===
            financial_dashboard = create_financial_dashboard_altair(resultados)
            if financial_dashboard:
                st.altair_chart(financial_dashboard, use_container_width=True)

            st.markdown("---")

            # === ANÁLISE DE MARGENS ===
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

            # === RESUMO EXECUTIVO ===
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

            # Nota final
            st.info("""
            💡 **Nota Importante:** Esta DRE segue a estrutura contábil brasileira oficial. 
            Para decisões estratégicas, consulte sempre um contador qualificado.
            """)

    # --- TAB5: DASHBOARD PREMIUM ---
    with tab5:
        st.header("🚀 Dashboard Premium")
        
        if not df_filtered.empty:
            # KPIs Premium usando st.columns (sem HTML complexo)
            create_premium_kpi_cards(df_filtered)
            
            st.markdown("---")
            
            # Gráficos lado a lado - 2/3 para vendas diárias, 1/3 para radial
            col_chart1, col_chart2 = st.columns([2, 1])
            
            with col_chart1:
                # Gráfico de vendas diárias (2/3 do espaço)
                daily_chart = create_advanced_daily_sales_chart(df_filtered)
                if daily_chart:
                    st.altair_chart(daily_chart, use_container_width=True)
            
            with col_chart2:
                # MUDANÇA: Gráfico radial em vez de pizza (1/3 do espaço)
                radial_chart = create_radial_plot(df_filtered)
                if radial_chart:
                    st.altair_chart(radial_chart, use_container_width=True)
            
            st.markdown("---")
            
            # MUDANÇA: Gráfico de área com gradiente em tela cheia
            area_chart = create_area_chart_with_gradient(df_filtered)
            if area_chart:
                st.altair_chart(area_chart, use_container_width=True)
            
            st.markdown("---")
            
            # Insights Inteligentes usando st.columns (sem HTML complexo)
            create_premium_insights(df_filtered)
            
        else:
            st.warning("⚠️ Sem dados disponíveis. Ajuste os filtros na sidebar ou registre algumas vendas para visualizar o dashboard premium.")

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    main()


# --- Funções para Heatmap (Adaptadas do código fornecido) ---
import plotly.graph_objects as go
import datetime as dt # Renomeado para evitar conflito com datetime.datetime

def criar_calendario_anual_heatmap(df, ano):
    """Cria calendário anual heatmap com base no DataFrame processado."""
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        st.warning(f"Dados insuficientes ou ausentes para gerar o heatmap anual de {ano}.")
        return None, None

    # Filtrar dados para o ano especificado
    df_ano_filtrado = df[df['Data'].dt.year == ano].copy()

    if df_ano_filtrado.empty:
        st.info(f"Sem dados de vendas registrados para o ano {ano} para gerar o heatmap.")
        # Criar um DataFrame vazio com as colunas esperadas para evitar erros posteriores
        df_ano_completo = pd.DataFrame(columns=['Data', 'Cartão', 'Dinheiro', 'Pix', 'Total_Vendas'])
        df_ano_completo['Data'] = pd.to_datetime(df_ano_completo['Data'])
    else:
        # Renomear 'Total' para 'Total_Vendas' para compatibilidade com a função original
        df_ano_filtrado.rename(columns={'Total': 'Total_Vendas'}, inplace=True)

        # Criar range completo do ano
        dates_completo = pd.date_range(f'{ano}-01-01', f'{ano}-12-31', freq='D')

        # Criar DataFrame completo para o ano todo, preenchendo dias sem vendas
        dados_ano_completo = []
        df_ano_filtrado_indexed = df_ano_filtrado.set_index('Data')
        for date in dates_completo:
            if date in df_ano_filtrado_indexed.index:
                row = df_ano_filtrado_indexed.loc[date]
                # Se houver múltiplas entradas para o mesmo dia, some os valores
                if isinstance(row, pd.DataFrame):
                    row = row.sum()
                dados_ano_completo.append({
                    'Data': date,
                    'Cartão': row.get('Cartão', 0),
                    'Dinheiro': row.get('Dinheiro', 0),
                    'Pix': row.get('Pix', 0),
                    'Total_Vendas': row.get('Total_Vendas', 0)
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

    # Calcular posições corretamente para começar em 01/01
    df_ano_completo['data_str'] = df_ano_completo['Data'].dt.strftime('%d/%m/%Y')
    df_ano_completo['dia_semana'] = df_ano_completo['Data'].dt.dayofweek  # 0=Monday

    # Calcular semana do ano corretamente
    try:
        primeiro_dia = dt.date(ano, 1, 1)
    except ValueError:
        st.error(f"Ano inválido fornecido para o heatmap: {ano}")
        return None, None
    primeiro_dia_semana = primeiro_dia.weekday()  # Que dia da semana é 01/01

    # Criar posições x,y para cada dia
    x_positions = []
    y_positions = []
    valores = []
    hover_texts = []

    for _, row in df_ano_completo.iterrows():
        # Calcular dias desde 01/01
        dias_desde_inicio = (row['Data'].date() - primeiro_dia).days

        # Calcular posição da semana (x) e dia da semana (y)
        semana = (dias_desde_inicio + primeiro_dia_semana) // 7
        dia_semana = (dias_desde_inicio + primeiro_dia_semana) % 7

        x_positions.append(semana)
        y_positions.append(dia_semana)

        # Classificar valores nas 4 faixas (ajustado para usar Total_Vendas)
        total_vendas_dia = row.get('Total_Vendas', 0)
        if total_vendas_dia == 0:
            categoria = 0  # Sem vendas
        elif total_vendas_dia < 1500:
            categoria = 1  # Verde mais claro
        elif total_vendas_dia < 2500:
            categoria = 2  # Verde claro
        elif total_vendas_dia < 3000:
            categoria = 3  # Verde médio
        else:
            categoria = 4  # Verde escuro

        valores.append(categoria)

        # Criar hover text - apenas data, total, cartão, dinheiro e pix
        if total_vendas_dia > 0:
            hover_text = (
                f"📅 {row['data_str']}<br>"
                f"💰 Total: R$ {total_vendas_dia:,.2f}<br>"
                f"💳 Cartão: R$ {row.get('Cartão', 0):,.2f}<br>"
                f"💵 Dinheiro: R$ {row.get('Dinheiro', 0):,.2f}<br>"
                f"📱 Pix: R$ {row.get('Pix', 0):,.2f}"
            )
        else:
            hover_text = f"📅 {row['data_str']}<br>❌ Sem vendas"

        hover_texts.append(hover_text)

    # Criar matriz para heatmap
    max_semana = max(x_positions) + 1 if x_positions else 1 # Evitar erro se não houver dados
    matriz_vendas = np.full((7, max_semana), 0.0)  # Inicializar com 0
    matriz_hover = np.full((7, max_semana), '', dtype=object)

    for x, y, valor, hover in zip(x_positions, y_positions, valores, hover_texts):
        if 0 <= y < 7 and 0 <= x < max_semana:
            matriz_vendas[y, x] = valor
            matriz_hover[y, x] = hover

    # Escala de cores com #161b22 para dias vazios
    escala_4_tons = [
        [0.0, '#161b22'],      # Dias sem vendas
        [0.001, '#39D353'],    # Nível 1 - Verde mais claro
        [0.25, '#39D353'],
        [0.251, '#37AB4B'],    # Nível 2 - Verde claro
        [0.5, '#37AB4B'],
        [0.501, '#006D31'],    # Nível 3 - Verde médio
        [0.75, '#006D31'],
        [0.751, '#0D4428'],    # Nível 4 - Verde escuro
        [1.0, '#0D4428']
    ]

    # Criar heatmap SEM LEGENDA
    fig = go.Figure(data=go.Heatmap(
        z=matriz_vendas,
        text=matriz_hover,
        hovertemplate='%{text}<extra></extra>',
        colorscale=escala_4_tons,
        showscale=False,  # REMOVER LEGENDA
        zmin=0,
        zmax=4,
        xgap=3,
        ygap=3,
        hoverongaps=False
    ))

    # Calcular posições dos meses para labels
    meses_posicoes = []
    meses_nomes_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                      'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    for mes in range(1, 13):
        try:
            primeiro_dia_mes = dt.date(ano, mes, 1)
            dias_desde_inicio = (primeiro_dia_mes - primeiro_dia).days
            semana_mes = (dias_desde_inicio + primeiro_dia_semana) // 7
            meses_posicoes.append(semana_mes)
        except ValueError: # Caso o ano seja inválido, já tratado acima
            pass

    # Layout com MAIOR DISTÂNCIA entre nomes dos dias e o gráfico
    fig.update_layout(
        title=f"📊 Calendário de Vendas Heatmap {ano}",
        paper_bgcolor='rgba(0,0,0,0)',  # Background transparente
        plot_bgcolor='rgba(0,0,0,0)',   # Background transparente
        font=dict(color='#ffffff', family="Arial"),  # LETRAS BRANCAS

        xaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            tickmode='array',
            tickvals=meses_posicoes,
            ticktext=meses_nomes_pt,
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
            ticklen=0,  # Remover tick marks
            ticklabelstandoff=5  # PROPRIEDADE CORRETA PARA AFASTAR OS LABELS
        ),

        height=350, # Altura ajustada para melhor visualização no Streamlit
        # width=1400, # Largura removida para ser responsiva
        autosize=True,
        title_x=0.5,
        title_font=dict(size=18, color='#ffffff'),
        margin=dict(l=80, r=20, t=100, b=20)  # Margens ajustadas
    )

    return fig, df_ano_completo

def criar_heatmap_vendas_mensais(df_ano_completo, ano):
    """Função para criar heatmap mensal horizontal com base no DataFrame anual completo."""
    if df_ano_completo is None or df_ano_completo.empty:
        st.warning(f"Dados anuais completos ausentes para gerar o heatmap mensal de {ano}.")
        return None, None

    # Agrupar vendas por mês a partir do df_ano_completo
    df_vendas = df_ano_completo[df_ano_completo['Total_Vendas'] > 0].copy()
    if not df_vendas.empty:
        df_vendas['Mes'] = df_vendas['Data'].dt.month
        vendas_mensais = df_vendas.groupby('Mes').agg({
            'Total_Vendas': 'sum',
            'Cartão': 'sum',
            'Dinheiro': 'sum',
            'Pix': 'sum'
        }).reset_index()
    else:
        vendas_mensais = pd.DataFrame(columns=['Mes', 'Total_Vendas', 'Cartão', 'Dinheiro', 'Pix'])

    # Nomes dos meses
    meses_nomes_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                      'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    # Criar matriz horizontal (1 linha x 12 colunas)
    matriz_mensal = np.zeros((1, 12))
    matriz_hover_mensal = np.full((1, 12), '', dtype=object)

    # Preencher todos os 12 meses
    for mes_idx in range(12):
        mes_num = mes_idx + 1
        mes_nome = meses_nomes_pt[mes_idx]

        dados_mes = vendas_mensais[vendas_mensais['Mes'] == mes_num]

        if len(dados_mes) > 0:
            row = dados_mes.iloc[0]
            total_vendas_mes = row.get('Total_Vendas', 0)
            matriz_mensal[0, mes_idx] = total_vendas_mes

            # Hover - apenas mês, total, cartão, dinheiro e pix
            hover_text = (
                f"📅 {mes_nome} {ano}<br>"
                f"💰 Total: R$ {total_vendas_mes:,.2f}<br>"
                f"💳 Cartão: R$ {row.get('Cartão', 0):,.2f}<br>"
                f"💵 Dinheiro: R$ {row.get('Dinheiro', 0):,.2f}<br>"
                f"📱 Pix: R$ {row.get('Pix', 0):,.2f}"
            )
        else:
            matriz_mensal[0, mes_idx] = 0 # Garante que meses sem vendas fiquem com 0
            hover_text = f"📅 {mes_nome} {ano}<br>❌ Sem dados"

        matriz_hover_mensal[0, mes_idx] = hover_text

    # Determinar zmin e zmax para a escala de cores mensal
    min_vendas_mes = vendas_mensais['Total_Vendas'].min() if not vendas_mensais.empty else 0
    max_vendas_mes = vendas_mensais['Total_Vendas'].max() if not vendas_mensais.empty else 1 # Evitar divisão por zero se max for 0
    if max_vendas_mes == 0: max_vendas_mes = 1 # Evitar divisão por zero

    # Escala de cores proporcional aos valores mensais
    escala_mensal = [
        [0.0, '#161b22'],     # Meses sem dados / valor 0
        [0.001, '#39D353'],   # Verde mais claro (início da escala)
        [0.25, '#37AB4B'],    # Verde claro
        [0.5, '#006D31'],     # Verde médio
        [1.0, '#0D4428']      # Verde escuro (fim da escala)
    ]

    # Criar heatmap mensal horizontal SEM LEGENDA
    fig_mensal = go.Figure(data=go.Heatmap(
        z=matriz_mensal,
        text=matriz_hover_mensal,
        hovertemplate='%{text}<extra></extra>',
        colorscale=escala_mensal,
        showscale=False,  # REMOVER LEGENDA
        xgap=5,
        ygap=5,
        zmin=0, # Fixar mínimo em 0
        zmax=max_vendas_mes # Usar máximo real para a escala
    ))

    # Layout do heatmap mensal com espaçamento correto
    fig_mensal.update_layout(
        title=f'📊 Vendas Mensais Heatmap {ano}',
        paper_bgcolor='rgba(0,0,0,0)',  # Background transparente
        plot_bgcolor='rgba(0,0,0,0)',   # Background transparente
        font=dict(color='#ffffff', family="Arial"),  # LETRAS BRANCAS

        xaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            tickmode='array',
            tickvals=list(range(12)),
            ticktext=meses_nomes_pt,
            tickfont=dict(color='#ffffff', size=14),
            side='bottom'
        ),

        yaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),

        height=200, # Altura ajustada
        # width=1400, # Largura removida para ser responsiva
        autosize=True,
        title_x=0.5,
        title_font=dict(size=18, color='#ffffff'),
        margin=dict(l=80, r=20, t=80, b=50)  # Margens ajustadas
    )

    return fig_mensal, vendas_mensais

# --- Fim das Funções Heatmap ---


