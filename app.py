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
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Sistema de Análise de Vendas para ClipsBurger."
    }
)

# CSS Minimalista para melhorias sutis e compatibilidade com tema escuro
st.markdown("""
<style>
    /* Melhora a aparência dos containers com borda */
    div[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > div[style*="border"] {
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); /* Sombra sutil */
        padding: 15px; /* Adiciona um pouco de padding interno */
        margin-bottom: 15px; /* Espaço entre containers */
    }
    /* Títulos principais */
    h1 {
        color: #FF4B4B; /* Cor primária do Streamlit (pode ajustar) */
    }
    /* Ajuste no spinner para ser mais visível em ambos os temas */
    .stSpinner > div {
        border-top-color: #FF4B4B !important; /* Cor do spinner */
    }
    /* Ajuste para métricas dentro de containers */
    div[data-testid="stMetric"] {
        background-color: transparent; /* Remove fundo padrão da métrica se estiver dentro de um container estilizado */
        border: none;
        box-shadow: none;
        padding: 0;
    }
</style>
""", unsafe_allow_html=True)

# Habilitar tema para gráficos Altair que funciona bem em ambos os modos
alt.themes.enable('vox') # Vox geralmente se adapta bem a fundos escuros

CHART_HEIGHT = 400 # Altura padrão para gráficos grandes

# --- Funções de Suporte ---
@st.cache_data(ttl=300)  # Cache por 5 minutos
def read_google_sheet():
    """Função para ler os dados da planilha Google Sheets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
                 'https://www.googleapis.com/auth/spreadsheets.readonly',
                 'https://www.googleapis.com/auth/drive.readonly']
        # Carregar credenciais dos segredos do Streamlit
        credentials_dict = {
            "type": st.secrets["google_credentials"]["type"],
            "project_id": st.secrets["google_credentials"]["project_id"],
            "private_key_id": st.secrets["google_credentials"]["private_key_id"],
            "private_key": st.secrets["google_credentials"]["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["google_credentials"]["client_email"],
            "client_id": st.secrets["google_credentials"]["client_id"],
            "auth_uri": st.secrets["google_credentials"]["auth_uri"],
            "token_uri": st.secrets["google_credentials"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["google_credentials"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["google_credentials"]["client_x509_cert_url"]
        }
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
        worksheet_name = st.secrets["google_sheets"]["worksheet_name"]

        with st.spinner("🔄 Conectando à planilha e carregando dados..."):
            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            rows = worksheet.get_all_records()
            if not rows:
                st.toast("⚠️ Planilha de vendas está vazia.", icon="📄")
                return pd.DataFrame(), worksheet
            df = pd.DataFrame(rows)
            st.toast("✔️ Dados carregados da planilha!", icon="📊")
            return df, worksheet
    except SpreadsheetNotFound:
        st.error(f"❌ Planilha com ID fornecido não encontrada. Verifique o ID e as permissões.")
        return pd.DataFrame(), None
    except KeyError as e:
        st.error(f"❌ Erro ao carregar segredos: {e}. Verifique seu arquivo secrets.toml.")
        return pd.DataFrame(), None
    except Exception as e:
        st.error(f"❌ Erro de autenticação ou conexão com Google Sheets: {e}")
        return pd.DataFrame(), None

def add_data_to_sheet(date_str, cartao, dinheiro, pix, worksheet_obj):
    """Função para adicionar dados à planilha Google Sheets"""
    if worksheet_obj is None:
        st.error("❌ Não foi possível acessar a planilha para registrar a venda.")
        return False
    try:
        with st.spinner("⏳ Registrando venda na planilha..."):
            new_row = [date_str, float(cartao), float(dinheiro), float(pix)]
            worksheet_obj.append_row(new_row)
            st.toast("✅ Venda registrada com sucesso!", icon="🎉")
            return True
    except Exception as e:
        st.error(f"❌ Erro ao adicionar dados na planilha: {e}")
        return False

@st.cache_data(ttl=300)
def process_data(df_raw):
    """Função para processar e preparar os dados"""
    if df_raw.empty:
        return pd.DataFrame()
    df = df_raw.copy()
    for col in ['Cartão', 'Dinheiro', 'Pix']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']

    if 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        df.dropna(subset=['Data'], inplace=True) # Remove linhas onde a data não pôde ser convertida
        if not df.empty:
            df['Ano'] = df['Data'].dt.year
            df['Mês'] = df['Data'].dt.month
            df['MêsNome'] = df['Data'].dt.strftime('%B').str.capitalize()
            df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
            df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
            df['DiaSemanaNum'] = df['Data'].dt.dayofweek # Segunda=0 ... Sábado=5, Domingo=6
            df['DiaSemanaNome'] = df['Data'].dt.day_name().map({
                'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
                'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            })
    return df

# --- Funções de Gráficos ---
def create_pie_chart_payment_methods(df_data):
    if df_data.empty or not all(col in df_data.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
        return None
    payment_sum = df_data[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
    payment_sum.columns = ['Método', 'Valor']
    total_pagamentos = payment_sum['Valor'].sum()
    if total_pagamentos == 0: return None
    payment_sum['Porcentagem'] = (payment_sum['Valor'] / total_pagamentos) * 100

    pie_chart = alt.Chart(payment_sum).mark_arc(innerRadius=70, outerRadius=140).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        color=alt.Color("Método:N", legend=alt.Legend(title="Método"), scale=alt.Scale(scheme='tableau10')),
        tooltip=[
            alt.Tooltip("Método:N"),
            alt.Tooltip("Valor:Q", format="R$,.2f", title="Valor"),
            alt.Tooltip("Porcentagem:Q", format=".1f", title="% do Total")
        ]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams(text="Distribuição por Método de Pagamento", fontSize=16, dy=-10, anchor='middle'))

    text_values = pie_chart.mark_text(radius=105, size=14, fontWeight='bold').encode(
        text=alt.Text("Porcentagem:Q", format=".0f") + "%"
    )
    return pie_chart + text_values

def create_daily_sales_bar_chart(df_data):
    if df_data.empty or 'DataFormatada' not in df_data.columns: return None
    daily_data_melted = df_data.melt(
        id_vars=['DataFormatada', 'Data'],
        value_vars=['Cartão', 'Dinheiro', 'Pix'],
        var_name='Método',
        value_name='Valor'
    )
    daily_data_melted = daily_data_melted[daily_data_melted['Valor'] > 0]
    if daily_data_melted.empty: return None

    bar_chart = alt.Chart(daily_data_melted).mark_bar().encode(
        x=alt.X('DataFormatada:N', title='Data', sort=alt.EncodingSortField(field="Data", op="min", order='ascending'), axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('sum(Valor):Q', title='Valor Total (R$)'), # Empilha os valores para cada dia
        color=alt.Color('Método:N', legend=alt.Legend(title="Método"), scale=alt.Scale(scheme='tableau10')),
        tooltip=[
            alt.Tooltip('DataFormatada:N', title="Data"),
            alt.Tooltip('Método:N'),
            alt.Tooltip('sum(Valor):Q', format='R$,.2f', title="Valor") # sum(Valor) não é o ideal aqui, deveria ser só Valor para tooltip
        ]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams(text="Vendas Diárias por Método", fontSize=16, dy=-10, anchor='middle'))
    return bar_chart

def create_accumulated_capital_line_chart(df_data):
    if df_data.empty or 'Data' not in df_data.columns or 'Total' not in df_data.columns: return None
    df_accumulated = df_data.sort_values('Data').copy()
    if df_accumulated.empty: return None # Checagem adicional
    df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()

    line_chart = alt.Chart(df_accumulated).mark_area(
        line={'color':'steelblue', 'strokeWidth': 2},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='white', offset=0), alt.GradientStop(color='steelblue', offset=1)],
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
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams(text="Crescimento do Capital Acumulado", fontSize=16, dy=-10, anchor='middle'))
    return line_chart

def create_avg_sales_by_weekday_bar_chart(df_data):
    if df_data.empty or 'DiaSemanaNome' not in df_data.columns or 'DiaSemanaNum' not in df_data.columns: return None
    dias_funcionamento = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
    df_data_funcionamento = df_data[df_data['DiaSemanaNome'].isin(dias_funcionamento)]
    if df_data_funcionamento.empty: return None

    vendas_media_dia_semana = df_data_funcionamento.groupby(['DiaSemanaNum', 'DiaSemanaNome'])['Total'].mean().reset_index()

    bar_chart = alt.Chart(vendas_media_dia_semana).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X('DiaSemanaNome:N', title='Dia da Semana', sort=alt.EncodingSortField(field="DiaSemanaNum", op="min", order='ascending')),
        y=alt.Y('Total:Q', title='Média de Vendas (R$)'),
        color=alt.Color('DiaSemanaNome:N', legend=None, scale=alt.Scale(scheme='tableau10')),
        tooltip=[alt.Tooltip('DiaSemanaNome:N', title="Dia"), alt.Tooltip('Total:Q', format='R$,.2f', title="Média")]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams(text="Média de Vendas por Dia da Semana (Seg-Sáb)", fontSize=16, dy=-10, anchor='middle'))
    text_on_bars = bar_chart.mark_text(dy=-10).encode(text=alt.Text('Total:Q', format="R$,.0f"))
    return bar_chart + text_on_bars

def create_monthly_trend_line_chart(df_data):
    if df_data.empty or 'AnoMês' not in df_data.columns or df_data['AnoMês'].nunique() <= 1: return None
    vendas_mensais = df_data.groupby('AnoMês')['Total'].sum().reset_index()
    vendas_mensais['Variação %'] = vendas_mensais['Total'].pct_change() * 100

    line_chart = alt.Chart(vendas_mensais).mark_line(point=alt.OverlayMarkDef(color="firebrick", size=50, filled=True), strokeWidth=3).encode(
        x=alt.X('AnoMês:N', title='Mês', sort='ascending'),
        y=alt.Y('Total:Q', title='Total de Vendas (R$)'),
        tooltip=[
            alt.Tooltip('AnoMês:N', title="Mês"),
            alt.Tooltip('Total:Q', format='R$,.2f', title="Faturamento"),
            alt.Tooltip('Variação %:Q', format='+.1f', title="Variação MoM (%)")
        ]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams(text="Tendência Mensal de Faturamento", fontSize=16, dy=-10, anchor='middle'))
    return line_chart

def create_weekly_seasonality_bar_chart(df_data):
    if df_data.empty or 'DiaSemanaNome' not in df_data.columns or 'DiaSemanaNum' not in df_data.columns or len(df_data) <=6: return None
    dias_funcionamento = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
    df_data_funcionamento = df_data[df_data['DiaSemanaNome'].isin(dias_funcionamento)]
    if df_data_funcionamento.empty: return None

    vendas_sum_dia_semana = df_data_funcionamento.groupby(['DiaSemanaNum', 'DiaSemanaNome'])['Total'].sum().reset_index()
    total_periodo_saz = vendas_sum_dia_semana['Total'].sum()
    if total_periodo_saz == 0: return None
    vendas_sum_dia_semana['Porcentagem'] = (vendas_sum_dia_semana['Total'] / total_periodo_saz) * 100

    bar_chart = alt.Chart(vendas_sum_dia_semana).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X('DiaSemanaNome:N', title='Dia da Semana', sort=alt.EncodingSortField(field="DiaSemanaNum", op="min", order='ascending')),
        y=alt.Y('Porcentagem:Q', title='% do Volume Semanal'),
        color=alt.Color('DiaSemanaNome:N', legend=None, scale=alt.Scale(scheme='tableau10')),
        tooltip=[
            alt.Tooltip('DiaSemanaNome:N', title="Dia"),
            alt.Tooltip('Total:Q', format='R$,.2f', title="Total no Período"),
            alt.Tooltip('Porcentagem:Q', format='.1f', title="% do Total")
        ]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams(text="Distribuição % de Vendas na Semana (Seg-Sáb)", fontSize=16, dy=-10, anchor='middle'))
    text_on_bars = bar_chart.mark_text(dy=-10).encode(text=alt.Text('Porcentagem:Q', format=".0f") + "%")
    return bar_chart + text_on_bars

def create_sales_value_histogram(df_data):
    if df_data.empty or 'Total' not in df_data.columns: return None
    histogram = alt.Chart(df_data).mark_bar().encode(
        alt.X('Total:Q', bin=alt.Bin(maxbins=20), title='Valor da Venda (R$)'),
        alt.Y('count()', title='Frequência (Nº de Vendas)'),
        tooltip=[
            alt.Tooltip('count()', title="Nº de Vendas"),
            alt.Tooltip('Total:Q', bin=True, title="Intervalo de Valor")
        ]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams(text="Distribuição dos Valores Totais de Venda", fontSize=16, dy=-10, anchor='middle'))
    return histogram

# --- Interface Principal ---
def main():
    st.title("🍔 Sistema de Vendas ClipsBurger")

    df_raw, worksheet_obj = read_google_sheet()
    df_processed = process_data(df_raw)

    tab_registrar, tab_analise, tab_estatisticas = st.tabs([
        "📝 Registrar Venda", "📈 Análise Detalhada", "📊 Estatísticas Chave"
    ])

    with tab_registrar:
        st.header("Nova Venda")
        with st.container(border=True): # Adicionado container com borda
            with st.form("venda_form"):
                data_venda = st.date_input("🗓️ Data da Venda", datetime.now(), key="data_venda_input")
                c1, c2, c3 = st.columns(3)
                cartao = c1.number_input("💳 Cartão (R$)", min_value=0.0, format="%.2f", key="cartao_input")
                dinheiro = c2.number_input("💵 Dinheiro (R$)", min_value=0.0, format="%.2f", key="dinheiro_input")
                pix = c3.number_input("📱 PIX (R$)", min_value=0.0, format="%.2f", key="pix_input")
                total_venda_calculado = cartao + dinheiro + pix
                st.markdown(f"<h3 style='text-align: center; margin-top:10px;'>Total: R$ {total_venda_calculado:,.2f}</h3>", unsafe_allow_html=True)

                submitted = st.form_submit_button("💾 Registrar Venda", use_container_width=True, type="primary")
                if submitted:
                    if total_venda_calculado > 0:
                        formatted_date = data_venda.strftime('%d/%m/%Y')
                        if add_data_to_sheet(formatted_date, cartao, dinheiro, pix, worksheet_obj):
                            st.cache_data.clear()
                            st.rerun()
                    else:
                        st.warning("⚠️ O total da venda deve ser maior que zero.")

    df_filtrado_sidebar = df_processed.copy()
    with st.sidebar:
        st.header("🔍 Filtros")
        if not df_processed.empty and 'Ano' in df_processed.columns:
            anos_disponiveis = sorted(df_processed['Ano'].unique(), reverse=True)
            default_anos = anos_disponiveis[:1]
            selected_anos = st.multiselect("Ano(s)", anos_disponiveis, default=default_anos, key="sel_anos_sidebar")

            if selected_anos:
                df_filtrado_sidebar = df_filtrado_sidebar[df_filtrado_sidebar['Ano'].isin(selected_anos)]
                meses_ano_filtrado = sorted(df_filtrado_sidebar['Mês'].unique())
                meses_opcoes = {m: datetime(2000,m,1).strftime('%B').capitalize() for m in meses_ano_filtrado}

                default_meses_num = []
                if datetime.now().year in selected_anos and datetime.now().month in meses_opcoes:
                         default_meses_num = [datetime.now().month]

                selected_meses_num = st.multiselect(
                    "Mês(es)",
                    options=list(meses_opcoes.keys()),
                    format_func=lambda m: meses_opcoes[m],
                    default=default_meses_num if default_meses_num else list(meses_opcoes.keys()),
                    key="sel_meses_sidebar"
                )
                if selected_meses_num:
                    df_filtrado_sidebar = df_filtrado_sidebar[df_filtrado_sidebar['Mês'].isin(selected_meses_num)]
            else:
                st.multiselect("Mês(es)", [], disabled=True)
        else:
            st.info("Sem dados para aplicar filtros.")

    with tab_analise:
        st.header("Análise Detalhada das Vendas")
        if df_filtrado_sidebar.empty:
            st.info("ℹ️ Sem dados para exibir com os filtros atuais ou a planilha está vazia.")
        else:
            with st.container(border=True):
                st.subheader("📋 Tabela de Vendas Filtradas")
                st.dataframe(
                    df_filtrado_sidebar[['DataFormatada', 'DiaSemanaNome', 'Cartão', 'Dinheiro', 'Pix', 'Total']],
                    use_container_width=True, height=350, hide_index=True,
                    column_config={
                        "DataFormatada": "Data", "DiaSemanaNome": "Dia",
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
                    if chart_pie_payment: st.altair_chart(chart_pie_payment, use_container_width=True)
                    else: st.caption("Sem dados para o gráfico de métodos de pagamento.")

                with st.container(border=True):
                    chart_accum_capital = create_accumulated_capital_line_chart(df_filtrado_sidebar)
                    if chart_accum_capital: st.altair_chart(chart_accum_capital, use_container_width=True)
                    else: st.caption("Sem dados para o gráfico de capital acumulado.")
            with charts_col2:
                with st.container(border=True):
                    chart_daily_sales = create_daily_sales_bar_chart(df_filtrado_sidebar)
                    if chart_daily_sales: st.altair_chart(chart_daily_sales, use_container_width=True)
                    else: st.caption("Sem dados para o gráfico de vendas diárias.")

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
                maior_venda_f = df_filtrado_sidebar['Total'].max() if not df_filtrado_sidebar.empty else 0

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
                    if chart_avg_weekday: st.altair_chart(chart_avg_weekday, use_container_width=True)
                    else: st.caption("Sem dados para média por dia da semana.")
                with st.container(border=True):
                    chart_sales_hist = create_sales_value_histogram(df_filtrado_sidebar)
                    if chart_sales_hist: st.altair_chart(chart_sales_hist, use_container_width=True)
                    else: st.caption("Sem dados para histograma de valores.")
            with stats_c2:
                with st.container(border=True):
                    chart_monthly_trend = create_monthly_trend_line_chart(df_filtrado_sidebar)
                    if chart_monthly_trend: st.altair_chart(chart_monthly_trend, use_container_width=True)
                    else: st.caption("Sem dados para tendência mensal (>1 mês).")
                with st.container(border=True):
                    chart_weekly_seas = create_weekly_seasonality_bar_chart(df_filtrado_sidebar)
                    if chart_weekly_seas: st.altair_chart(chart_weekly_seas, use_container_width=True)
                    else: st.caption("Sem dados para sazonalidade semanal (>6 dias).")

            with st.expander("💡 Mais Insights e Projeções (Simplificado)", expanded=False):
                if not df_filtrado_sidebar.empty:
                    dias_distintos = df_filtrado_sidebar['Data'].nunique()
                    media_diaria_faturamento = total_faturamento_f / dias_distintos if dias_distintos > 0 else 0
                    st.markdown(f"**Média Diária de Faturamento (no período):** R$ {media_diaria_faturamento:,.2f} (baseado em {dias_distintos} dias com vendas)")
                    projecao_30_dias = media_diaria_faturamento * 30 # Considerando 30 dias corridos
                    st.markdown(f"**Projeção Simples para 30 dias:** R$ {projecao_30_dias:,.2f} (se o ritmo atual se mantiver)")
                else:
                    st.caption("Sem dados para insights adicionais.")

if __name__ == "__main__":
    main()
