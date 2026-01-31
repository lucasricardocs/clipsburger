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
        "JBC (Junior Bacon Cheese)": 10.00,
        "Double Cheese Burger": 15.00,
        "Cebola Adicional": 0.50
    },
    "bebidas": {
        "Refri Lata": 15.00
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
    if pd.isna(value) or value is None:
        return "R$ -"
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_global_centered_styles():
    return [
        {'selector': 'th', 'props': [('text-align', 'center'), ('vertical-align', 'middle'), ('background-color', '#000033'), ('color', '#ffffff'), ('padding', '8px'), ('border', '1px solid #444')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('vertical-align', 'middle'), ('padding', '8px'), ('color', '#e0e0e0'), ('background-color', '#1a1a4a')]},
        {'selector': 'table', 'props': [('width', '100%'), ('margin-left', 'auto'), ('margin-right', 'auto')]}
    ]

def init_data_file():
    if not os.path.exists(CONFIG["excel_file"]):
        pd.DataFrame(columns=['Data', 'Dinheiro', 'Cartao', 'Pix']).to_excel(
            CONFIG["excel_file"], index=False)

def load_data():
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
    try:
        df['Data'] = pd.to_datetime(df['Data'])
        df.to_excel(CONFIG["excel_file"], index=False)
        st.success("Dados salvos com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")

def round_to_50_or_00(value):
    return int(round(value))

def calculate_combination_value(combination, item_prices):
    return sum(item_prices.get(name, 0) * quantity for name, quantity in combination.items())

# --- FUNÇÕES PARA ALGORITMO GENÉTICO COM RESTRIÇÃO DE COMBO ---
def create_individual_combo(item_prices, max_combos=100):
    """
    Cria um indivíduo respeitando a regra do combo:
    - Número de JBC = Número de Refri Lata
    - Cebola pode variar livremente
    """
    num_combos = random.randint(1, max_combos)
    num_cebolas = random.randint(0, 50)
    
    individual = {
        "JBC (Junior Bacon Cheese)": num_combos,
        "Refri Lata": num_combos,
        "Cebola Adicional": num_cebolas
    }
    
    return individual

def evaluate_fitness_combo(individual, target_value):
    """Avalia fitness com penalização se JBC != Refri Lata"""
    preco_jbc = CARDAPIOS["sanduiches"]["JBC (Junior Bacon Cheese)"]
    preco_lata = CARDAPIOS["bebidas"]["Refri Lata"]
    preco_cebola = CARDAPIOS["sanduiches"]["Cebola Adicional"]
    
    qty_jbc = individual.get("JBC (Junior Bacon Cheese)", 0)
    qty_lata = individual.get("Refri Lata", 0)
    qty_cebola = individual.get("Cebola Adicional", 0)
    
    # Penalização severa se JBC != Lata
    if qty_jbc != qty_lata:
        return 1_000_000 + abs(qty_jbc - qty_lata) * 1000
    
    total = (preco_jbc * qty_jbc) + (preco_lata * qty_lata) + (preco_cebola * qty_cebola)
    
    if total > target_value:
        return 1_000_000 + (total - target_value)
    
    score = target_value - total
    return score

def crossover_combo(parent1, parent2):
    """Crossover mantendo a regra do combo"""
    # Combos vêm de um dos pais
    if random.random() < 0.5:
        num_combos = parent1.get("JBC (Junior Bacon Cheese)", 0)
    else:
        num_combos = parent2.get("JBC (Junior Bacon Cheese)", 0)
    
    # Cebolas podem ser média ou de um dos pais
    if random.random() < 0.5:
        num_cebolas = (parent1.get("Cebola Adicional", 0) + parent2.get("Cebola Adicional", 0)) // 2
    else:
        num_cebolas = parent1.get("Cebola Adicional", 0) if random.random() < 0.5 else parent2.get("Cebola Adicional", 0)
    
    return {
        "JBC (Junior Bacon Cheese)": num_combos,
        "Refri Lata": num_combos,
        "Cebola Adicional": num_cebolas
    }

def mutate_combo(individual, mutation_rate=0.3):
    """Mutação mantendo a regra do combo"""
    new_individual = individual.copy()
    
    # Mutar número de combos
    if random.random() < mutation_rate:
        change = random.choice([-5, -3, -1, 1, 3, 5])
        new_combos = max(0, new_individual["JBC (Junior Bacon Cheese)"] + change)
        new_individual["JBC (Junior Bacon Cheese)"] = new_combos
        new_individual["Refri Lata"] = new_combos  # Mantém igual!
    
    # Mutar cebolas
    if random.random() < mutation_rate:
        change = random.choice([-3, -2, -1, 1, 2, 3])
        new_cebolas = max(0, new_individual.get("Cebola Adicional", 0) + change)
        new_individual["Cebola Adicional"] = new_cebolas
    
    return new_individual

def genetic_algorithm_combo(target_value, population_size=50, generations=100, max_combos=100):
    """Algoritmo genético com restrição de combo"""
    if target_value <= 0:
        return {}
    
    population = [create_individual_combo(CARDAPIOS, max_combos) for _ in range(population_size)]
    best_individual = {}
    best_fitness = float('inf')
    
    for generation in range(generations):
        fitness_scores = [(individual, evaluate_fitness_combo(individual, target_value)) 
                         for individual in population]
        fitness_scores.sort(key=lambda x: x[1])
        
        if fitness_scores[0][1] < best_fitness:
            best_individual = fitness_scores[0][0].copy()
            best_fitness = fitness_scores[0][1]
        
        if best_fitness == 0:
            break
        
        # Elitismo
        elite_size = max(5, population_size // 10)
        next_generation = [ind[0].copy() for ind in fitness_scores[:elite_size]]
        
        # Criar nova geração
        while len(next_generation) < population_size:
            tournament_size = 3
            tournament = random.sample(fitness_scores, tournament_size)
            tournament.sort(key=lambda x: x[1])
            parent1 = tournament[0][0]
            parent2 = random.choice(fitness_scores[:10])[0]
            
            child = crossover_combo(parent1, parent2)
            child = mutate_combo(child)
            next_generation.append(child)
        
        population = next_generation
    
    # Limpar valores zero
    final_combination = {k: int(v) for k, v in best_individual.items() if v > 0}
    
    return final_combination

def buscar_combinacao_combo(target_value, max_time_seconds=5, population_size=100, generations=200):
    """Busca a melhor combinação respeitando a regra do combo"""
    start_time = time.time()
    best_global_individual = {}
    best_global_diff = float('inf')
    attempts = 0
    
    while (time.time() - start_time) < max_time_seconds:
        attempts += 1
        current_result = genetic_algorithm_combo(target_value, population_size, generations)
        current_fitness = evaluate_fitness_combo(current_result, target_value)
        
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
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, -1), (1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
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
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
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

# --- LÓGICA DE PROCESSAMENTO GENÉTICO (SEPARADA) ---
def gerar_dados_geneticos_combo(valor_alvo_total, pop_size, n_gens):
    """Gera dados usando o algoritmo genético com restrição de combo"""
    combinacao, ciclos = buscar_combinacao_combo(
        valor_alvo_total, 
        max_time_seconds=5, 
        population_size=pop_size, 
        generations=n_gens
    )
    
    # Separar sanduíches e bebidas
    sanduiches = {}
    bebidas = {}
    
    for item, qty in combinacao.items():
        if item in CARDAPIOS["sanduiches"]:
            sanduiches[item] = qty
        elif item in CARDAPIOS["bebidas"]:
            bebidas[item] = qty
    
    # Calcular valores
    val_sand = sum(CARDAPIOS["sanduiches"][k] * v for k, v in sanduiches.items())
    val_beb = sum(CARDAPIOS["bebidas"][k] * v for k, v in bebidas.items())
    val_total = val_sand + val_beb
    
    return {
        'sanduiches': sanduiches,
        'bebidas': bebidas,
        'val_sand': val_sand,
        'val_beb': val_beb,
        'val_total': val_total,
        'alvo': valor_alvo_total,
        'ciclos': ciclos
    }

def renderizar_resultados(dados):
    st.subheader(f"Valor Alvo: {format_currency(dados['alvo'])}")
    st.caption(f"🤖 O algoritmo realizou {dados['ciclos']} ciclos completos de evolução.")
    
    # Verificar se a regra do combo foi respeitada
    qty_jbc = dados['sanduiches'].get("JBC (Junior Bacon Cheese)", 0)
    qty_lata = dados['bebidas'].get("Refri Lata", 0)
    qty_cebola = dados['sanduiches'].get("Cebola Adicional", 0)
    
    if qty_jbc == qty_lata and qty_jbc > 0:
        st.success(f"✅ **Combo 1 identificado:** {qty_jbc} unidades (JBC + Refri Lata)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🍔 Produtos")
        if dados['sanduiches']:
            df_s = pd.DataFrame({
                'Produto': list(dados['sanduiches'].keys()),
                'Qnt': list(dados['sanduiches'].values()),
                'Preço Unitário': [CARDAPIOS["sanduiches"][k] for k in dados['sanduiches']],
                'Subtotal': [CARDAPIOS["sanduiches"][k]*v for k,v in dados['sanduiches'].items()]
            })
            df_s = df_s.sort_values('Subtotal', ascending=False)
            html_s = df_s.style.format({'Qnt':'{:.0f}', 'Preço Unitário':'R$ {:.2f}', 'Subtotal':'R$ {:.2f}'})\
                .set_table_styles(get_global_centered_styles()).hide(axis='index').to_html()
            st.markdown(html_s, unsafe_allow_html=True)
            st.write("")
            st.metric("Total Produtos", format_currency(dados['val_sand']))
        else:
            st.warning("Sem itens")

    with col2:
        st.markdown("### 🥤 Bebidas")
        if dados['bebidas']:
            df_b = pd.DataFrame({
                'Produto': list(dados['bebidas'].keys()),
                'Qnt': list(dados['bebidas'].values()),
                'Preço Unitário': [CARDAPIOS["bebidas"][k] for k in dados['bebidas']],
                'Subtotal': [CARDAPIOS["bebidas"][k]*v for k,v in dados['bebidas'].items()]
            })
            df_b = df_b.sort_values('Subtotal', ascending=False)
            html_b = df_b.style.format({'Qnt':'{:.0f}', 'Preço Unitário':'R$ {:.2f}', 'Subtotal':'R$ {:.2f}'})\
                .set_table_styles(get_global_centered_styles()).hide(axis='index').to_html()
            st.markdown(html_b, unsafe_allow_html=True)
            st.write("")
            st.metric("Total Bebidas", format_currency(dados['val_beb']))
        else:
            st.warning("Sem itens")

    diff = dados['alvo'] - dados['val_total']
    
    # FUNDOS TRANSPARENTES
    cor_border = "#10b981" if diff == 0 else "#f97316"
    cor_text = "#a7f3d0" if diff == 0 else "#fdba74" 
    
    st.markdown("---")
    
    # Informações do Combo - FUNDO TRANSPARENTE
    if qty_jbc > 0 and qty_lata > 0:
        valor_combos = qty_jbc * 25.00
        valor_cebolas = qty_cebola * 0.50
        
        st.markdown(f"""
        <div style="background-color: rgba(65, 105, 225, 0.1); border: 2px solid #4169E1; border-radius: 10px; padding: 15px; margin-bottom: 15px; backdrop-filter: blur(10px);">
            <h4 style="margin:0; color: #87CEEB; text-align: center;">🎁 COMBO 1</h4>
            <p style="text-align: center; color: #e5e7eb; margin: 5px 0;">
                {qty_jbc} Combo(s) x R$ 25,00 = <b>{format_currency(valor_combos)}</b>
            </p>
            <p style="text-align: center; color: #e5e7eb; margin: 5px 0; font-size: 14px;">
                (1 JBC + 1 Refri Lata por combo)
            </p>
            {f'<p style="text-align: center; color: #FFD700; margin: 5px 0; font-size: 14px;">+ {qty_cebola} Cebola(s) Adicional(is) x R$ 0,50 = <b>{format_currency(valor_cebolas)}</b></p>' if qty_cebola > 0 else ''}
        </div>
        """, unsafe_allow_html=True)
    
    # Box do valor total - FUNDO TRANSPARENTE
    st.markdown(f"""
    <div style="background-color: rgba(0, 0, 51, 0.3); border: 3px solid {cor_border}; border-radius: 15px; padding: 25px; text-align: center; margin-top: 10px; margin-bottom: 20px; backdrop-filter: blur(10px);">
        <h3 style="margin:0; color: {cor_text}; font-family: sans-serif;">💰 VALOR TOTAL DA COMBINAÇÃO</h3>
        <p style="font-size: 45px; font-weight: 800; margin: 10px 0; color: {cor_text};">
            {format_currency(dados['val_total'])}
        </p>
        <p style="font-size: 16px; margin: 0; color: #e5e7eb;">
            Meta: <b>{format_currency(dados['alvo'])}</b> | Diferença: <b style="color: {'#fca5a5' if diff != 0 else '#86efac'}">{format_currency(abs(diff))}</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title=CONFIG["page_title"],
    layout=CONFIG["layout"],
    initial_sidebar_state=CONFIG["sidebar_state"]
)

# --- CSS GLOBAL COM LOGO ---
st.markdown("""
<style>
    /* 1. FUNDO - Gradiente Azul Escuro */
    .stApp {
        background: linear-gradient(to bottom, #1e005e 0%, #000033 50%, #000000 100%);
        background-size: cover;
        background-attachment: fixed;
        color: #f0f2f6;
    }

    /* 2. Centralização de tabelas */
    th, td {
        text-align: center !important;
        vertical-align: middle !important;
        color: #e0e0e0 !important;
    }
    div[data-testid="stTable"] table {
        margin-left: auto;
        margin-right: auto;
    }
    
    /* 3. Inputs */
    .stTextInput input, .stNumberInput input, .stSelectbox, .stDateInput, div[data-baseweb="select"] > div {
        background-color: #1a1c24 !important; 
        color: white !important;
        border: 1px solid #444 !important;
    }
    .stSelectbox div[data-baseweb="select"] span {
        color: white !important;
    }

    /* 4. MENU ESTILIZADO */
    div[role="radiogroup"] {
        display: flex;
        flex-direction: row;
        justify-content: center;
        width: 100%;
        background-color: transparent;
        gap: 15px;
    }
    
    div[role="radiogroup"] label {
        background-color: transparent !important;
        border: none !important;
        padding: 5px 15px !important;
        margin: 0 !important;
        box-shadow: none !important;
        cursor: pointer;
        transition: all 0.3s ease;
        border-right: 2px solid #555 !important;
        border-radius: 0 !important;
    }

    div[role="radiogroup"] label:last-child {
        border-right: none !important;
    }

    div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }

    div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
        font-size: 16px !important; 
        white-space: nowrap !important;
        font-weight: 500;
        margin: 0;
        padding-bottom: 2px;
        color: #b0b0b0; 
        border-bottom: 2px solid transparent; 
    }

    div[role="radiogroup"] label:hover div[data-testid="stMarkdownContainer"] p {
        color: #ff4b4b !important;
        border-bottom: 2px solid #ff4b4b !important;
    }

    div[role="radiogroup"] label[data-checked="true"] div[data-testid="stMarkdownContainer"] p {
        color: #ff4b4b !important;
        border-bottom: 2px solid #ff4b4b !important;
        font-weight: bold;
    }

    /* 5. LOGO COM EFEITO */
    .logo-container {
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 1rem;
    }
    
    .logo-wrapper {
        position: relative;
        margin-right: 20px;
        width: 240px;
        height: 240px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .logo-background {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 175px;
        height: 175px;
        background-image: url('https://raw.githubusercontent.com/lucasricardocs/combo/main/logo.png');
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        filter: blur(20px) brightness(1.8) saturate(2.5);
        z-index: 1;
        animation: celestialPulse 12s ease-in-out infinite alternate;
    }
    
    .logo-main {
        position: relative;
        width: 200px;
        height: 200px;
        background-image: url('https://raw.githubusercontent.com/lucasricardocs/combo/main/logo.png');
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        z-index: 2;
    }
    
    @keyframes celestialPulse {
        0% { 
            filter: blur(20px) brightness(1.8) saturate(2.5);
            transform: translate(-50%, -50%) scale(1);
        }
        50% { 
            filter: blur(25px) brightness(2.2) saturate(3);
            transform: translate(-50%, -50%) scale(1.1);
        }
        100% { 
            filter: blur(20px) brightness(1.8) saturate(2.5);
            transform: translate(-50%, -50%) scale(1);
        }
    }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZAÇÃO SESSION STATE ---
init_data_file()
if 'df_receipts' not in st.session_state:
    st.session_state.df_receipts = load_data()
if 'uploaded_data' not in st.session_state:
    st.session_state.uploaded_data = None
if 'vendas_data' not in st.session_state:
    st.session_state.vendas_data = None
if 'resultado_arquivo' not in st.session_state:
    st.session_state.resultado_arquivo = None
if 'resultado_pix' not in st.session_state:
    st.session_state.resultado_pix = None

# --- INTERFACE PRINCIPAL ---

# Logo com efeito
st.markdown("""
<div class="logo-container">
    <div class="logo-wrapper">
        <div class="logo-background"></div>
        <div class="logo-main"></div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style='text-align: center; margin-bottom: 20px;'>
    <h2 style='color: #ff4b4b; margin: 0;'>🍔 Sistema de Gestão - Clips Burger</h2>
    <p style='color: #b0b0b0; margin-top: 5px;'>Análise inteligente de vendas e combinações</p>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configurações do Algoritmo")
    
    st.info("🧬 Algoritmo Genético com Restrição de Combo")
    
    population_size = st.slider(
        "Tamanho da População", 
        min_value=20, 
        max_value=200, 
        value=100, 
        step=10,
        help="Maior população = melhor resultado, mas mais lento"
    )
    
    generations = st.slider(
        "Número de Gerações", 
        min_value=10, 
        max_value=500, 
        value=200, 
        step=10,
        help="Mais gerações = melhor convergência"
    )
    
    st.divider()
    
    st.caption("⚠️ **Regra do Combo 1:**")
    st.caption("JBC = Refri Lata (sempre iguais)")
    st.caption("Cebola = ajuste fino (R$ 0,50)")

# --- MENU DE NAVEGAÇÃO ---
menu_opcoes = ["📈 Resumo das Vendas", "🧩 Análise com Arquivo", "💸 Calculadora PIX"]
escolha_menu = st.radio("Navegação", menu_opcoes, horizontal=True, label_visibility="collapsed", key="nav_menu")

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
                    pdf_display = f'<a href="application/pdf;base64,{b64_pdf}" download="relatorio_clips_burger.pdf">📥 Clique aqui para baixar o Relatório PDF</a>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                    st.success("Relatório gerado com sucesso!")
            
        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo: {str(e)}")
            st.exception(e)
    else:
        st.info("Aguardando upload do arquivo de transações.")

elif escolha_menu == "🧩 Análise com Arquivo":
    st.header("🧩 Análise de Combinações por Arquivo")
    
    if st.session_state.vendas_data is not None:
        vendas = st.session_state.vendas_data
        
        forma_selecionada = st.selectbox(
            "Selecione a forma de pagamento",
            options=vendas['Forma'].tolist(),
            format_func=lambda x: f"{x} ({format_currency(vendas.loc[vendas['Forma'] == x, 'Valor'].iloc[0])})"
        )
        
        valor_selecionado = vendas.loc[vendas['Forma'] == forma_selecionada, 'Valor'].iloc[0]
        
        if st.button("🔎 Analisar Combinação", type="primary", use_container_width=True):
            with st.spinner("Calculando a melhor combinação com Combo 1..."):
                dados = gerar_dados_geneticos_combo(
                    valor_selecionado, 
                    population_size, 
                    generations
                )
                st.session_state.resultado_arquivo = dados
        
        if st.session_state.resultado_arquivo:
            st.divider()
            renderizar_resultados(st.session_state.resultado_arquivo)
        
    else:
        st.info("Faça o upload de dados na aba 'Resumo das Vendas' primeiro.")

elif escolha_menu == "💸 Calculadora PIX":
    st.header("💸 Calculadora Rápida (PIX/Manual)")
    st.markdown("Digite um valor e descubra quantos Combos 1 + Cebolas formam esse total.")
    
    col_input, col_action = st.columns([0.4, 0.6])
    
    with col_input:
        valor_pix_input = st.number_input(
            "Digite o Valor (R$):", 
            min_value=0.0, 
            step=1.0, 
            format="%.2f",
            help="Insira o valor para análise"
        )
    
    with col_action:
        st.write("")
        st.write("")
        if st.button("🚀 Calcular Combinação", type="primary", use_container_width=True):
            if valor_pix_input > 0:
                with st.spinner("Calculando a melhor combinação..."):
                    dados = gerar_dados_geneticos_combo(
                        valor_pix_input, 
                        population_size, 
                        generations
                    )
                    st.session_state.resultado_pix = dados
            else:
                st.error("Por favor, insira um valor maior que zero.")

    if st.session_state.resultado_pix:
        st.divider()
        renderizar_resultados(st.session_state.resultado_pix)

# Rodapé
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: small;'>
        © 2025 Clips Burger - Sistema de Gestão de Combos | Desenvolvido com ❤️ e Streamlit
    </div>
    """, 
    unsafe_allow_html=True
)
