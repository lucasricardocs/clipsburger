import streamlit as st
import gspread
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import time

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
WORKSHEET_NAME = 'Vendas'

# Configuração da página Streamlit
st.set_page_config(
    page_title="Sistema Financeiro - Clips Burger", 
    layout="wide", 
    page_icon="🍔",
    initial_sidebar_state="expanded"
)

# Define a ordem correta dos dias da semana e meses
dias_semana_ordem = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# --- Detecção de Dispositivo Móvel ---
def detect_mobile_device():
    """Detecta se o usuário está em um dispositivo móvel"""
    try:
        # Tenta detectar através do user agent se disponível
        user_agent = st.context.headers.get("user-agent", "").lower()
        mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
        is_mobile_ua = any(keyword in user_agent for keyword in mobile_keywords)
        
        # Também permite configuração manual
        if 'mobile_override' in st.session_state:
            return st.session_state.mobile_override
        
        return is_mobile_ua
    except:
        # Fallback: usar configuração manual ou assumir desktop
        return st.session_state.get('mobile_override', False)

def is_mobile():
    """Função simplificada para verificar se é mobile"""
    return detect_mobile_device()

def apply_mobile_styles():
    """Aplica estilos CSS específicos para dispositivos móveis"""
    if is_mobile():
        st.markdown("""
        <style>
        /* Estilos para dispositivos móveis */
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 100%;
        }
        
        .stMetric {
            font-size: 0.8rem;
            background-color: #f0f2f6;
            padding: 0.5rem;
            border-radius: 0.5rem;
            margin: 0.2rem 0;
        }
        
        .stMetric > div {
            font-size: 0.9rem;
        }
        
        .stColumns {
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.2rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            font-size: 0.8rem;
            padding: 0.3rem 0.6rem;
        }
        
        .stDataFrame {
            font-size: 0.7rem;
        }
        
        .stPlotlyChart {
            height: 300px !important;
        }
        
        .stForm {
            border: 1px solid #e6e6e6;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 0.5rem 0;
        }
        
        .stNumberInput > div > div > input {
            font-size: 0.9rem;
        }
        
        .stSelectbox > div > div {
            font-size: 0.9rem;
        }
        
        /* Ajustar sidebar para mobile */
        .css-1d391kg {
            width: 100%;
            min-width: 100%;
        }
        
        /* Reduzir espaçamento entre elementos */
        .element-container {
            margin-bottom: 0.5rem;
        }
        
        /* Ajustar títulos para mobile */
        h1 {
            font-size: 1.5rem;
            line-height: 1.2;
        }
        
        h2 {
            font-size: 1.2rem;
            line-height: 1.1;
        }
        
        h3 {
            font-size: 1rem;
            line-height: 1.1;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        /* Estilos para desktop */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        
        .stMetric {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.8rem;
            border: 1px solid #e9ecef;
            margin: 0.5rem 0;
        }
        
        .stPlotlyChart {
            height: 600px !important;
        }
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
            st.error("Credenciais do Google ('google_credentials') não encontradas em st.secrets.")
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
        st.error(f"Erro ao converter valores: {ve}")
        return False
    except Exception as e:
        st.error(f"Erro ao adicionar dados: {e}")
        return False

@st.cache_data
def process_data(df_input):
    """Processa e prepara os dados de vendas para análise."""
    df = df_input.copy()
    
    if df.empty:
        return pd.DataFrame()

    for col in ['Cartão', 'Dinheiro', 'Pix']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0

    df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']

    if 'Data' in df.columns and not df['Data'].isnull().all():
        try:
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            df.dropna(subset=['Data'], inplace=True)

            if not df.empty:
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['MêsNome'] = df['Mês'].map(lambda x: meses_ordem[int(x)-1] if pd.notna(x) and 1 <= int(x) <= 12 else "Inválido")
                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                
                day_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
                df['DiaSemana'] = df['Data'].dt.dayofweek.map(day_map)
                df['DiaDoMes'] = df['Data'].dt.day
                
        except Exception as e:
            st.error(f"Erro ao processar datas: {e}")
            
    return df

# --- Funções de Gráficos Animados ---
def create_animated_sales_timeline(df):
    """Cria um gráfico animado da evolução das vendas ao longo do tempo"""
    if df.empty or 'Data' not in df.columns:
        return None
    
    df_anim = df.copy()
    df_anim['Data'] = pd.to_datetime(df_anim['Data'])
    df_anim = df_anim.sort_values('Data')
    
    df_anim['Total_Acumulado'] = df_anim['Total'].cumsum()
    df_anim['Dia_Sequencial'] = range(1, len(df_anim) + 1)
    df_anim['Data_Formatada'] = df_anim['Data'].dt.strftime('%d/%m/%Y')
    
    fig = px.line(
        df_anim,
        x='Dia_Sequencial',
        y='Total_Acumulado',
        animation_frame='Dia_Sequencial',
        title='🎬 Evolução Animada do Faturamento Acumulado',
        labels={
            'Dia_Sequencial': 'Dia de Operação',
            'Total_Acumulado': 'Faturamento Acumulado (R$)'
        },
        hover_data=['Data_Formatada', 'Total']
    )
    
    height = 400 if is_mobile() else 600
    
    fig.update_layout(
        height=height,
        showlegend=False,
        xaxis_title="Dia de Operação",
        yaxis_title="Faturamento Acumulado (R$)",
        font=dict(size=10 if is_mobile() else 12),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20) if is_mobile() else dict(l=40, r=40, t=60, b=40)
    )
    
    if 'updatemenus' in fig.layout and fig.layout.updatemenus:
        fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 200
        fig.layout.updatemenus[0].buttons[0].args[1]['transition']['duration'] = 100
    
    return fig

def create_animated_payment_race(df):
    """Cria um gráfico de corrida animado entre métodos de pagamento"""
    if df.empty or 'AnoMês' not in df.columns:
        return None
    
    df_monthly = df.groupby(['AnoMês'])[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
    df_monthly = df_monthly.sort_values('AnoMês')
    
    df_race = []
    for i, row in df_monthly.iterrows():
        for metodo in ['Cartão', 'Dinheiro', 'Pix']:
            df_race.append({
                'Mês': row['AnoMês'],
                'Método': metodo,
                'Valor': df_monthly.loc[:i, metodo].sum(),
                'Frame': i
            })
    
    df_race = pd.DataFrame(df_race)
    
    fig = px.bar(
        df_race,
        x='Valor',
        y='Método',
        animation_frame='Frame',
        orientation='h',
        title='🏁 Corrida dos Métodos de Pagamento',
        color='Método',
        color_discrete_map={
            'Cartão': '#1f77b4',
            'Dinheiro': '#2ca02c', 
            'Pix': '#ff7f0e'
        }
    )
    
    height = 400 if is_mobile() else 500
    
    fig.update_layout(
        height=height,
        font=dict(size=10 if is_mobile() else 12),
        margin=dict(l=20, r=20, t=40, b=20) if is_mobile() else dict(l=40, r=40, t=60, b=40)
    )
    
    return fig

def create_realtime_gauges(df):
    """Cria indicadores gauge em tempo real"""
    if df.empty:
        return None
    
    vendas_hoje = df[df['Data'] == datetime.now().date()]['Total'].sum()
    meta_diaria = 500
    media_mensal = df['Total'].mean()
    
    fig = make_subplots(
        rows=1, cols=3,
        specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]],
        subplot_titles=('Vendas Hoje', 'Meta Diária', 'Performance')
    )
    
    # Gauge 1: Vendas de hoje
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=vendas_hoje,
            title={'text': "Vendas Hoje (R$)"},
            gauge={
                'axis': {'range': [None, meta_diaria * 1.5]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, meta_diaria * 0.5], 'color': "lightgray"},
                    {'range': [meta_diaria * 0.5, meta_diaria], 'color': "gray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': meta_diaria
                }
            }
        ),
        row=1, col=1
    )
    
    # Gauge 2: Percentual da meta
    percentual_meta = (vendas_hoje / meta_diaria * 100) if meta_diaria > 0 else 0
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=percentual_meta,
            title={'text': "Meta (%)"},
            gauge={
                'axis': {'range': [None, 150]},
                'bar': {'color': "green"},
                'steps': [
                    {'range': [0, 50], 'color': "red"},
                    {'range': [50, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "lightgreen"},
                    {'range': [100, 150], 'color': "green"}
                ]
            }
        ),
        row=1, col=2
    )
    
    # Gauge 3: Performance vs média
    performance = (vendas_hoje / media_mensal * 100) if media_mensal > 0 else 0
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=performance,
            title={'text': "vs Média (%)"},
            gauge={
                'axis': {'range': [None, 200]},
                'bar': {'color': "purple"}
            }
        ),
        row=1, col=3
    )
    
    height = 300 if is_mobile() else 400
    
    fig.update_layout(
        height=height,
        title_text="🎯 Indicadores de Performance",
        title_x=0.5,
        font=dict(size=10 if is_mobile() else 12),
        margin=dict(l=10, r=10, t=40, b=10) if is_mobile() else dict(l=40, r=40, t=60, b=40)
    )
    
    return fig

# --- Funções de Cálculos Financeiros ---
def calculate_financial_results(df, salario_minimo, custo_contadora, custo_fornecedores_percentual):
    """Calcula os resultados financeiros com base nos dados de vendas."""
    results = {
        'faturamento_bruto': 0, 'faturamento_tributavel': 0, 'faturamento_nao_tributavel': 0,
        'imposto_simples': 0, 'custo_funcionario': 0, 'custo_contadora': custo_contadora,
        'custo_fornecedores_valor': 0, 'total_custos': 0,
        'lucro_bruto': 0, 'margem_lucro_bruto': 0, 'lucro_liquido': 0, 'margem_lucro_liquido': 0
    }
    
    if df.empty: 
        return results
    
    results['faturamento_bruto'] = df['Total'].sum()
    results['faturamento_tributavel'] = df['Cartão'].sum() + df['Pix'].sum()
    results['faturamento_nao_tributavel'] = df['Dinheiro'].sum()
    
    results['imposto_simples'] = results['faturamento_tributavel'] * 0.06
    results['custo_funcionario'] = salario_minimo * 1.55
    results['custo_fornecedores_valor'] = results['faturamento_bruto'] * (custo_fornecedores_percentual / 100)
    results['total_custos'] = results['imposto_simples'] + results['custo_funcionario'] + results['custo_contadora'] + results['custo_fornecedores_valor']
    
    results['lucro_bruto'] = results['faturamento_bruto'] - results['total_custos']
    results['lucro_liquido'] = results['faturamento_bruto'] - results['faturamento_tributavel']
    
    if results['faturamento_bruto'] > 0:
        results['margem_lucro_bruto'] = (results['lucro_bruto'] / results['faturamento_bruto']) * 100
        results['margem_lucro_liquido'] = (results['lucro_liquido'] / results['faturamento_bruto']) * 100
    
    return results

def format_brl(value):
    """Formata valores em moeda brasileira"""
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

# --- Interface Principal da Aplicação ---
def main():
    # Aplicar estilos responsivos
    apply_mobile_styles()
    
    # Controle manual de mobile (para testes)
    with st.sidebar:
        st.markdown("### 📱 Configurações de Dispositivo")
        mobile_override = st.checkbox(
            "Forçar modo mobile", 
            value=st.session_state.get('mobile_override', False),
            help="Ative para testar o layout mobile no desktop"
        )
        st.session_state.mobile_override = mobile_override
        
        if is_mobile():
            st.success("📱 Modo Mobile Ativo")
        else:
            st.info("🖥️ Modo Desktop Ativo")
    
    # Título responsivo
    if is_mobile():
        st.title("🍔 CLIPS BURGER")
        st.caption("Sistema Financeiro Mobile")
    else:
        try:
            col_logo, col_title = st.columns([2, 7])
            with col_logo:
                st.image('logo.png', width=300)
            with col_title:
                st.title("SISTEMA FINANCEIRO - CLIP'S BURGER")
                st.caption("Gestão inteligente de vendas com análise financeira em tempo real")
        except:
            st.title("🍔 SISTEMA FINANCEIRO - CLIPS BURGER")
            st.caption("Gestão inteligente de vendas com análise financeira em tempo real")

    # Carregar dados
    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    # Tabs responsivas
    if is_mobile():
        tab_names = ["📝 Venda", "📈 Análise", "💡 Stats", "💰 Contábil", "🎬 Animado"]
    else:
        tab_names = ["📝 Registrar Venda", "📈 Análise Detalhada", "💡 Estatísticas", "💰 Análise Contábil", "🎬 Gráficos Animados"]
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_names)

    # --- TAB 1: REGISTRAR VENDA ---
    with tab1:
        st.header("📝 Registrar Nova Venda")
        with st.form("venda_form"):
            data_input = st.date_input("📅 Data da Venda", value=datetime.now(), format="DD/MM/YYYY")
            
            if is_mobile():
                # Layout vertical para mobile
                cartao_input = st.number_input("💳 Cartão (R$)", min_value=0.0, value=0.0, format="%.2f")
                dinheiro_input = st.number_input("💵 Dinheiro (R$)", min_value=0.0, value=0.0, format="%.2f")
                pix_input = st.number_input("📱 PIX (R$)", min_value=0.0, value=0.0, format="%.2f")
            else:
                # Layout horizontal para desktop
                col1, col2, col3 = st.columns(3)
                with col1: cartao_input = st.number_input("💳 Cartão (R$)", min_value=0.0, value=0.0, format="%.2f")
                with col2: dinheiro_input = st.number_input("💵 Dinheiro (R$)", min_value=0.0, value=0.0, format="%.2f")
                with col3: pix_input = st.number_input("📱 PIX (R$)", min_value=0.0, value=0.0, format="%.2f")
            
            total_venda_form = (cartao_input or 0.0) + (dinheiro_input or 0.0) + (pix_input or 0.0)
            st.markdown(f"### **💰 Total: {format_brl(total_venda_form)}**")
            
            submitted = st.form_submit_button("✅ Registrar Venda", type="primary", use_container_width=True)
            
            if submitted:
                if total_venda_form > 0:
                    formatted_date = data_input.strftime('%d/%m/%Y')
                    worksheet_obj = get_worksheet()
                    if worksheet_obj and add_data_to_sheet(formatted_date, cartao_input, dinheiro_input, pix_input, worksheet_obj):
                        read_sales_data.clear()
                        process_data.clear()
                        st.success("✅ Venda registrada!")
                        st.rerun()
                    elif not worksheet_obj: 
                        st.error("❌ Falha ao conectar à planilha.")
                else: 
                    st.warning("⚠️ O valor deve ser maior que zero.")

    # --- SIDEBAR COM FILTROS ---
    with st.sidebar:
        st.header("🔍 Filtros")
        st.markdown("---")
        
        selected_anos_filter, selected_meses_filter = [], []
        
        if not df_processed.empty and 'Ano' in df_processed.columns:
            anos_disponiveis = sorted(df_processed['Ano'].dropna().unique().astype(int), reverse=True)
            if anos_disponiveis:
                default_ano = [datetime.now().year] if datetime.now().year in anos_disponiveis else [anos_disponiveis[0]]
                selected_anos_filter = st.multiselect("📅 Ano(s):", options=anos_disponiveis, default=default_ano)
                
                if selected_anos_filter:
                    df_para_filtro_mes = df_processed[df_processed['Ano'].isin(selected_anos_filter)]
                    if not df_para_filtro_mes.empty and 'Mês' in df_para_filtro_mes.columns:
                        meses_numeros_disponiveis = sorted(df_para_filtro_mes['Mês'].dropna().unique().astype(int))
                        meses_opcoes_dict = {m_num: meses_ordem[m_num-1] for m_num in meses_numeros_disponiveis if 1 <= m_num <= 12}
                        meses_opcoes_display = [f"{m_num} - {m_nome}" for m_num, m_nome in meses_opcoes_dict.items()]
                        
                        default_mes_num = datetime.now().month
                        default_mes_str = f"{default_mes_num} - {meses_ordem[default_mes_num-1]}" if 1 <= default_mes_num <= 12 and meses_opcoes_dict else None
                        default_meses_selecionados = [default_mes_str] if default_mes_str and default_mes_str in meses_opcoes_display else meses_opcoes_display
                        
                        selected_meses_str = st.multiselect("📆 Mês(es):", options=meses_opcoes_display, default=default_meses_selecionados)
                        selected_meses_filter = [int(m.split(" - ")[0]) for m in selected_meses_str]

    # Aplicar filtros
    df_filtered = df_processed.copy()
    if not df_filtered.empty:
        if selected_anos_filter and 'Ano' in df_filtered.columns: 
            df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos_filter)]
        if selected_meses_filter and 'Mês' in df_filtered.columns: 
            df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses_filter)]

    # --- TAB 2: ANÁLISE DETALHADA ---
    with tab2:
        st.header("📈 Análise Detalhada")
        if not df_filtered.empty:
            # Resumo em métricas
            if is_mobile():
                st.metric("Total de Vendas", len(df_filtered))
                st.metric("Faturamento", format_brl(df_filtered['Total'].sum()))
                st.metric("Média por Venda", format_brl(df_filtered['Total'].mean()))
            else:
                col1, col2, col3 = st.columns(3)
                col1.metric("Total de Vendas", len(df_filtered))
                col2.metric("Faturamento Total", format_brl(df_filtered['Total'].sum()))
                col3.metric("Média por Venda", format_brl(df_filtered['Total'].mean()))
            
            # Tabela de dados
            st.subheader("📊 Dados de Vendas")
            cols_to_display = ['DataFormatada', 'DiaSemana', 'Cartão', 'Dinheiro', 'Pix', 'Total']
            cols_existentes = [col for col in cols_to_display if col in df_filtered.columns]
            
            if cols_existentes:
                height = 300 if is_mobile() else 600
                st.dataframe(df_filtered[cols_existentes], use_container_width=True, height=height, hide_index=True)
        else:
            st.info("Nenhum dado disponível para os filtros selecionados.")

    # --- TAB 3: ESTATÍSTICAS ---
    with tab3:
        st.header("💡 Estatísticas")
        if not df_filtered.empty:
            # Métricas principais
            total_faturamento = df_filtered['Total'].sum()
            cartao_total = df_filtered['Cartão'].sum()
            dinheiro_total = df_filtered['Dinheiro'].sum()
            pix_total = df_filtered['Pix'].sum()
            
            if is_mobile():
                st.metric("💰 Faturamento Total", format_brl(total_faturamento))
                st.metric("💳 Cartão", format_brl(cartao_total))
                st.metric("💵 Dinheiro", format_brl(dinheiro_total))
                st.metric("📱 PIX", format_brl(pix_total))
            else:
                col1, col2 = st.columns(2)
                col1.metric("💰 Faturamento Total", format_brl(total_faturamento))
                col2.metric("📊 Média Diária", format_brl(df_filtered['Total'].mean()))
                
                col3, col4, col5 = st.columns(3)
                col3.metric("💳 Cartão", format_brl(cartao_total))
                col4.metric("💵 Dinheiro", format_brl(dinheiro_total))
                col5.metric("📱 PIX", format_brl(pix_total))
        else:
            st.info("Sem dados para estatísticas.")

    # --- TAB 4: ANÁLISE CONTÁBIL ---
    with tab4:
        st.header("💰 Análise Contábil")
        
        # Parâmetros financeiros
        with st.container(border=True):
            st.subheader("⚙️ Parâmetros Contábeis")
            
            if is_mobile():
                salario_minimo_input = st.number_input("💼 Salário Base (R$)", min_value=0.0, value=1550.0, format="%.2f")
                custo_contadora_input = st.number_input("📋 Contabilidade (R$)", min_value=0.0, value=316.0, format="%.2f")
                custo_fornecedores_percentual = st.number_input("📦 Custo Produtos (%)", min_value=0.0, max_value=100.0, value=30.0, format="%.1f")
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    salario_minimo_input = st.number_input("💼 Salário Base (R$)", min_value=0.0, value=1550.0, format="%.2f")
                with col2:
                    custo_contadora_input = st.number_input("📋 Contabilidade (R$)", min_value=0.0, value=316.0, format="%.2f")
                with col3:
                    custo_fornecedores_percentual = st.number_input("📦 Custo Produtos (%)", min_value=0.0, max_value=100.0, value=30.0, format="%.1f")

        if not df_filtered.empty:
            resultados = calculate_financial_results(df_filtered, salario_minimo_input, custo_contadora_input, custo_fornecedores_percentual)
            
            st.subheader("📊 Resultados Financeiros")
            
            if is_mobile():
                st.metric("💰 Faturamento Bruto", format_brl(resultados['faturamento_bruto']))
                st.metric("🏦 Receita Tributável", format_brl(resultados['faturamento_tributavel']))
                st.metric("💵 Receita Não Tributável", format_brl(resultados['faturamento_nao_tributavel']))
                st.metric("💸 Total de Custos", format_brl(resultados['total_custos']))
                st.metric("📈 Lucro Bruto", format_brl(resultados['lucro_bruto']))
            else:
                col1, col2, col3 = st.columns(3)
                col1.metric("💰 Faturamento Bruto", format_brl(resultados['faturamento_bruto']))
                col2.metric("🏦 Receita Tributável", format_brl(resultados['faturamento_tributavel']))
                col3.metric("💵 Receita Não Tributável", format_brl(resultados['faturamento_nao_tributavel']))
                
                col4, col5 = st.columns(2)
                col4.metric("💸 Total de Custos", format_brl(resultados['total_custos']))
                col5.metric("📈 Lucro Bruto", format_brl(resultados['lucro_bruto']))
        else:
            st.info("Sem dados para análise contábil.")

    # --- TAB 5: GRÁFICOS ANIMADOS ---
    with tab5:
        st.header("🎬 Gráficos Animados")
        
        if df_filtered.empty:
            st.warning("📊 Sem dados para gráficos animados.")
            return
        
        # Seção 1: Gráficos Animados
        st.subheader("🎥 Animações Temporais")
        
        if is_mobile():
            # Layout vertical para mobile
            if st.button("▶️ Evolução das Vendas", use_container_width=True):
                with st.spinner("Gerando animação..."):
                    fig_timeline = create_animated_sales_timeline(df_filtered)
                    if fig_timeline:
                        st.plotly_chart(fig_timeline, use_container_width=True)
            
            if st.button("🏁 Corrida dos Pagamentos", use_container_width=True):
                with st.spinner("Gerando corrida..."):
                    fig_race = create_animated_payment_race(df_filtered)
                    if fig_race:
                        st.plotly_chart(fig_race, use_container_width=True)
        else:
            # Layout horizontal para desktop
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("▶️ Reproduzir Evolução das Vendas"):
                    with st.spinner("Gerando animação..."):
                        fig_timeline = create_animated_sales_timeline(df_filtered)
                        if fig_timeline:
                            st.plotly_chart(fig_timeline, use_container_width=True)
            
            with col2:
                if st.button("🏁 Corrida dos Métodos de Pagamento"):
                    with st.spinner("Gerando corrida animada..."):
                        fig_race = create_animated_payment_race(df_filtered)
                        if fig_race:
                            st.plotly_chart(fig_race, use_container_width=True)
        
        st.markdown("---")
        
        # Seção 2: Indicadores em Tempo Real
        st.subheader("🎯 Indicadores de Performance")
        fig_gauges = create_realtime_gauges(df_filtered)
        if fig_gauges:
            st.plotly_chart(fig_gauges, use_container_width=True)
        
        # Auto-refresh para dados em tempo real
        if st.checkbox("🔄 Auto-atualização (30s)"):
            time.sleep(30)
            st.rerun()

if __name__ == "__main__":
    main()
