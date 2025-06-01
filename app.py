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
st.set_page_config(page_title="Clips Burger", layout="wide", page_icon="🍔")

# Configuração de tema para gráficos mais bonitos
alt.data_transformers.enable('json')

# Paleta de cores otimizada para modo escuro
CORES_MODO_ESCURO = ['#4c78a8', '#54a24b', '#f58518', '#e45756', '#72b7b2', '#ff9da6', '#9d755d', '#bab0ac']

# Define a ordem correta dos dias da semana e meses
dias_semana_ordem = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# CSS para melhorar a aparência
def inject_css():
    # Base CSS styles
    base_css = """
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
    /* Estilos premium removidos */
    """
    
    # CSS da logo animada (integrado)
    fire_logo_css = """
    /* Logo Container com Efeito de Fogo */
    .logo-fire-container {
        position: relative;
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 2rem auto;
        height: 280px;
        width: 100%;
        max-width: 400px;
        overflow: visible;
    }

    /* Logo Principal */
    .fire-logo {
        position: relative;
        z-index: 10;
        max-width: 200px;
        width: auto;
        height: auto;
        object-fit: contain;
        filter: drop-shadow(0 0 20px rgba(255, 69, 0, 0.8));
        animation: logoFloat 3s ease-in-out infinite;
        display: block;
        margin: 0 auto;
    }

    /* Animação de Flutuação da Logo */
    @keyframes logoFloat {
        0%, 100% {
            transform: translateY(0px) scale(1);
            filter: drop-shadow(0 0 20px rgba(255, 69, 0, 0.8));
        }
        50% {
            transform: translateY(-10px) scale(1.05);
            filter: drop-shadow(0 0 30px rgba(255, 140, 0, 1));
        }
    }

    /* Container das Chamas */
    .fire-container {
        position: absolute;
        bottom: -30px;
        left: 50%;
        transform: translateX(-50%);
        width: 300px;
        height: 180px;
        z-index: 1;
        pointer-events: none;
    }

    /* Chamas Individuais */
    .flame {
        position: absolute;
        bottom: 0;
        border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
        transform-origin: center bottom;
        animation: flicker 0.5s ease-in-out infinite alternate;
    }

    /* Chama Principal (Vermelha) */
    .flame-red {
        left: 50%;
        transform: translateX(-50%);
        width: 80px;
        height: 120px;
        background: radial-gradient(circle, #ff4500 0%, #ff6347 30%, #dc143c 70%, #8b0000 100%);
        box-shadow: 0 0 30px #ff4500, 0 0 60px #ff6347, 0 0 90px #dc143c;
        animation: flicker 0.8s ease-in-out infinite alternate;
    }

    /* Chama Laranja */
    .flame-orange {
        left: 45%;
        transform: translateX(-50%);
        width: 60px;
        height: 90px;
        background: radial-gradient(circle, #ffa500 0%, #ff8c00 50%, #ff4500 100%);
        box-shadow: 0 0 25px #ffa500, 0 0 50px #ff8c00;
        animation: flicker 0.6s ease-in-out infinite alternate;
        animation-delay: 0.2s;
    }

    /* Chama Amarela */
    .flame-yellow {
        left: 55%;
        transform: translateX(-50%);
        width: 40px;
        height: 70px;
        background: radial-gradient(circle, #ffff00 0%, #ffd700 50%, #ffa500 100%);
        box-shadow: 0 0 20px #ffff00, 0 0 40px #ffd700;
        animation: flicker 0.4s ease-in-out infinite alternate;
        animation-delay: 0.4s;
    }

    /* Chama Branca (Centro) */
    .flame-white {
        left: 50%;
        transform: translateX(-50%);
        width: 25px;
        height: 50px;
        background: radial-gradient(circle, #ffffff 0%, #ffff99 50%, #ffd700 100%);
        box-shadow: 0 0 15px #ffffff, 0 0 30px #ffff99;
        animation: flicker 0.3s ease-in-out infinite alternate;
        animation-delay: 0.1s;
    }

    /* Partículas de Fogo */
    .fire-particle {
        position: absolute;
        border-radius: 50%;
        animation: particle-rise linear infinite;
        pointer-events: none;
    }

    .fire-particle.small {
        width: 3px;
        height: 3px;
        background: radial-gradient(circle, #ff6347 0%, #ff4500 100%);
        box-shadow: 0 0 6px #ff6347;
    }

    .fire-particle.medium {
        width: 5px;
        height: 5px;
        background: radial-gradient(circle, #ffa500 0%, #ff6347 100%);
        box-shadow: 0 0 8px #ffa500;
    }

    .fire-particle.large {
        width: 7px;
        height: 7px;
        background: radial-gradient(circle, #ffff00 0%, #ffa500 100%);
        box-shadow: 0 0 10px #ffff00;
    }

    .fire-particle:nth-child(5) { left: 15%; animation-delay: 0s; animation-duration: 2.5s; }
    .fire-particle:nth-child(6) { left: 25%; animation-delay: 0.3s; animation-duration: 2.2s; }
    .fire-particle:nth-child(7) { left: 35%; animation-delay: 0.6s; animation-duration: 2.8s; }
    .fire-particle:nth-child(8) { left: 45%; animation-delay: 0.9s; animation-duration: 2.0s; }
    .fire-particle:nth-child(9) { left: 55%; animation-delay: 1.2s; animation-duration: 2.6s; }
    .fire-particle:nth-child(10) { left: 65%; animation-delay: 1.5s; animation-duration: 2.3s; }
    .fire-particle:nth-child(11) { left: 75%; animation-delay: 1.8s; animation-duration: 2.7s; }
    .fire-particle:nth-child(12) { left: 85%; animation-delay: 2.1s; animation-duration: 2.1s; }
    .fire-particle:nth-child(13) { left: 20%; animation-delay: 0.4s; animation-duration: 2.4s; }
    .fire-particle:nth-child(14) { left: 30%; animation-delay: 0.7s; animation-duration: 2.9s; }
    .fire-particle:nth-child(15) { left: 40%; animation-delay: 1.0s; animation-duration: 2.2s; }
    .fire-particle:nth-child(16) { left: 50%; animation-delay: 1.3s; animation-duration: 2.5s; }
    .fire-particle:nth-child(17) { left: 60%; animation-delay: 1.6s; animation-duration: 2.8s; }
    .fire-particle:nth-child(18) { left: 70%; animation-delay: 1.9s; animation-duration: 2.1s; }
    .fire-particle:nth-child(19) { left: 80%; animation-delay: 2.2s; animation-duration: 2.6s; }

    /* Animações das Chamas */
    @keyframes flicker {
        0% {
            transform: translateX(-50%) rotate(-2deg) scaleY(1);
            opacity: 0.8;
        }
        25% {
            transform: translateX(-50%) rotate(1deg) scaleY(1.1);
            opacity: 0.9;
        }
        50% {
            transform: translateX(-50%) rotate(-1deg) scaleY(0.95);
            opacity: 1;
        }
        75% {
            transform: translateX(-50%) rotate(2deg) scaleY(1.05);
            opacity: 0.85;
        }
        100% {
            transform: translateX(-50%) rotate(-1deg) scaleY(1);
            opacity: 0.9;
        }
    }

    /* Animações das Partículas */
    @keyframes particle-rise {
        0% {
            bottom: 0;
            opacity: 1;
            transform: translateX(0) scale(1);
        }
        25% {
            opacity: 0.8;
            transform: translateX(5px) scale(1.1);
        }
        50% {
            opacity: 0.6;
            transform: translateX(-3px) scale(0.9);
        }
        75% {
            opacity: 0.3;
            transform: translateX(8px) scale(0.7);
        }
        100% {
            bottom: 200px;
            opacity: 0;
            transform: translateX(15px) scale(0.3);
        }
    }

    @keyframes particle-rise-alt {
        0% {
            bottom: 0;
            opacity: 1;
            transform: translateX(0) rotate(0deg) scale(1);
        }
        30% {
            opacity: 0.9;
            transform: translateX(-8px) rotate(45deg) scale(1.2);
        }
        60% {
            opacity: 0.5;
            transform: translateX(12px) rotate(90deg) scale(0.8);
        }
        100% {
            bottom: 180px;
            opacity: 0;
            transform: translateX(-5px) rotate(180deg) scale(0.2);
        }
    }

    .fire-particle:nth-child(even) {
        animation-name: particle-rise-alt;
    }

    /* Responsividade para logo */
    @media screen and (max-width: 768px) {
        .logo-fire-container {
            height: 240px;
            max-width: 350px;
        }
        
        .fire-logo {
            max-width: 180px;
        }
        
        .fire-container {
            width: 250px;
            height: 150px;
            bottom: -20px;
        }
    }

    @media screen and (max-width: 480px) {
        .logo-fire-container {
            height: 200px;
            max-width: 300px;
            margin: 1rem auto;
        }
        
        .fire-logo {
            max-width: 150px;
        }
        
        .fire-container {
            width: 200px;
            height: 120px;
            bottom: -15px;
        }
        
        .flame-red {
            width: 60px;
            height: 90px;
        }
        
        .flame-orange {
            width: 45px;
            height: 70px;
        }
        
        .flame-yellow {
            width: 30px;
            height: 50px;
        }
        
        .flame-white {
            width: 20px;
            height: 35px;
        }
    }
    """

    # Combine and inject CSS
    st.markdown(f"<style>{base_css}\n{fire_logo_css}</style>", unsafe_allow_html=True)

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
        # width=500, # Removido para usar use_container_width
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
        height=500,
        # width=1000, # Removido para usar use_container_width
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
        # width=1000, # Removido para usar use_container_width
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
        # width=1000, # Removido para usar use_container_width
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
        # width=1000, # Removido para usar use_container_width
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
    </div>
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
        # width=1000, # Removido para usar use_container_width
        padding={'bottom': 100}
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    return chart

# --- Funções premium removidas ---
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

    # DEBUG: Verificar colunas disponíveis
    print("Colunas disponíveis:", df.columns.tolist())

    # Determinar o ano atual ou mais recente dos dados
    current_year = df['Data'].dt.year.max()
    df = df[df['Data'].dt.year == current_year]

    if df.empty:
        st.info(f"Sem dados para o ano {current_year} para gerar o heatmap.")
        return None

    # Obter o dia da semana do primeiro dia do ano (0=segunda, 6=domingo)
    first_day_of_year = pd.Timestamp(f'{current_year}-01-01')
    first_day_weekday = first_day_of_year.weekday()  # 0=segunda, 6=domingo
    
    # Calcular quantos dias antes do 01/01 precisamos adicionar para começar na segunda-feira
    days_before = first_day_weekday  # Se 01/01 é quarta (2), precisamos de 2 dias antes
    
    # Criar range de datas começando na segunda-feira da semana do 01/01
    start_date = first_day_of_year - pd.Timedelta(days=days_before)
    end_date = datetime(current_year, 12, 31)
    
    # Garantir que terminamos no domingo da última semana
    days_after = 6 - end_date.weekday()  # Quantos dias faltam para chegar ao domingo
    if days_after < 6:  # Se não é domingo, adicionar dias
        end_date = end_date + pd.Timedelta(days=days_after)
    
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')

    # DataFrame com todas as datas (incluindo dias antes do 01/01)
    full_df = pd.DataFrame({'Data': all_dates})
    
    # Marcar quais datas são do ano atual
    full_df['is_current_year'] = full_df['Data'].dt.year == current_year
    
    # CORREÇÃO: Verificar e mapear nomes de colunas corretos
    # Possíveis variações do nome da coluna Cartão
    possible_cartao_names = ['Cartao', 'Cartão', 'cartao', 'cartão', 'CARTAO', 'CARTÃO']
    cartao_col = None
    for col_name in possible_cartao_names:
        if col_name in df.columns:
            cartao_col = col_name
            break
    
    # Possíveis variações do nome da coluna Dinheiro
    possible_dinheiro_names = ['Dinheiro', 'dinheiro', 'DINHEIRO']
    dinheiro_col = None
    for col_name in possible_dinheiro_names:
        if col_name in df.columns:
            dinheiro_col = col_name
            break
    
    # Possíveis variações do nome da coluna Pix
    possible_pix_names = ['Pix', 'PIX', 'pix']
    pix_col = None
    for col_name in possible_pix_names:
        if col_name in df.columns:
            pix_col = col_name
            break

    # Certificar que as colunas existem antes de mergear
    cols_to_merge = ['Data', 'Total']
    if cartao_col:
        cols_to_merge.append(cartao_col)
    if dinheiro_col:
        cols_to_merge.append(dinheiro_col)
    if pix_col:
        cols_to_merge.append(pix_col)
    
    cols_present = [col for col in cols_to_merge if col in df.columns]
    full_df = full_df.merge(df[cols_present], on='Data', how='left')
    
    # CORREÇÃO: Preencher NaNs e padronizar nomes das colunas
    # Garantir que as colunas existem com nomes padronizados
    if cartao_col and cartao_col in full_df.columns:
        full_df['Cartao'] = full_df[cartao_col].fillna(0)
    else:
        full_df['Cartao'] = 0
    
    if dinheiro_col and dinheiro_col in full_df.columns:
        full_df['Dinheiro'] = full_df[dinheiro_col].fillna(0)
    else:
        full_df['Dinheiro'] = 0
    
    if pix_col and pix_col in full_df.columns:
        full_df['Pix'] = full_df[pix_col].fillna(0)
    else:
        full_df['Pix'] = 0
    
    # Garantir que Total existe
    if 'Total' not in full_df.columns:
        full_df['Total'] = 0
    else:
        full_df['Total'] = full_df['Total'].fillna(0)
    
    # CORREÇÃO: Para dias que não são do ano atual, definir como None apenas para visualização
    full_df['display_total'] = full_df['Total'].copy()
    mask_not_current_year = ~full_df['is_current_year']
    full_df.loc[mask_not_current_year, 'display_total'] = None

    # Mapear os nomes dos dias (ordem fixa)
    full_df['day_of_week'] = full_df['Data'].dt.weekday  # 0=segunda, 6=domingo
    day_name_map = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
    full_df['day_display_name'] = full_df['day_of_week'].map(day_name_map)
    
    # Ordem fixa dos dias para exibição (sempre a mesma)
    day_display_names = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
    
    full_df['week'] = full_df['Data'].dt.isocalendar().week
    full_df['month'] = full_df['Data'].dt.month
    full_df['month_name'] = full_df['Data'].dt.strftime('%b')

    # Recalcular week baseado na primeira data (que agora é uma segunda-feira)
    full_df['week_corrected'] = ((full_df['Data'] - start_date).dt.days // 7)
    
    # DEBUG: Verificar se as colunas estão corretas
    print("Colunas no full_df:", full_df.columns.tolist())
    print("Amostra dos dados:")
    print(full_df[['Data', 'Total', 'Cartao', 'Dinheiro', 'Pix']].head())
    
    # Encontrar a primeira semana de cada mês para os rótulos (apenas para meses do ano atual)
    month_labels = full_df[full_df['is_current_year']].groupby('month').agg(
        week_corrected=('week_corrected', 'min'),
        month_name=('month_name', 'first')
    ).reset_index()

    # Labels dos meses
    months_chart = alt.Chart(month_labels).mark_text(
        align='center',
        baseline='bottom',
        fontSize=12,
        dy=-1,
        dx=-30,
        color='#A9A9A9'
    ).encode(
        x=alt.X('week_corrected:O', axis=None),
        text='month_name:N'
    )

    # CORREÇÃO: Construir tooltip dinamicamente baseado nas colunas disponíveis
    tooltip_fields = [
        alt.Tooltip('Data:T', title='Data', format='%d/%m/%Y'),
        alt.Tooltip('day_display_name:N', title='Dia'),
        alt.Tooltip('Total:Q', title='Total Vendas (R$)', format=',.2f')
    ]
    
    # Adicionar campos de pagamento apenas se existirem
    if 'Cartao' in full_df.columns:
        tooltip_fields.append(alt.Tooltip('Cartao:Q', title='Cartão (R$)', format=',.2f'))
    if 'Dinheiro' in full_df.columns:
        tooltip_fields.append(alt.Tooltip('Dinheiro:Q', title='Dinheiro (R$)', format=',.2f'))
    if 'Pix' in full_df.columns:
        tooltip_fields.append(alt.Tooltip('Pix:Q', title='Pix (R$)', format=',.2f'))

    # Gráfico principal (heatmap)
    heatmap = alt.Chart(full_df).mark_rect(
        stroke='#ffffff',
        strokeWidth=2,
        cornerRadius=0.5
    ).encode(
        x=alt.X('week_corrected:O',
                title=None, 
                axis=None),
        y=alt.Y('day_display_name:N', 
                sort=day_display_names,
                title=None,
                axis=alt.Axis(labelAngle=0, labelFontSize=12, ticks=False, domain=False, grid=False, labelColor='#A9A9A9')),
        color=alt.Color('display_total:Q',
            scale=alt.Scale(
                range=['#f0f0f0', '#9be9a8', '#40c463', '#30a14e', '#216e39'],
                type='threshold',
                domain=[0.01, 1500, 2500, 3500]
            ),
            legend=None),
        tooltip=tooltip_fields
    ).properties(
        height=250
    )

    # Combinar gráfico final
    final_chart = alt.vconcat(
        months_chart,
        heatmap,
        spacing=1
    ).configure_view(
        strokeWidth=0
    ).configure_concat(
        spacing=5
    ).properties(
        title=alt.TitleParams(
            text=f'Atividade de Vendas - {current_year}',
            fontSize=18,
            anchor='start',
            color='white',
            dy=-10
        )
    ).configure(
        background='transparent'
    )

    return final_chart

# Função para formatar valores em moeda brasileira
def format_brl(value):
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

# --- Interface Principal da Aplicação ---

# --- Interface Principal da Aplicação ---
def main():
    # Injetar CSS primeiro (CORREÇÃO 1)
    inject_css()

    # Carregar e processar dados (CORREÇÃO 2)
    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    # --- LOGO ANIMADA ---
    LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/clips_dashboard/main/logo.png"
    st.markdown(f"""
    <div class="logo-fire-container">
        <img src="{LOGO_URL}" class="fire-logo" alt="Clips Burger Logo">
        <div class="fire-container">
            <div class="flame flame-red"></div>
            <div class="flame flame-orange"></div>
            <div class="flame flame-yellow"></div>
            <div class="flame flame-white"></div>
            <!-- Partículas -->
            <div class="fire-particle small"></div>
            <div class="fire-particle medium"></div>
            <div class="fire-particle large"></div>
            <div class="fire-particle small"></div>
            <div class="fire-particle medium"></div>
            <div class="fire-particle large"></div>
            <div class="fire-particle small"></div>
            <div class="fire-particle medium"></div>
            <div class="fire-particle large"></div>
            <div class="fire-particle small"></div>
            <div class="fire-particle medium"></div>
            <div class="fire-particle large"></div>
            <div class="fire-particle small"></div>
            <div class="fire-particle medium"></div>
            <div class="fire-particle large"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Criar as tabs ANTES de usá-las (CORREÇÃO 3)
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Registrar Venda", 
        "🔎 Análise Detalhada", 
        "💡 Estatísticas e Tendências", 
        "📊 Análise Contábil"
    ])

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

                        # NOVA LÓGICA: Sempre priorizar o mês atual quando o ano atual está selecionado
                        default_meses_selecionados = []
                        ano_atual = datetime.now().year
                        mes_atual = datetime.now().month

                        if ano_atual in selected_anos_filter:
                            mes_atual_str = f"{mes_atual} - {meses_ordem[mes_atual-1]}"

                            # Adicionar mês atual mesmo sem dados
                            if mes_atual_str not in meses_opcoes_display:
                                meses_opcoes_display.append(mes_atual_str)
                                meses_opcoes_display = sorted(meses_opcoes_display, key=lambda x: int(x.split(" - ")[0]))

                            default_meses_selecionados = [mes_atual_str]
                        else:
                            default_meses_selecionados = meses_opcoes_display

                        selected_meses_str = st.multiselect(
                            "📆 Mês(es):", 
                            options=meses_opcoes_display, 
                            default=default_meses_selecionados,
                            help="💡 O mês atual é selecionado automaticamente. Você pode alterar conforme necessário."
                        )
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
if __name__ == "__main__":
    main()
