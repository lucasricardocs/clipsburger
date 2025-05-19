import streamlit as st
import gspread
import pandas as pd
from datetime import datetime
import pygwalker as pyg
import altair as alt
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
st.set_page_config(
    page_title="Sistema de Registro de Vendas", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS para o layout
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
    .chart-container {
        background-color: #121212;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid #333;
    }
    .chart-title {
        color: #4dabf7;
        font-size: 1.2em;
        margin-bottom: 10px;
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
                
                # Ordenar dias da semana
                ordem_dias = {'Segunda': 0, 'Terça': 1, 'Quarta': 2, 'Quinta': 3, 'Sexta': 4, 'Sábado': 5}
                df['DiaSemana_order'] = df['DiaSemana'].map(ordem_dias)
        except Exception as e:
            st.warning(f"Erro ao processar datas: {e}")
    
    return df

def calculate_metrics(df):
    """Calcula métricas resumidas dos dados"""
    if df.empty:
        return {'total_vendas': 0, 'total_faturamento': 0, 'media_por_venda': 0, 'melhor_dia': None}
    
    # Métricas básicas
    total_vendas = len(df)
    total_faturamento = df['Total'].sum()
    media_por_venda = df['Total'].mean()
    
    # Calcular o melhor dia da semana
    melhor_dia = None
    if 'DiaSemana' in df.columns and not df.empty:
        vendas_por_dia = df.groupby('DiaSemana')['Total'].sum()
        if not vendas_por_dia.empty:
            melhor_dia = vendas_por_dia.idxmax()
            
    return {
        'total_vendas': total_vendas,
        'total_faturamento': total_faturamento,
        'media_por_venda': media_por_venda,
        'melhor_dia': melhor_dia
    }

def create_favorite_charts(df):
    """Cria os gráficos favoritos pré-definidos usando PyGWalker"""
    charts = {}
    
    if df.empty:
        return charts
    
    try:
        # 1. Gráfico de Tendência de Vendas (acumulado ao longo do tempo)
        df_acum = df.sort_values('Data').copy()
        df_acum['Total Acumulado'] = df_acum['Total'].cumsum()
        
        # 2. Prepare os dados para gráficos por dia da semana
        dia_semana_stats = df.groupby('DiaSemana').agg(
            Total=('Total', 'sum'),
            Quantidade=('Total', 'count'),
            Media=('Total', 'mean')
        ).reset_index()
        
        # Ordenar dias da semana corretamente
        ordem_dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
        dia_semana_stats['DiaSemana_ordem'] = dia_semana_stats['DiaSemana'].map(
            {dia: i for i, dia in enumerate(ordem_dias)}
        )
        dia_semana_stats = dia_semana_stats.sort_values('DiaSemana_ordem')
        
        # 3. Preparar dados para gráfico de métodos de pagamento
        metodo_pagamento = pd.DataFrame({
            'Método': ['Cartão', 'Dinheiro', 'PIX'],
            'Valor': [
                df['Cartão'].sum(),
                df['Dinheiro'].sum(),
                df['Pix'].sum()
            ]
        })
        total = metodo_pagamento['Valor'].sum()
        if total > 0:
            metodo_pagamento['Porcentagem'] = (metodo_pagamento['Valor'] / total * 100).round(1)
        else:
            metodo_pagamento['Porcentagem'] = 0
        
        # Armazenar os dataframes para uso com PyGWalker
        charts['df_acumulado'] = df_acum
        charts['df_dia_semana'] = dia_semana_stats
        charts['df_metodos'] = metodo_pagamento
        
        # Preparar dados para gráfico de vendas mensais
        vendas_mensais = df.groupby('AnoMês').agg(
            Total=('Total', 'sum'),
            Quantidade=('Total', 'count')
        ).reset_index()
        charts['df_mensal'] = vendas_mensais
    
    except Exception as e:
        st.error(f"Erro ao preparar dados para gráficos: {e}")
    
    return charts

def main():
    st.title("📊 Sistema de Registro de Vendas")
    
    df_raw, worksheet = read_google_sheet()
    df = process_data(df_raw)
    
    # Abas principais do aplicativo
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Registrar Venda", 
        "📈 Meus Gráficos Favoritos", 
        "🔍 Análise Interativa",
        "📋 Dados"
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
            # Filtro de Ano
            anos = sorted(df['Ano'].unique(), reverse=True)
            selected_anos = st.multiselect("Selecione o(s) Ano(s):", options=anos, default=anos[:1])
            
            # Filtro de Mês
            meses_disponiveis = sorted(df[df['Ano'].isin(selected_anos)]['Mês'].unique()) if selected_anos else []
            meses_opcoes = [f"{m:02d} - {datetime(2020, m, 1).strftime('%B')}" for m in meses_disponiveis]
            selected_meses_str = st.multiselect("Selecione o(s) Mês(es):", options=meses_opcoes, default=meses_opcoes)
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
    
    # Preparar dados para gráficos
    metrics = calculate_metrics(df_filtered)
    charts_data = create_favorite_charts(df_filtered)
    
    # Aba 2: Meus Gráficos Favoritos
    with tab2:
        st.header("Meus Gráficos Favoritos")
        
        if df_filtered.empty:
            st.info("Não há dados para exibir com os filtros selecionados.")
        else:
            # Exibir resumo em formato de cards
            st.markdown(f"""
            <div class="resumo-container">
                <div class="resumo-item">
                    <div class="resumo-titulo">Total de Vendas</div>
                    <div class="resumo-valor">{metrics['total_vendas']}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Faturamento Total</div>
                    <div class="resumo-valor">R$ {metrics['total_faturamento']:,.2f}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Ticket Médio</div>
                    <div class="resumo-valor">R$ {metrics['media_por_venda']:,.2f}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Melhor Dia</div>
                    <div class="resumo-valor">{metrics['melhor_dia'] if metrics['melhor_dia'] else 'N/A'}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Seção 1: Gráfico de acumulação de capital
            st.markdown('<div class="chart-container"><div class="chart-title">💰 Acúmulo de Capital ao Longo do Tempo</div>', unsafe_allow_html=True)
            if 'df_acumulado' in charts_data:
                df_acum = charts_data['df_acumulado']
                # Gráfico com Altair para garantir melhor renderização
                chart = alt.Chart(df_acum).mark_area(
                    color="lightblue",
                    line=True
                ).encode(
                    x=alt.X('Data:T', title='Data'),
                    y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
                    tooltip=['DataFormatada:N', alt.Tooltip('Total Acumulado:Q', format='R$ ,.2f')]
                ).properties(height=400)
                
                st.altair_chart(chart, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Seção 2: Gráfico de vendas por dia da semana
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="chart-container"><div class="chart-title">📊 Vendas por Dia da Semana</div>', unsafe_allow_html=True)
                if 'df_dia_semana' in charts_data:
                    df_dias = charts_data['df_dia_semana']
                    chart = alt.Chart(df_dias).mark_bar().encode(
                        x=alt.X('DiaSemana:N', sort=['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'], title='Dia da Semana'),
                        y=alt.Y('Total:Q', title='Total de Vendas (R$)'),
                        color=alt.Color('DiaSemana:N', legend=None),
                        tooltip=[
                            alt.Tooltip('DiaSemana:N', title='Dia'),
                            alt.Tooltip('Total:Q', title='Total', format='R$ ,.2f'),
                            alt.Tooltip('Quantidade:Q', title='Quantidade')
                        ]
                    ).properties(height=300)
                    st.altair_chart(chart, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="chart-container"><div class="chart-title">💳 Distribuição por Método de Pagamento</div>', unsafe_allow_html=True)
                if 'df_metodos' in charts_data:
                    df_met = charts_data['df_metodos']
                    chart = alt.Chart(df_met).mark_arc().encode(
                        theta=alt.Theta(field="Valor", type="quantitative"),
                        color=alt.Color(field="Método", type="nominal", 
                                       scale=alt.Scale(domain=['Cartão', 'Dinheiro', 'PIX'],
                                                     range=['#4285F4', '#34A853', '#FBBC05'])),
                        tooltip=[
                            alt.Tooltip('Método:N'),
                            alt.Tooltip('Valor:Q', format='R$ ,.2f'),
                            alt.Tooltip('Porcentagem:Q', format='.1f%')
                        ]
                    ).properties(height=300)
                    st.altair_chart(chart, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Seção 3: Vendas mensais
            st.markdown('<div class="chart-container"><div class="chart-title">📈 Evolução Mensal de Vendas</div>', unsafe_allow_html=True)
            if 'df_mensal' in charts_data and not charts_data['df_mensal'].empty:
                df_mensal = charts_data['df_mensal']
                chart = alt.Chart(df_mensal).mark_line(point=True).encode(
                    x=alt.X('AnoMês:N', title='Mês', sort=None),
                    y=alt.Y('Total:Q', title='Total (R$)'),
                    tooltip=[
                        alt.Tooltip('AnoMês:N', title='Mês'),
                        alt.Tooltip('Total:Q', title='Total', format='R$ ,.2f'),
                        alt.Tooltip('Quantidade:Q', title='Quantidade')
                    ]
                ).properties(height=350)
                
                bars = alt.Chart(df_mensal).mark_bar(opacity=0.3).encode(
                    x='AnoMês:N',
                    y='Quantidade:Q'
                )
                
                st.altair_chart(chart + bars, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Seção 4: Histograma dos valores
            st.markdown('<div class="chart-container"><div class="chart-title">📊 Distribuição dos Valores de Venda</div>', unsafe_allow_html=True)
            chart = alt.Chart(df_filtered).mark_bar().encode(
                x=alt.X('Total:Q', bin=alt.Bin(maxbins=20), title='Valor da Venda (R$)'),
                y='count()',
                tooltip=['count()', alt.Tooltip('Total:Q', format='R$ ,.2f')]
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Aba 3: Análise Interativa (PyGWalker)
    with tab3:
        st.header("Análise Interativa com PyGWalker")
        
        if df_filtered.empty:
            st.info("Não há dados para visualizar. Selecione outro período nos filtros.")
        else:
            # Preparar dados para o PyGWalker
            # Calculando o total acumulado para cada linha
            if 'Data' in df_filtered.columns:
                df_viz = df_filtered.sort_values('Data').copy()
                df_viz['Total Acumulado'] = df_viz['Total'].cumsum()
                
                # Adicionar métricas úteis para análise
                df_viz['% Cartão'] = (df_viz['Cartão'] / df_viz['Total'] * 100).round(2)
                df_viz['% Dinheiro'] = (df_viz['Dinheiro'] / df_viz['Total'] * 100).round(2)
                df_viz['% Pix'] = (df_viz['Pix'] / df_viz['Total'] * 100).round(2)
            else:
                df_viz = df_filtered.copy()
            
            st.write("### Análise interativa: arraste e solte campos para criar visualizações")
            
            # Configurar e renderizar o PyGWalker
            try:
                # Configuração personalizada para o PyGWalker
                config = {
                    "theme": "dark",
                    "enableQueryEditor": False,
                    "defaultConfigPanelCollapsed": False,
                }
                
                # Renderizar o PyGWalker como um componente HTML
                pyg_html = pyg.walk(df_viz, env='Streamlit', return_html=True, config=config)
                st.components.v1.html(pyg_html, height=800)
                
            except Exception as e:
                st.error(f"Erro ao carregar o PyGWalker: {e}")
                st.warning("""
                Se o PyGWalker não carregar, é possível usar os gráficos pré-definidos 
                na aba "Meus Gráficos Favoritos".
                """)
                st.dataframe(df_viz.head(50))
    
    # Aba 4: Dados
    with tab4:
        st.header("Dados de Vendas")
        
        if df_filtered.empty:
            st.info("Não há dados para exibir com os filtros selecionados.")
        else:
            # Dados de vendas filtrados
            st.subheader("🧾 Dados Filtrados")
            st.dataframe(
                df_filtered[['DataFormatada', 'DiaSemana', 'Cartão', 'Dinheiro', 'Pix', 'Total']],
                use_container_width=True,
                column_config={
                    "DataFormatada": st.column_config.TextColumn("Data"),
                    "DiaSemana": st.column_config.TextColumn("Dia da Semana"),
                    "Cartão": st.column_config.NumberColumn("Cartão (R$)", format="R$ %.2f"),
                    "Dinheiro": st.column_config.NumberColumn("Dinheiro (R$)", format="R$ %.2f"),
                    "Pix": st.column_config.NumberColumn("PIX (R$)", format="R$ %.2f"),
                    "Total": st.column_config.NumberColumn("Total (R$)", format="R$ %.2f")
                }
            )

if __name__ == "__main__":
    main()