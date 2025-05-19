import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import locale

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
WORKSHEET_NAME = 'Vendas'

# Configuração da página Streamlit com tema escuro
st.set_page_config(
    page_title="Sistema de Registro de Vendas",
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Sistema de Registro de Vendas"
    }
)

# Configura o locale para Português do Brasil para formatação de datas e nomes
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')  # Alternativa para Windows
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')  # Outra alternativa comum
        except locale.Error:
            try:
                locale.setlocale(locale.LC_TIME, 'C')  # Fallback para locale padrão
            except locale.Error:
                st.warning("Locale pt_BR não encontrado. Nomes de meses/dias podem aparecer em inglês.")

# Configuração de tema para os gráficos Altair
def configure_altair_theme():
    return {
        'config': {
            'background': 'transparent',
            'title': {'color': '#ffffff', 'fontSize': 16, 'font': 'Inter'},
            'axis': {
                'labelColor': '#cccccc',
                'titleColor': '#ffffff',
                'gridColor': '#555555',
                'domainColor': '#555555',
                'tickColor': '#555555',
                'grid': False,  # Remove linhas horizontais por padrão
            },
            'legend': {
                'labelColor': '#cccccc',
                'titleColor': '#ffffff',
                'symbolType': 'circle'
            },
            'range': {
                'category': ['#4c78a8', '#f58518', '#e45756', '#72b7b2', '#54a24b', '#eeca3b']
            },
            'view': {
                'stroke': 'transparent'  # Remove a borda do gráfico
            }
        }
    }

alt.themes.register('dark_theme', configure_altair_theme)
alt.themes.enable('dark_theme')

CHART_HEIGHT = 380  # Altura padrão para gráficos grandes

# --- Funções de Cache para Acesso ao Google Sheets ---
@st.cache_resource
def get_google_auth():
    """Autoriza o acesso ao Google Sheets e retorna o cliente gspread."""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/spreadsheets.readonly',
              'https://www.googleapis.com/auth/drive.readonly']
    try:
        credentials_dict = st.secrets["google_credentials"]
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
            st.error(f"Planilha com ID {SPREADSHEET_ID} não encontrada.")
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
                st.toast("⚠️ Planilha de vendas está vazia.", icon="📄")
                return pd.DataFrame(columns=['Data', 'Cartão', 'Dinheiro', 'Pix'])
            df = pd.DataFrame(rows)
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
        new_row = [date, float(cartao), float(dinheiro), float(pix)]
        worksheet_obj.append_row(new_row)
        st.success("Dados registrados com sucesso!")
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar dados na planilha: {e}")
        return False

@st.cache_data
def process_data(df_input):
    """Processa e prepara os dados de vendas para análise."""
    df = df_input.copy()
    if not df.empty:
        for col in ['Cartão', 'Dinheiro', 'Pix']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0  # Adiciona coluna se não existir para evitar erros
        
        df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']
        
        if 'Data' in df.columns:
            try:
                df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
                df.dropna(subset=['Data'], inplace=True)  # Remove linhas onde a data não pôde ser convertida
                
                if not df.empty:
                    df['Ano'] = df['Data'].dt.year
                    df['Mês'] = df['Data'].dt.month
                    df['MêsNome'] = df['Data'].dt.strftime('%B').str.capitalize()
                    df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                    df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                    # Usar strftime('%A') para nome do dia da semana de acordo com o locale
                    df['DiaSemana'] = df['Data'].dt.strftime('%A').str.capitalize()
                    df['DiaSemanaNum'] = df['Data'].dt.dayofweek  # Para ordenação
                else:
                    st.warning("Nenhuma data válida encontrada após conversão inicial.")

            except Exception as e:  # Alterado para Exception genérica após pd.to_datetime
                st.error(f"Erro ao processar a coluna 'Data': {e}")
                # Retornar colunas básicas mesmo em caso de erro para evitar quebras
                for col_date_derived in ['Ano', 'Mês', 'MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana', 'DiaSemanaNum']:
                    if col_date_derived not in df.columns:
                         df[col_date_derived] = None 
    return df

# --- Funções de Gráficos ---
def create_pie_chart_payment_methods(df_data):
    """Cria gráfico de pizza para métodos de pagamento"""
    if df_data is None or df_data.empty or not all(col in df_data.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
        return None
    payment_sum = df_data[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
    payment_sum.columns = ['Método', 'Valor']
    total_pagamentos = payment_sum['Valor'].sum()
    if total_pagamentos == 0:
        return None
    payment_sum['Porcentagem'] = (payment_sum['Valor'] / total_pagamentos) * 100

    # Gráfico de pizza melhorado com cores mais vibrantes e estilo moderno
    pie_chart = alt.Chart(payment_sum).mark_arc(innerRadius=80, padAngle=0.03).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        color=alt.Color("Método:N", 
                       scale=alt.Scale(range=['#4c78a8', '#f58518', '#72b7b2']),
                       legend=alt.Legend(title="Método", orient="bottom")),
        tooltip=[
            alt.Tooltip("Método:N"),
            alt.Tooltip("Valor:Q", format="R$,.2f", title="Valor"),
            alt.Tooltip("Porcentagem:Q", format=".1f", title="% do Total")
        ]
    ).properties(
        height=CHART_HEIGHT, 
        title=alt.TitleParams("Distribuição por Método de Pagamento", fontSize=18, anchor='middle')
    )
    
    # Texto no centro do gráfico
    text_values = pie_chart.mark_text(radius=110, size=14, fontWeight='bold', color='white').encode(
        text=alt.Text("Porcentagem:Q", format=".0f") + "%"
    )
    
    return pie_chart + text_values

def create_daily_sales_bar_chart(df_data):
    """Cria gráfico de barras para vendas diárias"""
    if df_data is None or df_data.empty or 'DataFormatada' not in df_data.columns:
        return None
    
    # Preparar dados para ordenação
    df_to_melt = df_data.copy()
    if 'Data' not in df_to_melt.columns and 'DataFormatada' in df_to_melt.columns:
        df_to_melt.loc[:, 'Data'] = pd.to_datetime(df_to_melt['DataFormatada'], format='%d/%m/%Y', errors='coerce')
    elif 'Data' not in df_to_melt.columns:
        return None  # Não pode ordenar sem 'Data'
    
    daily_data = df_to_melt.melt(
        id_vars=['DataFormatada', 'Data'],
        value_vars=['Cartão', 'Dinheiro', 'Pix'],
        var_name='Método',
        value_name='Valor'
    )
    daily_data = daily_data[daily_data['Valor'] > 0]
    
    if daily_data.empty:
        return None

    # Gráfico de barras melhorado com barras arredondadas e cores mais vibrantes
    bar_chart = alt.Chart(daily_data).mark_bar(
        cornerRadiusTopLeft=4,
        cornerRadiusTopRight=4,
        size=16
    ).encode(
        x=alt.X('DataFormatada:N', 
                title='Data', 
                axis=alt.Axis(labelAngle=-45, labelFontSize=11), 
                sort=alt.EncodingSortField(field="Data", op="min", order='ascending')),
        y=alt.Y('Valor:Q', 
                title='Valor (R$)', 
                stack='zero',
                axis=alt.Axis(grid=False, domain=True)),  # Remove linhas horizontais
        color=alt.Color('Método:N', 
                       scale=alt.Scale(range=['#4c78a8', '#f58518', '#72b7b2']),
                       legend=alt.Legend(title="Método", orient="bottom")),
        tooltip=['DataFormatada', 'Método', alt.Tooltip('Valor:Q', format='R$,.2f')]
    ).properties(
        height=CHART_HEIGHT, 
        title=alt.TitleParams("Vendas Diárias por Método", fontSize=18, anchor='middle')
    ).configure_view(
        strokeWidth=0  # Remove a borda do gráfico
    )
    
    return bar_chart

def create_accumulated_capital_line_chart(df_data):
    """Cria gráfico de linha para capital acumulado"""
    if df_data is None or df_data.empty or 'Data' not in df_data.columns or 'Total' not in df_data.columns:
        return None
    
    df_accumulated = df_data.sort_values('Data').copy()
    if df_accumulated.empty:
        return None
        
    df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()

    # Gráfico de área melhorado com gradiente e linha mais suave
    line_chart = alt.Chart(df_accumulated).mark_area(
        line={'color':'#4c78a8', 'strokeWidth': 3},
        point=False,
        interpolate='monotone',
        color=alt.Gradient(
            gradient='linear',
            stops=[
                alt.GradientStop(color='rgba(76,120,168,0.1)', offset=0.2), 
                alt.GradientStop(color='rgba(76,120,168,0.7)', offset=1)
            ],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X('Data:T', 
                title='Data', 
                axis=alt.Axis(format="%d/%m/%y", labelAngle=-45, labelFontSize=11, grid=False)),
        y=alt.Y('Total Acumulado:Q', 
                title='Capital Acumulado (R$)',
                axis=alt.Axis(grid=False)),  # Remove linhas horizontais
        tooltip=[
            alt.Tooltip('DataFormatada', title="Data"), 
            alt.Tooltip('Total Acumulado:Q', format='R$,.2f')
        ]
    ).properties(
        height=CHART_HEIGHT, 
        title=alt.TitleParams("Acúmulo de Capital", fontSize=18, anchor='middle')
    ).configure_view(
        strokeWidth=0  # Remove a borda do gráfico
    )
    
    return line_chart

def create_heatmap_sales_by_weekday_month(df_data):
    """Cria um heatmap de vendas por dia da semana e mês"""
    if df_data is None or df_data.empty or 'DiaSemana' not in df_data.columns or 'MêsNome' not in df_data.columns:
        return None
    
    # Agrupa os dados por dia da semana e mês
    heatmap_data = df_data.groupby(['DiaSemana', 'MêsNome', 'DiaSemanaNum', 'Mês'])['Total'].mean().reset_index()
    
    if heatmap_data.empty:
        return None
    
    # Ordena os dias da semana corretamente
    dias_ordem_numerica = list(range(7))  # 0=Segunda, ..., 6=Domingo
    nomes_dias_map = {i: (datetime(2000,1,3) + timedelta(days=i)).strftime('%A').capitalize() for i in dias_ordem_numerica}
    
    # Ordena os meses corretamente
    meses_ordem = list(range(1, 13))
    
    # Cria o heatmap
    heatmap = alt.Chart(heatmap_data).mark_rect().encode(
        x=alt.X('MêsNome:N', 
                title='Mês', 
                sort=meses_ordem,
                axis=alt.Axis(labelAngle=0)),
        y=alt.Y('DiaSemana:N', 
                title='Dia da Semana', 
                sort=alt.EncodingSortField(field="DiaSemanaNum", order='ascending'),
                axis=alt.Axis(labelAlign='right')),
        color=alt.Color('Total:Q', 
                       scale=alt.Scale(scheme='viridis'),
                       legend=alt.Legend(title="Média de Vendas (R$)")),
        tooltip=[
            alt.Tooltip('DiaSemana:N', title="Dia"),
            alt.Tooltip('MêsNome:N', title="Mês"),
            alt.Tooltip('Total:Q', format='R$,.2f', title="Média")
        ]
    ).properties(
        width=600,
        height=300,
        title=alt.TitleParams("Média de Vendas por Dia e Mês", fontSize=18, anchor='middle')
    ).configure_view(
        strokeWidth=0
    )
    
    return heatmap

def create_avg_sales_by_weekday_bar_chart(df_data):
    """Cria gráfico de barras para média de vendas por dia da semana (incluindo sábado)"""
    if df_data is None or df_data.empty or 'DiaSemana' not in df_data.columns or 'DiaSemanaNum' not in df_data.columns:
        return None
    
    # Ajustado para usar DiaSemanaNum para ordenação correta e incluir Sábado
    dias_ordem_numerica = list(range(6))  # 0=Segunda, ..., 5=Sábado
    nomes_dias_map = {i: (datetime(2000,1,3) + timedelta(days=i)).strftime('%A').capitalize() for i in dias_ordem_numerica}
    dias_ordem_locale = [nomes_dias_map[i] for i in dias_ordem_numerica]

    df_funcionamento = df_data[df_data['DiaSemanaNum'].isin(dias_ordem_numerica)]
    if df_funcionamento.empty:
        return None
    
    vendas_media_dia = df_funcionamento.groupby(['DiaSemanaNum', 'DiaSemana'])['Total'].mean().reset_index()
    
    # Gráfico de barras melhorado com cores por dia e valores nos topos
    bar_chart = alt.Chart(vendas_media_dia).mark_bar(
        cornerRadiusTopLeft=6,
        cornerRadiusTopRight=6
    ).encode(
        x=alt.X('DiaSemana:N', 
                title='Dia da Semana', 
                sort=alt.EncodingSortField(field="DiaSemanaNum", order='ascending'),
                axis=alt.Axis(labelAngle=0)),
        y=alt.Y('Total:Q', 
                title='Média de Vendas (R$)',
                axis=alt.Axis(grid=False)),  # Remove linhas horizontais
        color=alt.Color('DiaSemana:N', 
                       scale=alt.Scale(scheme='tableau10'),
                       legend=None),
        tooltip=[alt.Tooltip('DiaSemana:N', title="Dia"), alt.Tooltip('Total:Q', format='R$,.2f', title="Média")]
    ).properties(
        height=CHART_HEIGHT, 
        title=alt.TitleParams(text="Média de Vendas por Dia da Semana", fontSize=18, anchor='middle')
    ).configure_view(
        strokeWidth=0
    )
    
    # Adiciona texto com valores no topo das barras
    text_on_bars = alt.Chart(vendas_media_dia).mark_text(
        dy=-8,
        color='white',
        fontSize=12,
        fontWeight='bold'
    ).encode(
        x='DiaSemana:N',
        y='Total:Q',
        text=alt.Text('Total:Q', format="R$,.0f")
    )
    
    return bar_chart + text_on_bars

def create_weekly_seasonality_bar_chart(df_data):
    """Cria gráfico de barras para sazonalidade semanal (incluindo sábado)"""
    if df_data is None or df_data.empty or 'DiaSemana' not in df_data.columns or 'DiaSemanaNum' not in df_data.columns or len(df_data) < 6:
        return None
    
    # Ajustado para usar DiaSemanaNum para ordenação correta e incluir Sábado
    dias_ordem_numerica = list(range(6))  # 0=Segunda, ..., 5=Sábado
    nomes_dias_map = {i: (datetime(2000,1,3) + timedelta(days=i)).strftime('%A').capitalize() for i in dias_ordem_numerica}
    dias_ordem_locale = [nomes_dias_map[i] for i in dias_ordem_numerica]

    df_funcionamento = df_data[df_data['DiaSemanaNum'].isin(dias_ordem_numerica)]
    if df_funcionamento.empty:
        return None
    
    vendas_total_dia = df_funcionamento.groupby(['DiaSemanaNum', 'DiaSemana'])['Total'].sum().reset_index()
    total_semanal_abs = vendas_total_dia['Total'].sum()
    
    if total_semanal_abs == 0:
        return None
        
    vendas_total_dia['Porcentagem'] = (vendas_total_dia['Total'] / total_semanal_abs * 100)
    
    # Gráfico de barras melhorado com cores por dia e valores nos topos
    bar_chart = alt.Chart(vendas_total_dia).mark_bar(
        cornerRadiusTopLeft=6,
        cornerRadiusTopRight=6
    ).encode(
        x=alt.X('DiaSemana:N', 
                title='Dia da Semana', 
                sort=alt.EncodingSortField(field="DiaSemanaNum", order='ascending'),
                axis=alt.Axis(labelAngle=0)),
        y=alt.Y('Porcentagem:Q', 
                title='% do Volume Semanal',
                axis=alt.Axis(grid=False)),  # Remove linhas horizontais
        color=alt.Color('DiaSemana:N', 
                       scale=alt.Scale(scheme='tableau10'),
                       legend=None),
        tooltip=[
            alt.Tooltip('DiaSemana:N', title="Dia"), 
            alt.Tooltip('Total:Q', format='R$,.2f', title="Total"),
            alt.Tooltip('Porcentagem:Q', format='.1f', title="% do Total")
        ]
    ).properties(
        height=CHART_HEIGHT, 
        title=alt.TitleParams(text="Distribuição Semanal de Vendas", fontSize=18, anchor='middle')
    ).configure_view(
        strokeWidth=0
    )
    
    # Adiciona texto com valores no topo das barras
    text_on_bars = alt.Chart(vendas_total_dia).mark_text(
        dy=-8,
        color='white',
        fontSize=12,
        fontWeight='bold'
    ).encode(
        x='DiaSemana:N',
        y='Porcentagem:Q',
        text=alt.Text('Porcentagem:Q', format='.1f') + "%"
    )
    
    return bar_chart + text_on_bars

def create_monthly_trend_chart(df_data):
    """Cria gráfico de tendência mensal com linha e pontos"""
    if df_data is None or df_data.empty or 'AnoMês' not in df_data.columns:
        return None
    
    vendas_mensais = df_data.groupby('AnoMês')['Total'].sum().reset_index()
    if len(vendas_mensais) < 2:
        return None
    
    # Gráfico de linha com pontos e área sombreada
    line_chart = alt.Chart(vendas_mensais).mark_line(
        point=True,
        strokeWidth=3,
        color='#4c78a8',
        interpolate='monotone'
    ).encode(
        x=alt.X('AnoMês:N', 
                title='Mês',
                axis=alt.Axis(labelAngle=-45, labelFontSize=11, grid=False)),
        y=alt.Y('Total:Q', 
                title='Total de Vendas (R$)',
                axis=alt.Axis(grid=False)),
        tooltip=['AnoMês', alt.Tooltip('Total:Q', format='R$,.2f')]
    )
    
    # Adiciona área sombreada abaixo da linha
    area = alt.Chart(vendas_mensais).mark_area(
        opacity=0.3,
        color='#4c78a8',
        interpolate='monotone'
    ).encode(
        x='AnoMês:N',
        y='Total:Q'
    )
    
    # Combina os gráficos
    chart = (area + line_chart).properties(
        height=CHART_HEIGHT,
        title=alt.TitleParams("Tendência de Vendas Mensais", fontSize=18, anchor='middle')
    ).configure_view(
        strokeWidth=0
    )
    
    return chart

def create_payment_method_evolution_chart(df_data):
    """Cria gráfico de evolução dos métodos de pagamento ao longo do tempo"""
    if df_data is None or df_data.empty or 'AnoMês' not in df_data.columns:
        return None
    
    # Agrupa os dados por mês e método de pagamento
    payment_evolution = df_data.groupby('AnoMês')[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
    
    if payment_evolution.empty or len(payment_evolution) < 2:
        return None
    
    # Converte para formato longo para facilitar a visualização
    payment_evolution_long = payment_evolution.melt(
        id_vars=['AnoMês'],
        value_vars=['Cartão', 'Dinheiro', 'Pix'],
        var_name='Método',
        value_name='Valor'
    )
    
    # Cria o gráfico de linhas com pontos
    evolution_chart = alt.Chart(payment_evolution_long).mark_line(
        point=True,
        strokeWidth=2
    ).encode(
        x=alt.X('AnoMês:N', 
                title='Mês',
                axis=alt.Axis(labelAngle=-45, labelFontSize=11, grid=False)),
        y=alt.Y('Valor:Q', 
                title='Valor (R$)',
                axis=alt.Axis(grid=False)),
        color=alt.Color('Método:N', 
                       scale=alt.Scale(range=['#4c78a8', '#f58518', '#72b7b2']),
                       legend=alt.Legend(title="Método", orient="bottom")),
        tooltip=['AnoMês', 'Método', alt.Tooltip('Valor:Q', format='R$,.2f')]
    ).properties(
        height=CHART_HEIGHT,
        title=alt.TitleParams("Evolução dos Métodos de Pagamento", fontSize=18, anchor='middle')
    ).configure_view(
        strokeWidth=0
    )
    
    return evolution_chart

# --- Função Principal ---
def main():
    st.title("📊 Sistema de Registro de Vendas")
    
    # Lê os dados da planilha
    df_sales = read_sales_data()
    
    # Processa os dados para análise
    df_processed = process_data(df_sales)
    
    # Cria as abas
    tab1, tab2, tab3 = st.tabs(["📝 Registro", "📈 Análise", "📊 Estatísticas"])
    
    with tab1:
        st.header("📝 Registro de Vendas")
        
        # Formulário para adicionar nova venda
        with st.form(key="sales_form"):
            st.subheader("Nova Venda")
            
            col1, col2 = st.columns(2)
            with col1:
                data_input = st.date_input("Data", datetime.now())
            
            col1, col2, col3 = st.columns(3)
            with col1:
                cartao_input = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f", step=10.0)
            with col2:
                dinheiro_input = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f", step=10.0)
            with col3:
                pix_input = st.number_input("Pix (R$)", min_value=0.0, format="%.2f", step=10.0)
            
            submit_button = st.form_submit_button(label="Registrar Venda")
            
            if submit_button:
                if cartao_input > 0 or dinheiro_input > 0 or pix_input > 0:
                    formatted_date = data_input.strftime('%d/%m/%Y')
                    worksheet_obj = get_worksheet()
                    if add_data_to_sheet(formatted_date, cartao_input, dinheiro_input, pix_input, worksheet_obj):
                        read_sales_data.clear()  # Limpa o cache dos dados de vendas
                        process_data.clear()  # Limpa o cache dos dados processados
                        st.rerun()  # Força o recarregamento da app para refletir novos dados
                else:
                    st.warning("Pelo menos um valor de venda deve ser maior que zero.")

    # Prepara dados para abas de análise e estatística
    # Filtros na sidebar (afetam Tab2 e Tab3)
    selected_anos_filter = []
    selected_meses_filter = []

    with st.sidebar:
        st.header("🔍 Filtros")
        if not df_processed.empty and 'Ano' in df_processed.columns and not df_processed['Ano'].dropna().empty:
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            anos_disponiveis = sorted(df_processed['Ano'].dropna().unique().astype(int))
            default_anos = [current_year] if current_year in anos_disponiveis else anos_disponiveis
            selected_anos_filter = st.multiselect("Selecione o(s) Ano(s):", options=anos_disponiveis, default=default_anos)

            if selected_anos_filter:
                df_para_filtro_mes = df_processed[df_processed['Ano'].isin(selected_anos_filter)]
                if not df_para_filtro_mes.empty and 'Mês' in df_para_filtro_mes.columns and not df_para_filtro_mes['Mês'].dropna().empty:
                    meses_numeros_disponiveis = sorted(df_para_filtro_mes['Mês'].dropna().unique().astype(int))
                    # Gera nomes dos meses com base no locale
                    meses_nomes_map = {m: datetime(2000, m, 1).strftime('%B').capitalize() for m in meses_numeros_disponiveis}
                    meses_opcoes = [f"{m} - {meses_nomes_map[m]}" for m in meses_numeros_disponiveis]
                    
                    default_mes_opcao_str = f"{current_month} - {datetime(2000, current_month, 1).strftime('%B').capitalize()}"
                    default_meses_selecionados = [default_mes_opcao_str] if default_mes_opcao_str in meses_opcoes else meses_opcoes
                    
                    selected_meses_str = st.multiselect("Selecione o(s) Mês(es):", options=meses_opcoes, default=default_meses_selecionados)
                    selected_meses_filter = [int(m.split(" - ")[0]) for m in selected_meses_str]
        else:
            st.sidebar.info("Não há dados suficientes para aplicar filtros de data.")

    # Aplicar filtros aos dados processados
    df_filtered = df_processed.copy()
    if not df_filtered.empty:
        if selected_anos_filter and 'Ano' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos_filter)]
        if selected_meses_filter and 'Mês' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses_filter)]
    
    with tab2:
        st.header("Análise Detalhada de Vendas")
        if not df_filtered.empty and 'DataFormatada' in df_filtered.columns:
            st.subheader("Dados Filtrados")
            
            # Tabela sem container e não expansível
            st.dataframe(df_filtered[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']], 
                        use_container_width=True, 
                        height=300)

            # Duas colunas para os gráficos principais
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Distribuição por Método")
                payment_filtered_data = pd.DataFrame({
                    'Método': ['Cartão', 'Dinheiro', 'PIX'],
                    'Valor': [df_filtered['Cartão'].sum(), df_filtered['Dinheiro'].sum(), df_filtered['Pix'].sum()]
                })
                pie_chart = alt.Chart(payment_filtered_data).mark_arc(innerRadius=50, padAngle=0.03).encode(
                    theta=alt.Theta("Valor:Q", stack=True),
                    color=alt.Color("Método:N", 
                                   scale=alt.Scale(range=['#4c78a8', '#f58518', '#72b7b2']),
                                   legend=alt.Legend(title="Método", orient="bottom")),
                    tooltip=["Método", alt.Tooltip("Valor:Q", format="R$,.2f")]
                ).properties(height=300)
                text = pie_chart.mark_text(radius=90, size=14, fontWeight='bold', color='white').encode(
                    text=alt.Text("Valor:Q", format="R$,.0f")
                )
                st.altair_chart(pie_chart + text, use_container_width=True)
            
            with col2:
                st.subheader("Evolução dos Métodos")
                if 'AnoMês' in df_filtered.columns:
                    payment_evolution = df_filtered.groupby('AnoMês')[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
                    if not payment_evolution.empty and len(payment_evolution) > 1:
                        payment_evolution_long = payment_evolution.melt(
                            id_vars=['AnoMês'],
                            value_vars=['Cartão', 'Dinheiro', 'Pix'],
                            var_name='Método',
                            value_name='Valor'
                        )
                        evolution_chart = alt.Chart(payment_evolution_long).mark_line(
                            point=True,
                            strokeWidth=2
                        ).encode(
                            x=alt.X('AnoMês:N', title='Mês', axis=alt.Axis(labelAngle=-45, grid=False)),
                            y=alt.Y('Valor:Q', title='Valor (R$)', axis=alt.Axis(grid=False)),
                            color=alt.Color('Método:N', scale=alt.Scale(range=['#4c78a8', '#f58518', '#72b7b2'])),
                            tooltip=['AnoMês', 'Método', alt.Tooltip('Valor:Q', format='R$,.2f')]
                        ).properties(height=300)
                        st.altair_chart(evolution_chart, use_container_width=True)
                    else:
                        st.info("Dados insuficientes para mostrar evolução dos métodos.")
                else:
                    st.info("Dados de mês não disponíveis para evolução.")

            st.subheader("Vendas Diárias por Método de Pagamento")
            daily_data = df_filtered.melt(id_vars=['DataFormatada'], value_vars=['Cartão', 'Dinheiro', 'Pix'], var_name='Método', value_name='Valor')
            bar_chart = alt.Chart(daily_data).mark_bar(
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
                size=16
            ).encode(
                x=alt.X('DataFormatada:N', title='Data', axis=alt.Axis(labelAngle=-45, grid=False)),
                y=alt.Y('Valor:Q', title='Valor (R$)', stack='zero', axis=alt.Axis(grid=False)),
                color=alt.Color('Método:N', scale=alt.Scale(range=['#4c78a8', '#f58518', '#72b7b2'])),
                tooltip=['DataFormatada', 'Método', alt.Tooltip('Valor:Q', format='R$,.2f')]
            ).properties(height=400)
            st.altair_chart(bar_chart, use_container_width=True)

            st.subheader("Acúmulo de Capital ao Longo do Tempo")
            if 'Data' in df_filtered.columns:
                df_accumulated = df_filtered.sort_values('Data').copy()
                df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()
                line_chart = alt.Chart(df_accumulated).mark_area(
                    line={'color':'#4c78a8', 'strokeWidth': 3},
                    point=True,
                    interpolate='monotone',
                    color=alt.Gradient(
                        gradient='linear',
                        stops=[
                            alt.GradientStop(color='rgba(76,120,168,0.1)', offset=0.2), 
                            alt.GradientStop(color='rgba(76,120,168,0.7)', offset=1)
                        ],
                        x1=1, x2=1, y1=1, y2=0
                    )
                ).encode(
                    x=alt.X('Data:T', title='Data', axis=alt.Axis(format="%d/%m/%y", labelAngle=-45, grid=False)),
                    y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)', axis=alt.Axis(grid=False)),
                    tooltip=['DataFormatada', alt.Tooltip('Total Acumulado:Q', format='R$,.2f')]
                ).properties(height=400)
                st.altair_chart(line_chart, use_container_width=True)
            else:
                st.info("Coluna 'Data' não encontrada para gráfico de acúmulo.")
                
            # Novo gráfico: Heatmap de vendas por dia da semana e mês
            if 'DiaSemana' in df_filtered.columns and 'MêsNome' in df_filtered.columns:
                st.subheader("Padrão de Vendas por Dia e Mês")
                heatmap = create_heatmap_sales_by_weekday_month(df_filtered)
                if heatmap:
                    st.altair_chart(heatmap, use_container_width=True)
                else:
                    st.info("Dados insuficientes para o heatmap de vendas.")
        else:
            st.info("Não há dados para exibir na Análise Detalhada ou os dados filtrados estão vazios.")

    with tab3:
        st.header("📊 Estatísticas de Vendas")
        if not df_filtered.empty and 'Total' in df_filtered.columns:
            st.subheader("💰 Resumo Financeiro")
            total_vendas = len(df_filtered)
            total_faturamento = df_filtered['Total'].sum()
            media_por_venda = df_filtered['Total'].mean() if total_vendas > 0 else 0
            maior_venda = df_filtered['Total'].max() if total_vendas > 0 else 0
            menor_venda = df_filtered['Total'].min() if total_vendas > 0 else 0

            # Usando cards para destacar as métricas principais
            cols1 = st.columns(2)
            with cols1[0]:
                st.metric("🔢 Total de Vendas", f"{total_vendas}")
            with cols1[1]:
                st.metric("💵 Faturamento Total", f"R$ {total_faturamento:,.2f}")
            
            cols2 = st.columns(3)
            with cols2[0]:
                st.metric("📈 Média por Venda", f"R$ {media_por_venda:,.2f}")
            with cols2[1]:
                st.metric("⬆️ Maior Venda", f"R$ {maior_venda:,.2f}")
            with cols2[2]:
                st.metric("⬇️ Menor Venda", f"R$ {menor_venda:,.2f}")

            st.markdown("---")
            st.subheader("💳 Métodos de Pagamento")
            cartao_total = df_filtered['Cartão'].sum()
            dinheiro_total = df_filtered['Dinheiro'].sum()
            pix_total = df_filtered['Pix'].sum()
            total_pagamentos = cartao_total + dinheiro_total + pix_total
            cartao_pct = (cartao_total / total_pagamentos * 100) if total_pagamentos > 0 else 0
            dinheiro_pct = (dinheiro_total / total_pagamentos * 100) if total_pagamentos > 0 else 0
            pix_pct = (pix_total / total_pagamentos * 100) if total_pagamentos > 0 else 0

            # Usando colunas para organizar as informações de métodos de pagamento
            payment_cols = st.columns(3)
            with payment_cols[0]:
                st.info(f"**💳 Cartão:** R$ {cartao_total:.2f} ({cartao_pct:.1f}%)")
            with payment_cols[1]:
                st.info(f"**💵 Dinheiro:** R$ {dinheiro_total:.2f} ({dinheiro_pct:.1f}%)")
            with payment_cols[2]:
                st.info(f"**📱 PIX:** R$ {pix_total:.2f} ({pix_pct:.1f}%)")

            if total_pagamentos > 0:
                payment_data_stats = pd.DataFrame({'Método': ['Cartão', 'Dinheiro', 'PIX'], 'Valor': [cartao_total, dinheiro_total, pix_total]})
                pie_chart_stats = alt.Chart(payment_data_stats).mark_arc(innerRadius=80, padAngle=0.03).encode(
                    theta=alt.Theta("Valor:Q", stack=True),
                    color=alt.Color("Método:N", 
                                   scale=alt.Scale(range=['#4c78a8', '#f58518', '#72b7b2']),
                                   legend=alt.Legend(title="Método", orient="bottom")),
                    tooltip=["Método", alt.Tooltip("Valor:Q", format="R$,.2f")]
                ).properties(height=350)
                text_stats = pie_chart_stats.mark_text(radius=110, size=14, fontWeight='bold', color='white').encode(
                    text=alt.Text("Valor:Q", format="R$,.0f")
                )
                st.altair_chart(pie_chart_stats + text_stats, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📅 Análise Temporal")
            if total_vendas > 1 and 'Data' in df_filtered.columns and 'DiaSemana' in df_filtered.columns:
                metodo_preferido = "Cartão" if cartao_total >= max(dinheiro_total, pix_total) else \
                                  "Dinheiro" if dinheiro_total >= max(cartao_total, pix_total) else "PIX"
                emoji_metodo = "💳" if metodo_preferido == "Cartão" else "💵" if metodo_preferido == "Dinheiro" else "📱"
                
                # Usando cards para destacar informações temporais
                stats_cols_temporal = st.columns(3)
                with stats_cols_temporal[0]:
                    st.success(f"**{emoji_metodo} Método Preferido:** {metodo_preferido}")
                
                dias_distintos = df_filtered['Data'].nunique()
                media_diaria = total_faturamento / dias_distintos if dias_distintos > 0 else 0
                with stats_cols_temporal[1]:
                    st.success(f"**📊 Média Diária:** R$ {media_diaria:.2f}")
                
                dia_mais_vendas = df_filtered.groupby('DiaSemana')['Total'].sum().idxmax() if not df_filtered.empty else "N/A"
                with stats_cols_temporal[2]:
                    st.success(f"**📆 Dia com Mais Vendas:** {dia_mais_vendas}")

                # Gráfico de média por dia da semana (Seg-Sáb, usando locale)
                dias_uteis_nomes_locale = [datetime(2000, 1, i).strftime('%A').capitalize() for i in range(3, 3+6)]  # Seg a Sáb
                df_dias_uteis = df_filtered[df_filtered['DiaSemana'].isin(dias_uteis_nomes_locale)]
                if not df_dias_uteis.empty:
                    vendas_por_dia_uteis = df_dias_uteis.groupby('DiaSemana')['Total'].mean().reset_index()
                    # Garantir a ordem correta dos dias da semana no gráfico
                    dias_ordem_numerica = list(range(6))  # 0=Segunda, ..., 5=Sábado
                    nomes_dias_map = {i: (datetime(2000,1,3) + timedelta(days=i)).strftime('%A').capitalize() for i in dias_ordem_numerica}
                    dias_ordem_locale = [nomes_dias_map[i] for i in dias_ordem_numerica]
                    
                    vendas_por_dia_uteis['DiaSemanaOrdem'] = vendas_por_dia_uteis['DiaSemana'].map({dia: i for i, dia in enumerate(dias_ordem_locale)})
                    vendas_por_dia_uteis = vendas_por_dia_uteis.sort_values('DiaSemanaOrdem')

                    chart_dias_uteis = alt.Chart(vendas_por_dia_uteis).mark_bar(
                        cornerRadiusTopLeft=6,
                        cornerRadiusTopRight=6
                    ).encode(
                        x=alt.X('DiaSemana:N', title='Dia da Semana', sort=dias_ordem_locale, axis=alt.Axis(labelAngle=0, grid=False)),
                        y=alt.Y('Total:Q', title='Média de Vendas (R$)', axis=alt.Axis(grid=False)),
                        color=alt.Color('DiaSemana:N', scale=alt.Scale(scheme='tableau10'), legend=None),
                        tooltip=['DiaSemana', alt.Tooltip('Total:Q', format='R$,.2f')]
                    ).properties(height=350)
                    
                    # Adiciona texto com valores no topo das barras
                    text_on_bars = alt.Chart(vendas_por_dia_uteis).mark_text(
                        dy=-8,
                        color='white',
                        fontSize=12,
                        fontWeight='bold'
                    ).encode(
                        x='DiaSemana:N',
                        y='Total:Q',
                        text=alt.Text('Total:Q', format="R$,.0f")
                    )
                    
                    st.altair_chart(chart_dias_uteis + text_on_bars, use_container_width=True)
            
            if 'AnoMês' in df_filtered.columns and df_filtered['AnoMês'].nunique() > 1:
                st.subheader("📈 Tendência Mensal")
                vendas_mensais = df_filtered.groupby('AnoMês')['Total'].sum().reset_index()
                if len(vendas_mensais) >= 2:
                    ultimo_mes_val = vendas_mensais.iloc[-1]['Total']
                    penultimo_mes_val = vendas_mensais.iloc[-2]['Total']
                    variacao = ((ultimo_mes_val - penultimo_mes_val) / penultimo_mes_val * 100) if penultimo_mes_val > 0 else 0
                    emoji_tendencia = "🚀" if variacao > 10 else "📈" if variacao > 0 else "📉" if variacao < 0 else "➡️"
                    
                    # Usando card para destacar a variação mensal
                    st.warning(f"**{emoji_tendencia} Variação do último mês:** {variacao:.1f}% ({'-' if variacao < 0 else '+'} R$ {abs(ultimo_mes_val - penultimo_mes_val):.2f})")
                    
                    # Gráfico de tendência mensal melhorado
                    monthly_trend = create_monthly_trend_chart(df_filtered)
                    if monthly_trend:
                        st.altair_chart(monthly_trend, use_container_width=True)
            
            # Sazonalidade semanal
            if 'DiaSemana' in df_filtered.columns and 'DiaSemanaNum' in df_filtered.columns and len(df_filtered) > 6:
                st.subheader("📊 Sazonalidade Semanal")
                
                # Gráfico de sazonalidade semanal melhorado
                seasonality_chart = create_weekly_seasonality_bar_chart(df_filtered)
                if seasonality_chart:
                    st.altair_chart(seasonality_chart, use_container_width=True)
                
                dias_ordem_numerica = list(range(6))  # 0=Segunda, ..., 5=Sábado
                nomes_dias_map = {i: (datetime(2000,1,3) + timedelta(days=i)).strftime('%A').capitalize() for i in dias_ordem_numerica}
                dias_ordem_locale = [nomes_dias_map[i] for i in dias_ordem_numerica]
                
                df_dias_trabalho = df_filtered[df_filtered['DiaSemanaNum'].isin(dias_ordem_numerica)]
                if not df_dias_trabalho.empty:
                    vendas_dia_semana_total = df_dias_trabalho.groupby(['DiaSemanaNum', 'DiaSemana'])['Total'].sum().reset_index()
                    total_semanal_abs = vendas_dia_semana_total['Total'].sum()
                    
                    if total_semanal_abs > 0:
                        melhor_dia_df = vendas_dia_semana_total.loc[vendas_dia_semana_total['Total'].idxmax()]
                        pior_dia_df = vendas_dia_semana_total.loc[vendas_dia_semana_total['Total'].idxmin()]
                        
                        # Usando cards para destacar melhor e pior dia
                        best_worst_cols = st.columns(2)
                        with best_worst_cols[0]:
                            st.success(f"**🔝 Melhor dia:** {melhor_dia_df['DiaSemana']} (R$ {melhor_dia_df['Total']:.2f})")
                        with best_worst_cols[1]:
                            st.error(f"**🔻 Pior dia:** {pior_dia_df['DiaSemana']} (R$ {pior_dia_df['Total']:.2f})")

        else:
            st.info("Não há dados para exibir na aba Estatísticas ou os dados filtrados estão vazios.")

if __name__ == "__main__":
    main()
