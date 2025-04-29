import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, APIError
import locale # To format currency correctly if needed

# Set locale for currency formatting if desired (e.g., Brazilian Portuguese)
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    st.warning("Locale 'pt_BR.UTF-8' not available. Using default locale.")

# --- Page Config ---
st.set_page_config(page_title="Sistema de Registro e Análise de Vendas", layout="wide") # Use wide layout

# --- Google Sheets Functions ---

@st.cache_data(ttl=600) # Cache data for 10 minutes
def read_google_sheet_data():
    """Função para ler os dados da planilha Google Sheets - retorna APENAS o DataFrame"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly', 'https://www.googleapis.com/auth/drive.readonly']
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
        worksheet_name = 'Vendas'
        try:
            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            rows = worksheet.get_all_records()
            # Ensure consistent header cases, strip whitespace
            df = pd.DataFrame(rows)
            df.columns = [col.strip().title() for col in df.columns] # Standardize column names like 'Cartão', 'Dinheiro', 'Pix', 'Data'
            return df
        except SpreadsheetNotFound:
            st.error(f"Planilha com ID {spreadsheet_id} não encontrada.")
            return pd.DataFrame()
        except APIError as e:
            st.error(f"Erro na API do Google Sheets ao ler: {e}. Verifique as permissões.")
            return pd.DataFrame()
        except Exception as e: # Catch other gspread or parsing errors
             st.error(f"Erro ao processar dados da planilha: {e}")
             return pd.DataFrame()
    except KeyError:
        st.error("Credenciais 'google_credentials' não encontradas nos segredos do Streamlit.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro de autenticação ou leitura inicial: {e}")
        return pd.DataFrame()

def get_worksheet():
    """Função para obter o objeto worksheet para escrita."""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets'] # Write scope needed
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
        worksheet_name = 'Vendas'
        try:
            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            return worksheet
        except SpreadsheetNotFound:
            st.error(f"Planilha com ID {spreadsheet_id} não encontrada para escrita.")
            return None
        except APIError as e:
             st.error(f"Erro na API do Google Sheets ao obter planilha para escrita: {e}. Verifique as permissões.")
             return None
        except Exception as e:
             st.error(f"Erro ao obter worksheet para escrita: {e}")
             return None
    except KeyError:
        st.error("Credenciais 'google_credentials' não encontradas nos segredos do Streamlit.")
        return None
    except Exception as e:
        st.error(f"Erro de autenticação ao obter worksheet: {e}")
        return None

def add_data_to_sheet(date_str, cartao, dinheiro, pix, worksheet):
    """Função para adicionar dados à planilha Google Sheets"""
    if worksheet is None:
        st.error("Não foi possível acessar a planilha para registrar a venda.")
        return False
    try:
        # Ensure worksheet headers match expected format (optional but good practice)
        # expected_headers = ['Data', 'Cartão', 'Dinheiro', 'Pix']
        # current_headers = worksheet.row_values(1)
        # if current_headers != expected_headers:
        #    st.warning(f"Cabeçalho da planilha {current_headers} difere do esperado {expected_headers}. Tentando adicionar mesmo assim.")

        new_row = [date_str, float(cartao), float(dinheiro), float(pix)]
        worksheet.append_row(new_row, value_input_option='USER_ENTERED') # Use USER_ENTERED to allow Sheets formulas if any
        st.success("Dados registrados com sucesso!")
        return True
    except APIError as e:
        st.error(f"Erro na API do Google Sheets ao adicionar dados: {e}. Verifique as permissões.")
        return False
    except Exception as e:
        st.error(f"Erro ao adicionar dados: {e}")
        return False

# --- Data Processing ---
def process_data(df):
    """Função para processar e preparar os dados"""
    if df.empty:
        return df

    # Standardize required columns - check if they exist
    required_cols = ['Cartão', 'Dinheiro', 'Pix', 'Data']
    if not all(col in df.columns for col in required_cols):
        st.error(f"Erro: Colunas esperadas {required_cols} não encontradas na planilha. Colunas presentes: {list(df.columns)}")
        return pd.DataFrame() # Return empty if essential columns missing

    # Convert payment columns to numeric
    for col in ['Cartão', 'Dinheiro', 'Pix']:
        df[col] = pd.to_numeric(df[col], errors='coerce') # Coerce errors to NaN

    # Handle potential NaNs from conversion or empty cells before summing
    df.fillna({'Cartão': 0, 'Dinheiro': 0, 'Pix': 0}, inplace=True)

    df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']

    # Process Date Column
    try:
        # Attempt different formats if needed, but start with the expected one
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')

        # Check for parsing errors
        original_date_rows = df_raw['Data'].astype(str).str.strip().ne('') # Count non-empty original date strings
        parsed_nulls = df['Data'].isna().sum()
        original_nulls = (~original_date_rows).sum() # Count original empty/nulls

        if parsed_nulls > original_nulls:
            failed_count = parsed_nulls - original_nulls
            st.warning(f"Atenção: {failed_count} datas não puderam ser reconhecidas com o formato DD/MM/YYYY e foram ignoradas na análise temporal.")

        # Extract date parts only if parsing was successful (column is datetime)
        if pd.api.types.is_datetime64_any_dtype(df['Data']):
            df['Ano'] = df['Data'].dt.year
            df['Mês'] = df['Data'].dt.month
            df['MêsNome'] = df['Data'].dt.strftime('%B').str.capitalize() # Capitalize month name
            df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
            df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
            # Add Day of Week (in Portuguese) and Number
            df['DiaSemana'] = df['Data'].dt.strftime('%A').str.capitalize() # Capitalize day name
            df['DiaSemanaNum'] = df['Data'].dt.dayofweek # Monday=0, Sunday=6
        else:
             # Handle case where the entire column failed parsing
             st.error("Coluna 'Data' não pôde ser convertida para formato de data. Análises temporais podem falhar.")
             # Create dummy columns to avoid errors later, or handle absence in charts
             for col in ['Ano', 'Mês', 'MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana', 'DiaSemanaNum']:
                 df[col] = None

    except KeyError:
         st.error("Coluna 'Data' não encontrada na planilha.")
         return pd.DataFrame() # Cannot proceed without date
    except Exception as e:
        st.error(f"Erro inesperado ao processar a coluna 'Data': {e}")
        # Create dummy columns
        for col in ['Ano', 'Mês', 'MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana', 'DiaSemanaNum']:
            df[col] = None

    # Drop rows where Date parsing failed completely if needed for analysis integrity
    # df.dropna(subset=['Data'], inplace=True)

    return df

# --- Statistics Function ---
def display_global_stats(df):
    """Exibe estatísticas gerais baseadas em todo o DataFrame processado."""
    st.subheader("Estatísticas Gerais (Todos os Dados)")
    if df.empty or 'Total' not in df.columns or df['Data'].isna().all():
        st.info("Não há dados suficientes ou datas válidas para exibir estatísticas gerais.")
        return

    # Filter out potential future dates if necessary
    df_valid = df[df['Data'] <= datetime.now()].copy()
    if df_valid.empty:
         st.info("Nenhum dado histórico encontrado para estatísticas.")
         return

    # Calculate Stats
    total_geral = df_valid['Total'].sum()
    num_dias_registro = df_valid['DataFormatada'].nunique()
    media_diaria = total_geral / num_dias_registro if num_dias_registro > 0 else 0

    # Best/Worst Sales Day
    df_daily_sum = df_valid.groupby('DataFormatada')['Total'].sum().reset_index()
    if not df_daily_sum.empty:
        best_day_row = df_daily_sum.loc[df_daily_sum['Total'].idxmax()]
        # Find worst day with sales > 0
        worst_day_row = df_daily_sum[df_daily_sum['Total'] > 0].loc[df_daily_sum['Total'].idxmin()] if not df_daily_sum[df_daily_sum['Total'] > 0].empty else None
    else:
        best_day_row = pd.Series({'DataFormatada': 'N/A', 'Total': 0})
        worst_day_row = None

    # Payment Method Totals
    total_cartao = df_valid['Cartão'].sum()
    total_dinheiro = df_valid['Dinheiro'].sum()
    total_pix = df_valid['Pix'].sum()
    payment_totals = {'Cartão': total_cartao, 'Dinheiro': total_dinheiro, 'Pix': total_pix}
    most_used_payment = max(payment_totals, key=payment_totals.get) if any(v > 0 for v in payment_totals.values()) else "N/A"

    # Best Sales Month
    df_monthly_sum = df_valid.groupby('AnoMês')['Total'].sum().reset_index()
    if not df_monthly_sum.empty:
        best_month_row = df_monthly_sum.loc[df_monthly_sum['Total'].idxmax()]
    else:
        best_month_row = pd.Series({'AnoMês': 'N/A', 'Total': 0})

    # Display Stats
    col1, col2, col3 = st.columns(3)
    col1.metric("Vendas Totais Gerais", f"R$ {total_geral:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")) # Brazilian format
    col2.metric("Média Diária Geral", f"R$ {media_diaria:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))
    col3.metric("Total de Dias com Registro", f"{num_dias_registro}")

    st.markdown("---")
    col4, col5, col6 = st.columns(3)
    col4.metric("Dia de Maior Venda", f"{best_day_row['DataFormatada']}", f"R$ {best_day_row['Total']:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))
    if worst_day_row is not None:
        col5.metric("Dia de Menor Venda (> R$0)", f"{worst_day_row['DataFormatada']}", f"R$ {worst_day_row['Total']:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))
    else:
        col5.metric("Dia de Menor Venda (> R$0)", "N/A", "R$ 0,00")
    col6.metric("Forma de Pag. Mais Usada (Valor)", most_used_payment, f"R$ {payment_totals.get(most_used_payment, 0):,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))

    col7, col8, col9 = st.columns(3) # Placeholder for maybe another row
    col7.metric("Mês de Maior Venda", f"{best_month_row['AnoMês']}", f"R$ {best_month_row['Total']:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))

# --- Main Application ---
def main():
    st.title("📊 Sistema de Registro e Análise de Vendas")

    # Load and process data ONCE at the start
    # Assign to df_raw first to pass to process_data if needed for comparison
    global df_raw # Make df_raw accessible in process_data if needed there
    df_raw = read_google_sheet_data()
    df_processed = process_data(df_raw.copy()) if not df_raw.empty else pd.DataFrame()

    tab1, tab2 = st.tabs(["📈 Registrar Venda & Estatísticas", "🔍 Análise Detalhada"])

    # --- TAB 1: Registration & Global Stats ---
    with tab1:
        st.header("Registrar Nova Venda")
        with st.form("venda_form"):
            data = st.date_input("Data", datetime.now())
            col_form1, col_form2, col_form3 = st.columns(3)
            with col_form1:
                cartao = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f", key="cartao_input")
            with col_form2:
                dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f", key="dinheiro_input")
            with col_form3:
                pix = st.number_input("PIX (R$)", min_value=0.0, format="%.2f", key="pix_input")

            total = cartao + dinheiro + pix
            st.markdown(f"**Total da venda: R$ {total:,.2f}**".replace(",", "#").replace(".", ",").replace("#", "."))

            submitted = st.form_submit_button("Registrar Venda")
            if submitted:
                if total > 0:
                    formatted_date = data.strftime('%d/%m/%Y')
                    worksheet = get_worksheet() # Get worksheet for writing
                    if worksheet:
                         success = add_data_to_sheet(formatted_date, cartao, dinheiro, pix, worksheet)
                         if success:
                             # Clear cache and rerun to update stats immediately
                             st.cache_data.clear()
                             st.rerun()
                else:
                    st.warning("O valor total da venda deve ser maior que zero.")

        st.divider() # Separate registration from stats

        # Display stats using the pre-processed data
        display_global_stats(df_processed)

    # --- TAB 2: Detailed Analysis ---
    with tab2:
        st.header("Análise Detalhada de Vendas")

        if df_processed.empty or 'Data' not in df_processed.columns or df_processed['Data'].isna().all():
            st.info("Não há dados válidos para análise. Verifique a planilha ou os registros.")
        else:
            # --- Filters ---
            anos_disponiveis = sorted(df_processed['Ano'].dropna().unique().astype(int))
            if not anos_disponiveis:
                st.warning("Nenhum ano válido encontrado nos dados.")
                st.stop() # Stop execution of this tab if no years

            col_filt1, col_filt2 = st.columns(2)
            with col_filt1:
                selected_anos = st.multiselect("Selecione o(s) Ano(s):", options=anos_disponiveis, default=anos_disponiveis)

            # Filter based on selected years first
            df_filtered_years = df_processed[df_processed['Ano'].isin(selected_anos)].copy()

            if df_filtered_years.empty:
                 st.info("Nenhum dado encontrado para o(s) ano(s) selecionado(s).")
                 st.stop()

            meses_disponiveis = sorted(df_filtered_years['Mês'].dropna().unique().astype(int))
            if not meses_disponiveis:
                st.warning("Nenhum mês válido encontrado para o(s) ano(s) selecionado(s).")
                st.stop() # Stop execution if no months

            # Create month options with names
            meses_nomes_map = {m: datetime(2020, m, 1).strftime('%B').capitalize() for m in meses_disponiveis}
            meses_opcoes = [f"{m} - {meses_nomes_map[m]}" for m in meses_disponiveis]

            with col_filt2:
                selected_meses_str = st.multiselect("Selecione o(s) Mês(es):", options=meses_opcoes, default=meses_opcoes)

            # Extract month numbers from selection
            selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]
            df_filtered = df_filtered_years[df_filtered_years['Mês'].isin(selected_meses)].copy()

            # --- Display Filtered Data & Summary ---
            if df_filtered.empty:
                st.info("Nenhum dado encontrado para os filtros selecionados.")
            else:
                st.subheader("Resumo do Período Filtrado")
                total_filt = df_filtered['Total'].sum()
                dias_filt = df_filtered['DataFormatada'].nunique()
                media_filt = total_filt / dias_filt if dias_filt > 0 else 0
                col_s1, col_s2, col_s3 = st.columns(3)
                col_s1.metric("Vendas Totais (Filtro)", f"R$ {total_filt:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))
                col_s2.metric("Média Diária (Filtro)", f"R$ {media_filt:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))
                col_s3.metric("Dias Registrados (Filtro)", f"{dias_filt}")
                st.divider()

                st.subheader("Dados Filtrados")
                # Select and rename columns for display
                display_cols = {'DataFormatada': 'Data', 'Cartão': 'Cartão (R$)', 'Dinheiro': 'Dinheiro (R$)', 'Pix': 'Pix (R$)', 'Total': 'Total (R$)'}
                st.dataframe(df_filtered[list(display_cols.keys())].rename(columns=display_cols), use_container_width=True)
                st.divider()

                # --- Altair Charts (Using df_filtered) ---
                st.header("Visualizações")

                # Chart 1: Payment Method Distribution (Pie)
                st.subheader("Distribuição por Método de Pagamento")
                payment_filtered = pd.DataFrame({
                    'Método': ['Cartão', 'Dinheiro', 'PIX'],
                    'Valor': [df_filtered['Cartão'].sum(), df_filtered['Dinheiro'].sum(), df_filtered['Pix'].sum()]
                }).query('Valor > 0') # Exclude methods with zero value

                if not payment_filtered.empty:
                    base_pie = alt.Chart(payment_filtered).encode(
                        theta=alt.Theta("Valor:Q", stack=True),
                        color=alt.Color("Método:N", scale=alt.Scale(scheme='category10'), legend=alt.Legend(title="Método")),
                        order=alt.Order("Valor:Q", sort="descending"), # Sort slices by size
                        tooltip=[
                            alt.Tooltip("Método:N"),
                            alt.Tooltip("Valor:Q", format=",.2f", title="Valor (R$)"),
                            alt.Tooltip("Valor:Q", aggregate="sum", title="Total Geral", format=",.2f"), # Show total in tooltip (doesn't work directly this way)
                            alt.Tooltip("Valor:Q", title="Percentual", format=".1%") # Calculate percentage? Requires transform_calculate
                        ]
                    ).properties(
                        #title='Distribuição Percentual' # Removed title from properties to use st.subheader
                    )
                    pie_chart = base_pie.mark_arc(outerRadius=140, innerRadius=60) # Donut chart
                    text_pie = base_pie.mark_text(radius=160).encode(
                        text=alt.Text('Valor:Q', format='.1%'), # Display percentage
                        order=alt.Order("Valor:Q", sort="descending"),
                        color=alt.value("black") # Set text color
                    ).transform_calculate(
                       percent = alt.datum.Valor / payment_filtered['Valor'].sum() # Calculate percentage
                    )
                    # Layering text requires adjustment, or use transform_window for percentage
                    # Simplified: show value on tooltip, maybe labels outside if needed
                    final_pie = pie_chart # Combine text later if layout works

                    # Add total label in the center
                    total_value_text = alt.Chart(payment_filtered).mark_text(align='center', baseline='middle', fontSize=20, fontWeight='bold', color='#4A4A4A').encode(
                        text=alt.Text('sum(Valor):Q', format=",.2f"),
                        color = alt.value("black") # Ensure text is visible
                    ).properties(title=alt.TitleParams(text=f"Total: R$", align='center', baseline='bottom', dy=-125, dx= 0, fontSize=16)) # Position title manually near text

                    # Layering text needs care. Let's keep pie simple for now. Tooltips provide details.
                    st.altair_chart(pie_chart, use_container_width=True)
                else:
                     st.info("Nenhum dado de pagamento para exibir o gráfico de pizza.")

                # Chart 2: Daily Sales by Method (Bar)
                st.subheader("Vendas Diárias por Método de Pagamento")
                daily_filtered = df_filtered.groupby('DataFormatada')[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
                daily_filtered_long = pd.melt(daily_filtered,
                                              id_vars=['DataFormatada'],
                                              value_vars=['Cartão', 'Dinheiro', 'Pix'],
                                              var_name='Método', value_name='Valor')
                daily_filtered_long = daily_filtered_long[daily_filtered_long['Valor'] > 0] # Show only bars with value

                if not daily_filtered_long.empty:
                     # Sort x-axis by date
                     daily_filtered_long['Data'] = pd.to_datetime(daily_filtered_long['DataFormatada'], format='%d/%m/%Y')

                     bar_chart_filtered = alt.Chart(daily_filtered_long).mark_bar().encode(
                        x=alt.X('Data:T', title='Data', axis=alt.Axis(format="%d/%m", labelAngle=-45)), # Format date on axis
                        y=alt.Y('sum(Valor):Q', title='Valor (R$)'),
                        color=alt.Color('Método:N', legend=alt.Legend(title="Pagamento"), scale=alt.Scale(scheme='category10')),
                        tooltip=[
                            alt.Tooltip('DataFormatada', title='Data'),
                            alt.Tooltip('Método:N'),
                            alt.Tooltip('sum(Valor):Q', title='Valor (R$)', format=',.2f')
                        ]
                    ).properties(
                         #title="Vendas Diárias Detalhadas"
                    ).interactive() # Allow zooming/panning
                     st.altair_chart(bar_chart_filtered, use_container_width=True)
                else:
                    st.info("Nenhum dado diário para exibir o gráfico de barras.")

                # Chart 3: Cumulative Capital (Line)
                st.subheader("Acúmulo de Capital ao Longo do Tempo")
                # Ensure data is sorted correctly by date before calculating cumsum
                df_accumulated = df_filtered.sort_values('Data').copy()
                # Need to handle potential multiple entries per day correctly if calculating daily cumulative
                df_daily_total = df_accumulated.groupby('Data')['Total'].sum().reset_index()
                df_daily_total['Total Acumulado'] = df_daily_total['Total'].cumsum()

                if not df_daily_total.empty:
                    acum_chart = alt.Chart(df_daily_total).mark_line(point=True, strokeWidth=3).encode(
                        x=alt.X('Data:T', title='Data', axis=alt.Axis(format="%d/%m/%Y")),
                        y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
                        tooltip=[
                            alt.Tooltip('Data:T', title='Data', format='%d/%m/%Y'),
                            alt.Tooltip('Total Acumulado:Q', title='Acumulado (R$)', format=',.2f')
                            ]
                    ).properties(
                         #title="Evolução do Capital Acumulado"
                    ).interactive()
                    st.altair_chart(acum_chart, use_container_width=True)
                else:
                    st.info("Nenhum dado para exibir o gráfico de acúmulo de capital.")

                st.divider()
                st.header("Análises Adicionais")

                # Chart 4: Monthly Sales Trend (Bar Chart)
                st.subheader("Vendas Mensais Totais")
                df_monthly = df_filtered.groupby(['AnoMês', 'Ano', 'Mês'])['Total'].sum().reset_index()
                # Ensure proper sorting by year and month
                df_monthly = df_monthly.sort_values(by=['Ano', 'Mês'])

                if not df_monthly.empty:
                    monthly_chart = alt.Chart(df_monthly).mark_bar().encode(
                        x=alt.X('AnoMês', title='Mês/Ano', sort=df_monthly['AnoMês'].tolist()), # Sort chronologically
                        y=alt.Y('Total:Q', title='Total Vendido (R$)'),
                        tooltip=[
                            alt.Tooltip('AnoMês', title='Mês/Ano'),
                            alt.Tooltip('Total:Q', title='Total (R$)', format=",.2f")
                        ]
                    ).properties(
                        #title="Total de Vendas por Mês"
                    ).interactive()
                    st.altair_chart(monthly_chart, use_container_width=True)
                else:
                    st.info("Nenhum dado mensal para exibir o gráfico de tendência.")


                # Chart 5: Sales by Day of Week (Bar Chart)
                st.subheader("Vendas Médias por Dia da Semana")
                # Requires 'DiaSemana' and 'DiaSemanaNum' from process_data
                if 'DiaSemana' in df_filtered.columns and 'DiaSemanaNum' in df_filtered.columns:
                    df_weekday = df_filtered.groupby(['DiaSemanaNum', 'DiaSemana'])['Total'].mean().reset_index() # Use mean for average
                    # Define the correct order for days of the week (Portuguese)
                    weekday_order = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']

                    if not df_weekday.empty:
                        weekday_chart = alt.Chart(df_weekday).mark_bar().encode(
                            x=alt.X('DiaSemana', title='Dia da Semana', sort=weekday_order), # Sort Mon-Sun
                            y=alt.Y('Total:Q', title='Média de Vendas (R$)'),
                            color=alt.Color('DiaSemana', legend=None, scale=alt.Scale(scheme='category10')), # Color bars by day
                            tooltip=[
                                alt.Tooltip('DiaSemana', title='Dia da Semana'),
                                alt.Tooltip('Total:Q', title='Média (R$)', format=",.2f")
                            ]
                        ).properties(
                            #title="Média de Vendas por Dia da Semana"
                        )
                        st.altair_chart(weekday_chart, use_container_width=True)
                    else:
                         st.info("Nenhum dado para exibir o gráfico por dia da semana.")
                else:
                     st.warning("Colunas 'DiaSemana'/'DiaSemanaNum' não disponíveis para análise por dia da semana.")


                # Chart 6: Payment Method Trend (Layered Area Chart - Monthly)
                st.subheader("Tendência de Métodos de Pagamento (Mensal)")
                df_monthly_payment = df_filtered.groupby(['AnoMês', 'Ano', 'Mês'])[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
                df_monthly_payment_long = pd.melt(df_monthly_payment,
                                                  id_vars=['AnoMês', 'Ano', 'Mês'],
                                                  value_vars=['Cartão', 'Dinheiro', 'Pix'],
                                                  var_name='Método', value_name='ValorMensal')
                # Sort for correct area layering and axis
                df_monthly_payment_long = df_monthly_payment_long.sort_values(by=['Ano', 'Mês'])

                if not df_monthly_payment_long.empty:
                    payment_trend_chart = alt.Chart(df_monthly_payment_long).mark_area().encode(
                        x=alt.X('AnoMês', title='Mês/Ano', sort=df_monthly_payment_long['AnoMês'].unique().tolist()), # Ensure chronological sort
                        y=alt.Y('sum(ValorMensal):Q', stack='normalize', title='Proporção de Vendas', axis=alt.Axis(format='%')), # Normalize for percentage view
                        color=alt.Color('Método:N', scale=alt.Scale(scheme='category10'), legend=alt.Legend(title="Método")),
                        tooltip=[
                            alt.Tooltip('AnoMês', title='Mês/Ano'),
                            alt.Tooltip('Método:N'),
                            alt.Tooltip('sum(ValorMensal):Q', title='Valor Mensal (R$)', format=",.2f")
                        ]
                    ).properties(
                        #title="Proporção Mensal por Método de Pagamento"
                    ).interactive()
                    st.altair_chart(payment_trend_chart, use_container_width=True)
                else:
                    st.info("Nenhum dado para exibir o gráfico de tendência de pagamentos.")


if __name__ == "__main__":
    main()
