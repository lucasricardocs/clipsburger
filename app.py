import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import random
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# --- CONSTANTES E CONFIGURAÇÕES ---
CONFIG = {
    "page_title": "Gestão - Clips Burger",
    "layout": "wide",
    "sidebar_state": "expanded",
    "logo_path": "logo.png"
}

CARDAPIOS = {
    "sanduiches": {
        "X Salada Simples": 18.00,
        "X Salada Especial": 20.00,
        "X Bacon Simples": 22.00,
        "X Bacon Especial": 24.00,
        "X Hamburgão": 35.00,
        "X Mata-Fome": 39.00,
        "X Frango Simples": 22.00,
        "X Frango Especial": 24.00,
        "X Frango Bacon": 27.00,
        "X Frango Tudo": 30.00,
        "X Lombo Simples": 23.00,
        "X Lombo Especial": 26.00,
        "X Lombo Bacon": 28.00,
        "X Lombo Tudo": 31.00,
        "X Filé Simples": 28.00,
        "X Filé Especial": 30.00,
        "X Filé Bacon": 33.00,
        "X Filé Tudo": 36.00
    },
    "bebidas": {
        "Suco": 10.00,
        "Creme": 15.00,
        "Refri caçula": 3.50,
        "Refri Lata": 7.00,
        "Refri 600": 8.00,
        "Refri 1L": 10.00,
        "Refri 2L": 15.00,
        "Água": 3.00,
        "Água com Gas": 4.00
    }
}

FORMAS_PAGAMENTO = {
    'crédito à vista elo': 'Crédito Elo',
    'crédito à vista mastercard': 'Crédito MasterCard',
    'crédito à vista visa': 'Crédito Visa',
    'crédito à vista american express': 'Crédito Amex',
    'débito elo': 'Débito Elo',
    'débito mastercard': 'Débito MasterCard',
    'débito visa': 'Débito Visa',
    'pix': 'PIX'
}

# --- FUNÇÕES UTILITÁRIAS ---
def format_currency(value):
    """Formata um valor como moeda brasileira."""
    if pd.isna(value) or value is None:
        return "R$ -"
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def calculate_combination_value(combination, item_prices):
    """Calcula o valor total de uma combinação."""
    return sum(item_prices.get(name, 0) * quantity for name, quantity in combination.items())

# --- FUNÇÕES PARA GOOGLE SHEETS ---
@st.cache_data(ttl=600)
def get_google_sheet_data():
    """Obtém dados da planilha Google Sheets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_info(st.secrets["google_credentials"], scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key('1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg')
        worksheet = spreadsheet.worksheet('Vendas')
        return pd.DataFrame(worksheet.get_all_records())
    except Exception as e:
        st.error(f"Erro ao acessar Google Sheets: {e}")
        return pd.DataFrame()

def process_transactions(df):
    """Processa os dados de transações."""
    if df.empty:
        return df
    
    df['Tipo'] = df['Tipo'].str.lower().str.strip().fillna('desconhecido')
    df['Bandeira'] = df['Bandeira'].str.lower().str.strip().fillna('desconhecida')
    df['Valor'] = pd.to_numeric(df['Valor'].str.replace('.', '').str.replace(',', '.'), errors='coerce')
    df = df.dropna(subset=['Valor'])
    df['Forma'] = (df['Tipo'] + ' ' + df['Bandeira']).map(FORMAS_PAGAMENTO)
    return df.dropna(subset=['Forma'])

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title=CONFIG["page_title"],
    layout=CONFIG["layout"],
    initial_sidebar_state=CONFIG["sidebar_state"]
)

# --- INTERFACE PRINCIPAL ---
col_title1, col_title2 = st.columns([0.30, 0.70])
with col_title1:
    try:
        st.image(CONFIG["logo_path"], width=150)
    except FileNotFoundError:
        st.warning("Logo não encontrada")
with col_title2:
    st.title("Sistema de Gestão")
    st.markdown("<p style='font-weight:bold; font-size:30px; margin-top:-15px'>Clip's Burger</p>", 
               unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configurações")
    drink_percentage = st.slider("Percentual para Bebidas (%) 🍹", 0, 100, 20, 5)
    st.caption(f"({100 - drink_percentage}% para Sanduíches 🍔)")
    
    algoritmo = st.radio("Algoritmo para Combinações", ["Busca Local", "Algoritmo Genético"])
    
    if algoritmo == "Busca Local":
        max_iterations = st.select_slider("Qualidade da Otimização ✨", 
                                        options=[1000, 5000, 10000, 20000, 50000],
                                        value=10000)
    else:
        population_size = st.slider("Tamanho da População", 20, 200, 50, 10)
        generations = st.slider("Número de Gerações", 10, 500, 100, 10)

# --- ABAS PRINCIPAIS ---
tab1, tab2 = st.tabs(["📊 Painel de Vendas", "🧩 Análise de Combinações"])

with tab1:
    df_raw = get_google_sheet_data()
    df = process_transactions(df_raw)
    
    if not df.empty:
        # Filtros de período
        st.sidebar.header("🔍 Filtros Temporais")
        min_date = pd.to_datetime(df['Data']).min().date()
        max_date = pd.to_datetime(df['Data']).max().date()
        
        date_range = st.sidebar.date_input(
            "Selecione o período:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            df_filtered = df[(pd.to_datetime(df['Data']) >= pd.to_datetime(start_date)) & 
                            (pd.to_datetime(df['Data']) <= pd.to_datetime(end_date))]
        else:
            df_filtered = df.copy()
        
        # Métricas principais
        total_vendas = df_filtered['Valor'].sum()
        vendas_por_forma = df_filtered.groupby('Forma')['Valor'].sum().reset_index()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Faturamento Total", format_currency(total_vendas))
        with col2:
            st.metric("Transações", len(df_filtered))
        with col3:
            st.metric("Ticket Médio", format_currency(df_filtered['Valor'].mean()))
        
        # Gráfico de vendas por forma de pagamento
        st.subheader("Vendas por Forma de Pagamento")
        chart_forma = alt.Chart(vendas_por_forma).mark_bar().encode(
            x=alt.X('Forma:N', sort='-y', title='Forma de Pagamento'),
            y=alt.Y('Valor:Q', title='Valor (R$)'),
            color=alt.Color('Forma:N', legend=None),
            tooltip=['Forma', alt.Tooltip('Valor:Q', format='$.2f', title='Total')]
        ).properties(height=400)
        st.altair_chart(chart_forma, use_container_width=True)
        
        # Evolução diária
        st.subheader("Evolução Diária das Vendas")
        df_daily = df_filtered.copy()
        df_daily['Data'] = pd.to_datetime(df_daily['Data'])
        df_daily = df_daily.groupby('Data')['Valor'].sum().reset_index()
        
        line_chart = alt.Chart(df_daily).mark_line(point=True).encode(
            x=alt.X('Data:T', title='Data'),
            y=alt.Y('Valor:Q', title='Valor (R$)'),
            tooltip=[alt.Tooltip('Data:T', format='%d/%m/%Y'), 'Valor']
        ).properties(height=400)
        st.altair_chart(line_chart, use_container_width=True)
        
        # Estatísticas curiosas
        st.subheader("📌 Insights e Estatísticas")
        cols = st.columns(2)
        with cols[0]:
            st.metric("Forma de Pagamento Mais Usada", df_filtered['Forma'].mode()[0])
            st.metric("Maior Venda Única", format_currency(df_filtered['Valor'].max()))
        with cols[1]:
            st.metric("Dias com Vendas", df_daily.shape[0])
            st.metric("Percentual PIX", f"{(df_filtered[df_filtered['Forma'] == 'PIX']['Valor'].sum() / total_vendas * 100):.1f}%")
        
        # Detalhamento dos dados
        with st.expander("🔍 Visualizar Dados Detalhados"):
            st.dataframe(df_filtered.sort_values('Data', ascending=False))
    else:
        st.warning("Nenhum dado encontrado na planilha.")

with tab2:
    st.header("🧩 Análise de Combinações")
    
    if 'df' in locals() and not df.empty:
        vendas_por_forma = df.groupby('Forma')['Valor'].sum().reset_index()
        forma_selecionada = st.selectbox(
            "Selecione a forma de pagamento para análise:",
            options=vendas_por_forma['Forma'].tolist(),
            format_func=lambda x: f"{x} ({format_currency(vendas_por_forma.loc[vendas_por_forma['Forma'] == x, 'Valor'].iloc[0])})"
        )
        
        valor_total = vendas_por_forma.loc[vendas_por_forma['Forma'] == forma_selecionada, 'Valor'].iloc[0]
        valor_sanduiches = valor_total * (1 - drink_percentage/100)
        valor_bebidas = valor_total * (drink_percentage/100)
        
        st.write(f"**Valor total para combinações:** {format_currency(valor_total)}")
        st.write(f"**Distribuição:** {format_currency(valor_sanduiches)} em sanduíches ({100-drink_percentage}%) e {format_currency(valor_bebidas)} em bebidas ({drink_percentage}%)")
        
        # Gerar combinações
        if st.button("Gerar Combinações"):
            with st.spinner("Calculando melhores combinações..."):
                if algoritmo == "Algoritmo Genético":
                    combinacao_sanduiches = genetic_algorithm(
                        CARDAPIOS["sanduiches"], valor_sanduiches,
                        population_size=population_size, generations=generations
                    )
                    combinacao_bebidas = genetic_algorithm(
                        CARDAPIOS["bebidas"], valor_bebidas,
                        population_size=population_size, generations=generations
                    )
                else:
                    combinacao_sanduiches = local_search(
                        CARDAPIOS["sanduiches"], valor_sanduiches, max_iterations
                    )
                    combinacao_bebidas = local_search(
                        CARDAPIOS["bebidas"], valor_bebidas, max_iterations
                    )
                
                # Exibir resultados
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🍔 Sanduíches")
                    if combinacao_sanduiches:
                        df_sand = pd.DataFrame({
                            'Item': combinacao_sanduiches.keys(),
                            'Quantidade': combinacao_sanduiches.values(),
                            'Preço': [CARDAPIOS["sanduiches"][k] for k in combinacao_sanduiches.keys()]
                        })
                        df_sand['Subtotal'] = df_sand['Quantidade'] * df_sand['Preço']
                        st.dataframe(df_sand)
                        total_sand = df_sand['Subtotal'].sum()
                        st.metric("Total Sanduíches", format_currency(total_sand))
                
                with col2:
                    st.subheader("🍹 Bebidas")
                    if combinacao_bebidas:
                        df_beb = pd.DataFrame({
                            'Item': combinacao_bebidas.keys(),
                            'Quantidade': combinacao_bebidas.values(),
                            'Preço': [CARDAPIOS["bebidas"][k] for k in combinacao_bebidas.keys()]
                        })
                        df_beb['Subtotal'] = df_beb['Quantidade'] * df_beb['Preço']
                        st.dataframe(df_beb)
                        total_beb = df_beb['Subtotal'].sum()
                        st.metric("Total Bebidas", format_currency(total_beb))
                
                if combinacao_sanduiches and combinacao_bebidas:
                    st.success(f"Combinação total: {format_currency(total_sand + total_beb)} (Diferença: {format_currency((total_sand + total_beb) - valor_total)})")
    else:
        st.info("Carregue os dados na aba Painel de Vendas primeiro.")

# Rodapé
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: small;'>
        © 2025 Clips Burger - Sistema de Gestão | Desenvolvido com ❤️ e Streamlit
    </div>
    """, 
    unsafe_allow_html=True
)
