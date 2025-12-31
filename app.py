import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import random
import os
import numpy as np
import time
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

# --- CONSTANTES E CONFIGURAÇÕES ---
CONFIG = {
    "page_title": "Gestão - Clips Burger",
    "layout": "centered",
    "sidebar_state": "expanded",
    "excel_file": "recebimentos.xlsx",
    "logo_path": "logo.png"
}

CARDAPIOS = {
    "sanduiches": {
        "X Salada Simples": 18.00,
        "X Salada Especial": 20.00,
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

def get_global_centered_styles():
    """Retorna estilos CSS para centralizar tabelas Pandas/HTML."""
    return [
        {'selector': 'th', 'props': [('text-align', 'center'), ('vertical-align', 'middle'), ('background-color', '#262730'), ('color', 'white'), ('padding', '8px')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('vertical-align', 'middle'), ('padding', '8px')]},
        {'selector': 'table', 'props': [('width', '100%'), ('margin-left', 'auto'), ('margin-right', 'auto')]}
    ]

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
    """Força estritamente para INTEIRO."""
    return int(round(value))

def calculate_combination_value(combination, item_prices):
    """Calcula o valor total de uma combinação."""
    return sum(item_prices.get(name, 0) * quantity for name, quantity in combination.items())

# --- FUNÇÕES PARA ALGORITMO GENÉTICO ---
def create_individual(item_prices, combination_size):
    """Cria um indivíduo (combinação) aleatório com inteiros."""
    if not item_prices:
        return {}
    
    items = list(item_prices.keys())
    size = min(combination_size, len(items))
    selected_items = random.sample(items, size)
    
    return {
        name: int(random.randint(1, 100)) 
        for name in selected_items 
    }

def evaluate_fitness(individual, item_prices, target_value):
    """
    Avalia a adequação com REGRAS DE NEGÓCIO:
    1. Penalidade Extrema: Se passar do valor alvo.
    2. Penalidade Média: Se um único item representar > 50% do valor total.
    3. Score Base: Diferença para o alvo.
    """
    total = calculate_combination_value(individual, item_prices)
    
    # 1. Penalidade de Estouro (O mais grave)
    if total > target_value:
        return 1_000_000 + (total - target_value)
    
    score = target_value - total
    
    # 2. Penalidade de Diversidade (>50% do valor em um item)
    if total > 0:
        limite_concentracao = total * 0.50
        for item, qty in individual.items():
            valor_item = item_prices.get(item, 0) * qty
            if valor_item > limite_concentracao:
                score += 5000 + (valor_item - limite_concentracao)
                
    return score

def crossover(parent1, parent2):
    all_keys = set(list(parent1.keys()) + list(parent2.keys()))
    child = {}
    for key in all_keys:
        if key in parent1 and key in parent2:
            child[key] = parent1[key] if random.random() < 0.5 else parent2[key]
        elif key in parent1:
            if random.random() < 0.5: child[key] = parent1[key]
        elif key in parent2:
            if random.random() < 0.5: child[key] = parent2[key]
    return child

def mutate(individual, item_prices, mutation_rate=0.2, max_items=5):
    new_individual = individual.copy()
    
    # Adicionar item
    if (random.random() < mutation_rate and 
        len(new_individual) < max_items and 
        len(new_individual) < len(item_prices)):
        
        possible_new_items = [item for item in item_prices.keys() if item not in new_individual]
        if possible_new_items:
            new_item = random.choice(possible_new_items)
            new_individual[new_item] = 1
    
    # Remover item
    if random.random() < mutation_rate and len(new_individual) > 1:
        item_to_remove = random.choice(list(new_individual.keys()))
        del new_individual[item_to_remove]
    
    # Modificar quantidades
    for key in list(new_individual.keys()):
        if random.random() < mutation_rate:
            change = random.choice([-1, 1]) 
            new_value = max(1, int(new_individual[key] + change))
            new_individual[key] = new_value
    
    return new_individual

def genetic_algorithm(item_prices, target_value, population_size=50, generations=100, 
                    combination_size=5, elite_size=5, tournament_size=3):
    if not item_prices or target_value <= 0:
        return {}
    
    population = [create_individual(item_prices, combination_size) for _ in range(population_size)]
    best_individual = {}
    best_fitness = float('inf')
    
    for generation in range(generations):
        fitness_scores = [(individual, evaluate_fitness(individual, item_prices, target_value)) 
                         for individual in population]
        fitness_scores.sort(key=lambda x: x[1])
        
        if fitness_scores[0][1] < best_fitness:
            best_individual = fitness_scores[0][0].copy()
            best_fitness = fitness_scores[0][1]
        
        if best_fitness == 0:
            break
        
        next_generation = [ind[0].copy() for ind in fitness_scores[:elite_size]]
        while len(next_generation) < population_size:
            tournament = random.sample(fitness_scores, tournament_size)
            tournament.sort(key=lambda x: x[1])
            parent1 = tournament[0][0]
            parent2 = random.choice(fitness_scores[:10])[0]
            child = crossover(parent1, parent2)
            child = mutate(child, item_prices, max_items=combination_size)
            next_generation.append(child)
        population = next_generation
    
    # Poda de Segurança
    final_combination = {k: int(v) for k, v in best_individual.items() if v > 0}
    final_total = calculate_combination_value(final_combination, item_prices)

    while final_total > target_value and len(final_combination) > 0:
        item_to_reduce = random.choice(list(final_combination.keys()))
        if final_combination[item_to_reduce] <= 1:
            del final_combination[item_to_reduce]
        else:
            final_combination[item_to_reduce] -= 1
        final_total = calculate_combination_value(final_combination, item_prices)

    return final_combination

def buscar_combinacao_exata(item_prices, target_value, max_time_seconds=5, 
                            population_size=100, generations=200, combination_size=10):
    start_time = time.time()
    best_global_individual = {}
    best_global_diff = float('inf') 
    attempts = 0

    while (time.time() - start_time) < max_time_seconds:
        attempts += 1
        current_result = genetic_algorithm(
            item_prices, target_value, population_size, generations, combination_size
        )
        current_fitness = evaluate_fitness(current_result, item_prices, target_value)

        if current_fitness == 0:
            return current_result, attempts
        
        if current_fitness < best_global_diff:
            best_global_diff = current_fitness
            best_global_individual = current_result
            
    return best_global_individual, attempts

# --- FUNÇÕES PARA GERAR PDF ---
def create_watermark(canvas, logo_path, width=400, height=400, opacity=0.1):
    try:
        if os.path.exists(logo_path):
            canvas.saveState()
            canvas.setFillColorRGB(255, 255, 255, alpha=opacity)
            canvas.drawImage(logo_path, (A4[0] - width) / 2, (A4[1] - height) / 2, 
                             width=width, height=height, mask='auto', preserveAspectRatio=True)
            canvas.restoreState()
    except Exception as e:
        print(f"Erro ao adicionar marca d'água: {e}")

def fig_to_buffer(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    buf.seek(0)
    return buf

def create_pdf_report(df, vendas, total_vendas, imposto_simples, custo_funcionario, 
                    custo_contadora, total_custos, lucro_estimado, logo_path):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading1']
    subheading_style = styles['Heading2']
    normal_style = styles['Normal']
    elements = []
    
    try:
        if os.path.exists(logo_path):
            img = Image(logo_path, width=2*inch, height=1.5*inch)
            img.hAlign = 'CENTER'
            elements.append(img)
            elements.append(Spacer(1, 0.5*inch))
    except Exception as e:
        print(f"Erro ao adicionar logo: {e}")
    
    elements.append(Paragraph("Relatório Financeiro - Clips Burger", title_style))
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(f"Data do relatório: {datetime.now().strftime('%d/%m/%Y')}", normal_style))
    elements.append(Spacer(1, 0.25*inch))
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
    # ESTILO DO PDF CENTRALIZADO
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, -1), (1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        # Centraliza tudo (antes estava RIGHT para valores)
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))
    
    elements.append(Paragraph("Análise de Vendas", heading_style))
    elements.append(Spacer(1, 0.1*inch))
    
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
    
    try:
        custos_df = pd.DataFrame({
            'Item': ['Impostos', 'Funcionário', 'Contadora'],
            'Valor': [imposto_simples, custo_funcionario, custo_contadora]
        })
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.pie(custos_df['Valor'], labels=custos_df['Item'], autopct='%1.1f%%', startangle=90, shadow=True)
        ax.set_title('Composição dos Custos')
        plt.tight_layout()
        img_buf = fig_to_buffer(fig)
        img = Image(img_buf, width=doc.width, height=4*inch)
        elements.append(img)
        plt.close(fig)
    except Exception as e:
        elements.append(Paragraph(f"Erro ao gerar gráfico de custos: {e}", normal_style))
    
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("Detalhamento por Forma de Pagamento", subheading_style))
    elements.append(Spacer(1, 0.1*inch))
    
    data = [["Forma de Pagamento", "Valor"]]
    for _, row in vendas.iterrows():
        data.append([row['Forma'], format_currency(row['Valor'])])
    
    table = Table(data, colWidths=[doc.width/2, doc.width/4])
    # ESTILO DO PDF CENTRALIZADO
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        # Centraliza tudo (antes estava RIGHT para valores)
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, inch))
    footer_text = "Este relatório foi gerado automaticamente pelo Sistema de Gestão da Clips Burger."
    elements.append(Paragraph(footer_text, normal_style))
    
    def add_watermark(canvas, doc):
        create_watermark(canvas, logo_path, width=300, height=300, opacity=0.1)
    
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

# --- FUNÇÃO CENTRAL DE ANÁLISE GENÉTICA E EXIBIÇÃO ---
def processar_analise_genetica(valor_alvo_total, drink_pct, pop_size, n_gens, tam_sand, tam_beb):
    """
    Função reutilizável para rodar a análise e exibir os resultados.
    """
    st.subheader(f"Valor Alvo: {format_currency(valor_alvo_total)}")
    target_sanduiches_inicial = valor_alvo_total * (1 - drink_pct/100)
    
    combinacao_sanduiches = {}
    combinacao_bebidas = {}
    
    # 1. PROCESSAMENTO (Apenas Genético)
    with st.spinner("🤖 O Algoritmo Genético está trabalhando..."):
        progress_text = "Calculando Sanduíches..."
        my_bar = st.progress(0, text=progress_text)

        # A. Sanduíches
        combinacao_sanduiches, t_sand = buscar_combinacao_exata(
            CARDAPIOS["sanduiches"], target_sanduiches_inicial, max_time_seconds=5, 
            population_size=pop_size, generations=n_gens, combination_size=tam_sand
        )
        
        valor_real_sanduiches = calculate_combination_value(combinacao_sanduiches, CARDAPIOS["sanduiches"])
        
        # B. Compensação
        target_bebidas_corrigido = valor_alvo_total - valor_real_sanduiches
        my_bar.progress(50, text=f"Sanduíches: {format_currency(valor_real_sanduiches)}. Calculando Bebidas (Compensação)...")
        
        # C. Bebidas
        combinacao_bebidas, t_beb = buscar_combinacao_exata(
            CARDAPIOS["bebidas"], target_bebidas_corrigido, max_time_seconds=5, 
            population_size=pop_size, generations=n_gens, combination_size=tam_beb
        )
        
        my_bar.progress(100, text="Pronto!")
        time.sleep(0.3)
        my_bar.empty()
        
        st.caption(f"🤖 O algoritmo realizou {t_sand + t_beb} ciclos completos de evolução.")

    # 2. CÁLCULOS FINAIS
    valor_real_sanduiches = calculate_combination_value(combinacao_sanduiches, CARDAPIOS["sanduiches"])
    valor_real_bebidas = calculate_combination_value(combinacao_bebidas, CARDAPIOS["bebidas"])
    valor_real_total = valor_real_sanduiches + valor_real_bebidas
    
    # 3. EXIBIÇÃO COM TABELAS CENTRALIZADAS
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🍔 Sanduíches")
        if combinacao_sanduiches:
            df_s = pd.DataFrame({'Qnt': list(combinacao_sanduiches.values()), 'Produto': list(combinacao_sanduiches.keys()),
                                 'Preço Unitário': [CARDAPIOS["sanduiches"][k] for k in combinacao_sanduiches],
                                 'Subtotal': [CARDAPIOS["sanduiches"][k]*v for k,v in combinacao_sanduiches.items()]})
            df_s = df_s.sort_values('Subtotal', ascending=False)
            html_s = df_s.style.format({'Qnt':'{:.0f}', 'Preço Unitário':'R$ {:.2f}', 'Subtotal':'R$ {:.2f}'})\
                .set_table_styles(get_global_centered_styles()).hide(axis='index').to_html()
            st.markdown(html_s, unsafe_allow_html=True)
            st.write("")
            st.metric("Total Sanduíches", format_currency(valor_real_sanduiches))
        else: st.warning("Sem itens")

    with col2:
        st.markdown("### 🍹 Bebidas")
        if combinacao_bebidas:
            df_b = pd.DataFrame({'Qnt': list(combinacao_bebidas.values()), 'Produto': list(combinacao_bebidas.keys()),
                                 'Preço Unitário': [CARDAPIOS["bebidas"][k] for k in combinacao_bebidas],
                                 'Subtotal': [CARDAPIOS["bebidas"][k]*v for k,v in combinacao_bebidas.items()]})
            df_b = df_b.sort_values('Subtotal', ascending=False)
            html_b = df_b.style.format({'Qnt':'{:.0f}', 'Preço Unitário':'R$ {:.2f}', 'Subtotal':'R$ {:.2f}'})\
                .set_table_styles(get_global_centered_styles()).hide(axis='index').to_html()
            st.markdown(html_b, unsafe_allow_html=True)
            st.write("")
            st.metric("Total Bebidas", format_currency(valor_real_bebidas))
        else: st.warning("Sem itens")

    # 4. DESTAQUE TOTAL
    diff = valor_alvo_total - valor_real_total
    cor_box = "#ecfdf5" if diff == 0 else "#fff7ed" 
    cor_border = "#10b981" if diff == 0 else "#f97316"
    cor_text = "#047857" if diff == 0 else "#c2410c"
    
    st.markdown("---")
    st.markdown(f"""
    <div style="background-color: {cor_box}; border: 2px solid {cor_border}; border-radius: 10px; padding: 20px; text-align: center; margin-top: 10px; margin-bottom: 20px;">
        <h3 style="margin:0; color: {cor_text}; font-family: sans-serif;">💰 VALOR TOTAL DA COMBINAÇÃO</h3>
        <p style="font-size: 45px; font-weight: 800; margin: 10px 0; color: {cor_text};">
            {format_currency(valor_real_total)}
        </p>
        <p style="font-size: 16px; margin: 0; color: #555;">
            Meta: <b>{format_currency(valor_alvo_total)}</b> | Diferença: <b style="color: {'red' if diff != 0 else 'green'}">{format_currency(diff)}</b>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.warning("""
    **Atenção:** Esta é apenas uma combinação hipotética que corresponde aproximadamente 
    ao valor vendido. O número real de produtos pode variar.
    """)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title=CONFIG["page_title"],
    layout=CONFIG["layout"],
    initial_sidebar_state=CONFIG["sidebar_state"]
)

# CSS GLOBAL: FUNDO CINZA, CENTRALIZAÇÃO DE TABELAS E OUTROS AJUSTES
st.markdown("""
<style>
    /* Fundo da página em cinza clarinho */
    .stApp {
        background-color: #f4f4f4;
    }

    /* Centralização de tabelas e textos */
    th, td {
        text-align: center !important;
        vertical-align: middle !important;
    }
    div[data-testid="stTable"] table {
        margin-left: auto;
        margin-right: auto;
    }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZAÇÃO ---
init_data_file()
if 'df_receipts' not in st.session_state:
    st.session_state.df_receipts = load_data()
if 'uploaded_data' not in st.session_state:
    st.session_state.uploaded_data = None
if 'vendas_data' not in st.session_state:
    st.session_state.vendas_data = None

# --- INTERFACE PRINCIPAL ---

# Função para converter imagem em Base64 (Necessário para HTML)
def get_img_as_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# --- CSS E HTML PARA LOGO, FLUTUAÇÃO E FAÍSCAS ---
st.markdown("""
<style>
    /* Container principal */
    .logo-container {
        position: relative;
        width: 300px;
        height: 300px;
        margin: 0 auto 20px auto;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    /* A imagem da logo */
    .logo-animada {
        width: 300px;
        height: auto;
        animation: float 3s ease-in-out infinite;
        position: relative;
        z-index: 5; /* Logo fica atrás das faíscas agora */
    }

    /* Animação de flutuação */
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-15px); }
        100% { transform: translateY(0px); }
    }

    /* --- Efeito de Faíscas --- */
    .sparkle {
        position: absolute;
        width: 12px;
        height: 12px;
        background-color: #FFD700;
        border-radius: 50%;
        top: 50%;
        left: 50%; /* Nascem no centro */
        z-index: 10; /* AGORA ESTÃO NA FRENTE DA LOGO */
        opacity: 0;
        box-shadow: 0 0 10px #FFD700, 0 0 20px orange;
        pointer-events: none;
    }

    /* Movimentos mais amplos */
    @keyframes sparkle-move-1 {
        0% { transform: translate(-50%, -50%) scale(0); opacity: 0; }
        50% { opacity: 1; }
        100% { transform: translate(-180px, -180px) scale(1); opacity: 0; }
    }
    @keyframes sparkle-move-2 {
        0% { transform: translate(-50%, -50%) scale(0); opacity: 0; }
        50% { opacity: 1; }
        100% { transform: translate(180px, -150px) scale(1); opacity: 0; }
    }
    @keyframes sparkle-move-3 {
        0% { transform: translate(-50%, -50%) scale(0); opacity: 0; }
        50% { opacity: 1; }
        100% { transform: translate(-150px, 180px) scale(1); opacity: 0; }
    }
    @keyframes sparkle-move-4 {
        0% { transform: translate(-50%, -50%) scale(0); opacity: 0; }
        50% { opacity: 1; }
        100% { transform: translate(160px, 160px) scale(1); opacity: 0; }
    }

    .s1 { animation: sparkle-move-1 2s ease-out infinite; }
    .s2 { animation: sparkle-move-2 2s ease-out 0.5s infinite; }
    .s3 { animation: sparkle-move-3 2s ease-out 1.0s infinite; }
    .s4 { animation: sparkle-move-4 2s ease-out 1.5s infinite; }
</style>
""", unsafe_allow_html=True)

try:
    if os.path.exists(CONFIG["logo_path"]):
        img_base64 = get_img_as_base64(CONFIG["logo_path"])
        st.markdown(
            f"""
            <div class="logo-container">
                <div class="sparkle s1"></div>
                <div class="sparkle s2"></div>
                <div class="sparkle s3"></div>
                <div class="sparkle s4"></div>
                <img src="data:image/png;base64,{img_base64}" class="logo-animada">
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.warning("Logo não encontrada. Verifique o arquivo logo.png.")
except Exception as e:
    st.error(f"Erro na logo: {e}")

st.markdown("""
Bem-vindo(a)! Esta ferramenta ajuda a visualizar suas vendas por forma de pagamento
e tenta encontrar combinações *hipotéticas* de produtos que poderiam corresponder a esses totais.
""")
st.divider()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configurações")
    
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
    
    st.divider()
    st.info("🧬 Algoritmo Genético Ativo")
    
    population_size = st.slider(
        "Tamanho da População", 20, 200, 50, 10
    )
    generations = st.slider(
        "Número de Gerações", 10, 500, 100, 10
    )
    
    st.info("Lembre-se: As combinações são aproximações heurísticas.")

# --- MENU DE NAVEGAÇÃO (SUBSTITUINDO ST.TABS PARA MANTER O ESTADO) ---
# Usamos st.radio horizontal para garantir que a aba não mude ao clicar em botões

menu_opcoes = ["📈 Resumo das Vendas", "🧩 Detalhes das Combinações", "💰 Cadastro de Recebimentos", "💸 Calculadora PIX"]
escolha_menu = st.radio("Navegação", menu_opcoes, horizontal=True, label_visibility="collapsed")
st.divider()

# --- CONTEÚDO DAS ABAS ---

if escolha_menu == "📈 Resumo das Vendas":
    st.header("📤 Upload de Dados")
    arquivo = st.file_uploader("Envie o arquivo de transações (.csv ou .xlsx)", 
                             type=["csv", "xlsx"])
    
    if arquivo:
        try:
            with st.spinner("Processando arquivo..."):
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
                
                required_cols = ['Tipo', 'Bandeira', 'Valor']
                if not all(col in df.columns for col in required_cols):
                    st.error(f"Erro: O arquivo precisa conter as colunas: {', '.join(required_cols)}")
                    st.stop()

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
                
                st.session_state.uploaded_data = df
                st.session_state.vendas_data = vendas
                st.session_state.total_vendas = total_vendas
            
            st.header("📊 Visualização de Dados")
            
            st.subheader("Total de Vendas por Forma de Pagamento")
            bar_chart = create_altair_chart(
                vendas, 'bar', 'Forma', 'Valor', 'Forma',
                title=''
            ).properties(
                width=800,
                height=500
            )
            st.altair_chart(bar_chart, use_container_width=True)
            
            st.header("⚙️ Parâmetros Financeiros")
            col1, col2 = st.columns(2)
            with col1:
                salario_minimo = st.number_input("Salário Mínimo (R$)", value=1518.0, step=50.0)
            with col2:
                custo_contadora = st.number_input("Custo com Contadora (R$)", value=316.0, step=10.0)
            
            st.header("💰 Resultados Financeiros")
            
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
            
            total_custos = imposto_simples + custo_funcionario + custo_contadora
            lucro_estimado = total_vendas - total_custos
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de Custos", format_currency(total_custos))
            with col2:
                st.metric("Lucro Estimado", format_currency(lucro_estimado))
            
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
                **1. Imposto Simples Nacional** `Faturamento Bruto × 6%`  
                **2. Custo Funcionário CLT** `Salário + FGTS (8%) + Férias (1 mês + 1/3) + 13º Salário`  
                **3. Total de Custos** `Imposto + Funcionário + Contadora`  
                **4. Lucro Estimado** `Faturamento Bruto - Total de Custos`
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
            
            st.header("📑 Relatório")
            if st.button("Gerar Relatório PDF"):
                with st.spinner("Gerando relatório..."):
                    pdf_buffer = create_pdf_report(
                        df, vendas, total_vendas, imposto_simples, custo_funcionario, 
                        custo_contadora, total_custos, lucro_estimado, CONFIG["logo_path"]
                    )
                    b64_pdf = base64.b64encode(pdf_buffer.getvalue()).decode()
                    pdf_display = f'<a href="data:application/pdf;base64,{b64_pdf}" download="relatorio_clips_burger.pdf">📥 Clique aqui para baixar o Relatório PDF</a>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                    st.success("Relatório gerado com sucesso!")
            
        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo: {str(e)}")
            st.exception(e)
    else:
        st.info("Aguardando upload do arquivo de transações.")

elif escolha_menu == "🧩 Detalhes das Combinações":
    st.header("🧩 Análise de Combinações")
    
    if st.session_state.vendas_data is not None:
        vendas = st.session_state.vendas_data
        total_vendas = st.session_state.total_vendas
        
        forma_selecionada = st.selectbox(
            "Selecione a forma de pagamento",
            options=vendas['Forma'].tolist(),
            format_func=lambda x: f"{x} ({format_currency(vendas.loc[vendas['Forma'] == x, 'Valor'].iloc[0])})"
        )
        
        valor_selecionado = vendas.loc[vendas['Forma'] == forma_selecionada, 'Valor'].iloc[0]
        
        if st.button("🔎 Analisar Combinação (Arquivo)", use_container_width=True):
            processar_analise_genetica(
                valor_selecionado, 
                drink_percentage, 
                population_size, 
                generations, 
                tamanho_combinacao_sanduiches, 
                tamanho_combinacao_bebidas
            )
        
    else:
        st.info("Faça o upload de dados na aba 'Resumo das Vendas' para visualizar possíveis combinações.")

elif escolha_menu == "💰 Cadastro de Recebimentos":
    st.header("💰 Cadastro e Análise de Recebimentos")
    
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
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {str(e)}")

    if not st.session_state.df_receipts.empty:
        st.subheader("📅 Filtros de Período")
        filtro_tipo = st.radio("Tipo de Filtro:", ["Intervalo de Datas", "Mês Específico"], horizontal=True)
        
        if filtro_tipo == "Intervalo de Datas":
            cols = st.columns(2)
            with cols[0]:
                inicio = st.date_input("Data inicial", value=st.session_state.df_receipts['Data'].min())
            with cols[1]:
                fim = st.date_input("Data final", value=st.session_state.df_receipts['Data'].max())
        else:
            meses_disponiveis = sorted(st.session_state.df_receipts['Data'].dt.to_period('M').unique(), reverse=True)
            mes_selecionado = st.selectbox("Selecione o mês:", options=meses_disponiveis, format_func=lambda x: x.strftime('%B/%Y'))
            inicio = pd.to_datetime(mes_selecionado.start_time)
            fim = pd.to_datetime(mes_selecionado.end_time)
        
        df_filtered = st.session_state.df_receipts[
            (st.session_state.df_receipts['Data'] >= pd.to_datetime(inicio)) & 
            (st.session_state.df_receipts['Data'] <= pd.to_datetime(fim))
        ].copy()
        
        if not df_filtered.empty:
            df_filtered['Total'] = df_filtered['Dinheiro'] + df_filtered['Cartao'] + df_filtered['Pix']
            totais = {
                'Dinheiro': df_filtered['Dinheiro'].sum(),
                'Cartão': df_filtered['Cartao'].sum(),
                'PIX': df_filtered['Pix'].sum()
            }
            total_periodo = sum(totais.values())
            
            st.subheader("📊 Resumo do Período")
            st.markdown("""
            <style>
                div[data-testid="stMetric"] {padding: 5px 10px;}
                div[data-testid="stMetric"] > div {gap: 2px;}
                div[data-testid="stMetric"] label {font-size: 14px !important; font-weight: 500 !important; color: #6b7280 !important;}
                div[data-testid="stMetric"] > div > div {font-size: 18px !important; font-weight: 600 !important;}
            </style>
            """, unsafe_allow_html=True)
            
            cols1 = st.columns(4)
            cols2 = st.columns(4)
            with cols1[0]: st.metric("Dinheiro", format_currency(totais['Dinheiro']))
            with cols1[1]: st.metric("Cartão", format_currency(totais['Cartão']))
            with cols1[2]: st.metric("PIX", format_currency(totais['PIX']))
            with cols1[3]: st.metric("Total Geral", format_currency(total_periodo))
            with cols2[0]: st.metric("Média Diária", format_currency(df_filtered['Total'].mean()))
            with cols2[1]: st.metric("Maior Venda", format_currency(df_filtered['Total'].max()))
            with cols2[2]: st.metric("Dias Registrados", len(df_filtered))
            with cols2[3]: st.metric("Dias sem Registro", (fim - inicio).days + 1 - len(df_filtered))
            
            st.subheader("📈 Visualizações Gráficas")
            tab_graficos1, tab_graficos2, tab_graficos3 = st.tabs(["Distribuição", "Comparação", "Acumulado"])
            
            with tab_graficos1:
                df_pie = pd.DataFrame({'Forma': list(totais.keys()), 'Valor': list(totais.values())})
                pie_chart = alt.Chart(df_pie).mark_arc().encode(
                    theta='Valor', color=alt.Color('Forma', legend=alt.Legend(title="Forma de Pagamento")), tooltip=['Forma', 'Valor']
                ).properties(height=400, title='Distribuição dos Recebimentos')
                st.altair_chart(pie_chart, use_container_width=True)
            
            with tab_graficos2:
                df_bar = df_filtered.melt(id_vars=['Data'], value_vars=['Dinheiro', 'Cartao', 'Pix'], var_name='Forma', value_name='Valor')
                bar_chart = alt.Chart(df_bar).mark_bar().encode(
                    x='monthdate(Data):O', y='sum(Valor):Q', color='Forma', tooltip=['Forma', 'sum(Valor)']
                ).properties(height=400, title='Vendas por Forma de Pagamento')
                st.altair_chart(bar_chart, use_container_width=True)
            
            with tab_graficos3:
                df_acumulado = df_filtered.sort_values('Data').copy()
                df_acumulado['Acumulado'] = df_acumulado['Total'].cumsum()
                line_chart = alt.Chart(df_acumulado).mark_line(point=True, strokeWidth=3, color='red').encode(
                    x='Data:T', y='Acumulado:Q', tooltip=['Data', 'Acumulado']
                ).properties(height=400, title='Receita Total Acumulada')
                st.altair_chart(line_chart, use_container_width=True)
            
            st.subheader("📋 Dados Detalhados")
            
            # USO DA FUNÇÃO GLOBAL CENTRALIZADA
            html_tabela_dados = df_filtered.sort_values('Data', ascending=False).style.format({
                'Dinheiro': lambda x: format_currency(x),
                'Cartao': lambda x: format_currency(x),
                'Pix': lambda x: format_currency(x),
                'Total': lambda x: format_currency(x),
                'Data': lambda x: x.strftime('%d/%m/%Y')
            }).set_table_styles(get_global_centered_styles()).hide(axis='index').to_html()
            st.markdown(html_tabela_dados, unsafe_allow_html=True)
            
        else:
            st.warning("Nenhum registro encontrado no período selecionado")
    else:
        st.info("Nenhum dado cadastrado ainda. Adicione seu primeiro registro acima.")

elif escolha_menu == "💸 Calculadora PIX":
    st.header("💸 Calculadora Rápida (PIX/Manual)")
    st.markdown("Use esta aba para analisar um valor específico de PIX recebido, sem precisar subir planilha.")
    
    col_input, col_action = st.columns([0.4, 0.6])
    
    with col_input:
        valor_pix_input = st.number_input(
            "Digite o Valor do PIX recebido (R$):", 
            min_value=0.0, 
            step=1.0, 
            format="%.2f",
            help="Insira o valor exato que caiu na conta."
        )
    
    with col_action:
        st.write("") # Espaço para alinhar
        st.write("")
        analisar_btn = st.button("🚀 Calcular Combinação PIX", type="primary", use_container_width=True)
    
    st.divider()
    
    if analisar_btn and valor_pix_input > 0:
        processar_analise_genetica(
            valor_pix_input, 
            drink_percentage, 
            population_size, 
            generations, 
            tamanho_combinacao_sanduiches, 
            tamanho_combinacao_bebidas
        )
    elif analisar_btn and valor_pix_input <= 0:
        st.error("Por favor, insira um valor maior que zero.")
    else:
        st.info("Insira um valor e clique no botão para ver a mágica acontecer! ✨")

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
