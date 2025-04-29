import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, APIError
import locale
from tenacity import retry, stop_after_attempt, wait_exponential

# --- Constants ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly'
]
SPREADSHEET_ID = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
WORKSHEET_NAME = 'Vendas'
REQUIRED_COLS = ['Cartão', 'Dinheiro', 'Pix', 'Data']
PAYMENT_METHODS = ['Cartão', 'Dinheiro', 'Pix']
WEEKDAY_ORDER = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 
                'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']

# --- Initial Setup ---
def setup_locale():
    """Configure locale settings for currency formatting"""
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except locale.Error:
        st.warning("Locale 'pt_BR.UTF-8' not available. Using default locale.")

def setup_page_config():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="Sistema de Registro e Análise de Vendas",
        layout="wide",
        menu_items={
            'Get Help': 'https://example.com/help',
            'Report a bug': 'https://example.com/bug',
            'About': "Sistema de análise de vendas v1.0"
        }
    )

# --- Google Sheets Functions ---
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_google_client():
    """Authenticate with Google Sheets API with retry logic"""
    try:
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except KeyError:
        st.error("Credenciais 'google_credentials' não encontradas nos segredos do Streamlit.")
        return None
    except Exception as e:
        st.error(f"Erro de autenticação: {e}")
        return None

@st.cache_data(ttl=600)
def load_sheet_data():
    """Load data from Google Sheets with caching"""
    try:
        gc = get_google_client()
        if not gc:
            return pd.DataFrame()
        
        worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        rows = worksheet.get_all_records()
        
        if not rows:
            st.warning("A planilha está vazia.")
            return pd.DataFrame()
            
        df = pd.DataFrame(rows)
        df.columns = [col.strip().title() for col in df.columns]
        return df
        
    except SpreadsheetNotFound:
        st.error(f"Planilha com ID {SPREADSHEET_ID} não encontrada.")
        return pd.DataFrame()
    except APIError as e:
        st.error(f"Erro na API do Google Sheets: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro inesperado ao carregar dados: {e}")
        return pd.DataFrame()

def get_worksheet_for_writing():
    """Get worksheet object for writing data"""
    gc = get_google_client()
    if not gc:
        return None
    try:
        return gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    except Exception as e:
        st.error(f"Erro ao acessar planilha para escrita: {e}")
        return None

def add_sale_record(date_str, cartao, dinheiro, pix, worksheet):
    """Add a new sale record to the worksheet"""
    if not worksheet:
        return False
    
    try:
        new_row = [date_str, float(cartao), float(dinheiro), float(pix)]
        worksheet.append_row(new_row, value_input_option='USER_ENTERED')
        return True
    except APIError as e:
        st.error(f"Erro na API ao adicionar dados: {e}")
        return False
    except Exception as e:
        st.error(f"Erro ao registrar venda: {e}")
        return False

# --- Data Processing ---
def process_dates(df):
    """Process and validate date columns"""
    if 'Data' not in df.columns:
        st.error("Coluna 'Data' não encontrada.")
        return df
    
    try:
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        
        # Count parsing errors
        original_non_empty = df['Data'].notna().sum()
        parsed_nulls = df['Data'].isna().sum()
        
        if parsed_nulls > 0:
            st.warning(f"{parsed_nulls} datas não puderam ser reconhecidas (formato DD/MM/YYYY)")
        
        # Add date components
        df['Ano'] = df['Data'].dt.year
        df['Mês'] = df['Data'].dt.month
        df['MêsNome'] = df['Data'].dt.strftime('%B').str.capitalize()
        df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
        df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
        df['DiaSemana'] = df['Data'].dt.strftime('%A').str.capitalize()
        df['DiaSemanaNum'] = df['Data'].dt.dayofweek
        
        return df
        
    except Exception as e:
        st.error(f"Erro ao processar datas: {e}")
        return df

def process_payments(df):
    """Process payment columns"""
    for method in PAYMENT_METHODS:
        if method in df.columns:
            df[method] = pd.to_numeric(df[method], errors='coerce').fillna(0)
        else:
            st.warning(f"Coluna '{method}' não encontrada - definindo como zero")
            df[method] = 0
    
    df['Total'] = df[PAYMENT_METHODS].sum(axis=1)
    return df

@st.cache_data
def process_data(df):
    """Main data processing pipeline"""
    if df.empty:
        return df
    
    # Validate required columns
    missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing_cols:
        st.error(f"Colunas obrigatórias faltando: {missing_cols}")
        return pd.DataFrame()
    
    df = process_dates(df)
    df = process_payments(df)
    
    return df

# --- Visualization Functions ---
def create_payment_pie_chart(data):
    """Create pie chart of payment method distribution"""
    payment_data = pd.DataFrame({
        'Método': PAYMENT_METHODS,
        'Valor': [data[method].sum() for method in PAYMENT_METHODS]
    }).query('Valor > 0')
    
    if payment_data.empty:
        return None
    
    pie = alt.Chart(payment_data).mark_arc(outerRadius=140, innerRadius=60).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        color=alt.Color("Método:N", scale=alt.Scale(scheme='category10'),
        tooltip=[
            alt.Tooltip("Método:N"),
            alt.Tooltip("Valor:Q", format=",.2f", title="Valor (R$)")
        ]
    )
    
    return pie

def create_daily_sales_chart(data):
    """Create bar chart of daily sales by payment method"""
    daily_data = data.groupby('DataFormatada')[PAYMENT_METHODS].sum().reset_index()
    daily_long = daily_data.melt(
        id_vars=['DataFormatada'],
        value_vars=PAYMENT_METHODS,
        var_name='Método',
        value_name='Valor'
    ).query('Valor > 0')
    
    if daily_long.empty:
        return None
    
    daily_long['Data'] = pd.to_datetime(daily_long['DataFormatada'], format='%d/%m/%Y')
    
    chart = alt.Chart(daily_long).mark_bar().encode(
        x=alt.X('Data:T', title='Data', axis=alt.Axis(format="%d/%m")),
        y=alt.Y('sum(Valor):Q', title='Valor (R$)'),
        color=alt.Color('Método:N', scale=alt.Scale(scheme='category10')),
        tooltip=[
            alt.Tooltip('DataFormatada', title='Data'),
            alt.Tooltip('Método:N'),
            alt.Tooltip('sum(Valor):Q', title='Valor (R$)', format=',.2f')
        ]
    ).interactive()
    
    return chart

def create_cumulative_chart(data):
    """Create line chart of cumulative sales"""
    df_sorted = data.sort_values('Data')
    daily_total = df_sorted.groupby('Data')['Total'].sum().reset_index()
    daily_total['Total Acumulado'] = daily_total['Total'].cumsum()
    
    if daily_total.empty:
        return None
    
    chart = alt.Chart(daily_total).mark_line(point=True).encode(
        x=alt.X('Data:T', title='Data'),
        y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
        tooltip=[
            alt.Tooltip('Data:T', format='%d/%m/%Y'),
            alt.Tooltip('Total Acumulado:Q', format=',.2f')
        ]
    ).interactive()
    
    return chart

def create_monthly_trend_chart(data):
    """Create bar chart of monthly sales"""
    monthly_data = data.groupby(['AnoMês', 'Ano', 'Mês'])['Total'].sum().reset_index()
    monthly_data = monthly_data.sort_values(['Ano', 'Mês'])
    
    if monthly_data.empty:
        return None
    
    chart = alt.Chart(monthly_data).mark_bar().encode(
        x=alt.X('AnoMês', title='Mês/Ano', sort=monthly_data['AnoMês'].tolist()),
        y=alt.Y('Total:Q', title='Total Vendido (R$)'),
        tooltip=[
            alt.Tooltip('AnoMês', title='Mês/Ano'),
            alt.Tooltip('Total:Q', format=",.2f")
        ]
    ).interactive()
    
    return chart

def create_weekday_chart(data):
    """Create bar chart of sales by weekday"""
    if 'DiaSemana' not in data.columns:
        return None
    
    weekday_data = data.groupby(['DiaSemanaNum', 'DiaSemana'])['Total'].mean().reset_index()
    
    if weekday_data.empty:
        return None
    
    chart = alt.Chart(weekday_data).mark_bar().encode(
        x=alt.X('DiaSemana', title='Dia da Semana', sort=WEEKDAY_ORDER),
        y=alt.Y('Total:Q', title='Média de Vendas (R$)'),
        color=alt.Color('DiaSemana', legend=None, scale=alt.Scale(scheme='category10')),
        tooltip=[
            alt.Tooltip('DiaSemana', title='Dia da Semana'),
            alt.Tooltip('Total:Q', format=",.2f")
        ]
    )
    
    return chart

# --- UI Components ---
def show_sales_form():
    """Render the sales registration form"""
    with st.form("venda_form"):
        date = st.date_input("Data", datetime.now())
        cols = st.columns(3)
        
        cartao = cols[0].number_input("Cartão (R$)", min_value=0.0, format="%.2f")
        dinheiro = cols[1].number_input("Dinheiro (R$)", min_value=0.0, format="%.2f")
        pix = cols[2].number_input("PIX (R$)", min_value=0.0, format="%.2f")
        
        total = cartao + dinheiro + pix
        st.markdown(f"**Total da venda: R$ {total:,.2f}**".replace(",", "#").replace(".", ",").replace("#", "."))
        
        if st.form_submit_button("Registrar Venda"):
            if total > 0:
                worksheet = get_worksheet_for_writing()
                if add_sale_record(
                    date.strftime('%d/%m/%Y'),
                    cartao,
                    dinheiro,
                    pix,
                    worksheet
                ):
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.warning("O valor total da venda deve ser maior que zero.")

def show_global_stats(df):
    """Display global statistics"""
    if df.empty:
        st.info("Não há dados suficientes para exibir estatísticas.")
        return
    
    st.subheader("Estatísticas Gerais")
    
    total_sales = df['Total'].sum()
    num_days = df['DataFormatada'].nunique()
    daily_avg = total_sales / num_days if num_days > 0 else 0
    
    # Best/worst day
    daily_sum = df.groupby('DataFormatada')['Total'].sum().reset_index()
    best_day = daily_sum.loc[daily_sum['Total'].idxmax()] if not daily_sum.empty else None
    worst_day = daily_sum[daily_sum['Total'] > 0].loc[daily_sum['Total'].idxmin()] if not daily_sum[daily_sum['Total'] > 0].empty else None
    
    # Payment totals
    payment_totals = {method: df[method].sum() for method in PAYMENT_METHODS}
    most_used = max(payment_totals, key=payment_totals.get) if any(payment_totals.values()) else "N/A"
    
    # Best month
    monthly_sum = df.groupby('AnoMês')['Total'].sum().reset_index()
    best_month = monthly_sum.loc[monthly_sum['Total'].idxmax()] if not monthly_sum.empty else None
    
    # Display metrics
    cols = st.columns(3)
    cols[0].metric("Vendas Totais", f"R$ {total_sales:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))
    cols[1].metric("Média Diária", f"R$ {daily_avg:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))
    cols[2].metric("Dias Registrados", num_days)
    
    st.divider()
    
    cols = st.columns(3)
    if best_day is not None:
        cols[0].metric("Melhor Dia", best_day['DataFormatada'], f"R$ {best_day['Total']:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))
    if worst_day is not None:
        cols[1].metric("Pior Dia (>R$0)", worst_day['DataFormatada'], f"R$ {worst_day['Total']:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))
    cols[2].metric("Pagamento Mais Usado", most_used, f"R$ {payment_totals.get(most_used, 0):,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))
    
    if best_month is not None:
        st.metric("Melhor Mês", best_month['AnoMês'], f"R$ {best_month['Total']:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))

def show_filtered_analysis(df):
    """Show filtered data analysis"""
    if df.empty:
        st.info("Não há dados para análise.")
        return
    
    st.subheader("Resumo do Período")
    
    total = df['Total'].sum()
    days = df['DataFormatada'].nunique()
    avg = total / days if days > 0 else 0
    
    cols = st.columns(3)
    cols[0].metric("Vendas Totais", f"R$ {total:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))
    cols[1].metric("Média Diária", f"R$ {avg:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))
    cols[2].metric("Dias Registrados", days)
    
    st.divider()
    
    # Visualizations
    st.subheader("Distribuição por Método de Pagamento")
    pie_chart = create_payment_pie_chart(df)
    st.altair_chart(pie_chart if pie_chart else st.info("Sem dados para gráfico"), use_container_width=True)
    
    st.subheader("Vendas Diárias por Método")
    daily_chart = create_daily_sales_chart(df)
    st.altair_chart(daily_chart if daily_chart else st.info("Sem dados para gráfico"), use_container_width=True)
    
    st.subheader("Acúmulo de Capital")
    cum_chart = create_cumulative_chart(df)
    st.altair_chart(cum_chart if cum_chart else st.info("Sem dados para gráfico"), use_container_width=True)
    
    st.subheader("Vendas Mensais")
    monthly_chart = create_monthly_trend_chart(df)
    st.altair_chart(monthly_chart if monthly_chart else st.info("Sem dados para gráfico"), use_container_width=True)
    
    st.subheader("Vendas por Dia da Semana")
    weekday_chart = create_weekday_chart(df)
    st.altair_chart(weekday_chart if weekday_chart else st.info("Sem dados para gráfico"), use_container_width=True)

def apply_filters(df):
    """Apply user filters to the data"""
    if df.empty:
        return df
    
    st.sidebar.header("Filtros")
    
    available_years = sorted(df['Ano'].dropna().unique().astype(int))
    selected_years = st.sidebar.multiselect(
        "Anos",
        options=available_years,
        default=available_years
    )
    
    df_filtered = df[df['Ano'].isin(selected_years)]
    
    if df_filtered.empty:
        return df_filtered
    
    # Month selection with names
    month_map = {m: datetime(2020, m, 1).strftime('%B').capitalize() 
                for m in df_filtered['Mês'].dropna().unique().astype(int)}
    month_options = [f"{m} - {month_map[m]}" for m in month_map]
    
    selected_months_str = st.sidebar.multiselect(
        "Meses",
        options=month_options,
        default=month_options
    )
    
    selected_months = [int(m.split(" - ")[0]) for m in selected_months_str]
    df_filtered = df_filtered[df_filtered['Mês'].isin(selected_months)]
    
    return df_filtered

def show_data_table(df):
    """Display filtered data in a table"""
    if df.empty:
        return
    
    st.subheader("Dados Filtrados")
    
    display_cols = {
        'DataFormatada': 'Data',
        'Cartão': 'Cartão (R$)',
        'Dinheiro': 'Dinheiro (R$)',
        'Pix': 'Pix (R$)',
        'Total': 'Total (R$)'
    }
    
    st.dataframe(
        df[list(display_cols.keys())].rename(columns=display_cols),
        use_container_width=True,
        hide_index=True
    )

# --- Main Application ---
def main():
    setup_locale()
    setup_page_config()
    
    st.title("📊 Sistema de Registro e Análise de Vendas")
    
    # Load and process data
    with st.spinner("Carregando dados..."):
        df_raw = load_sheet_data()
        df_processed = process_data(df_raw)
    
    # Create tabs
    tab1, tab2 = st.tabs(["📈 Registrar & Estatísticas", "🔍 Análise Detalhada"])
    
    with tab1:
        show_sales_form()
        st.divider()
        show_global_stats(df_processed)
    
    with tab2:
        if df_processed.empty:
            st.info("Não há dados suficientes para análise.")
        else:
            df_filtered = apply_filters(df_processed)
            show_data_table(df_filtered)
            st.divider()
            show_filtered_analysis(df_filtered)

if __name__ == "__main__":
    main()