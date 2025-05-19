import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import locale

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID_SECRET = "google_sheets.spreadsheet_id"  # Chave para o segredo
WORKSHEET_NAME_SECRET = "google_sheets.worksheet_name" # Chave para o segredo

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema de Vendas ClipsBurger", layout="centered")

# Configura o locale para Português do Brasil para formatação de datas e nomes
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252') # Alternativa para Windows
    except locale.Error:
        st.warning("Locale pt_BR não encontrado. Nomes de meses/dias podem aparecer em inglês.")

# CSS específico para a seção de resumo
st.markdown("""
<style>
    /* Estilo para os containers da seção de resumo */
    .resume-kpi-container {
        border: 1px solid #4A4A4A; /* Borda sutil, funciona bem em tema escuro */
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px; /* Espaço entre os KPIs */
        text-align: center; /* Centraliza o texto da métrica */
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    .resume-kpi-container:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    /* Ajuste para o st.metric dentro desses containers específicos */
    .resume-kpi-container div[data-testid="stMetric"] {
        background-color: transparent !important; /* Garante que não haja fundo branco da métrica */
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    .resume-kpi-container div[data-testid="stMetricLabel"] {
        font-size: 0.9em; /* Tamanho menor para o label da métrica */
    }
    .resume-kpi-container div[data-testid="stMetricValue"] {
        font-size: 1.5em; /* Tamanho maior para o valor da métrica */
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


CHART_HEIGHT = 380 # Altura padrão para gráficos grandes

# --- Funções de Cache para Acesso ao Google Sheets ---
@st.cache_resource
def get_google_auth():
    """Autoriza o acesso ao Google Sheets e retorna o cliente gspread."""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/spreadsheets.readonly',
              'https://www.googleapis.com/auth/drive.readonly']
    try:
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
        return gc
    except KeyError as e:
        st.error(f"❌ Erro ao carregar segredos: Chave '{e}' não encontrada. Verifique seu `secrets.toml`.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro de autenticação com Google: {e}")
        return None

@st.cache_resource
def get_worksheet():
    """Retorna o objeto worksheet da planilha especificada."""
    gc = get_google_auth()
    if gc:
        try:
            spreadsheet_id = st.secrets.get(SPREADSHEET_ID_SECRET, "ID_PADRAO_SE_NAO_ENCONTRADO") # Fallback
            worksheet_name = st.secrets.get(WORKSHEET_NAME_SECRET, "Vendas") # Fallback
            
            if spreadsheet_id == "ID_PADRAO_SE_NAO_ENCONTRADO":
                st.error(f"Chave '{SPREADSHEET_ID_SECRET}' não encontrada nos segredos.")
                return None

            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            return worksheet
        except SpreadsheetNotFound:
            st.error(f"Planilha com ID '{spreadsheet_id}' ou aba '{worksheet_name}' não encontrada.")
            return None
        except KeyError as e: # Para o caso de SPREADSHEET_ID_SECRET ou WORKSHEET_NAME_SECRET não estarem nos segredos
            st.error(f"Chave de segredo '{e}' não encontrada para detalhes da planilha. Verifique seu `secrets.toml`.")
            return None
        except Exception as e:
            st.error(f"Erro ao acessar a planilha '{worksheet_name}': {e}")
            return None
    return None

@st.cache_data(show_spinner="Lendo dados da planilha...")
def read_sales_data():
    """Lê todos os registros da planilha de vendas e retorna como DataFrame."""
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records()
            if not rows:
                st.toast("⚠️ Planilha de vendas está vazia.", icon="📄")
                return pd.DataFrame(columns=['Data', 'Cartão', 'Dinheiro', 'Pix']) # Schema esperado
            df = pd.DataFrame(rows)
            # Garante que as colunas monetárias existam, mesmo que a planilha esteja mal formatada
            for col_monetaria in ['Cartão', 'Dinheiro', 'Pix']:
                if col_monetaria not in df.columns:
                    df[col_monetaria] = 0
            if 'Data' not in df.columns: # Garante que a coluna 'Data' existe
                df['Data'] = pd.NaT # Usar NaT para datas ausentes

            return df
        except Exception as e:
            st.error(f"Erro ao ler dados da planilha: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- Funções de Manipulação de Dados ---
def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet_obj):
    """Adiciona uma nova linha de dados à planilha Google Sheets."""
    if worksheet_obj is None:
        st.error("Não foi possível acessar a planilha para adicionar dados.")
        return False
    try:
        new_row = [date, float(cartao), float(dinheiro), float(pix)]
        worksheet_obj.append_row(new_row)
        st.success("Dados registrados com sucesso!")
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar dados na planilha: {e}")
        return False

@st.cache_data(show_spinner="Processando dados...")
def process_data(df_input):
    """Processa e prepara os dados de vendas para análise."""
    if df_input is None or df_input.empty:
        return pd.DataFrame()
    
    df = df_input.copy()
    
    for col in ['Cartão', 'Dinheiro', 'Pix']:
        if col not in df.columns: # Adiciona coluna se não existir
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']
    
    if 'Data' in df.columns and not df['Data'].isnull().all():
        try:
            df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
            df.dropna(subset=['Data'], inplace=True)
            
            if not df.empty:
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['MêsNome'] = df['Data'].dt.strftime('%B').str.capitalize()
                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                df['DiaSemana'] = df['Data'].dt.strftime('%A').str.capitalize()
                df['DiaSemanaNum'] = df['Data'].dt.dayofweek # Para ordenação
            else:
                st.toast("Nenhuma data válida encontrada após conversão.", icon="⚠️")

        except Exception as e:
            st.error(f"Erro ao processar a coluna 'Data': {e}")
            # Cria colunas derivadas vazias para evitar erros downstream
            for col_date_derived in ['Ano', 'Mês', 'MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana', 'DiaSemanaNum']:
                if col_date_derived not in df.columns:
                     df[col_date_derived] = None
    else: # Se não há coluna 'Data' ou está toda vazia
        for col_date_derived in ['Ano', 'Mês', 'MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana', 'DiaSemanaNum']:
            if col_date_derived not in df.columns:
                 df[col_date_derived] = None
    return df

# --- Funções de Gráficos --- (Adaptadas para usar theme="streamlit")
def create_pie_chart_payment_methods(df_data):
    if df_data is None or df_data.empty or not all(col in df_data.columns for col in ['Cartão', 'Dinheiro', 'Pix']): return None
    payment_sum = df_data[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
    payment_sum.columns = ['Método', 'Valor']
    total_pagamentos = payment_sum['Valor'].sum()
    if total_pagamentos == 0: return None
    payment_sum['Porcentagem'] = (payment_sum['Valor'] / total_pagamentos) * 100
    pie_chart = alt.Chart(payment_sum).mark_arc(innerRadius=70, outerRadius=140).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
        tooltip=[alt.Tooltip("Método:N"), alt.Tooltip("Valor:Q", format="R$,.2f", title="Valor"), alt.Tooltip("Porcentagem:Q", format=".1f", title="%")]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams("Distribuição por Método de Pagamento", fontSize=16, dy=-10, anchor='middle'))
    text_values = pie_chart.mark_text(radius=105, size=14, fontWeight='bold').encode(text=alt.Text("Porcentagem:Q", format=".0f") + "%")
    return pie_chart + text_values

def create_daily_sales_bar_chart(df_data):
    if df_data is None or df_data.empty or 'DataFormatada' not in df_data.columns: return None
    if 'Data' not in df_data.columns and 'DataFormatada' in df_data.columns:
        df_data_copy = df_data.copy()
        df_data_copy.loc[:, 'Data'] = pd.to_datetime(df_data_copy['DataFormatada'], format='%d/%m/%Y', errors='coerce')
        df_to_melt = df_data_copy
    elif 'Data' in df_data.columns:
        df_to_melt = df_data
    else: return None
    
    daily_data = df_to_melt.melt(id_vars=['DataFormatada', 'Data'], value_vars=['Cartão', 'Dinheiro', 'Pix'], var_name='Método', value_name='Valor')
    daily_data = daily_data[daily_data['Valor'] > 0]
    if daily_data.empty: return None
    
    bar_chart = alt.Chart(daily_data).mark_bar(size=20).encode(
        x=alt.X('DataFormatada:N', title='Data', axis=alt.Axis(labelAngle=-45), sort=alt.EncodingSortField(field="Data", op="min", order='ascending')),
        y=alt.Y('Valor:Q', title='Valor (R$)'),
        color=alt.Color('Método:N', legend=alt.Legend(title="Método")),
        tooltip=['DataFormatada', 'Método', alt.Tooltip('Valor:Q', format='R$,.2f')]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams("Vendas Diárias por Método", fontSize=16, dy=-10, anchor='middle'))
    return bar_chart

def create_accumulated_capital_line_chart(df_data):
    if df_data is None or df_data.empty or 'Data' not in df_data.columns or 'Total' not in df_data.columns: return None
    df_accumulated = df_data.sort_values('Data').copy()
    if df_accumulated.empty: return None
    df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()
    line_chart = alt.Chart(df_accumulated).mark_area(line={'color':'steelblue', 'strokeWidth':2}, color=alt.Gradient(gradient='linear',stops=[alt.GradientStop(color='rgba(70,130,180,0.1)',offset=0.3),alt.GradientStop(color='rgba(70,130,180,0.7)',offset=1)],x1=1,x2=1,y1=1,y2=0)).encode(
        x=alt.X('Data:T', title='Data', axis=alt.Axis(format="%d/%m/%y")),
        y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
        tooltip=[alt.Tooltip('DataFormatada', title="Data"), alt.Tooltip('Total Acumulado:Q', format='R$,.2f')]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams("Acúmulo de Capital", fontSize=16, dy=-10, anchor='middle'))
    return line_chart

def create_avg_sales_by_weekday_bar_chart(df_data):
    if df_data is None or df_data.empty or 'DiaSemana' not in df_data.columns: return None
    dias_ordem_locale = [datetime(2000, 1, i).strftime('%A').capitalize() for i in range(3, 3+7)][:6] # Seg a Sáb
    df_funcionamento = df_data[df_data['DiaSemana'].isin(dias_ordem_locale)]
    if df_funcionamento.empty: return None
    
    vendas_media_dia = df_funcionamento.groupby('DiaSemana')['Total'].mean().reset_index()
    vendas_media_dia['DiaSemana'] = pd.Categorical(vendas_media_dia['DiaSemana'], categories=dias_ordem_locale, ordered=True)
    vendas_media_dia = vendas_media_dia.sort_values('DiaSemana')

    bar_chart = alt.Chart(vendas_media_dia).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X('DiaSemana:N', title='Dia da Semana', sort=dias_ordem_locale),
        y=alt.Y('Total:Q', title='Média de Vendas (R$)'),
        color=alt.Color('DiaSemana:N', legend=None),
        tooltip=[alt.Tooltip('DiaSemana:N', title="Dia"), alt.Tooltip('Total:Q', format='R$,.2f', title="Média")]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams("Média de Vendas por Dia da Semana (Seg-Sáb)", fontSize=16, dy=-10, anchor='middle'))
    text_on_bars = bar_chart.mark_text(dy=-10).encode(text=alt.Text('Total:Q', format="R$,.0f"))
    return bar_chart + text_on_bars

def create_monthly_trend_line_chart(df_data):
    if df_data is None or df_data.empty or 'AnoMês' not in df_data.columns or df_data['AnoMês'].nunique() <= 1: return None
    vendas_mensais = df_data.groupby('AnoMês')['Total'].sum().reset_index()
    vendas_mensais['Variação %'] = vendas_mensais['Total'].pct_change() * 100
    line_chart = alt.Chart(vendas_mensais).mark_line(point=alt.OverlayMarkDef(color="firebrick",size=50,filled=True),strokeWidth=3).encode(
        x=alt.X('AnoMês:N', title='Mês', sort='ascending'),
        y=alt.Y('Total:Q', title='Total de Vendas (R$)'),
        tooltip=[alt.Tooltip('AnoMês:N'), alt.Tooltip('Total:Q', format='R$,.2f'), alt.Tooltip('Variação %:Q', format='+.1f')]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams("Tendência Mensal de Faturamento", fontSize=16, dy=-10, anchor='middle'))
    return line_chart

def create_sales_value_histogram(df_data):
    if df_data is None or df_data.empty or 'Total' not in df_data.columns: return None
    histogram = alt.Chart(df_data).mark_bar().encode(
        alt.X('Total:Q', bin=alt.Bin(maxbins=20), title='Valor da Venda (R$)'),
        alt.Y('count()', title='Frequência'),
        tooltip=[alt.Tooltip('count()', title="Nº de Vendas"), alt.Tooltip('Total:Q', bin=True, title="Faixa de Valor")]
    ).properties(height=CHART_HEIGHT, title=alt.TitleParams("Distribuição dos Valores de Venda", fontSize=16, dy=-10, anchor='middle'))
    return histogram

# --- Interface Principal da Aplicação ---
def main():
    st.title("📊 Sistema de Registro de Vendas ClipsBurger")
    
    df_raw = read_sales_data()
    df_processed = process_data(df_raw.copy()) # Passar cópia para process_data

    tab1, tab2, tab3 = st.tabs(["📝 Registrar Venda", "📈 Análise Detalhada", "📊 Estatísticas"])

    with tab1:
        st.header("Registrar Nova Venda")
        with st.form("venda_form"):
            data_input = st.date_input("Data", datetime.now(), key="form_data")
            col1, col2, col3 = st.columns(3)
            cartao_input = col1.number_input("Cartão (R$)", min_value=0.0, format="%.2f", key="form_cartao")
            dinheiro_input = col2.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f", key="form_dinheiro")
            pix_input = col3.number_input("PIX (R$)", min_value=0.0, format="%.2f", key="form_pix")
            
            total_venda_form = cartao_input + dinheiro_input + pix_input
            st.markdown(f"**Total da venda: R$ {total_venda_form:,.2f}**")
            submitted = st.form_submit_button("💾 Registrar Venda", type="primary")
            
            if submitted:
                if total_venda_form > 0:
                    formatted_date = data_input.strftime('%d/%m/%Y')
                    worksheet_obj = get_worksheet() # Pega o worksheet (cacheado)
                    if add_data_to_sheet(formatted_date, cartao_input, dinheiro_input, pix_input, worksheet_obj):
                        read_sales_data.clear()
                        process_data.clear()
                        st.rerun()
                else:
                    st.warning("O total da venda deve ser maior que zero.")

    # Filtros na sidebar
    df_filtered = df_processed.copy() # Começa com todos os dados processados
    if not df_processed.empty and 'Ano' in df_processed.columns and not df_processed['Ano'].dropna().empty:
        with st.sidebar:
            st.header("🔍 Filtros")
            current_year = datetime.now().year
            anos_disponiveis = sorted(df_processed['Ano'].dropna().unique().astype(int), reverse=True)
            default_anos = [current_year] if current_year in anos_disponiveis else (anos_disponiveis[:1] if anos_disponiveis else [])
            selected_anos_filter = st.multiselect("Ano(s):", options=anos_disponiveis, default=default_anos, key="filter_ano")

            df_para_filtro_mes = df_processed.copy()
            if selected_anos_filter:
                df_para_filtro_mes = df_para_filtro_mes[df_para_filtro_mes['Ano'].isin(selected_anos_filter)]
            
            selected_meses_filter = []
            if not df_para_filtro_mes.empty and 'Mês' in df_para_filtro_mes.columns and not df_para_filtro_mes['Mês'].dropna().empty:
                current_month = datetime.now().month
                meses_numeros_disponiveis = sorted(df_para_filtro_mes['Mês'].dropna().unique().astype(int))
                meses_nomes_map = {m: datetime(2000, m, 1).strftime('%B').capitalize() for m in meses_numeros_disponiveis}
                
                default_meses_sel = []
                if selected_anos_filter and (current_year in selected_anos_filter) and (current_month in meses_nomes_map):
                    default_meses_sel = [current_month]
                elif meses_numeros_disponiveis: # Se não, default para todos os meses disponíveis para os anos selecionados
                    default_meses_sel = meses_numeros_disponiveis

                selected_meses_filter = st.multiselect("Mês(es):", 
                                                       options=meses_numeros_disponiveis, 
                                                       format_func=lambda m: f"{m:02d} - {meses_nomes_map.get(m, str(m))}",
                                                       default=default_meses_sel,
                                                       key="filter_mes",
                                                       disabled=not selected_anos_filter or not meses_numeros_disponiveis) # Desabilita se não houver anos ou meses

            # Aplica filtros
            if selected_anos_filter:
                df_filtered = df_processed[df_processed['Ano'].isin(selected_anos_filter)]
                if selected_meses_filter and 'Mês' in df_filtered.columns: # Só filtra por mês se meses foram selecionados
                    df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses_filter)]
            # Se nenhum filtro de ano, df_filtered já é df_processed.copy()
    else: # df_processed está vazio ou não tem coluna 'Ano'
        with st.sidebar:
            st.header("🔍 Filtros")
            st.info("Sem dados para aplicar filtros.")
        df_filtered = pd.DataFrame() # Garante que df_filtered é um DF vazio


    with tab2:
        st.header("Análise Detalhada de Vendas")
        if df_filtered.empty:
            st.info("ℹ️ Sem dados para exibir com os filtros atuais ou a planilha está vazia.")
        else:
            with st.container(border=True):
                st.subheader("📋 Tabela de Vendas Filtradas")
                cols_display = ['DataFormatada', 'DiaSemana', 'Cartão', 'Dinheiro', 'Pix', 'Total']
                cols_presentes = [col for col in cols_display if col in df_filtered.columns]
                st.dataframe(df_filtered[cols_presentes], use_container_width=True, height=350, hide_index=True)

            charts_col1, charts_col2 = st.columns(2)
            with charts_col1:
                with st.container(border=True):
                    chart = create_pie_chart_payment_methods(df_filtered)
                    if chart: st.altair_chart(chart, use_container_width=True, theme="streamlit")
                    else: st.caption("Sem dados para gráfico de métodos de pagamento.")
            with charts_col2:
                with st.container(border=True):
                    chart = create_daily_sales_bar_chart(df_filtered)
                    if chart: st.altair_chart(chart, use_container_width=True, theme="streamlit")
                    else: st.caption("Sem dados para gráfico de vendas diárias.")
            
            with st.container(border=True): # Gráfico de capital acumulado ocupando largura total
                chart = create_accumulated_capital_line_chart(df_filtered)
                if chart: st.altair_chart(chart, use_container_width=True, theme="streamlit")
                else: st.caption("Sem dados para gráfico de capital acumulado.")


    with tab3:
        st.header("📊 Estatísticas de Vendas")
        if df_filtered.empty:
            st.info("ℹ️ Sem dados para exibir com os filtros atuais ou a planilha está vazia.")
        else:
            with st.container(border=True): # Container para a seção de resumo
                st.subheader("🚀 Resumo Financeiro do Período")
                total_vendas = len(df_filtered)
                total_faturamento = df_filtered['Total'].sum()
                media_por_venda = total_faturamento / total_vendas if total_vendas > 0 else 0
                maior_venda = df_filtered['Total'].max() if total_vendas > 0 else 0

                # --- Seção de Resumo 2x2 ---
                col_resumo1, col_resumo2 = st.columns(2)
                with col_resumo1:
                    # Usando a classe CSS definida no st.markdown global
                    st.markdown('<div class="resume-kpi-container">', unsafe_allow_html=True)
                    st.metric(label="💰 Faturamento Total", value=f"R$ {total_faturamento:,.2f}")
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown('<div class="resume-kpi-container">', unsafe_allow_html=True)
                    st.metric(label="💸 Ticket Médio", value=f"R$ {media_por_venda:,.2f}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col_resumo2:
                    st.markdown('<div class="resume-kpi-container">', unsafe_allow_html=True)
                    st.metric(label="📈 Total de Vendas", value=f"{total_vendas:,} vendas")
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown('<div class="resume-kpi-container">', unsafe_allow_html=True)
                    st.metric(label="⭐ Maior Venda Única", value=f"R$ {maior_venda:,.2f}")
                    st.markdown('</div>', unsafe_allow_html=True)
            # --- Fim da Seção de Resumo ---

            st.markdown("---") # Separador visual

            stats_col_graf1, stats_col_graf2 = st.columns(2)
            with stats_col_graf1:
                with st.container(border=True):
                    chart = create_avg_sales_by_weekday_bar_chart(df_filtered)
                    if chart: st.altair_chart(chart, use_container_width=True, theme="streamlit")
                    else: st.caption("Sem dados para gráfico de média por dia da semana.")
                with st.container(border=True):
                    chart = create_sales_value_histogram(df_filtered)
                    if chart: st.altair_chart(chart, use_container_width=True, theme="streamlit")
                    else: st.caption("Sem dados para histograma de valores de venda.")
            with stats_col_graf2:
                with st.container(border=True):
                    chart = create_monthly_trend_line_chart(df_filtered)
                    if chart: st.altair_chart(chart, use_container_width=True, theme="streamlit")
                    else: st.caption("Sem dados suficientes para tendência mensal (>1 mês).")
                with st.container(border=True):
                    chart = create_weekly_seasonality_bar_chart(df_filtered)
                    if chart: st.altair_chart(chart, use_container_width=True, theme="streamlit")
                    else: st.caption("Sem dados suficientes para sazonalidade semanal (>6 dias).")
            
            with st.expander("💡 Mais Insights e Projeções (Simplificado)", expanded=False):
                if not df_filtered.empty and 'Data' in df_filtered.columns and 'Total' in df_filtered.columns:
                    dias_distintos = df_filtered['Data'].nunique()
                    if dias_distintos > 0:
                        media_diaria_faturamento = total_faturamento / dias_distintos
                        st.markdown(f"**Média Diária (no período):** R$ {media_diaria_faturamento:,.2f} ({dias_distintos} dias com vendas)")
                        projecao_30_dias = media_diaria_faturamento * 30
                        st.markdown(f"**Projeção Próximos 30 dias:** R$ {projecao_30_dias:,.2f}")
                    else:
                        st.caption("Não há dias distintos com vendas no período selecionado.")
                else:
                    st.caption("Sem dados para insights adicionais.")

if __name__ == "__main__":
    main()
