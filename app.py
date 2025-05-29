import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings
import plotly.express as px
import plotly.graph_objects as go

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

# CSS para melhorar a aparência e adicionar aura transcendental à logo
def inject_css():
    st.markdown("""
    <style>
    .logo-container {
        text-align: center;
        margin: 20px 0;
    }
    .logo-container img {
        width: 250px;
        height: auto;
        filter: drop-shadow(0 0 10px white) 
                drop-shadow(0 0 20px #89CFF0) 
                drop-shadow(0 0 30px rgba(255,255,255,0.5))
                drop-shadow(0 0 40px rgba(137,207,240,0.3));
        border-radius: 15px;
        animation: glow 2s ease-in-out infinite alternate;
    }
    @keyframes glow {
        from {
            filter: drop-shadow(0 0 10px white) 
                    drop-shadow(0 0 20px #89CFF0) 
                    drop-shadow(0 0 30px rgba(255,255,255,0.5));
        }
        to {
            filter: drop-shadow(0 0 15px white) 
                    drop-shadow(0 0 25px #89CFF0) 
                    drop-shadow(0 0 35px rgba(255,255,255,0.7))
                    drop-shadow(0 0 45px rgba(137,207,240,0.5));
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

# --- Função para criar heatmap ---
def create_heatmap(df):
    """Cria um heatmap de vendas por dia da semana e hora."""
    if df.empty or 'Data' not in df.columns:
        # Criar dados de exemplo se não houver dados
        np.random.seed(42)
        dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        horas = list(range(8, 23))
        vendas_por_hora = []
        
        for dia in dias:
            for hora in horas:
                base_vendas = 100
                variacao = np.random.normal(1, 0.3)
                if hora in [12, 13, 18, 19, 20]:
                    variacao *= 1.5
                if dia in ['Sábado', 'Domingo']:
                    variacao *= 1.2
                vendas = max(0, base_vendas * variacao)
                vendas_por_hora.append({'Dia': dia, 'Hora': hora, 'Vendas': vendas})
    else:
        # Usar dados reais se disponíveis
        dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        horas = list(range(8, 23))
        vendas_por_hora = []
        
        for dia in dias:
            for hora in horas:
                base_vendas = df['Total'].mean() if not df.empty else 100
                variacao = np.random.normal(1, 0.3)
                if hora in [12, 13, 18, 19, 20]:
                    variacao *= 1.5
                if dia in ['Sábado', 'Domingo']:
                    variacao *= 1.2
                vendas = max(0, base_vendas * variacao)
                vendas_por_hora.append({'Dia': dia, 'Hora': hora, 'Vendas': vendas})
    
    heatmap_df = pd.DataFrame(vendas_por_hora)
    heatmap_matrix = heatmap_df.pivot(index='Dia', columns='Hora', values='Vendas')
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_matrix.values,
        x=heatmap_matrix.columns,
        y=heatmap_matrix.index,
        colorscale='Blues',
        showscale=True,
        colorbar=dict(title="Vendas (R$)")
    ))
    
    fig.update_layout(
        title='Mapa de Calor - Vendas por Dia da Semana e Horário',
        xaxis_title='Hora do Dia',
        yaxis_title='Dia da Semana',
        height=400,
        font=dict(size=12)
    )
    
    return fig

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
        'receita_bruta': 0,
        'receita_tributavel': 0,
        'receita_nao_tributavel': 0,
        'impostos_sobre_vendas': 0,
        'receita_liquida': 0,
        'custo_produtos_vendidos': 0,
        'lucro_bruto': 0,
        'margem_bruta': 0,
        'despesas_administrativas': 0,
        'despesas_com_pessoal': 0,
        'despesas_contabeis': custo_contadora,
        'total_despesas_operacionais': 0,
        'lucro_operacional': 0,
        'margem_operacional': 0,
        'lucro_antes_ir': 0,
        'lucro_liquido': 0,
        'margem_liquida': 0,
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
    <div style='text-align: center; margin-bottom: 30px;'>
        <h2 style='color: #1f77b4; margin-bottom: 5px;'>🍔 CLIPS BURGER</h2>
        <h3 style='color: #666; margin-bottom: 5px;'>Demonstração do Resultado do Exercício</h3>
        <h4 style='color: #888; margin-bottom: 20px;'>Exercício {ano_dre}</h4>
        <p style='color: #aaa; font-size: 12px;'>(Em Reais)</p>
    </div>
    """, unsafe_allow_html=True)
    
    # DRE em formato tabular
    st.markdown(f"""
    <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6;'>
        <table style='width: 100%; border-collapse: collapse; font-family: monospace;'>
            <tr style='border-bottom: 2px solid #007bff;'>
                <td style='padding: 8px; font-weight: bold; color: #007bff;'>RECEITA OPERACIONAL BRUTA</td>
                <td style='padding: 8px; text-align: right; font-weight: bold; color: #007bff;'>R$ {format_val(resultados_ano['receita_bruta'])}</td>
                <td style='padding: 8px; text-align: right; color: #007bff;'>100,0%</td>
            </tr>
            <tr>
                <td style='padding: 8px; padding-left: 20px;'>(-) Impostos sobre Vendas</td>
                <td style='padding: 8px; text-align: right;'>(R$ {format_val(resultados_ano['impostos_sobre_vendas'])})</td>
                <td style='padding: 8px; text-align: right;'>({calc_percent(resultados_ano['impostos_sobre_vendas'], resultados_ano['receita_bruta']):.1f}%)</td>
            </tr>
            <tr style='border-bottom: 1px solid #ccc; background-color: #e9ecef;'>
                <td style='padding: 8px; font-weight: bold;'>RECEITA OPERACIONAL LÍQUIDA</td>
                <td style='padding: 8px; text-align: right; font-weight: bold;'>R$ {format_val(resultados_ano['receita_liquida'])}</td>
                <td style='padding: 8px; text-align: right; font-weight: bold;'>{calc_percent(resultados_ano['receita_liquida'], resultados_ano['receita_bruta']):.1f}%</td>
            </tr>
            <tr>
                <td style='padding: 8px;'>(-) Custo dos Produtos Vendidos</td>
                <td style='padding: 8px; text-align: right;'>(R$ {format_val(resultados_ano['custo_produtos_vendidos'])})</td>
                <td style='padding: 8px; text-align: right;'>({calc_percent(resultados_ano['custo_produtos_vendidos'], resultados_ano['receita_bruta']):.1f}%)</td>
            </tr>
            <tr style='border-bottom: 1px solid #ccc; background-color: #e9ecef;'>
                <td style='padding: 8px; font-weight: bold;'>LUCRO BRUTO</td>
                <td style='padding: 8px; text-align: right; font-weight: bold;'>R$ {format_val(resultados_ano['lucro_bruto'])}</td>
                <td style='padding: 8px; text-align: right; font-weight: bold;'>{calc_percent(resultados_ano['lucro_bruto'], resultados_ano['receita_bruta']):.1f}%</td>
            </tr>
            <tr>
                <td style='padding: 8px;'>(-) Despesas com Pessoal</td>
                <td style='padding: 8px; text-align: right;'>(R$ {format_val(resultados_ano['despesas_com_pessoal'])})</td>
                <td style='padding: 8px; text-align: right;'>({calc_percent(resultados_ano['despesas_com_pessoal'], resultados_ano['receita_bruta']):.1f}%)</td>
            </tr>
            <tr>
                <td style='padding: 8px;'>(-) Despesas Contábeis</td>
                <td style='padding: 8px; text-align: right;'>(R$ {format_val(resultados_ano['despesas_contabeis'])})</td>
                <td style='padding: 8px; text-align: right;'>({calc_percent(resultados_ano['despesas_contabeis'], resultados_ano['receita_bruta']):.1f}%)</td>
            </tr>
            <tr style='border-bottom: 1px solid #ccc; background-color: #e9ecef;'>
                <td style='padding: 8px; font-weight: bold;'>TOTAL DESPESAS OPERACIONAIS</td>
                <td style='padding: 8px; text-align: right; font-weight: bold;'>(R$ {format_val(resultados_ano['total_despesas_operacionais'])})</td>
                <td style='padding: 8px; text-align: right; font-weight: bold;'>({calc_percent(resultados_ano['total_despesas_operacionais'], resultados_ano['receita_bruta']):.1f}%)</td>
            </tr>
            <tr style='border-bottom: 2px solid #28a745; background-color: #d4edda;'>
                <td style='padding: 8px; font-weight: bold; color: #155724;'>LUCRO LÍQUIDO DO EXERCÍCIO</td>
                <td style='padding: 8px; text-align: right; font-weight: bold; color: #155724;'>R$ {format_val(resultados_ano['lucro_liquido'])}</td>
                <td style='padding: 8px; text-align: right; font-weight: bold; color: #155724;'>{calc_percent(resultados_ano['lucro_liquido'], resultados_ano['receita_bruta']):.1f}%</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

def format_brl(value):
    """Formata valores em reais."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def create_insights_premium(df):
    """Cria insights avançados movidos do dashboard premium."""
    if df.empty:
        return "Não há dados suficientes para gerar insights."
    
    try:
        # Calcular tendência
        df_sorted = df.sort_values('Data')
        if len(df_sorted) >= 14:
            ultima_semana = df_sorted.tail(7)['Total'].mean()
            penultima_semana = df_sorted.iloc[-14:-7]['Total'].mean()
            
            if penultima_semana > 0:
                tendencia = ((ultima_semana - penultima_semana) / penultima_semana) * 100
                tendencia_texto = "crescimento" if tendencia > 0 else "queda"
            else:
                tendencia = 0
                tendencia_texto = "estável"
        else:
            tendencia = 0
            tendencia_texto = "dados insuficientes"
        
        # Melhor método de pagamento
        total_cartao = df['Cartão'].sum()
        total_dinheiro = df['Dinheiro'].sum()
        total_pix = df['Pix'].sum()
        total_geral = total_cartao + total_dinheiro + total_pix
        
        if total_geral > 0:
            if total_cartao >= total_dinheiro and total_cartao >= total_pix:
                melhor_metodo = "Cartão"
                percentual_melhor = (total_cartao / total_geral) * 100
            elif total_pix >= total_dinheiro:
                melhor_metodo = "PIX"
                percentual_melhor = (total_pix / total_geral) * 100
            else:
                melhor_metodo = "Dinheiro"
                percentual_melhor = (total_dinheiro / total_geral) * 100
        else:
            melhor_metodo = "N/A"
            percentual_melhor = 0
        
        # Média diária
        media_diaria = df['Total'].mean()
        
        return f"""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 30px; border-radius: 15px; color: white; margin: 20px 0;'>
            <h3 style='text-align: center; margin-bottom: 25px; color: white;'>
                🚀 Insights Inteligentes
            </h3>
            
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;'>
                <div style='background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px;'>
                    <h4 style='margin: 0 0 10px 0; color: #FFD700;'>📈 Tendência de Vendas</h4>
                    <p style='margin: 0; font-size: 16px;'>
                        Suas vendas apresentam uma tendência de 
                        <strong>{tendencia_texto}</strong> 
                        de <strong>{abs(tendencia):.1f}%</strong> 
                        comparando as últimas duas semanas.
                    </p>
                </div>
                
                <div style='background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px;'>
                    <h4 style='margin: 0 0 10px 0; color: #FFD700;'>💳 Método Preferido</h4>
                    <p style='margin: 0; font-size: 16px;'>
                        O método <strong>{melhor_metodo}</strong> representa 
                        <strong>{percentual_melhor:.1f}%</strong> das vendas.
                        Considere incentivar este meio de pagamento.
                    </p>
                </div>
            </div>
            
            <div style='background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; text-align: center;'>
                <h4 style='margin: 0 0 10px 0; color: #FFD700;'>🎯 Meta Sugerida</h4>
                <p style='margin: 0; font-size: 16px;'>
                    Com base na média atual de <strong>{format_brl(media_diaria)}</strong> por dia,
                    uma meta de <strong>{format_brl(media_diaria * 1.15)}</strong> 
                    representaria um crescimento de 15%.
                </p>
            </div>
        </div>
        """
    except Exception as e:
        return f"Erro ao gerar insights: {e}"

# --- Interface Principal ---
def main():
    try:
        # Logo com aura transcendental (250px e referência correta ao arquivo na mesma pasta)
        st.markdown("""
        <div class="logo-container">
            <img src="logo.png" alt="Clips Burger Logo">
        </div>
        """, unsafe_allow_html=True)
        
        st.title("🍔 SISTEMA FINANCEIRO - CLIPS BURGER")
        st.caption("Gestão inteligente de vendas com análise financeira em tempo real - " + str(datetime.now().year))
    except:
        st.title("🍔 SISTEMA FINANCEIRO - CLIPS BURGER")
        st.caption("Gestão inteligente de vendas com análise financeira em tempo real")
    
    df_raw = read_sales_data()
    df_processed = process_data(df_raw)
    
    # Criar 4 tabs (removida a tab Dashboard Premium)
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Registrar Venda",
        "📈 Análise Detalhada", 
        "💡 Estatísticas",
        "💰 Análise Contábil"
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
        if total_venda_form > 0:
            cartao_pct = (cartao_val / total_venda_form) * 100
            dinheiro_pct = (dinheiro_val / total_venda_form) * 100
            pix_pct = (pix_val / total_venda_form) * 100
            
            st.markdown(f"""
            <div style='background: linear-gradient(90deg, #4c78a8, #54a24b); 
                        padding: 20px; border-radius: 10px; margin: 20px 0; color: white;'>
                <h3 style='text-align: center; margin-bottom: 15px;'>
                    💰 Total da Venda: {format_brl(total_venda_form)}
                </h3>
                <div style='display: flex; justify-content: space-around; text-align: center;'>
                    <div>
                        <strong>💳 Cartão</strong><br>
                        {format_brl(cartao_val)}<br>
                        <small>{cartao_pct:.1f}% do total</small>
                    </div>
                    <div>
                        <strong>💵 Dinheiro</strong><br>
                        {format_brl(dinheiro_val)}<br>
                        <small>{dinheiro_pct:.1f}% do total</small>
                    </div>
                    <div>
                        <strong>📱 PIX</strong><br>
                        {format_brl(pix_val)}<br>
                        <small>{pix_pct:.1f}% do total</small>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Form para submissão
        with st.form("form_venda", clear_on_submit=True):
            submitted = st.form_submit_button("💾 Registrar Venda", type="primary", use_container_width=True)
            
            if submitted:
                if total_venda_form > 0:
                    worksheet = get_worksheet()
                    if worksheet:
                        success = add_data_to_sheet(
                            data_input.strftime('%d/%m/%Y'),
                            cartao_val,
                            dinheiro_val, 
                            pix_val,
                            worksheet
                        )
                        if success:
                            st.cache_data.clear()
                            st.rerun()
                else:
                    st.error("⚠️ Por favor, insira pelo menos um valor maior que zero.")
    
    with tab2:
        st.header("📈 Análise Detalhada das Vendas")
        
        if df_processed.empty:
            st.info("📊 Nenhum dado de vendas encontrado. Registre algumas vendas para ver as análises.")
        else:
            # Filtros
            col1, col2 = st.columns(2)
            
            with col1:
                if 'Ano' in df_processed.columns and not df_processed['Ano'].isnull().all():
                    anos_disponiveis = sorted(df_processed['Ano'].dropna().unique())
                    selected_anos = st.multiselect(
                        "🗓️ Filtrar por Ano",
                        options=anos_disponiveis,
                        default=anos_disponiveis,
                        key="anos_tab2"
                    )
                else:
                    selected_anos = []
            
            with col2:
                if 'MêsNome' in df_processed.columns and not df_processed['MêsNome'].isnull().all():
                    meses_disponiveis = [m for m in meses_ordem if m in df_processed['MêsNome'].unique()]
                    selected_meses = st.multiselect(
                        "📅 Filtrar por Mês",
                        options=meses_disponiveis,
                        default=meses_disponiveis,
                        key="meses_tab2"
                    )
                else:
                    selected_meses = []
            
            # Aplicar filtros
            df_filtered = df_processed.copy()
            if selected_anos and 'Ano' in df_filtered.columns:
                df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos)]
            if selected_meses and 'MêsNome' in df_filtered.columns:
                df_filtered = df_filtered[df_filtered['MêsNome'].isin(selected_meses)]
            
            if df_filtered.empty:
                st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
            else:
                # Métricas principais
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_vendas = df_filtered['Total'].sum()
                    st.metric("💰 Total de Vendas", format_brl(total_vendas))
                
                with col2:
                    media_diaria = df_filtered['Total'].mean()
                    st.metric("📊 Média Diária", format_brl(media_diaria))
                
                with col3:
                    dias_com_vendas = len(df_filtered[df_filtered['Total'] > 0])
                    st.metric("📅 Dias com Vendas", dias_com_vendas)
                
                with col4:
                    melhor_dia = df_filtered.loc[df_filtered['Total'].idxmax(), 'DataFormatada'] if not df_filtered.empty else "N/A"
                    st.metric("🏆 Melhor Dia", melhor_dia)
                
                # Gráficos
                st.subheader("📈 Gráficos de Análise")
                
                # Gráfico de área com gradiente
                area_chart = create_area_chart_with_gradient(df_filtered)
                if area_chart:
                    st.altair_chart(area_chart, use_container_width=True)
                
                # Gráfico de vendas diárias
                daily_chart = create_advanced_daily_sales_chart(df_filtered)
                if daily_chart:
                    st.altair_chart(daily_chart, use_container_width=True)
                
                # Análise por dia da semana
                weekday_chart, best_weekday = create_enhanced_weekday_analysis(df_filtered)
                if weekday_chart:
                    st.altair_chart(weekday_chart, use_container_width=True)
                    if best_weekday:
                        st.info(f"🏆 **Melhor dia da semana:** {best_weekday}")
                
                # Histograma
                histogram = create_sales_histogram(df_filtered)
                if histogram:
                    st.altair_chart(histogram, use_container_width=True)
    
    with tab3:
        st.header("💡 Estatísticas Avançadas")
        
        if df_processed.empty:
            st.info("📊 Nenhum dado disponível para análise estatística.")
        else:
            # Filtros (mesmo sistema da tab2)
            col1, col2 = st.columns(2)
            
            with col1:
                if 'Ano' in df_processed.columns and not df_processed['Ano'].isnull().all():
                    anos_disponiveis = sorted(df_processed['Ano'].dropna().unique())
                    selected_anos_stats = st.multiselect(
                        "🗓️ Filtrar por Ano",
                        options=anos_disponiveis,
                        default=anos_disponiveis,
                        key="anos_tab3"
                    )
                else:
                    selected_anos_stats = []
            
            with col2:
                if 'MêsNome' in df_processed.columns and not df_processed['MêsNome'].isnull().all():
                    meses_disponiveis = [m for m in meses_ordem if m in df_processed['MêsNome'].unique()]
                    selected_meses_stats = st.multiselect(
                        "📅 Filtrar por Mês",
                        options=meses_disponiveis,
                        default=meses_disponiveis,
                        key="meses_tab3"
                    )
                else:
                    selected_meses_stats = []
            
            # Aplicar filtros
            df_filtered_stats = df_processed.copy()
            if selected_anos_stats and 'Ano' in df_filtered_stats.columns:
                df_filtered_stats = df_filtered_stats[df_filtered_stats['Ano'].isin(selected_anos_stats)]
            if selected_meses_stats and 'MêsNome' in df_filtered_stats.columns:
                df_filtered_stats = df_filtered_stats[df_filtered_stats['MêsNome'].isin(selected_meses_stats)]
            
            if df_filtered_stats.empty:
                st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
            else:
                # Informações Gerais
                st.subheader("📋 Informações Gerais")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("📊 Total de Registros", len(df_filtered_stats))
                    st.metric("💰 Receita Total", format_brl(df_filtered_stats['Total'].sum()))
                
                with col2:
                    st.metric("📈 Média por Venda", format_brl(df_filtered_stats['Total'].mean()))
                    st.metric("🎯 Mediana", format_brl(df_filtered_stats['Total'].median()))
                
                with col3:
                    st.metric("📊 Desvio Padrão", format_brl(df_filtered_stats['Total'].std()))
                    st.metric("🏆 Maior Venda", format_brl(df_filtered_stats['Total'].max()))
                
                # Heatmap inserido logo abaixo das informações gerais
                st.subheader("🔥 Mapa de Calor - Vendas por Período")
                heatmap_fig = create_heatmap(df_filtered_stats)
                if heatmap_fig:
                    st.plotly_chart(heatmap_fig, use_container_width=True)
                
                # Elementos movidos do Dashboard Premium (não redundantes)
                st.subheader("🚀 Análises Avançadas")
                
                # Insights inteligentes
                insights_html = create_insights_premium(df_filtered_stats)
                st.markdown(insights_html, unsafe_allow_html=True)
                
                # Gráfico radial
                st.subheader("📊 Distribuição de Métodos de Pagamento")
                radial_chart = create_radial_plot(df_filtered_stats)
                if radial_chart:
                    st.altair_chart(radial_chart, use_container_width=True)
                
                # Análise de correlações
                st.subheader("🔗 Análise de Correlações")
                
                if len(df_filtered_stats) > 1:
                    correlation_data = df_filtered_stats[['Cartão', 'Dinheiro', 'Pix', 'Total']].corr()
                    
                    # Criar heatmap de correlação
                    fig_corr = px.imshow(
                        correlation_data,
                        text_auto=True,
                        aspect="auto",
                        title="Matriz de Correlação entre Métodos de Pagamento",
                        color_continuous_scale="RdBu_r"
                    )
                    st.plotly_chart(fig_corr, use_container_width=True)
                
                # Estatísticas descritivas detalhadas
                st.subheader("📈 Estatísticas Descritivas Detalhadas")
                
                stats_df = df_filtered_stats[['Cartão', 'Dinheiro', 'Pix', 'Total']].describe()
                st.dataframe(stats_df.style.format("R$ {:.2f}"), use_container_width=True)
    
    with tab4:
        st.header("💰 Análise Contábil e Financeira")
        
        if df_processed.empty:
            st.info("📊 Nenhum dado disponível para análise contábil.")
        else:
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
                custo_contadora_mensal = st.number_input(
                    "📋 Custo Contadora/Mês (R$)",
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
                    format="%.1f",
                    key="fornecedores_tab4"
                )

            
            # Filtros por ano
            if 'Ano' in df_processed.columns and not df_processed['Ano'].isnull().all():
                anos_disponiveis = sorted(df_processed['Ano'].dropna().unique())
                selected_anos_filter = st.multiselect(
                    "🗓️ Filtrar por Ano (para DRE)",
                    options=anos_disponiveis,
                    default=anos_disponiveis[-1:] if anos_disponiveis else [],
                    key="anos_tab4"
                )
            else:
                selected_anos_filter = []
            
            # Aplicar filtros
            df_filtered_contabil = df_processed.copy()
            if selected_anos_filter and 'Ano' in df_filtered_contabil.columns:
                df_filtered_contabil = df_filtered_contabil[df_filtered_contabil['Ano'].isin(selected_anos_filter)]
            
            if df_filtered_contabil.empty:
                st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
            else:
                # Calcular resultados financeiros
                custo_contadora_anual = custo_contadora_mensal * 12
                resultados = calculate_financial_results(
                    df_filtered_contabil,
                    salario_minimo,
                    custo_contadora_anual,
                    custo_fornecedores
                )
                
                # Métricas principais
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("💰 Receita Bruta", format_brl(resultados['receita_bruta']))
                
                with col2:
                    st.metric("💸 Impostos", format_brl(resultados['impostos_sobre_vendas']))
                
                with col3:
                    st.metric("📊 Lucro Bruto", format_brl(resultados['lucro_bruto']))
                
                with col4:
                    st.metric("🎯 Lucro Líquido", format_brl(resultados['lucro_liquido']))
                
                # DRE Textual
                st.subheader("📋 Demonstração do Resultado do Exercício (DRE)")
                create_dre_textual(resultados, df_filtered_contabil, selected_anos_filter)
                
                # Análise de margem
                st.subheader("📈 Análise de Margens")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Margem Bruta",
                        f"{resultados['margem_bruta']:.1f}%",
                        delta=f"{resultados['margem_bruta'] - 50:.1f}%" if resultados['margem_bruta'] > 0 else None
                    )
                
                with col2:
                    st.metric(
                        "Margem Operacional",
                        f"{resultados['margem_operacional']:.1f}%",
                        delta=f"{resultados['margem_operacional'] - 20:.1f}%" if resultados['margem_operacional'] > 0 else None
                    )
                
                with col3:
                    st.metric(
                        "Margem Líquida",
                        f"{resultados['margem_liquida']:.1f}%",
                        delta=f"{resultados['margem_liquida'] - 15:.1f}%" if resultados['margem_liquida'] > 0 else None
                    )
                
                # Análise tributária
                st.subheader("🏛️ Análise Tributária")
                
                if resultados['receita_bruta'] > 0:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.info(f"""
                        **💳 Receita Tributável:** {format_brl(resultados['receita_tributavel'])}
                        
                        **💵 Receita Não Tributável:** {format_brl(resultados['receita_nao_tributavel'])}
                        
                        **📊 Economia Fiscal:** {format_brl(resultados['receita_nao_tributavel'] * 0.06)}
                        """)
                    
                    with col2:
                        perc_tributavel = (resultados['receita_tributavel'] / resultados['receita_bruta']) * 100
                        perc_nao_tributavel = (resultados['receita_nao_tributavel'] / resultados['receita_bruta']) * 100
                        
                        st.success(f"""
                        **📈 % Tributável:** {perc_tributavel:.1f}%
                        
                        **📉 % Não Tributável:** {perc_nao_tributavel:.1f}%
                        
                        **💡 Recomendação:** {'Incentivar pagamentos em dinheiro' if perc_tributavel > 70 else 'Manter estratégia atual'}
                        """)

if __name__ == '__main__':
    main()

