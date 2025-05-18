import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página com layout wide
st.set_page_config(
    page_title="Sistema de Registro de Vendas", 
    layout="centered",
    initial_sidebar_state="expanded"
)

# CSS personalizado para melhorar a aparência
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }
    .stMetric:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
    }
    h1, h2, h3 {
        color: #1E3A8A;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: white;
        border-radius: 5px 5px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E3A8A;
        color: white;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #ddd;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    div[data-testid="stForm"] {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 20px;
        background-color: white;
    }
    div[data-testid="stVerticalBlock"] {
        gap: 20px;
    }
    button[kind="primaryFormSubmit"] {
        background-color: #1E3A8A;
        color: white;
    }
    .stDataFrame {
        border: 1px solid #ddd;
        border-radius: 10px;
    }
    .sidebar .sidebar-content {
        background-color: #f1f5f9;
    }
</style>
""", unsafe_allow_html=True)

# Habilitar tema para gráficos Altair
alt.themes.enable('fivethirtyeight')

@st.cache_data(ttl=300)  # Cache por 5 minutos
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

@st.cache_data(ttl=300)  # Cache por 5 minutos
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
            # Remover linhas com datas inválidas
            df = df.dropna(subset=['Data'])
            
            if not df.empty:
                # Colunas derivadas de data
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['MêsNome'] = df['Data'].dt.strftime('%B')
                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                df['DiaSemana'] = df['Data'].dt.day_name()
                df['DiaSemanaNum'] = df['Data'].dt.dayofweek  # 0=Segunda, 6=Domingo
                
                # Mapeamento de dias da semana para português
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
        except Exception as e:
            st.warning(f"Erro ao processar datas: {e}")
    
    return df

@st.cache_data
def convert_df_to_csv(df):
    """Converter DataFrame para CSV para download"""
    return df.to_csv(index=False).encode('utf-8')

def create_kpi_metrics(df):
    """Criar métricas KPI a partir do DataFrame"""
    total_vendas = len(df)
    total_faturamento = df['Total'].sum()
    media_por_venda = df['Total'].mean() if total_vendas > 0 else 0
    maior_venda = df['Total'].max() if total_vendas > 0 else 0
    menor_venda = df['Total'].min() if total_vendas > 0 else 0
    
    # Calcular variação em relação ao período anterior (se possível)
    variacao_faturamento = None
    if 'Mês' in df.columns and 'Ano' in df.columns and not df.empty:
        # Agrupar por mês e ano
        vendas_mensais = df.groupby(['Ano', 'Mês'])['Total'].sum().reset_index()
        if len(vendas_mensais) >= 2:
            ultimo_mes = vendas_mensais.iloc[-1]['Total']
            penultimo_mes = vendas_mensais.iloc[-2]['Total']
            if penultimo_mes > 0:
                variacao_faturamento = ((ultimo_mes - penultimo_mes) / penultimo_mes) * 100
    
    return {
        'total_vendas': total_vendas,
        'total_faturamento': total_faturamento,
        'media_por_venda': media_por_venda,
        'maior_venda': maior_venda,
        'menor_venda': menor_venda,
        'variacao_faturamento': variacao_faturamento
    }

def main():
    # Título principal com logo/ícone
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
        
        with st.container(border=True):
            with st.form("venda_form"):
                data = st.date_input("📅 Data da Venda", datetime.now())
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    cartao = st.number_input("💳 Cartão (R$)", 
                                           min_value=0.0, 
                                           format="%.2f",
                                           help="Valor recebido em cartão de crédito/débito")
                with col2:
                    dinheiro = st.number_input("💵 Dinheiro (R$)", 
                                             min_value=0.0, 
                                             format="%.2f",
                                             help="Valor recebido em dinheiro")
                with col3:
                    pix = st.number_input("📱 PIX (R$)", 
                                        min_value=0.0, 
                                        format="%.2f",
                                        help="Valor recebido via PIX")
                
                total = cartao + dinheiro + pix
                
                # Mostrar total calculado
                st.markdown(f"""
                <div style='background-color:#f0f8ff; padding:10px; border-radius:5px; margin:10px 0;'>
                    <h3 style='margin:0; text-align:center;'>Total da venda: R$ {total:.2f}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                submitted = st.form_submit_button("💾 Registrar Venda", 
                                               use_container_width=True,
                                               type="primary")
                
                if submitted:
                    if total > 0:
                        formatted_date = data.strftime('%d/%m/%Y')
                        success = add_data_to_sheet(formatted_date, cartao, dinheiro, pix, worksheet)
                        if success:
                            # Limpar o cache para forçar recarga dos dados
                            st.cache_data.clear()
                            # Recarregar a página
                            st.rerun()
                    else:
                        st.warning("⚠️ O valor total da venda deve ser maior que zero.")
    
    # Filtros na sidebar para as abas de análise e estatísticas
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
            
            # Filtro de Método de Pagamento
            payment_methods = ["Cartão", "Dinheiro", "Pix"]
            selected_methods = st.multiselect(
                "Métodos de Pagamento:",
                options=payment_methods,
                default=payment_methods,
                key="filter_methods"
            )
            
            # Botão para limpar filtros
            if st.button("🔄 Limpar Filtros", use_container_width=True):
                st.session_state["filter_years"] = default_anos
                st.session_state["filter_months"] = default_meses if default_meses else meses_opcoes
                st.session_state["filter_methods"] = payment_methods
                st.rerun()
            
            # Aplicar filtros
            df_filtered = df.copy()
            
            if selected_anos:
                df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos)]
            
            if selected_meses:
                df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)]
            
            # Exportar dados filtrados
            if not df_filtered.empty:
                st.markdown("---")
                st.subheader("📤 Exportar Dados")
                csv = convert_df_to_csv(df_filtered)
                st.download_button(
                    label="📥 Baixar como CSV",
                    data=csv,
                    file_name=f"vendas_{'_'.join(str(a) for a in selected_anos)}_{'-'.join(str(m) for m in selected_meses)}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
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
            with st.container(border=True):
                st.subheader("🧾 Dados Filtrados")
                
                # Adicionar botões para alternar entre tabela e cartões
                view_type = st.radio(
                    "Visualização:",
                    ["Tabela", "Cartões"],
                    horizontal=True,
                    key="view_type"
                )
                
                if view_type == "Tabela":
                    # Mostrar como tabela
                    st.dataframe(
                        df_filtered[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total', 'DiaSemana']], 
                        use_container_width=True,
                        height=300,
                        column_config={
                            "DataFormatada": st.column_config.TextColumn("Data"),
                            "Cartão": st.column_config.NumberColumn("Cartão (R$)", format="R$ %.2f"),
                            "Dinheiro": st.column_config.NumberColumn("Dinheiro (R$)", format="R$ %.2f"),
                            "Pix": st.column_config.NumberColumn("PIX (R$)", format="R$ %.2f"),
                            "Total": st.column_config.NumberColumn("Total (R$)", format="R$ %.2f"),
                            "DiaSemana": st.column_config.TextColumn("Dia da Semana")
                        },
                        hide_index=True
                    )
                else:
                    # Mostrar como cartões
                    num_cards_to_show = min(10, len(df_filtered))
                    for i in range(0, num_cards_to_show, 3):
                        cols = st.columns(3)
                        for j in range(3):
                            if i+j < num_cards_to_show:
                                venda = df_filtered.iloc[i+j]
                                with cols[j]:
                                    st.markdown(f"""
                                    <div style='background-color:white; padding:15px; border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,0.1); height:200px;'>
                                        <h4 style='color:#1E3A8A; margin-top:0;'>{venda['DataFormatada']} ({venda['DiaSemana']})</h4>
                                        <p><b>Cartão:</b> R$ {venda['Cartão']:.2f}</p>
                                        <p><b>Dinheiro:</b> R$ {venda['Dinheiro']:.2f}</p>
                                        <p><b>PIX:</b> R$ {venda['Pix']:.2f}</p>
                                        <h3 style='color:#1E3A8A; text-align:right;'>R$ {venda['Total']:.2f}</h3>
                                    </div>
                                    """, unsafe_allow_html=True)
                    
                    if num_cards_to_show < len(df_filtered):
                        st.info(f"Mostrando {num_cards_to_show} de {len(df_filtered)} vendas. Use a visualização em tabela para ver todas.")
            
            # Resumo dos dados
            kpis = create_kpi_metrics(df_filtered)
            
            # KPIs em cards
            st.subheader("📌 Resumo")
            kpi_cols = st.columns(4)
            
            with kpi_cols[0]:
                st.metric(
                    "Total de Vendas", 
                    f"{kpis['total_vendas']}"
                )
            
            with kpi_cols[1]:
                st.metric(
                    "Faturamento Total", 
                    f"R$ {kpis['total_faturamento']:,.2f}",
                    delta=f"{kpis['variacao_faturamento']:.1f}%" if kpis['variacao_faturamento'] is not None else None
                )
            
            with kpi_cols[2]:
                st.metric(
                    "Ticket Médio", 
                    f"R$ {kpis['media_por_venda']:,.2f}"
                )
            
            with kpi_cols[3]:
                st.metric(
                    "Maior Venda", 
                    f"R$ {kpis['maior_venda']:,.2f}"
                )
            
            # Gráficos
            st.markdown("---")
            
            # Distribuição por Método de Pagamento
            with st.container(border=True):
                st.subheader("💳 Distribuição por Método de Pagamento")
                
                payment_data = pd.DataFrame({
                    'Método': ['Cartão', 'Dinheiro', 'PIX'],
                    'Valor': [
                        df_filtered['Cartão'].sum(), 
                        df_filtered['Dinheiro'].sum(), 
                        df_filtered['Pix'].sum()
                    ]
                })
                
                # Adicionar porcentagem
                total_pagamentos = payment_data['Valor'].sum()
                if total_pagamentos > 0:
                    payment_data['Porcentagem'] = payment_data['Valor'] / total_pagamentos * 100
                    
                    # Mostrar valores e porcentagens em texto
                    payment_cols = st.columns(3)
                    for i, metodo in enumerate(['Cartão', 'Dinheiro', 'PIX']):
                        valor = payment_data[payment_data['Método'] == metodo]['Valor'].values[0]
                        pct = payment_data[payment_data['Método'] == metodo]['Porcentagem'].values[0]
                        
                        icone = "💳" if metodo == "Cartão" else "💵" if metodo == "Dinheiro" else "📱"
                        
                        payment_cols[i].markdown(f"""
                        <div style='background-color:white; padding:15px; border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,0.1); text-align:center;'>
                            <h3 style='margin:0;'>{icone} {metodo}</h3>
                            <h2 style='margin:10px 0;'>R$ {valor:,.2f}</h2>
                            <p style='margin:0; color:#666;'>{pct:.1f}% do total</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Gráfico de pizza
                    pie_chart = alt.Chart(payment_data).mark_arc(innerRadius=70).encode(
                        theta=alt.Theta("Valor:Q", stack=True),
                        color=alt.Color("Método:N", 
                                      legend=alt.Legend(title="Método de Pagamento"),
                                      scale=alt.Scale(domain=['Cartão', 'Dinheiro', 'PIX'],
                                                    range=['#4285F4', '#34A853', '#FBBC05'])),
                        tooltip=[
                            alt.Tooltip("Método:N", title="Método"),
                            alt.Tooltip("Valor:Q", title="Valor", format="R$ ,.2f"),
                            alt.Tooltip("Porcentagem:Q", title="Porcentagem", format=".1f%")
                        ]
                    ).properties(
                        height=400
                    )
                    
                    # Texto no centro do gráfico
                    text_pie = pie_chart.mark_text(radius=150, size=16).encode(
                        text=alt.Text("Valor:Q", format="R$ ,.2f")
                    )
                    
                    st.altair_chart(pie_chart + text_pie, use_container_width=True)
            
            # Vendas Diárias
            with st.container(border=True):
                st.subheader("📆 Vendas Diárias por Método de Pagamento")
                
                if 'DataFormatada' in df_filtered.columns:
                    # Preparar dados para o gráfico
                    daily_data = df_filtered.melt(
                        id_vars=['DataFormatada', 'Data'], 
                        value_vars=['Cartão', 'Dinheiro', 'Pix'],
                        var_name='Método', 
                        value_name='Valor'
                    )
                    
                    # Filtrar apenas valores positivos
                    daily_data = daily_data[daily_data['Valor'] > 0]
                    
                    # Gráfico de barras empilhadas
                    bar_chart = alt.Chart(daily_data).mark_bar().encode(
                        x=alt.X('DataFormatada:N', 
                              title='Data', 
                              sort=alt.EncodingSortField(field="Data", order='ascending'),
                              axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y('Valor:Q', 
                              title='Valor (R$)',
                              stack='zero'),
                        color=alt.Color('Método:N', 
                                      legend=alt.Legend(title="Método de Pagamento"),
                                      scale=alt.Scale(domain=['Cartão', 'Dinheiro', 'Pix'],
                                                    range=['#4285F4', '#34A853', '#FBBC05'])),
                        tooltip=[
                            alt.Tooltip('DataFormatada:N', title='Data'),
                            alt.Tooltip('Método:N', title='Método'),
                            alt.Tooltip('Valor:Q', title='Valor', format='R$ ,.2f')
                        ]
                    ).properties(
                        height=400
                    )
                    
                    # Adicionar linha com total diário
                    daily_totals = df_filtered.groupby('DataFormatada')['Total'].sum().reset_index()
                    
                    line_chart = alt.Chart(daily_totals).mark_line(
                        color='red',
                        strokeWidth=3,
                        point=alt.OverlayMarkDef(color="red", size=80)
                    ).encode(
                        x=alt.X('DataFormatada:N', title='Data'),
                        y=alt.Y('Total:Q', title='Total (R$)'),
                        tooltip=[
                            alt.Tooltip('DataFormatada:N', title='Data'),
                            alt.Tooltip('Total:Q', title='Total', format='R$ ,.2f')
                        ]
                    )
                    
                    # Combinar gráficos
                    st.altair_chart(bar_chart + line_chart, use_container_width=True)
                    
                    # Estatísticas de vendas diárias
                    daily_stats_cols = st.columns(3)
                    
                    with daily_stats_cols[0]:
                        max_day = daily_totals.loc[daily_totals['Total'].idxmax()]
                        st.markdown(f"""
                        <div style='background-color:#f0f8ff; padding:15px; border-radius:10px; text-align:center;'>
                            <h4 style='margin:0;'>⭐ Melhor Dia</h4>
                            <h3 style='margin:5px 0;'>{max_day['DataFormatada']}</h3>
                            <h2 style='margin:0;'>R$ {max_day['Total']:,.2f}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with daily_stats_cols[1]:
                        min_day = daily_totals.loc[daily_totals['Total'].idxmin()]
                        st.markdown(f"""
                        <div style='background-color:#fff0f0; padding:15px; border-radius:10px; text-align:center;'>
                            <h4 style='margin:0;'>📉 Pior Dia</h4>
                            <h3 style='margin:5px 0;'>{min_day['DataFormatada']}</h3>
                            <h2 style='margin:0;'>R$ {min_day['Total']:,.2f}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with daily_stats_cols[2]:
                        avg_daily = daily_totals['Total'].mean()
                        st.markdown(f"""
                        <div style='background-color:#f0fff0; padding:15px; border-radius:10px; text-align:center;'>
                            <h4 style='margin:0;'>📊 Média Diária</h4>
                            <h3 style='margin:5px 0;'>&nbsp;</h3>
                            <h2 style='margin:0;'>R$ {avg_daily:,.2f}</h2>
                        </div>
                        """, unsafe_allow_html=True)
            
            # Acúmulo de Capital
            with st.container(border=True):
                st.subheader("💰 Acúmulo de Capital ao Longo do Tempo")
                
                if not df_filtered.empty and 'Data' in df_filtered.columns:
                    # Ordenar por data
                    df_accumulated = df_filtered.sort_values('Data').copy()
                    df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()
                    
                    # Gráfico de linha
                    line_chart = alt.Chart(df_accumulated).mark_area(
                        opacity=0.5,
                        line={'color': '#4285F4'},
                        color=alt.Gradient(
                            gradient='linear',
                            stops=[alt.GradientStop(color='white', offset=0),
                                  alt.GradientStop(color='#4285F4', offset=1)],
                            x1=0,
                            y1=1,
                            x2=0,
                            y2=0
                        )
                    ).encode(
                        x=alt.X('Data:T', 
                              title='Data',
                              axis=alt.Axis(format='%d/%m/%Y', labelAngle=-45)),
                        y=alt.Y('Total Acumulado:Q', 
                              title='Capital Acumulado (R$)'),
                        tooltip=[
                            alt.Tooltip('DataFormatada:N', title='Data'),
                            alt.Tooltip('Total Acumulado:Q', title='Acumulado', format='R$ ,.2f'),
                            alt.Tooltip('Total:Q', title='Venda do Dia', format='R$ ,.2f')
                        ]
                    ).properties(
                        height=400
                    )
                    
                    # Adicionar pontos
                    points = alt.Chart(df_accumulated).mark_circle(
                        size=80,
                        color='#4285F4'
                    ).encode(
                        x='Data:T',
                        y='Total Acumulado:Q'
                    )
                    
                    st.altair_chart(line_chart + points, use_container_width=True)
                    
                    # Mostrar valor final acumulado
                    final_value = df_accumulated['Total Acumulado'].iloc[-1]
                    st.markdown(f"""
                    <div style='background-color:#f0f8ff; padding:15px; border-radius:10px; text-align:center; margin-top:10px;'>
                        <h4 style='margin:0;'>💰 Capital Total Acumulado</h4>
                        <h1 style='margin:10px 0; color:#1E3A8A;'>R$ {final_value:,.2f}</h1>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Aba 3: Estatísticas
    with tab3:
        st.header("Estatísticas Avançadas de Vendas")
        
        if df_filtered.empty:
            st.info("Não há dados para exibir com os filtros selecionados.")
        else:
            # Resumo Financeiro
            with st.container(border=True):
                st.subheader("💰 Resumo Financeiro")
                
                # Criar KPIs
                kpis = create_kpi_metrics(df_filtered)
                
                # Primeira linha de KPIs
                kpi_cols1 = st.columns(3)
                
                with kpi_cols1[0]:
                    st.metric(
                        "🔢 Total de Vendas", 
                        f"{kpis['total_vendas']}"
                    )
                
                with kpi_cols1[1]:
                    st.metric(
                        "💵 Faturamento Total", 
                        f"R$ {kpis['total_faturamento']:,.2f}",
                        delta=f"{kpis['variacao_faturamento']:.1f}%" if kpis['variacao_faturamento'] is not None else None
                    )
                
                with kpi_cols1[2]:
                    st.metric(
                        "📈 Média por Venda", 
                        f"R$ {kpis['media_por_venda']:,.2f}"
                    )
                
                # Segunda linha de KPIs
                kpi_cols2 = st.columns(2)
                
                with kpi_cols2[0]:
                    st.metric(
                        "⬆️ Maior Venda", 
                        f"R$ {kpis['maior_venda']:,.2f}"
                    )
                
                with kpi_cols2[1]:
                    st.metric(
                        "⬇️ Menor Venda", 
                        f"R$ {kpis['menor_venda']:,.2f}"
                    )
            
            # Métodos de Pagamento
            with st.expander("💳 Métodos de Pagamento", expanded=True):
                cartao_total = df_filtered['Cartão'].sum()
                dinheiro_total = df_filtered['Dinheiro'].sum()
                pix_total = df_filtered['Pix'].sum()
                
                total_pagamentos = cartao_total + dinheiro_total + pix_total
                
                if total_pagamentos > 0:
                    cartao_pct = (cartao_total / total_pagamentos * 100)
                    dinheiro_pct = (dinheiro_total / total_pagamentos * 100)
                    pix_pct = (pix_total / total_pagamentos * 100)
                    
                    # Mostrar valores e porcentagens
                    payment_cols = st.columns(3)
                    
                    payment_cols[0].markdown(f"""
                    <div style='background-color:white; padding:15px; border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,0.1); text-align:center;'>
                        <h3 style='margin:0;'>💳 Cartão</h3>
                        <h2 style='margin:10px 0;'>R$ {cartao_total:,.2f}</h2>
                        <div style='background-color:#f0f0f0; border-radius:5px; padding:5px;'>
                            <div style='background-color:#4285F4; width:{cartao_pct}%; height:10px; border-radius:5px;'></div>
                        </div>
                        <p style='margin:5px 0;'>{cartao_pct:.1f}%</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    payment_cols[1].markdown(f"""
                    <div style='background-color:white; padding:15px; border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,0.1); text-align:center;'>
                        <h3 style='margin:0;'>💵 Dinheiro</h3>
                        <h2 style='margin:10px 0;'>R$ {dinheiro_total:,.2f}</h2>
                        <div style='background-color:#f0f0f0; border-radius:5px; padding:5px;'>
                            <div style='background-color:#34A853; width:{dinheiro_pct}%; height:10px; border-radius:5px;'></div>
                        </div>
                        <p style='margin:5px 0;'>{dinheiro_pct:.1f}%</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    payment_cols[2].markdown(f"""
                    <div style='background-color:white; padding:15px; border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,0.1); text-align:center;'>
                        <h3 style='margin:0;'>📱 PIX</h3>
                        <h2 style='margin:10px 0;'>R$ {pix_total:,.2f}</h2>
                        <div style='background-color:#f0f0f0; border-radius:5px; padding:5px;'>
                            <div style='background-color:#FBBC05; width:{pix_pct}%; height:10px; border-radius:5px;'></div>
                        </div>
                        <p style='margin:5px 0;'>{pix_pct:.1f}%</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Gráfico de pizza para métodos de pagamento
                    payment_data = pd.DataFrame({
                        'Método': ['Cartão', 'Dinheiro', 'PIX'],
                        'Valor': [cartao_total, dinheiro_total, pix_total],
                        'Porcentagem': [cartao_pct, dinheiro_pct, pix_pct]
                    })
                    
                    pie_chart = alt.Chart(payment_data).mark_arc(innerRadius=70).encode(
                        theta=alt.Theta("Valor:Q", stack=True),
                        color=alt.Color("Método:N", 
                                      legend=alt.Legend(title="Método"),
                                      scale=alt.Scale(domain=['Cartão', 'Dinheiro', 'PIX'],
                                                    range=['#4285F4', '#34A853', '#FBBC05'])),
                        tooltip=[
                            alt.Tooltip("Método:N", title="Método"),
                            alt.Tooltip("Valor:Q", title="Valor", format="R$ ,.2f"),
                            alt.Tooltip("Porcentagem:Q", title="Porcentagem", format=".1f%")
                        ]
                    ).properties(
                        height=400
                    )
                    
                    text = pie_chart.mark_text(radius=120, size=16).encode(
                        text=alt.Text("Porcentagem:Q", format=".1f%")
                    )
                    
                    st.altair_chart(pie_chart + text, use_container_width=True)
            
            # Análise Temporal
            with st.expander("📅 Análise Temporal", expanded=True):
                if 'DiaSemana' in df_filtered.columns:
                    st.subheader("📊 Desempenho por Dia da Semana")
                    
                    # Dias da semana em português e ordem correta
                    dias_ordem = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
                    
                    # Agrupando por dia da semana
                    vendas_por_dia = df_filtered.groupby('DiaSemana')['Total'].mean().reset_index()
                    
                    # Garantir que todos os dias estão presentes
                    for dia in dias_ordem:
                        if dia not in vendas_por_dia['DiaSemana'].values:
                            vendas_por_dia = pd.concat([vendas_por_dia, pd.DataFrame({'DiaSemana': [dia], 'Total': [0]})], ignore_index=True)
                    
                    # Ordenar dias da semana
                    vendas_por_dia['DiaSemanaOrdem'] = vendas_por_dia['DiaSemana'].map({dia: i for i, dia in enumerate(dias_ordem)})
                    vendas_por_dia = vendas_por_dia.sort_values('DiaSemanaOrdem')
                    
                    # Normalizar para mapa de calor
                    max_valor = vendas_por_dia['Total'].max() if vendas_por_dia['Total'].max() > 0 else 1
                    vendas_por_dia['Normalizado'] = vendas_por_dia['Total'] / max_valor
                    
                    # Mapa de calor
                    heatmap = alt.Chart(vendas_por_dia).mark_rect().encode(
                        x=alt.X('DiaSemana:N', 
                              title='Dia da Semana', 
                              sort=dias_ordem),
                        y=alt.Y('Total:Q', 
                              title='', 
                              axis=None),
                        color=alt.Color('Normalizado:Q', 
                                      scale=alt.Scale(domain=[0, 1], 
                                                    range=['#FF9999', '#FFFF99', '#99FF99']),
                                      legend=None),
                        tooltip=[
                            alt.Tooltip('DiaSemana:N', title='Dia'),
                            alt.Tooltip('Total:Q', title='Média', format='R$ ,.2f')
                        ]
                    ).properties(
                        title='Média de Vendas por Dia da Semana',
                        height=100
                    )
                    
                    # Texto para o mapa de calor
                    text = alt.Chart(vendas_por_dia).mark_text(baseline='middle').encode(
                        x=alt.X('DiaSemana:N', sort=dias_ordem),
                        y=alt.Y('Total:Q', axis=None),
                        text=alt.Text('Total:Q', format='R$ ,.2f'),
                        color=alt.condition(
                            alt.datum.Normalizado > 0.5,
                            alt.value('black'),
                            alt.value('black')
                        )
                    )
                    
                    # Combinar mapa de calor e texto
                    chart_final = (heatmap + text).properties(height=200)
                    st.altair_chart(chart_final, use_container_width=True)
                    
                    # Gráfico de barras para dia da semana
                    bar_chart = alt.Chart(vendas_por_dia).mark_bar(
                        cornerRadiusTopLeft=5,
                        cornerRadiusTopRight=5
                    ).encode(
                        x=alt.X('DiaSemana:N', 
                              title='Dia da Semana', 
                              sort=dias_ordem),
                        y=alt.Y('Total:Q', 
                              title='Média de Vendas (R$)'),
                        color=alt.Color('DiaSemana:N', 
                                      legend=None,
                                      scale=alt.Scale(scheme='category10')),
                        tooltip=[
                            alt.Tooltip('DiaSemana:N', title='Dia'),
                            alt.Tooltip('Total:Q', title='Média', format='R$ ,.2f')
                        ]
                    ).properties(
                        height=400
                    )
                    
                    # Adicionar valores no topo das barras
                    text_bar = bar_chart.mark_text(
                        align='center',
                        baseline='bottom',
                        dy=-5
                    ).encode(
                        text=alt.Text('Total:Q', format='R$ ,.2f')
                    )
                    
                    st.altair_chart(bar_chart + text_bar, use_container_width=True)
                    
                    # Destacar melhor e pior dia
                    melhor_dia = vendas_por_dia.loc[vendas_por_dia['Total'].idxmax()]
                    pior_dia = vendas_por_dia.loc[vendas_por_dia['Total'].idxmin()]
                    
                    best_worst_cols = st.columns(2)
                    
                    best_worst_cols[0].markdown(f"""
                    <div style='background-color:#f0fff0; padding:15px; border-radius:10px; text-align:center;'>
                        <h4 style='margin:0;'>🔝 Melhor Dia da Semana</h4>
                        <h2 style='margin:10px 0;'>{melhor_dia['DiaSemana']}</h2>
                        <h3 style='margin:0;'>R$ {melhor_dia['Total']:,.2f}</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    best_worst_cols[1].markdown(f"""
                    <div style='background-color:#fff0f0; padding:15px; border-radius:10px; text-align:center;'>
                        <h4 style='margin:0;'>🔻 Pior Dia da Semana</h4>
                        <h2 style='margin:10px 0;'>{pior_dia['DiaSemana']}</h2>
                        <h3 style='margin:0;'>R$ {pior_dia['Total']:,.2f}</h3>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Tendência Mensal
            if 'AnoMês' in df_filtered.columns and df_filtered['AnoMês'].nunique() > 1:
                with st.expander("📈 Tendência Mensal", expanded=True):
                    st.subheader("📈 Evolução Mensal de Vendas")
                    
                    # Agrupar por mês
                    vendas_mensais = df_filtered.groupby('AnoMês').agg({
                        'Total': 'sum',
                        'Data': 'count'
                    }).reset_index()
                    vendas_mensais.rename(columns={'Data': 'Quantidade'}, inplace=True)
                    
                    # Calcular variação percentual
                    if len(vendas_mensais) >= 2:
                        vendas_mensais['Variação %'] = vendas_mensais['Total'].pct_change() * 100
                        
                        # Mostrar variação do último mês
                        ultimo_mes = vendas_mensais.iloc[-1]
                        variacao = ultimo_mes['Variação %']
                        
                        if not pd.isna(variacao):
                            icone = "🚀" if variacao > 10 else "📈" if variacao > 0 else "📉" if variacao < 0 else "➡️"
                            
                            st.markdown(f"""
                            <div style='background-color:{'#f0fff0' if variacao > 0 else '#fff0f0'}; padding:15px; border-radius:10px; text-align:center; margin-bottom:20px;'>
                                <h4 style='margin:0;'>{icone} Variação em {ultimo_mes['AnoMês']}</h4>
                                <h1 style='margin:10px 0; color:{'#34A853' if variacao > 0 else '#EA4335'};'>{variacao:+.1f}%</h1>
                                <p style='margin:0;'>Em relação ao mês anterior</p>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Gráfico de linha para tendência mensal
                    line_chart = alt.Chart(vendas_mensais).mark_line(
                        point=alt.OverlayMarkDef(size=100),
                        strokeWidth=3
                    ).encode(
                        x=alt.X('AnoMês:N', 
                              title='Mês',
                              sort=None),
                        y=alt.Y('Total:Q', 
                              title='Total de Vendas (R$)'),
                        tooltip=[
                            alt.Tooltip('AnoMês:N', title='Mês'),
                            alt.Tooltip('Total:Q', title='Total', format='R$ ,.2f'),
                            alt.Tooltip('Quantidade:Q', title='Quantidade'),
                            alt.Tooltip('Variação %:Q', title='Variação', format='+.1f%')
                        ]
                    ).properties(
                        height=400
                    )
                    
                    # Adicionar barras para quantidade
                    bar_chart = alt.Chart(vendas_mensais).mark_bar(
                        opacity=0.3,
                        color='#4285F4'
                    ).encode(
                        x=alt.X('AnoMês:N', sort=None),
                        y=alt.Y('Quantidade:Q', 
                              title='Quantidade de Vendas',
                              axis=alt.Axis(titleColor='#4285F4'))
                    )
                    
                    # Criar escala secundária para quantidade
                    st.altair_chart(alt.layer(line_chart, bar_chart).resolve_scale(
                        y='independent'
                    ), use_container_width=True)
                    
                    # Tabela com dados mensais
                    st.markdown("### Detalhamento Mensal")
                    
                    # Formatar tabela
                    vendas_mensais_display = vendas_mensais.copy()
                    vendas_mensais_display['Total'] = vendas_mensais_display['Total'].map('R$ {:.2f}'.format)
                    vendas_mensais_display['Variação %'] = vendas_mensais_display['Variação %'].map('{:+.1f}%'.format)
                    
                    st.dataframe(
                        vendas_mensais_display,
                        column_config={
                            "AnoMês": st.column_config.TextColumn("Mês"),
                            "Total": st.column_config.TextColumn("Total"),
                            "Quantidade": st.column_config.NumberColumn("Qtd. Vendas"),
                            "Variação %": st.column_config.TextColumn("Variação")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
            
            # Projeções e Metas
            with st.expander("🎯 Projeções e Metas", expanded=True):
                st.subheader("🎯 Projeções e Metas")
                
                # Calcular média diária
                dias_distintos = df_filtered['Data'].nunique()
                media_diaria = kpis['total_faturamento'] / dias_distintos if dias_distintos > 0 else 0
                
                # Projeções
                projecao_mensal = media_diaria * 20  # 20 dias úteis
                meta_mensal = projecao_mensal * 1.2  # Meta 20% acima da projeção
                meta_diaria = meta_mensal / 20
                
                # Mostrar projeções em cards
                proj_cols = st.columns(3)
                
                proj_cols[0].markdown(f"""
                <div style='background-color:#f0f8ff; padding:15px; border-radius:10px; text-align:center;'>
                    <h4 style='margin:0;'>📊 Média Diária</h4>
                    <h2 style='margin:10px 0;'>R$ {media_diaria:,.2f}</h2>
                    <p style='margin:0; color:#666;'>Baseado em {dias_distintos} dias</p>
                </div>
                """, unsafe_allow_html=True)
                
                proj_cols[1].markdown(f"""
                <div style='background-color:#f0fff0; padding:15px; border-radius:10px; text-align:center;'>
                    <h4 style='margin:0;'>📅 Projeção Mensal</h4>
                    <h2 style='margin:10px 0;'>R$ {projecao_mensal:,.2f}</h2>
                    <p style='margin:0; color:#666;'>Baseado em 20 dias úteis</p>
                </div>
                """, unsafe_allow_html=True)
                
                proj_cols[2].markdown(f"""
                <div style='background-color:#fff8f0; padding:15px; border-radius:10px; text-align:center;'>
                    <h4 style='margin:0;'>🌟 Meta Mensal</h4>
                    <h2 style='margin:10px 0;'>R$ {meta_mensal:,.2f}</h2>
                    <p style='margin:0; color:#666;'>Meta diária: R$ {meta_diaria:,.2f}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Taxa de crescimento se houver dados suficientes
                if 'AnoMês' in df_filtered.columns and df_filtered['AnoMês'].nunique() >= 3:
                    st.markdown("### 📈 Previsão Baseada em Tendência")
                    
                    vendas_mensais = df_filtered.groupby('AnoMês')['Total'].sum().reset_index()
                    
                    # Calcular taxa média de crescimento
                    taxas = []
                    for i in range(1, len(vendas_mensais)):
                        if vendas_mensais.iloc[i-1]['Total'] > 0:
                            taxa = (vendas_mensais.iloc[i]['Total'] / vendas_mensais.iloc[i-1]['Total']) - 1
                            taxas.append(taxa)
                    
                    if taxas:
                        taxa_media = sum(taxas) / len(taxas)
                        ultimo_mes = vendas_mensais.iloc[-1]['Total']
                        previsao_proximo = ultimo_mes * (1 + taxa_media)
                        
                        # Mostrar previsão
                        taxa_cols = st.columns(2)
                        
                        taxa_cols[0].markdown(f"""
                        <div style='background-color:#f0f8ff; padding:15px; border-radius:10px; text-align:center;'>
                            <h4 style='margin:0;'>📈 Taxa Média de Crescimento</h4>
                            <h2 style='margin:10px 0;'>{taxa_media*100:+.1f}%</h2>
                            <p style='margin:0; color:#666;'>Baseado em {len(taxas)} períodos</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        taxa_cols[1].markdown(f"""
                        <div style='background-color:#f0fff0; padding:15px; border-radius:10px; text-align:center;'>
                            <h4 style='margin:0;'>🔮 Previsão Próximo Mês</h4>
                            <h2 style='margin:10px 0;'>R$ {previsao_proximo:,.2f}</h2>
                            <p style='margin:0; color:#666;'>Baseado na taxa histórica</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Gráfico de previsão
                        # Adicionar ponto de previsão
                        ultimo_mes_str = vendas_mensais.iloc[-1]['AnoMês']
                        proximo_mes_str = f"Previsão"
                        
                        dados_previsao = pd.DataFrame([
                            {'AnoMês': ultimo_mes_str, 'Total': ultimo_mes, 'Tipo': 'Histórico'},
                            {'AnoMês': proximo_mes_str, 'Total': previsao_proximo, 'Tipo': 'Previsão'}
                        ])
                        
                        chart_previsao = alt.Chart(dados_previsao).mark_line(
                            strokeDash=[5, 5],
                            strokeWidth=2,
                            color='#EA4335'
                        ).encode(
                            x=alt.X('AnoMês:N', title=''),
                            y=alt.Y('Total:Q', title='Valor (R$)'),
                            tooltip=['AnoMês:N', alt.Tooltip('Total:Q', format='R$ ,.2f'), 'Tipo:N']
                        )
                        
                        # Adicionar pontos
                        points_previsao = alt.Chart(dados_previsao).mark_circle(
                            size=100
                        ).encode(
                            x='AnoMês:N',
                            y='Total:Q',
                            color=alt.Color('Tipo:N', scale=alt.Scale(domain=['Histórico', 'Previsão'],
                                                                    range=['#4285F4', '#EA4335']))
                        )
                        
                        # Adicionar texto
                        text_previsao = alt.Chart(dados_previsao).mark_text(
                            align='center',
                            baseline='bottom',
                            dy=-10,
                            fontSize=14
                        ).encode(
                            x='AnoMês:N',
                            y='Total:Q',
                            text=alt.Text('Total:Q', format='R$ ,.2f'),
                            color=alt.Color('Tipo:N', scale=alt.Scale(domain=['Histórico', 'Previsão'],
                                                                    range=['#4285F4', '#EA4335']))
                        )
                        
                        st.altair_chart(chart_previsao + points_previsao + text_previsao, use_container_width=True)

if __name__ == "__main__":
    main()
