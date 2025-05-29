import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
import plotly.graph_objects as go
import datetime
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

# CSS para melhorar a aparência com aura na logo e logo maior
def inject_css():
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #2196f3, #fff);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
    }
    
    .logo-with-aura {
        filter: drop-shadow(0 0 20px white) drop-shadow(0 0 40px #2196f3);
        width: 250px !important;
        height: auto;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #1e3c72, #2a5298);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin: 10px 0;
    }
    
    .footer-creative {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(90deg, #fff, #2196f3 80%);
        color: #222;
        text-align: center;
        padding: 15px 0;
        z-index: 999;
        border-top: 2px solid #2196f3;
        box-shadow: 0 -2px 10px rgba(33,150,243,0.2);
    }
    
    .footer-creative a {
        color: #1565c0;
        text-decoration: none;
        font-weight: bold;
        margin: 0 15px;
    }
    
    .footer-creative a:hover {
        color: #0d47a1;
    }
    
    .stApp > div:first-child {
        margin-bottom: 80px;
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

# --- Função do Heatmap (integrada do paste-2.txt) ---
def criar_calendario_anual_espacamento_correto(df, ano):
    """Cria calendário anual com heatmap de vendas"""
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    df_ano = df[df['Data'].dt.year == ano].copy()
    df_ano['Total_Vendas'] = df_ano['Cartão'] + df_ano['Dinheiro'] + df_ano['Pix']

    dates_completo = pd.date_range(f'{ano}-01-01', f'{ano}-12-31', freq='D')
    dados_ano_completo = []
    for date_ in dates_completo:
        row = df_ano[df_ano['Data'] == date_]
        if not row.empty:
            row = row.iloc[0]
            dados_ano_completo.append({
                'Data': date_,
                'Cartão': row['Cartão'],
                'Dinheiro': row['Dinheiro'],
                'Pix': row['Pix'],
                'Total_Vendas': row['Total_Vendas']
            })
        else:
            dados_ano_completo.append({
                'Data': date_,
                'Cartão': 0,
                'Dinheiro': 0,
                'Pix': 0,
                'Total_Vendas': 0
            })
    
    df_ano_completo = pd.DataFrame(dados_ano_completo)
    df_ano_completo['data_str'] = df_ano_completo['Data'].dt.strftime('%d/%m/%Y')
    df_ano_completo['dia_semana'] = df_ano_completo['Data'].dt.dayofweek

    primeiro_dia = datetime.date(ano, 1, 1)
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
                         f"💰 Total: R$ {row['Total_Vendas']:,.2f}<br>"
                         f"💳 Cartão: R$ {row['Cartão']:,.2f}<br>"
                         f"💵 Dinheiro: R$ {row['Dinheiro']:,.2f}<br>"
                         f"📱 Pix: R$ {row['Pix']:,.2f}")
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
        primeiro_dia_mes = datetime.date(ano, mes, 1)
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
            ticklabelstandoff=5
        ),
        height=500,
        width=1400,
        title_x=0.5,
        title_font=dict(size=18, color='#ffffff'),
        margin=dict(l=150, r=50, t=150, b=50)
    )

    return fig, df_ano_completo

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
    """Cria gráfico de área com gradiente - evolução acumulativa nas vendas."""
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        return None

    df_sorted = df.sort_values('Data').copy()
    # Calcula a soma acumulada DENTRO dos dados filtrados (mês/ano selecionado)
    df_sorted['Total_Acumulado'] = df_sorted['Total'].cumsum()
    
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
            "Total_Acumulado:Q",
            title="Vendas Acumuladas no Período (R$)",
            axis=alt.Axis(labelFontSize=12)
        ),
        tooltip=[
            alt.Tooltip("DataFormatada:N", title="Data"),
            alt.Tooltip("Total:Q", title="Venda Diária (R$)", format=",.2f"),
            alt.Tooltip("Total_Acumulado:Q", title="Venda Acumulada (R$)", format=",.2f")
        ]
    ).properties(
        title=alt.TitleParams(
            text="Evolução Acumulada das Vendas no Período",
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
    st.markdown(f"""<div style="text-align: center; font-size: 20px; font-weight: bold; margin-bottom: 30px;">
    🍔 CLIPS BURGER - DRE SIMPLIFICADO<br>
    Exercício {ano_dre}<br>
    <span style="font-size: 14px; font-weight: normal;">Em R$</span>
    </div>""", unsafe_allow_html=True)

    # DRE principal
    st.markdown(f"""
    **RECEITA OPERACIONAL BRUTA**  
    {format_val(resultados_ano['receita_bruta'])}

    **(-) IMPOSTOS SOBRE VENDAS**  
    ({format_val(resultados_ano['impostos_sobre_vendas'])})

    **RECEITA OPERACIONAL LÍQUIDA**  
    {format_val(resultados_ano['receita_liquida'])} | {calc_percent(resultados_ano['receita_liquida'], resultados_ano['receita_liquida']):.1f}%

    **(-) CUSTO DOS PRODUTOS VENDIDOS**  
    ({format_val(resultados_ano['custo_produtos_vendidos'])})

    **LUCRO BRUTO**  
    {format_val(resultados_ano['lucro_bruto'])} | {resultados_ano['margem_bruta']:.1f}%

    **(-) DESPESAS OPERACIONAIS:**
    - Despesas com Pessoal: ({format_val(resultados_ano['despesas_com_pessoal'])})
    - Despesas Contábeis: ({format_val(resultados_ano['despesas_contabeis'])})

    **TOTAL DESPESAS OPERACIONAIS**  
    ({format_val(resultados_ano['total_despesas_operacionais'])})

    **LUCRO OPERACIONAL**  
    {format_val(resultados_ano['lucro_operacional'])} | {resultados_ano['margem_operacional']:.1f}%

    **LUCRO LÍQUIDO DO EXERCÍCIO**  
    **{format_val(resultados_ano['lucro_liquido'])}** | **{resultados_ano['margem_liquida']:.1f}%**
    """)

def format_brl(value):
    """Formata valores em Real brasileiro."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- Interface Principal ---
def show_logo_with_aura():
    """Exibe logo com aura branca e azul"""
    st.markdown("""
    <div class="logo-container">
        <div style="text-align: center;">
            <h1 style="
                font-size: 3em; 
                background: linear-gradient(45deg, #2196f3, #fff, #2196f3);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                filter: drop-shadow(0 0 20px white) drop-shadow(0 0 40px #2196f3);
                margin: 0;
            ">🍔 CLIPS BURGER</h1>
            <p style="color: #2196f3; font-size: 1.2em; margin-top: 10px;">
                Sistema Financeiro Inteligente
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def show_creative_footer():
    """Exibe rodapé criativo fixo"""
    st.markdown("""
    <div class="footer-creative">
        Feito com <span style="color:#2196f3; font-size:1.3em;">❤️</span> por <b>Clips Burger</b> &mdash; 
        Gestão inteligente de vendas &middot;
        <a href="mailto:contato@clipsburger.com">Contato</a> &middot;
        <a href="#">Política de Privacidade</a> &middot;
        <span style="color: #666;">&copy; 2025</span>
    </div>
    """, unsafe_allow_html=True)

# Exibir logo e rodapé
show_logo_with_aura()

# Ler e processar dados
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
    if total_venda_form > 0:
        cartao_pct = (cartao_val / total_venda_form) * 100
        dinheiro_pct = (dinheiro_val / total_venda_form) * 100
        pix_pct = (pix_val / total_venda_form) * 100
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e3c72, #2a5298); padding: 20px; border-radius: 10px; text-align: center; color: white; margin: 20px 0;">
            <h3>💰 Total da Venda: {format_brl(total_venda_form)}</h3>
            <div style="display: flex; justify-content: space-around; margin-top: 15px;">
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

    # Botão de registro
    if st.button("✅ Registrar Venda", type="primary", use_container_width=True):
        if total_venda_form > 0:
            worksheet = get_worksheet()
            if worksheet:
                data_str = data_input.strftime("%d/%m/%Y")
                success = add_data_to_sheet(data_str, cartao_val, dinheiro_val, pix_val, worksheet)
                if success:
                    st.cache_data.clear()
                    st.rerun()
        else:
            st.error("Por favor, insira pelo menos um valor de venda.")

with tab2:
    st.header("📈 Análise Detalhada de Vendas")
    
    if df_processed.empty:
        st.warning("Nenhum dado disponível para análise.")
    else:
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            anos_disponíveis = sorted(df_processed['Ano'].dropna().unique(), reverse=True)
            anos_selecionados = st.multiselect("🗓️ Selecione o(s) ano(s):", anos_disponíveis, default=anos_disponíveis[:1])
        
        with col2:
            if anos_selecionados:
                df_anos = df_processed[df_processed['Ano'].isin(anos_selecionados)]
                meses_disponíveis = sorted(df_anos['Mês'].dropna().unique())
                meses_selecionados = st.multiselect("📅 Selecione o(s) mês(es):", meses_disponíveis, default=meses_disponíveis)
            else:
                meses_selecionados = []

        # Aplicar filtros
        df_filtered = df_processed.copy()
        if anos_selecionados:
            df_filtered = df_filtered[df_filtered['Ano'].isin(anos_selecionados)]
        if meses_selecionados:
            df_filtered = df_filtered[df_filtered['Mês'].isin(meses_selecionados)]

        if df_filtered.empty:
            st.warning("Nenhum dado disponível para os filtros selecionados.")
        else:
            # Métricas principais
            total_vendas = df_filtered['Total'].sum()
            total_cartao = df_filtered['Cartão'].sum()
            total_dinheiro = df_filtered['Dinheiro'].sum()
            total_pix = df_filtered['Pix'].sum()
            media_diaria = df_filtered['Total'].mean()
            dias_com_venda = len(df_filtered[df_filtered['Total'] > 0])

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Total de Vendas", format_brl(total_vendas))
            col2.metric("📊 Média Diária", format_brl(media_diaria))
            col3.metric("📅 Dias com Vendas", dias_com_venda)
            col4.metric("🎯 Melhor Venda", format_brl(df_filtered['Total'].max()) if not df_filtered.empty else "R$ 0,00")

            # Gráficos
            st.subheader("📊 Evolução Acumulada das Vendas")
            area_chart = create_area_chart_with_gradient(df_filtered)
            if area_chart:
                st.altair_chart(area_chart, use_container_width=True)

            st.subheader("📈 Vendas Diárias por Método")
            daily_chart = create_advanced_daily_sales_chart(df_filtered)
            if daily_chart:
                st.altair_chart(daily_chart, use_container_width=True)

            st.subheader("🎯 Análise por Método de Pagamento")
            radial_chart = create_radial_plot(df_filtered)
            if radial_chart:
                st.altair_chart(radial_chart, use_container_width=True)

with tab3:
    st.header("💡 Estatísticas Avançadas")
    
    if df_processed.empty:
        st.warning("Nenhum dado disponível para estatísticas.")
    else:
        # Análise por dia da semana
        st.subheader("📅 Análise por Dia da Semana")
        weekday_chart, best_day = create_enhanced_weekday_analysis(df_processed)
        if weekday_chart:
            st.altair_chart(weekday_chart, use_container_width=True)
            if best_day:
                st.info(f"🎯 **Melhor dia da semana:** {best_day}")

        # Histograma de vendas
        st.subheader("📊 Distribuição dos Valores de Vendas")
        histogram = create_sales_histogram(df_processed)
        if histogram:
            st.altair_chart(histogram, use_container_width=True)

        # Análise de tendências
        if len(df_processed) >= 14:
            df_sorted = df_processed.sort_values('Data').copy()
            ultima_semana = df_sorted.tail(7)['Total'].sum()
            penultima_semana = df_sorted.iloc[-14:-7]['Total'].sum() if len(df_sorted) >= 14 else 0
            
            if penultima_semana > 0:
                tendencia = ((ultima_semana - penultima_semana) / penultima_semana) * 100
                tendencia_texto = "crescimento" if tendencia > 0 else "queda"
                
                # Análise de métodos de pagamento
                total_cartao = df_processed['Cartão'].sum()
                total_dinheiro = df_processed['Dinheiro'].sum()
                total_pix = df_processed['Pix'].sum()
                total_geral = total_cartao + total_dinheiro + total_pix
                
                if total_geral > 0:
                    pct_cartao = (total_cartao / total_geral) * 100
                    pct_dinheiro = (total_dinheiro / total_geral) * 100
                    pct_pix = (total_pix / total_geral) * 100
                    
                    metodos = [
                        ("Cartão", pct_cartao),
                        ("Dinheiro", pct_dinheiro),
                        ("PIX", pct_pix)
                    ]
                    melhor_metodo, percentual_melhor = max(metodos, key=lambda x: x[1])
                    
                    # Calcular média diária
                    media_diaria = df_processed['Total'].mean()
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 30px; border-radius: 15px; color: white; text-align: center; margin: 20px 0;">
                        <h3>🎯 Insights Principais</h3>
                        
                        <p style="font-size: 1.1em; margin: 15px 0;">
                        Suas vendas apresentam uma tendência de <strong>{tendencia_texto}</strong>
                        de <strong>{abs(tendencia):.1f}%</strong> comparando as últimas duas semanas.
                        </p>
                        
                        <p style="font-size: 1.1em; margin: 15px 0;">
                        O método <strong>{melhor_metodo}</strong> representa 
                        <strong>{percentual_melhor:.1f}%</strong> das vendas.
                        Considere incentivar este meio de pagamento.
                        </p>
                        
                        <p style="font-size: 1.1em; margin: 15px 0;">
                        Com base na média atual de <strong>{format_brl(media_diaria)}</strong> por dia,
                        uma meta de <strong>{format_brl(media_diaria * 1.15)}</strong>
                        representaria um crescimento de 15%.
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

with tab4:
    st.header("💰 Análise Contábil e DRE")
    
    if df_processed.empty:
        st.warning("Nenhum dado disponível para análise contábil.")
    else:
        # Configurações financeiras
        st.subheader("⚙️ Configurações Financeiras")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            salario_minimo = st.number_input(
                "💼 Salário Mínimo (R$)", 
                min_value=0.0, 
                value=1550.0, 
                format="%.2f",
                key="salario_tab4"
            )
        
        with col2:
            custo_contadora_mensal = st.number_input(
                "📊 Contadora (Mensal R$)", 
                min_value=0.0, 
                value=316.0, 
                format="%.2f",
                key="contadora_tab4"
            )
        
        with col3:
            custo_fornecedores_perc = st.number_input(
                "🏪 Fornecedores (%)", 
                min_value=0.0, 
                max_value=100.0, 
                value=30.0, 
                format="%.1f",
                key="fornecedores_tab4"
            )

        # Filtros para DRE
        anos_dre = sorted(df_processed['Ano'].dropna().unique(), reverse=True)
        ano_selecionado_dre = st.selectbox("📅 Ano para DRE:", anos_dre)
        
        df_dre = df_processed[df_processed['Ano'] == ano_selecionado_dre].copy()
        
        if not df_dre.empty:
            # Calcular resultados financeiros
            custo_contadora_anual = custo_contadora_mensal * 12
            resultados = calculate_financial_results(df_dre, salario_minimo, custo_contadora_anual, custo_fornecedores_perc)
            
            # Exibir DRE
            st.subheader(f"📋 DRE - Demonstração do Resultado do Exercício {ano_selecionado_dre}")
            create_dre_textual(resultados, df_dre, [ano_selecionado_dre])
            
            # Métricas resumidas
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Receita Bruta", format_brl(resultados['receita_bruta']))
            col2.metric("💵 Receita Líquida", format_brl(resultados['receita_liquida']))
            col3.metric("📈 Lucro Bruto", format_brl(resultados['lucro_bruto']))
            col4.metric("🎯 Lucro Líquido", format_brl(resultados['lucro_liquido']))

with tab5:
    st.header("🚀 Dashboard Premium - Calendário de Vendas")
    
    if df_processed.empty or df_processed['Data'].isnull().all():
        st.warning("Nenhum dado de vendas disponível para exibir o heatmap.")
    else:
        anos_disponiveis = sorted(df_processed['Data'].dt.year.unique(), reverse=True)
        ano_selecionado = st.selectbox("📅 Selecione o ano para visualizar o calendário de vendas:", anos_disponiveis)
        
        # Criar e exibir heatmap
        fig, df_ano_completo = criar_calendario_anual_espacamento_correto(df_processed, ano_selecionado)
        st.plotly_chart(fig, use_container_width=True)
        
        # Estatísticas do ano
        vendas_ano = df_ano_completo[df_ano_completo['Total_Vendas'] > 0]
        if not vendas_ano.empty:
            st.subheader(f"📊 Estatísticas do Ano {ano_selecionado}")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Total do Ano", format_brl(vendas_ano['Total_Vendas'].sum()))
            col2.metric("📅 Dias com Vendas", len(vendas_ano))
            col3.metric("📊 Média Diária", format_brl(vendas_ano['Total_Vendas'].mean()))
            col4.metric("🎯 Melhor Dia", format_brl(vendas_ano['Total_Vendas'].max()))

# Exibir rodapé criativo
show_creative_footer()
