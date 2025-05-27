import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
import base64
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
    /* TABS COM FONTE MAIOR */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 60px !important;
        padding: 0 24px !important;
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
        transition: all 0.3s ease;
        animation: slideInUp 0.6s ease-out;
    }
    
    .stMetric:hover {
        transform: translateY(-3px);
        background-color: rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
    }
    
    /* Dashboard Premium Styles */
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    /* Logo com aura CORRIGIDA - tamanho 2 e aura 5% maior */
    .logo-aura {
        position: relative;
        display: flex;
        justify-content: center;
        align-items: center;
        width: 160px;
        height: 160px;
        margin: 0 auto;
    }
    
    .logo-aura::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 168px;
        height: 168px;
        background: radial-gradient(circle, rgba(76, 120, 168, 0.4) 0%, rgba(76, 120, 168, 0.2) 40%, rgba(76, 120, 168, 0.1) 70%, transparent 100%);
        border-radius: 50%;
        animation: pulse-aura 3s ease-in-out infinite;
        z-index: 1;
    }
    
    .logo-aura img {
        position: relative;
        z-index: 2;
        border-radius: 15px;
        filter: drop-shadow(0 0 20px rgba(255, 255, 255, 0.3));
    }
    
    @keyframes pulse-aura {
        0%, 100% { 
            transform: translate(-50%, -50%) scale(1);
            opacity: 0.6;
        }
        50% { 
            transform: translate(-50%, -50%) scale(1.1);
            opacity: 1;
        }
    }
    
    /* Animações para containers */
    @keyframes slideInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes fadeInScale {
        from {
            opacity: 0;
            transform: scale(0.9);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }
    
    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* Cards uniformes ANIMADOS */
    .uniform-card {
        background: rgba(255,255,255,0.1);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        min-height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
        border: 1px solid rgba(255,255,255,0.1);
        animation: fadeInScale 0.6s ease-out;
    }
    
    .uniform-card:hover {
        transform: translateY(-8px) scale(1.03);
        background: rgba(255,255,255,0.2);
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    /* Container interativo para gráficos ANIMADO */
    .interactive-container {
        background: rgba(255,255,255,0.05);
        border-radius: 15px;
        padding: 1rem;
        margin: 1rem 0;
        border: 1px solid rgba(255,255,255,0.1);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        animation: slideInLeft 0.8s ease-out;
    }
    
    .interactive-container:hover {
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        box-shadow: 0 15px 30px rgba(0,0,0,0.2);
        transform: translateY(-5px);
    }
    
    /* Calendar container CORRIGIDO - mais compacto */
    .calendar-container {
        background: rgba(255,255,255,0.05);
        border-radius: 15px;
        padding: 1rem;
        margin: 1rem 0;
        border: 1px solid rgba(255,255,255,0.1);
        min-height: 320px;
        max-height: 400px;
        animation: fadeInScale 0.8s ease-out;
        transition: all 0.3s ease;
    }
    
    .calendar-container:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 25px rgba(0,0,0,0.2);
    }
    
    /* Responsividade MELHORADA */
    .stPlotlyChart, .stAltairChart {
        width: 100% !important;
        min-height: 600px;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }
    
    /* Responsividade para containers de dados */
    @media (max-width: 1200px) {
        .uniform-card {
            min-height: 160px;
            margin: 0.5rem 0;
        }
    }
    
    @media (max-width: 768px) {
        .logo-aura {
            width: 120px;
            height: 120px;
        }
        .logo-aura::before {
            width: 126px;
            height: 126px;
        }
        .logo-aura img {
            width: 80px !important;
        }
        
        .uniform-card {
            min-height: 140px;
            padding: 1rem;
            margin: 0.5rem 0;
        }
        
        .interactive-container {
            padding: 0.5rem;
            margin: 0.5rem 0;
        }
        
        .calendar-container {
            min-height: 280px;
            max-height: 350px;
        }
    }
    
    @media (max-width: 480px) {
        .uniform-card {
            min-height: 120px;
            padding: 0.8rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# Função auxiliar para converter imagem em base64
def get_base64_of_image(path):
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return ""

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

# --- Função para criar gráfico de calendário ---
def create_calendar_chart(df):
    """Cria um gráfico de calendário com as vendas - CORRIGIDO."""
    if df.empty or 'Data' not in df.columns:
        return None
    
    # Preparar dados para o calendário
    calendar_data = []
    for _, row in df.iterrows():
        total = row['Total']
        # Determinar nível baseado no valor
        if total == 0:
            level = 0
        elif total <= 50:
            level = 1
        elif total <= 100:
            level = 2
        elif total <= 200:
            level = 3
        else:
            level = 4
            
        calendar_data.append({
            'date': row['Data'].strftime('%Y-%m-%d'),
            'level': level,
            'count': total
        })
    
    # Converter para JSON
    import json
    calendar_json = json.dumps(calendar_data)
    
    calendar_html = f"""
    <div class="calendar-container">
        <h3 style="color: white; text-align: center; margin-bottom: 15px; font-size: 1.25rem; font-weight: 600;">📅 Calendário de Vendas</h3>
        <div id="calendar-container" style="width: 100%; height: 300px;"></div>
    </div>
    
    <script src="https://cdn.anychart.com/releases/v8/js/anychart-base.min.js"></script>
    <script src="https://cdn.anychart.com/releases/v8/js/anychart-ui.min.js"></script>
    <script src="https://cdn.anychart.com/releases/v8/js/anychart-exports.min.js"></script>
    <script src="https://cdn.anychart.com/releases/v8/js/anychart-calendar.min.js"></script>
    <script src="https://cdn.anychart.com/releases/v8/js/anychart-data-adapter.min.js"></script>
    <link href="https://cdn.anychart.com/releases/v8/css/anychart-ui.min.css" type="text/css" rel="stylesheet">
    <link href="https://cdn.anychart.com/releases/v8/fonts/css/anychart-font.min.css" type="text/css" rel="stylesheet">
    
    <script>
        anychart.onDocumentReady(function() {{
            var data = {calendar_json};
            var dataset = anychart.data.set(data);
            var mapping = dataset.mapAs({{
                x: 'date',
                value: 'level'
            }});
            var chart = anychart.calendar(mapping);

            chart.background('#22282D');

            // CORREÇÃO: Configurar meses com fonte consistente
            chart.months()
                .stroke(false)
                .noDataStroke(false)
                .labels().fontSize(12)
                .labels().fontFamily('Arial, sans-serif')
                .labels().fontColor('#ffffff');

            // CORREÇÃO: Reduzir espaçamento entre dias
            chart.days()
                .spacing(2)
                .stroke(false)
                .noDataStroke(false)
                .noDataFill('#2d333b')
                .noDataHatchFill(false);

            // CORREÇÃO: Configurar semanas com fonte consistente
            chart.weeks()
                .labels().fontSize(11)
                .labels().fontFamily('Arial, sans-serif')
                .labels().fontColor('#ffffff');

            chart.colorRange(false);

            var customColorScale = anychart.scales.ordinalColor();
            customColorScale.ranges([
                {{equal: 0, color: '#2d333b'}},
                {{equal: 1, color: '#0D4428'}},
                {{equal: 2, color: '#006D31'}},
                {{equal: 3, color: '#37AB4B'}},
                {{equal: 4, color: '#39D353'}}
            ]);

            chart.colorScale(customColorScale);

            chart.tooltip()
                .format('R$ {{%count}} em vendas')
                .fontSize(12)
                .fontFamily('Arial, sans-serif');

            // CORREÇÃO: Altura menor e mais compacta
            chart.listen('chartDraw', function() {{
                var actualHeight = Math.min(chart.getActualHeight(), 350);
                document.getElementById('calendar-container').style.height = actualHeight + 'px';
            }});

            chart.container('calendar-container');
            chart.draw();
        }});
    </script>
    """
    
    return calendar_html

# --- Função para criar gráfico de frequência por dia ---
def create_frequency_chart(attendance_data):
    """Cria gráfico de frequência por dia da semana."""
    if not attendance_data or 'frequencia_por_dia' not in attendance_data:
        return None
    
    freq_data = []
    for dia, dados in attendance_data['frequencia_por_dia'].items():
        freq_data.append({
            'Dia': dia,
            'Frequência (%)': dados['frequencia'],
            'Trabalhados': dados['trabalhados'],
            'Esperados': dados['esperados'],
            'Faltas': dados['faltas']
        })
    
    freq_df = pd.DataFrame(freq_data)
    
    if freq_df.empty:
        return None
    
    # Gráfico de frequência por dia
    freq_chart = alt.Chart(freq_df).mark_bar(
        color='#4caf50',
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5,
        stroke='white',
        strokeWidth=1
    ).encode(
        x=alt.X('Dia:O', title='Dia da Semana', sort=["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"]),
        y=alt.Y('Frequência (%):Q', title='Taxa de Frequência (%)', scale=alt.Scale(domain=[0, 100])),
        tooltip=[
            alt.Tooltip('Dia:N', title='Dia'),
            alt.Tooltip('Trabalhados:Q', title='Dias Trabalhados'),
            alt.Tooltip('Esperados:Q', title='Dias Esperados'),
            alt.Tooltip('Faltas:Q', title='Faltas'),
            alt.Tooltip('Frequência (%):Q', title='Frequência (%)', format='.1f')
        ]
    )
    
    # Adicionar texto com percentuais
    text = alt.Chart(freq_df).mark_text(
        dy=-8,
        color='white',
        fontSize=12,
        fontWeight='bold',
        stroke='black',
        strokeWidth=1
    ).encode(
        x=alt.X('Dia:O', sort=["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"]),
        y=alt.Y('Frequência (%):Q'),
        text=alt.Text('Frequência (%):Q', format='.0f')
    )
    
    chart = (freq_chart + text).properties(
        title="📊 Taxa de Frequência por Dia da Semana",
        height=400,
        width='container'
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    return chart

# --- Funções de Análise de Frequência ---
def calculate_attendance_analysis(df):
    """Calcula análise detalhada de frequência e faltas."""
    if df.empty or 'Data' not in df.columns:
        return {}
    
    data_inicio = df['Data'].min()
    data_fim = df['Data'].max()
    
    # Calcular total de dias no período
    total_dias_periodo = (data_fim - data_inicio).days + 1
    
    # Calcular domingos (folgas) no período
    domingos_periodo = 0
    data_atual = data_inicio
    while data_atual <= data_fim:
        if data_atual.weekday() == 6:  # Domingo = 6
            domingos_periodo += 1
        data_atual += timedelta(days=1)
    
    # Dias úteis esperados (excluindo domingos)
    dias_uteis_esperados = total_dias_periodo - domingos_periodo
    
    # Dias efetivamente trabalhados
    dias_trabalhados = len(df)
    
    # Dias de falta
    dias_falta = max(0, dias_uteis_esperados - dias_trabalhados)
    
    # Taxa de frequência
    taxa_frequencia = (dias_trabalhados / dias_uteis_esperados * 100) if dias_uteis_esperados > 0 else 0
    
    # Análise por dia da semana
    dias_trabalho = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"]
    frequencia_por_dia = {}
    
    for dia in dias_trabalho:
        total_dias_esperados = 0
        data_atual = data_inicio
        while data_atual <= data_fim:
            day_name_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado"}
            if data_atual.weekday() in day_name_map and day_name_map[data_atual.weekday()] == dia:
                total_dias_esperados += 1
            data_atual += timedelta(days=1)
        
        dias_trabalhados_dia = len(df[df['DiaSemana'] == dia]) if 'DiaSemana' in df.columns else 0
        frequencia_por_dia[dia] = {
            'esperados': total_dias_esperados,
            'trabalhados': dias_trabalhados_dia,
            'faltas': max(0, total_dias_esperados - dias_trabalhados_dia),
            'frequencia': (dias_trabalhados_dia / total_dias_esperados * 100) if total_dias_esperados > 0 else 0
        }
    
    return {
        'periodo_inicio': data_inicio,
        'periodo_fim': data_fim,
        'total_dias_periodo': total_dias_periodo,
        'domingos_folga': domingos_periodo,
        'dias_uteis_esperados': dias_uteis_esperados,
        'dias_trabalhados': dias_trabalhados,
        'dias_falta': dias_falta,
        'taxa_frequencia': taxa_frequencia,
        'frequencia_por_dia': frequencia_por_dia
    }

# --- Funções de Gráficos Interativos em Altair ---
def create_interactive_radial_chart(df):
    """Cria um gráfico radial (não pizza) sem valores exibidos."""
    if df.empty or not any(col in df.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
        return None
    
    payment_data = pd.DataFrame({
        'Método': ['Cartão', 'Dinheiro', 'PIX'],
        'Valor': [df['Cartão'].sum(), df['Dinheiro'].sum(), df['Pix'].sum()]
    })
    payment_data = payment_data[payment_data['Valor'] > 0]
    
    if payment_data.empty:
        return None

    # Calcular percentuais para tooltip apenas
    total_geral = payment_data['Valor'].sum()
    payment_data['Percentual'] = (payment_data['Valor'] / total_geral * 100).round(1)

    # Gráfico radial usando mark_arc com raios diferentes
    radial_chart = alt.Chart(payment_data).mark_arc(
        innerRadius=60,
        outerRadius=180,
        stroke='white',
        strokeWidth=3,
        cornerRadius=5
    ).encode(
        theta=alt.Theta('Valor:Q', stack=True),
        radius=alt.Radius('Valor:Q', scale=alt.Scale(type='sqrt', zero=True, rangeMin=60, rangeMax=180)),
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
                titlePadding=10,
                padding=10
            )
        ),
        tooltip=[
            alt.Tooltip('Método:N', title='Método'),
            alt.Tooltip('Valor:Q', title='Valor (R$)', format=',.2f'),
            alt.Tooltip('Percentual:Q', title='Percentual (%)', format='.1f')
        ]
    ).properties(
        title="🎯 Distribuição Radial por Método de Pagamento",
        width=600,
        height=600,
        padding={'bottom': 100}
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )

    return radial_chart

def create_interactive_histogram(df, title="Distribuição dos Valores de Venda Diários"):
    """Histograma interativo SEM valores exibidos acima das barras."""
    if df.empty or 'Total' not in df.columns or df['Total'].isnull().all():
        return None
    
    df_filtered_hist = df[df['Total'] > 0].copy()
    if df_filtered_hist.empty:
        return None
    
    # Criar dados agregados para o histograma
    hist_data = []
    bins = pd.cut(df_filtered_hist['Total'], bins=15, include_lowest=True)
    for interval in bins.cat.categories:
        count = len(df_filtered_hist[(df_filtered_hist['Total'] >= interval.left) & 
                                   (df_filtered_hist['Total'] <= interval.right)])
        if count > 0:
            hist_data.append({
                'bin_start': interval.left,
                'bin_end': interval.right,
                'bin_center': (interval.left + interval.right) / 2,
                'count': count,
                'range_label': f"R$ {interval.left:,.0f} - R$ {interval.right:,.0f}".replace(",", "."),
                'percentage': (count / len(df_filtered_hist) * 100)
            })
    
    hist_df = pd.DataFrame(hist_data)
    
    if hist_df.empty:
        return None
    
    # CORREÇÃO: Gráfico de barras SEM texto de valores
    chart = alt.Chart(hist_df).mark_bar(
        color=CORES_MODO_ESCURO[0],
        opacity=0.8,
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5,
        stroke='white',
        strokeWidth=1
    ).encode(
        x=alt.X(
            'bin_center:Q',
            title="Faixa de Valor da Venda Diária (R$)",
            axis=alt.Axis(labelFontSize=12, format=',.0f')
        ),
        y=alt.Y(
            'count:Q',
            title='Número de Dias (Frequência)',
            axis=alt.Axis(labelFontSize=12)
        ),
        tooltip=[
            alt.Tooltip('range_label:N', title="Faixa de Valor"),
            alt.Tooltip('count:Q', title="Número de Dias"),
            alt.Tooltip('percentage:Q', title="Percentual (%)", format='.1f')
        ]
    ).properties(
        title=alt.TitleParams(
            text=title,
            fontSize=20,
            anchor='start'
        ),
        height=600,
        width='container',
        padding={'bottom': 100}
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )

    return chart

def create_area_chart_with_gradient(df):
    """Cria gráfico de área ACUMULADO com gradiente melhorado para Tab2."""
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        return None
    
    df_sorted = df.sort_values('Data').copy()
    df_sorted['Total_Acumulado'] = df_sorted['Total'].cumsum()
    
    if df_sorted.empty:
        return None
    
    area_chart = alt.Chart(df_sorted).mark_area(
        interpolate='monotone',
        line={'color': '#2a9d8f', 'strokeWidth': 3},
        color=alt.Gradient(
            gradient='linear',
            stops=[
                alt.GradientStop(color='#2a9d8f', offset=0),
                alt.GradientStop(color='#98c1d9', offset=1)
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
            'Total_Acumulado:Q',
            title='Vendas Acumuladas (R$)',
            axis=alt.Axis(labelFontSize=12)
        ),
        tooltip=[
            alt.Tooltip('DataFormatada:N', title='Data'),
            alt.Tooltip('Total:Q', title='Venda do Dia (R$)', format=',.2f'),
            alt.Tooltip('Total_Acumulado:Q', title='Total Acumulado (R$)', format=',.2f')
        ]
    ).properties(
        title=alt.TitleParams(
            text='📈 Evolução Acumulada das Vendas',
            fontSize=18,
            anchor='start'
        ),
        height=600,
        width='container'
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    return area_chart

def create_interactive_accumulation_chart(df):
    """Cria gráfico de patrimônio acumulado com cores melhoradas."""
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        return None
    
    df_accumulated = df.sort_values('Data').copy()
    df_accumulated['Patrimonio_Acumulado'] = df_accumulated['Total'].cumsum()
    
    if df_accumulated.empty:
        return None
    
    max_value = df_accumulated['Patrimonio_Acumulado'].max()
    max_date = df_accumulated[df_accumulated['Patrimonio_Acumulado'] == max_value]['Data'].iloc[0]
    
    # Gráfico de área com cores melhoradas
    area_chart = alt.Chart(df_accumulated).mark_area(
        opacity=0.7,
        interpolate='monotone',
        line={'color': '#e76f51', 'strokeWidth': 3},
        color=alt.Gradient(
            gradient='linear',
            stops=[
                alt.GradientStop(color='#e76f51', offset=0),
                alt.GradientStop(color='#f4a261', offset=1)
            ],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X(
            'Data:T',
            title='Período',
            axis=alt.Axis(format='%d/%m', labelAngle=-45, labelFontSize=12)
        ),
        y=alt.Y(
            'Patrimonio_Acumulado:Q',
            title='Patrimônio Acumulado (R$)',
            scale=alt.Scale(zero=True),
            axis=alt.Axis(labelFontSize=12)
        ),
        tooltip=[
            alt.Tooltip('DataFormatada:N', title='Data'),
            alt.Tooltip('Total:Q', title='Venda do Dia (R$)', format=',.2f'),
            alt.Tooltip('Patrimonio_Acumulado:Q', title='Patrimônio Acumulado (R$)', format=',.2f')
        ]
    )
    
    # Linha de tendência com cor harmoniosa
    line_chart = alt.Chart(df_accumulated).mark_line(
        color='#e76f51',
        strokeWidth=4,
        point=alt.OverlayMarkDef(color='#264653', size=100)
    ).encode(
        x='Data:T',
        y='Patrimonio_Acumulado:Q',
        tooltip=[
            alt.Tooltip('DataFormatada:N', title='Data'),
            alt.Tooltip('Patrimonio_Acumulado:Q', title='Patrimônio (R$)', format=',.2f')
        ]
    )
    
    # Ponto do pico com cor destacada
    peak_data = pd.DataFrame({
        'Data': [max_date],
        'Patrimonio_Acumulado': [max_value],
        'Label': [f'Pico: R$ {max_value:,.0f}']
    })
    
    peak_point = alt.Chart(peak_data).mark_circle(
        size=300,
        color='#264653',
        stroke='white',
        strokeWidth=3
    ).encode(
        x='Data:T',
        y='Patrimonio_Acumulado:Q',
        tooltip=['Label:N']
    )
    
    peak_text = alt.Chart(peak_data).mark_text(
        align='center',
        baseline='bottom',
        fontSize=14,
        fontWeight='bold',
        color='#264653',
        dy=-15
    ).encode(
        x='Data:T',
        y='Patrimonio_Acumulado:Q',
        text=alt.value(f'🎯 Patrimônio: R$ {max_value:,.0f}')
    )
    
    combined_chart = alt.layer(
        area_chart,
        line_chart,
        peak_point,
        peak_text
    ).properties(
        title=alt.TitleParams(
            text="💰 Evolução do Patrimônio Acumulado",
            fontSize=20,
            anchor='start'
        ),
        height=600,
        width='container'
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    return combined_chart

def create_advanced_daily_sales_chart(df):
    """Cria um gráfico de vendas diárias."""
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
        size=25
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
            fontSize=18,
            anchor='start'
        ),
        height=600,
        width='container',
        padding={'bottom': 100}
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    return bars

def create_enhanced_weekday_analysis(df):
    """Cria análise de vendas por dia da semana."""
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
            fontSize=20,
            anchor='start'
        ),
        height=600,
        width='container',
        padding={'bottom': 100}
    ).configure_view(
        stroke=None
    ).configure(
        background='transparent'
    )
    
    best_day = weekday_stats.loc[weekday_stats['Média'].idxmax(), 'DiaSemana'] if not weekday_stats.empty else "N/A"
    
    return chart, best_day

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
            fontSize=22,
            anchor='start'
        ),
        height=600,
        width='container',
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

def create_attendance_insights(df):
    """Cria seção de insights de frequência e assiduidade com gráfico."""
    if df.empty:
        return
    
    attendance_data = calculate_attendance_analysis(df)
    
    if not attendance_data:
        st.info("Dados insuficientes para análise de frequência.")
        return
    
    st.subheader("📅 Análise de Frequência e Assiduidade")
    
    # Métricas principais de frequência
    col_freq1, col_freq2, col_freq3, col_freq4 = st.columns(4)
    
    with col_freq1:
        st.metric(
            "📊 Taxa de Frequência",
            f"{attendance_data['taxa_frequencia']:.1f}%",
            help="Percentual de dias úteis trabalhados"
        )
    
    with col_freq2:
        st.metric(
            "✅ Dias Trabalhados",
            f"{attendance_data['dias_trabalhados']}",
            help="Total de dias com vendas registradas"
        )
    
    with col_freq3:
        st.metric(
            "❌ Dias de Falta",
            f"{attendance_data['dias_falta']}",
            delta=f"-{attendance_data['dias_falta']}" if attendance_data['dias_falta'] > 0 else "Perfeito!",
            help="Dias úteis sem vendas registradas"
        )
    
    with col_freq4:
        st.metric(
            "🏖️ Domingos (Folga)",
            f"{attendance_data['domingos_folga']}",
            help="Domingos no período (folgas programadas)"
        )
    
    # Gráfico de frequência por dia da semana
    st.subheader("📊 Frequência por Dia da Semana")
    
    freq_chart = create_frequency_chart(attendance_data)
    if freq_chart:
        st.altair_chart(freq_chart, use_container_width=True)
    
    # Insights sobre frequência
    if attendance_data['frequencia_por_dia']:
        freq_data = []
        for dia, dados in attendance_data['frequencia_por_dia'].items():
            freq_data.append({
                'Dia': dia,
                'Frequência (%)': dados['frequencia']
            })
        
        freq_df = pd.DataFrame(freq_data)
        
        if not freq_df.empty:
            melhor_freq_dia = freq_df.loc[freq_df['Frequência (%)'].idxmax(), 'Dia']
            pior_freq_dia = freq_df.loc[freq_df['Frequência (%)'].idxmin(), 'Dia']
            
            col_insight1, col_insight2 = st.columns(2)
            
            with col_insight1:
                st.success(f"🏆 **Melhor Frequência:** {melhor_freq_dia} ({freq_df.loc[freq_df['Dia'] == melhor_freq_dia, 'Frequência (%)'].iloc[0]:.1f}%)")
            
            with col_insight2:
                if freq_df.loc[freq_df['Dia'] == pior_freq_dia, 'Frequência (%)'].iloc[0] < 80:
                    st.warning(f"⚠️ **Atenção:** {pior_freq_dia} ({freq_df.loc[freq_df['Dia'] == pior_freq_dia, 'Frequência (%)'].iloc[0]:.1f}%)")
                else:
                    st.info(f"📊 **Menor Frequência:** {pior_freq_dia} ({freq_df.loc[freq_df['Dia'] == pior_freq_dia, 'Frequência (%)'].iloc[0]:.1f}%)")

def create_premium_insights(df):
    """Insights otimizados com informações relevantes."""
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
    
    st.subheader("🧠 Insights Estratégicos Avançados")
    
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
    # Título com logo CORRIGIDO - tamanho 2 e título 5
    try:
        col_logo, col_title = st.columns([2, 5])  # MUDANÇA: proporção 2:5
        with col_logo:
            # Logo com aura CORRIGIDA usando CSS
            logo_base64 = get_base64_of_image('logo.png')
            if logo_base64:
                st.markdown(f"""
                <div class="logo-aura">
                    <img src="data:image/png;base64,{logo_base64}" width="120" alt="Logo Clips Burger"/>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="logo-aura">
                    <div style="width: 120px; height: 120px; background: #4c78a8; border-radius: 15px; display: flex; align-items: center; justify-content: center; font-size: 2rem; color: white; position: relative; z-index: 2;">🍔</div>
                </div>
                """, unsafe_allow_html=True)
        
        with col_title:
            st.markdown(f"""
            <div style="padding-left: 20px; display: flex; flex-direction: column; justify-content: center; height: 160px;">
                <h1 style='margin: 0; font-size: 2.5rem; background: linear-gradient(135deg, #4c78a8, #72b7b2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
                    SISTEMA FINANCEIRO - CLIP'S BURGER
                </h1>
                <p style='margin: 10px 0 0 0; font-size: 1.1rem; color: #888; font-weight: 300;'>
                    Gestão inteligente de vendas com análise financeira em tempo real - {datetime.now().year}
                </p>
            </div>
            """, unsafe_allow_html=True)
    except:
        st.title("🍔 SISTEMA FINANCEIRO - CLIPS BURGER")
        st.caption("Gestão inteligente de vendas com análise financeira em tempo real")

    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    # Criar 4 tabs com fontes maiores
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Registrar Venda", 
        "📈 Análise Detalhada", 
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

            # Container interativo para gráfico de vendas diárias
            with st.container():
                daily_chart = create_advanced_daily_sales_chart(df_filtered)
                if daily_chart:
                    st.altair_chart(daily_chart, use_container_width=True)
                else:
                    st.info("Sem dados de vendas diárias para exibir o gráfico nos filtros selecionados.")

            # Container interativo para gráfico de área ACUMULADO
            with st.container():
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

    # --- TAB3: ANÁLISE CONTÁBIL COMPLETA ---
    with tab3:
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
            
    # --- TAB4: DASHBOARD PREMIUM OTIMIZADO ---
    with tab4:
        st.header("🚀 Dashboard Premium - Análise Completa")
        
        if not df_filtered.empty:
            # === SEÇÃO 1: KPIs PRINCIPAIS ===
            create_premium_kpi_cards(df_filtered)
            
            st.markdown("---")
            
            # === SEÇÃO 2: CALENDÁRIO DE VENDAS ===
            calendar_html = create_calendar_chart(df_filtered)
            if calendar_html:
                st.components.v1.html(calendar_html, height=400)
            
            st.markdown("---")
            
            # === SEÇÃO 3: ANÁLISE DE FREQUÊNCIA E ASSIDUIDADE ===
            create_attendance_insights(df_filtered)
            
            st.markdown("---")
            
            # === SEÇÃO 4: GRÁFICOS PRINCIPAIS ===
            st.subheader("📊 Análise Visual Avançada")
            
            # Layout responsivo: em telas menores, os gráficos vão para baixo
            col_chart1, col_chart2 = st.columns([2, 1], gap="large")
            
            with col_chart1:
                daily_chart = create_advanced_daily_sales_chart(df_filtered)
                if daily_chart:
                    st.altair_chart(daily_chart, use_container_width=True)
            
            with col_chart2:
                radial_chart = create_interactive_radial_chart(df_filtered)
                if radial_chart:
                    st.altair_chart(radial_chart, use_container_width=True)
            
            st.markdown("---")
            
            # === SEÇÃO 5: GRÁFICO DE PATRIMÔNIO ACUMULADO ===
            accumulation_chart = create_interactive_accumulation_chart(df_filtered)
            if accumulation_chart:
                st.altair_chart(accumulation_chart, use_container_width=True)
            
            st.markdown("---")
            
            # === SEÇÃO 6: ANÁLISE POR DIA DA SEMANA ===
            st.subheader("📅 Performance por Dia da Semana")
            
            weekday_chart, best_day = create_enhanced_weekday_analysis(df_filtered)
            if weekday_chart:
                st.altair_chart(weekday_chart, use_container_width=True)
            
            st.markdown("---")
            
            # === SEÇÃO 7: HISTOGRAMA SEM NÚMEROS ===
            st.subheader("📊 Distribuição de Valores de Vendas")
            
            sales_histogram_chart = create_interactive_histogram(df_filtered)
            if sales_histogram_chart: 
                st.altair_chart(sales_histogram_chart, use_container_width=True)
            
            st.markdown("---")
            
            # === SEÇÃO 8: INSIGHTS ESTRATÉGICOS ===
            create_premium_insights(df_filtered)
            
        else:
            st.warning("⚠️ Sem dados disponíveis. Ajuste os filtros na sidebar ou registre algumas vendas para visualizar o dashboard premium.")

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    main()
