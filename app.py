import streamlit as st
import pandas as pd
import numpy as np
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, DataTable, TableColumn
from bokeh.models.widgets import NumberFormatter
from bokeh.palettes import Category10, Spectral6
from bokeh.transform import cumsum
from math import pi

# Configuração da página
st.set_page_config(
    page_title="Sistema de Registro de Vendas", 
    layout="centered",
    initial_sidebar_state="expanded"
)

# CSS para resumo em 2 colunas
st.markdown("""
<style>
    .resumo-container {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
        margin-bottom: 25px;
    }
    .resumo-item {
        background-color: #1e1e1e;
        color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333333;
    }
    .resumo-titulo {
        font-size: 1.1em;
        color: #4dabf7;
        margin-bottom: 10px;
        font-weight: 600;
    }
    .resumo-valor {
        font-size: 1.8em;
        color: #ffffff;
        font-weight: 700;
    }
    [data-testid="stElementToolbar"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def read_google_sheet():
    """Função para ler os dados da planilha Google Sheets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 
                 'https://www.googleapis.com/auth/spreadsheets.readonly', 
                 'https://www.googleapis.com/auth/drive.readonly']
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
        worksheet_name = 'Vendas'
        try:
            with st.spinner("Conectando à planilha..."):
                spreadsheet = gc.open_by_key(spreadsheet_id)
                worksheet = spreadsheet.worksheet(worksheet_name)
                rows = worksheet.get_all_records()
                df = pd.DataFrame(rows)
                return df, worksheet
        except SpreadsheetNotFound:
            st.error(f"Planilha com ID {spreadsheet_id} não encontrada.")
            return pd.DataFrame(), None
    except Exception as e:
        st.error(f"Erro de autenticação: {e}")
        return pd.DataFrame(), None

def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet):
    """Função para adicionar dados à planilha Google Sheets"""
    if worksheet is None:
        st.error("Não foi possível acessar a planilha.")
        return False
    try:
        with st.spinner("Registrando venda..."):
            new_row = [date, float(cartao), float(dinheiro), float(pix)]
            worksheet.append_row(new_row)
            st.toast("Venda registrada com sucesso!", icon="✅")
            return True
    except Exception as e:
        st.error(f"Erro ao adicionar dados: {e}")
        return False

@st.cache_data(ttl=300)
def process_data(df_raw):
    """Função para processar e preparar os dados"""
    if df_raw.empty:
        return pd.DataFrame()
    
    df = df_raw.copy()
    
    # Processamento dos valores monetários
    for col in ['Cartão', 'Dinheiro', 'Pix']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Cálculo do total
    df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']
    
    # Processamento de datas
    if 'Data' in df.columns:
        try:
            df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
            df = df.dropna(subset=['Data'])
            
            if not df.empty:
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['MêsNome'] = df['Data'].dt.strftime('%B')
                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                df['DiaSemana'] = df['Data'].dt.day_name()
                
                dias_semana_map = {
                    'Monday': 'Segunda',
                    'Tuesday': 'Terça',
                    'Wednesday': 'Quarta',
                    'Thursday': 'Quinta',
                    'Friday': 'Sexta',
                    'Saturday': 'Sábado',
                    'Sunday': 'Domingo'
                }
                df['DiaSemana'] = df['DiaSemana'].map(dias_semana_map)
                
                # Remover domingos
                df = df[df['DiaSemana'] != 'Domingo'].copy()
        except Exception as e:
            st.warning(f"Erro ao processar datas: {e}")
    
    return df

def create_accumulated_line_chart(df):
    """Cria gráfico de linha para capital acumulado usando Bokeh"""
    if df.empty or 'Data' not in df.columns:
        return None
        
    df_sorted = df.sort_values('Data').copy()
    df_sorted['Total Acumulado'] = df_sorted['Total'].cumsum()
    
    source = ColumnDataSource(df_sorted)
    
    p = figure(
        x_axis_type='datetime', 
        title='Acúmulo de Capital ao Longo do Tempo', 
        height=400, 
        sizing_mode='stretch_width',
        toolbar_location='above'
    )
    
    # Linha principal
    p.line('Data', 'Total Acumulado', source=source, line_width=3, color='#4285F4')
    
    # Pontos
    p.circle('Data', 'Total Acumulado', source=source, size=8, color='#4285F4', alpha=0.7)
    
    # Tooltip
    hover = HoverTool(
        tooltips=[
            ('Data', '@DataFormatada'),
            ('Acumulado', 'R$ @{Total Acumulado}{0,0.00}'),
            ('Venda do dia', 'R$ @{Total}{0,0.00}')
        ]
    )
    p.add_tools(hover)
    
    # Estilo
    p.yaxis.axis_label = 'Capital Acumulado (R$)'
    p.xaxis.axis_label = 'Data'
    p.background_fill_color = "#f5f5f5"
    p.border_fill_color = "whitesmoke"
    p.outline_line_color = "#dddddd"
    
    return p

def create_bar_chart_day_of_week(df):
    """Cria gráfico de barras agrupado por dia da semana usando Bokeh"""
    if df.empty or 'DiaSemana' not in df.columns:
        return None
        
    # Dias da semana em ordem correta
    dias_ordem = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
    
    # Agrupar por dia da semana
    vendas_por_dia = df.groupby('DiaSemana')['Total'].sum().reindex(dias_ordem).fillna(0)
    
    source = ColumnDataSource(data=dict(
        dia=vendas_por_dia.index.tolist(),
        total=vendas_por_dia.values
    ))
    
    p = figure(
        x_range=dias_ordem, 
        title='Faturamento por Dia da Semana', 
        height=350, 
        sizing_mode='stretch_width',
        toolbar_location='above'
    )
    
    # Barras
    p.vbar(
        x='dia', 
        top='total', 
        width=0.7, 
        source=source, 
        color='#34A853',
        line_color='white',
        alpha=0.8
    )
    
    # Tooltip
    hover = HoverTool(
        tooltips=[
            ('Dia', '@dia'),
            ('Total', 'R$ @total{0,0.00}')
        ]
    )
    p.add_tools(hover)
    
    # Estilo
    p.yaxis.axis_label = 'Faturamento (R$)'
    p.xaxis.axis_label = 'Dia da Semana'
    p.background_fill_color = "#f5f5f5"
    p.border_fill_color = "whitesmoke"
    p.outline_line_color = "#dddddd"
    
    return p

def create_pie_chart_payment_methods(df):
    """Cria gráfico de pizza para métodos de pagamento usando Bokeh"""
    if df.empty:
        return None
    
    # Somar valores por método de pagamento
    pagamentos = df[['Cartão', 'Dinheiro', 'Pix']].sum()
    pagamentos = pagamentos[pagamentos > 0]
    
    # Preparar dados
    data = pd.Series(pagamentos).reset_index(name='value').rename(columns={'index': 'method'})
    data['angle'] = data['value']/data['value'].sum() * 2*pi
    data['percentage'] = data['value']/data['value'].sum() * 100
    
    # Cores para os métodos de pagamento
    colors = {'Cartão': '#4285F4', 'Dinheiro': '#34A853', 'Pix': '#FBBC05'}
    data['color'] = data['method'].map(colors)
    
    source = ColumnDataSource(data)
    
    p = figure(
        height=350, 
        title='Distribuição por Método de Pagamento', 
        toolbar_location='above', 
        tools='hover',
        tooltips=[
            ('Método', '@method'),
            ('Valor', 'R$ @value{0,0.00}'),
            ('Porcentagem', '@percentage{0.0}%')
        ],
        sizing_mode='stretch_width'
    )
    
    # Gráfico de pizza
    p.wedge(
        x=0, 
        y=1, 
        radius=0.8,
        start_angle=cumsum('angle', include_zero=True), 
        end_angle=cumsum('angle'),
        line_color='white', 
        fill_color='color', 
        legend_field='method', 
        source=source
    )
    
    # Remover eixos desnecessários
    p.axis.visible = False
    p.grid.grid_line_color = None
    p.background_fill_color = "#f5f5f5"
    p.border_fill_color = "whitesmoke"
    p.outline_line_color = "#dddddd"
    
    return p

def create_histogram(df):
    """Cria histograma dos valores de venda usando Bokeh"""
    if df.empty or 'Total' not in df.columns:
        return None
    
    # Calcular histograma
    hist, edges = np.histogram(df['Total'], bins=20)
    
    # Criar dataframe com os valores do histograma
    hist_df = pd.DataFrame({
        'count': hist,
        'left': edges[:-1],
        'right': edges[1:]
    })
    hist_df['interval'] = [f'{left:.2f} - {right:.2f}' for left, right in zip(hist_df['left'], hist_df['right'])]
    
    source = ColumnDataSource(hist_df)
    
    p = figure(
        title='Distribuição dos Valores de Venda', 
        height=350, 
        sizing_mode='stretch_width',
        toolbar_location='above'
    )
    
    # Barras do histograma
    p.quad(
        bottom=0, 
        top='count', 
        left='left', 
        right='right',
        source=source,
        fill_color='#FBBC05',
        line_color='white',
        alpha=0.8
    )
    
    # Tooltip
    hover = HoverTool(
        tooltips=[
            ('Intervalo', '@interval'),
            ('Contagem', '@count')
        ]
    )
    p.add_tools(hover)
    
    # Estilo
    p.yaxis.axis_label = 'Frequência'
    p.xaxis.axis_label = 'Valor da Venda (R$)'
    p.background_fill_color = "#f5f5f5"
    p.border_fill_color = "whitesmoke"
    p.outline_line_color = "#dddddd"
    
    return p

def create_data_table(df):
    """Cria tabela de dados usando Bokeh"""
    if df.empty:
        return None
    
    # Preparar dados para a tabela
    if 'Data' in df.columns:
        df_table = df[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total', 'DiaSemana']].copy()
    else:
        return None
    
    # Fonte de dados para a tabela
    source = ColumnDataSource(df_table)
    
    # Definir colunas da tabela
    columns = [
        TableColumn(field="DataFormatada", title="Data"),
        TableColumn(field="DiaSemana", title="Dia da Semana"),
        TableColumn(field="Cartão", title="Cartão (R$)", formatter=NumberFormatter(format="R$ 0,0.00")),
        TableColumn(field="Dinheiro", title="Dinheiro (R$)", formatter=NumberFormatter(format="R$ 0,0.00")),
        TableColumn(field="Pix", title="PIX (R$)", formatter=NumberFormatter(format="R$ 0,0.00")),
        TableColumn(field="Total", title="Total (R$)", formatter=NumberFormatter(format="R$ 0,0.00"))
    ]
    
    # Criar tabela
    data_table = DataTable(
        source=source, 
        columns=columns, 
        width=800, 
        height=300, 
        sizing_mode='stretch_width',
        index_position=None
    )
    
    return data_table

def main():
    st.title("📊 Sistema de Registro de Vendas")
    
    # Carregar dados
    df_raw, worksheet = read_google_sheet()
    df = process_data(df_raw)
    
    # Abas principais
    tab1, tab2, tab3 = st.tabs([
        "📝 Registrar Venda", 
        "📈 Análise Detalhada", 
        "📊 Estatísticas"
    ])
    
    # Aba 1: Registro de Vendas
    with tab1:
        st.header("Registrar Nova Venda")
        
        with st.form("venda_form"):
            data = st.date_input("📅 Data da Venda", datetime.now())
            is_sunday = data.weekday() == 6  # 6 = Domingo
            
            col1, col2, col3 = st.columns(3)
            with col1:
                cartao = st.number_input("💳 Cartão (R$)", min_value=0.0, format="%.2f")
            with col2:
                dinheiro = st.number_input("💵 Dinheiro (R$)", min_value=0.0, format="%.2f")
            with col3:
                pix = st.number_input("📱 PIX (R$)", min_value=0.0, format="%.2f")
            
            total = cartao + dinheiro + pix
            st.write(f"Total da venda: R$ {total:.2f}")
            
            submitted = st.form_submit_button("💾 Registrar Venda", use_container_width=True)
            
            if submitted:
                if is_sunday:
                    st.error("⚠️ Não é possível registrar vendas aos domingos!")
                elif total > 0:
                    if add_data_to_sheet(data.strftime('%d/%m/%Y'), cartao, dinheiro, pix, worksheet):
                        st.cache_data.clear()
                        st.rerun()
                else:
                    st.warning("⚠️ O valor total deve ser maior que zero.")
    
    # Filtros na sidebar
    with st.sidebar:
        st.header("🔍 Filtros")
        
        if not df.empty and 'Data' in df.columns:
            # Obter mês e ano atual
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            # Filtro de Ano
            anos = sorted(df['Ano'].unique(), reverse=True)
            default_anos = [current_year] if current_year in anos else anos[:1]
            selected_anos = st.multiselect(
                "Selecione o(s) Ano(s):",
                options=anos,
                default=default_anos,
                key="filter_years"
            )
            
            # Filtro de Mês
            meses_disponiveis = sorted(df[df['Ano'].isin(selected_anos)]['Mês'].unique()) if selected_anos else []
            meses_nomes = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
            meses_opcoes = [f"{m:02d} - {meses_nomes[m]}" for m in meses_disponiveis]
            
            # Default para o mês atual ou todos
            default_mes_opcao = [f"{current_month:02d} - {datetime(2020, current_month, 1).strftime('%B')}"]
            default_meses = [m for m in meses_opcoes if m.startswith(f"{current_month:02d} -")]
            
            selected_meses_str = st.multiselect(
                "Selecione o(s) Mês(es):",
                options=meses_opcoes,
                default=default_meses if default_meses else meses_opcoes,
                key="filter_months"
            )
            selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]
            
            # Aplicar filtros
            df_filtered = df.copy()
            
            if selected_anos:
                df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos)]
            
            if selected_meses:
                df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)]
            
        else:
            st.info("Não há dados disponíveis para filtrar.")
            df_filtered = pd.DataFrame()
    
    # Aba 2: Análise Detalhada
    with tab2:
        st.header("Análise Detalhada de Vendas")
        
        if df_filtered.empty:
            st.info("Não há dados para exibir com os filtros selecionados.")
        else:
            # Mostrar dados filtrados em uma tabela
            st.subheader("🧾 Dados Filtrados")
            
            # Tabela Bokeh
            data_table = create_data_table(df_filtered)
            if data_table:
                st.bokeh_chart(data_table, use_container_width=True)
            
            # Resumo dos dados
            total_vendas = len(df_filtered)
            total_faturamento = df_filtered['Total'].sum()
            media_por_venda = df_filtered['Total'].mean() if total_vendas > 0 else 0
            maior_venda = df_filtered['Total'].max() if total_vendas > 0 else 0
            
            # Melhor dia da semana
            melhor_dia = None
            if 'DiaSemana' in df_filtered.columns and not df_filtered.empty:
                vendas_por_dia = df_filtered.groupby('DiaSemana')['Total'].sum()
                if not vendas_por_dia.empty:
                    melhor_dia = vendas_por_dia.idxmax()
            
            # Exibir métricas em cards
            st.subheader("📌 Resumo")
            
            st.markdown(f"""
            <div class="resumo-container">
                <div class="resumo-item">
                    <div class="resumo-titulo">Total de Vendas</div>
                    <div class="resumo-valor">{total_vendas}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Faturamento Total</div>
                    <div class="resumo-valor">R$ {total_faturamento:,.2f}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Ticket Médio</div>
                    <div class="resumo-valor">R$ {media_por_venda:,.2f}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Melhor Dia</div>
                    <div class="resumo-valor">{melhor_dia if melhor_dia else 'N/A'}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Acúmulo de Capital
            st.subheader("💰 Acúmulo de Capital ao Longo do Tempo")
            
            line_chart = create_accumulated_line_chart(df_filtered)
            if line_chart:
                st.bokeh_chart(line_chart, use_container_width=True)
    
    # Aba 3: Estatísticas
    with tab3:
        st.header("Estatísticas Avançadas de Vendas")
        
        if df_filtered.empty:
            st.info("Não há dados para exibir com os filtros selecionados.")
        else:
            # Análise por Dia da Semana
            st.subheader("📅 Análise por Dia da Semana")
            
            bar_chart = create_bar_chart_day_of_week(df_filtered)
            if bar_chart:
                st.bokeh_chart(bar_chart, use_container_width=True)
            
            # Métodos de Pagamento
            st.subheader("💳 Métodos de Pagamento")
            
            pie_chart = create_pie_chart_payment_methods(df_filtered)
            if pie_chart:
                st.bokeh_chart(pie_chart, use_container_width=True)
            
            # Histograma dos valores
            st.subheader("📊 Distribuição dos Valores de Venda")
            
            histogram = create_histogram(df_filtered)
            if histogram:
                st.bokeh_chart(histogram, use_container_width=True)

if __name__ == "__main__":
    main()
