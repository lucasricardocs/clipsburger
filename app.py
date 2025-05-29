import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings
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

# CSS para melhorar a aparência e adicionar aura na logo
def inject_css():
    st.markdown("""
    <style>
        /* Estilo geral da aplicação */
        .stApp {
            background-color: #0e1117;
        }
        
        /* Container da logo com aura branca e azul celestial */
        .logo-container {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            margin: 20px 0;
        }
        
        .logo-with-aura {
            position: relative;
            display: inline-block;
            border-radius: 50%;
            padding: 10px;
            background: radial-gradient(circle at center, 
                        rgba(255, 255, 255, 0.3) 0%, 
                        rgba(135, 206, 250, 0.4) 30%, 
                        rgba(0, 191, 255, 0.3) 50%, 
                        rgba(173, 216, 230, 0.2) 70%, 
                        transparent 100%);
            box-shadow: 
                0 0 30px rgba(255, 255, 255, 0.6),
                0 0 60px rgba(135, 206, 250, 0.5),
                0 0 90px rgba(0, 191, 255, 0.3),
                inset 0 0 30px rgba(255, 255, 255, 0.1);
            animation: pulse-aura 3s ease-in-out infinite;
        }
        
        .logo-with-aura img {
            border-radius: 50%;
            display: block;
            max-width: 150px;
            height: auto;
        }
        
        @keyframes pulse-aura {
            0%, 100% {
                box-shadow: 
                    0 0 30px rgba(255, 255, 255, 0.6),
                    0 0 60px rgba(135, 206, 250, 0.5),
                    0 0 90px rgba(0, 191, 255, 0.3),
                    inset 0 0 30px rgba(255, 255, 255, 0.1);
            }
            50% {
                box-shadow: 
                    0 0 40px rgba(255, 255, 255, 0.8),
                    0 0 80px rgba(135, 206, 250, 0.7),
                    0 0 120px rgba(0, 191, 255, 0.5),
                    inset 0 0 40px rgba(255, 255, 255, 0.2);
            }
        }
        
        /* Estilo para métricas */
        [data-testid="metric-container"] {
            background: linear-gradient(145deg, #1e2329, #2d3748);
            border-radius: 10px;
            padding: 15px;
            border: 1px solid #4a5568;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        /* Estilo para gráficos */
        .js-plotly-plot {
            border-radius: 10px;
            background: #1a202c;
        }
        
        /* Estilo para sidebar */
        .css-1d391kg {
            background-color: #1a202c;
        }
        
        /* Títulos */
        h1, h2, h3 {
            color: #ffffff;
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

# --- Funções para os heatmaps ---
def criar_calendario_anual_espacamento_correto(df, ano):
    """Cria calendário anual com maior distância entre nomes dos dias e o gráfico"""
    
    # Criar range completo do ano
    dates_completo = pd.date_range(f'{ano}-01-01', f'{ano}-12-31', freq='D')
    
    # Criar DataFrame completo para o ano todo
    dados_ano_completo = []
    for date in dates_completo:
        if date in df['Data'].values:
            row = df[df['Data'] == date].iloc[0]
            dados_ano_completo.append({
                'Data': date,
                'Cartão': row['Cartão'],
                'Dinheiro': row['Dinheiro'],
                'Pix': row['Pix'],
                'Total_Vendas': row['Total']
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
        
        # Classificar valores nas 4 faixas
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
    
    # Criar matriz para heatmap
    max_semana = max(x_positions) + 1
    matriz_vendas = np.full((7, max_semana), 0.0)
    matriz_hover = np.full((7, max_semana), '', dtype=object)
    
    for x, y, valor, hover in zip(x_positions, y_positions, valores, hover_texts):
        if 0 <= y < 7 and 0 <= x < max_semana:
            matriz_vendas[y, x] = valor
            matriz_hover[y, x] = hover
    
    # Escala de cores com #161b22 para dias vazios
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
    
    # Calcular posições dos meses para labels
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

def criar_heatmap_vendas_mensais_espacamento_correto(df):
    """Função para criar heatmap mensal horizontal com espaçamento correto"""
    
    df_vendas = df[df['Total_Vendas'] > 0].copy()
    df_vendas['Mes'] = df_vendas['Data'].dt.month
    vendas_mensais = df_vendas.groupby('Mes').agg({
        'Total_Vendas': 'sum',
        'Cartão': 'sum',
        'Dinheiro': 'sum',
        'Pix': 'sum'
    }).reset_index()
    
    meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    vendas_mensais['Mes_Nome'] = vendas_mensais['Mes'].map(
        lambda x: meses_nomes[x-1] if x <= len(meses_nomes) else f'Mês {x}'
    )
    
    matriz_mensal = np.zeros((1, 12))
    matriz_hover_mensal = np.full((1, 12), '', dtype=object)
    
    for mes_idx in range(12):
        mes_num = mes_idx + 1
        mes_nome = meses_nomes[mes_idx]
        
        dados_mes = vendas_mensais[vendas_mensais['Mes'] == mes_num]
        
        if len(dados_mes) > 0:
            row = dados_mes.iloc[0]
            matriz_mensal[0, mes_idx] = row['Total_Vendas']
            
            hover_text = (f"📅 {mes_nome} 2025<br>"
                         f"💰 Total: R$ {row['Total_Vendas']:,.2f}<br>"
                         f"💳 Cartão: R$ {row['Cartão']:,.2f}<br>"
                         f"💵 Dinheiro: R$ {row['Dinheiro']:,.2f}<br>"
                         f"📱 Pix: R$ {row['Pix']:,.2f}")
        else:
            matriz_mensal[0, mes_idx] = 0
            hover_text = f"📅 {mes_nome} 2025<br>❌ Sem dados"
        
        matriz_hover_mensal[0, mes_idx] = hover_text
    
    fig = go.Figure(data=go.Heatmap(
        z=matriz_mensal,
        text=matriz_hover_mensal,
        hovertemplate='%{text}<extra></extra>',
        colorscale=[
            [0.0, '#161b22'],
            [0.001, '#39D353'],
            [0.25, '#37AB4B'],
            [0.5, '#006D31'],
            [1.0, '#0D4428']
        ],
        showscale=False,
        xgap=5,
        ygap=5,
    ))
    
    fig.update_layout(
        title='📊 Vendas Mensais 2025',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff', family="Arial"),
        xaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            tickmode='array',
            tickvals=list(range(12)),
            ticktext=meses_nomes,
            tickfont=dict(color='#ffffff', size=14),
            side='bottom'
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        height=250,
        width=1400,
        title_x=0.5,
        title_font=dict(size=18, color='#ffffff'),
        margin=dict(l=150, r=50, t=150, b=50)
    )
    
    return fig, vendas_mensais

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
    <div style="text-align: center; margin-bottom: 30px;">
        <h2 style="color: #4c78a8; margin-bottom: 5px;">CLIPS BURGER LTDA</h2>
        <h3 style="color: #ffffff; margin-bottom: 5px;">DEMONSTRAÇÃO DO RESULTADO DO EXERCÍCIO</h3>
        <h4 style="color: #ffffff; margin-bottom: 20px;">Exercício {ano_dre}</h4>
        <p style="color: #ffffff; font-size: 14px;">(Em R$)</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Corpo do DRE
    st.markdown(f"""
    <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; font-family: 'Courier New', monospace;">
        <table style="width: 100%; color: #ffffff; font-size: 14px;">
            <tr>
                <td style="padding: 5px 0; border-bottom: 1px solid #444;"><strong>RECEITA OPERACIONAL BRUTA</strong></td>
                <td style="text-align: right; padding: 5px 0; border-bottom: 1px solid #444;"><strong>{format_val(resultados_ano['receita_bruta'])}</strong></td>
                <td style="text-align: right; padding: 5px 0; border-bottom: 1px solid #444;"><strong>100,0%</strong></td>
            </tr>
            <tr>
                <td style="padding: 5px 0; padding-left: 20px;">Receita Tributável (Cartão + PIX)</td>
                <td style="text-align: right; padding: 5px 0;">{format_val(resultados_ano['receita_tributavel'])}</td>
                <td style="text-align: right; padding: 5px 0;">{calc_percent(resultados_ano['receita_tributavel'], resultados_ano['receita_bruta']):.1f}%</td>
            </tr>
            <tr>
                <td style="padding: 5px 0; padding-left: 20px;">Receita Não Tributável (Dinheiro)</td>
                <td style="text-align: right; padding: 5px 0;">{format_val(resultados_ano['receita_nao_tributavel'])}</td>
                <td style="text-align: right; padding: 5px 0;">{calc_percent(resultados_ano['receita_nao_tributavel'], resultados_ano['receita_bruta']):.1f}%</td>
            </tr>
            <tr>
                <td style="padding: 5px 0; border-bottom: 1px solid #444;"><strong>(-) IMPOSTOS SOBRE VENDAS</strong></td>
                <td style="text-align: right; padding: 5px 0; border-bottom: 1px solid #444;"><strong>({format_val(resultados_ano['impostos_sobre_vendas'])})</strong></td>
                <td style="text-align: right; padding: 5px 0; border-bottom: 1px solid #444;"><strong>({calc_percent(resultados_ano['impostos_sobre_vendas'], resultados_ano['receita_bruta']):.1f}%)</strong></td>
            </tr>
            <tr>
                <td style="padding: 5px 0; padding-left: 20px;">Simples Nacional (6% s/ receita tributável)</td>
                <td style="text-align: right; padding: 5px 0;">({format_val(resultados_ano['impostos_sobre_vendas'])})</td>
                <td style="text-align: right; padding: 5px 0;">({calc_percent(resultados_ano['impostos_sobre_vendas'], resultados_ano['receita_bruta']):.1f}%)</td>
            </tr>
            <tr style="background-color: #2d3748;">
                <td style="padding: 8px 0; border-bottom: 2px solid #4c78a8;"><strong>= RECEITA OPERACIONAL LÍQUIDA</strong></td>
                <td style="text-align: right; padding: 8px 0; border-bottom: 2px solid #4c78a8;"><strong>{format_val(resultados_ano['receita_liquida'])}</strong></td>
                <td style="text-align: right; padding: 8px 0; border-bottom: 2px solid #4c78a8;"><strong>{calc_percent(resultados_ano['receita_liquida'], resultados_ano['receita_bruta']):.1f}%</strong></td>
            </tr>
            <tr>
                <td style="padding: 5px 0; border-bottom: 1px solid #444;"><strong>(-) CUSTO DOS PRODUTOS VENDIDOS</strong></td>
                <td style="text-align: right; padding: 5px 0; border-bottom: 1px solid #444;"><strong>({format_val(resultados_ano['custo_produtos_vendidos'])})</strong></td>
                <td style="text-align: right; padding: 5px 0; border-bottom: 1px solid #444;"><strong>({calc_percent(resultados_ano['custo_produtos_vendidos'], resultados_ano['receita_bruta']):.1f}%)</strong></td>
            </tr>
            <tr style="background-color: #2d3748;">
                <td style="padding: 8px 0; border-bottom: 2px solid #54a24b;"><strong>= LUCRO BRUTO</strong></td>
                <td style="text-align: right; padding: 8px 0; border-bottom: 2px solid #54a24b;"><strong>{format_val(resultados_ano['lucro_bruto'])}</strong></td>
                <td style="text-align: right; padding: 8px 0; border-bottom: 2px solid #54a24b;"><strong>{calc_percent(resultados_ano['lucro_bruto'], resultados_ano['receita_bruta']):.1f}%</strong></td>
            </tr>
            <tr>
                <td style="padding: 5px 0; border-bottom: 1px solid #444;"><strong>(-) DESPESAS OPERACIONAIS</strong></td>
                <td style="text-align: right; padding: 5px 0; border-bottom: 1px solid #444;"><strong>({format_val(resultados_ano['total_despesas_operacionais'])})</strong></td>
                <td style="text-align: right; padding: 5px 0; border-bottom: 1px solid #444;"><strong>({calc_percent(resultados_ano['total_despesas_operacionais'], resultados_ano['receita_bruta']):.1f}%)</strong></td>
            </tr>
            <tr>
                <td style="padding: 5px 0; padding-left: 20px;">Despesas com Pessoal</td>
                <td style="text-align: right; padding: 5px 0;">({format_val(resultados_ano['despesas_com_pessoal'])})</td>
                <td style="text-align: right; padding: 5px 0;">({calc_percent(resultados_ano['despesas_com_pessoal'], resultados_ano['receita_bruta']):.1f}%)</td>
            </tr>
            <tr>
                <td style="padding: 5px 0; padding-left: 20px;">Despesas Contábeis</td>
                <td style="text-align: right; padding: 5px 0;">({format_val(resultados_ano['despesas_contabeis'])})</td>
                <td style="text-align: right; padding: 5px 0;">({calc_percent(resultados_ano['despesas_contabeis'], resultados_ano['receita_bruta']):.1f}%)</td>
            </tr>
            <tr style="background-color: #2d3748;">
                <td style="padding: 8px 0; border-bottom: 2px solid #f58518;"><strong>= LUCRO OPERACIONAL</strong></td>
                <td style="text-align: right; padding: 8px 0; border-bottom: 2px solid #f58518;"><strong>{format_val(resultados_ano['lucro_operacional'])}</strong></td>
                <td style="text-align: right; padding: 8px 0; border-bottom: 2px solid #f58518;"><strong>{calc_percent(resultados_ano['lucro_operacional'], resultados_ano['receita_bruta']):.1f}%</strong></td>
            </tr>
            <tr style="background-color: #1a5f1a;">
                <td style="padding: 10px 0; border-bottom: 3px solid #ffffff;"><strong>= LUCRO LÍQUIDO DO EXERCÍCIO</strong></td>
                <td style="text-align: right; padding: 10px 0; border-bottom: 3px solid #ffffff;"><strong>{format_val(resultados_ano['lucro_liquido'])}</strong></td>
                <td style="text-align: right; padding: 10px 0; border-bottom: 3px solid #ffffff;"><strong>{calc_percent(resultados_ano['lucro_liquido'], resultados_ano['receita_bruta']):.1f}%</strong></td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

def format_brl(value):
    """Formata valor em reais brasileiro."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_insights_text(df):
    """Gera insights automáticos baseados nos dados."""
    if df.empty:
        return "Sem dados suficientes para análise."
    
    try:
        # Análise de tendência das últimas duas semanas
        df_recent = df.sort_values('Data').tail(14)
        if len(df_recent) >= 7:
            primeira_semana = df_recent.head(7)['Total'].mean()
            segunda_semana = df_recent.tail(7)['Total'].mean()
            
            if segunda_semana > primeira_semana:
                tendencia = ((segunda_semana - primeira_semana) / primeira_semana) * 100
                tendencia_texto = "crescimento"
            else:
                tendencia = ((primeira_semana - segunda_semana) / primeira_semana) * 100
                tendencia_texto = "queda"
        else:
            tendencia = 0
            tendencia_texto = "estabilidade"
        
        # Método de pagamento mais usado
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
        <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                    padding: 25px; border-radius: 15px; color: white; 
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3);">
            <h3 style="text-align: center; margin-bottom: 20px; color: #ffffff;">
                📊 Insights Automáticos
            </h3>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
                    <h4 style="margin: 0 0 10px 0; color: #ffd700;">📈 Tendência</h4>
                    <p style="margin: 0; font-size: 14px;">
                        Suas vendas apresentam uma tendência de <strong>{tendencia_texto}</strong> 
                        de <strong>{abs(tendencia):.1f}%</strong> comparando as últimas duas semanas.
                    </p>
                </div>
                
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
                    <h4 style="margin: 0 0 10px 0; color: #ffd700;">💳 Método Preferido</h4>
                    <p style="margin: 0; font-size: 14px;">
                        O método <strong>{melhor_metodo}</strong> representa 
                        <strong>{percentual_melhor:.1f}%</strong> das vendas. 
                        Considere incentivar este meio de pagamento.
                    </p>
                </div>
                
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
                    <h4 style="margin: 0 0 10px 0; color: #ffd700;">🎯 Meta Sugerida</h4>
                    <p style="margin: 0; font-size: 14px;">
                        Com base na média atual de <strong>{format_brl(media_diaria)}</strong> por dia, 
                        uma meta de <strong>{format_brl(media_diaria * 1.15)}</strong> 
                        representaria um crescimento de 15%.
                    </p>
                </div>
            </div>
        </div>
        """
    except Exception as e:
        return f"Erro ao gerar insights: {e}"

# --- Interface Principal ---
try:
    # Logo com aura
    st.markdown("""
    <div class="logo-container">
        <div class="logo-with-aura">
            <img src="https://github.com/lucasricardocs/clips_dashboard/blob/d53268c2008d717071298d9d0bb32e73f584d514/logo.png?raw=true" alt="Clips Burger Logo">
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.title("🍔 SISTEMA FINANCEIRO - CLIPS BURGER")
    st.caption(f"Gestão inteligente de vendas com análise financeira em tempo real - {datetime.now().year}")
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
    # Calcular total em tempo real (fora do form)
    cartao_val = cartao_input if cartao_input is not None else 0.0
    dinheiro_val = dinheiro_input if dinheiro_input is not None else 0.0
    pix_val = pix_input if pix_input is not None else 0.0
    
    total_venda = cartao_val + dinheiro_val + pix_val
    st.markdown(f"**Total da Venda: R$ {total_venda:.2f}**")
    
    if st.button("Adicionar Venda"):
        if total_venda > 0:
            worksheet = get_worksheet()
            if add_data_to_sheet(data_input.strftime('%d/%m/%Y'), cartao_val, dinheiro_val, pix_val, worksheet):
                st.success("Venda adicionada com sucesso!")
                st.cache_data.clear()  # Limpa o cache para atualizar os dados
            else:
                st.error("Erro ao adicionar venda.")
        else:
            st.error("O total da venda deve ser maior que zero.")

with tab2:
    st.header("📈 Análise Detalhada")
    
    if not df_processed.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            radial_plot = create_radial_plot(df_processed)
            if radial_plot:
                st.altair_chart(radial_plot, use_container_width=True)
            else:
                st.info("Dados insuficientes para gráfico radial.")
        
        with col2:
            area_chart = create_area_chart_with_gradient(df_processed)
            if area_chart:
                st.altair_chart(area_chart, use_container_width=True)
            else:
                st.info("Dados insuficientes para gráfico de área.")
        
        st.markdown("---")
        
        daily_sales_chart = create_advanced_daily_sales_chart(df_processed)
        if daily_sales_chart:
            st.altair_chart(daily_sales_chart, use_container_width=True)
        else:
            st.info("Dados insuficientes para gráfico de vendas diárias.")
        
        weekday_analysis_chart, best_day = create_enhanced_weekday_analysis(df_processed)
        if weekday_analysis_chart:
            st.altair_chart(weekday_analysis_chart, use_container_width=True)
            if best_day:
                st.markdown(f"**🏆 Melhor dia da semana para vendas: {best_day}**")
        else:
            st.info("Dados insuficientes para análise por dia da semana.")
        
        sales_histogram = create_sales_histogram(df_processed)
        if sales_histogram:
            st.altair_chart(sales_histogram, use_container_width=True)
        else:
            st.info("Dados insuficientes para histograma de vendas.")
    
    else:
        st.warning("⚠️ Nenhum dado disponível para análise. Adicione algumas vendas primeiro.")

with tab3:
    st.header("💡 Estatísticas")
    
    if not df_processed.empty:
        insights_html = get_insights_text(df_processed)
        st.markdown(insights_html, unsafe_allow_html=True)
        
        # Estatísticas adicionais
        st.markdown("---")
        st.subheader("📊 Estatísticas Gerais")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_vendas = df_processed['Total'].sum()
            st.metric("💰 Total Geral", f"R$ {total_vendas:,.2f}")
        
        with col2:
            media_vendas = df_processed['Total'].mean()
            st.metric("📈 Média por Dia", f"R$ {media_vendas:,.2f}")
        
        with col3:
            maior_venda = df_processed['Total'].max()
            st.metric("🏆 Maior Venda", f"R$ {maior_venda:,.2f}")
        
        with col4:
            total_dias = len(df_processed[df_processed['Total'] > 0])
            st.metric("📅 Dias com Vendas", total_dias)
    
    else:
        st.warning("⚠️ Nenhum dado disponível para estatísticas. Adicione algumas vendas primeiro.")

with tab4:
    st.header("💰 Análise Contábil")
    
    if not df_processed.empty:
        # Parâmetros configuráveis
        st.subheader("⚙️ Configurações Financeiras")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            salario_minimo = st.number_input(
                "💼 Salário Mensal (R$)", 
                min_value=0.0, 
                value=1550.0, 
                format="%.2f",
                key="salario_tab4"
            )
        
        with col2:
            custo_contadora = st.number_input(
                "📊 Custo Contadora Mensal (R$)", 
                min_value=0.0, 
                value=316.0, 
                format="%.2f",
                key="contadora_tab4"
            )
        
        with col3:
            custo_fornecedores_percentual = st.number_input(
                "📦 Custo Fornecedores (%)", 
                min_value=0.0, 
                max_value=100.0, 
                value=30.0, 
                format="%.1f",
                key="fornecedores_tab4"
            )
        
        st.markdown("---")
        
        # Calcular resultados financeiros
        resultados = calculate_financial_results(
            df_processed, 
            salario_minimo, 
            custo_contadora * 12,  # Anualizar
            custo_fornecedores_percentual
        )
        
        # Exibir DRE
        anos_disponiveis = sorted(df_processed['Ano'].unique()) if 'Ano' in df_processed.columns else [datetime.now().year]
        create_dre_textual(resultados, df_processed, anos_disponiveis)
        
        # Métricas resumidas
        st.markdown("---")
        st.subheader("📈 Resumo Financeiro")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "💰 Receita Bruta", 
                f"R$ {resultados['receita_bruta']:,.2f}"
            )
        
        with col2:
            st.metric(
                "📊 Lucro Bruto", 
                f"R$ {resultados['lucro_bruto']:,.2f}",
                delta=f"{resultados['margem_bruta']:.1f}%"
            )
        
        with col3:
            st.metric(
                "🎯 Lucro Operacional", 
                f"R$ {resultados['lucro_operacional']:,.2f}",
                delta=f"{resultados['margem_operacional']:.1f}%"
            )
        
        with col4:
            st.metric(
                "✅ Lucro Líquido", 
                f"R$ {resultados['lucro_liquido']:,.2f}",
                delta=f"{resultados['margem_liquida']:.1f}%"
            )
    
    else:
        st.warning("⚠️ Nenhum dado disponível para análise contábil. Adicione algumas vendas primeiro.")

with tab5:
    st.header("🚀 Dashboard Premium")
    
    if not df_processed.empty:
        # Preparar dados para heatmap
        df_heatmap = df_processed.copy()
        
        # Criar os heatmaps
        st.markdown("## 📅 **Calendário de Vendas Anual**")
        st.markdown("Visualização estilo GitHub mostrando a intensidade das vendas ao longo do ano")
        
        try:
            fig_anual, df_completo = criar_calendario_anual_espacamento_correto(df_heatmap, datetime.now().year)
            st.plotly_chart(fig_anual, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao criar calendário anual: {e}")
            st.info("Verifique se há dados suficientes para o ano atual.")
        
        st.markdown("---")
        st.markdown("## 📊 **Resumo Mensal**")
        st.markdown("Visão consolidada das vendas por mês")
        
        try:
            fig_mensal, vendas_mensais = criar_heatmap_vendas_mensais_espacamento_correto(df_completo if 'df_completo' in locals() else df_heatmap)
            st.plotly_chart(fig_mensal, use_container_width=True)
            
            # Tabela de dados mensais
            if not vendas_mensais.empty:
                st.markdown("### 📋 Dados Mensais Detalhados")
                st.dataframe(
                    vendas_mensais.style.format({
                        'Total': 'R$ {:,.2f}',
                        'Cartão': 'R$ {:,.2f}',
                        'Dinheiro': 'R$ {:,.2f}',
                        'Pix': 'R$ {:,.2f}'
                    }),
                    use_container_width=True
                )
            else:
                st.info("Nenhum dado mensal disponível.")
        
        except Exception as e:
            st.error(f"Erro ao criar heatmap mensal: {e}")
            st.info("Verifique se há dados suficientes para análise mensal.")
        
        # Informações adicionais
        st.markdown("---")
        st.markdown("### ℹ️ **Legenda dos Heatmaps**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **Calendário Anual:**
            - 🟫 Sem vendas
            - 🟢 Vendas baixas (< R$ 1.500)
            - 🟢 Vendas médias (R$ 1.500 - R$ 2.500)
            - 🟢 Vendas altas (R$ 2.500 - R$ 3.000)
            - 🟢 Vendas muito altas (> R$ 3.000)
            """)
        
        with col2:
            st.markdown("""
            **Resumo Mensal:**
            - Intensidade da cor indica o volume de vendas
            - Hover para ver detalhes específicos
            - Dados consolidados por mês
            """)
    
    else:
        st.warning("⚠️ Nenhum dado disponível para o Dashboard Premium. Adicione algumas vendas primeiro.")
        
        # Mostrar exemplo do que seria exibido
        st.markdown("### 🎯 **Prévia do Dashboard Premium**")
        st.info("""
        Quando você adicionar dados de vendas, este dashboard mostrará:
        
        📅 **Calendário Anual**: Visualização estilo GitHub com a intensidade das vendas por dia
        
        📊 **Heatmap Mensal**: Resumo consolidado das vendas por mês
        
        📋 **Tabelas Detalhadas**: Dados organizados e formatados
        
        🎨 **Gráficos Interativos**: Hover para ver detalhes específicos
        """)

# Rodapé informativo
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 20px; color: #666;">
    <p>🍔 <strong>Clips Burger - Sistema Financeiro</strong> | Desenvolvido com ❤️ usando Streamlit</p>
    <p>📊 Dashboard integrado com Google Sheets | 🔄 Atualização em tempo real</p>
</div>
""", unsafe_allow_html=True)

