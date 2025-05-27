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
import warnings

# Configuração da página com tema escuro
st.set_page_config(
    page_title="Clips Burger Analytics", 
    layout="wide", 
    page_icon="🍔",
    initial_sidebar_state="expanded"
)

# CSS customizado para design premium
def inject_premium_css():
    st.markdown("""
    <style>
    /* Tema escuro personalizado */
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    /* Header principal */
    .main-header {
        background: linear-gradient(135deg, #ff6b35, #f7931e, #ff6b35);
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px rgba(255, 107, 53, 0.3);
        text-align: center;
        color: white;
    }
    
    /* Cards de métricas premium */
    .metric-card {
        background: linear-gradient(135deg, #1e3c72, #2a5298);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        margin: 1rem 0;
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
    }
    
    /* Sidebar premium */
    .css-1d391kg {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    
    /* Botões customizados */
    .stButton > button {
        background: linear-gradient(135deg, #ff6b35, #f7931e);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.75rem 2rem;
        font-weight: bold;
        box-shadow: 0 10px 20px rgba(255, 107, 53, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 15px 30px rgba(255, 107, 53, 0.4);
    }
    
    /* Gráficos com bordas elegantes */
    .stPlotlyChart {
        border-radius: 15px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
        margin: 1rem 0;
    }
    
    /* Animações suaves */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .animate-fade-in {
        animation: fadeInUp 0.6s ease-out;
    }
    </style>
    """, unsafe_allow_html=True)

inject_premium_css()

# Suas funções existentes aqui (get_google_auth, read_sales_data, etc.)
# ... (mantenha todas as funções que você já tem)

def create_premium_kpi_cards(df):
    """Cria cards KPI premium com animações"""
    if df.empty:
        return
    
    total_vendas = df['Total'].sum()
    media_diaria = df['Total'].mean()
    melhor_dia = df.loc[df['Total'].idxmax(), 'DataFormatada'] if not df.empty else "N/A"
    crescimento = ((df['Total'].tail(7).mean() - df['Total'].head(7).mean()) / df['Total'].head(7).mean() * 100) if len(df) >= 14 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card animate-fade-in">
            <h3 style="color: #64ffda; margin: 0;">💰 Faturamento Total</h3>
            <h1 style="color: white; margin: 0.5rem 0; font-size: 2.5rem;">{format_brl(total_vendas)}</h1>
            <p style="color: #b0bec5; margin: 0;">Receita acumulada</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card animate-fade-in">
            <h3 style="color: #ff9800; margin: 0;">📊 Média Diária</h3>
            <h1 style="color: white; margin: 0.5rem 0; font-size: 2.5rem;">{format_brl(media_diaria)}</h1>
            <p style="color: #b0bec5; margin: 0;">Por dia trabalhado</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card animate-fade-in">
            <h3 style="color: #4caf50; margin: 0;">🏆 Melhor Dia</h3>
            <h1 style="color: white; margin: 0.5rem 0; font-size: 2rem;">{melhor_dia}</h1>
            <p style="color: #b0bec5; margin: 0;">Maior faturamento</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        cor_crescimento = "#4caf50" if crescimento >= 0 else "#f44336"
        icone_crescimento = "📈" if crescimento >= 0 else "📉"
        st.markdown(f"""
        <div class="metric-card animate-fade-in">
            <h3 style="color: {cor_crescimento}; margin: 0;">{icone_crescimento} Tendência</h3>
            <h1 style="color: white; margin: 0.5rem 0; font-size: 2.5rem;">{crescimento:+.1f}%</h1>
            <p style="color: #b0bec5; margin: 0;">Últimos 7 dias</p>
        </div>
        """, unsafe_allow_html=True)

def create_premium_sales_chart(df):
    """Cria gráfico de vendas premium com Plotly"""
    if df.empty:
        return None
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Vendas Diárias', 'Métodos de Pagamento', 'Tendência Semanal', 'Performance por Dia'),
        specs=[[{"secondary_y": True}, {"type": "pie"}],
               [{"colspan": 2}, None]],
        vertical_spacing=0.1
    )
    
    # Gráfico 1: Vendas diárias com linha de tendência
    fig.add_trace(
        go.Scatter(
            x=df['Data'], 
            y=df['Total'],
            mode='lines+markers',
            name='Vendas Diárias',
            line=dict(color='#ff6b35', width=3),
            marker=dict(size=8, color='#ff6b35'),
            hovertemplate='<b>%{x}</b><br>Vendas: R$ %{y:,.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Linha de tendência
    z = np.polyfit(range(len(df)), df['Total'], 1)
    p = np.poly1d(z)
    fig.add_trace(
        go.Scatter(
            x=df['Data'],
            y=p(range(len(df))),
            mode='lines',
            name='Tendência',
            line=dict(color='#64ffda', width=2, dash='dash'),
            hovertemplate='Tendência: R$ %{y:,.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Gráfico 2: Pizza dos métodos de pagamento
    metodos = ['Cartão', 'Dinheiro', 'PIX']
    valores = [df[metodo].sum() for metodo in metodos]
    cores = ['#ff6b35', '#64ffda', '#4caf50']
    
    fig.add_trace(
        go.Pie(
            labels=metodos,
            values=valores,
            hole=0.4,
            marker=dict(colors=cores, line=dict(color='#000000', width=2)),
            textinfo='label+percent',
            textfont=dict(size=12, color='white'),
            hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>Percentual: %{percent}<extra></extra>'
        ),
        row=1, col=2
    )
    
    # Gráfico 3: Performance por dia da semana
    if 'DiaSemana' in df.columns:
        vendas_por_dia = df.groupby('DiaSemana')['Total'].mean().reindex(dias_semana_ordem).fillna(0)
        
        fig.add_trace(
            go.Bar(
                x=vendas_por_dia.index,
                y=vendas_por_dia.values,
                name='Média por Dia',
                marker=dict(
                    color=vendas_por_dia.values,
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Vendas (R$)")
                ),
                hovertemplate='<b>%{x}</b><br>Média: R$ %{y:,.2f}<extra></extra>'
            ),
            row=2, col=1
        )
    
    # Configurações do layout
    fig.update_layout(
        title=dict(
            text="📊 Dashboard Analítico - Clips Burger",
            font=dict(size=24, color='white'),
            x=0.5
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        height=800,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Atualizar eixos
    fig.update_xaxes(gridcolor='rgba(255,255,255,0.1)', gridwidth=1)
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)', gridwidth=1)
    
    return fig

def create_financial_sunburst(resultados):
    """Cria gráfico sunburst para análise financeira"""
    
    # Dados hierárquicos para o sunburst
    labels = [
        "Receita Total",
        "Receita Tributável", "Receita Não Tributável",
        "Cartão + PIX", "Dinheiro",
        "Impostos", "Receita Líquida Trib.",
        "Custos", "Despesas", "Lucro"
    ]
    
    parents = [
        "",
        "Receita Total", "Receita Total",
        "Receita Tributável", "Receita Não Tributável",
        "Cartão + PIX", "Cartão + PIX",
        "Receita Líquida Trib.", "Receita Líquida Trib.", "Receita Líquida Trib."
    ]
    
    values = [
        resultados['receita_bruta'],
        resultados['receita_tributavel'], resultados['receita_nao_tributavel'],
        resultados['receita_tributavel'], resultados['receita_nao_tributavel'],
        resultados['impostos_sobre_vendas'], resultados['receita_liquida'],
        resultados['custo_produtos_vendidos'], resultados['total_despesas_operacionais'], resultados['lucro_liquido']
    ]
    
    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>Percentual: %{percentParent}<extra></extra>',
        maxdepth=3,
        insidetextorientation='radial'
    ))
    
    fig.update_layout(
        title="🌟 Análise Financeira Hierárquica",
        font=dict(size=12, color='white'),
        paper_bgcolor='rgba(0,0,0,0)',
        height=600
    )
    
    return fig

# Função principal do dashboard
def main():
    # Header principal
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 3rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">🍔 CLIPS BURGER ANALYTICS</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">Dashboard Executivo de Inteligência de Negócios</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Carregar dados (use suas funções existentes)
    df_raw = read_sales_data()
    df_processed = process_data(df_raw)
    
    if not df_processed.empty:
        # KPIs principais
        create_premium_kpi_cards(df_processed)
        
        st.markdown("---")
        
        # Gráficos principais
        col1, col2 = st.columns([2, 1])
        
        with col1:
            chart = create_premium_sales_chart(df_processed)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
        
        with col2:
            # Calcular resultados financeiros
            resultados = calculate_financial_results(df_processed, 1550, 316, 30)
            sunburst = create_financial_sunburst(resultados)
            st.plotly_chart(sunburst, use_container_width=True)
        
        # Seção de insights
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1e3c72, #2a5298); padding: 2rem; border-radius: 15px; margin: 2rem 0;">
            <h2 style="color: #64ffda; margin: 0 0 1rem 0;">🧠 Insights Inteligentes</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">
                <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px;">
                    <h4 style="color: #ff9800; margin: 0;">📈 Tendência de Crescimento</h4>
                    <p style="color: white; margin: 0.5rem 0;">Análise automática de padrões de vendas</p>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px;">
                    <h4 style="color: #4caf50; margin: 0;">💡 Recomendações</h4>
                    <p style="color: white; margin: 0.5rem 0;">Sugestões baseadas em dados históricos</p>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px;">
                    <h4 style="color: #e91e63; margin: 0;">🎯 Metas</h4>
                    <p style="color: white; margin: 0.5rem 0;">Acompanhamento de objetivos mensais</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    else:
        st.error("Não foi possível carregar os dados. Verifique a conexão com o Google Sheets.")

if __name__ == "__main__":
    main()
