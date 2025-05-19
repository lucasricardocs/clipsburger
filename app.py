import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
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
                df['DiaSemanaNum'] = df['Data'].dt.dayofweek
                df['Semana'] = df['Data'].dt.isocalendar().week
                
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
        except Exception as e:
            st.warning(f"Erro ao processar datas: {e}")
    
    return df

def calculate_statistics(df):
    """Função para calcular estatísticas avançadas dos dados"""
    stats = {}
    
    if df.empty:
        return stats
    
    # Estatísticas básicas
    stats['total_vendas'] = len(df)
    stats['total_faturamento'] = df['Total'].sum()
    stats['media_por_venda'] = df['Total'].mean()
    stats['mediana_por_venda'] = df['Total'].median()
    stats['maior_venda'] = df['Total'].max()
    stats['menor_venda'] = df['Total'].min()
    stats['desvio_padrao'] = df['Total'].std()
    
    # Melhor dia da semana
    if 'DiaSemana' in df.columns:
        vendas_por_dia = df.groupby('DiaSemana')['Total'].agg(['sum', 'count', 'mean'])
        stats['melhor_dia_valor'] = vendas_por_dia['sum'].idxmax()
        stats['melhor_dia_quant'] = vendas_por_dia['count'].idxmax()
        stats['melhor_dia_media'] = vendas_por_dia['mean'].idxmax()
    
    # Tendências (últimos 30 dias vs 30 dias anteriores)
    if 'Data' in df.columns:
        hoje = datetime.now()
        ultimo_mes = df[df['Data'] >= (hoje - timedelta(days=30))]
        mes_anterior = df[(df['Data'] < (hoje - timedelta(days=30))) & 
                          (df['Data'] >= (hoje - timedelta(days=60)))]
        
        if not ultimo_mes.empty and not mes_anterior.empty:
            faturamento_ultimo = ultimo_mes['Total'].sum()
            faturamento_anterior = mes_anterior['Total'].sum()
            
            if faturamento_anterior > 0:
                stats['tendencia_faturamento'] = ((faturamento_ultimo - faturamento_anterior) / 
                                                 faturamento_anterior) * 100
            else:
                stats['tendencia_faturamento'] = 100
    
    # Taxa de crescimento mensal
    if 'AnoMês' in df.columns:
        vendas_mensais = df.groupby('AnoMês')['Total'].sum().reset_index()
        if len(vendas_mensais) >= 2:
            ultimo_mes = vendas_mensais['Total'].iloc[-1]
            penultimo_mes = vendas_mensais['Total'].iloc[-2]
            
            if penultimo_mes > 0:
                stats['taxa_crescimento_mensal'] = ((ultimo_mes - penultimo_mes) / penultimo_mes) * 100
    
    # Distribuição por método de pagamento
    pagamentos_total = df[['Cartão', 'Dinheiro', 'Pix']].sum()
    total_pagamentos = pagamentos_total.sum()
    
    if total_pagamentos > 0:
        stats['perc_cartao'] = (pagamentos_total['Cartão'] / total_pagamentos) * 100
        stats['perc_dinheiro'] = (pagamentos_total['Dinheiro'] / total_pagamentos) * 100
        stats['perc_pix'] = (pagamentos_total['Pix'] / total_pagamentos) * 100
    
    # Sazonalidade semanal
    if 'Semana' in df.columns and 'Ano' in df.columns:
        vendas_semanais = df.groupby(['Ano', 'Semana'])['Total'].sum().reset_index()
        stats['media_semanal'] = vendas_semanais['Total'].mean()
        stats['mediana_semanal'] = vendas_semanais['Total'].median()
    
    return stats

def main():
    st.title("📊 Sistema de Registro de Vendas")
    
    df_raw, worksheet = read_google_sheet()
    df = process_data(df_raw)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Registrar", "📈 Análise", "📊 Estatísticas", "🔍 Insights"])
    
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
            anos = sorted(df['Ano'].unique(), reverse=True)
            selected_anos = st.multiselect("Selecione o(s) Ano(s):", options=anos, default=anos[:1])
            
            meses_disponiveis = sorted(df[df['Ano'].isin(selected_anos)]['Mês'].unique()) if selected_anos else []
            meses_opcoes = [f"{m:02d} - {datetime(2020, m, 1).strftime('%B')}" for m in meses_disponiveis]
            selected_meses_str = st.multiselect("Selecione o(s) Mês(es):", options=meses_opcoes, default=meses_opcoes)
            selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]
            
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
            # Tabela de dados filtrados
            st.subheader("🧾 Dados Filtrados")
            st.dataframe(
                df_filtered[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total', 'DiaSemana']], 
                height=300,
                use_container_width=True
            )
            
            # Estatísticas calculadas
            stats = calculate_statistics(df_filtered)
            st.subheader("📌 Resumo")
            
            st.markdown(f"""
            <div class="resumo-container">
                <div class="resumo-item">
                    <div class="resumo-titulo">Total de Vendas</div>
                    <div class="resumo-valor">{stats.get('total_vendas', 'N/A')}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Faturamento Total</div>
                    <div class="resumo-valor">R$ {stats.get('total_faturamento', 0):,.2f}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Ticket Médio</div>
                    <div class="resumo-valor">R$ {stats.get('media_por_venda', 0):,.2f}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Melhor Dia (Valor)</div>
                    <div class="resumo-valor">{stats.get('melhor_dia_valor', 'N/A')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Acúmulo de Capital
            st.subheader("💰 Evolução do Faturamento")
            
            try:
                df_accumulated = df_filtered.sort_values('Data').copy()
                df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()
                
                chart = alt.Chart(df_accumulated).mark_line().encode(
                    x='Data:T',
                    y='Total Acumulado:Q',
                    tooltip=['DataFormatada:N', alt.Tooltip('Total Acumulado:Q', format='$,.2f')]
                ).properties(height=400)
                
                st.altair_chart(chart, use_container_width=True)
            except Exception as e:
                st.error(f"Erro no gráfico: {e}")
                st.dataframe(df_accumulated[['DataFormatada', 'Total Acumulado']])
    
    # Aba 3: Estatísticas
    with tab3:
        st.header("Estatísticas Avançadas de Vendas")
        
        if df_filtered.empty:
            st.info("Não há dados para exibir com os filtros selecionados.")
        else:
            # Distribuição por Dia da Semana
            st.subheader("📅 Desempenho por Dia da Semana")
            
            try:
                # Dias da semana (sem domingo)
                dias_ordem = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
                
                vendas_por_dia = df_filtered.groupby('DiaSemana').agg(
                    Total_Valor=('Total', 'sum'),
                    Média_Venda=('Total', 'mean'),
                    Quantidade=('Total', 'count')
                ).reset_index()
                
                # Ordenar pela ordem dos dias
                ordem_dias = {dia: i for i, dia in enumerate(dias_ordem)}
                vendas_por_dia['Ordem'] = vendas_por_dia['DiaSemana'].map(ordem_dias)
                vendas_por_dia = vendas_por_dia.sort_values('Ordem').drop('Ordem', axis=1)
                
                # Gráficos por dia da semana
                col1, col2 = st.columns(2)
                
                with col1:
                    chart1 = alt.Chart(vendas_por_dia).mark_bar().encode(
                        x=alt.X('DiaSemana:N', sort=dias_ordem, title='Dia da Semana'),
                        y=alt.Y('Total_Valor:Q', title='Total Vendido (R$)'),
                        color=alt.Color('DiaSemana:N', legend=None),
                        tooltip=[
                            alt.Tooltip('DiaSemana:N', title='Dia'),
                            alt.Tooltip('Total_Valor:Q', title='Total', format='R$ ,.2f'),
                            alt.Tooltip('Quantidade:Q', title='Quantidade')
                        ]
                    ).properties(height=300, title="Faturamento por Dia")
                    st.altair_chart(chart1, use_container_width=True)
                
                with col2:
                    chart2 = alt.Chart(vendas_por_dia).mark_bar().encode(
                        x=alt.X('DiaSemana:N', sort=dias_ordem, title='Dia da Semana'),
                        y=alt.Y('Média_Venda:Q', title='Média por Venda (R$)'),
                        color=alt.Color('DiaSemana:N', legend=None),
                        tooltip=[
                            alt.Tooltip('DiaSemana:N', title='Dia'),
                            alt.Tooltip('Média_Venda:Q', title='Média', format='R$ ,.2f')
                        ]
                    ).properties(height=300, title="Ticket Médio por Dia")
                    st.altair_chart(chart2, use_container_width=True)
                
                # Tabela de dias da semana
                st.dataframe(
                    vendas_por_dia,
                    column_config={
                        "DiaSemana": st.column_config.TextColumn("Dia"),
                        "Total_Valor": st.column_config.NumberColumn("Faturamento", format="R$ %.2f"),
                        "Média_Venda": st.column_config.NumberColumn("Ticket Médio", format="R$ %.2f"),
                        "Quantidade": st.column_config.NumberColumn("Qtd. Vendas")
                    },
                    use_container_width=True,
                    hide_index=True
                )
            except Exception as e:
                st.error(f"Erro ao gerar análise por dia da semana: {e}")
            
            # Distribuição dos Métodos de Pagamento
            st.subheader("💳 Distribuição por Método de Pagamento")
            
            try:
                metodos = pd.DataFrame({
                    'Método': ['Cartão', 'Dinheiro', 'PIX'],
                    'Valor': [
                        df_filtered['Cartão'].sum(),
                        df_filtered['Dinheiro'].sum(),
                        df_filtered['Pix'].sum()
                    ]
                })
                
                metodos['Porcentagem'] = metodos['Valor'] / metodos['Valor'].sum() * 100
                
                col1, col2 = st.columns(2)
                
                with col1:
                    chart_pie = alt.Chart(metodos).mark_arc().encode(
                        theta=alt.Theta('Valor:Q'),
                        color=alt.Color('Método:N'),
                        tooltip=[
                            alt.Tooltip('Método:N'),
                            alt.Tooltip('Valor:Q', format='R$ ,.2f'),
                            alt.Tooltip('Porcentagem:Q', format='.1f%')
                        ]
                    ).properties(height=300, title="Distribuição de Pagamentos")
                    st.altair_chart(chart_pie, use_container_width=True)
                
                with col2:
                    st.dataframe(
                        metodos,
                        column_config={
                            "Método": st.column_config.TextColumn("Método"),
                            "Valor": st.column_config.NumberColumn("Total", format="R$ %.2f"),
                            "Porcentagem": st.column_config.NumberColumn("% do Total", format="%.1f%%")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
            except Exception as e:
                st.error(f"Erro ao gerar análise de métodos de pagamento: {e}")
            
            # Histograma das Vendas
            st.subheader("📊 Distribuição dos Valores de Venda")
            
            try:
                # Criar histograma interativo
                hist = alt.Chart(df_filtered).mark_bar().encode(
                    x=alt.X('Total:Q', bin=alt.Bin(maxbins=20), title='Valor da Venda (R$)'),
                    y='count()',
                    tooltip=['count()', alt.Tooltip('Total:Q', title='Valor', format='R$ ,.2f')]
                ).properties(height=300)
                
                st.altair_chart(hist, use_container_width=True)
                
                # Estatísticas da distribuição
                col1, col2, col3 = st.columns(3)
                col1.metric("Média", f"R$ {df_filtered['Total'].mean():.2f}")
                col2.metric("Mediana", f"R$ {df_filtered['Total'].median():.2f}")
                col3.metric("Desvio Padrão", f"R$ {df_filtered['Total'].std():.2f}")
            except Exception as e:
                st.error(f"Erro ao gerar histograma: {e}")
    
    # Aba 4: Insights
    with tab4:
        st.header("🔍 Insights de Vendas")
        
        if df_filtered.empty:
            st.info("Não há dados para gerar insights.")
        else:
            stats = calculate_statistics(df_filtered)
            
            # Evolução Mensal
            st.subheader("📈 Evolução Mensal de Vendas")
            
            try:
                if 'AnoMês' in df_filtered.columns:
                    vendas_mensais = df_filtered.groupby('AnoMês').agg(
                        Valor=('Total', 'sum'),
                        Quantidade=('Total', 'count'),
                        Média=('Total', 'mean')
                    ).reset_index()
                    
                    chart = alt.Chart(vendas_mensais).mark_line(
                        point=True
                    ).encode(
                        x=alt.X('AnoMês:N', title='Mês', sort=None),
                        y=alt.Y('Valor:Q', title='Total de Vendas (R$)'),
                        tooltip=[
                            alt.Tooltip('AnoMês:N', title='Mês'),
                            alt.Tooltip('Valor:Q', title='Valor', format='R$ ,.2f'),
                            alt.Tooltip('Quantidade:Q', title='Qtd. Vendas'),
                            alt.Tooltip('Média:Q', title='Média', format='R$ ,.2f')
                        ]
                    ).properties(height=400)
                    
                    # Adicionar barras para quantidade
                    bars = alt.Chart(vendas_mensais).mark_bar(opacity=0.3).encode(
                        x='AnoMês:N',
                        y='Quantidade:Q'
                    )
                    
                    # Plotar o gráfico combinado
                    st.altair_chart(chart + bars, use_container_width=True)
                    
                    # Calcular taxa de crescimento
                    if len(vendas_mensais) >= 2:
                        vendas_mensais['Crescimento'] = vendas_mensais['Valor'].pct_change() * 100
                        
                        # Tabela com crescimento
                        st.dataframe(
                            vendas_mensais,
                            column_config={
                                "AnoMês": st.column_config.TextColumn("Mês"),
                                "Valor": st.column_config.NumberColumn("Faturamento", format="R$ %.2f"),
                                "Quantidade": st.column_config.NumberColumn("Vendas"),
                                "Média": st.column_config.NumberColumn("Ticket Médio", format="R$ %.2f"),
                                "Crescimento": st.column_config.NumberColumn("Crescimento", format="%+.1f%%")
                            },
                            use_container_width=True,
                            hide_index=True
                        )
            except Exception as e:
                st.error(f"Erro ao gerar evolução mensal: {e}")
            
            # Análise de Correlação
            st.subheader("🔄 Correlações entre Variáveis")
            
            try:
                # Preparar dados para correlação
                corr_data = df_filtered[['Total', 'DiaSemanaNum', 'Mês']].copy()
                
                # Adicionar valor médio do dia da semana para comparação
                dias_media = df_filtered.groupby('DiaSemanaNum')['Total'].mean().reset_index()
                dias_media.columns = ['DiaSemanaNum', 'MediaDiaSemana']
                corr_data = pd.merge(corr_data, dias_media, on='DiaSemanaNum')
                
                # Calcular correlações
                correlations = corr_data.corr()
                
                # Exibir correlações em formato de mapa de calor
                corr_df = pd.DataFrame({
                    'Variável 1': ['Valor da Venda', 'Valor da Venda', 'Dia da Semana'],
                    'Variável 2': ['Dia da Semana', 'Mês', 'Mês'],
                    'Correlação': [
                        correlations.loc['Total', 'DiaSemanaNum'],
                        correlations.loc['Total', 'Mês'],
                        correlations.loc['DiaSemanaNum', 'Mês']
                    ]
                })
                
                # Exibir tabela de correlações
                st.dataframe(
                    corr_df,
                    column_config={
                        "Variável 1": st.column_config.TextColumn("Variável 1"),
                        "Variável 2": st.column_config.TextColumn("Variável 2"),
                        "Correlação": st.column_config.NumberColumn("Correlação", format="%.3f")
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Interpretação das correlações
                st.write("**Interpretação:**")
                st.write("- Correlação próxima a 1: forte relação positiva")
                st.write("- Correlação próxima a -1: forte relação negativa")
                st.write("- Correlação próxima a 0: pouca ou nenhuma relação")
                
                # Boxplot de vendas por dia da semana
                st.subheader("📦 Dispersão dos Valores por Dia da Semana")
                
                box = alt.Chart(df_filtered).mark_boxplot().encode(
                    x=alt.X('DiaSemana:N', title='Dia da Semana', sort=dias_ordem),
                    y=alt.Y('Total:Q', title='Valor da Venda (R$)'),
                    color='DiaSemana:N'
                ).properties(height=400)
                
                st.altair_chart(box, use_container_width=True)
            
            except Exception as e:
                st.error(f"Erro ao gerar análise de correlações: {e}")
            
            # Previsões baseadas em tendências
            st.subheader("🔮 Projeções")
            
            try:
                if 'Data' in df_filtered.columns and len(df_filtered) >= 10:
                    # Calcula a média diária dos últimos dados
                    media_diaria = df_filtered['Total'].mean()
                    
                    col1, col2, col3 = st.columns(3)
                    
                    # Projeção para o próximo mês (22 dias úteis)
                    projecao_mes = media_diaria * 22
                    col1.metric("Projeção Mensal", f"R$ {projecao_mes:.2f}")
                    
                    # Projeção para próxima semana (6 dias úteis)
                    projecao_semana = media_diaria * 6
                    col2.metric("Projeção Semanal", f"R$ {projecao_semana:.2f}")
                    
                    # Meta sugerida (15% acima da média)
                    meta_sugerida = projecao_mes * 1.15
                    col3.metric("Meta Sugerida", f"R$ {meta_sugerida:.2f}", "+15%")
                    
                    # Taxa de crescimento se disponível
                    if 'taxa_crescimento_mensal' in stats:
                        st.metric("Taxa de Crescimento Mensal", 
                                f"{stats['taxa_crescimento_mensal']:+.1f}%")
                
            except Exception as e:
                st.error(f"Erro ao gerar projeções: {e}")

if __name__ == "__main__":
    main()