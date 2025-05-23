import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import locale

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
WORKSHEET_NAME = 'Vendas'

# Configuração da página Streamlit - Alterado para centered
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="centered")

# Configura o locale para Português do Brasil para formatação de datas e nomes
#try:
    #locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
#except locale.Error:
    #st.warning("Locale pt_BR.UTF-8 não encontrado. Nomes de meses/dias podem aparecer em inglês.")

# Define a ordem correta dos dias da semana e meses
dias_semana_ordem = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"]
meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# --- Funções de Cache para Acesso ao Google Sheets ---
@st.cache_resource
def get_google_auth():
    """Autoriza o acesso ao Google Sheets e retorna o cliente gspread."""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/spreadsheets.readonly',
              'https://www.googleapis.com/auth/drive.readonly']
    try:
        credentials_dict = st.secrets.get("google_credentials")
        if not credentials_dict:
            st.error("Credenciais do Google não encontradas em st.secrets. Configure o arquivo .streamlit/secrets.toml")
            return None
        else:
            creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Erro de autenticação com Google: {e}")
        return None

@st.cache_resource
def get_worksheet():
    """Retorna o objeto worksheet da planilha especificada."""
    gc = get_google_auth()
    if gc:
        try:
            spreadsheet = gc.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
            return worksheet
        except SpreadsheetNotFound:
            st.error(f"Planilha com ID {SPREADSHEET_ID} não encontrada.")
            return None
        except Exception as e:
            st.error(f"Erro ao acessar a planilha '{WORKSHEET_NAME}': {e}")
            return None
    return None

@st.cache_data
def read_sales_data():
    """Lê todos os registros da planilha de vendas e retorna como DataFrame."""
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records()
            df = pd.DataFrame(rows)
            for col in ['Cartão', 'Dinheiro', 'Pix']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                else:
                    df[col] = 0
            df.fillna({col: 0 for col in ['Cartão', 'Dinheiro', 'Pix']}, inplace=True)
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
        st.success("Dados registrados com sucesso! ✅")
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar dados na planilha: {e}")
        return False

@st.cache_data
def process_data(df_input):
    """Processa e prepara os dados de vendas para análise."""
    df = df_input.copy()
    if not df.empty:
        for col in ['Cartão', 'Dinheiro', 'Pix']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0

        df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']

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
                    # Usar dayofweek (locale-independent) e mapear para nomes em português
                    day_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado"}
                    df['DiaSemana'] = df['Data'].dt.dayofweek.map(day_map)
                    df['DiaDoMes'] = df['Data'].dt.day

                    df['DiaSemana'] = pd.Categorical(df['DiaSemana'], categories=dias_semana_ordem, ordered=True)
                    df['MêsNome'] = pd.Categorical(df['MêsNome'], categories=meses_ordem, ordered=True)
                else:
                    st.warning("Nenhuma data válida encontrada após conversão inicial.")
            except Exception as e:
                st.error(f"Erro ao processar a coluna 'Data': {e}")
                for col_date_derived in ['Ano', 'Mês', 'MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana', 'DiaDoMes']:
                    if col_date_derived not in df.columns:
                         df[col_date_derived] = None
        else:
             st.error("Coluna 'Data' não encontrada no DataFrame inicial.")
    return df

# --- Funções de Visualização ---
def create_heatmap(df, title="Mapa de Calor: Total de Vendas (Dia da Semana x Mês)"):
    """Cria um mapa de calor do total de vendas por dia da semana e mês."""
    if df.empty or 'DiaSemana' not in df.columns or 'MêsNome' not in df.columns or 'Total' not in df.columns:
        st.info("Dados insuficientes para gerar o Mapa de Calor.")
        return None

    # Remove valores nulos e agrupa os dados
    df_clean = df.dropna(subset=['DiaSemana', 'Total'])
    if df_clean.empty:
        st.info("Não há dados válidos para gerar o Mapa de Calor.")
        return None
    
    heatmap_data = df_clean.groupby(['DiaSemana'], observed=True)['Total'].sum().reset_index()
    
    if heatmap_data.empty:
        st.info("Não há dados agrupados para gerar o Mapa de Calor.")
        return None

    heatmap = alt.Chart(heatmap_data).mark_rect().encode(
        x=alt.X('MêsNome:O', title='Mês', sort=meses_ordem),
        y=alt.Y('DiaSemana:O', title='Dia da Semana', sort=dias_semana_ordem),
        color=alt.Color('Total:Q', 
                       legend=alt.Legend(title="Total Vendido (R$)"), 
                       scale=alt.Scale(scheme='viridis')),
        tooltip=[
            alt.Tooltip('MêsNome:O', title='Mês'),
            alt.Tooltip('DiaSemana:O', title='Dia da Semana'),
            alt.Tooltip('Total:Q', title='Total Vendido (R$)', format=",.2f")
        ]
    ).properties(
        title=title,
        height=400,
        width=600
    ).resolve_scale(
        color='independent'
    )
    return heatmap

def create_payment_evolution_chart(df, title="Evolução da Preferência por Pagamento (Mensal)"):
    """Cria um gráfico de área empilhada mostrando a evolução dos métodos de pagamento."""
    if df.empty or 'AnoMês' not in df.columns or not any(col in df.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
        st.info("Dados insuficientes para gerar o gráfico de Evolução de Pagamento.")
        return None

    monthly_payments = df.groupby('AnoMês')[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
    monthly_payments_long = monthly_payments.melt(
        id_vars=['AnoMês'],
        value_vars=['Cartão', 'Dinheiro', 'Pix'],
        var_name='Método',
        value_name='Valor'
    )
    monthly_payments_long = monthly_payments_long[monthly_payments_long['Valor'] > 0]
    
    if monthly_payments_long.empty:
        st.info("Nenhum dado de pagamento encontrado no período para gerar o gráfico.")
        return None

    area_chart = alt.Chart(monthly_payments_long).mark_area().encode(
        x=alt.X('AnoMês', title='Mês/Ano', axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Valor:Q', title='Valor Total (R$)', stack='zero', axis=alt.Axis(format=",.2f")),
        color=alt.Color('Método:N', legend=alt.Legend(title="Método de Pagamento")),
        tooltip=[
            alt.Tooltip("AnoMês", title="Mês/Ano"),
            alt.Tooltip("Método", title="Método"),
            alt.Tooltip("Valor", title="Valor (R$)", format=",.2f")
        ]
    ).properties(
        title=title,
        height=600
    ).interactive()
    return area_chart

def create_sales_histogram(df, title="Distribuição dos Valores de Venda Diários"):
    """Cria um histograma da distribuição dos valores totais de venda diários."""
    if df.empty or 'Total' not in df.columns:
        st.info("Dados insuficientes para gerar o Histograma de Vendas.")
        return None
    
    df_filtered_hist = df[df['Total'] > 0]

    if df_filtered_hist.empty:
        st.info("Nenhuma venda com valor maior que zero encontrada para gerar o histograma.")
        return None

    histogram = alt.Chart(df_filtered_hist).mark_bar().encode(
        alt.X("Total:Q", bin=alt.Bin(maxbins=20), title="Faixa de Valor da Venda Diária (R$)"),
        alt.Y('count()', title='Número de Dias (Frequência)'),
        tooltip=[
            alt.Tooltip("Total:Q", bin=True, title="Faixa de Valor (R$)"),
            alt.Tooltip("count()", title="Número de Dias")
        ]
    ).properties(
        title=title,
        height=600
    ).interactive()
    return histogram

# --- Funções de Análise Textual ---
def analyze_sales_by_weekday(df):
    """Calcula a média de vendas por dia da semana e encontra o dia com maior média."""
    if df.empty or 'DiaSemana' not in df.columns or 'Total' not in df.columns:
        return None, None

    try:
        # Calcula a média de vendas por dia da semana, tratando valores não numéricos
        df_copy = df.copy()
        df_copy['Total'] = pd.to_numeric(df_copy['Total'], errors='coerce')
        df_copy.dropna(subset=['Total'], inplace=True)
        
        if df_copy.empty:
             return None, None
             
        avg_sales_weekday = df_copy.groupby('DiaSemana', observed=False)['Total'].mean().reindex(dias_semana_ordem)

        # Verifica se há valores não nulos para calcular o máximo
        if avg_sales_weekday.notna().any():
            best_day = avg_sales_weekday.idxmax()
            # Verifica se o melhor dia realmente tem um valor (não é NaN)
            if pd.notna(avg_sales_weekday[best_day]):
                 return best_day, avg_sales_weekday
            else:
                 return None, avg_sales_weekday # Retorna médias, mas sem melhor dia definido
        else:
            # Retorna None para best_day se todas as médias forem NaN
            return None, avg_sales_weekday
            
    except Exception as e:
        st.error(f"Erro ao analisar vendas por dia da semana: {e}")
        return None, None

# --- Interface Principal da Aplicação ---
def main():
    st.title("📊 Sistema de Registro de Vendas")

    df_raw = read_sales_data()
    # Só processa se df_raw não for None e não estiver vazio
    df_processed = process_data(df_raw) if df_raw is not None and not df_raw.empty else pd.DataFrame()

    # Define as abas - Removida a aba "Novas Análises"
    tab1, tab2, tab3 = st.tabs(["Registrar Venda", "Análise Detalhada", "Estatísticas"])

    with tab1:
        st.header("Registrar Nova Venda")
        with st.form("venda_form"):
            data_input = st.date_input("Data", datetime.now())
            col1, col2, col3 = st.columns(3)
            with col1:
                cartao_input = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f")
            with col2:
                dinheiro_input = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f")
            with col3:
                pix_input = st.number_input("PIX (R$)", min_value=0.0, format="%.2f")

            total_venda_form = cartao_input + dinheiro_input + pix_input
            st.markdown(f"**Total da venda: R$ {total_venda_form:.2f}**")
            submitted = st.form_submit_button("Registrar Venda")

            if submitted:
                if total_venda_form > 0:
                    formatted_date = data_input.strftime('%d/%m/%Y')
                    worksheet_obj = get_worksheet()
                    if add_data_to_sheet(formatted_date, cartao_input, dinheiro_input, pix_input, worksheet_obj):
                        read_sales_data.clear()
                        process_data.clear()
                        st.success("Venda registrada! Recarregando dados...")
                        st.rerun()
                else:
                    st.warning("Pelo menos um valor de venda deve ser maior que zero.")

    # --- Filtros na Sidebar ---
    selected_anos_filter = []
    selected_meses_filter = []

    with st.sidebar:
        st.header("🔍 Filtros")
        # Verifica se df_processed existe e não está vazio antes de acessar colunas
        if df_processed is not None and not df_processed.empty and 'Ano' in df_processed.columns and not df_processed['Ano'].dropna().empty:
            current_month = datetime.now().month
            current_year = datetime.now().year
            anos_disponiveis = sorted(df_processed['Ano'].dropna().unique().astype(int))
            default_anos = [current_year] if current_year in anos_disponiveis else anos_disponiveis
            selected_anos_filter = st.multiselect("Selecione o(s) Ano(s):", options=anos_disponiveis, default=default_anos)

            if selected_anos_filter:
                df_para_filtro_mes = df_processed[df_processed['Ano'].isin(selected_anos_filter)]
                if not df_para_filtro_mes.empty and 'Mês' in df_para_filtro_mes.columns and not df_para_filtro_mes['Mês'].dropna().empty:
                    meses_numeros_disponiveis = sorted(df_para_filtro_mes['Mês'].dropna().unique().astype(int))
                    meses_nomes_map = {m: datetime(2000, m, 1).strftime('%B').capitalize() for m in meses_numeros_disponiveis}
                    meses_opcoes = [f"{m} - {meses_nomes_map[m]}" for m in meses_numeros_disponiveis if m in meses_nomes_map]
                    default_mes_opcao_str = f"{current_month} - {datetime(2000, current_month, 1).strftime('%B').capitalize()}"
                    default_meses_selecionados = [default_mes_opcao_str] if default_mes_opcao_str in meses_opcoes else meses_opcoes
                    selected_meses_str = st.multiselect("Selecione o(s) Mês(es):", options=meses_opcoes, default=default_meses_selecionados)
                    selected_meses_filter = [int(m.split(" - ")[0]) for m in selected_meses_str]
        else:
            st.sidebar.info("Não há dados processados ou coluna 'Ano' para aplicar filtros.")

    # Aplicar filtros
    df_filtered = df_processed.copy() if df_processed is not None else pd.DataFrame()
    if not df_filtered.empty:
        if selected_anos_filter and 'Ano' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos_filter)]
        if selected_meses_filter and 'Mês' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses_filter)]
    else:
        # Não mostra warning se df_processed for None (erro de credenciais)
        if df_processed is not None:
             st.warning("Não há dados processados para filtrar.")

    # --- Aba de Análise Detalhada ---
    with tab2:
        st.header("Análise Detalhada de Vendas")
        if not df_filtered.empty and 'DataFormatada' in df_filtered.columns:
            st.subheader("Dados Filtrados")
            st.dataframe(df_filtered[['DataFormatada', 'DiaSemana', 'MêsNome', 'Cartão', 'Dinheiro', 'Pix', 'Total']], use_container_width=True, height=300)
            
            st.subheader("Distribuição por Método de Pagamento (Filtrado)")
            payment_filtered_data = pd.DataFrame({
                'Método': ['Cartão', 'Dinheiro', 'PIX'],
                'Valor': [df_filtered['Cartão'].sum(), df_filtered['Dinheiro'].sum(), df_filtered['Pix'].sum()]
            })
            payment_filtered_data = payment_filtered_data[payment_filtered_data['Valor'] > 0]
            if not payment_filtered_data.empty:
                pie_chart = alt.Chart(payment_filtered_data).mark_arc().encode(
                    theta=alt.Theta("Valor:Q", stack=True),
                    color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
                    tooltip=["Método", alt.Tooltip("Valor", format=",.2f")]
                ).properties(
                    height=500,
                    width=500
                ).interactive()
                st.altair_chart(pie_chart, use_container_width=True)
            else:
                 st.info("Sem dados de pagamento para exibir o gráfico de pizza nos filtros selecionados.")

            st.subheader("Vendas Diárias por Método de Pagamento (Filtrado)")
            if not df_filtered.empty and 'Data' in df_filtered.columns:
                df_filtered_sorted = df_filtered.sort_values('Data')
                daily_data = df_filtered_sorted.melt(id_vars=['Data', 'DataFormatada'], value_vars=['Cartão', 'Dinheiro', 'Pix'], var_name='Método', value_name='Valor')
                daily_data = daily_data[daily_data['Valor'] > 0]
                if not daily_data.empty:
                    bar_chart = alt.Chart(daily_data).mark_bar(size=15).encode(
                        x=alt.X('Data:T', title='Data', axis=alt.Axis(format="%d/%m/%Y", labelAngle=-45)),
                        y=alt.Y('Valor:Q', title='Valor (R$)', axis=alt.Axis(format=",.2f")),
                        color=alt.Color('Método:N', legend=alt.Legend(title="Método")),
                        tooltip=["DataFormatada", "Método", alt.Tooltip("Valor", format=",.2f")]
                    ).properties(height=700).interactive()
                    st.altair_chart(bar_chart, use_container_width=True)
                else:
                    st.info("Sem dados de vendas diárias para exibir o gráfico de barras nos filtros selecionados.")
            else:
                 st.info("Coluna 'Data' necessária para o gráfico de vendas diárias.")

            st.subheader("Acúmulo de Capital ao Longo do Tempo (Filtrado)")
            if 'Data' in df_filtered.columns and not df_filtered.empty:
                df_accumulated = df_filtered.sort_values('Data').copy()
                df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()

                # Cria o gráfico de barras para os valores diários
                bar_chart = alt.Chart(df_accumulated).mark_bar().encode(
                    x=alt.X('Data:T', title='Data', axis=alt.Axis(format="%d/%m/%Y")),
                    y=alt.Y('Total:Q', title='Valor Diário (R$)'),
                    tooltip=["DataFormatada", alt.Tooltip("Total", format=",.2f")]
                ).properties(height=700)

                # Cria o gráfico de linha para o total acumulado
                line_chart = alt.Chart(df_accumulated).mark_line(point=True, strokeWidth=2, color='red').encode(
                    x=alt.X('Data:T', title='Data', axis=alt.Axis(format="%d/%m/%Y")),
                    y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
                    tooltip=["DataFormatada", alt.Tooltip("Total Acumulado", format=",.2f")]
                ).properties(height=700)

                # Sobrepõe os gráficos de barras e linha
                combined_chart = alt.layer(bar_chart, line_chart).resolve_scale(y='independent')
                st.altair_chart(combined_chart, use_container_width=True)
            else:
                st.info("Coluna 'Data' não encontrada ou dados insuficientes para gráfico de acúmulo.")
        else:
            st.info("Não há dados para exibir na Análise Detalhada com os filtros selecionados ou o DataFrame está vazio.")

    # --- Aba de Estatísticas (Agora inclui as novas análises) ---
    with tab3:
        st.header("📊 Estatísticas e Análises de Vendas (Filtrado)")
        
        # Verifica se há dados filtrados para exibir estatísticas
        if not df_filtered.empty and 'Total' in df_filtered.columns:
            st.subheader("💰 Resumo Financeiro")
            total_vendas = len(df_filtered)
            total_faturamento = df_filtered['Total'].sum()
            media_por_venda = df_filtered['Total'].mean() if total_vendas > 0 else 0
            maior_venda = df_filtered['Total'].max() if total_vendas > 0 else 0
            menor_venda = df_filtered[df_filtered['Total'] > 0]['Total'].min() if (df_filtered['Total'] > 0).any() else 0

            col1, col2 = st.columns(2)
            col1.metric("🔢 Total de Registros (Dias com Venda)", f"{total_vendas}")
            col2.metric("💵 Faturamento Total", f"R$ {total_faturamento:,.2f}")
            col3, col4 = st.columns(2)
            col3.metric("📈 Média por Registro", f"R$ {media_por_venda:,.2f}")
            col4.metric("⬆️ Maior Venda Diária", f"R$ {maior_venda:,.2f}")
            col5, col6 = st.columns(2)
            col5.metric("⬇️ Menor Venda Diária (>0)", f"R$ {menor_venda:,.2f}")

            st.divider()
            st.subheader("💳 Métodos de Pagamento")
            cartao_total = df_filtered['Cartão'].sum()
            dinheiro_total = df_filtered['Dinheiro'].sum()
            pix_total = df_filtered['Pix'].sum()
            total_pagamentos = cartao_total + dinheiro_total + pix_total

            if total_pagamentos > 0:
                cartao_pct = (cartao_total / total_pagamentos * 100)
                dinheiro_pct = (dinheiro_total / total_pagamentos * 100)
                pix_pct = (pix_total / total_pagamentos * 100)

                payment_cols = st.columns(3)
                payment_cols[0].metric("💳 Cartão", f"R$ {cartao_total:,.2f}", f"{cartao_pct:.1f}%")
                payment_cols[1].metric("💵 Dinheiro", f"R$ {dinheiro_total:,.2f}", f"{dinheiro_pct:.1f}%")
                payment_cols[2].metric("📱 PIX", f"R$ {pix_total:,.2f}", f"{pix_pct:.1f}%")

                payment_data_stats = pd.DataFrame({'Método': ['Cartão', 'Dinheiro', 'PIX'], 'Valor': [cartao_total, dinheiro_total, pix_total]})
                payment_data_stats = payment_data_stats[payment_data_stats['Valor'] > 0]
                if not payment_data_stats.empty:
                    pie_chart_stats = alt.Chart(payment_data_stats).mark_arc().encode(
                        theta=alt.Theta("Valor:Q", stack=True),
                        color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
                        tooltip=["Método", alt.Tooltip("Valor", format=",.2f")]
                    ).properties(
                        height=500,
                        width=500
                    ).interactive()
                    st.altair_chart(pie_chart_stats, use_container_width=True)
                else:
                    st.info("Sem dados de pagamento para o gráfico de pizza nesta seção.")
            else:
                st.info("Sem dados de pagamento para exibir nesta seção.")

            st.divider()
            st.subheader("📅 Análise Temporal e Desempenho Semanal")
            
            # Análise textual por dia da semana
            best_weekday, avg_sales_weekday = analyze_sales_by_weekday(df_filtered)
            
            if avg_sales_weekday is not None:
                if best_weekday and pd.notna(avg_sales_weekday[best_weekday]):
                    st.success(f"🏆 **Melhor Dia da Semana:** {best_weekday} - Média: R$ {avg_sales_weekday[best_weekday]:,.2f}")
                else:
                    st.warning("⚠️ Não foi possível determinar o melhor dia da semana (dados insuficientes)")
                
                st.markdown("### 📊 Média de Vendas por Dia da Semana")
                
                # Criar colunas para exibir as médias de forma organizada
                cols = st.columns(2)
                col_idx = 0
                
                for day, avg_sale in avg_sales_weekday.items():
                    with cols[col_idx % 2]:
                        if pd.notna(avg_sale):
                            st.metric(
                                label=f"📅 {day}",
                                value=f"R$ {avg_sale:,.2f}",
                                delta=None
                            )
                        else:
                            st.metric(
                                label=f"📅 {day}",
                                value="Sem dados",
                                delta=None
                            )
                    col_idx += 1
            else:
                st.info("📊 Dados insuficientes para calcular a média de vendas por dia da semana.")
            
            # Gráficos movidos para cá
            st.divider()
            st.subheader("🔥 Mapa de Calor: Total de Vendas (Dia da Semana x Mês)")
            heatmap_chart = create_heatmap(df_filtered)
            if heatmap_chart:
                st.altair_chart(heatmap_chart, use_container_width=True)
            
            st.divider()
            st.subheader("📈 Evolução da Preferência por Pagamento (Mensal)")
            payment_evolution_chart = create_payment_evolution_chart(df_filtered)
            if payment_evolution_chart:
                st.altair_chart(payment_evolution_chart, use_container_width=True)

            st.divider()
            st.subheader("📊 Distribuição dos Valores de Venda Diários (Histograma)")
            sales_histogram_chart = create_sales_histogram(df_filtered)
            if sales_histogram_chart:
                st.altair_chart(sales_histogram_chart, use_container_width=True)

        else:
            # Mensagem se não houver dados filtrados ou processados
            st.info("Não há dados para exibir nas Estatísticas com os filtros selecionados ou o DataFrame inicial está vazio/inválido.")

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    main()