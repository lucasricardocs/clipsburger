import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página com layout centered
st.set_page_config(
    page_title="Sistema de Registro de Vendas", 
    layout="centered",
    initial_sidebar_state="expanded"
)

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
            st.write(f"Total da venda: R$ {total:.2f}")
            
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
            
            # Aplicar filtros
            df_filtered = df.copy()
            
            if selected_anos:
                df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos)]
            
            if selected_meses:
                df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)]
            
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
            st.subheader("🧾 Dados Filtrados")
            
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
            
            # Resumo dos dados
            kpis = create_kpi_metrics(df_filtered)
            
            # KPIs em cards
            st.subheader("📌 Resumo")
            kpi_cols = st.columns(2)
            
            with kpi_cols[0]:
                st.metric(
                    "Total de Vendas", 
                    f"{kpis['total_vendas']}"
                )
                st.metric(
                    "Ticket Médio", 
                    f"R$ {kpis['media_por_venda']:,.2f}"
                )
            
            with kpi_cols[1]:
                st.metric(
                    "Faturamento Total", 
                    f"R$ {kpis['total_faturamento']:,.2f}",
                    delta=f"{kpis['variacao_faturamento']:.1f}%" if kpis['variacao_faturamento'] is not None else None
                )
                st.metric(
                    "Maior Venda", 
                    f"R$ {kpis['maior_venda']:,.2f}"
                )
            
            # Acúmulo de Capital
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
                        stops=[alt.GradientStop(color='#1E1E1E', offset=0),
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
                st.write(f"💰 Capital Total Acumulado: R$ {final_value:,.2f}")
    
    # Aba 3: Estatísticas
    with tab3:
        st.header("Estatísticas Avançadas de Vendas")
        
        if df_filtered.empty:
            st.info("Não há dados para exibir com os filtros selecionados.")
        else:
            # Resumo Financeiro
            st.subheader("💰 Resumo Financeiro")
            
            # Criar KPIs
            kpis = create_kpi_metrics(df_filtered)
            
            # Primeira linha de KPIs
            kpi_cols1 = st.columns(2)
            
            with kpi_cols1[0]:
                st.metric(
                    "🔢 Total de Vendas", 
                    f"{kpis['total_vendas']}"
                )
                st.metric(
                    "📈 Média por Venda", 
                    f"R$ {kpis['media_por_venda']:,.2f}"
                )
            
            with kpi_cols1[1]:
                st.metric(
                    "💵 Faturamento Total", 
                    f"R$ {kpis['total_faturamento']:,.2f}",
                    delta=f"{kpis['variacao_faturamento']:.1f}%" if kpis['variacao_faturamento'] is not None else None
                )
                st.metric(
                    "⬆️ Maior Venda", 
                    f"R$ {kpis['maior_venda']:,.2f}"
                )
            
            # Métodos de Pagamento
            st.subheader("💳 Métodos de Pagamento")
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
                
                payment_cols[0].write(f"💳 Cartão: R$ {cartao_total:,.2f} ({cartao_pct:.1f}%)")
                payment_cols[1].write(f"💵 Dinheiro: R$ {dinheiro_total:,.2f} ({dinheiro_pct:.1f}%)")
                payment_cols[2].write(f"📱 PIX: R$ {pix_total:,.2f} ({pix_pct:.1f}%)")
                
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
            st.subheader("📅 Análise Temporal")
            if 'DiaSemana' in df_filtered.columns:
                st.write("📊 Desempenho por Dia da Semana")
                
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
                
                # Gráfico de barras para dia da semana
                bar_chart = alt.Chart(vendas_por_dia).mark_bar().encode(
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
                
                best_worst_cols[0].write(f"🔝 Melhor Dia da Semana: {melhor_dia['DiaSemana']} (R$ {melhor_dia['Total']:,.2f})")
                best_worst_cols[1].write(f"🔻 Pior Dia da Semana: {pior_dia['DiaSemana']} (R$ {pior_dia['Total']:,.2f})")

if __name__ == "__main__":
    main()
