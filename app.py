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
    page_icon="📊",
    layout="wide",  # Alterado para wide para melhor uso do espaço
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Sistema de Registro de Vendas - Versão 1.0"
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

# Configuração para usar tema escuro para os gráficos Altair
def configure_altair_theme():
    return {
        'config': {
            'title': {'color': '#ffffff', 'font': 'Inter', 'fontSize': 20},
            'axis': {
                'labelColor': '#cccccc',
                'titleColor': '#ffffff',
                'gridColor': '#555555',
                'domainColor': '#888888'
            },
            'legend': {
                'labelColor': '#cccccc',
                'titleColor': '#ffffff',
                'symbolStrokeWidth': 2
            },
            'view': {
                'stroke': 'transparent'
            },
            'range': {
                'category': ['#4c78a8', '#f58518', '#54a24b', '#e45756', '#72b7b2', '#eeca3b']
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
        st.success("✅ Dados registrados com sucesso!")
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

    # Mapeamento de métodos para emojis
    payment_sum['MétodoEmoji'] = payment_sum['Método'].map({
        'Cartão': '💳 Cartão', 
        'Dinheiro': '💵 Dinheiro', 
        'Pix': '📱 Pix'
    })

    pie_chart = alt.Chart(payment_sum).mark_arc(innerRadius=50, stroke='#1E1E1E', strokeWidth=2).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        color=alt.Color("MétodoEmoji:N", 
                       legend=alt.Legend(
                           title="Método de Pagamento",
                           labelFont="Inter",
                           titleFont="Inter",
                           symbolSize=100,
                           padding=10
                       )),
        tooltip=[
            alt.Tooltip("MétodoEmoji:N", title="Método"),
            alt.Tooltip("Valor:Q", format="R$ {,.2f}", title="Valor"),
            alt.Tooltip("Porcentagem:Q", format=".1f", title="% do Total")
        ]
    ).properties(
        height=CHART_HEIGHT, 
        title=alt.TitleParams(
            "Distribuição por Método de Pagamento",
            fontSize=18, 
            font="Inter",
            dy=-10, 
            anchor='middle'
        )
    )
    
    text_values = pie_chart.mark_text(
        radius=105, 
        size=16, 
        fontWeight='bold',
        font="Inter",
        color='white'
    ).encode(
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
    
    # Mapeamento de métodos para emojis
    metodo_emoji_map = {
        'Cartão': '💳 Cartão', 
        'Dinheiro': '💵 Dinheiro', 
        'Pix': '📱 Pix'
    }
    
    daily_data = df_to_melt.melt(
        id_vars=['DataFormatada', 'Data'],
        value_vars=['Cartão', 'Dinheiro', 'Pix'],
        var_name='Método',
        value_name='Valor'
    )
    daily_data = daily_data[daily_data['Valor'] > 0]
    daily_data['MétodoEmoji'] = daily_data['Método'].map(metodo_emoji_map)
    
    if daily_data.empty:
        return None

    bar_chart = alt.Chart(daily_data).mark_bar(
        size=20,
        cornerRadiusTopLeft=3,
        cornerRadiusTopRight=3
    ).encode(
        x=alt.X('DataFormatada:N', 
                title='Data', 
                axis=alt.Axis(labelAngle=-45, labelFont="Inter", titleFont="Inter"), 
                sort=alt.EncodingSortField(field="Data", op="min", order='ascending')),
        y=alt.Y('Valor:Q', title='Valor (R$)', stack='zero', axis=alt.Axis(labelFont="Inter", titleFont="Inter")),
        color=alt.Color('MétodoEmoji:N', 
                       legend=alt.Legend(
                           title="Método de Pagamento",
                           labelFont="Inter",
                           titleFont="Inter"
                       )),
        tooltip=[
            alt.Tooltip('DataFormatada', title="Data"),
            alt.Tooltip('MétodoEmoji:N', title="Método"),
            alt.Tooltip('Valor:Q', format='R$ {,.2f}', title="Valor")
        ]
    ).properties(
        height=CHART_HEIGHT, 
        title=alt.TitleParams(
            "Vendas Diárias por Método",
            fontSize=18, 
            font="Inter",
            dy=-10, 
            anchor='middle'
        )
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

    line_chart = alt.Chart(df_accumulated).mark_area(
        line={'color':'#4c78a8', 'strokeWidth': 3}, # Cor principal do tema
        point=True, # Adiciona pontos para destacar os dias
        interpolate='monotone', # Linha mais suave
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='rgba(76,120,168,0.1)', offset=0.2), # Usando a cor principal com transparência
                   alt.GradientStop(color='rgba(76,120,168,0.7)', offset=1)],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X('Data:T',
                title='Data',
                axis=alt.Axis(
                    format="%d/%m/%y", 
                    labelAngle=-45, 
                    labelFontSize=11, 
                    grid=False,
                    labelFont="Inter",
                    titleFont="Inter"
                )
               ),
        y=alt.Y('Total Acumulado:Q',
                title='Capital Acumulado (R$)',
                axis=alt.Axis(
                    grid=False,
                    labelFont="Inter",
                    titleFont="Inter"
                )
               ),
        tooltip=[
            alt.Tooltip('DataFormatada', title="Data"), 
            alt.Tooltip('Total Acumulado:Q', format='R$ {,.2f}', title="Total Acumulado")
        ]
    ).properties(
        height=CHART_HEIGHT,
        title=alt.TitleParams(
            "Acúmulo de Capital",
            fontSize=18, 
            font="Inter",
            dy=-10, 
            anchor='middle'
        )
    ).configure_view(
        strokeWidth=0  # Remove a borda do gráfico
    )
    
    return line_chart

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
    
    # Adicionar emojis para os dias da semana
    dias_emoji_map = {
        0: "🔵 Segunda", # Segunda
        1: "🟠 Terça",   # Terça
        2: "🟢 Quarta",  # Quarta
        3: "🟣 Quinta",  # Quinta
        4: "🟡 Sexta",   # Sexta
        5: "⚪ Sábado"    # Sábado
    }
    vendas_media_dia['DiaSemanaEmoji'] = vendas_media_dia['DiaSemanaNum'].map(dias_emoji_map)
    
    bar_chart = alt.Chart(vendas_media_dia).mark_bar(
        cornerRadiusTopLeft=5, 
        cornerRadiusTopRight=5
    ).encode(
        x=alt.X('DiaSemanaEmoji:N', 
                title='Dia da Semana', 
                sort=alt.EncodingSortField(field="DiaSemanaNum", order='ascending'),
                axis=alt.Axis(labelFont="Inter", titleFont="Inter")),
        y=alt.Y('Total:Q', 
                title='Média de Vendas (R$)',
                axis=alt.Axis(labelFont="Inter", titleFont="Inter")),
        color=alt.Color('DiaSemanaEmoji:N', 
                       legend=None,
                       scale=alt.Scale(
                           range=['#4c78a8', '#f58518', '#54a24b', '#e45756', '#72b7b2', '#eeca3b']
                       )),
        tooltip=[
            alt.Tooltip('DiaSemana:N', title="Dia"), 
            alt.Tooltip('Total:Q', format='R$ {,.2f}', title="Média")
        ]
    ).properties(
        height=CHART_HEIGHT, 
        title=alt.TitleParams(
            text="Média de Vendas por Dia da Semana (Seg-Sáb)",
            fontSize=18, 
            font="Inter",
            dy=-10, 
            anchor='middle'
        )
    )
    
    text_on_bars = bar_chart.mark_text(
        dy=-10,
        color='white',
        font="Inter",
        fontWeight='bold'
    ).encode(
        text=alt.Text('Total:Q', format="R$ {,.0f}")
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
    
    # Adicionar emojis para os dias da semana
    dias_emoji_map = {
        0: "🔵 Segunda", # Segunda
        1: "🟠 Terça",   # Terça
        2: "🟢 Quarta",  # Quarta
        3: "🟣 Quinta",  # Quinta
        4: "🟡 Sexta",   # Sexta
        5: "⚪ Sábado"    # Sábado
    }
    vendas_total_dia['DiaSemanaEmoji'] = vendas_total_dia['DiaSemanaNum'].map(dias_emoji_map)
        
    vendas_total_dia['Porcentagem'] = (vendas_total_dia['Total'] / total_semanal_abs * 100)
    
    bar_chart = alt.Chart(vendas_total_dia).mark_bar(
        cornerRadiusTopLeft=5, 
        cornerRadiusTopRight=5
    ).encode(
        x=alt.X('DiaSemanaEmoji:N', 
                title='Dia da Semana', 
                sort=alt.EncodingSortField(field="DiaSemanaNum", order='ascending'),
                axis=alt.Axis(labelFont="Inter", titleFont="Inter")),
        y=alt.Y('Porcentagem:Q', 
                title='% do Volume Semanal',
                axis=alt.Axis(labelFont="Inter", titleFont="Inter")),
        color=alt.Color('DiaSemanaEmoji:N', 
                       legend=None,
                       scale=alt.Scale(
                           range=['#4c78a8', '#f58518', '#54a24b', '#e45756', '#72b7b2', '#eeca3b']
                       )),
        tooltip=[
            alt.Tooltip('DiaSemana:N', title="Dia"), 
            alt.Tooltip('Total:Q', format='R$ {,.2f}', title="Total"),
            alt.Tooltip('Porcentagem:Q', format='.1f', title="% do Total")
        ]
    ).properties(
        height=CHART_HEIGHT, 
        title=alt.TitleParams(
            text="Distribuição Semanal de Vendas (Seg-Sáb)",
            fontSize=18, 
            font="Inter",
            dy=-10, 
            anchor='middle'
        )
    )
    
    text_on_bars = bar_chart.mark_text(
        dy=-10,
        color='white',
        font="Inter",
        fontWeight='bold'
    ).encode(
        text=alt.Text('Porcentagem:Q', format='.1f') + "%"
    )
    
    return bar_chart + text_on_bars

# --- Função Principal ---
def main():
    # Aplicar estilo personalizado para o tema escuro
    st.markdown("""
    <style>
    /* Não estamos usando CSS personalizado, apenas ajustando o espaçamento */
    div.block-container {padding-top: 1rem;}
    </style>
    """, unsafe_allow_html=True)
    
    # Cabeçalho principal com ícone e título
    st.title("📊 Sistema de Registro de Vendas")
    
    # Lê os dados da planilha
    df_sales = read_sales_data()
    
    # Processa os dados para análise
    df_processed = process_data(df_sales)
    
    # Cria as abas com ícones mais descritivos
    tab1, tab2, tab3 = st.tabs([
        "📝 Registro de Vendas", 
        "📈 Análise Detalhada", 
        "📊 Estatísticas"
    ])
    
    with tab1:
        # Container para o formulário de registro
        with st.container():
            st.header("📝 Registro de Vendas")
            
            # Formulário para adicionar nova venda com design melhorado
            with st.form(key="sales_form", border=True):
                st.subheader("💰 Nova Venda")
                
                # Data com calendário mais visível
                col1, col2 = st.columns([1, 1])
                with col1:
                    data_input = st.date_input(
                        "📅 Data",
                        datetime.now(),
                        format="DD/MM/YYYY"
                    )
                
                # Valores com ícones e formatação monetária
                col1, col2, col3 = st.columns(3)
                with col1:
                    cartao_input = st.number_input(
                        "💳 Cartão (R$)",
                        min_value=0.0,
                        format="%.2f",
                        step=10.0
                    )
                with col2:
                    dinheiro_input = st.number_input(
                        "💵 Dinheiro (R$)",
                        min_value=0.0,
                        format="%.2f",
                        step=10.0
                    )
                with col3:
                    pix_input = st.number_input(
                        "📱 Pix (R$)",
                        min_value=0.0,
                        format="%.2f",
                        step=10.0
                    )
                
                # Total calculado para visualização
                total = cartao_input + dinheiro_input + pix_input
                st.metric(
                    label="💲 Total da Venda",
                    value=f"R$ {total:.2f}"
                )
                
                # Botão de submissão mais destacado
                submit_button = st.form_submit_button(
                    label="✅ Registrar Venda",
                    use_container_width=True,
                    type="primary"  # Destaca o botão
                )
                
                if submit_button:
                    if cartao_input > 0 or dinheiro_input > 0 or pix_input > 0:
                        formatted_date = data_input.strftime('%d/%m/%Y')
                        worksheet_obj = get_worksheet()
                        if add_data_to_sheet(formatted_date, cartao_input, dinheiro_input, pix_input, worksheet_obj):
                            read_sales_data.clear()  # Limpa o cache dos dados de vendas
                            process_data.clear()  # Limpa o cache dos dados processados
                            st.rerun()  # Força o recarregamento da app para refletir novos dados
                    else:
                        st.warning("⚠️ Pelo menos um valor de venda deve ser maior que zero.")

    # Prepara dados para abas de análise e estatística
    # Filtros na sidebar (afetam Tab2 e Tab3)
    selected_anos_filter = []
    selected_meses_filter = []

    with st.sidebar:
        # Melhorar o design da sidebar
        st.sidebar.image("https://img.icons8.com/fluency/96/analytics.png", width=80)
        st.sidebar.title("Controles")
        
        # Separador visual
        st.sidebar.divider()
        
        # Filtros com design melhorado
        st.sidebar.header("🔍 Filtros de Dados")
        
        if not df_processed.empty and 'Ano' in df_processed.columns and not df_processed['Ano'].dropna().empty:
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            anos_disponiveis = sorted(df_processed['Ano'].dropna().unique().astype(int))
            default_anos = [current_year] if current_year in anos_disponiveis else anos_disponiveis
            
            # Filtro de anos com ícone
            selected_anos_filter = st.multiselect(
                "📅 Selecione o(s) Ano(s):",
                options=anos_disponiveis,
                default=default_anos
            )

            if selected_anos_filter:
                df_para_filtro_mes = df_processed[df_processed['Ano'].isin(selected_anos_filter)]
                if not df_para_filtro_mes.empty and 'Mês' in df_para_filtro_mes.columns and not df_para_filtro_mes['Mês'].dropna().empty:
                    meses_numeros_disponiveis = sorted(df_para_filtro_mes['Mês'].dropna().unique().astype(int))
                    # Gera nomes dos meses com base no locale
                    meses_nomes_map = {m: datetime(2000, m, 1).strftime('%B').capitalize() for m in meses_numeros_disponiveis}
                    meses_opcoes = [f"{m} - {meses_nomes_map[m]}" for m in meses_numeros_disponiveis]
                    
                    default_mes_opcao_str = f"{current_month} - {datetime(2000, current_month, 1).strftime('%B').capitalize()}"
                    default_meses_selecionados = [default_mes_opcao_str] if default_mes_opcao_str in meses_opcoes else meses_opcoes
                    
                    # Filtro de meses com ícone
                    selected_meses_str = st.multiselect(
                        "📆 Selecione o(s) Mês(es):",
                        options=meses_opcoes,
                        default=default_meses_selecionados
                    )
                    selected_meses_filter = [int(m.split(" - ")[0]) for m in selected_meses_str]
        else:
            st.sidebar.info("ℹ️ Não há dados suficientes para aplicar filtros de data.")
        
        # Adicionar informações úteis na sidebar
        st.sidebar.divider()
        st.sidebar.caption("Sistema de Registro de Vendas v1.0")
        st.sidebar.caption("© 2025 - Todos os direitos reservados")

    # Aplicar filtros aos dados processados
    df_filtered = df_processed.copy()
    if not df_filtered.empty:
        if selected_anos_filter and 'Ano' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos_filter)]
        if selected_meses_filter and 'Mês' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses_filter)]
    
    with tab2:
        st.header("📈 Análise Detalhada de Vendas")
        
        if not df_filtered.empty and 'DataFormatada' in df_filtered.columns:
            # Resumo dos dados filtrados
            with st.container():
                # Métricas principais em destaque
                total_vendas = len(df_filtered)
                total_valor = df_filtered['Total'].sum()
                media_valor = df_filtered['Total'].mean() if total_vendas > 0 else 0
                
                # Exibir métricas em cards
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        label="🧾 Total de Registros",
                        value=f"{total_vendas}"
                    )
                with col2:
                    st.metric(
                        label="💰 Valor Total",
                        value=f"R$ {total_valor:,.2f}"
                    )
                with col3:
                    st.metric(
                        label="📊 Média por Venda",
                        value=f"R$ {media_valor:,.2f}"
                    )
            
            # Separador visual
            st.divider()
            
            # Dados detalhados em um expander
            with st.expander("📋 Ver Dados Detalhados", expanded=False):
                # Melhorar a visualização da tabela
                st.dataframe(
                    df_filtered[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']].style.format({
                        'Cartão': 'R$ {:.2f}',
                        'Dinheiro': 'R$ {:.2f}',
                        'Pix': 'R$ {:.2f}',
                        'Total': 'R$ {:.2f}'
                    }),
                    use_container_width=True,
                    height=300,
                    column_config={
                        "DataFormatada": "Data",
                        "Cartão": st.column_config.NumberColumn("💳 Cartão", format="R$ %.2f"),
                        "Dinheiro": st.column_config.NumberColumn("💵 Dinheiro", format="R$ %.2f"),
                        "Pix": st.column_config.NumberColumn("📱 Pix", format="R$ %.2f"),
                        "Total": st.column_config.NumberColumn("💰 Total", format="R$ %.2f")
                    },
                    hide_index=True
                )
            
            # Gráficos em containers separados
            st.subheader("💳 Distribuição por Método de Pagamento")
            pie_chart = create_pie_chart_payment_methods(df_filtered)
            if pie_chart:
                st.altair_chart(pie_chart, use_container_width=True, theme=None)
            else:
                st.info("ℹ️ Não há dados suficientes para gerar o gráfico de métodos de pagamento.")

            st.subheader("📅 Vendas Diárias por Método")
            daily_chart = create_daily_sales_bar_chart(df_filtered)
            if daily_chart:
                st.altair_chart(daily_chart, use_container_width=True, theme=None)
            else:
                st.info("ℹ️ Não há dados suficientes para gerar o gráfico de vendas diárias.")

            st.subheader("📈 Acúmulo de Capital")
            capital_chart = create_accumulated_capital_line_chart(df_filtered)
            if capital_chart:
                st.altair_chart(capital_chart, use_container_width=True, theme=None)
            else:
                st.info("ℹ️ Não há dados suficientes para gerar o gráfico de acúmulo de capital.")
        else:
            # Mensagem amigável quando não há dados
            st.info("ℹ️ Não há dados para exibir na Análise Detalhada ou os dados filtrados estão vazios.")
            st.markdown("Adicione registros na aba **📝 Registro de Vendas** para visualizar análises.")

    with tab3:
        st.header("📊 Estatísticas de Vendas")
        
        if not df_filtered.empty and 'Total' in df_filtered.columns:
            # Container para resumo financeiro
            with st.container():
                st.subheader("💰 Resumo Financeiro")
                
                # Calcular métricas
                total_vendas = len(df_filtered)
                total_faturamento = df_filtered['Total'].sum()
                media_por_venda = df_filtered['Total'].mean() if total_vendas > 0 else 0
                maior_venda = df_filtered['Total'].max() if total_vendas > 0 else 0
                menor_venda = df_filtered['Total'].min() if total_vendas > 0 else 0
                
                # Exibir métricas em cards com melhor organização
                col1, col2 = st.columns(2)
                with col1:
                    # Card para total de vendas
                    with st.container(border=True):
                        st.markdown("### 🧾 Total de Vendas")
                        st.markdown(f"## {total_vendas}")
                with col2:
                    # Card para faturamento
                    with st.container(border=True):
                        st.markdown("### 💵 Faturamento Total")
                        st.markdown(f"## R$ {total_faturamento:,.2f}")
                
                col1, col2 = st.columns(2)
                with col1:
                    # Card para média por venda
                    with st.container(border=True):
                        st.markdown("### 📊 Média por Venda")
                        st.markdown(f"## R$ {media_por_venda:,.2f}")
                with col2:
                    # Card para maior venda
                    with st.container(border=True):
                        st.markdown("### ⬆️ Maior Venda")
                        st.markdown(f"## R$ {maior_venda:,.2f}")
                
                # Card para menor venda
                with st.container(border=True):
                    st.markdown("### ⬇️ Menor Venda")
                    st.markdown(f"## R$ {menor_venda:,.2f}")
            
            # Separador visual
            st.divider()
            
            # Container para métodos de pagamento
            with st.container():
                st.subheader("💳 Métodos de Pagamento")
                
                # Calcular valores e percentuais
                cartao_total = df_filtered['Cartão'].sum()
                dinheiro_total = df_filtered['Dinheiro'].sum()
                pix_total = df_filtered['Pix'].sum()
                total_pagamentos = cartao_total + dinheiro_total + pix_total
                
                cartao_pct = (cartao_total / total_pagamentos * 100) if total_pagamentos > 0 else 0
                dinheiro_pct = (dinheiro_total / total_pagamentos * 100) if total_pagamentos > 0 else 0
                pix_pct = (pix_total / total_pagamentos * 100) if total_pagamentos > 0 else 0
                
                # Exibir cards de métodos de pagamento
                payment_cols = st.columns(3)
                with payment_cols[0]:
                    with st.container(border=True):
                        st.markdown("### 💳 Cartão")
                        st.markdown(f"#### R$ {cartao_total:,.2f}")
                        st.progress(cartao_pct/100)
                        st.caption(f"{cartao_pct:.1f}% do total")
                with payment_cols[1]:
                    with st.container(border=True):
                        st.markdown("### 💵 Dinheiro")
                        st.markdown(f"#### R$ {dinheiro_total:,.2f}")
                        st.progress(dinheiro_pct/100)
                        st.caption(f"{dinheiro_pct:.1f}% do total")
                with payment_cols[2]:
                    with st.container(border=True):
                        st.markdown("### 📱 PIX")
                        st.markdown(f"#### R$ {pix_total:,.2f}")
                        st.progress(pix_pct/100)
                        st.caption(f"{pix_pct:.1f}% do total")
                
                # Gráfico de pizza para métodos de pagamento
                if total_pagamentos > 0:
                    pie_chart = create_pie_chart_payment_methods(df_filtered)
                    if pie_chart:
                        st.altair_chart(pie_chart, use_container_width=True, theme=None)
            
            # Separador visual
            st.divider()
            
            # Container para análise temporal
            with st.container():
                st.subheader("📅 Análise Temporal")
                
                if total_vendas > 1 and 'Data' in df_filtered.columns and 'DiaSemana' in df_filtered.columns:
                    # Determinar método preferido
                    metodo_preferido = "Cartão" if cartao_total >= max(dinheiro_total, pix_total) else \
                                      "Dinheiro" if dinheiro_total >= max(cartao_total, pix_total) else "PIX"
                    emoji_metodo = "💳" if metodo_preferido == "Cartão" else "💵" if metodo_preferido == "Dinheiro" else "📱"
                    
                    # Calcular métricas temporais
                    dias_distintos = df_filtered['Data'].nunique()
                    media_diaria = total_faturamento / dias_distintos if dias_distintos > 0 else 0
                    
                    dia_mais_vendas = df_filtered.groupby('DiaSemana')['Total'].sum().idxmax() if not df_filtered.empty else "N/A"
                    
                    # Exibir cards de análise temporal
                    stats_cols_temporal = st.columns(3)
                    with stats_cols_temporal[0]:
                        with st.container(border=True):
                            st.markdown(f"### {emoji_metodo} Método Preferido")
                            st.markdown(f"## {metodo_preferido}")
                    
                    with stats_cols_temporal[1]:
                        with st.container(border=True):
                            st.markdown("### 📊 Média Diária")
                            st.markdown(f"## R$ {media_diaria:,.2f}")
                    
                    with stats_cols_temporal[2]:
                        with st.container(border=True):
                            st.markdown("### 📆 Dia com Mais Vendas")
                            st.markdown(f"## {dia_mais_vendas}")
                    
                    # Gráficos de análise por dia da semana
                    weekday_chart = create_avg_sales_by_weekday_bar_chart(df_filtered)
                    if weekday_chart:
                        st.altair_chart(weekday_chart, use_container_width=True, theme=None)
                    
                    seasonality_chart = create_weekly_seasonality_bar_chart(df_filtered)
                    if seasonality_chart:
                        st.altair_chart(seasonality_chart, use_container_width=True, theme=None)
                    
                    # Análise de melhor e pior dia
                    if 'DiaSemana' in df_filtered.columns:
                        vendas_por_dia = df_filtered.groupby('DiaSemana')['Total'].sum().reset_index()
                        if not vendas_por_dia.empty:
                            melhor_dia = vendas_por_dia.loc[vendas_por_dia['Total'].idxmax()]
                            pior_dia = vendas_por_dia.loc[vendas_por_dia['Total'].idxmin()]
                            
                            best_worst_cols = st.columns(2)
                            with best_worst_cols[0]:
                                with st.container(border=True):
                                    st.markdown("### 🔝 Melhor Dia da Semana")
                                    st.markdown(f"## {melhor_dia['DiaSemana']}")
                                    st.caption(f"Total: R$ {melhor_dia['Total']:,.2f}")
                            with best_worst_cols[1]:
                                with st.container(border=True):
                                    st.markdown("### 🔻 Pior Dia da Semana")
                                    st.markdown(f"## {pior_dia['DiaSemana']}")
                                    st.caption(f"Total: R$ {pior_dia['Total']:,.2f}")
                
                # Análise de tendência mensal
                if 'AnoMês' in df_filtered.columns and df_filtered['AnoMês'].nunique() > 1:
                    st.subheader("📈 Tendência Mensal")
                    
                    vendas_mensais = df_filtered.groupby('AnoMês')['Total'].sum().reset_index()
                    if len(vendas_mensais) >= 2:
                        ultimo_mes_val = vendas_mensais.iloc[-1]['Total']
                        penultimo_mes_val = vendas_mensais.iloc[-2]['Total']
                        variacao = ((ultimo_mes_val - penultimo_mes_val) / penultimo_mes_val * 100) if penultimo_mes_val > 0 else 0
                        emoji_tendencia = "🚀" if variacao > 10 else "📈" if variacao > 0 else "📉" if variacao < 0 else "➡️"
                        
                        # Card para variação mensal
                        with st.container(border=True):
                            st.markdown(f"### {emoji_tendencia} Variação do Último Mês")
                            st.markdown(f"## {variacao:.1f}%")
                            st.caption(f"{'Aumento' if variacao >= 0 else 'Redução'} de R$ {abs(ultimo_mes_val - penultimo_mes_val):,.2f}")
                        
                        # Gráfico de tendência mensal
                        chart_tendencia = alt.Chart(vendas_mensais).mark_line(
                            point=True,
                            strokeWidth=3
                        ).encode(
                            x=alt.X('AnoMês:N', 
                                   title='Mês',
                                   axis=alt.Axis(labelAngle=-45, labelFont="Inter", titleFont="Inter")),
                            y=alt.Y('Total:Q', 
                                   title='Total de Vendas (R$)',
                                   axis=alt.Axis(labelFont="Inter", titleFont="Inter")),
                            tooltip=[
                                alt.Tooltip('AnoMês:N', title="Mês"), 
                                alt.Tooltip('Total:Q', format='R$ {,.2f}', title="Total")
                            ]
                        ).properties(
                            title=alt.TitleParams(
                                "Tendência de Vendas Mensais",
                                fontSize=18, 
                                font="Inter",
                                dy=-10, 
                                anchor='middle'
                            ),
                            height=400
                        )
                        st.altair_chart(chart_tendencia, use_container_width=True, theme=None)
        else:
            # Mensagem amigável quando não há dados
            st.info("ℹ️ Não há dados para exibir na aba Estatísticas ou os dados filtrados estão vazios.")
            st.markdown("Adicione registros na aba **📝 Registro de Vendas** para visualizar estatísticas.")

if __name__ == "__main__":
    main()
