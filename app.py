import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import locale
import numpy as np

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
WORKSHEET_NAME = 'Vendas'

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="centered") # Alterado para layout="wide"

# Configura o locale para Português do Brasil para formatação de datas e nomes
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    st.warning("Locale pt_BR.UTF-8 não encontrado. Nomes de meses/dias podem aparecer em inglês.")

# --- Funções de Cache para Acesso ao Google Sheets ---
@st.cache_resource
def get_google_auth():
    """Autoriza o acesso ao Google Sheets e retorna o cliente gspread."""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/spreadsheets.readonly',
              'https://www.googleapis.com/auth/drive.readonly']
    try:
        credentials_dict = st.secrets["google_credentials"]
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
            # Tratamento para colunas que podem vir como string vazia e deveriam ser numéricas
            for col_num in ['Cartão', 'Dinheiro', 'Pix']:
                if col_num in df.columns:
                    df[col_num] = pd.to_numeric(df[col_num], errors='coerce').fillna(0)
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
                    df['DiaSemana'] = df['Data'].dt.strftime('%A').str.capitalize()
                    df['SemanaAno'] = df['Data'].dt.isocalendar().week
                else:
                    st.warning("Nenhuma data válida encontrada após conversão inicial.")
            except Exception as e:
                st.error(f"Erro ao processar a coluna 'Data': {e}")
                for col_date_derived in ['Ano', 'Mês', 'MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana', 'SemanaAno']:
                    if col_date_derived not in df.columns:
                         df[col_date_derived] = None 
    return df

# --- Funções de Comparação de Período ---
def get_previous_period_data(df, current_year, current_month, comparison_type):
    if df.empty or 'Data' not in df.columns:
        return pd.DataFrame()

    if comparison_type == "Mês Anterior":
        prev_date = datetime(current_year, current_month, 1) - relativedelta(months=1)
        prev_year, prev_month = prev_date.year, prev_date.month
        return df[(df['Ano'] == prev_year) & (df['Mês'] == prev_month)]
    elif comparison_type == "Ano Anterior (mesmo mês)":
        prev_year = current_year - 1
        return df[(df['Ano'] == prev_year) & (df['Mês'] == current_month)]
    return pd.DataFrame()

# --- Interface Principal da Aplicação ---
def main():
    st.title("📊 Sistema de Registro e Análise Avançada de Vendas")
    
    df_raw = read_sales_data()
    df_processed = process_data(df_raw) if not df_raw.empty else pd.DataFrame()

    tab1, tab2, tab3, tab4 = st.tabs(["Registrar Venda", "Análise Detalhada", "Estatísticas Gerais", "Análise Comparativa e Avançada"]) # Nova aba

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
                        st.experimental_rerun()
                else:
                    st.warning("Pelo menos um valor de venda deve ser maior que zero.")

    # --- Filtros na Sidebar (afetam Tab2, Tab3, Tab4) ---
    selected_anos_filter = []
    selected_meses_filter = []
    comparison_period_option = "Nenhum"

    with st.sidebar:
        st.header("🔍 Filtros Principais")
        if not df_processed.empty and 'Ano' in df_processed.columns and not df_processed['Ano'].dropna().empty:
            current_month_dt = datetime.now().month
            current_year_dt = datetime.now().year
            
            anos_disponiveis = sorted(df_processed['Ano'].dropna().unique().astype(int))
            default_anos = [current_year_dt] if current_year_dt in anos_disponiveis else anos_disponiveis
            selected_anos_filter = st.multiselect("Selecione o(s) Ano(s):", options=anos_disponiveis, default=default_anos)

            if selected_anos_filter:
                df_para_filtro_mes = df_processed[df_processed['Ano'].isin(selected_anos_filter)]
                if not df_para_filtro_mes.empty and 'Mês' in df_para_filtro_mes.columns and not df_para_filtro_mes['Mês'].dropna().empty:
                    meses_numeros_disponiveis = sorted(df_para_filtro_mes['Mês'].dropna().unique().astype(int))
                    meses_nomes_map = {m: datetime(2000, m, 1).strftime('%B').capitalize() for m in meses_numeros_disponiveis}
                    meses_opcoes = [f"{m} - {meses_nomes_map[m]}" for m in meses_numeros_disponiveis]
                    
                    default_mes_opcao_str = f"{current_month_dt} - {datetime(2000, current_month_dt, 1).strftime('%B').capitalize()}"
                    # Selecionar o mês atual do ano mais recente selecionado por padrão
                    if selected_anos_filter and max(selected_anos_filter) == current_year_dt:
                         default_meses_selecionados = [default_mes_opcao_str] if default_mes_opcao_str in meses_opcoes else meses_opcoes if not meses_opcoes else [meses_opcoes[0]]
                    else:
                        default_meses_selecionados = meses_opcoes if not meses_opcoes else [meses_opcoes[0]]

                    selected_meses_str = st.multiselect("Selecione o(s) Mês(es):", options=meses_opcoes, default=default_meses_selecionados)
                    selected_meses_filter = [int(m.split(" - ")[0]) for m in selected_meses_str]
            
            st.header("📅 Filtro de Comparação")
            comparison_period_option = st.selectbox(
                "Comparar com:", 
                ["Nenhum", "Mês Anterior", "Ano Anterior (mesmo mês)"]
            )

        else:
            st.sidebar.info("Não há dados suficientes para aplicar filtros de data.")

    # Aplicar filtros principais aos dados processados
    df_filtered_main = df_processed.copy()
    if not df_filtered_main.empty:
        if selected_anos_filter and 'Ano' in df_filtered_main.columns:
            df_filtered_main = df_filtered_main[df_filtered_main['Ano'].isin(selected_anos_filter)]
        if selected_meses_filter and 'Mês' in df_filtered_main.columns:
            df_filtered_main = df_filtered_main[df_filtered_main['Mês'].isin(selected_meses_filter)]
    
    # --- Aba de Análise Detalhada ---
    with tab2:
        st.header("Análise Detalhada de Vendas (Período Selecionado)")
        if not df_filtered_main.empty and 'DataFormatada' in df_filtered_main.columns:
            st.subheader("Dados Filtrados")
            st.dataframe(df_filtered_main[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']].sort_values(by='DataFormatada'), use_container_width=True, height=300)

            col_विश्1, col_विश्2 = st.columns(2)
            with col_विश्1:
                st.subheader("Distribuição por Método de Pagamento")
                payment_filtered_data = pd.DataFrame({
                    'Método': ['Cartão', 'Dinheiro', 'PIX'],
                    'Valor': [df_filtered_main['Cartão'].sum(), df_filtered_main['Dinheiro'].sum(), df_filtered_main['Pix'].sum()]
                })
                pie_chart = alt.Chart(payment_filtered_data).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta("Valor:Q", stack=True),
                    color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
                    tooltip=["Método", alt.Tooltip("Valor:Q", format=",.2f")]
                ).properties(height=350)
                text_pie = pie_chart.mark_text(radius=100, size=14).encode(text=alt.condition(alt.datum.Valor > 0, alt.Text("Valor:Q", format=",.0f"), alt.value("")))
                st.altair_chart(pie_chart + text_pie, use_container_width=True)
            
            with col_विश्2:
                st.subheader("Acúmulo de Capital ao Longo do Tempo")
                if 'Data' in df_filtered_main.columns:
                    df_accumulated = df_filtered_main.sort_values('Data').copy()
                    df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()
                    line_chart = alt.Chart(df_accumulated).mark_line(point=True, strokeWidth=3).encode(
                        x=alt.X('Data:T', title='Data'),
                        y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
                        tooltip=['DataFormatada', alt.Tooltip('Total Acumulado:Q', format=",.2f")]
                    ).properties(height=350)
                    st.altair_chart(line_chart, use_container_width=True)

            st.subheader("Vendas Diárias por Método de Pagamento")
            daily_data = df_filtered_main.melt(id_vars=['DataFormatada', 'Data'], value_vars=['Cartão', 'Dinheiro', 'Pix'], var_name='Método', value_name='Valor')
            bar_chart = alt.Chart(daily_data).mark_bar(size=15).encode(
                x=alt.X('Data:T', title='Data', axis=alt.Axis(labelAngle=-45, format="%d/%m")),
                y=alt.Y('Valor:Q', title='Valor (R$)'),
                color=alt.Color('Método:N', legend=alt.Legend(title="Método")),
                tooltip=['DataFormatada', 'Método', alt.Tooltip('Valor:Q', format=",.2f")]
            ).properties(height=400)
            st.altair_chart(bar_chart, use_container_width=True)

        else:
            st.info("Não há dados para exibir na Análise Detalhada para o período selecionado.")

    # --- Aba de Estatísticas Gerais ---
    with tab3:
        st.header("📊 Estatísticas Gerais (Período Selecionado)")
        if not df_filtered_main.empty and 'Total' in df_filtered_main.columns:
            total_vendas = len(df_filtered_main)
            total_faturamento = df_filtered_main['Total'].sum()
            media_por_venda = df_filtered_main['Total'].mean() if total_vendas > 0 else 0
            maior_venda = df_filtered_main['Total'].max() if total_vendas > 0 else 0
            menor_venda = df_filtered_main['Total'].min() if total_vendas > 0 and df_filtered_main['Total'].min() > 0 else (df_filtered_main[df_filtered_main['Total']>0]['Total'].min() if not df_filtered_main[df_filtered_main['Total']>0].empty else 0) 
            
            # Para deltas em st.metric, precisamos de dados do período anterior
            # Esta é uma simplificação, idealmente viria de uma função de comparação mais robusta
            delta_faturamento = None
            delta_vendas = None
            if selected_anos_filter and selected_meses_filter and comparison_period_option != "Nenhum":
                # Supondo que o filtro principal seleciona apenas UM ano e UM mês para comparação simples
                if len(selected_anos_filter) == 1 and len(selected_meses_filter) == 1:
                    df_prev_period_simple = get_previous_period_data(df_processed, selected_anos_filter[0], selected_meses_filter[0], comparison_period_option)
                    if not df_prev_period_simple.empty:
                        prev_faturamento = df_prev_period_simple['Total'].sum()
                        prev_vendas = len(df_prev_period_simple)
                        delta_faturamento = total_faturamento - prev_faturamento
                        delta_vendas = total_vendas - prev_vendas
            
            st.subheader("💰 Resumo Financeiro")
            cols1_stats, cols2_stats = st.columns(2)
            cols1_stats.metric("🔢 Total de Vendas", f"{total_vendas}", delta=f"{delta_vendas}" if delta_vendas is not None else None)
            cols1_stats.metric("💵 Faturamento Total", f"R$ {total_faturamento:,.2f}", delta=f"R$ {delta_faturamento:,.2f}" if delta_faturamento is not None else None)
            cols2_stats.metric("📈 Média por Venda", f"R$ {media_por_venda:,.2f}")
            cols2_stats.metric("⬆️ Maior Venda", f"R$ {maior_venda:,.2f}")
            cols2_stats.metric("⬇️ Menor Venda (acima de 0)", f"R$ {menor_venda:,.2f}")

            st.markdown("---")
            st.subheader("💳 Métodos de Pagamento")
            # ... (código de métodos de pagamento similar ao anterior, usando df_filtered_main)
            cartao_total = df_filtered_main['Cartão'].sum()
            dinheiro_total = df_filtered_main['Dinheiro'].sum()
            pix_total = df_filtered_main['Pix'].sum()
            total_pagamentos = cartao_total + dinheiro_total + pix_total
            cartao_pct = (cartao_total / total_pagamentos * 100) if total_pagamentos > 0 else 0
            dinheiro_pct = (dinheiro_total / total_pagamentos * 100) if total_pagamentos > 0 else 0
            pix_pct = (pix_total / total_pagamentos * 100) if total_pagamentos > 0 else 0

            payment_cols = st.columns(3)
            payment_cols[0].markdown(f"**💳 Cartão:** R$ {cartao_total:.2f} ({cartao_pct:.1f}%)")
            payment_cols[1].markdown(f"**💵 Dinheiro:** R$ {dinheiro_total:.2f} ({dinheiro_pct:.1f}%)")
            payment_cols[2].markdown(f"**📱 PIX:** R$ {pix_total:.2f} ({pix_pct:.1f}%)")

            if total_pagamentos > 0:
                payment_data_stats = pd.DataFrame({'Método': ['Cartão', 'Dinheiro', 'PIX'], 'Valor': [cartao_total, dinheiro_total, pix_total]})
                pie_chart_stats = alt.Chart(payment_data_stats).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta("Valor:Q", stack=True), color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
                    tooltip=["Método", alt.Tooltip("Valor:Q", format=",.2f")]
                ).properties(height=350)
                text_stats_pie = pie_chart_stats.mark_text(radius=100, size=14).encode(text=alt.condition(alt.datum.Valor > 0, alt.Text("Valor:Q", format=",.0f"), alt.value("")))
                st.altair_chart(pie_chart_stats + text_stats_pie, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📅 Análise Temporal Básica")
            if total_vendas > 1 and 'Data' in df_filtered_main.columns and 'DiaSemana' in df_filtered_main.columns:
                metodo_preferido = "Cartão" if cartao_total >= max(dinheiro_total, pix_total) else \
                                  "Dinheiro" if dinheiro_total >= max(cartao_total, pix_total) else "PIX"
                emoji_metodo = "💳" if metodo_preferido == "Cartão" else "💵" if metodo_preferido == "Dinheiro" else "📱"
                
                stats_cols_temporal = st.columns(3)
                stats_cols_temporal[0].markdown(f"**{emoji_metodo} Método Preferido:** {metodo_preferido}")
                
                dias_distintos = df_filtered_main['Data'].nunique()
                media_diaria = total_faturamento / dias_distintos if dias_distintos > 0 else 0
                stats_cols_temporal[1].markdown(f"**📊 Média Diária:** R$ {media_diaria:.2f}")
                
                if not df_filtered_main.empty and not df_filtered_main['DiaSemana'].dropna().empty:
                    dia_mais_vendas = df_filtered_main.groupby('DiaSemana')['Total'].sum().idxmax()
                    stats_cols_temporal[2].markdown(f"**📆 Dia com Mais Vendas (Volume):** {dia_mais_vendas}")
                else:
                    stats_cols_temporal[2].markdown("**📆 Dia com Mais Vendas (Volume):** N/A")
        else:
            st.info("Não há dados para exibir na aba Estatísticas para o período selecionado.")

    # --- Aba de Análise Comparativa e Avançada ---
    with tab4:
        st.header("🔬 Análise Comparativa e Estatísticas Avançadas")

        if df_filtered_main.empty:
            st.info("Selecione um período com dados para visualizações avançadas.")
        else:
            # Comparação de Períodos
            if comparison_period_option != "Nenhum" and selected_anos_filter and selected_meses_filter:
                # Supondo que o filtro principal seleciona apenas UM ano e UM mês para comparação
                if len(selected_anos_filter) == 1 and len(selected_meses_filter) == 1:
                    current_period_label = f"{selected_meses_filter[0]}/{selected_anos_filter[0]}"
                    df_previous_period = get_previous_period_data(df_processed, selected_anos_filter[0], selected_meses_filter[0], comparison_period_option)
                    
                    st.subheader(f"Comparativo: {current_period_label} vs. {comparison_period_option}")
                    if not df_previous_period.empty:
                        fat_atual = df_filtered_main['Total'].sum()
                        fat_anterior = df_previous_period['Total'].sum()
                        var_fat = ((fat_atual - fat_anterior) / fat_anterior * 100) if fat_anterior > 0 else float('inf') if fat_atual > 0 else 0
                        
                        col_comp1, col_comp2 = st.columns(2)
                        col_comp1.metric(f"Faturamento {current_period_label}", f"R$ {fat_atual:,.2f}")
                        col_comp2.metric(f"Faturamento {comparison_period_option}", f"R$ {fat_anterior:,.2f}", delta=f"{var_fat:.1f}%" if var_fat != float('inf') else "N/A (anterior=0)")
                        
                        # Gráfico comparativo de faturamento por dia (exemplo)
                        df_comp_chart_curr = df_filtered_main.groupby(df_filtered_main['Data'].dt.day)['Total'].sum().reset_index().rename(columns={'Total': 'Atual', 'Data':'Dia'})
                        df_comp_chart_prev = df_previous_period.groupby(df_previous_period['Data'].dt.day)['Total'].sum().reset_index().rename(columns={'Total': 'Anterior', 'Data':'Dia'})
                        
                        df_comp_chart = pd.merge(df_comp_chart_curr, df_comp_chart_prev, on='Dia', how='outer').fillna(0)
                        df_comp_chart_melted = df_comp_chart.melt(id_vars='Dia', value_vars=['Atual', 'Anterior'], var_name='Período', value_name='Faturamento')

                        comp_bar_chart = alt.Chart(df_comp_chart_melted).mark_bar(opacity=0.7).encode(
                            x=alt.X('Dia:O', title='Dia do Mês'),
                            y=alt.Y('Faturamento:Q', title='Faturamento (R$)'),
                            color='Período:N',
                            tooltip=['Dia', 'Período', alt.Tooltip('Faturamento:Q', format=",.2f")],
                            xOffset='Período:N'
                        ).properties(
                            title=f'Comparativo Diário de Faturamento: {current_period_label} vs. {comparison_period_option}',
                            height=350
                        )
                        st.altair_chart(comp_bar_chart, use_container_width=True)
                    else:
                        st.warning(f"Não há dados para o período de comparação ({comparison_period_option}).")
                else:
                    st.warning("Para comparação, selecione apenas um único mês e ano no filtro principal.")
            else:
                st.info("Selecione um período de comparação na barra lateral para visualizar análises comparativas.")
            
            st.markdown("---")
            st.subheader("📊 Distribuição de Vendas (Período Selecionado)")
            # Box Plot
            if not df_filtered_main.empty and 'Total' in df_filtered_main.columns:
                box_plot = alt.Chart(df_filtered_main).mark_boxplot(extent='min-max').encode(
                    y=alt.Y('Total:Q', title='Valor da Venda (R$)'),
                    tooltip=[alt.Tooltip('Total:Q', format=",.2f")]
                ).properties(
                    title='Distribuição dos Valores de Venda',
                    width=200, height=350
                )
                # Histograma
                hist_dist = alt.Chart(df_filtered_main).mark_bar().encode(
                    alt.X('Total:Q', bin=alt.Bin(maxbins=20), title='Valor da Venda (R$)'),
                    alt.Y('count()', title='Frequência')
                ).properties(title='Histograma dos Valores de Venda', height=350)
                
                col_dist1, col_dist2 = st.columns([1,2])
                with col_dist1:
                    st.altair_chart(box_plot, use_container_width=True)
                with col_dist2:
                    st.altair_chart(hist_dist, use_container_width=True)

                # Estatísticas Descritivas
                st.markdown("**Estatísticas Descritivas do Valor Total da Venda:**")
                desc_stats = df_filtered_main['Total'].describe().drop('count') # Drop count as it's shown elsewhere
                st.table(desc_stats.apply(lambda x: f"R$ {x:,.2f}"))
                st.markdown(f"**Mediana:** R$ {df_filtered_main['Total'].median():,.2f}")
                st.markdown(f"**Amplitude Interquartil (IQR):** R$ {(df_filtered_main['Total'].quantile(0.75) - df_filtered_main['Total'].quantile(0.25)):,.2f}")

if __name__ == "__main__":
    main()

