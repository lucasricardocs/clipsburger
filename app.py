import streamlit as st
import gspread
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
WORKSHEET_NAME = 'Vendas'

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema Financeiro - Clips Burger", layout="centered", page_icon="🍔")

# Configuração de tema para gráficos mais bonitos
alt.data_transformers.enable('json')

# Paleta de cores personalizada
CORES_PERSONALIZADAS = {
    'primary': '#1f77b4',
    'secondary': '#ff7f0e', 
    'success': '#2ca02c',
    'danger': '#d62728',
    'warning': '#ff7f0e',
    'info': '#17becf',
    'gradient': ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a']
}

# Define a ordem correta dos dias da semana e meses
dias_semana_ordem = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

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

# --- Função para filtrar por somatório de últimos N dias ---
def filter_by_rolling_days(df, dias_selecionados):
    """Filtra o DataFrame para incluir apenas registros dos últimos N dias selecionados."""
    if df.empty or not dias_selecionados or 'Data' not in df.columns:
        return df
    
    # Pega a data mais recente dos dados
    data_mais_recente = df['Data'].max()
    
    # Calcula o maior período selecionado
    max_dias = max(dias_selecionados)
    
    # Filtra para incluir apenas os últimos N dias
    data_inicio = data_mais_recente - timedelta(days=max_dias - 1)
    df_filtrado = df[df['Data'] >= data_inicio].copy()
    
    return df_filtrado

# --- Funções de Gráficos Interativos Aprimorados ---
def create_enhanced_payment_pie_chart(df):
    """Cria um gráfico de pizza interativo e moderno para métodos de pagamento."""
    if df.empty or not any(col in df.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
        return None
    
    payment_data = pd.DataFrame({
        'Método': ['💳 Cartão', '💵 Dinheiro', '📱 PIX'],
        'Valor': [df['Cartão'].sum(), df['Dinheiro'].sum(), df['Pix'].sum()]
    })
    payment_data = payment_data[payment_data['Valor'] > 0]
    
    if payment_data.empty:
        return None
    
    # Gráfico de pizza com Plotly para maior interatividade
    fig = px.pie(
        payment_data, 
        values='Valor', 
        names='Método',
        title="🥧 Distribuição por Método de Pagamento",
        color_discrete_sequence=px.colors.qualitative.Set3,
        hover_data=['Valor']
    )
    
    fig.update_traces(
        textposition='inside', 
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>Percentual: %{percent}<extra></extra>',
        pull=[0.1, 0, 0]  # Destaca o primeiro segmento
    )
    
    fig.update_layout(
        showlegend=True,
        height=500,
        font=dict(size=14),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    return fig

def create_advanced_daily_sales_chart(df):
    """Cria um gráfico de vendas diárias com múltiplas visualizações."""
    if df.empty or 'Data' not in df.columns:
        return None
    
    df_sorted = df.sort_values('Data')
    
    # Criar subplot com múltiplos gráficos
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('📊 Vendas Diárias por Método de Pagamento', '📈 Tendência de Vendas Totais'),
        vertical_spacing=0.12,
        specs=[[{"secondary_y": False}], [{"secondary_y": True}]]
    )
    
    # Gráfico de barras empilhadas
    fig.add_trace(
        go.Bar(name='💳 Cartão', x=df_sorted['Data'], y=df_sorted['Cartão'], 
               marker_color='#1f77b4', hovertemplate='Data: %{x}<br>Cartão: R$ %{y:,.2f}<extra></extra>'),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(name='💵 Dinheiro', x=df_sorted['Data'], y=df_sorted['Dinheiro'], 
               marker_color='#2ca02c', hovertemplate='Data: %{x}<br>Dinheiro: R$ %{y:,.2f}<extra></extra>'),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(name='📱 PIX', x=df_sorted['Data'], y=df_sorted['Pix'], 
               marker_color='#ff7f0e', hovertemplate='Data: %{x}<br>PIX: R$ %{y:,.2f}<extra></extra>'),
        row=1, col=1
    )
    
    # Linha de tendência
    fig.add_trace(
        go.Scatter(name='📈 Total Diário', x=df_sorted['Data'], y=df_sorted['Total'],
                  mode='lines+markers', line=dict(color='#d62728', width=3),
                  marker=dict(size=8), hovertemplate='Data: %{x}<br>Total: R$ %{y:,.2f}<extra></extra>'),
        row=2, col=1
    )
    
    # Média móvel de 7 dias
    if len(df_sorted) >= 7:
        df_sorted['Media_Movel'] = df_sorted['Total'].rolling(window=7, center=True).mean()
        fig.add_trace(
            go.Scatter(name='📊 Média Móvel (7 dias)', x=df_sorted['Data'], y=df_sorted['Media_Movel'],
                      mode='lines', line=dict(color='#9467bd', width=2, dash='dash'),
                      hovertemplate='Data: %{x}<br>Média 7 dias: R$ %{y:,.2f}<extra></extra>'),
            row=2, col=1
        )
    
    # Configurações do layout
    fig.update_layout(
        height=800,
        showlegend=True,
        barmode='stack',
        title_text="📊 Análise Completa de Vendas Diárias",
        title_x=0.5,
        font=dict(size=12),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
    )
    
    # Configurar eixos
    fig.update_xaxes(title_text="Data", row=2, col=1)
    fig.update_yaxes(title_text="Valor (R$)", row=1, col=1)
    fig.update_yaxes(title_text="Valor Total (R$)", row=2, col=1)
    
    return fig

def create_interactive_accumulation_chart(df):
    """Cria um gráfico de acumulação interativo estilo montanha."""
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        return None
    
    df_accumulated = df.sort_values('Data').copy()
    df_accumulated['Total_Acumulado'] = df_accumulated['Total'].cumsum()
    df_accumulated['Crescimento_Diario'] = df_accumulated['Total_Acumulado'].pct_change() * 100
    
    fig = go.Figure()
    
    # Área de acumulação
    fig.add_trace(go.Scatter(
        x=df_accumulated['Data'],
        y=df_accumulated['Total_Acumulado'],
        fill='tonexty',
        mode='lines',
        line=dict(color='rgba(31, 119, 180, 0.8)', width=3),
        fillcolor='rgba(31, 119, 180, 0.3)',
        name='💰 Capital Acumulado',
        hovertemplate='<b>Data:</b> %{x}<br><b>Acumulado:</b> R$ %{y:,.2f}<extra></extra>'
    ))
    
    # Pontos de destaque para valores máximos
    max_value = df_accumulated['Total_Acumulado'].max()
    max_date = df_accumulated[df_accumulated['Total_Acumulado'] == max_value]['Data'].iloc[0]
    
    fig.add_trace(go.Scatter(
        x=[max_date],
        y=[max_value],
        mode='markers',
        marker=dict(size=15, color='red', symbol='star'),
        name='🎯 Pico Máximo',
        hovertemplate='<b>Pico Máximo</b><br>Data: %{x}<br>Valor: R$ %{y:,.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="🏔️ Evolução do Capital Acumulado",
        xaxis_title="Período",
        yaxis_title="Capital Acumulado (R$)",
        height=600,
        showlegend=True,
        hovermode='x unified',
        font=dict(size=12)
    )
    
    # Adicionar anotação no pico
    fig.add_annotation(
        x=max_date,
        y=max_value,
        text=f"Pico: R$ {max_value:,.2f}",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=2,
        arrowcolor="red",
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="red",
        borderwidth=1
    )
    
    return fig

def create_enhanced_weekday_analysis(df):
    """Cria análise avançada de vendas por dia da semana."""
    if df.empty or 'DiaSemana' not in df.columns or 'Total' not in df.columns:
        return None, None
    
    df_copy = df.copy()
    df_copy['Total'] = pd.to_numeric(df_copy['Total'], errors='coerce')
    df_copy.dropna(subset=['Total', 'DiaSemana'], inplace=True)
    
    if df_copy.empty:
        return None, None
    
    # Análise por dia da semana
    weekday_stats = df_copy.groupby('DiaSemana').agg({
        'Total': ['mean', 'sum', 'count', 'std']
    }).round(2)
    
    weekday_stats.columns = ['Média', 'Total', 'Dias_Vendas', 'Desvio_Padrão']
    weekday_stats = weekday_stats.reindex([d for d in dias_semana_ordem if d in weekday_stats.index])
    
    # Gráfico combinado
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('📊 Média de Vendas por Dia', '📈 Total de Vendas por Dia'),
        specs=[[{"secondary_y": False}, {"secondary_y": True}]]
    )
    
    # Gráfico de barras para média
    fig.add_trace(
        go.Bar(
            x=weekday_stats.index,
            y=weekday_stats['Média'],
            name='💰 Média Diária',
            marker_color='lightblue',
            text=[f'R$ {val:,.0f}' for val in weekday_stats['Média']],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Média: R$ %{y:,.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Gráfico de linha para total
    fig.add_trace(
        go.Scatter(
            x=weekday_stats.index,
            y=weekday_stats['Total'],
            mode='lines+markers',
            name='📈 Total Acumulado',
            line=dict(color='orange', width=3),
            marker=dict(size=10),
            hovertemplate='<b>%{x}</b><br>Total: R$ %{y:,.2f}<extra></extra>'
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        height=500,
        showlegend=True,
        title_text="📅 Análise Detalhada por Dia da Semana"
    )
    
    best_day = weekday_stats['Média'].idxmax()
    
    return fig, best_day

def create_financial_dashboard(resultados):
    """Cria um dashboard financeiro interativo."""
    # Dados para o gráfico de cascata
    categorias = ['Faturamento Bruto', 'Impostos', 'Custo Produtos', 'Folha Pagamento', 'Serviços Contábeis', 'Lucro Final']
    valores = [
        resultados['faturamento_bruto'],
        -resultados['imposto_simples'],
        -resultados['custo_fornecedores_valor'],
        -resultados['custo_funcionario'],
        -resultados['custo_contadora'],
        resultados['lucro_bruto']
    ]
    
    # Gráfico de cascata
    fig = go.Figure(go.Waterfall(
        name="Fluxo Financeiro",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "relative", "total"],
        x=categorias,
        textposition="outside",
        text=[f"R$ {abs(v):,.0f}" for v in valores],
        y=valores,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "red"}},
        increasing={"marker": {"color": "green"}},
        totals={"marker": {"color": "blue"}}
    ))
    
    fig.update_layout(
        title="💰 Fluxo de Formação do Resultado Financeiro",
        height=600,
        showlegend=False,
        xaxis_title="Componentes Financeiros",
        yaxis_title="Valor (R$)"
    )
    
    return fig

def create_payment_evolution_chart(df, title="Evolução da Preferência por Pagamento (Mensal)"):
    if df.empty or 'AnoMês' not in df.columns or not any(col in df.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
        return None
    df_chart = df.sort_values('AnoMês')
    monthly_payments = df_chart.groupby('AnoMês')[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
    monthly_payments_long = monthly_payments.melt(
        id_vars=['AnoMês'], value_vars=['Cartão', 'Dinheiro', 'Pix'], var_name='Método', value_name='Valor')
    monthly_payments_long = monthly_payments_long[monthly_payments_long['Valor'] > 0]
    if monthly_payments_long.empty: return None
    area_chart = alt.Chart(monthly_payments_long).mark_area().encode(
        x=alt.X('AnoMês:N', title='Mês/Ano', sort=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Valor:Q', title='Valor Total (R$)', stack='zero', axis=alt.Axis(format=",.2f")),
        color=alt.Color('Método:N', legend=alt.Legend(title="Método de Pagamento")),
        tooltip=[alt.Tooltip("AnoMês", title="Mês/Ano"), alt.Tooltip("Método", title="Método"), alt.Tooltip("Valor", title="Valor (R$)", format=",.2f")]
    ).properties(title=title, height=600).interactive()
    return area_chart

def create_sales_histogram(df, title="Distribuição dos Valores de Venda Diários"):
    if df.empty or 'Total' not in df.columns or df['Total'].isnull().all(): return None
    df_filtered_hist = df[df['Total'] > 0].copy()
    if df_filtered_hist.empty: return None
    histogram = alt.Chart(df_filtered_hist).mark_bar().encode(
        alt.X("Total:Q", bin=alt.Bin(maxbins=20), title="Faixa de Valor da Venda Diária (R$)"),
        alt.Y('count()', title='Número de Dias (Frequência)'),
        tooltip=[alt.Tooltip("Total:Q", bin=True, title="Faixa de Valor (R$)"), alt.Tooltip("count()", title="Número de Dias")]
    ).properties(title=title, height=600).interactive()
    return histogram

def analyze_sales_by_weekday(df):
    if df.empty or 'DiaSemana' not in df.columns or 'Total' not in df.columns or df['DiaSemana'].isnull().all() or df['Total'].isnull().all(): return None, None
    try:
        df_copy = df.copy()
        df_copy['Total'] = pd.to_numeric(df_copy['Total'], errors='coerce')
        df_copy.dropna(subset=['Total', 'DiaSemana'], inplace=True)
        if df_copy.empty: return None, None
        avg_sales_weekday = df_copy.groupby('DiaSemana', observed=False)['Total'].mean().reindex(dias_semana_ordem).dropna()
        if not avg_sales_weekday.empty:
            best_day = avg_sales_weekday.idxmax()
            return best_day, avg_sales_weekday
        else: return None, avg_sales_weekday
    except Exception as e:
        st.error(f"Erro ao analisar vendas por dia da semana: {e}")
        return None, None

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
    
    # RECEITAS
    results['faturamento_bruto'] = df['Total'].sum()
    results['faturamento_tributavel'] = df['Cartão'].sum() + df['Pix'].sum()
    results['faturamento_nao_tributavel'] = df['Dinheiro'].sum()
    
    # CUSTOS E DESPESAS
    results['imposto_simples'] = results['faturamento_tributavel'] * 0.06
    results['custo_funcionario'] = salario_minimo * 1.55
    results['custo_fornecedores_valor'] = results['faturamento_bruto'] * (custo_fornecedores_percentual / 100)
    results['total_custos'] = results['imposto_simples'] + results['custo_funcionario'] + results['custo_contadora'] + results['custo_fornecedores_valor']
    
    # RESULTADOS
    results['lucro_bruto'] = results['faturamento_bruto'] - results['total_custos']
    results['lucro_liquido'] = results['faturamento_bruto'] - results['faturamento_tributavel']
    
    # MARGENS
    if results['faturamento_bruto'] > 0:
        results['margem_lucro_bruto'] = (results['lucro_bruto'] / results['faturamento_bruto']) * 100
        results['margem_lucro_liquido'] = (results['lucro_liquido'] / results['faturamento_bruto']) * 100
    
    return results

# Função para formatar valores em moeda brasileira
def format_brl(value):
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

# --- Interface Principal da Aplicação ---
def main():
    # Título melhorado com logo
    try:
        col_logo, col_title = st.columns([2, 7])
        with col_logo:
            st.image('logo.png', width=300)
        with col_title:
            st.title("SISTEMA FINANCEIRO - CLIP'S BURGER")
            st.caption("Gestão inteligente de vendas com análise financeira em tempo real")
    except FileNotFoundError:
        st.title("🍔 SISTEMA FINANCEIRO - CLIPS BURGER")
        st.caption("Gestão inteligente de vendas com análise financeira em tempo real")
    except Exception as e:
        st.title("🍔 SISTEMA FINANCEIRO - CLIPS BURGER")
        st.caption("Gestão inteligente de vendas com análise financeira em tempo real")

    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    tab1, tab2, tab3, tab4 = st.tabs(["📝 Registrar Venda", "📈 Análise Detalhada", "💡 Estatísticas", "💰 Análise Contábil"])

    with tab1:
        st.header("📝 Registrar Nova Venda")
        with st.form("venda_form"):
            data_input = st.date_input("📅 Data da Venda", value=datetime.now(), format="DD/MM/YYYY")
            col1, col2, col3 = st.columns(3)
            with col1: cartao_input = st.number_input("💳 Cartão (R$)", min_value=0.0, value=0.0, format="%.2f", key="cartao_venda")
            with col2: dinheiro_input = st.number_input("💵 Dinheiro (R$)", min_value=0.0, value=0.0, format="%.2f", key="dinheiro_venda")
            with col3: pix_input = st.number_input("📱 PIX (R$)", min_value=0.0, value=0.0, format="%.2f", key="pix_venda")
            total_venda_form = (cartao_input or 0.0) + (dinheiro_input or 0.0) + (pix_input or 0.0)
            st.markdown(f"### **💰 Total da venda: {format_brl(total_venda_form)}**")
            submitted = st.form_submit_button("✅ Registrar Venda", type="primary")
            if submitted:
                if total_venda_form > 0:
                    formatted_date = data_input.strftime('%d/%m/%Y')
                    worksheet_obj = get_worksheet()
                    if worksheet_obj and add_data_to_sheet(formatted_date, cartao_input, dinheiro_input, pix_input, worksheet_obj):
                        read_sales_data.clear(); process_data.clear()
                        st.success("✅ Venda registrada e dados recarregados!")
                        st.rerun()
                    elif not worksheet_obj: st.error("❌ Falha ao conectar à planilha. Venda não registrada.")
                else: st.warning("⚠️ O valor total da venda deve ser maior que zero.")

    # --- SIDEBAR COM FILTROS MELHORADOS ---
    selected_anos_filter, selected_meses_filter, selected_dias_rolling = [], [], []
    
    with st.sidebar:
        st.header("🔍 Filtros de Período")
        st.markdown("---")
        
        # Filtro de Anos
        if not df_processed.empty and 'Ano' in df_processed.columns and not df_processed['Ano'].isnull().all():
            anos_disponiveis = sorted(df_processed['Ano'].dropna().unique().astype(int), reverse=True)
            if anos_disponiveis:
                default_ano = [datetime.now().year] if datetime.now().year in anos_disponiveis else [anos_disponiveis[0]] if anos_disponiveis else []
                selected_anos_filter = st.multiselect("📅 Ano(s):", options=anos_disponiveis, default=default_ano)
                
                # Filtro de Meses
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
                        
                        # NOVO: Filtro de Somatório dos Últimos N Dias
                        st.markdown("### 📊 Análise de Últimos Dias")
                        dias_opcoes = [1, 2, 3, 5, 7]
                        selected_dias_rolling = st.multiselect(
                            "🔄 Somatório dos últimos:",
                            options=dias_opcoes,
                            default=[7],
                            format_func=lambda x: f"Últimos {x} dia{'s' if x > 1 else ''}"
                        )
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
        
        # Aplicar filtro de rolling days se selecionado
        if selected_dias_rolling:
            df_filtered = filter_by_rolling_days(df_filtered, selected_dias_rolling)

    # Mostrar informações dos filtros aplicados na sidebar
    if not df_filtered.empty:
        total_registros_filtrados = len(df_filtered)
        total_faturamento_filtrado = df_filtered['Total'].sum()
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📈 Resumo dos Filtros Aplicados")
        st.sidebar.metric("Registros Filtrados", total_registros_filtrados)
        st.sidebar.metric("Faturamento Filtrado", format_brl(total_faturamento_filtrado))
        
        # Mostrar informação sobre filtro de dias se aplicado
        if selected_dias_rolling:
            max_dias = max(selected_dias_rolling)
            st.sidebar.info(f"📅 Exibindo dados dos últimos {max_dias} dias")
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
            
            st.subheader("🥧 Distribuição por Método de Pagamento")
            pie_chart = create_enhanced_payment_pie_chart(df_filtered)
            if pie_chart:
                st.plotly_chart(pie_chart, use_container_width=True)
            else:
                st.info("Sem dados de pagamento para exibir o gráfico de pizza nos filtros selecionados.")

            st.subheader("📊 Análise Completa de Vendas Diárias")
            daily_chart = create_advanced_daily_sales_chart(df_filtered)
            if daily_chart:
                st.plotly_chart(daily_chart, use_container_width=True)
            else:
                st.info("Sem dados de vendas diárias para exibir o gráfico nos filtros selecionados.")

            st.subheader("🏔️ Evolução do Capital Acumulado")
            accumulation_chart = create_interactive_accumulation_chart(df_filtered)
            if accumulation_chart:
                st.plotly_chart(accumulation_chart, use_container_width=True)
            else:
                st.info("Não foi possível gerar o gráfico de acumulação.")
        else:
             if df_processed.empty and df_raw.empty and get_worksheet() is None: st.warning("Não foi possível carregar os dados. Verifique configurações e credenciais.")
             elif df_processed.empty: st.info("Não há dados processados para exibir. Verifique a planilha de origem.")
             elif df_filtered.empty: st.info("Nenhum dado corresponde aos filtros selecionados.")
             else: st.info("Não há dados para exibir na Análise Detalhada. Pode ser um problema no processamento.")

    with tab3:
        st.header("💡 Estatísticas e Tendências de Vendas")
        if not df_filtered.empty and 'Total' in df_filtered.columns and not df_filtered['Total'].isnull().all():
            st.subheader("💰 Resumo Financeiro Agregado")
            total_registros = len(df_filtered); total_faturamento = df_filtered['Total'].sum()
            media_por_registro = df_filtered['Total'].mean() if total_registros > 0 else 0
            maior_venda_diaria = df_filtered['Total'].max() if total_registros > 0 else 0
            menor_venda_diaria = df_filtered[df_filtered['Total'] > 0]['Total'].min() if not df_filtered[df_filtered['Total'] > 0].empty else 0
            col1, col2 = st.columns(2)
            col1.metric("🔢 Total de Registros (Dias com Venda)", f"{total_registros}")
            col2.metric("💵 Faturamento Total", format_brl(total_faturamento))
            col3, col4 = st.columns(2)
            col3.metric("📈 Média por Registro", format_brl(media_por_registro))
            col4.metric("⬆️ Maior Venda Diária", format_brl(maior_venda_diaria))
            st.metric("⬇️ Menor Venda Diária (>0)", format_brl(menor_venda_diaria))
            st.divider()

            st.subheader("💳 Métodos de Pagamento (Visão Geral)")
            cartao_total = df_filtered['Cartão'].sum() if 'Cartão' in df_filtered else 0
            dinheiro_total = df_filtered['Dinheiro'].sum() if 'Dinheiro' in df_filtered else 0
            pix_total = df_filtered['Pix'].sum() if 'Pix' in df_filtered else 0
            total_pagamentos_geral = cartao_total + dinheiro_total + pix_total
            if total_pagamentos_geral > 0:
                cartao_pct = (cartao_total / total_pagamentos_geral * 100)
                dinheiro_pct = (dinheiro_total / total_pagamentos_geral * 100)
                pix_pct = (pix_total / total_pagamentos_geral * 100)
                payment_cols = st.columns(3)
                payment_cols[0].metric("💳 Cartão", format_brl(cartao_total), f"{cartao_pct:.1f}% do total")
                payment_cols[1].metric("💵 Dinheiro", format_brl(dinheiro_total), f"{dinheiro_pct:.1f}% do total")
                payment_cols[2].metric("📱 PIX", format_brl(pix_total), f"{pix_pct:.1f}% do total")
            else: st.info("Sem dados de pagamento para exibir o resumo nesta seção.")
            st.divider()

            st.subheader("📅 Análise Avançada por Dia da Semana")
            weekday_chart, best_day = create_enhanced_weekday_analysis(df_filtered)
            if weekday_chart:
                st.plotly_chart(weekday_chart, use_container_width=True)
                if best_day:
                    st.success(f"🏆 **Melhor Dia da Semana:** {best_day}")
            else:
                st.info("📊 Dados insuficientes para calcular a análise por dia da semana.")
            st.divider()
            
            st.subheader("📈 Evolução dos Métodos de Pagamento")
            payment_evolution_chart = create_payment_evolution_chart(df_filtered)
            if payment_evolution_chart: st.altair_chart(payment_evolution_chart, use_container_width=True)
            else: st.info("Dados insuficientes para Evolução de Pagamento.")
            st.divider()

            st.subheader("📊 Distribuição de Valores de Venda Diários")
            sales_histogram_chart = create_sales_histogram(df_filtered)
            if sales_histogram_chart: st.altair_chart(sales_histogram_chart, use_container_width=True)
            else: st.info("Dados insuficientes para o Histograma de Vendas.")
        else:
            if df_processed.empty and df_raw.empty and get_worksheet() is None: st.warning("Não foi possível carregar os dados da planilha.")
            elif df_processed.empty: st.info("Não há dados processados para exibir estatísticas.")
            elif df_filtered.empty: st.info("Nenhum dado corresponde aos filtros para exibir estatísticas.")
            else: st.info("Não há dados de 'Total' para exibir nas Estatísticas.")

    # --- TAB4: ANÁLISE CONTÁBIL COMPLETA ---
    with tab4:
        st.header("📊 Análise Contábil e Financeira Detalhada")
        
        st.markdown("""
        ### 📋 **Sobre esta Análise**
        
        Esta seção apresenta uma **análise contábil completa** do Clips Burger, baseada nos dados de vendas filtrados. 
        Os cálculos seguem as **normas contábeis brasileiras** e consideram:
        
        - **Regime Tributário:** Simples Nacional (6% sobre receita tributável)
        - **Receita Tributável:** Apenas vendas via Cartão e PIX
        - **Receita Não Tributável:** Vendas em dinheiro (não declaradas)
        - **Custos Operacionais:** Funcionários, contadora e fornecedores
        """)
        
        # Parâmetros Financeiros
        with st.container(border=True):
            st.subheader("⚙️ Parâmetros para Simulação Contábil")
            st.markdown("Configure os valores abaixo para simular diferentes cenários financeiros:")
            
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
                    help="Percentual do faturamento destinado à compra de produtos (hambúrgueres, batatas, bebidas, etc.).",
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

            st.subheader("💰 Dashboard Financeiro Interativo")
            financial_dashboard = create_financial_dashboard(resultados)
            if financial_dashboard:
                st.plotly_chart(financial_dashboard, use_container_width=True)

            # === SEÇÃO 1: DEMONSTRATIVO DE RECEITAS ===
            with st.container(border=True):
                st.subheader("💰 Demonstrativo de Receitas")
                st.markdown("""
                **Explicação:** As receitas são classificadas entre tributáveis e não tributáveis conforme a legislação brasileira.
                No Simples Nacional, apenas as receitas declaradas (cartão e PIX) são tributadas.
                """)
                
                col_rec1, col_rec2, col_rec3 = st.columns(3)
                
                with col_rec1:
                    st.metric(
                        "📈 Faturamento Bruto Total",
                        format_brl(resultados['faturamento_bruto']),
                        help="Soma de todas as vendas (cartão + PIX + dinheiro)"
                    )
                
                with col_rec2:
                    st.metric(
                        "🏦 Receita Tributável",
                        format_brl(resultados['faturamento_tributavel']),
                        f"{((resultados['faturamento_tributavel'] / resultados['faturamento_bruto'] * 100) if resultados['faturamento_bruto'] > 0 else 0):.1f}% do total",
                        help="Vendas via cartão e PIX (sujeitas à tributação)"
                    )
                
                with col_rec3:
                    st.metric(
                        "💵 Receita Não Tributável",
                        format_brl(resultados['faturamento_nao_tributavel']),
                        f"{((resultados['faturamento_nao_tributavel'] / resultados['faturamento_bruto'] * 100) if resultados['faturamento_bruto'] > 0 else 0):.1f}% do total",
                        help="Vendas em dinheiro (não declaradas)"
                    )

            st.markdown("---")

            # === SEÇÃO 2: DEMONSTRATIVO DE RESULTADOS ===
            with st.container(border=True):
                st.subheader("🎯 Demonstrativo de Resultados (DRE Simplificado)")
                st.markdown("""
                **Explicação:** O DRE mostra a formação do resultado financeiro do período, seguindo a estrutura contábil padrão.
                """)
                
                # Métricas de resultado
                col_result1, col_result2 = st.columns(2)
                
                with col_result1:
                    st.metric(
                        "💰 Lucro Operacional",
                        format_brl(resultados['lucro_bruto']),
                        f"{resultados['margem_lucro_bruto']:.2f}% do Faturamento",
                        delta_color="normal" if resultados['lucro_bruto'] >= 0 else "inverse"
                    )
                    st.caption("Resultado após todos os custos e despesas operacionais")
                
                with col_result2:
                    st.metric(
                        "🏦 Diferença (Bruto - Tributável)",
                        format_brl(resultados['lucro_liquido']),
                        f"{resultados['margem_lucro_liquido']:.2f}% do Faturamento",
                        delta_color="off"
                    )
                    st.caption("Diferença entre faturamento total e receita declarada")

            st.markdown("---")

            # === SEÇÃO 3: ANÁLISE DE INDICADORES ===
            with st.container(border=True):
                st.subheader("📈 Análise de Indicadores Financeiros")
                st.markdown("""
                **Explicação:** Os indicadores financeiros ajudam a avaliar a saúde econômica do negócio e comparar com benchmarks do setor.
                """)
                
                # Calcular indicadores
                if resultados['faturamento_bruto'] > 0:
                    indicadores = {
                        'Margem Bruta': (resultados['faturamento_bruto'] - resultados['custo_fornecedores_valor']) / resultados['faturamento_bruto'] * 100,
                        'Margem Operacional': resultados['margem_lucro_bruto'],
                        'Carga Tributária': resultados['imposto_simples'] / resultados['faturamento_bruto'] * 100,
                        'Custo de Pessoal': resultados['custo_funcionario'] / resultados['faturamento_bruto'] * 100,
                        'Custo dos Produtos': resultados['custo_fornecedores_valor'] / resultados['faturamento_bruto'] * 100
                    }
                    
                    # Exibir indicadores
                    col_ind1, col_ind2, col_ind3 = st.columns(3)
                    
                    with col_ind1:
                        st.metric("📊 Margem Bruta", f"{indicadores['Margem Bruta']:.1f}%")
                        st.metric("🏛️ Carga Tributária", f"{indicadores['Carga Tributária']:.1f}%")
                    
                    with col_ind2:
                        st.metric("💼 Margem Operacional", f"{indicadores['Margem Operacional']:.1f}%")
                        st.metric("👥 Custo de Pessoal", f"{indicadores['Custo de Pessoal']:.1f}%")
                    
                    with col_ind3:
                        st.metric("📦 Custo dos Produtos", f"{indicadores['Custo dos Produtos']:.1f}%")

            st.markdown("---")

            # Nota final
            st.info("""
            💡 **Nota Importante:** Esta análise é uma simulação baseada nos dados informados e parâmetros configurados. 
            Para decisões financeiras importantes, consulte sempre um contador ou consultor financeiro qualificado.
            
            **Limitações:** Não inclui outros custos como aluguel, energia, marketing, depreciação, provisões, 
            nem impostos sobre o lucro (IRPJ, CSLL) que podem ser aplicáveis dependendo do regime tributário.
            """)

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    main()
