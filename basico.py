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

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="centered")

# Configura o locale para Português do Brasil para formatação de datas e nomes
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')  # Alternativa para Windows
    except locale.Error:
        st.warning("Locale pt_BR não encontrado. Nomes de meses/dias podem aparecer em inglês.")

# CSS específico para a seção de resumo
st.markdown("""
    /* Estilo para os containers da seção de resumo */
    .resume-kpi-container {
        border: 1px solid #4A4A4A;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        text-align: center;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    .resume-kpi-container:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    /* Ajuste para o st.metric dentro desses containers específicos */
    .resume-kpi-container div[data-testid="stMetric"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    .resume-kpi-container div[data-testid="stMetricLabel"] {
        font-size: 0.9em;
    }
    .resume-kpi-container div[data-testid="stMetricValue"] {
        font-size: 1.5em;
        font-weight: bold;
    }
    
    /* Estilo específico para as tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f0f0;
        border-radius: 4px 4px 0 0;
        padding: 10px 16px;
        border: 1px solid #e0e0e0;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #4A4A4A;
        color: white;
    }
    
    /* Estilo específico para os resumos nas tabs 2 e 3 */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"]:has(div:contains("Análise Detalhada")) .stDataFrame,
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"]:has(div:contains("Estatísticas")) .stMetric {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    
    /* Estilo para os gráficos nas tabs */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"]:has(div:contains("Análise Detalhada")) [data-testid="element-container"],
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"]:has(div:contains("Estatísticas")) [data-testid="element-container"] {
        background-color: #fafafa;
        border-radius: 8px;
        padding: 5px;
        margin-top: 10px;
    }
    
    /* Estilo específico para os containers de KPI nas tabs 2 e 3 */
    .tab2-kpi-container, .tab3-kpi-container {
        background-color: #f9f9f9;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    
    .tab2-kpi-container:hover, .tab3-kpi-container:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border-color: #aaa;
    }
    
    /* Estilo para tabelas de dados nas tabs 2 e 3 */
    .tab2-data-table, .tab3-data-table {
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 20px;
    }
    
    .tab2-data-table th, .tab3-data-table th {
        background-color: #4A4A4A;
        color: white;
        padding: 12px;
        text-align: left;
    }
    
    .tab2-data-table td, .tab3-data-table td {
        padding: 10px;
        border-bottom: 1px solid #ddd;
    }
    
    .tab2-data-table tr:nth-child(even), .tab3-data-table tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    
    /* Estilo para gráficos específicos nas tabs 2 e 3 */
    .tab2-chart-container, .tab3-chart-container {
        background-color: white;
        border: 1px solid #eaeaea;
        border-radius: 8px;
        padding: 15px;
        margin-top: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
""", unsafe_allow_html=True)

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

    pie_chart = alt.Chart(payment_sum).mark_arc(innerRadius=50).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
        tooltip=[
            alt.Tooltip("Método:N"),
            alt.Tooltip("Valor:Q", format="R$,.2f", title="Valor"),
            alt.Tooltip("Porcentagem:Q", format=".1f", title="% do Total")
        ]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams("Distribuição por Método de Pagamento", fontSize=16, dy=-10, anchor='middle'))
    
    text_values = pie_chart.mark_text(radius=105, size=14, fontWeight='bold').encode(
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

    bar_chart = alt.Chart(daily_data).mark_bar(size=20).encode(
        x=alt.X('DataFormatada:N', 
                title='Data', 
                axis=alt.Axis(labelAngle=-45), 
                sort=alt.EncodingSortField(field="Data", op="min", order='ascending')),
        y=alt.Y('Valor:Q', title='Valor (R$)', stack='zero'),
        color=alt.Color('Método:N', legend=alt.Legend(title="Método")),
        tooltip=['DataFormatada', 'Método', alt.Tooltip('Valor:Q', format='R$,.2f')]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams("Vendas Diárias por Método", fontSize=16, dy=-10, anchor='middle'))
    
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
        line={'color':'steelblue', 'strokeWidth': 2},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='rgba(70,130,180,0.1)', offset=0.3), 
                   alt.GradientStop(color='rgba(70,130,180,0.7)', offset=1)],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X('Data:T', title='Data', axis=alt.Axis(format="%d/%m/%y")),
        y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
        tooltip=[
            alt.Tooltip('DataFormatada', title="Data"), 
            alt.Tooltip('Total Acumulado:Q', format='R$,.2f')
        ]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams("Acúmulo de Capital", fontSize=16, dy=-10, anchor='middle'))
    
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
    
    bar_chart = alt.Chart(vendas_media_dia).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X('DiaSemana:N', title='Dia da Semana', sort=alt.EncodingSortField(field="DiaSemanaNum", order='ascending')),
        y=alt.Y('Total:Q', title='Média de Vendas (R$)'),
        color=alt.Color('DiaSemana:N', legend=None),
        tooltip=[alt.Tooltip('DiaSemana:N', title="Dia"), alt.Tooltip('Total:Q', format='R$,.2f', title="Média")]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams(text="Média de Vendas por Dia da Semana (Seg-Sáb)", fontSize=16, dy=-10, anchor='middle'))
    
    text_on_bars = bar_chart.mark_text(dy=-10).encode(text=alt.Text('Total:Q', format="R$,.0f"))
    
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
    total_vendas = vendas_total_dia['Total'].sum()
    
    if total_vendas == 0:
        return None
        
    vendas_total_dia['Porcentagem'] = (vendas_total_dia['Total'] / total_vendas) * 100
    
    bar_chart = alt.Chart(vendas_total_dia).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X('DiaSemana:N', title='Dia da Semana', sort=alt.EncodingSortField(field="DiaSemanaNum", order='ascending')),
        y=alt.Y('Porcentagem:Q', title='% do Volume Semanal'),
        color=alt.Color('DiaSemana:N', legend=None),
        tooltip=[
            alt.Tooltip('DiaSemana:N', title="Dia"), 
            alt.Tooltip('Total:Q', format='R$,.2f', title="Total"),
            alt.Tooltip('Porcentagem:Q', format='.1f', title="% do Total")
        ]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams(text="Distribuição Semanal de Vendas (Seg-Sáb)", fontSize=16, dy=-10, anchor='middle'))
    
    text_on_bars = bar_chart.mark_text(dy=-10).encode(text=alt.Text('Porcentagem:Q', format='.1f') + "%")
    
    return bar_chart + text_on_bars

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
            
            # Aplicando o CSS para o container de dados na tab2
            st.markdown('<div class="tab2-kpi-container">', unsafe_allow_html=True)
            st.dataframe(df_filtered[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']], use_container_width=True, height=300)
            st.markdown('</div>', unsafe_allow_html=True)

            st.subheader("Distribuição por Método de Pagamento")
            
            # Aplicando o CSS para o container de gráfico na tab2
            st.markdown('<div class="tab2-chart-container">', unsafe_allow_html=True)
            payment_filtered_data = pd.DataFrame({
                'Método': ['Cartão', 'Dinheiro', 'PIX'],
                'Valor': [df_filtered['Cartão'].sum(), df_filtered['Dinheiro'].sum(), df_filtered['Pix'].sum()]
            })
            pie_chart = alt.Chart(payment_filtered_data).mark_arc(innerRadius=50).encode(
                theta=alt.Theta("Valor:Q", stack=True),
                color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
                tooltip=["Método", "Valor"]
            ).properties(width=700, height=500)
            text = pie_chart.mark_text(radius=120, size=16).encode(text="Valor:Q")
            st.altair_chart(pie_chart + text, use_container_width=True, theme="streamlit")
            st.markdown('</div>', unsafe_allow_html=True)

            st.subheader("Vendas Diárias por Método de Pagamento")
            
            # Aplicando o CSS para o container de gráfico na tab2
            st.markdown('<div class="tab2-chart-container">', unsafe_allow_html=True)
            daily_data = df_filtered.melt(id_vars=['DataFormatada'], value_vars=['Cartão', 'Dinheiro', 'Pix'], var_name='Método', value_name='Valor')
            bar_chart = alt.Chart(daily_data).mark_bar(size=20).encode(
                x=alt.X('DataFormatada:N', title='Data', axis=alt.Axis(labelAngle=-45), sort=alt.EncodingSortField(field="DataFormatada", op="min", order='ascending')),
                y=alt.Y('Valor:Q', title='Valor (R$)'),
                color=alt.Color('Método:N', legend=alt.Legend(title="Método")),
                tooltip=['DataFormatada', 'Método', 'Valor']
            ).properties(width=700, height=500)
            st.altair_chart(bar_chart, use_container_width=True, theme="streamlit")
            st.markdown('</div>', unsafe_allow_html=True)

            st.subheader("Acúmulo de Capital ao Longo do Tempo")
            
            # Aplicando o CSS para o container de gráfico na tab2
            st.markdown('<div class="tab2-chart-container">', unsafe_allow_html=True)
            if 'Data' in df_filtered.columns:
                df_accumulated = df_filtered.sort_values('Data').copy()
                df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()
                line_chart = alt.Chart(df_accumulated).mark_line(point=True, strokeWidth=3).encode(
                    x=alt.X('Data:T', title='Data'),
                    y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
                    tooltip=['DataFormatada', 'Total Acumulado']
                ).properties(width=700, height=500)
                st.altair_chart(line_chart, use_container_width=True, theme="streamlit")
            else:
                st.info("Coluna 'Data' não encontrada para gráfico de acúmulo.")
            st.markdown('</div>', unsafe_allow_html=True)
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

            # Aplicando o CSS para os containers de KPI na tab3
            cols1 = st.columns(2)
            with cols1[0]:
                st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                st.metric("🔢 Total de Vendas", f"{total_vendas}")
                st.markdown('</div>', unsafe_allow_html=True)
            with cols1[1]:
                st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                st.metric("💵 Faturamento Total", f"R$ {total_faturamento:,.2f}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            cols2 = st.columns(2)
            with cols2[0]:
                st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                st.metric("📈 Média por Venda", f"R$ {media_por_venda:,.2f}")
                st.markdown('</div>', unsafe_allow_html=True)
            with cols2[1]:
                st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                st.metric("⬆️ Maior Venda", f"R$ {maior_venda:,.2f}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            cols3 = st.columns(1)
            with cols3[0]:
                st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                st.metric("⬇️ Menor Venda", f"R$ {menor_venda:,.2f}")
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("💳 Métodos de Pagamento")
            cartao_total = df_filtered['Cartão'].sum()
            dinheiro_total = df_filtered['Dinheiro'].sum()
            pix_total = df_filtered['Pix'].sum()
            total_pagamentos = cartao_total + dinheiro_total + pix_total
            cartao_pct = (cartao_total / total_pagamentos * 100) if total_pagamentos > 0 else 0
            dinheiro_pct = (dinheiro_total / total_pagamentos * 100) if total_pagamentos > 0 else 0
            pix_pct = (pix_total / total_pagamentos * 100) if total_pagamentos > 0 else 0

            # Aplicando o CSS para os containers de métodos de pagamento na tab3
            payment_cols = st.columns(3)
            with payment_cols[0]:
                st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                st.markdown(f"**💳 Cartão:** R$ {cartao_total:.2f} ({cartao_pct:.1f}%)")
                st.markdown('</div>', unsafe_allow_html=True)
            with payment_cols[1]:
                st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                st.markdown(f"**💵 Dinheiro:** R$ {dinheiro_total:.2f} ({dinheiro_pct:.1f}%)")
                st.markdown('</div>', unsafe_allow_html=True)
            with payment_cols[2]:
                st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                st.markdown(f"**📱 PIX:** R$ {pix_total:.2f} ({pix_pct:.1f}%)")
                st.markdown('</div>', unsafe_allow_html=True)

            if total_pagamentos > 0:
                # Aplicando o CSS para o container de gráfico na tab3
                st.markdown('<div class="tab3-chart-container">', unsafe_allow_html=True)
                payment_data_stats = pd.DataFrame({'Método': ['Cartão', 'Dinheiro', 'PIX'], 'Valor': [cartao_total, dinheiro_total, pix_total]})
                pie_chart_stats = alt.Chart(payment_data_stats).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta("Valor:Q", stack=True), color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
                    tooltip=["Método", "Valor"]
                ).properties(height=500)
                text_stats = pie_chart_stats.mark_text(radius=120, size=16).encode(text="Valor:Q")
                st.altair_chart(pie_chart_stats + text_stats, use_container_width=True, theme="streamlit")
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.subheader("📅 Análise Temporal")
            if total_vendas > 1 and 'Data' in df_filtered.columns and 'DiaSemana' in df_filtered.columns:
                metodo_preferido = "Cartão" if cartao_total >= max(dinheiro_total, pix_total) else \
                                  "Dinheiro" if dinheiro_total >= max(cartao_total, pix_total) else "PIX"
                emoji_metodo = "💳" if metodo_preferido == "Cartão" else "💵" if metodo_preferido == "Dinheiro" else "📱"
                
                # Aplicando o CSS para os containers de análise temporal na tab3
                stats_cols_temporal = st.columns(3)
                with stats_cols_temporal[0]:
                    st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                    st.markdown(f"**{emoji_metodo} Método Preferido:** {metodo_preferido}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                dias_distintos = df_filtered['Data'].nunique()
                media_diaria = total_faturamento / dias_distintos if dias_distintos > 0 else 0
                with stats_cols_temporal[1]:
                    st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                    st.markdown(f"**📊 Média Diária:** R$ {media_diaria:.2f}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                dia_mais_vendas = df_filtered.groupby('DiaSemana')['Total'].sum().idxmax() if not df_filtered.empty else "N/A"
                with stats_cols_temporal[2]:
                    st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                    st.markdown(f"**📆 Dia com Mais Vendas:** {dia_mais_vendas}")
                    st.markdown('</div>', unsafe_allow_html=True)

                # Gráfico de média por dia da semana (Seg-Sáb, usando locale)
                dias_uteis_nomes_locale = [datetime(2000, 1, i).strftime('%A').capitalize() for i in range(3, 3+6)]  # Seg a Sáb
                df_dias_uteis = df_filtered[df_filtered['DiaSemana'].isin(dias_uteis_nomes_locale)]
                if not df_dias_uteis.empty:
                    # Aplicando o CSS para o container de gráfico na tab3
                    st.markdown('<div class="tab3-chart-container">', unsafe_allow_html=True)
                    vendas_por_dia_uteis = df_dias_uteis.groupby('DiaSemana')['Total'].mean().reset_index()
                    # Garantir a ordem correta dos dias da semana no gráfico
                    dias_ordem_numerica = list(range(6))  # 0=Segunda, ..., 5=Sábado
                    nomes_dias_map = {i: (datetime(2000,1,3) + timedelta(days=i)).strftime('%A').capitalize() for i in dias_ordem_numerica}
                    dias_ordem_locale = [nomes_dias_map[i] for i in dias_ordem_numerica]
                    
                    vendas_por_dia_uteis['DiaSemanaOrdem'] = vendas_por_dia_uteis['DiaSemana'].map({dia: i for i, dia in enumerate(dias_ordem_locale)})
                    vendas_por_dia_uteis = vendas_por_dia_uteis.sort_values('DiaSemanaOrdem')

                    chart_dias_uteis = alt.Chart(vendas_por_dia_uteis).mark_bar().encode(
                        x=alt.X('DiaSemana:N', title='Dia da Semana', sort=dias_ordem_locale),
                        y=alt.Y('Total:Q', title='Média de Vendas (R$)'),
                        tooltip=['DiaSemana', 'Total']
                    ).properties(title='Média de Vendas por Dia da Semana (Seg-Sáb)', height=500)
                    st.altair_chart(chart_dias_uteis, use_container_width=True, theme="streamlit")
                    st.markdown('</div>', unsafe_allow_html=True)
            
            if 'AnoMês' in df_filtered.columns and df_filtered['AnoMês'].nunique() > 1:
                st.subheader("📈 Tendência Mensal")
                vendas_mensais = df_filtered.groupby('AnoMês')['Total'].sum().reset_index()
                if len(vendas_mensais) >= 2:
                    ultimo_mes_val = vendas_mensais.iloc[-1]['Total']
                    penultimo_mes_val = vendas_mensais.iloc[-2]['Total']
                    variacao = ((ultimo_mes_val - penultimo_mes_val) / penultimo_mes_val * 100) if penultimo_mes_val > 0 else 0
                    emoji_tendencia = "🚀" if variacao > 10 else "📈" if variacao > 0 else "📉" if variacao < 0 else "➡️"
                    
                    # Aplicando o CSS para o container de tendência mensal na tab3
                    st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                    st.markdown(f"**{emoji_tendencia} Variação do último mês:** {variacao:.1f}% ({'-' if variacao < 0 else '+'} R$ {abs(ultimo_mes_val - penultimo_mes_val):.2f})")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Aplicando o CSS para o container de gráfico na tab3
                    st.markdown('<div class="tab3-chart-container">', unsafe_allow_html=True)
                    chart_tendencia = alt.Chart(vendas_mensais).mark_line(point=True).encode(
                        x=alt.X('AnoMês:N', title='Mês'),
                        y=alt.Y('Total:Q', title='Total de Vendas (R$)'),
                        tooltip=['AnoMês', 'Total']
                    ).properties(title='Tendência de Vendas Mensais', height=400)
                    st.altair_chart(chart_tendencia, use_container_width=True, theme="streamlit")
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # Sazonalidade semanal
            if 'DiaSemana' in df_filtered.columns and 'DiaSemanaNum' in df_filtered.columns and len(df_filtered) > 6:
                dias_ordem_numerica = list(range(6))  # 0=Segunda, ..., 5=Sábado
                nomes_dias_map = {i: (datetime(2000,1,3) + timedelta(days=i)).strftime('%A').capitalize() for i in dias_ordem_numerica}
                dias_ordem_locale = [nomes_dias_map[i] for i in dias_ordem_numerica]
                
                df_dias_trabalho = df_filtered[df_filtered['DiaSemanaNum'].isin(dias_ordem_numerica)]
                if not df_dias_trabalho.empty:
                    vendas_dia_semana_total = df_dias_trabalho.groupby(['DiaSemanaNum', 'DiaSemana'])['Total'].sum().reset_index()
                    total_semanal_abs = vendas_dia_semana_total['Total'].sum()
                    
                    if total_semanal_abs > 0:
                        vendas_dia_semana_total['Porcentagem'] = (vendas_dia_semana_total['Total'] / total_semanal_abs * 100)
                        
                        # Aplicando o CSS para o container de gráfico na tab3
                        st.markdown('<div class="tab3-chart-container">', unsafe_allow_html=True)
                        chart_sazonalidade = alt.Chart(vendas_dia_semana_total).mark_bar().encode(
                            x=alt.X('DiaSemana:N', title='Dia da Semana', sort=alt.EncodingSortField(field="DiaSemanaNum", order='ascending')),
                            y=alt.Y('Porcentagem:Q', title='% do Volume Semanal'),
                            color=alt.Color('DiaSemana:N', legend=None),
                            tooltip=['DiaSemana', 'Total', 'Porcentagem']
                        ).properties(title='Distribuição Semanal de Vendas (Seg-Sáb)', height=500)
                        st.altair_chart(chart_sazonalidade, use_container_width=True, theme="streamlit")
                        st.markdown('</div>', unsafe_allow_html=True)

                        melhor_dia_df = vendas_dia_semana_total.loc[vendas_dia_semana_total['Total'].idxmax()]
                        pior_dia_df = vendas_dia_semana_total.loc[vendas_dia_semana_total['Total'].idxmin()]
                        
                        # Aplicando o CSS para os containers de melhor/pior dia na tab3
                        best_worst_cols = st.columns(2)
                        with best_worst_cols[0]:
                            st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                            st.markdown(f"**🔝 Melhor dia:** {melhor_dia_df['DiaSemana']} ({melhor_dia_df['Porcentagem']:.1f}% do total)")
                            st.markdown('</div>', unsafe_allow_html=True)
                        with best_worst_cols[1]:
                            st.markdown('<div class="tab3-kpi-container">', unsafe_allow_html=True)
                            st.markdown(f"**🔻 Pior dia:** {pior_dia_df['DiaSemana']} ({pior_dia_df['Porcentagem']:.1f}% do total)")
                            st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.info("Não há dados para exibir na aba Estatísticas ou os dados filtrados estão vazios.")

if __name__ == "__main__":
    main()
