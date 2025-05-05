# Adicionando as importações necessárias para PDF e algoritmo genético
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import random
import os
import numpy as np
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from io import BytesIO
import matplotlib.pyplot as plt
import io
import base64
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# --- CONSTANTES E CONFIGURAÇÕES ---
CONFIG = {
    "page_title": "Gestão - Clips Burger",
    "layout": "wide",
    "sidebar_state": "expanded",
    "excel_file": "recebimentos.xlsx",
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

def init_data_file():
    """Inicializa o arquivo de dados se não existir."""
    if not os.path.exists(CONFIG["excel_file"]):
        pd.DataFrame(columns=['Data', 'Dinheiro', 'Cartao', 'Pix']).to_excel(
            CONFIG["excel_file"], index=False)

def load_data():
    """Carrega os dados do arquivo Excel."""
    try:
        if os.path.exists(CONFIG["excel_file"]):
            df = pd.read_excel(CONFIG["excel_file"])
            if not df.empty:
                df['Data'] = pd.to_datetime(df['Data'])
                return df.sort_values('Data', ascending=False)
        return pd.DataFrame(columns=['Data', 'Dinheiro', 'Cartao', 'Pix'])
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(columns=['Data', 'Dinheiro', 'Cartao', 'Pix'])

def save_data(df):
    """Salva os dados no arquivo Excel."""
    try:
        df['Data'] = pd.to_datetime(df['Data'])
        df.to_excel(CONFIG["excel_file"], index=False)
        st.success("Dados salvos com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")

def round_to_50_or_00(value):
    """Arredonda para o múltiplo de 0.50 mais próximo."""
    return round(value * 2) / 2

def calculate_combination_value(combination, item_prices):
    """Calcula o valor total de uma combinação."""
    return sum(item_prices.get(name, 0) * quantity for name, quantity in combination.items())

# --- FUNÇÕES PARA ALGORITMO GENÉTICO ---
def create_individual(item_prices, combination_size):
    """Cria um indivíduo (combinação) aleatório para o algoritmo genético."""
    if not item_prices:
        return {}
    
    items = list(item_prices.keys())
    # Garante que não tentaremos selecionar mais itens do que existem
    size = min(combination_size, len(items))
    
    # Seleciona exatamente 'size' itens (sem repetição)
    selected_items = random.sample(items, size)
    
    return {
        name: round_to_50_or_00(random.uniform(1, 100))
        for name in selected_items 
    }

def evaluate_fitness(individual, item_prices, target_value):
    """Avalia a adequação de um indivíduo ao valor alvo."""
    total = calculate_combination_value(individual, item_prices)
    # Penalidade maior se exceder o valor alvo
    if total > target_value:
        return 1000 + abs(total - target_value)
    return abs(target_value - total)

def crossover(parent1, parent2):
    """Realiza o cruzamento entre dois pais para criar um filho."""
    # Cria um conjunto com todas as chaves dos dois pais
    all_keys = set(list(parent1.keys()) + list(parent2.keys()))
    child = {}
    
    for key in all_keys:
        if key in parent1 and key in parent2:
            # Se a chave existe em ambos os pais, escolhe um valor ou a média
            if random.random() < 0.5:
                child[key] = parent1[key]
            else:
                child[key] = parent2[key]
        elif key in parent1:
            # Se existe apenas no primeiro pai, 50% de chance de incluir
            if random.random() < 0.5:
                child[key] = parent1[key]
        elif key in parent2:
            # Se existe apenas no segundo pai, 50% de chance de incluir
            if random.random() < 0.5:
                child[key] = parent2[key]
    
    return child

def mutate(individual, item_prices, mutation_rate=0.2, max_items=5):
    """Aplica mutação a um indivíduo, respeitando o número máximo de itens."""
    new_individual = individual.copy()
    
    # Possivelmente adicionar um novo item (só se ainda não atingiu o máximo)
    if (random.random() < mutation_rate and 
        len(new_individual) < max_items and 
        len(new_individual) < len(item_prices)):
        
        possible_new_items = [item for item in item_prices.keys() if item not in new_individual]
        if possible_new_items:
            new_item = random.choice(possible_new_items)
            new_individual[new_item] = round_to_50_or_00(random.uniform(1, 100))
    
    # Possivelmente remover um item existente (só se tiver mais de 1 item)
    if random.random() < mutation_rate and len(new_individual) > 1:
        item_to_remove = random.choice(list(new_individual.keys()))
        del new_individual[item_to_remove]
    
    # Modificar quantidades existentes
    for key in list(new_individual.keys()):
        if random.random() < mutation_rate:
            change = random.choice([-1.0, -0.5, 0.5, 1.0])
            new_value = max(0.5, round_to_50_or_00(new_individual[key] + change))
            new_individual[key] = new_value
    
    return new_individual

def genetic_algorithm(item_prices, target_value, population_size=50, generations=100, 
                    combination_size=5, elite_size=5, tournament_size=3):
    """
    Implementa um algoritmo genético para encontrar combinações de produtos
    que se aproximem de um valor alvo.
    """
    if not item_prices or target_value <= 0:
        return {}
    
    # Inicializa a população
    population = [create_individual(item_prices, combination_size) for _ in range(population_size)]
    
    best_individual = {}
    best_fitness = float('inf')
    
    for generation in range(generations):
        # Avalia a população
        fitness_scores = [(individual, evaluate_fitness(individual, item_prices, target_value)) 
                         for individual in population]
        
        # Ordena por fitness (menor é melhor)
        fitness_scores.sort(key=lambda x: x[1])
        
        # Atualiza o melhor indivíduo se encontrarmos um melhor
        if fitness_scores[0][1] < best_fitness:
            best_individual = fitness_scores[0][0].copy()
            best_fitness = fitness_scores[0][1]
        
        # Se encontramos uma combinação perfeita ou muito próxima, terminamos
        if best_fitness < 0.01:
            break
        
        # Seleciona a elite para a próxima geração
        next_generation = [ind[0].copy() for ind in fitness_scores[:elite_size]]
        
        # Completa a próxima geração com novos indivíduos
        while len(next_generation) < population_size:
            # Seleção de torneio
            tournament = random.sample(fitness_scores, tournament_size)
            tournament.sort(key=lambda x: x[1])
            parent1 = tournament[0][0]
            
            tournament = random.sample(fitness_scores, tournament_size)
            tournament.sort(key=lambda x: x[1])
            parent2 = tournament[0][0]
            
            # Cruzamento
            child = crossover(parent1, parent2)
            
            # Mutação (passando o combination_size como max_items)
            child = mutate(child, item_prices, max_items=combination_size)
            
            next_generation.append(child)
        
        # Atualiza a população
        population = next_generation
    
    # Retorna combinação com valores arredondados
    return {k: round(v) for k, v in best_individual.items() if round(v) > 0}

# --- FUNÇÕES PARA GERAR PDF ---
def create_watermark(canvas, logo_path, width=400, height=400, opacity=0.1):
    """Adiciona a logo como marca d'água no PDF."""
    try:
        if os.path.exists(logo_path):
            canvas.saveState()
            canvas.setFillColorRGB(255, 255, 255, alpha=opacity)
            canvas.drawImage(logo_path, 
                         (A4[0] - width) / 2, 
                         (A4[1] - height) / 2, 
                         width=width, 
                         height=height,
                         mask='auto',
                         preserveAspectRatio=True)
            canvas.restoreState()
    except Exception as e:
        print(f"Erro ao adicionar marca d'água: {e}")

def fig_to_buffer(fig):
    """Converte uma figura matplotlib para buffer de bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    buf.seek(0)
    return buf

def create_pdf_report(df, vendas, total_vendas, imposto_simples, custo_funcionario, 
                    custo_contadora, total_custos, lucro_estimado, logo_path):
    """
    Cria um relatório em PDF com os dados financeiros.
    """
    buffer = BytesIO()
    
    # Configuração do documento
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=72, 
        leftMargin=72,
        topMargin=72, 
        bottomMargin=72
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading1']
    subheading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Lista de elementos do PDF
    elements = []
    
    # Logo no topo
    try:
        if os.path.exists(logo_path):
            img = Image(logo_path, width=2*inch, height=1.5*inch)
            img.hAlign = 'CENTER'
            elements.append(img)
            elements.append(Spacer(1, 0.5*inch))
    except Exception as e:
        print(f"Erro ao adicionar logo: {e}")
    
    # Título
    elements.append(Paragraph("Relatório Financeiro - Clips Burger", title_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Data do relatório
    elements.append(Paragraph(f"Data do relatório: {datetime.now().strftime('%d/%m/%Y')}", normal_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Resumo financeiro
    elements.append(Paragraph("Resumo Financeiro", heading_style))
    elements.append(Spacer(1, 0.1*inch))
    
    data = [
        ["Métrica", "Valor"],
        ["Faturamento Bruto", format_currency(total_vendas)],
        ["Imposto Simples (6%)", format_currency(imposto_simples)],
        ["Custo Funcionário CLT", format_currency(custo_funcionario)],
        ["Custo Contadora", format_currency(custo_contadora)],
        ["Total de Custos", format_currency(total_custos)],
        ["Lucro Estimado", format_currency(lucro_estimado)]
    ]
    
    table = Table(data, colWidths=[doc.width/2.5, doc.width/2.5])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, -1), (1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Gráficos
    elements.append(Paragraph("Análise de Vendas", heading_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Gráfico de barras - Vendas por Forma de Pagamento
    try:
        fig, ax = plt.subplots(figsize=(8, 5))
        vendas.plot(kind='bar', x='Forma', y='Valor', ax=ax, color='steelblue')
        ax.set_title('Vendas por Forma de Pagamento')
        ax.set_ylabel('Valor (R$)')
        ax.set_xlabel('')
        plt.tight_layout()
        
        img_buf = fig_to_buffer(fig)
        img = Image(img_buf, width=doc.width, height=4*inch)
        elements.append(img)
        elements.append(Spacer(1, 0.25*inch))
        plt.close(fig)
    except Exception as e:
        elements.append(Paragraph(f"Erro ao gerar gráfico de vendas: {e}", normal_style))
    
    # Gráfico de pizza - Composição dos Custos
    try:
        custos_df = pd.DataFrame({
            'Item': ['Impostos', 'Funcionário', 'Contadora'],
            'Valor': [imposto_simples, custo_funcionario, custo_contadora]
        })
        
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.pie(custos_df['Valor'], labels=custos_df['Item'], autopct='%1.1f%%', 
              startangle=90, shadow=True)
        ax.set_title('Composição dos Custos')
        plt.tight_layout()
        
        img_buf = fig_to_buffer(fig)
        img = Image(img_buf, width=doc.width, height=4*inch)
        elements.append(img)
        plt.close(fig)
    except Exception as e:
        elements.append(Paragraph(f"Erro ao gerar gráfico de custos: {e}", normal_style))
    
    # Tabela de vendas por forma de pagamento
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("Detalhamento por Forma de Pagamento", subheading_style))
    elements.append(Spacer(1, 0.1*inch))
    
    data = [["Forma de Pagamento", "Valor"]]
    for _, row in vendas.iterrows():
        data.append([row['Forma'], format_currency(row['Valor'])])
    
    table = Table(data, colWidths=[doc.width/2, doc.width/4])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
    ]))
    elements.append(table)
    
    # Rodapé
    elements.append(Spacer(1, inch))
    footer_text = "Este relatório foi gerado automaticamente pelo Sistema de Gestão da Clips Burger."
    elements.append(Paragraph(footer_text, normal_style))
    
    # Build do PDF com marca d'água
    def add_watermark(canvas, doc):
        create_watermark(canvas, logo_path, width=300, height=300, opacity=0.1)
    
    # Constrói o PDF
    doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)
    
    buffer.seek(0)
    return buffer

def create_altair_chart(data, chart_type, x_col, y_col, color_col=None, title=None, interactive=True):
    """Cria gráficos Altair com configuração padronizada."""
    if chart_type == 'line':
        chart = alt.Chart(data).mark_line(point=True).encode(
            x=alt.X(f'{x_col}:T', title=x_col),
            y=alt.Y(f'{y_col}:Q', title=y_col),
            tooltip=[x_col, y_col]
        )
    elif chart_type == 'bar':
        chart = alt.Chart(data).mark_bar().encode(
            x=alt.X(f'{x_col}:N', title=x_col),
            y=alt.Y(f'{y_col}:Q', title=y_col),
            color=alt.Color(f'{color_col}:N') if color_col else alt.value('steelblue'),
            tooltip=[x_col, y_col]
        )
    elif chart_type == 'pie':
        chart = alt.Chart(data).mark_arc().encode(
            theta=alt.Theta(f'{y_col}:Q', stack=True),
            color=alt.Color(f'{x_col}:N', legend=alt.Legend(title=x_col)),
            tooltip=[x_col, y_col]
        )
    
    chart = chart.properties(
        title=title if title else f'{y_col} por {x_col}',
        width=700,
        height=400
    )
    
    return chart.interactive() if interactive else chart

# --- FUNÇÕES PARA GOOGLE SHEETS ---
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
        return
    try:
        new_row = [date, float(cartao), float(dinheiro), float(pix)]
        worksheet.append_row(new_row)
        st.success("Dados registrados com sucesso!")
    except Exception as e:
        st.error(f"Erro ao adicionar dados: {e}")

def process_data(df):
    """Função para processar e preparar os dados"""
    if not df.empty:
        for col in ['Cartão', 'Dinheiro', 'Pix']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df['Total'] = df['Cartão'].fillna(0) + df['Dinheiro'].fillna(0) + df['Pix'].fillna(0)
        if 'Data' in df.columns:
            try:
                df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['MêsNome'] = df['Data'].dt.strftime('%B')
                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
            except ValueError:
                st.warning("Formato de data inconsistente na planilha.")
            except Exception as e:
                st.error(f"Erro ao processar a coluna 'Data': {e}")
    return df

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title=CONFIG["page_title"],
    layout=CONFIG["layout"],
    initial_sidebar_state=CONFIG["sidebar_state"]
)

# --- INICIALIZAÇÃO ---
init_data_file()
if 'df_receipts' not in st.session_state:
    st.session_state.df_receipts = load_data()
if 'uploaded_data' not in st.session_state:
    st.session_state.uploaded_data = None
if 'vendas_data' not in st.session_state:
    st.session_state.vendas_data = None

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

st.markdown("""
Bem-vindo(a)! Esta ferramenta ajuda a visualizar suas vendas por forma de pagamento
e tenta encontrar combinações *hipotéticas* de produtos que poderiam corresponder a esses totais.
""")
st.divider()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configurações")
    
    # Configurações do algoritmo
    st.subheader("Configurações de Análise")
    drink_percentage = st.slider(
        "Percentual para Bebidas (%) 🍹",
        min_value=0, max_value=100, value=20, step=5
    )
    st.caption(f"({100 - drink_percentage}% será alocado para Sanduíches 🍔)")

    tamanho_combinacao_bebidas = st.slider(
        "Número de tipos de Bebidas", 1, 10, 5, 1)
    tamanho_combinacao_sanduiches = st.slider(
        "Número de tipos de Sanduíches", 1, 10, 5, 1)
    
    # Seleção do algoritmo
    algoritmo = st.radio(
        "Algoritmo para Combinações",
        ["Busca Local", "Algoritmo Genético"]
    )
    
    if algoritmo == "Busca Local":
        max_iterations = st.select_slider(
            "Qualidade da Otimização ✨",
            options=[1000, 5000, 10000, 20000, 50000],
            value=10000
        )
    else:  # Algoritmo Genético
        population_size = st.slider(
            "Tamanho da População", 20, 200, 50, 10
        )
        generations = st.slider(
            "Número de Gerações", 10, 500, 100, 10
        )
        st.info("Algoritmo genético pode gerar combinações mais precisas.")
    
    st.info("Lembre-se: As combinações são aproximações heurísticas.")

# --- ABAS PRINCIPAIS ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 Resumo das Vendas", "🧩 Detalhes das Combinações", "💰 Cadastro de Recebimentos", "📊 Painel de Vendas (Google Sheets)"])

with tab1:
    # Seção de upload de arquivo
    st.header("📤 Upload de Dados")
    arquivo = st.file_uploader("Envie o arquivo de transações (.csv ou .xlsx)", 
                             type=["csv", "xlsx"])
    
    if arquivo:
        try:
            # Processamento do arquivo
            with st.spinner("Processando arquivo..."):
                # Verificar o tipo de arquivo
                if arquivo.name.endswith(".csv"):
                    try:
                        df = pd.read_csv(arquivo, sep=';', encoding='utf-8', dtype=str)
                    except pd.errors.ParserError:
                        arquivo.seek(0)
                        try:
                            df = pd.read_csv(arquivo, sep=',', encoding='utf-8', dtype=str)
                        except:
                            arquivo.seek(0)
                            df = pd.read_csv(arquivo, engine='python', dtype=str)
                else:
                    df = pd.read_excel(arquivo, dtype=str)
                
                # Verificar colunas obrigatórias
                required_cols = ['Tipo', 'Bandeira', 'Valor']
                if not all(col in df.columns for col in required_cols):
                    st.error(f"Erro: O arquivo precisa conter as colunas: {', '.join(required_cols)}")
                    st.stop()

                # Processamento dos dados
                df['Tipo'] = df['Tipo'].str.lower().str.strip().fillna('desconhecido')
                df['Bandeira'] = df['Bandeira'].str.lower().str.strip().fillna('desconhecida')
                df['Valor'] = pd.to_numeric(
                    df['Valor'].str.replace('.', '').str.replace(',', '.'), 
                    errors='coerce')
                df = df.dropna(subset=['Valor'])
                
                df['Forma'] = (df['Tipo'] + ' ' + df['Bandeira']).map(FORMAS_PAGAMENTO)
                df = df.dropna(subset=['Forma'])
                
                if df.empty:
                    st.warning("Nenhuma transação válida encontrada.")
                    st.stop()

                vendas = df.groupby('Forma')['Valor'].sum().reset_index()
                total_vendas = vendas['Valor'].sum()
                
                # Salva os dados no session state
                st.session_state.uploaded_data = df
                st.session_state.vendas_data = vendas
                st.session_state.total_vendas = total_vendas
            
            # Seção de Visualização de Dados
            st.header("📊 Visualização de Dados")
            
            # Gráfico de Barras
            st.subheader("Total de Vendas por Forma de Pagamento")
            bar_chart = create_altair_chart(
                vendas, 'bar', 'Forma', 'Valor', 'Forma',
                title=''
            ).properties(
                width=800,
                height=500
            )
            st.altair_chart(bar_chart, use_container_width=True)
            
            # Seção de Parâmetros Financeiros
            st.header("⚙️ Parâmetros Financeiros")
            col1, col2 = st.columns(2)
            with col1:
                salario_minimo = st.number_input("Salário Mínimo (R$)", value=1518.0, step=50.0)
            with col2:
                custo_contadora = st.number_input("Custo com Contadora (R$)", value=316.0, step=10.0)
            
            # Seção de Resultados
            st.header("💰 Resultados Financeiros")
            
            # Métricas Principais
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Faturamento Bruto", format_currency(total_vendas))
            with col2:
                imposto_simples = total_vendas * 0.06
                st.metric("Imposto Simples (6%)", format_currency(imposto_simples))
            with col3:
                fgts = salario_minimo * 0.08
                ferias = (salario_minimo / 12) * (4/3)
                decimo_terceiro = salario_minimo / 12
                custo_funcionario = salario_minimo + fgts + ferias + decimo_terceiro
                st.metric("Custo Funcionário CLT", format_currency(custo_funcionario))
            
            # Cálculo do Total de Custos
            total_custos = imposto_simples + custo_funcionario + custo_contadora
            lucro_estimado = total_vendas - total_custos
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de Custos", format_currency(total_custos))
            with col2:
                st.metric("Lucro Estimado", format_currency(lucro_estimado))
            
            # Seção de Detalhamento
            st.header("🔍 Detalhamento")
            
            tab_detalhes1, tab_detalhes2, tab_detalhes3 = st.tabs([
                "📝 Composição de Custos", 
                "📚 Explicação dos Cálculos",
                "🍰 Gráfico de Composição"
            ])
            
            with tab_detalhes1:
                st.subheader("Composição dos Custos")
                st.markdown(f"""
                - **Imposto Simples Nacional (6%)**: {format_currency(imposto_simples)}
                - **Custo Funcionário CLT**: {format_currency(custo_funcionario)}
                - **Custo Contadora**: {format_currency(custo_contadora)}
                """)
            
            with tab_detalhes2:
                st.subheader("Fórmulas Utilizadas")
                st.markdown("""
                **1. Imposto Simples Nacional**  
                `Faturamento Bruto × 6%`  
                
                **2. Custo Funcionário CLT**  
                `Salário + FGTS (8%) + Férias (1 mês + 1/3) + 13º Salário`  
                
                **3. Total de Custos**  
                `Imposto + Funcionário + Contadora`  
                
                **4. Lucro Estimado**  
                `Faturamento Bruto - Total de Custos`
                """)
            
            with tab_detalhes3:
                st.subheader("Composição dos Custos")
                custos_df = pd.DataFrame({
                    'Item': ['Impostos', 'Funcionário', 'Contadora'],
                    'Valor': [imposto_simples, custo_funcionario, custo_contadora]
                })
                
                graf_composicao = alt.Chart(custos_df).mark_arc().encode(
                    theta='Valor',
                    color='Item',
                    tooltip=['Item', alt.Tooltip('Valor', format='$.2f')]
                ).properties(
                    width=600,
                    height=500
                )
                
                st.altair_chart(graf_composicao, use_container_width=True)
            
            # Seção de Relatório PDF
            st.header("📑 Relatório")
            if st.button("Gerar Relatório PDF"):
                with st.spinner("Gerando relatório..."):
                    pdf_buffer = create_pdf_report(
                        df, vendas, total_vendas, imposto_simples, custo_funcionario, 
                        custo_contadora, total_custos, lucro_estimado, CONFIG["logo_path"]
                    )
                    
                    # Criando um link para download
                    b64_pdf = base64.b64encode(pdf_buffer.getvalue()).decode()
                    pdf_display = f'<a href="data:application/pdf;base64,{b64_pdf}" download="relatorio_clips_burger.pdf">📥 Clique aqui para baixar o Relatório PDF</a>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                    
                    st.success("Relatório gerado com sucesso!")
            
        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo: {str(e)}")
            st.exception(e)
    else:

with tab2:
    st.header("🧩 Análise de Combinações")
    
    if st.session_state.vendas_data is not None:
        vendas = st.session_state.vendas_data
        total_vendas = st.session_state.total_vendas
        
        # Seleção da forma de pagamento para análise
        forma_selecionada = st.selectbox(
            "Selecione a forma de pagamento",
            options=vendas['Forma'].tolist(),
            format_func=lambda x: f"{x} ({format_currency(vendas.loc[vendas['Forma'] == x, 'Valor'].iloc[0])})"
        )
        
        valor_selecionado = vendas.loc[vendas['Forma'] == forma_selecionada, 'Valor'].iloc[0]
        st.subheader(f"Valor total: {format_currency(valor_selecionado)}")
        
        # Distribuição entre sanduíches e bebidas
        valor_sanduiches = valor_selecionado * (1 - drink_percentage/100)
        valor_bebidas = valor_selecionado * (drink_percentage/100)
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"Valor para Sanduíches: {format_currency(valor_sanduiches)} ({100-drink_percentage}%)")
        with col2:
            st.info(f"Valor para Bebidas: {format_currency(valor_bebidas)} ({drink_percentage}%)")
        
        # Encontrar combinações
        with st.spinner("Calculando possíveis combinações..."):
            if algoritmo == "Algoritmo Genético":
                combinacao_sanduiches = genetic_algorithm(
                    CARDAPIOS["sanduiches"], 
                    valor_sanduiches,
                    population_size=population_size,
                    generations=generations,
                    combination_size=tamanho_combinacao_sanduiches
                )
                
                combinacao_bebidas = genetic_algorithm(
                    CARDAPIOS["bebidas"], 
                    valor_bebidas,
                    population_size=population_size,
                    generations=generations,
                    combination_size=tamanho_combinacao_bebidas
                )
            else:  # Busca Local
                best_sanduiches = {}
                best_diff_sanduiches = float('inf')
                
                for _ in range(max_iterations):
                    candidate = create_individual(CARDAPIOS["sanduiches"], tamanho_combinacao_sanduiches)
                    candidate = mutate(candidate, CARDAPIOS["sanduiches"], mutation_rate=0.3, max_items=tamanho_combinacao_sanduiches)
                    
                    diff = evaluate_fitness(candidate, CARDAPIOS["sanduiches"], valor_sanduiches)
                    if diff < best_diff_sanduiches:
                        best_sanduiches = candidate
                        best_diff_sanduiches = diff
                
                combinacao_sanduiches = {k: round(v) for k, v in best_sanduiches.items() if round(v) > 0}
                
                best_bebidas = {}
                best_diff_bebidas = float('inf')
                
                for _ in range(max_iterations):
                    candidate = create_individual(CARDAPIOS["bebidas"], tamanho_combinacao_bebidas)
                    candidate = mutate(candidate, CARDAPIOS["bebidas"], mutation_rate=0.3, max_items=tamanho_combinacao_bebidas)
                    
                    diff = evaluate_fitness(candidate, CARDAPIOS["bebidas"], valor_bebidas)
                    if diff < best_diff_bebidas:
                        best_bebidas = candidate
                        best_diff_bebidas = diff
                
                combinacao_bebidas = {k: round(v) for k, v in best_bebidas.items() if round(v) > 0}
        
        # Calcular valores reais
        valor_real_sanduiches = calculate_combination_value(combinacao_sanduiches, CARDAPIOS["sanduiches"])
        valor_real_bebidas = calculate_combination_value(combinacao_bebidas, CARDAPIOS["bebidas"])
        valor_real_total = valor_real_sanduiches + valor_real_bebidas
        
        # Exibir combinações
        st.subheader("Combinação Sugerida")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🍔 Sanduíches")
            if combinacao_sanduiches:
                df_sanduiches = pd.DataFrame({
                    'Qnt': list(combinacao_sanduiches.values()),
                    'Produto': list(combinacao_sanduiches.keys()),
                    'Preço Unitário': [CARDAPIOS["sanduiches"][item] for item in combinacao_sanduiches.keys()],
                    'Subtotal': [CARDAPIOS["sanduiches"][item] * qtd for item, qtd in combinacao_sanduiches.items()]
                })
                df_sanduiches = df_sanduiches.sort_values('Subtotal', ascending=False)
                
                st.dataframe(
                    df_sanduiches.style.format({
                        'Preço Unitário': 'R$ {:.2f}',
                        'Subtotal': 'R$ {:.2f}'
                    }),
                    hide_index=True,
                    use_container_width=True
                )
                
                st.metric(
                    "Total Sanduíches", 
                    format_currency(valor_real_sanduiches),
                    delta=format_currency(valor_real_sanduiches - valor_sanduiches)
                )
            else:
                st.info("Não foi possível encontrar uma combinação para sanduíches.")
        
        with col2:
            st.markdown("### 🍹 Bebidas")
            if combinacao_bebidas:
                df_bebidas = pd.DataFrame({
                    'Qnt': list(combinacao_bebidas.values()),
                    'Produto': list(combinacao_bebidas.keys()),
                    'Preço Unitário': [CARDAPIOS["bebidas"][item] for item in combinacao_bebidas.keys()],
                    'Subtotal': [CARDAPIOS["bebidas"][item] * qtd for item, qtd in combinacao_bebidas.items()]
                })
                df_bebidas = df_bebidas.sort_values('Subtotal', ascending=False)
                
                st.dataframe(
                    df_bebidas.style.format({
                        'Preço Unitário': 'R$ {:.2f}',
                        'Subtotal': 'R$ {:.2f}'
                    }),
                    hide_index=True,
                    use_container_width=True
                )
                
                st.metric(
                    "Total Bebidas", 
                    format_currency(valor_real_bebidas),
                    delta=format_currency(valor_real_bebidas - valor_bebidas)
                )
            else:
                st.info("Não foi possível encontrar uma combinação para bebidas.")
        
        # Total geral
        st.markdown("### 💰 Total")
        st.metric(
            "Valor Total da Combinação", 
            format_currency(valor_real_total),
            delta=format_currency(valor_real_total - valor_selecionado)
        )
        
        # Disclaimer
        st.warning("""
        **Atenção:** Esta é apenas uma combinação hipotética que corresponde aproximadamente 
        ao valor vendido. O número real de produtos pode variar. Use essa informação apenas 
        como um indicativo para análise de vendas.
        """)
        
    else:
        st.info("Faça o upload de dados na aba 'Resumo das Vendas' para visualizar possíveis combinações.")

with tab3:
    st.header("💰 Cadastro e Análise de Recebimentos")
    
    # Seção 1: Formulário para adicionar novos dados
    with st.expander("➕ Adicionar Novo Registro", expanded=True):
        with st.form("add_receipt_form"):
            cols = st.columns([1, 1, 1, 1])
            with cols[0]:
                data = st.date_input("Data*", value=datetime.now())
            
            st.write("**Valores por Forma de Pagamento**")
            cols = st.columns(3)
            with cols[0]:
                dinheiro = st.number_input("Dinheiro (R$)*", min_value=0.0, step=10.0)
            with cols[1]:
                cartao = st.number_input("Cartão (R$)*", min_value=0.0, step=10.0)
            with cols[2]:
                pix = st.number_input("PIX (R$)*", min_value=0.0, step=10.0)
            
            total_dia = dinheiro + cartao + pix
            st.metric("Total do Dia", format_currency(total_dia))
            
            submitted = st.form_submit_button("✅ Salvar Registro")
            
            if submitted:
                if total_dia <= 0:
                    st.error("O total do dia deve ser maior que zero!")
                else:
                    try:
                        new_record = pd.DataFrame({
                            'Data': [data],
                            'Dinheiro': [dinheiro],
                            'Cartao': [cartao],
                            'Pix': [pix]
                        })
                        st.session_state.df_receipts = pd.concat(
                            [st.session_state.df_receipts, new_record], 
                            ignore_index=True
                        )
                        save_data(st.session_state.df_receipts)
                        st.success("Registro salvo com sucesso!")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {str(e)}")

    # Seção 2: Visualização dos dados e gráficos
    if not st.session_state.df_receipts.empty:
        # Filtros de data
        st.subheader("📅 Filtros de Período")
        
        # Opções de filtro
        filtro_tipo = st.radio("Tipo de Filtro:", 
                             ["Intervalo de Datas", "Mês Específico"], 
                             horizontal=True)
        
        if filtro_tipo == "Intervalo de Datas":
            cols = st.columns(2)
            with cols[0]:
                inicio = st.date_input("Data inicial", 
                                     value=st.session_state.df_receipts['Data'].min())
            with cols[1]:
                fim = st.date_input("Data final", 
                                  value=st.session_state.df_receipts['Data'].max())
        else:
            # Filtro por mês
            meses_disponiveis = sorted(st.session_state.df_receipts['Data'].dt.to_period('M').unique(), reverse=True)
            mes_selecionado = st.selectbox("Selecione o mês:", 
                                         options=meses_disponiveis,
                                         format_func=lambda x: x.strftime('%B/%Y'))
            
            inicio = pd.to_datetime(mes_selecionado.start_time)
            fim = pd.to_datetime(mes_selecionado.end_time)
        
        # Aplica filtros
        df_filtered = st.session_state.df_receipts[
            (st.session_state.df_receipts['Data'] >= pd.to_datetime(inicio)) & 
            (st.session_state.df_receipts['Data'] <= pd.to_datetime(fim))
        ].copy()
        
        if not df_filtered.empty:
            # Adiciona coluna de Total
            df_filtered['Total'] = df_filtered['Dinheiro'] + df_filtered['Cartao'] + df_filtered['Pix']
            
            # Calcula totais por forma de pagamento
            totais = {
                'Dinheiro': df_filtered['Dinheiro'].sum(),
                'Cartão': df_filtered['Cartao'].sum(),
                'PIX': df_filtered['Pix'].sum()
            }
            total_periodo = sum(totais.values())
            
            # Seção 3: Métricas Resumo
            st.subheader("📊 Resumo do Período")
            
            # CSS para ajustar o tamanho das métricas
            st.markdown("""
            <style>
                div[data-testid="stMetric"] {
                    padding: 5px 10px;
                }
                div[data-testid="stMetric"] > div {
                    gap: 2px;
                }
                div[data-testid="stMetric"] label {
                    font-size: 14px !important;
                    font-weight: 500 !important;
                    color: #6b7280 !important;
                }
                div[data-testid="stMetric"] > div > div {
                    font-size: 18px !important;
                    font-weight: 600 !important;
                }
            </style>
            """, unsafe_allow_html=True)
            
            # Layout compacto em 2 linhas de 4 colunas
            cols1 = st.columns(4)
            cols2 = st.columns(4)
            
            with cols1[0]:
                st.metric("Dinheiro", format_currency(totais['Dinheiro']), 
                         help="Total em recebimentos de dinheiro")
            with cols1[1]:
                st.metric("Cartão", format_currency(totais['Cartão']),
                         help="Total em recebimentos por cartão")
            with cols1[2]:
                st.metric("PIX", format_currency(totais['PIX']),
                         help="Total em recebimentos por PIX")
            with cols1[3]:
                st.metric("Total Geral", format_currency(total_periodo),
                         help="Soma de todas as formas de pagamento")
            
            with cols2[0]:
                st.metric("Média Diária", format_currency(df_filtered['Total'].mean()),
                         help="Média de vendas por dia")
            with cols2[1]:
                st.metric("Maior Venda", format_currency(df_filtered['Total'].max()),
                         help=f"Dia: {df_filtered.loc[df_filtered['Total'].idxmax(), 'Data'].strftime('%d/%m')}")
            with cols2[2]:
                st.metric("Dias Registrados", len(df_filtered),
                         help="Total de dias com vendas registradas")
            with cols2[3]:
                st.metric("Dias sem Registro", (fim - inicio).days + 1 - len(df_filtered),
                         help="Dias do período sem vendas registradas")
            
            # Seção 4: Gráficos
            st.subheader("📈 Visualizações Gráficas")
            
            tab_graficos1, tab_graficos2, tab_graficos3 = st.tabs(["Distribuição", "Comparação", "Acumulado"])
            
            with tab_graficos1:
                # Gráfico de Pizza
                df_pie = pd.DataFrame({
                    'Forma': list(totais.keys()),
                    'Valor': list(totais.values())
                })
                
                pie_chart = alt.Chart(df_pie).mark_arc().encode(
                    theta='Valor',
                    color=alt.Color('Forma', legend=alt.Legend(title="Forma de Pagamento")),
                    tooltip=['Forma', 'Valor']
                ).properties(
                    height=400,
                    title='Distribuição dos Recebimentos'
                )
                st.altair_chart(pie_chart, use_container_width=True)
            
            with tab_graficos2:
                # Gráfico de Barras
                df_bar = df_filtered.melt(id_vars=['Data'], 
                                        value_vars=['Dinheiro', 'Cartao', 'Pix'],
                                        var_name='Forma', 
                                        value_name='Valor')
                
                bar_chart = alt.Chart(df_bar).mark_bar().encode(
                    x='monthdate(Data):O',
                    y='sum(Valor):Q',
                    color='Forma',
                    tooltip=['Forma', 'sum(Valor)']
                ).properties(
                    height=400,
                    title='Vendas por Forma de Pagamento'
                )
                st.altair_chart(bar_chart, use_container_width=True)
            
            with tab_graficos3:
                # Gráfico Acumulado
                df_acumulado = df_filtered.sort_values('Data').copy()
                df_acumulado['Acumulado'] = df_acumulado['Total'].cumsum()
                
                line_chart = alt.Chart(df_acumulado).mark_line(
                    point=True,
                    strokeWidth=3,
                    color='red'
                ).encode(
                    x='Data:T',
                    y='Acumulado:Q',
                    tooltip=['Data', 'Acumulado']
                ).properties(
                    height=400,
                    title='Receita Total Acumulada'
                )
                
                st.altair_chart(line_chart, use_container_width=True)
            
            # Seção 5: Tabela de Dados
            st.subheader("📋 Dados Detalhados")
            st.dataframe(
                df_filtered.sort_values('Data', ascending=False).style.format({
                    'Dinheiro': lambda x: format_currency(x),
                    'Cartao': lambda x: format_currency(x),
                    'Pix': lambda x: format_currency(x),
                    'Total': lambda x: format_currency(x)
                }),
                use_container_width=True,
                height=400
            )
            
        else:
            st.warning("Nenhum registro encontrado no período selecionado")
    else:
        st.info("Nenhum dado cadastrado ainda. Adicione seu primeiro registro acima.")

with tab4:
    st.header("📊 Painel de Vendas (Google Sheets)")
    
    # Filtros na sidebar
    with st.sidebar:
        st.header("🔍 Filtros")

        with st.spinner("Carregando dados..."):
            df_raw, _ = read_google_sheet()
            df = process_data(df_raw.copy()) if not df_raw.empty else pd.DataFrame()

            if not df.empty and 'Data' in df.columns:
                # Filtro de Ano
                anos = sorted(df['Ano'].unique())
                selected_anos = st.multiselect(
                    "Selecione o(s) Ano(s):",
                    options=anos,
                    default=anos
                )

                # Filtro de Mês
                meses_disponiveis = sorted(df[df['Ano'].isin(selected_anos)]['Mês'].unique()) if selected_anos else []
                meses_nomes = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
                meses_opcoes = [f"{m} - {meses_nomes[m]}" for m in meses_disponiveis]
                selected_meses_str = st.multiselect(
                    "Selecione o(s) Mês(es):",
                    options=meses_opcoes,
                    default=meses_opcoes
                )
                selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]

    # Conteúdo principal da análise
    if not df_raw.empty:
        if 'Data' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Data']):
            # Aplicar filtros
            df_filtered = df[df['Ano'].isin(selected_anos)] if selected_anos else df
            df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)] if selected_meses else df_filtered

            st.subheader("Dados Filtrados")
            st.dataframe(df_filtered[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']]
                         if 'DataFormatada' in df_filtered.columns else df_filtered, 
                         use_container_width=True,
                         height=300)

            # Gráficos
            st.subheader("Distribuição por Método de Pagamento")
            payment_filtered = pd.DataFrame({
                'Método': ['Cartão', 'Dinheiro', 'PIX'],
                'Valor': [df_filtered['Cartão'].sum(), df_filtered['Dinheiro'].sum(), df_filtered['Pix'].sum()]
            })

            pie_chart = alt.Chart(payment_filtered).mark_arc(innerRadius=50).encode(
                theta=alt.Theta("Valor:Q", stack=True),
                color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
                tooltip=["Método", "Valor"]
            ).properties(
                width=700,
                height=500
            )
            text = pie_chart.mark_text(radius=120, size=16).encode(text="Valor:Q")
            st.altair_chart(pie_chart + text, use_container_width=True)

            st.subheader("Vendas Diárias por Método de Pagamento")
            date_column = 'DataFormatada' if 'DataFormatada' in df_filtered.columns else 'Data'
            daily_data = df_filtered.melt(id_vars=[date_column], 
                                        value_vars=['Cartão', 'Dinheiro', 'Pix'],
                                        var_name='Método', 
                                        value_name='Valor')

            bar_chart = alt.Chart(daily_data).mark_bar(size=30).encode(
                x=alt.X(f'{date_column}:N', title='Data', axis=alt.Axis(labelAngle=-45)),
                y=alt.Y('Valor:Q', title='Valor (R$)'),
                color=alt.Color('Método:N', legend=alt.Legend(title="Método")),
                tooltip=[date_column, 'Método', 'Valor']
            ).properties(
                width=700,
                height=500
            )
            st.altair_chart(bar_chart, use_container_width=True)

            st.subheader("Acúmulo de Capital ao Longo do Tempo")
            df_accumulated = df_filtered.sort_values('Data').copy()
            df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()

            line_chart = alt.Chart(df_accumulated).mark_line(point=True, strokeWidth=3).encode(
                x=alt.X('Data:T', title='Data'),
                y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
                tooltip=['DataFormatada', 'Total Acumulado']
            ).properties(
                width=700,
                height=500
            )
            st.altair_chart(line_chart, use_container_width=True)

        else:
            st.info("Não há dados de data para análise.")
    else:
        st.info("Não há dados para exibir.")

# Adicionar rodapé
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: small;'>
        © 2025 Clips Burger - Sistema de Gestão | Desenvolvido com ❤️ e Streamlit
    </div>
    """, 
    unsafe_allow_html=True
)
