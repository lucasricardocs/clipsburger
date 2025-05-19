import streamlit as st
import pandas as pd
import altair as alt
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
st.set_page_config(
    page_title="Sistema de Registro de Vendas", 
    layout="centered",
    initial_sidebar_state="expanded"
)

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
                
                # Adicionar ordem dos dias da semana para garantir ordenação correta
                ordem_dias = {'Segunda': 1, 'Terça': 2, 'Quarta': 3, 'Quinta': 4, 'Sexta': 5, 'Sábado': 6, 'Domingo': 7}
                df['DiaSemanaOrdem'] = df['DiaSemana'].map(ordem_dias)
                
                # Remover domingos
                df = df[df['DiaSemana'] != 'Domingo'].copy()
        except Exception as e:
            st.warning(f"Erro ao processar datas: {e}")
    
    return df

def create_accumulated_chart(df):
    """Cria gráfico de linha para capital acumulado usando Altair"""
    if df.empty or 'Data' not in df.columns:
        return None
    
    # Ordenar por data e calcular acumulado
    df_sorted = df.sort_values('Data').copy()
    df_sorted['Total Acumulado'] = df_sorted['Total'].cumsum()
    
    # Criar gráfico de área para acúmulo de capital
    chart = alt.Chart(df_sorted).mark_area(
        opacity=0.6,
        line=True,
        color="#4285F4"
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
    
    # Adicionar pontos para destacar os valores individuais
    points = alt.Chart(df_sorted).mark_circle(
        size=60,
        color="#1A73E8"
    ).encode(
        x='Data:T',
        y='Total Acumulado:Q'
    )
    
    return chart + points

def create_weekday_chart(df):
    """Cria gráfico de barras por dia da semana usando Altair"""
    if df.empty or 'DiaSemana' not in df.columns:
        return None
    
    # Dias da semana em ordem correta
    dias_ordem = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
    
    # Agrupar por dia da semana
    vendas_por_dia = df.groupby('DiaSemana')['Total'].sum().reset_index()
    
    # Criar gráfico de barras
    chart = alt.Chart(vendas_por_dia).mark_bar(
        cornerRadiusTopLeft=3,
        cornerRadiusTopRight=3
    ).encode(
        x=alt.X('DiaSemana:N', 
               title='Dia da Semana',
               sort=dias_ordem),
        y=alt.Y('Total:Q', 
               title='Faturamento Total (R$)'),
        color=alt.Color('DiaSemana:N', 
                      scale=alt.Scale(scheme='tableau10'),
                      legend=None),
        tooltip=[
            alt.Tooltip('DiaSemana:N', title='Dia'),
            alt.Tooltip('Total:Q', title='Total', format='R$ ,.2f')
        ]
    ).properties(
        height=350
    )
    
    # Adicionar valores no topo das barras
    text = chart.mark_text(
        align='center',
        baseline='bottom',
        dy=-5,
        fontSize=12,
        fontWeight='bold'
    ).encode(
        text=alt.Text('Total:Q', format='R$ ,.0f')
    )
    
    return chart + text

def create_payment_methods_chart(df):
    """Cria gráfico de pizza para métodos de pagamento usando Altair"""
    if df.empty:
        return None
    
    # Calcular total por método de pagamento
    metodo_pagamento = pd.DataFrame({
        'Método': ['Cartão', 'Dinheiro', 'PIX'],
        'Valor': [
            df['Cartão'].sum(),
            df['Dinheiro'].sum(),
            df['Pix'].sum()
        ]
    })
    
    # Calcular porcentagens
    total = metodo_pagamento['Valor'].sum()
    if total > 0:
        metodo_pagamento['Porcentagem'] = (metodo_pagamento['Valor'] / total * 100).round(1)
    else:
        metodo_pagamento['Porcentagem'] = 0
    
    # Definir cores para os métodos
    domain = ['Cartão', 'Dinheiro', 'PIX']
    range_ = ['#4285F4', '#34A853', '#FBBC05']
    
    # Criar gráfico de pizza
    chart = alt.Chart(metodo_pagamento).mark_arc(outerRadius=120).encode(
        theta=alt.Theta(field="Valor", type="quantitative"),
        color=alt.Color('Método:N', scale=alt.Scale(domain=domain, range=range_)),
        tooltip=[
            alt.Tooltip('Método:N', title='Método'),
            alt.Tooltip('Valor:Q', title='Valor', format='R$ ,.2f'),
            alt.Tooltip('Porcentagem:Q', title='Porcentagem', format='.1f%')
        ]
    ).properties(
        height=350
    )
    
    # Adicionar texto de porcentagem
    text = alt.Chart(metodo_pagamento).mark_text(radius=150, size=16).encode(
        theta=alt.Theta(field="Valor", type="quantitative"),
        text=alt.Text('Porcentagem:Q', format='.1f%'),
        color=alt.value('black')
    )
    
    return chart + text

def create_histogram(df):
    """Cria histograma dos valores de venda usando Altair"""
    if df.empty or 'Total' not in df.columns:
        return None
    
    # Calcular estatísticas para destacar no tooltip
    mean = df['Total'].mean()
    median = df['Total'].median()
    
    # Criar histograma
    chart = alt.Chart(df).mark_bar(
        opacity=0.7,
        color='#FBBC05'
    ).encode(
        x=alt.X('Total:Q', 
               bin=alt.Bin(maxbins=20), 
               title='Valor da Venda (R$)'),
        y=alt.Y('count()', 
               title='Frequência'),
        tooltip=[
            alt.Tooltip('count()', title='Quantidade'),
            alt.Tooltip('Total:Q', title='Faixa de Valor', format='R$ ,.2f')
        ]
    ).properties(
        height=350
    )
    
    # Adicionar linha vertical para média
    mean_df = pd.DataFrame({'mean': [mean]})
    mean_line = alt.Chart(mean_df).mark_rule(
        color='red',
        strokeWidth=2,
        strokeDash=[4, 4]
    ).encode(
        x='mean:Q',
        size=alt.value(2),
        tooltip=alt.Tooltip('mean:Q', title='Média', format='R$ ,.2f')
    )
    
    # Adicionar linha vertical para mediana
    median_df = pd.DataFrame({'median': [median]})
    median_line = alt.Chart(median_df).mark_rule(
        color='green',
        strokeWidth=2,
        strokeDash=[4, 4]
    ).encode(
        x='median:Q',
        size=alt.value(2),
        tooltip=alt.Tooltip('median:Q', title='Mediana', format='R$ ,.2f')
    )
    
    return chart + mean_line + median_line

def create_monthly_chart(df):
    """Cria gráfico de evolução mensal usando Altair"""
    if df.empty or 'AnoMês' not in df.columns:
        return None
    
    # Agrupar por mês
    df_monthly = df.groupby('AnoMês').agg({
        'Total': 'sum',
        'Data': 'count'
    }).reset_index()
    
    df_monthly.rename(columns={'Data': 'Quantidade'}, inplace=True)
    
    # Cria linha de tendência
    line = alt.Chart(df_monthly).mark_line(
        point=alt.OverlayMarkDef(filled=True, size=100),
        color='#4285F4',
        strokeWidth=3
    ).encode(
        x=alt.X('AnoMês:N', title='Mês', sort=None),
        y=alt.Y('Total:Q', title='Faturamento Total (R$)'),
        tooltip=[
            alt.Tooltip('AnoMês:N', title='Mês'),
            alt.Tooltip('Total:Q', title='Faturamento', format='R$ ,.2f'),
            alt.Tooltip('Quantidade:Q', title='Quantidade de Vendas')
        ]
    )
    
    # Cria barras para quantidade
    bars = alt.Chart(df_monthly).mark_bar(
        opacity=0.3,
        color='#34A853'
    ).encode(
        x='AnoMês:N',
        y=alt.Y('Quantidade:Q', title='Quantidade de Vendas',
              axis=alt.Axis(titleColor='#34A853'))
    )
    
    # Combina os dois gráficos com escalas independentes
    chart = alt.layer(line, bars).resolve_scale(
        y='independent'
    ).properties(
        height=400
    )
    
    return chart

def main():
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
                        # Limpar cache e recarregar a página
                        st.cache_data.clear()
                        st.experimental_rerun()
                else:
                    st.warning("⚠️ O valor total deve ser maior que zero.")
    
    # Filtros na sidebar
    with st.sidebar:
        st.header("🔍 Filtros")
        
        if not df.empty and 'Data' in df.columns:
            # Obter mês e ano atual
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            # Filtro de Ano
            anos = sorted(df['Ano'].unique(), reverse=True)
            default_anos = [current_year] if current_year in anos else anos[:1] if anos else []
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
            
            # Tabela usando componente nativo do Streamlit
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
                },
                height=300
            )
            
            # Resumo dos dados
            total_vendas = len(df_filtered)
            total_faturamento = df_filtered['Total'].sum()
            media_por_venda = df_filtered['Total'].mean() if total_vendas > 0 else 0
            maior_venda = df_filtered['Total'].max() if total_vendas > 0 else 0
            
            # Melhor dia da semana
            melhor_dia = None
            if 'DiaSemana' in df_filtered.columns and not df_filtered.empty:
                vendas_por_dia = df_filtered.groupby('DiaSemana')['Total'].sum()
                if not vendas_por_dia.empty:
                    melhor_dia = vendas_por_dia.idxmax()
            
            # Exibir métricas em cards usando colunas do Streamlit em vez de CSS personalizado
            st.subheader("📌 Resumo")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de Vendas", f"{total_vendas}")
                st.metric("Ticket Médio", f"R$ {media_por_venda:,.2f}")
            with col2:
                st.metric("Faturamento Total", f"R$ {total_faturamento:,.2f}")
                st.metric("Melhor Dia", f"{melhor_dia if melhor_dia else 'N/A'}")
            
            # Acúmulo de Capital
            st.subheader("💰 Acúmulo de Capital ao Longo do Tempo")
            
            chart = create_accumulated_chart(df_filtered)
            if chart:
                st.altair_chart(chart, use_container_width=True)
    
    # Aba 3: Estatísticas
    with tab3:
        st.header("Estatísticas Avançadas de Vendas")
        
        if df_filtered.empty:
            st.info("Não há dados para exibir com os filtros selecionados.")
        else:
            # Layout em duas colunas para os primeiros gráficos
            col1, col2 = st.columns(2)
            
            with col1:
                # Análise por Dia da Semana
                st.subheader("📅 Vendas por Dia da Semana")
                
                chart = create_weekday_chart(df_filtered)
                if chart:
                    st.altair_chart(chart, use_container_width=True)
            
            with col2:
                # Métodos de Pagamento
                st.subheader("💳 Métodos de Pagamento")
                
                chart = create_payment_methods_chart(df_filtered)
                if chart:
                    st.altair_chart(chart, use_container_width=True)
            
            # Histograma dos valores
            st.subheader("📊 Distribuição dos Valores de Venda")
            
            chart = create_histogram(df_filtered)
            if chart:
                st.altair_chart(chart, use_container_width=True)
                
                # Estatísticas adicionais
                stats_cols = st.columns(4)
                stats_cols[0].metric("Média", f"R$ {df_filtered['Total'].mean():.2f}")
                stats_cols[1].metric("Mediana", f"R$ {df_filtered['Total'].median():.2f}")
                stats_cols[2].metric("Desvio Padrão", f"R$ {df_filtered['Total'].std():.2f}")
                # Correção: Adicionando verificação para evitar divisão por zero
                coef_var = 0
                if df_filtered['Total'].mean() > 0:
                    coef_var = (df_filtered['Total'].std() / df_filtered['Total'].mean() * 100)
                stats_cols[3].metric("Coef. de Variação", f"{coef_var:.1f}%")
            
            # Evolução mensal
            if 'AnoMês' in df_filtered.columns and df_filtered['AnoMês'].nunique() > 1:
                st.subheader("📈 Evolução Mensal de Vendas")
                
                chart = create_monthly_chart(df_filtered)
                if chart:
                    st.altair_chart(chart, use_container_width=True)

if __name__ == "__main__":
    main()
