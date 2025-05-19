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

# CSS para resumo em 2 colunas
st.markdown("""
<style>
    .resumo-container {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
        margin-bottom: 25px;
    }
    .resumo-item {
        background-color: #1e1e1e;  /* Fundo escuro */
        color: #ffffff;  /* Texto claro */
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333333;
    }
    .resumo-titulo {
        font-size: 1.1em;
        color: #4dabf7;  /* Azul claro */
        margin-bottom: 10px;
        font-weight: 600;
    }
    .resumo-valor {
        font-size: 1.8em;
        color: #ffffff;  /* Texto branco */
        font-weight: 700;
    }
    /* Para esconder o elemento da barra de ferramentas nos dataframes */
    [data-testid="stElementToolbar"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

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
        'maior_venda': maior_venda,
        'menor_venda': menor_venda,
        'variacao_faturamento': variacao_faturamento,
        'melhor_dia': melhor_dia
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
            
            # KPIs em cards com CSS personalizado
            st.subheader("📌 Resumo")
            
            # Usando HTML/CSS personalizado para o resumo em duas colunas
            st.markdown(f"""
            <div class="resumo-container">
                <div class="resumo-item">
                    <div class="resumo-titulo">Total de Vendas</div>
                    <div class="resumo-valor">{kpis['total_vendas']}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Faturamento Total</div>
                    <div class="resumo-valor">R$ {kpis['total_faturamento']:,.2f}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Ticket Médio</div>
                    <div class="resumo-valor">R$ {kpis['media_por_venda']:,.2f}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Melhor Dia</div>
                    <div class="resumo-valor">{kpis['melhor_dia'] if kpis['melhor_dia'] else 'N/A'}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Acúmulo de Capital
            st.subheader("💰 Acúmulo de Capital ao Longo do Tempo")
            
            if not df_filtered.empty and 'Data' in df_filtered.columns:
                # Ordenar por data
                df_accumulated = df_filtered.sort_values('Data').copy()
                df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()
                
                # Gráfico de linha
                line_chart = alt.Chart(df_accumulated).mark_line(
                    color='#4285F4',
                    strokeWidth=3
                ).encode(
                    x=alt.X('Data:T', 
                          title='Data',
                          axis=alt.Axis(format='%d/%m/%Y')),
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
                    size=60,
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
            
            # Usando HTML/CSS personalizado para o resumo em duas colunas
            st.markdown(f"""
            <div class="resumo-container">
                <div class="resumo-item">
                    <div class="resumo-titulo">🔢 Total de Vendas</div>
                    <div class="resumo-valor">{kpis['total_vendas']}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">💵 Faturamento Total</div>
                    <div class="resumo-valor">R$ {kpis['total_faturamento']:,.2f}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">📈 Média por Venda</div>
                    <div class="resumo-valor">R$ {kpis['media_por_venda']:,.2f}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">⬆️ Maior Venda</div>
                    <div class="resumo-valor">R$ {kpis['maior_venda']:,.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
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
                    'Valor': [cartao_total, dinheiro_total, pix_total]
                })
                
                # Adicionar porcentagem se o total for maior que zero
                if payment_data['Valor'].sum() > 0:
                    payment_data['Porcentagem'] = payment_data['Valor'] / payment_data['Valor'].sum() * 100

                # Gráfico de pizza simplificado
                pie_chart = alt.Chart(payment_data).mark_arc().encode(
                    theta='Valor:Q',
                    color=alt.Color('Método:N', 
                                  scale=alt.Scale(domain=['Cartão', 'Dinheiro', 'PIX'],
                                                range=['#4285F4', '#34A853', '#FBBC05'])),
                    tooltip=[
                        alt.Tooltip('Método:N', title='Método'),
                        alt.Tooltip('Valor:Q', title='Valor', format='R$ ,.2f'),
                        alt.Tooltip('Porcentagem:Q', title='Porcentagem', format='.1f%')
                    ]
                ).properties(
                    height=300
                )
                
                st.altair_chart(pie_chart, use_container_width=True)
            
            # Histograma de Valores
            st.subheader("📊 Distribuição de Valores")
            
            # Histograma para distribuição de valores
            if not df_filtered.empty:
                # Histograma simples
                histogram = alt.Chart(df_filtered).mark_bar().encode(
                    x=alt.X('Total:Q', bin=True, title='Valor da Venda (R$)'),
                    y='count()',
                    tooltip=['count()']
                ).properties(
                    title='Distribuição dos Valores de Venda',
                    height=300
                )
                
                st.altair_chart(histogram, use_container_width=True)
            
            # Análise por Dia da Semana
            st.subheader("📅 Análise por Dia da Semana")
            if 'DiaSemana' in df_filtered.columns:
                # Dias da semana em português e ordem correta
                dias_ordem = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
                
                # Agrupando por dia da semana
                vendas_por_dia = df_filtered.groupby('DiaSemana', observed=False).agg({
                    'Total': ['sum', 'mean', 'count']
                }).reset_index()
                
                vendas_por_dia.columns = ['DiaSemana', 'Total_Soma', 'Total_Media', 'Total_Contador']
                
                # Garantir que todos os dias estão presentes
                for dia in dias_ordem:
                    if dia not in vendas_por_dia['DiaSemana'].values:
                        vendas_por_dia = pd.concat([vendas_por_dia, pd.DataFrame({
                            'DiaSemana': [dia],
                            'Total_Soma': [0],
                            'Total_Media': [0],
                            'Total_Contador': [0]
                        })], ignore_index=True)
                
                # Ordenar dias da semana
                dias_dict = {dia: i for i, dia in enumerate(dias_ordem)}
                vendas_por_dia['DiaSemanaOrdem'] = vendas_por_dia['DiaSemana'].map(dias_dict)
                vendas_por_dia = vendas_por_dia.sort_values('DiaSemanaOrdem').reset_index(drop=True)
                
                # Gráfico de barras para dia da semana
                bar_chart = alt.Chart(vendas_por_dia).mark_bar().encode(
                    x=alt.X('DiaSemana:N', 
                          title='Dia da Semana', 
                          sort=dias_ordem),
                    y=alt.Y('Total_Soma:Q', 
                          title='Total de Vendas (R$)'),
                    color=alt.Color('DiaSemana:N', 
                                  legend=None),
                    tooltip=[
                        alt.Tooltip('DiaSemana:N', title='Dia'),
                        alt.Tooltip('Total_Soma:Q', title='Total', format='R$ ,.2f'),
                        alt.Tooltip('Total_Media:Q', title='Média', format='R$ ,.2f'),
                        alt.Tooltip('Total_Contador:Q', title='Qtd. Vendas')
                    ]
                ).properties(
                    height=400
                )
                
                # Adicionar linha com a média
                media_geral = vendas_por_dia['Total_Soma'].mean()
                rule = alt.Chart(pd.DataFrame({'media': [media_geral]})).mark_rule(
                    color='red',
                    strokeDash=[4, 4]
                ).encode(
                    y='media:Q'
                )
                
                st.altair_chart(bar_chart + rule, use_container_width=True)
                
                # Destacar melhor e pior dia
                melhor_dia = vendas_por_dia.loc[vendas_por_dia['Total_Soma'].idxmax()]
                pior_dia = vendas_por_dia.loc[vendas_por_dia['Total_Soma'].idxmin()]
                
                best_worst_cols = st.columns(3)
                
                with best_worst_cols[0]:
                    st.metric(
                        "🔝 Melhor Dia da Semana", 
                        f"{melhor_dia['DiaSemana']}",
                        f"R$ {melhor_dia['Total_Soma']:,.2f}"
                    )
                
                with best_worst_cols[1]:
                    st.metric(
                        "📊 Média Diária", 
                        f"R$ {media_geral:,.2f}"
                    )
                
                with best_worst_cols[2]:
                    st.metric(
                        "🔻 Pior Dia da Semana", 
                        f"{pior_dia['DiaSemana']}",
                        f"R$ {pior_dia['Total_Soma']:,.2f}"
                    )
                
                # Mostrar tabela com os dados por dia da semana
                st.markdown("#### Detalhamento por Dia da Semana")
                
                # Formatar tabela
                vendas_por_dia_display = vendas_por_dia[['DiaSemana', 'Total_Soma', 'Total_Media', 'Total_Contador']].copy()
                
                st.dataframe(
                    vendas_por_dia_display,
                    column_config={
                        "DiaSemana": st.column_config.TextColumn("Dia da Semana"),
                        "Total_Soma": st.column_config.NumberColumn("Total (R$)", format="R$ %.2f"),
                        "Total_Media": st.column_config.NumberColumn("Média (R$)", format="R$ %.2f"),
                        "Total_Contador": st.column_config.NumberColumn("Qtd. Vendas")
                    },
                    use_container_width=True,
                    hide_index=True
                )

if __name__ == "__main__":
    main()