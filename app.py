import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página com layout wide
st.set_page_config(
    page_title="Sistema de Vendas ClipsBurger",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Minimalista para melhorias sutis e compatibilidade com tema escuro
st.markdown("""

    /* Melhora a aparência dos containers com borda */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[style*="border"] {
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        padding: 15px;
        margin-bottom: 15px;
    }
    /* Ajuste no spinner para ser mais visível em ambos os temas */
    .stSpinner > div {
        border-top-color: #FF4B4B !important;
    }
    /* Ajuste para métricas dentro de containers com borda */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[style*="border"] div[data-testid="stMetric"] {
        background-color: transparent;
        border: none;
        box-shadow: none;
        padding: 0;
    }

""", unsafe_allow_html=True)

# Não use alt.themes.enable() - causa erro

CHART_HEIGHT = 380 # Altura padrão para gráficos grandes

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
        spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
        worksheet_name = st.secrets["google_sheets"]["worksheet_name"]
        try:
            with st.spinner("🔄 Conectando à planilha..."):
                spreadsheet = gc.open_by_key(spreadsheet_id)
                worksheet = spreadsheet.worksheet(worksheet_name)
                rows = worksheet.get_all_records()
                if not rows:
                    st.toast("⚠️ Planilha de vendas está vazia.", icon="📄")
                    return pd.DataFrame(), worksheet
                df = pd.DataFrame(rows)
                st.toast("✅ Dados carregados com sucesso!", icon="📊")
                return df, worksheet
        except SpreadsheetNotFound:
            st.error(f"❌ Planilha com ID {spreadsheet_id} não encontrada.")
            return pd.DataFrame(), None
    except Exception as e:
        st.error(f"❌ Erro de autenticação ou conexão: {e}")
        return pd.DataFrame(), None

def add_data_to_sheet(date_str, cartao, dinheiro, pix, worksheet_obj):
    """Função para adicionar dados à planilha Google Sheets"""
    if worksheet_obj is None:
        st.error("❌ Não foi possível acessar a planilha.")
        return False
    try:
        with st.spinner("⏳ Registrando venda..."):
            new_row = [date_str, float(cartao), float(dinheiro), float(pix)]
            worksheet_obj.append_row(new_row)
            st.toast("✅ Venda registrada com sucesso!", icon="🎉")
            return True
    except Exception as e:
        st.error(f"❌ Erro ao adicionar dados: {e}")
        return False

@st.cache_data(ttl=300)
def process_data(df_raw):
    """Função para processar e preparar os dados"""
    if df_raw is None or df_raw.empty:
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
            df.dropna(subset=['Data'], inplace=True)
            
            if not df.empty:
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['MêsNome'] = df['Data'].dt.strftime('%B').str.capitalize()
                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
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
                df['DiaSemana'] = df['Data'].dt.day_name().map(dias_semana_map)
        except Exception as e:
            st.warning(f"Erro ao processar datas: {e}")
    
    return df

def create_pie_chart_payment_methods(df_data):
    """Cria gráfico de pizza para métodos de pagamento"""
    if df_data is None or df_data.empty:
        return None
    
    payment_sum = df_data[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
    payment_sum.columns = ['Método', 'Valor']
    total_pagamentos = payment_sum['Valor'].sum()
    
    if total_pagamentos == 0:
        return None
        
    payment_sum['Porcentagem'] = (payment_sum['Valor'] / total_pagamentos) * 100

    pie_chart = alt.Chart(payment_sum).mark_arc(innerRadius=70, outerRadius=140).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
        tooltip=[
            alt.Tooltip("Método:N"),
            alt.Tooltip("Valor:Q", format="R$,.2f", title="Valor"),
            alt.Tooltip("Porcentagem:Q", format=".1f", title="% do Total")
        ]
    ).properties(
        height=CHART_HEIGHT, 
        title=alt.TitleParams(text="Distribuição por Método de Pagamento", fontSize=16, dy=-10, anchor='middle')
    )
    
    text_values = pie_chart.mark_text(radius=105, size=14, fontWeight='bold').encode(
        text=alt.Text("Porcentagem:Q", format=".0f") + "%"
    )
    
    return pie_chart + text_values

def create_daily_sales_bar_chart(df_data):
    """Cria gráfico de barras para vendas diárias"""
    if df_data is None or df_data.empty or 'DataFormatada' not in df_data.columns:
        return None
    
    daily_data_melted = df_data.melt(
        id_vars=['DataFormatada', 'Data'],
        value_vars=['Cartão', 'Dinheiro', 'Pix'],
        var_name='Método',
        value_name='Valor'
    )
    
    daily_data_melted = daily_data_melted[daily_data_melted['Valor'] > 0]
    
    if daily_data_melted.empty:
        return None

    bar_chart = alt.Chart(daily_data_melted).mark_bar().encode(
        x=alt.X('DataFormatada:N', title='Data', 
                sort=alt.EncodingSortField(field="Data", op="min", order='ascending'),
                axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Valor:Q', title='Valor (R$)', stack='zero'),
        color=alt.Color('Método:N', legend=alt.Legend(title="Método")),
        tooltip=[
            alt.Tooltip('DataFormatada:N', title="Data"),
            alt.Tooltip('Método:N'),
            alt.Tooltip('Valor:Q', format='R$,.2f', title="Valor do Segmento")
        ]
    ).properties(
        height=CHART_HEIGHT, 
        title=alt.TitleParams(text="Vendas Diárias por Método", fontSize=16, dy=-10, anchor='middle')
    )
    
    return bar_chart

def create_accumulated_capital_line_chart(df_data):
    """Cria gráfico de linha para capital acumulado"""
    if df_data is None or df_data.empty or 'Data' not in df_data.columns or 'Total' not in df_data.columns:
        return None
    
    df_accumulated = df_data.sort_values('Data').copy()
    
    if df_accumulated.empty:
        return None
        
    df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()

    line_chart = alt.Chart(df_accumulated).mark_area(
        line={'color':'steelblue', 'strokeWidth': 2},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='rgba(70, 130, 180, 0.1)', offset=0.3), 
                   alt.GradientStop(color='rgba(70, 130, 180, 0.7)', offset=1)],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X('Data:T', title='Data', axis=alt.Axis(format="%d/%m/%y", labelAngle=-45)),
        y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
        tooltip=[
            alt.Tooltip('Data:T', format='%d/%m/%Y', title="Data"),
            alt.Tooltip('Total Acumulado:Q', format='R$,.2f', title="Acumulado"),
            alt.Tooltip('Total:Q', format='R$,.2f', title="Venda Dia")
        ]
    ).properties(
        height=CHART_HEIGHT, 
        title=alt.TitleParams(text="Crescimento do Capital Acumulado", fontSize=16, dy=-10, anchor='middle')
    )
    
    return line_chart

def create_avg_sales_by_weekday_bar_chart(df_data):
    """Cria gráfico de barras para média de vendas por dia da semana"""
    if df_data is None or df_data.empty or 'DiaSemana' not in df_data.columns:
        return None
    
    dias_funcionamento = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
    df_data_funcionamento = df_data[df_data['DiaSemana'].isin(dias_funcionamento)]
    
    if df_data_funcionamento.empty:
        return None
    
    vendas_media_dia_semana = df_data_funcionamento.groupby(['DiaSemanaNum', 'DiaSemana'])['Total'].mean().reset_index()
    
    ordem_dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']

    bar_chart = alt.Chart(vendas_media_dia_semana).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X('DiaSemana:N', title='Dia da Semana', sort=ordem_dias),
        y=alt.Y('Total:Q', title='Média de Vendas (R$)'),
        color=alt.Color('DiaSemana:N', legend=None),
        tooltip=[alt.Tooltip('DiaSemana:N', title="Dia"), alt.Tooltip('Total:Q', format='R$,.2f', title="Média")]
    ).properties(
        height=CHART_HEIGHT, 
        title=alt.TitleParams(text="Média de Vendas por Dia da Semana (Seg-Sáb)", fontSize=16, dy=-10, anchor='middle')
    )
    
    text_on_bars = bar_chart.mark_text(dy=-10).encode(
        text=alt.Text('Total:Q', format="R$,.0f")
    )
    
    return bar_chart + text_on_bars

def create_monthly_trend_line_chart(df_data):
    """Cria gráfico de linha para tendência mensal"""
    if df_data is None or df_data.empty or 'AnoMês' not in df_data.columns or df_data['AnoMês'].nunique() Total: R$ {total_venda_calculado:,.2f}", unsafe_allow_html=True)

                submitted = st.form_submit_button("💾 Registrar Venda", use_container_width=True, type="primary")
                if submitted:
                    if total_venda_calculado > 0:
                        formatted_date = data_venda.strftime('%d/%m/%Y')
                        if add_data_to_sheet(formatted_date, cartao, dinheiro, pix, worksheet_obj):
                            st.cache_data.clear()
                            st.rerun()
                    else:
                        st.warning("⚠️ O total da venda deve ser maior que zero.")

    # Filtros na Sidebar
    df_filtrado_sidebar = pd.DataFrame()
    if not df_processed.empty and 'Ano' in df_processed.columns:
        df_filtrado_sidebar = df_processed.copy()  # Começa com todos os dados
        
        with st.sidebar:
            st.header("🔍 Filtros")
            
            # Filtro de Ano
            anos_disponiveis = sorted(df_processed['Ano'].unique(), reverse=True)
            current_year = datetime.now().year
            default_anos = [current_year] if current_year in anos_disponiveis else anos_disponiveis[:1]
            selected_anos = st.multiselect("Ano(s):", anos_disponiveis, default=default_anos)
            
            # Aplicar filtro de ano
            if selected_anos:
                df_filtrado_sidebar = df_filtrado_sidebar[df_filtrado_sidebar['Ano'].isin(selected_anos)]
                
                # Filtro de Mês (apenas se anos forem selecionados)
                if not df_filtrado_sidebar.empty:
                    meses_disponiveis = sorted(df_filtrado_sidebar['Mês'].unique())
                    meses_nomes = {m: datetime(2000, m, 1).strftime('%B').capitalize() for m in meses_disponiveis}
                    
                    # Por padrão, selecionar o mês atual ou todos
                    current_month = datetime.now().month
                    default_meses = [current_month] if current_month in meses_disponiveis else meses_disponiveis
                    
                    selected_meses = st.multiselect(
                        "Mês(es):",
                        options=meses_disponiveis,
                        format_func=lambda m: meses_nomes.get(m, str(m)),
                        default=default_meses
                    )
                    
                    # Aplicar filtro de mês
                    if selected_meses:
                        df_filtrado_sidebar = df_filtrado_sidebar[df_filtrado_sidebar['Mês'].isin(selected_meses)]
    else:
        with st.sidebar:
            st.header("🔍 Filtros")
            st.info("Sem dados disponíveis para filtrar.")

    with tab_analise:
        st.header("Análise Detalhada das Vendas")
        if df_filtrado_sidebar.empty:
            st.info("ℹ️ Sem dados para exibir com os filtros atuais ou a planilha está vazia.")
        else:
            with st.container(border=True):
                st.subheader("📋 Tabela de Vendas Filtradas")
                st.dataframe(
                    df_filtrado_sidebar[['DataFormatada', 'DiaSemana', 'Cartão', 'Dinheiro', 'Pix', 'Total']],
                    use_container_width=True, height=350, hide_index=True,
                    column_config={
                        "DataFormatada": "Data", "DiaSemana": "Dia",
                        "Cartão": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Dinheiro": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Pix": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Total": st.column_config.NumberColumn(format="R$ %.2f")
                    }
                )

            charts_col1, charts_col2 = st.columns(2)
            with charts_col1:
                with st.container(border=True):
                    chart_pie_payment = create_pie_chart_payment_methods(df_filtrado_sidebar)
                    if chart_pie_payment: 
                        st.altair_chart(chart_pie_payment, use_container_width=True, theme="streamlit")
                    else: 
                        st.caption("Sem dados para o gráfico de métodos de pagamento.")
                with st.container(border=True):
                    chart_accum_capital = create_accumulated_capital_line_chart(df_filtrado_sidebar)
                    if chart_accum_capital: 
                        st.altair_chart(chart_accum_capital, use_container_width=True, theme="streamlit")
                    else: 
                        st.caption("Sem dados para o gráfico de capital acumulado.")
            with charts_col2:
                with st.container(border=True):
                    chart_daily_sales = create_daily_sales_bar_chart(df_filtrado_sidebar)
                    if chart_daily_sales: 
                        st.altair_chart(chart_daily_sales, use_container_width=True, theme="streamlit")
                    else: 
                        st.caption("Sem dados para o gráfico de vendas diárias.")

    with tab_estatisticas:
        st.header("Estatísticas Chave e Tendências")
        if df_filtrado_sidebar.empty:
            st.info("ℹ️ Sem dados para exibir com os filtros atuais ou a planilha está vazia.")
        else:
            with st.container(border=True):
                st.subheader("🚀 Resumo Financeiro do Período")
                total_vendas_f = len(df_filtrado_sidebar)
                total_faturamento_f = df_filtrado_sidebar['Total'].sum()
                ticket_medio_f = total_faturamento_f / total_vendas_f if total_vendas_f > 0 else 0
                maior_venda_f = df_filtrado_sidebar['Total'].max() if total_vendas_f > 0 else 0

                col_resumo1, col_resumo2 = st.columns(2)
                with col_resumo1:
                    with st.container(border=True):
                        st.metric(label="💰 Faturamento Total", value=f"R$ {total_faturamento_f:,.2f}")
                    with st.container(border=True):
                        st.metric(label="💸 Ticket Médio", value=f"R$ {ticket_medio_f:,.2f}")
                with col_resumo2:
                    with st.container(border=True):
                        st.metric(label="📈 Total de Vendas", value=f"{total_vendas_f:,} vendas")
                    with st.container(border=True):
                        st.metric(label="⭐ Maior Venda Única", value=f"R$ {maior_venda_f:,.2f}")

            stats_c1, stats_c2 = st.columns(2)
            with stats_c1:
                with st.container(border=True):
                    chart_avg_weekday = create_avg_sales_by_weekday_bar_chart(df_filtrado_sidebar)
                    if chart_avg_weekday: 
                        st.altair_chart(chart_avg_weekday, use_container_width=True, theme="streamlit")
                    else: 
                        st.caption("Sem dados para média por dia da semana.")
                with st.container(border=True):
                    chart_sales_hist = create_sales_value_histogram(df_filtrado_sidebar)
                    if chart_sales_hist: 
                        st.altair_chart(chart_sales_hist, use_container_width=True, theme="streamlit")
                    else: 
                        st.caption("Sem dados para histograma de valores.")
            with stats_c2:
                with st.container(border=True):
                    chart_monthly_trend = create_monthly_trend_line_chart(df_filtrado_sidebar)
                    if chart_monthly_trend: 
                        st.altair_chart(chart_monthly_trend, use_container_width=True, theme="streamlit")
                    else: 
                        st.caption("Sem dados para tendência mensal (>1 mês).")
                with st.container(border=True):
                    chart_weekly_seas = create_weekly_seasonality_bar_chart(df_filtrado_sidebar)
                    if chart_weekly_seas: 
                        st.altair_chart(chart_weekly_seas, use_container_width=True, theme="streamlit")
                    else: 
                        st.caption("Sem dados para sazonalidade semanal (>6 dias).")

            with st.expander("💡 Mais Insights e Projeções (Simplificado)", expanded=False):
                if not df_filtrado_sidebar.empty and 'Data' in df_filtrado_sidebar.columns:
                    dias_distintos = df_filtrado_sidebar['Data'].nunique()
                    if dias_distintos > 0:
                        media_diaria_faturamento = total_faturamento_f / dias_distintos
                        st.markdown(f"**Média Diária de Faturamento (no período):** R$ {media_diaria_faturamento:,.2f} (baseado em {dias_distintos} dias com vendas)")
                        projecao_30_dias = media_diaria_faturamento * 30
                        st.markdown(f"**Projeção Simples para 30 dias:** R$ {projecao_30_dias:,.2f} (se o ritmo atual se mantiver)")
                    else:
                        st.caption("Não há dias distintos com vendas no período selecionado para calcular a média diária.")
                else:
                    st.caption("Sem dados para insights adicionais.")

if __name__ == "__main__":
    main()
