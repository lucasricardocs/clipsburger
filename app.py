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
        'About': "Sistema de Análise de Vendas para ClipsBurger. Desenvolvido com Streamlit."
    }
)

# CSS Minimalista para melhorias sutis e compatibilidade com tema escuro
st.markdown("""

    /* Melhora a aparência dos containers com borda */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[style*="border"] {
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); /* Sombra sutil */
        padding: 15px; /* Adiciona um pouco de padding interno */
        margin-bottom: 15px; /* Espaço entre containers */
    }
    /* Ajuste no spinner para ser mais visível em ambos os temas */
    .stSpinner > div {
        border-top-color: #FF4B4B !important; /* Cor do spinner */
    }
    /* Ajuste para métricas dentro de containers com borda, para não herdar estilos indesejados */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[style*="border"] div[data-testid="stMetric"] {
        background-color: transparent;
        border: none;
        box-shadow: none;
        padding: 0;
    }

""", unsafe_allow_html=True)

# Streamlit aplica seu tema aos gráficos Altair por padrão ao usar st.altair_chart(theme="streamlit") ou theme=None.
# Não é necessário alt.themes.enable() globalmente.

CHART_HEIGHT = 380 # Altura padrão para gráficos grandes

# --- Funções de Suporte ---
@st.cache_data(ttl=300)  # Cache por 5 minutos
def read_google_sheet():
    """Função para ler os dados da planilha Google Sheets usando st.secrets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
                 'https://www.googleapis.com/auth/spreadsheets.readonly',
                 'https://www.googleapis.com/auth/drive.readonly']

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
                st.toast("⚠️ Planilha de vendas está vazia ou não contém dados.", icon="📄")
                return pd.DataFrame(columns=['Data', 'Cartão', 'Dinheiro', 'Pix']), worksheet # Retorna DF com colunas esperadas
            df = pd.DataFrame(rows)
            # Assegurar que colunas monetárias existem, mesmo que a planilha esteja mal formatada
            for col_monetaria in ['Cartão', 'Dinheiro', 'Pix']:
                if col_monetaria not in df.columns:
                    df[col_monetaria] = 0
            if 'Data' not in df.columns: # Assegurar que a coluna 'Data' existe
                df['Data'] = pd.NaT # Usar NaT para datas ausentes

            st.toast("✔️ Dados carregados da planilha!", icon="📊")
            return df, worksheet
    except SpreadsheetNotFound:
        st.error(f"❌ Planilha com ID '{spreadsheet_id if 'spreadsheet_id' in st.secrets.get('google_sheets', {}) else 'NÃO DEFINIDO'}' ou aba '{worksheet_name if 'worksheet_name' in st.secrets.get('google_sheets', {}) else 'NÃO DEFINIDO'}' não encontrada. Verifique os valores em secrets.toml e as permissões.")
        return pd.DataFrame(), None
    except KeyError as e:
        st.error(f"❌ Erro ao carregar segredos: A chave '{e}' não foi encontrada. Verifique seu arquivo secrets.toml.")
        st.error("Estrutura esperada no secrets.toml: [google_credentials] com todos os campos do JSON, e [google_sheets] com spreadsheet_id e worksheet_name.")
        return pd.DataFrame(), None
    except Exception as e:
        st.error(f"❌ Erro de autenticação ou conexão com Google Sheets: {type(e).__name__} - {e}")
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
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()
    df = df_raw.copy()

    for col_pay in ['Cartão', 'Dinheiro', 'Pix']:
        if col_pay not in df.columns:
            df[col_pay] = 0
        df[col_pay] = pd.to_numeric(df[col_pay], errors='coerce').fillna(0)
    
    df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']

    if 'Data' in df.columns and not df['Data'].isnull().all(): # Processa apenas se a coluna Data existir e não for toda nula
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        df.dropna(subset=['Data'], inplace=True)
        if not df.empty:
            df['Ano'] = df['Data'].dt.year
            df['Mês'] = df['Data'].dt.month
            df['MêsNome'] = df['Data'].dt.strftime('%B').str.capitalize()
            df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
            df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
            df['DiaSemanaNum'] = df['Data'].dt.dayofweek
            df['DiaSemanaNome'] = df['Data'].dt.day_name().map({
                'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
                'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }).fillna('Desconhecido')
    return df

# --- Funções de Gráficos ---
def create_pie_chart_payment_methods(df_data):
    if df_data is None or df_data.empty or not all(col in df_data.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
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
    if df_data is None or df_data.empty or 'DataFormatada' not in df_data.columns: return None
    # Garante que 'Data' existe para ordenação, mesmo que 'DataFormatada' seja usada para o eixo X
    if 'Data' not in df_data.columns and 'DataFormatada' in df_data.columns:
        df_data_copy = df_data.copy() # Evitar SettingWithCopyWarning
        df_data_copy.loc[:, 'Data'] = pd.to_datetime(df_data_copy['DataFormatada'], format='%d/%m/%Y', errors='coerce')
        daily_data_melted = df_data_copy.melt(
            id_vars=['DataFormatada', 'Data'],
            value_vars=['Cartão', 'Dinheiro', 'Pix'],
            var_name='Método',
            value_name='Valor'
        )
    elif 'Data' in df_data.columns:
         daily_data_melted = df_data.melt(
            id_vars=['DataFormatada', 'Data'],
            value_vars=['Cartão', 'Dinheiro', 'Pix'],
            var_name='Método',
            value_name='Valor'
        )
    else:
        return None # Não tem nem DataFormatada nem Data

    daily_data_melted = daily_data_melted[daily_data_melted['Valor'] > 0]
    if daily_data_melted.empty: return None

    bar_chart = alt.Chart(daily_data_melted).mark_bar().encode(
        x=alt.X('DataFormatada:N', title='Data', sort=alt.EncodingSortField(field="Data", op="min", order='ascending'), axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Valor:Q', title='Valor (R$)', stack='zero'),
        color=alt.Color('Método:N', legend=alt.Legend(title="Método"), scale=alt.Scale(scheme='tableau10')),
        tooltip=[
            alt.Tooltip('DataFormatada:N', title="Data"),
            alt.Tooltip('Método:N'),
            alt.Tooltip('Valor:Q', format='R$,.2f', title="Valor do Segmento")
        ]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams(text="Vendas Diárias por Método", fontSize=16, dy=-10, anchor='middle'))
    return bar_chart

def create_accumulated_capital_line_chart(df_data):
    if df_data is None or df_data.empty or 'Data' not in df_data.columns or 'Total' not in df_data.columns: return None
    df_accumulated = df_data.sort_values('Data').copy()
    if df_accumulated.empty: return None
    df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()

    line_chart = alt.Chart(df_accumulated).mark_area(
        line={'color':'steelblue', 'strokeWidth': 2},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='rgba(70, 130, 180, 0)', offset=0.3), alt.GradientStop(color='rgba(70, 130, 180, 0.7)', offset=1)],
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
    if df_data is None or df_data.empty or 'DiaSemanaNome' not in df_data.columns or 'DiaSemanaNum' not in df_data.columns: return None
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
    df_filtrado_sidebar = pd.DataFrame() # Inicializa como DataFrame vazio
    if df_processed is not None and not df_processed.empty:
        df_para_filtrar_sidebar = df_processed.copy()
        df_filtrado_sidebar = df_processed.copy() # Default é mostrar todos os dados processados
    else:
        df_para_filtrar_sidebar = pd.DataFrame() # Garante que é DataFrame vazio se não houver dados processados

    with st.sidebar:
        st.header("🔍 Filtros")
        if not df_para_filtrar_sidebar.empty and 'Ano' in df_para_filtrar_sidebar.columns:
            anos_disponiveis = sorted(df_para_filtrar_sidebar['Ano'].unique(), reverse=True)
            default_anos = anos_disponiveis[:1] if anos_disponiveis else []
            selected_anos = st.multiselect("Ano(s)", anos_disponiveis, default=default_anos, key="sel_anos_sidebar")

            df_para_meses = pd.DataFrame(columns=['Mês'])
            if selected_anos:
                df_para_meses = df_para_filtrar_sidebar[df_para_filtrar_sidebar['Ano'].isin(selected_anos)]
            
            meses_opcoes = {}
            if not df_para_meses.empty and 'Mês' in df_para_meses.columns:
                meses_disponiveis_no_filtro_ano = sorted(df_para_meses['Mês'].unique())
                meses_opcoes = {m: datetime(2000, m, 1).strftime('%B').capitalize() for m in meses_disponiveis_no_filtro_ano}
            
            default_meses_num_sidebar = []
            if selected_anos and meses_opcoes:
                current_year_selected = datetime.now().year in selected_anos
                current_month_available = datetime.now().month in meses_opcoes
                if current_year_selected and current_month_available:
                    default_meses_num_sidebar = [datetime.now().month]
                else:
                    default_meses_num_sidebar = list(meses_opcoes.keys())
            
            selected_meses_num_sidebar = st.multiselect(
                "Mês(es)",
                options=list(meses_opcoes.keys()),
                format_func=lambda m: meses_opcoes.get(m, str(m)),
                default=default_meses_num_sidebar,
                key="sel_meses_sidebar",
                disabled=not selected_anos or not meses_opcoes # Desabilita se nenhum ano selecionado OU nenhum mês disponível para os anos selecionados
            )

            # Aplicar filtros ao df_filtrado_sidebar
            if selected_anos:
                df_filtrado_sidebar = df_para_filtrar_sidebar[df_para_filtrar_sidebar['Ano'].isin(selected_anos)]
                if selected_meses_num_sidebar and meses_opcoes : # Aplica filtro de mês apenas se anos E meses foram selecionados E há opções de meses
                    df_filtrado_sidebar = df_filtrado_sidebar[df_filtrado_sidebar['Mês'].isin(selected_meses_num_sidebar)]
            # Se nenhum ano selecionado, df_filtrado_sidebar mantém todos os dados processados (se houver)
            elif df_processed is not None:
                 df_filtrado_sidebar = df_processed.copy()

        else:
            st.info("Sem dados carregados para aplicar filtros.")
            df_filtrado_sidebar = pd.DataFrame()


    with tab_analise:
        st.header("Análise Detalhada das Vendas")
        if df_filtrado_sidebar is None or df_filtrado_sidebar.empty:
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
                    if chart_pie_payment: st.altair_chart(chart_pie_payment, use_container_width=True, theme="streamlit")
                    else: st.caption("Sem dados para o gráfico de métodos de pagamento.")
                with st.container(border=True):
                    chart_accum_capital = create_accumulated_capital_line_chart(df_filtrado_sidebar)
                    if chart_accum_capital: st.altair_chart(chart_accum_capital, use_container_width=True, theme="streamlit")
                    else: st.caption("Sem dados para o gráfico de capital acumulado.")
            with charts_col2:
                with st.container(border=True):
                    chart_daily_sales = create_daily_sales_bar_chart(df_filtrado_sidebar)
                    if chart_daily_sales: st.altair_chart(chart_daily_sales, use_container_width=True, theme="streamlit")
                    else: st.caption("Sem dados para o gráfico de vendas diárias.")

    with tab_estatisticas:
        st.header("Estatísticas Chave e Tendências")
        if df_filtrado_sidebar is None or df_filtrado_sidebar.empty:
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
                    if chart_avg_weekday: st.altair_chart(chart_avg_weekday, use_container_width=True, theme="streamlit")
                    else: st.caption("Sem dados para média por dia da semana.")
                with st.container(border=True):
                    chart_sales_hist = create_sales_value_histogram(df_filtrado_sidebar)
                    if chart_sales_hist: st.altair_chart(chart_sales_hist, use_container_width=True, theme="streamlit")
                    else: st.caption("Sem dados para histograma de valores.")
            with stats_c2:
                with st.container(border=True):
                    chart_monthly_trend = create_monthly_trend_line_chart(df_filtrado_sidebar)
                    if chart_monthly_trend: st.altair_chart(chart_monthly_trend, use_container_width=True, theme="streamlit")
                    else: st.caption("Sem dados para tendência mensal (>1 mês).")
                with st.container(border=True):
                    chart_weekly_seas = create_weekly_seasonality_bar_chart(df_filtrado_sidebar)
                    if chart_weekly_seas: st.altair_chart(chart_weekly_seas, use_container_width=True, theme="streamlit")
                    else: st.caption("Sem dados para sazonalidade semanal (>6 dias).")

            with st.expander("💡 Mais Insights e Projeções (Simplificado)", expanded=False):
                if not df_filtrado_sidebar.empty and 'Data' in df_filtrado_sidebar.columns and 'Total' in df_filtrado_sidebar.columns: # Garante que Total também existe
                    dias_distintos = df_filtrado_sidebar['Data'].nunique()
                    if dias_distintos > 0:
                        # Usa total_faturamento_f que já foi calculado com base no df_filtrado_sidebar
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
