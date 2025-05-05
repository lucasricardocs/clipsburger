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

# --- FUNÇÕES PARA ALGORITMO GENÉTICO ---
def create_individual(item_prices, combination_size):
    """Cria uma combinação aleatória de itens."""
    items = list(item_prices.keys())
    size = min(combination_size, len(items))
    selected_items = random.sample(items, size)
    
    return {
        name: random.randint(1, 10)  # Quantidade entre 1 e 10
        for name in selected_items
    }

def evaluate_fitness(individual, item_prices, target_value):
    """Avalia quão boa é a combinação."""
    total = calculate_combination_value(individual, item_prices)
    return abs(target_value - total)

def crossover(parent1, parent2):
    """Combina duas soluções para gerar uma nova."""
    child = {}
    for key in set(parent1.keys()).union(set(parent2.keys())):
        if random.random() < 0.5:
            if key in parent1:
                child[key] = parent1[key]
        else:
            if key in parent2:
                child[key] = parent2[key]
    return child

def mutate(individual, item_prices, mutation_rate=0.1):
    """Aplica mutações aleatórias na combinação."""
    new_individual = individual.copy()
    
    # Mutação: alterar quantidade
    for item in new_individual:
        if random.random() < mutation_rate:
            new_individual[item] = max(1, new_individual[item] + random.randint(-2, 2))
    
    # Mutação: adicionar novo item
    if random.random() < mutation_rate and len(new_individual) < len(item_prices):
        available_items = [item for item in item_prices if item not in new_individual]
        if available_items:
            new_item = random.choice(available_items)
            new_individual[new_item] = random.randint(1, 5)
    
    # Mutação: remover item
    if random.random() < mutation_rate and len(new_individual) > 1:
        item_to_remove = random.choice(list(new_individual.keys()))
        del new_individual[item_to_remove]
    
    return new_individual

def genetic_algorithm(item_prices, target_value, population_size=50, generations=100):
    """Executa o algoritmo genético para encontrar combinações."""
    population = [create_individual(item_prices, 5) for _ in range(population_size)]
    
    for _ in range(generations):
        # Avaliação
        fitness = [(ind, evaluate_fitness(ind, item_prices, target_value)) for ind in population]
        fitness.sort(key=lambda x: x[1])
        
        # Seleção dos melhores
        best = fitness[:population_size//2]
        new_population = [ind[0] for ind in best]
        
        # Reprodução
        while len(new_population) < population_size:
            parent1 = random.choice(best)[0]
            parent2 = random.choice(best)[0]
            child = crossover(parent1, parent2)
            child = mutate(child, item_prices)
            new_population.append(child)
        
        population = new_population
    
    # Retorna a melhor combinação
    best_combination = min(population, key=lambda x: evaluate_fitness(x, item_prices, target_value))
    return {k: v for k, v in best_combination.items() if v > 0}

# --- FUNÇÕES PARA GOOGLE SHEETS ---
def get_google_sheet():
    """Conecta e retorna a planilha do Google Sheets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
                 'https://www.googleapis.com/auth/drive']
        
        creds = Credentials.from_service_account_info(st.secrets["google_credentials"], scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(st.secrets["spreadsheet_id"])
        worksheet = spreadsheet.worksheet('Vendas')
        return worksheet
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        return None

@st.cache_data(ttl=600)
def get_sheet_data():
    """Obtém os dados da planilha"""
    worksheet = get_google_sheet()
    if worksheet:
        try:
            records = worksheet.get_all_records()
            return pd.DataFrame(records)
        except Exception as e:
            st.error(f"Erro ao ler dados: {e}")
    return pd.DataFrame()

def add_sale_to_sheet(data, forma_pagamento, valor, observacao=""):
    """Adiciona uma nova venda à planilha"""
    worksheet = get_google_sheet()
    if worksheet:
        try:
            data_formatada = data.strftime('%d/%m/%Y')
            
            if "débito" in forma_pagamento.lower():
                tipo = "débito"
                bandeira = forma_pagamento.split()[-1].lower()
            elif "crédito" in forma_pagamento.lower():
                tipo = "crédito"
                bandeira = forma_pagamento.split()[-1].lower()
            else:
                tipo = forma_pagamento.lower()
                bandeira = ""
            
            new_row = [
                data_formatada,
                tipo,
                bandeira,
                float(valor),
                observacao
            ]
            
            worksheet.append_row(new_row)
            get_sheet_data.clear()
            return True
        except Exception as e:
            st.error(f"Erro ao adicionar venda: {e}")
    return False

# --- INTERFACE STREAMLIT ---
st.set_page_config(
    page_title=CONFIG["page_title"],
    layout=CONFIG["layout"],
    initial_sidebar_state=CONFIG["sidebar_state"]
)

# Sidebar
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

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Painel de Vendas", "🧩 Análise de Combinações", "💰 Cadastrar Vendas"])

with tab1:
    st.header("📤 Upload de Dados de Vendas")
    
    # Upload do arquivo CSV
    uploaded_file = st.file_uploader("Carregue seu arquivo de vendas (CSV)", type="csv")
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        
        # Processamento dos dados
        df['Tipo'] = df['Tipo'].str.lower().str.strip()
        df['Bandeira'] = df['Bandeira'].str.lower().str.strip()
        df['Valor'] = pd.to_numeric(df['Valor'].str.replace(',', '.'), errors='coerce')
        df = df.dropna(subset=['Valor'])
        
        df['Forma'] = df.apply(lambda x: f"{x['Tipo']} {x['Bandeira']}" if x['Bandeira'] else x['Tipo'], axis=1)
        df['Forma'] = df['Forma'].map(FORMAS_PAGAMENTO)
        df = df.dropna(subset=['Forma'])
        
        # Adicionar valor manual do PIX
        st.subheader("🔹 Valor Mensal do PIX")
        pix_value = st.number_input("Insira o valor total recebido via PIX no período:", 
                                   min_value=0.0, value=0.0, step=100.0)
        
        if pix_value > 0:
            # Adiciona o PIX como uma linha adicional
            pix_row = pd.DataFrame([{
                'Data': df['Data'].max(),
                'Tipo': 'pix',
                'Bandeira': '',
                'Valor': pix_value,
                'Forma': 'PIX'
            }])
            df = pd.concat([df, pix_row], ignore_index=True)
        
        # Agrupa por forma de pagamento
        vendas_por_forma = df.groupby('Forma')['Valor'].sum().reset_index()
        total_vendas = vendas_por_forma['Valor'].sum()
        
        # Exibe métricas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Faturamento Total", format_currency(total_vendas))
        with col2:
            st.metric("Número de Vendas", len(df))
        with col3:
            st.metric("Ticket Médio", format_currency(df['Valor'].mean()))
        
        # Gráfico de vendas por forma de pagamento
        st.subheader("📈 Distribuição por Forma de Pagamento")
        chart = alt.Chart(vendas_por_forma).mark_bar().encode(
            x='Forma:N',
            y='Valor:Q',
            color='Forma:N',
            tooltip=['Forma', 'Valor']
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)
        
        # Salva os dados na sessão para uso nas outras abas
        st.session_state.vendas_data = vendas_por_forma
        st.session_state.total_vendas = total_vendas
        st.session_state.df_vendas = df

with tab2:
    st.header("🧩 Análise de Combinações")
    
    if 'vendas_data' in st.session_state and not st.session_state.vendas_data.empty:
        vendas = st.session_state.vendas_data
        total_vendas = st.session_state.total_vendas
        
        forma_selecionada = st.selectbox(
            "Selecione a forma de pagamento para análise:",
            options=vendas['Forma'].unique(),
            format_func=lambda x: f"{x} ({format_currency(vendas.loc[vendas['Forma'] == x, 'Valor'].iloc[0])})"
        )
        
        valor_total = vendas.loc[vendas['Forma'] == forma_selecionada, 'Valor'].iloc[0]
        valor_sanduiches = valor_total * (1 - drink_percentage/100)
        valor_bebidas = valor_total * (drink_percentage/100)
        
        st.write(f"**Valor total para combinações:** {format_currency(valor_total)}")
        st.write(f"**Distribuição:** {format_currency(valor_sanduiches)} em sanduíches ({100-drink_percentage}%) e {format_currency(valor_bebidas)} em bebidas ({drink_percentage}%)")
        
        if st.button("🔍 Gerar Combinações"):
            with st.spinner("Calculando melhores combinações..."):
                if algoritmo == "Algoritmo Genético":
                    combinacao_sanduiches = genetic_algorithm(
                        CARDAPIOS["sanduiches"], 
                        valor_sanduiches,
                        population_size=population_size,
                        generations=generations
                    )
                    combinacao_bebidas = genetic_algorithm(
                        CARDAPIOS["bebidas"], 
                        valor_bebidas,
                        population_size=population_size,
                        generations=generations
                    )
                else:
                    # Implementação simplificada de busca local
                    combinacao_sanduiches = {}
                    best_diff = float('inf')
                    for _ in range(max_iterations):
                        candidate = create_individual(CARDAPIOS["sanduiches"], 5)
                        current_diff = evaluate_fitness(candidate, CARDAPIOS["sanduiches"], valor_sanduiches)
                        if current_diff < best_diff:
                            combinacao_sanduiches = candidate
                            best_diff = current_diff
                    
                    combinacao_bebidas = {}
                    best_diff = float('inf')
                    for _ in range(max_iterations):
                        candidate = create_individual(CARDAPIOS["bebidas"], 3)
                        current_diff = evaluate_fitness(candidate, CARDAPIOS["bebidas"], valor_bebidas)
                        if current_diff < best_diff:
                            combinacao_bebidas = candidate
                            best_diff = current_diff
                
                # Exibe os resultados
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🍔 Sanduíches")
                    if combinacao_sanduiches:
                        df_sand = pd.DataFrame({
                            'Item': combinacao_sanduiches.keys(),
                            'Quantidade': combinacao_sanduiches.values(),
                            'Preço Unitário': [CARDAPIOS["sanduiches"][k] for k in combinacao_sanduiches.keys()]
                        })
                        df_sand['Subtotal'] = df_sand['Quantidade'] * df_sand['Preço Unitário']
                        st.dataframe(df_sand)
                        total_sand = df_sand['Subtotal'].sum()
                        st.metric("Total Sanduíches", format_currency(total_sand), 
                                delta=format_currency(total_sand - valor_sanduiches))
                
                with col2:
                    st.subheader("🍹 Bebidas")
                    if combinacao_bebidas:
                        df_beb = pd.DataFrame({
                            'Item': combinacao_bebidas.keys(),
                            'Quantidade': combinacao_bebidas.values(),
                            'Preço Unitário': [CARDAPIOS["bebidas"][k] for k in combinacao_bebidas.keys()]
                        })
                        df_beb['Subtotal'] = df_beb['Quantidade'] * df_beb['Preço Unitário']
                        st.dataframe(df_beb)
                        total_beb = df_beb['Subtotal'].sum()
                        st.metric("Total Bebidas", format_currency(total_beb),
                                delta=format_currency(total_beb - valor_bebidas))
                
                if combinacao_sanduiches and combinacao_bebidas:
                    st.success(f"🔹 Combinação total: {format_currency(total_sand + total_beb)} (Diferença: {format_currency((total_sand + total_beb) - valor_total)})")
    else:
        st.info("Por favor, carregue os dados de vendas na primeira aba.")

with tab3:
    st.header("💰 Cadastrar Vendas Manualmente")
    
    with st.form("sales_form"):
        cols = st.columns(3)
        with cols[0]:
            sale_date = st.date_input("Data da Venda", value=datetime.now())
        with cols[1]:
            payment_method = st.selectbox(
                "Forma de Pagamento",
                options=list(FORMAS_PAGAMENTO.values()),
                index=7  # PIX como padrão
            )
        with cols[2]:
            amount = st.number_input("Valor (R$)", min_value=0.01, step=0.01, format="%.2f")
        
        observation = st.text_input("Observação (opcional)", max_chars=100)
        
        submitted = st.form_submit_button("💾 Salvar Venda")
        
        if submitted:
            if amount <= 0:
                st.error("O valor da venda deve ser maior que zero!")
            else:
                success = add_sale_to_sheet(sale_date, payment_method, amount, observation)
                if success:
                    st.success("Venda cadastrada com sucesso no Google Sheets!")
                    st.balloons()
                else:
                    st.error("Erro ao cadastrar venda. Verifique a conexão.")

    # Mostrar últimas vendas cadastradas
    st.header("Últimas Vendas")
    sales_data = get_sheet_data()
    
    if not sales_data.empty:
        sales_data['Data'] = pd.to_datetime(sales_data['Data'], format='%d/%m/%Y', errors='coerce')
        sales_data['Forma de Pagamento'] = sales_data.apply(
            lambda x: f"{x['Tipo'].title()} {x['Bandeira'].title()}" if x['Bandeira'] else x['Tipo'].title(),
            axis=1
        )
        
        st.dataframe(
            sales_data.sort_values('Data', ascending=False).head(10)[
                ['Data', 'Forma de Pagamento', 'Valor', 'Observação']
            ],
            column_config={
                "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
                "Valor": st.column_config.NumberColumn(format="%.2f")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Nenhuma venda cadastrada ainda.")

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
