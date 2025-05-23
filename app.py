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

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="centered")

# Configura o locale para Português do Brasil para formatação de datas e nomes
#try:
   # locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
#except locale.Error:
    #st.warning("Locale pt_BR.UTF-8 não encontrado. Nomes de meses/dias podem aparecer em inglês.")

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
                df[col] = 0 # Adiciona coluna se não existir para evitar erros
        
        df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']
        
        if 'Data' in df.columns:
            try:
                df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
                df.dropna(subset=['Data'], inplace=True) # Remove linhas onde a data não pôde ser convertida
                
                if not df.empty:
                    df['Ano'] = df['Data'].dt.year
                    df['Mês'] = df['Data'].dt.month
                    df['MêsNome'] = df['Data'].dt.strftime('%B').str.capitalize()
                    df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                    df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                    # Usar strftime('%A') para nome do dia da semana de acordo com o locale
                    df['DiaSemana'] = df['Data'].dt.strftime('%A').str.capitalize()
                else:
                    st.warning("Nenhuma data válida encontrada após conversão inicial.")

            except Exception as e: # Alterado para Exception genérica após pd.to_datetime
                st.error(f"Erro ao processar a coluna 'Data': {e}")
                # Retornar colunas básicas mesmo em caso de erro para evitar quebras
                for col_date_derived in ['Ano', 'Mês', 'MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana']:
                    if col_date_derived not in df.columns:
                         df[col_date_derived] = None 
    return df

# --- Interface Principal da Aplicação ---
def main():
    st.title("📊 Sistema de Registro de Vendas")
    
    # Carrega os dados uma vez para uso nas abas
    df_raw = read_sales_data()
    df_processed = process_data(df_raw) if not df_raw.empty else pd.DataFrame()

    tab1, tab2, tab3 = st.tabs(["Registrar Venda", "Análise Detalhada", "Estatística"])

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
                        read_sales_data.clear() # Limpa o cache dos dados de vendas
                        process_data.clear() # Limpa o cache dos dados processados
                        st.rerun() # Força o recarregamento da app para refletir novos dados
                else:
                    st.warning("Pelo menos um valor de venda deve ser maior que zero.")

    # Prepara dados para abas de análise e estatística
    # Filtros na sidebar (afetam Tab2 e Tab3)
    selected_anos_filter = []
    selected_meses_filter = []

    with st.sidebar:
        st.header("🔍 Filtros")
        if not df_processed.empty and 'Ano' in df_processed.columns and not df_processed['Ano'].dropna().empty:
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            anos_disponiveis = sorted(df_processed['Ano'].dropna().unique().astype(int))
            default_anos = [current_year] if current_year in anos_disponiveis else anos_disponiveis
            selected_anos_filter = st.multiselect("Selecione o(s) Ano(s):", options=anos_disponiveis, default=default_anos)

            if selected_anos_filter:
                df_para_filtro_mes = df_processed[df_processed['Ano'].isin(selected_anos_filter)]
                if not df_para_filtro_mes.empty and 'Mês' in df_para_filtro_mes.columns and not df_para_filtro_mes['Mês'].dropna().empty:
                    meses_numeros_disponiveis = sorted(df_para_filtro_mes['Mês'].dropna().unique().astype(int))
                    # Gera nomes dos meses com base no locale
                    meses_nomes_map = {m: datetime(2000, m, 1).strftime('%B').capitalize() for m in meses_numeros_disponiveis}
                    meses_opcoes = [f"{m} - {meses_nomes_map[m]}" for m in meses_numeros_disponiveis]
                    
                    default_mes_opcao_str = f"{current_month} - {datetime(2000, current_month, 1).strftime('%B').capitalize()}"
                    default_meses_selecionados = [default_mes_opcao_str] if default_mes_opcao_str in meses_opcoes else meses_opcoes
                    
                    selected_meses_str = st.multiselect("Selecione o(s) Mês(es):", options=meses_opcoes, default=default_meses_selecionados)
                    selected_meses_filter = [int(m.split(" - ")[0]) for m in selected_meses_str]
        else:
            st.sidebar.info("Não há dados suficientes para aplicar filtros de data.")

    # Aplicar filtros aos dados processados
    df_filtered = df_processed.copy()
    if not df_filtered.empty:
        if selected_anos_filter and 'Ano' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos_filter)]
        if selected_meses_filter and 'Mês' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses_filter)]
    
    with tab2:
        st.header("Análise Detalhada de Vendas")
        if not df_filtered.empty and 'DataFormatada' in df_filtered.columns:
            st.subheader("Dados Filtrados")
            st.dataframe(df_filtered[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']], use_container_width=True, height=300)

            st.subheader("Distribuição por Método de Pagamento")
            payment_filtered_data = pd.DataFrame({
                'Método': ['Cartão', 'Dinheiro', 'PIX'],
                'Valor': [df_filtered['Cartão'].sum(), df_filtered['Dinheiro'].sum(), df_filtered['Pix'].sum()]
            })
            pie_chart = alt.Chart(payment_filtered_data).mark_arc(innerRadius=50).encode(
                theta=alt.Theta("Valor:Q", stack=True),
                color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
                tooltip=["Método", "Valor"]
            ).properties(width=700, height=500)
            text = pie_chart.mark_text(radius=120, size=16).encode(text="Valor:Q")
            st.altair_chart(pie_chart + text, use_container_width=True)

            st.subheader("Vendas Diárias por Método de Pagamento")
            daily_data = df_filtered.melt(id_vars=['DataFormatada'], value_vars=['Cartão', 'Dinheiro', 'Pix'], var_name='Método', value_name='Valor')
            bar_chart = alt.Chart(daily_data).mark_bar(size=20).encode(
                x=alt.X('DataFormatada:N', title='Data', axis=alt.Axis(labelAngle=-45), sort=alt.EncodingSortField(field="DataFormatada", op="min", order='ascending')),
                y=alt.Y('Valor:Q', title='Valor (R$)'),
                color=alt.Color('Método:N', legend=alt.Legend(title="Método")),
                tooltip=['DataFormatada', 'Método', 'Valor']
            ).properties(width=700, height=500)
            st.altair_chart(bar_chart, use_container_width=True)

            st.subheader("Acúmulo de Capital ao Longo do Tempo")
            if 'Data' in df_filtered.columns:
                df_accumulated = df_filtered.sort_values('Data').copy()
                df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()
                line_chart = alt.Chart(df_accumulated).mark_line(point=True, strokeWidth=3).encode(
                    x=alt.X('Data:T', title='Data'),
                    y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
                    tooltip=['DataFormatada', 'Total Acumulado']
                ).properties(width=700, height=500)
                st.altair_chart(line_chart, use_container_width=True)
            else:
                st.info("Coluna 'Data' não encontrada para gráfico de acúmulo.")
        else:
            st.info("Não há dados para exibir na Análise Detalhada ou os dados filtrados estão vazios.")

    with tab3:
        st.header("📊 Estatísticas de Vendas")
        if not df_filtered.empty and 'Total' in df_filtered.columns:
            st.subheader("💰 Resumo Financeiro")
            total_vendas = len(df_filtered)
            total_faturamento = df_filtered['Total'].sum()
            media_por_venda = df_filtered['Total'].mean() if total_vendas > 0 else 0
            maior_venda = df_filtered['Total'].max() if total_vendas > 0 else 0
            menor_venda = df_filtered['Total'].min() if total_vendas > 0 else 0

            cols1 = st.columns(2)
            cols1[0].metric("🔢 Total de Vendas", f"{total_vendas}")
            cols1[1].metric("💵 Faturamento Total", f"R$ {total_faturamento:,.2f}")
            cols2 = st.columns(2)
            cols2[0].metric("📈 Média por Venda", f"R$ {media_por_venda:,.2f}")
            cols2[1].metric("⬆️ Maior Venda", f"R$ {maior_venda:,.2f}")
            cols3 = st.columns(1)
            cols3[0].metric("⬇️ Menor Venda", f"R$ {menor_venda:,.2f}")

            st.markdown("---")
            st.subheader("💳 Métodos de Pagamento")
            cartao_total = df_filtered['Cartão'].sum()
            dinheiro_total = df_filtered['Dinheiro'].sum()
            pix_total = df_filtered['Pix'].sum()
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
                    tooltip=["Método", "Valor"]
                ).properties(height=500)
                text_stats = pie_chart_stats.mark_text(radius=120, size=16).encode(text="Valor:Q")
                st.altair_chart(pie_chart_stats + text_stats, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📅 Análise Temporal")
            if total_vendas > 1 and 'Data' in df_filtered.columns and 'DiaSemana' in df_filtered.columns:
                metodo_preferido = "Cartão" if cartao_total >= max(dinheiro_total, pix_total) else \
                                  "Dinheiro" if dinheiro_total >= max(cartao_total, pix_total) else "PIX"
                emoji_metodo = "💳" if metodo_preferido == "Cartão" else "💵" if metodo_preferido == "Dinheiro" else "📱"
                
                stats_cols_temporal = st.columns(3)
                stats_cols_temporal[0].markdown(f"**{emoji_metodo} Método Preferido:** {metodo_preferido}")
                
                dias_distintos = df_filtered['Data'].nunique()
                media_diaria = total_faturamento / dias_distintos if dias_distintos > 0 else 0
                stats_cols_temporal[1].markdown(f"**📊 Média Diária:** R$ {media_diaria:.2f}")
                
                dia_mais_vendas = df_filtered.groupby('DiaSemana')['Total'].sum().idxmax() if not df_filtered.empty else "N/A"
                stats_cols_temporal[2].markdown(f"**📆 Dia com Mais Vendas:** {dia_mais_vendas}")

                # Gráfico de média por dia da semana (Seg-Sex, usando locale)
                dias_uteis_nomes_locale = [datetime(2000, 1, i).strftime('%A').capitalize() for i in range(3, 3+5)] # Seg a Sex
                df_dias_uteis = df_filtered[df_filtered['DiaSemana'].isin(dias_uteis_nomes_locale)]
                if not df_dias_uteis.empty:
                    vendas_por_dia_uteis = df_dias_uteis.groupby('DiaSemana')['Total'].mean().reset_index()
                    # Garantir a ordem correta dos dias da semana no gráfico
                    vendas_por_dia_uteis['DiaSemana'] = pd.Categorical(vendas_por_dia_uteis['DiaSemana'], categories=dias_uteis_nomes_locale, ordered=True)
                    vendas_por_dia_uteis = vendas_por_dia_uteis.sort_values('DiaSemana')

                    chart_dias_uteis = alt.Chart(vendas_por_dia_uteis).mark_bar().encode(
                        x=alt.X('DiaSemana:N', title='Dia da Semana', sort=dias_uteis_nomes_locale),
                        y=alt.Y('Total:Q', title='Média de Vendas (R$)'),
                        tooltip=['DiaSemana', 'Total']
                    ).properties(title='Média de Vendas por Dia da Semana (Seg-Sex)', height=500)
                    st.altair_chart(chart_dias_uteis, use_container_width=True)
            
            if 'AnoMês' in df_filtered.columns and df_filtered['AnoMês'].nunique() > 1:
                st.subheader("📈 Tendência Mensal")
                vendas_mensais = df_filtered.groupby('AnoMês')['Total'].sum().reset_index()
                if len(vendas_mensais) >= 2:
                    ultimo_mes_val = vendas_mensais.iloc[-1]['Total']
                    penultimo_mes_val = vendas_mensais.iloc[-2]['Total']
                    variacao = ((ultimo_mes_val - penultimo_mes_val) / penultimo_mes_val * 100) if penultimo_mes_val > 0 else 0
                    emoji_tendencia = "🚀" if variacao > 10 else "📈" if variacao > 0 else "📉" if variacao < 0 else "➡️"
                    st.markdown(f"**{emoji_tendencia} Variação Mensal:** {variacao:.1f}%")
                    
                    trend_chart = alt.Chart(vendas_mensais).mark_line(point=True).encode(
                        x=alt.X('AnoMês:N', title='Mês', sort=alt.EncodingSortField(field="AnoMês", op="min", order='ascending')),
                        y=alt.Y('Total:Q', title='Total de Vendas (R$)'),
                        tooltip=['AnoMês', 'Total']
                    ).properties(title='Tendência Mensal de Vendas', height=500)
                    st.altair_chart(trend_chart, use_container_width=True)

            # Mais estatísticas (Avançadas, Projeções, Frequência, Sazonalidade, Evolução Métodos)
            # ... (O restante do código da Tab3 pode ser adaptado de forma similar, 
            #      garantindo que 'df_filtered' e as colunas derivadas de data estejam corretas)
            # Por exemplo, para Sazonalidade Semanal:
            st.markdown("---")
            st.subheader("📅 Sazonalidade Semanal (Todos os Dias)")
            if 'DiaSemana' in df_filtered.columns and len(df_filtered) > 6:
                todos_dias_semana_locale = [datetime(2000, 1, i).strftime('%A').capitalize() for i in range(3, 3+7)] # Seg a Dom
                vendas_dia_semana_total = df_filtered.groupby('DiaSemana')['Total'].sum().reset_index()
                if not vendas_dia_semana_total.empty:
                    total_semanal_abs = vendas_dia_semana_total['Total'].sum()
                    if total_semanal_abs > 0:
                        vendas_dia_semana_total['Porcentagem'] = (vendas_dia_semana_total['Total'] / total_semanal_abs * 100)
                        vendas_dia_semana_total['DiaSemana'] = pd.Categorical(vendas_dia_semana_total['DiaSemana'], categories=todos_dias_semana_locale, ordered=True)
                        vendas_dia_semana_total = vendas_dia_semana_total.sort_values('DiaSemana')

                        chart_sazonalidade = alt.Chart(vendas_dia_semana_total).mark_bar().encode(
                            x=alt.X('DiaSemana:N', title='Dia da Semana', sort=todos_dias_semana_locale),
                            y=alt.Y('Porcentagem:Q', title='% do Volume Semanal'),
                            tooltip=['DiaSemana', 'Total', 'Porcentagem']
                        ).properties(title='Distribuição Semanal de Vendas (Volume Total %)', height=500)
                        st.altair_chart(chart_sazonalidade, use_container_width=True)

                        melhor_dia_df = vendas_dia_semana_total.loc[vendas_dia_semana_total['Total'].idxmax()]
                        pior_dia_df = vendas_dia_semana_total.loc[vendas_dia_semana_total['Total'].idxmin()]
                        best_worst_cols = st.columns(2)
                        best_worst_cols[0].markdown(f"**🔝 Melhor dia:** {melhor_dia_df['DiaSemana']} ({melhor_dia_df['Porcentagem']:.1f}% do total)")
                        best_worst_cols[1].markdown(f"**🔻 Pior dia:** {pior_dia_df['DiaSemana']} ({pior_dia_df['Porcentagem']:.1f}% do total)")

        else:
            st.info("Não há dados para exibir na aba Estatísticas ou os dados filtrados estão vazios.")

if __name__ == "__main__":
    main()

