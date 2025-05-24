import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg' # Substitua pelo seu ID
WORKSHEET_NAME = 'Vendas'

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="wide")

# Define a ordem correta dos dias da semana e meses
dias_semana_ordem = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# --- Funções de Cache para Acesso ao Google Sheets ---
@st.cache_resource
def get_google_auth():
    """Autoriza o acesso ao Google Sheets e retorna o cliente gspread."""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/spreadsheets.readonly',
              'https://www.googleapis.com/auth/drive.readonly']
    try:
        if "google_credentials" not in st.secrets:
            st.error("Credenciais do Google ('google_credentials') não encontradas em st.secrets. Configure o arquivo .streamlit/secrets.toml")
            return None
        
        credentials_dict = st.secrets["google_credentials"]
        if not credentials_dict:
            st.error("As credenciais do Google em st.secrets estão vazias.")
            return None
            
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
            st.error(f"Planilha com ID '{SPREADSHEET_ID}' não encontrada.")
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
            if not rows:
                st.info("A planilha de vendas está vazia.")
                return pd.DataFrame()

            df = pd.DataFrame(rows)
            
            for col in ['Cartão', 'Dinheiro', 'Pix']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                else:
                    df[col] = 0
            
            if 'Data' not in df.columns:
                df['Data'] = pd.NaT

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
        cartao_val = float(cartao) if cartao else 0.0
        dinheiro_val = float(dinheiro) if dinheiro else 0.0
        pix_val = float(pix) if pix else 0.0
        
        new_row = [date, cartao_val, dinheiro_val, pix_val]
        worksheet_obj.append_row(new_row)
        st.success("Dados registrados com sucesso! ✅")
        return True
    except ValueError as ve:
        st.error(f"Erro ao converter valores para número: {ve}. Verifique os dados de entrada.")
        return False
    except Exception as e:
        st.error(f"Erro ao adicionar dados na planilha: {e}")
        return False

@st.cache_data
def process_data(df_input):
    """Processa e prepara os dados de vendas para análise."""
    df = df_input.copy()
    
    cols_to_ensure_numeric = ['Cartão', 'Dinheiro', 'Pix', 'Total']
    cols_to_ensure_date_derived = ['Ano', 'Mês', 'MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana', 'DiaDoMes']
    
    if df.empty:
        all_expected_cols = ['Data'] + cols_to_ensure_numeric + cols_to_ensure_date_derived
        empty_df = pd.DataFrame(columns=all_expected_cols)
        for col in cols_to_ensure_numeric:
            empty_df[col] = pd.Series(dtype='float')
        for col in cols_to_ensure_date_derived:
            empty_df[col] = pd.Series(dtype='object' if col in ['MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana'] else 'float')
        empty_df['Data'] = pd.Series(dtype='datetime64[ns]')
        return empty_df

    for col in ['Cartão', 'Dinheiro', 'Pix']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0

    df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']

    if 'Data' in df.columns and not df['Data'].isnull().all():
        try:
            if pd.api.types.is_string_dtype(df['Data']):
                df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
                if df['Data'].isnull().all():
                    df['Data'] = pd.to_datetime(df_input['Data'], errors='coerce')
            elif not pd.api.types.is_datetime64_any_dtype(df['Data']):
                df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
            
            df.dropna(subset=['Data'], inplace=True)

            if not df.empty:
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                try:
                    df['MêsNome'] = df['Data'].dt.strftime('%B').str.capitalize()
                    if not df['MêsNome'].dtype == 'object' or df['MêsNome'].str.isnumeric().any():
                         df['MêsNome'] = df['Mês'].map(lambda x: meses_ordem[int(x)-1] if 1 <= int(x) <= 12 else "Inválido")
                except Exception: # Fallback em caso de erro com strftime ou locale
                    df['MêsNome'] = df['Mês'].map(lambda x: meses_ordem[int(x)-1] if 1 <= int(x) <= 12 else "Inválido")

                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                
                day_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
                df['DiaSemana'] = df['Data'].dt.dayofweek.map(day_map)
                df['DiaDoMes'] = df['Data'].dt.day

                df['DiaSemana'] = pd.Categorical(df['DiaSemana'], categories=[d for d in dias_semana_ordem if d in df['DiaSemana'].unique()], ordered=True)
            else:
                for col in cols_to_ensure_date_derived:
                    df[col] = pd.Series(dtype='object' if col in ['MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana'] else 'float')
        except Exception as e:
            st.error(f"Erro crítico ao processar a coluna 'Data': {e}. Verifique o formato das datas na planilha.")
            for col in cols_to_ensure_date_derived:
                df[col] = pd.Series(dtype='object' if col in ['MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana'] else 'float')
    else:
        if 'Data' not in df.columns:
            st.warning("Coluna 'Data' não encontrada no DataFrame. Algumas análises temporais não estarão disponíveis.")
            df['Data'] = pd.NaT
        for col in cols_to_ensure_date_derived:
            df[col] = pd.Series(dtype='object' if col in ['MêsNome', 'AnoMês', 'DataFormatada', 'DiaSemana'] else 'float')
            
    return df

def create_payment_evolution_chart(df, title="Evolução da Preferência por Pagamento (Mensal)"):
    if df.empty or 'AnoMês' not in df.columns or not any(col in df.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
        return None
    df_chart = df.sort_values('AnoMês')
    monthly_payments = df_chart.groupby('AnoMês')[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
    monthly_payments_long = monthly_payments.melt(
        id_vars=['AnoMês'], value_vars=['Cartão', 'Dinheiro', 'Pix'], var_name='Método', value_name='Valor')
    monthly_payments_long = monthly_payments_long[monthly_payments_long['Valor'] > 0]
    if monthly_payments_long.empty: return None
    area_chart = alt.Chart(monthly_payments_long).mark_area().encode(
        x=alt.X('AnoMês:N', title='Mês/Ano', sort=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Valor:Q', title='Valor Total (R$)', stack='zero', axis=alt.Axis(format=",.2f")),
        color=alt.Color('Método:N', legend=alt.Legend(title="Método de Pagamento")),
        tooltip=[alt.Tooltip("AnoMês", title="Mês/Ano"), alt.Tooltip("Método", title="Método"), alt.Tooltip("Valor", title="Valor (R$)", format=",.2f")]
    ).properties(title=title, height=600).interactive()
    return area_chart

def create_sales_histogram(df, title="Distribuição dos Valores de Venda Diários"):
    if df.empty or 'Total' not in df.columns or df['Total'].isnull().all(): return None
    df_filtered_hist = df[df['Total'] > 0].copy()
    if df_filtered_hist.empty: return None
    histogram = alt.Chart(df_filtered_hist).mark_bar().encode(
        alt.X("Total:Q", bin=alt.Bin(maxbins=20), title="Faixa de Valor da Venda Diária (R$)"),
        alt.Y('count()', title='Número de Dias (Frequência)'),
        tooltip=[alt.Tooltip("Total:Q", bin=True, title="Faixa de Valor (R$)"), alt.Tooltip("count()", title="Número de Dias")]
    ).properties(title=title, height=600).interactive()
    return histogram

def analyze_sales_by_weekday(df):
    if df.empty or 'DiaSemana' not in df.columns or 'Total' not in df.columns or df['DiaSemana'].isnull().all() or df['Total'].isnull().all(): return None, None
    try:
        df_copy = df.copy()
        df_copy['Total'] = pd.to_numeric(df_copy['Total'], errors='coerce')
        df_copy.dropna(subset=['Total', 'DiaSemana'], inplace=True)
        if df_copy.empty: return None, None
        avg_sales_weekday = df_copy.groupby('DiaSemana', observed=False)['Total'].mean().reindex(dias_semana_ordem).dropna()
        if not avg_sales_weekday.empty:
            best_day = avg_sales_weekday.idxmax()
            return best_day, avg_sales_weekday
        else: return None, avg_sales_weekday
    except Exception as e:
        st.error(f"Erro ao analisar vendas por dia da semana: {e}")
        return None, None

def create_heatmap(df):
    if df.empty or not all(col in df.columns for col in ['DiaSemana', 'MêsNome', 'Total']) or df[['DiaSemana', 'MêsNome', 'Total']].isnull().all().any(): return None
    df_heatmap = df.copy()
    df_heatmap = df_heatmap.dropna(subset=['DiaSemana', 'MêsNome', 'Total'])
    df_heatmap = df_heatmap[df_heatmap['Total'] > 0]
    if df_heatmap.empty: return None
    df_heatmap['MêsNome'] = pd.Categorical(df_heatmap['MêsNome'], categories=meses_ordem, ordered=True)
    df_heatmap['DiaSemana'] = pd.Categorical(df_heatmap['DiaSemana'], categories=dias_semana_ordem, ordered=True)
    heatmap_data = df_heatmap.groupby(['DiaSemana', 'MêsNome'], observed=False)['Total'].sum().reset_index()
    heatmap_data = heatmap_data[heatmap_data['Total'] > 0]
    if heatmap_data.empty: return None
    all_days = [day for day in dias_semana_ordem if day in df_heatmap['DiaSemana'].unique()]
    all_months = [month for month in meses_ordem if month in df_heatmap['MêsNome'].unique()]
    from itertools import product
    full_grid = pd.DataFrame(list(product(all_days, all_months)), columns=['DiaSemana', 'MêsNome'])
    heatmap_complete = full_grid.merge(heatmap_data, on=['DiaSemana', 'MêsNome'], how='left').fillna(0)
    heatmap_chart = alt.Chart(heatmap_complete).mark_rect().encode(
        x=alt.X('MêsNome:O', title='Mês', sort=all_months),
        y=alt.Y('DiaSemana:O', title='Dia da Semana', sort=all_days),
        color=alt.Color('Total:Q', title='Total de Vendas (R$)', scale=alt.Scale(scheme='blues', domain=[0, heatmap_complete['Total'].max()]), legend=alt.Legend(format=",.0f")),
        tooltip=[alt.Tooltip('MêsNome:N', title='Mês'), alt.Tooltip('DiaSemana:N', title='Dia da Semana'), alt.Tooltip('Total:Q', title='Total Vendas (R$)', format=",.2f")]
    ).properties(title="Mapa de Calor: Total de Vendas (Dia da Semana x Mês)", width=600, height=600).interactive()
    return heatmap_chart

# --- Funções de Cálculos Financeiros ---
def calculate_financial_results(df, salario_minimo, custo_contadora, custo_fornecedores_percentual):
    """
    Calcula os resultados financeiros.
    O custo com fornecedores é um percentual sobre o faturamento bruto.
    """
    results = {
        'faturamento_bruto': 0, 'faturamento_tributavel': 0, 'imposto_simples': 0,
        'custo_funcionario': 0, 'custo_contadora': custo_contadora,
        'custo_fornecedores_valor': 0, 'total_custos_fixos_operacionais': 0,
        'lucro_bruto_antes_fornecedores': 0, 'lucro_liquido_operacional': 0,
        'resultado_bruto_menos_tributavel': 0 # Métrica específica
    }
    if df.empty: return results
    
    # Receitas
    results['faturamento_bruto'] = df['Total'].sum()
    results['faturamento_tributavel'] = df['Cartão'].sum() + df['Pix'].sum()
    
    # Custos Fixos e Impostos diretos sobre receita
    results['imposto_simples'] = results['faturamento_tributavel'] * 0.06 # 6% sobre o tributável
    results['custo_funcionario'] = salario_minimo * 1.55 # Estimativa de 55% de encargos sobre o salário
    
    # Total de Custos Fixos e Operacionais (sem fornecedores ainda)
    results['total_custos_fixos_operacionais'] = results['imposto_simples'] + results['custo_funcionario'] + results['custo_contadora']
    
    # Lucro Bruto antes de considerar o custo variável dos fornecedores
    results['lucro_bruto_antes_fornecedores'] = results['faturamento_bruto'] - results['total_custos_fixos_operacionais']
    
    # Custo com Fornecedores (variável, percentual sobre faturamento bruto)
    results['custo_fornecedores_valor'] = results['faturamento_bruto'] * (custo_fornecedores_percentual / 100)
    
    # Lucro Líquido Operacional Final (após todos os custos, incluindo fornecedores)
    results['lucro_liquido_operacional'] = results['lucro_bruto_antes_fornecedores'] - results['custo_fornecedores_valor']
    
    # Métrica específica solicitada: (Faturamento Bruto - Faturamento Tributável)
    results['resultado_bruto_menos_tributavel'] = results['faturamento_bruto'] - results['faturamento_tributavel']
    
    return results

# Função para formatar valores em moeda brasileira (sem locale)
def format_brl(value):
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

# --- Interface Principal da Aplicação ---
def main():
    st.title("📊 Sistema de Registro de Vendas e Análise Financeira")

    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    tab1, tab2, tab3, tab4 = st.tabs(["📝 Registrar Venda", "📈 Análise Detalhada", "💡 Estatísticas", "💰 Análise Financeira"])

    with tab1:
        st.header("Registrar Nova Venda")
        with st.form("venda_form"):
            data_input = st.date_input("Data da Venda", value=datetime.now(), format="DD/MM/YYYY")
            col1, col2, col3 = st.columns(3)
            with col1: cartao_input = st.number_input("Cartão (R$)", min_value=0.0, value=0.0, format="%.2f", key="cartao_venda")
            with col2: dinheiro_input = st.number_input("Dinheiro (R$)", min_value=0.0, value=0.0, format="%.2f", key="dinheiro_venda")
            with col3: pix_input = st.number_input("PIX (R$)", min_value=0.0, value=0.0, format="%.2f", key="pix_venda")
            total_venda_form = (cartao_input or 0.0) + (dinheiro_input or 0.0) + (pix_input or 0.0)
            st.markdown(f"**Total da venda: R$ {total_venda_form:.2f}**")
            submitted = st.form_submit_button("Registrar Venda")
            if submitted:
                if total_venda_form > 0:
                    formatted_date = data_input.strftime('%d/%m/%Y')
                    worksheet_obj = get_worksheet()
                    if worksheet_obj and add_data_to_sheet(formatted_date, cartao_input, dinheiro_input, pix_input, worksheet_obj):
                        read_sales_data.clear(); process_data.clear()
                        st.success("Venda registrada e dados recarregados!")
                        st.rerun()
                    elif not worksheet_obj: st.error("Falha ao conectar à planilha. Venda não registrada.")
                else: st.warning("O valor total da venda deve ser maior que zero.")

    selected_anos_filter, selected_meses_filter = [], []
    with st.sidebar:
        st.header("🔍 Filtros de Análise")
        if not df_processed.empty and 'Ano' in df_processed.columns and not df_processed['Ano'].isnull().all():
            anos_disponiveis = sorted(df_processed['Ano'].dropna().unique().astype(int), reverse=True)
            if anos_disponiveis:
                default_ano = [datetime.now().year] if datetime.now().year in anos_disponiveis else ([anos_disponiveis[0]] if anos_disponiveis else [])
                selected_anos_filter = st.multiselect("Ano(s):", options=anos_disponiveis, default=default_ano)
                if selected_anos_filter:
                    df_para_filtro_mes = df_processed[df_processed['Ano'].isin(selected_anos_filter)]
                    if not df_para_filtro_mes.empty and 'Mês' in df_para_filtro_mes.columns and not df_para_filtro_mes['Mês'].isnull().all():
                        meses_numeros_disponiveis = sorted(df_para_filtro_mes['Mês'].dropna().unique().astype(int))
                        meses_opcoes_dict = {m_num: meses_ordem[m_num-1] for m_num in meses_numeros_disponiveis if 1 <= m_num <= 12}
                        meses_opcoes_display = [f"{m_num} - {m_nome}" for m_num, m_nome in meses_opcoes_dict.items()]
                        default_mes_num = datetime.now().month
                        default_mes_str = f"{default_mes_num} - {meses_ordem[default_mes_num-1]}" if 1 <= default_mes_num <= 12 and meses_opcoes_dict else None
                        default_meses_selecionados = [default_mes_str] if default_mes_str and default_mes_str in meses_opcoes_display else meses_opcoes_display
                        selected_meses_str = st.multiselect("Mês(es):", options=meses_opcoes_display, default=default_meses_selecionados)
                        selected_meses_filter = [int(m.split(" - ")[0]) for m in selected_meses_str]
            else: st.sidebar.info("Nenhum ano disponível para filtro.")
        else: st.sidebar.info("Não há dados processados ou coluna 'Ano' para aplicar filtros.")
        
        st.sidebar.subheader("⚙️ Parâmetros Fixos (Simulação)")
        salario_minimo_input = st.sidebar.number_input("Salário Mínimo Base (R$)", min_value=0.0, value=1412.0, format="%.2f", help="Usado para calcular custo estimado de funcionário (Salário + 55% encargos).")
        custo_contadora_input = st.sidebar.number_input("Custo Mensal Contadora (R$)", min_value=0.0, value=316.0, format="%.2f")


    df_filtered = df_processed.copy()
    if not df_filtered.empty:
        if selected_anos_filter and 'Ano' in df_filtered.columns: df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos_filter)]
        if selected_meses_filter and 'Mês' in df_filtered.columns: df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses_filter)]
    
    with tab2:
        st.header("🔎 Análise Detalhada de Vendas (Conforme Filtros)")
        if not df_filtered.empty and 'DataFormatada' in df_filtered.columns:
            st.subheader("🧾 Tabela de Vendas Filtradas")
            cols_to_display_tab2 = ['DataFormatada', 'DiaSemana', 'Cartão', 'Dinheiro', 'Pix', 'Total']
            cols_existentes_tab2 = [col for col in cols_to_display_tab2 if col in df_filtered.columns]
            if cols_existentes_tab2: st.dataframe(df_filtered[cols_existentes_tab2], use_container_width=True, height=600, hide_index=True)
            else: st.info("Colunas necessárias para a tabela de dados filtrados não estão disponíveis.")
            
            st.subheader("🥧 Distribuição por Método de Pagamento")
            if any(col in df_filtered.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
                payment_filtered_data = pd.DataFrame({'Método': ['Cartão', 'Dinheiro', 'PIX'], 'Valor': [df_filtered['Cartão'].sum(), df_filtered['Dinheiro'].sum(), df_filtered['Pix'].sum()]})
                payment_filtered_data = payment_filtered_data[payment_filtered_data['Valor'] > 0]
                if not payment_filtered_data.empty:
                    pie_chart = alt.Chart(payment_filtered_data).mark_arc(outerRadius=180).encode(
                        theta=alt.Theta("Valor:Q", stack=True), color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
                        tooltip=["Método", alt.Tooltip("Valor", format=",.2f", title="Valor (R$)")]
                    ).properties(height=600).interactive()
                    st.altair_chart(pie_chart, use_container_width=True)
                else: st.info("Sem dados de pagamento para exibir o gráfico de pizza nos filtros selecionados.")
            else: st.info("Colunas de pagamento não encontradas para o gráfico de pizza.")

            st.subheader("📊 Vendas Diárias Detalhadas por Método")
            if 'Data' in df_filtered.columns and not df_filtered['Data'].isnull().all():
                df_filtered_sorted_daily = df_filtered.sort_values('Data')
                daily_data = df_filtered_sorted_daily.melt(id_vars=['Data', 'DataFormatada'], value_vars=['Cartão', 'Dinheiro', 'Pix'], var_name='Método', value_name='Valor')
                daily_data = daily_data[daily_data['Valor'] > 0]
                if not daily_data.empty:
                    bar_chart_daily = alt.Chart(daily_data).mark_bar(size=15).encode(
                        x=alt.X('Data:T', title='Data', axis=alt.Axis(format="%d/%m/%y", labelAngle=-45)), y=alt.Y('Valor:Q', title='Valor (R$)', axis=alt.Axis(format=",.2f")),
                        color=alt.Color('Método:N', legend=alt.Legend(title="Método")), tooltip=["DataFormatada", "Método", alt.Tooltip("Valor", format=",.2f", title="Valor (R$)")]
                    ).properties(height=600).interactive()
                    st.altair_chart(bar_chart_daily, use_container_width=True)
                else: st.info("Sem dados de vendas diárias para exibir o gráfico de barras nos filtros selecionados.")
            else: st.info("Coluna 'Data' não encontrada ou vazia para o gráfico de vendas diárias.")

            st.subheader("📈 Acúmulo de Capital ao Longo do Tempo")
            if 'Data' in df_filtered.columns and not df_filtered.empty and not df_filtered['Data'].isnull().all() and 'Total' in df_filtered.columns:
                df_accumulated = df_filtered.sort_values('Data').copy()
                df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()
                line_chart_accum = alt.Chart(df_accumulated).mark_line(point=True, strokeWidth=3, color='green').encode(
                    x=alt.X('Data:T', title='Data', axis=alt.Axis(format="%d/%m/%y", labelAngle=-45)),
                    y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)', axis=alt.Axis(format=",.2f")),
                    tooltip=[alt.Tooltip("DataFormatada", title="Data"), alt.Tooltip("Total Acumulado", format=",.2f", title="Acumulado (R$)")]
                ).properties(height=600).interactive()
                st.altair_chart(line_chart_accum, use_container_width=True)
            else: st.info("Dados insuficientes (Data ou Total) para o gráfico de acúmulo.")
        else:
             if df_processed.empty and df_raw.empty and get_worksheet() is None: st.warning("Não foi possível carregar os dados. Verifique configurações e credenciais.")
             elif df_processed.empty: st.info("Não há dados processados para exibir. Verifique a planilha de origem.")
             elif df_filtered.empty: st.info("Nenhum dado corresponde aos filtros selecionados.")
             else: st.info("Não há dados para exibir na Análise Detalhada. Pode ser um problema no processamento.")

    with tab3:
        st.header("💡 Estatísticas e Tendências de Vendas (Conforme Filtros)")
        if not df_filtered.empty and 'Total' in df_filtered.columns and not df_filtered['Total'].isnull().all():
            st.subheader("💰 Resumo Financeiro Agregado")
            total_registros = len(df_filtered); total_faturamento = df_filtered['Total'].sum()
            media_por_registro = df_filtered['Total'].mean() if total_registros > 0 else 0
            maior_venda_diaria = df_filtered['Total'].max() if total_registros > 0 else 0
            menor_venda_diaria = df_filtered[df_filtered['Total'] > 0]['Total'].min() if not df_filtered[df_filtered['Total'] > 0].empty else 0
            col1, col2 = st.columns(2)
            col1.metric("🔢 Total de Registros (Dias com Venda)", f"{total_registros}")
            col2.metric("💵 Faturamento Total", format_brl(total_faturamento))
            col3, col4 = st.columns(2)
            col3.metric("📈 Média por Registro", format_brl(media_por_registro))
            col4.metric("⬆️ Maior Venda Diária", format_brl(maior_venda_diaria))
            st.metric("⬇️ Menor Venda Diária (>0)", format_brl(menor_venda_diaria))
            st.divider()

            st.subheader("💳 Métodos de Pagamento (Visão Geral)")
            cartao_total = df_filtered['Cartão'].sum() if 'Cartão' in df_filtered else 0
            dinheiro_total = df_filtered['Dinheiro'].sum() if 'Dinheiro' in df_filtered else 0
            pix_total = df_filtered['Pix'].sum() if 'Pix' in df_filtered else 0
            total_pagamentos_geral = cartao_total + dinheiro_total + pix_total
            if total_pagamentos_geral > 0:
                cartao_pct = (cartao_total / total_pagamentos_geral * 100)
                dinheiro_pct = (dinheiro_total / total_pagamentos_geral * 100)
                pix_pct = (pix_total / total_pagamentos_geral * 100)
                payment_cols = st.columns(3)
                payment_cols[0].metric("💳 Cartão", format_brl(cartao_total), f"{cartao_pct:.1f}% do total")
                payment_cols[1].metric("💵 Dinheiro", format_brl(dinheiro_total), f"{dinheiro_pct:.1f}% do total")
                payment_cols[2].metric("📱 PIX", format_brl(pix_total), f"{pix_pct:.1f}% do total")
            else: st.info("Sem dados de pagamento para exibir o resumo nesta seção.")
            st.divider()

            st.subheader("📅 Análise Temporal e Desempenho Semanal")
            best_weekday, avg_sales_weekday = analyze_sales_by_weekday(df_filtered)
            if avg_sales_weekday is not None and not avg_sales_weekday.empty:
                if best_weekday and pd.notna(avg_sales_weekday.get(best_weekday)): st.success(f"🏆 **Melhor Dia (Média de Vendas):** {best_weekday} - {format_brl(avg_sales_weekday[best_weekday])}")
                else: st.warning("⚠️ Não foi possível determinar o melhor dia da semana (dados insuficientes).")
                avg_sales_weekday_df = avg_sales_weekday.reset_index(); avg_sales_weekday_df.columns = ['Dia da Semana', 'Média de Venda (R$)']
                chart_avg_weekday = alt.Chart(avg_sales_weekday_df).mark_bar().encode(
                    x=alt.X('Dia da Semana:O', sort=dias_semana_ordem, title=None), y=alt.Y('Média de Venda (R$):Q', axis=alt.Axis(format=",.2f")),
                    tooltip=[alt.Tooltip('Dia da Semana:N'), alt.Tooltip('Média de Venda (R$):Q', format=",.2f")]
                ).properties(height=600, title="Média de Vendas por Dia da Semana")
                st.altair_chart(chart_avg_weekday, use_container_width=True)
            else: st.info("📊 Dados insuficientes para calcular a média de vendas por dia da semana.")
            st.divider()
            
            charts_col1, charts_col2 = st.columns(2)
            with charts_col1:
                st.subheader("🔥 Mapa de Calor (Dia x Mês)")
                heatmap_chart = create_heatmap(df_filtered)
                if heatmap_chart: st.altair_chart(heatmap_chart, use_container_width=True)
                else: st.info("Dados insuficientes para o Mapa de Calor.")
            
            with charts_col2:
                st.subheader("📈 Evolução Pagamentos (Mensal)")
                payment_evolution_chart = create_payment_evolution_chart(df_filtered)
                if payment_evolution_chart: st.altair_chart(payment_evolution_chart, use_container_width=True)
                else: st.info("Dados insuficientes para Evolução de Pagamento.")
            st.divider()

            st.subheader("📊 Distribuição de Valores de Venda Diários")
            sales_histogram_chart = create_sales_histogram(df_filtered)
            if sales_histogram_chart: st.altair_chart(sales_histogram_chart, use_container_width=True)
            else: st.info("Dados insuficientes para o Histograma de Vendas.")
        else:
            if df_processed.empty and df_raw.empty and get_worksheet() is None: st.warning("Não foi possível carregar os dados da planilha.")
            elif df_processed.empty: st.info("Não há dados processados para exibir estatísticas.")
            elif df_filtered.empty: st.info("Nenhum dado corresponde aos filtros para exibir estatísticas.")
            else: st.info("Não há dados de 'Total' para exibir nas Estatísticas.")

    # --- Aba de Análise Financeira REORGANIZADA ---
    with tab4:
        st.header("🔬 Raio-X Financeiro (Baseado nos Filtros)")
        st.caption("Esta análise considera os dados filtrados no painel à esquerda e os parâmetros fixos (Salário, Contadora) da Sidebar.")
        
        # Parâmetro de Custo com Fornecedores agora DENTRO da tab4
        with st.container(border=True):
            st.subheader("📦 Parâmetro de Custo Variável")
            custo_fornecedores_percentual_input = st.number_input(
                "Custo com Fornecedores (% do Faturamento Bruto)", 
                min_value=0.0, max_value=100.0, value=30.0, format="%.1f",
                help="Percentual estimado do faturamento bruto destinado a cobrir custos de insumos (bebidas, frios, pães, etc.)."
            )
        st.markdown("---")

        if df_filtered.empty or 'Total' not in df_filtered.columns:
            st.info("Não há dados de vendas filtrados para realizar a análise financeira. Por favor, ajuste os filtros ou registre vendas.")
        else:
            # salario_minimo_input e custo_contadora_input vêm da sidebar
            resultados_financeiros = calculate_financial_results(
                df_filtered, 
                salario_minimo_input, 
                custo_contadora_input, 
                custo_fornecedores_percentual_input # Agora da tab4
            )

            # === BLOCO DE RECEITAS ===
            with st.container(border=True):
                st.subheader("📈 Receitas do Período")
                receita_bruta = resultados_financeiros['faturamento_bruto']
                receita_tributavel = resultados_financeiros['faturamento_tributavel']
                receita_nao_tributavel = receita_bruta - receita_tributavel

                col_rec1, col_rec2, col_rec3 = st.columns(3)
                col_rec1.metric("💰 Faturamento Bruto Total", format_brl(receita_bruta))
                col_rec2.metric("💳 Receita Tributável (Cartão+PIX)", format_brl(receita_tributavel), 
                                f"{((receita_tributavel / receita_bruta * 100) if receita_bruta > 0 else 0):.1f}% do total")
                col_rec3.metric("💵 Receita Não Tributável (Dinheiro)", format_brl(receita_nao_tributavel),
                                f"{((receita_nao_tributavel / receita_bruta * 100) if receita_bruta > 0 else 0):.1f}% do total")
            st.markdown("---")

            # === BLOCO DE CUSTOS TOTAIS (FIXOS + VARIÁVEIS) ===
            with st.container(border=True):
                st.subheader("💸 Despesas e Custos Operacionais Totais")
                
                custos_fixos_operacionais_df = pd.DataFrame({
                    'Componente de Custo': ['Imposto Simples (6% s/ Trib.)', 'Custo Estimado Funcionário', 'Custo Contadora'],
                    'Valor (R$)': [
                        resultados_financeiros['imposto_simples'],
                        resultados_financeiros['custo_funcionario'],
                        resultados_financeiros['custo_contadora']
                    ]
                })
                # Adiciona o custo com fornecedores ao DataFrame para o gráfico
                custo_fornecedores_df = pd.DataFrame({
                    'Componente de Custo': [f'Custo Fornecedores ({custo_fornecedores_percentual_input}%)'],
                    'Valor (R$)': [resultados_financeiros['custo_fornecedores_valor']]
                })
                
                todos_custos_df = pd.concat([custos_fixos_operacionais_df, custo_fornecedores_df], ignore_index=True)
                todos_custos_df = todos_custos_df[todos_custos_df['Valor (R$)'] > 0]

                if not todos_custos_df.empty:
                    todos_custos_df['Percentual sobre Faturamento Bruto (%)'] = (todos_custos_df['Valor (R$)'] / receita_bruta * 100) if receita_bruta > 0 else 0
                    
                    bar_chart_todos_custos = alt.Chart(todos_custos_df).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                        x=alt.X('Componente de Custo:N', sort=None, title=None, axis=alt.Axis(labelAngle=-25)), # Ajustado angulo
                        y=alt.Y('Valor (R$):Q', title="Valor (R$)"),
                        tooltip=[
                            alt.Tooltip('Componente de Custo:N', title="Custo"),
                            alt.Tooltip('Valor (R$):Q', title="Valor", format=",.2f"),
                            alt.Tooltip('Percentual sobre Faturamento Bruto (%):Q', title="% do Fat. Bruto", format=".2f")
                        ],
                        color=alt.Color('Componente de Custo:N', legend=None)
                    ).properties(
                        title=alt.TitleParams(text="Composição dos Custos Totais (Fixos + Fornecedores)", anchor='middle'),
                        height=400 # Ajustado altura
                    )
                    st.altair_chart(bar_chart_todos_custos, use_container_width=True)

                    st.markdown("**Detalhamento dos Custos:**")
                    for _, row in todos_custos_df.iterrows():
                        st.markdown(f"- **{row['Componente de Custo']}:** {format_brl(row['Valor (R$)'])} ({row['Percentual sobre Faturamento Bruto (%)']:.2f}%)")
                
                total_custos_geral_val = resultados_financeiros['total_custos_fixos_operacionais'] + resultados_financeiros['custo_fornecedores_valor']
                percentual_total_custos_geral = (total_custos_geral_val / receita_bruta * 100) if receita_bruta > 0 else 0
                st.markdown(f"--- \n- **📉 Total Geral de Custos:** **{format_brl(total_custos_geral_val)}** ({percentual_total_custos_geral:.2f}% do Faturamento Bruto)")
            st.markdown("---")

            # === BLOCO DE RESULTADOS FINANCEIROS (LUCRO) ===
            with st.container(border=True):
                st.subheader("🎯 Resultados e Lucratividade")
                lucro_liq_op = resultados_financeiros['lucro_liquido_operacional']
                perc_lucro_liq_op = (lucro_liq_op / receita_bruta * 100) if receita_bruta > 0 else 0
                
                # Métrica "Resultado Bruto Antes de Fornecedores" pode ser interessante
                lucro_bruto_antes_fornec = resultados_financeiros['lucro_bruto_antes_fornecedores']
                perc_lucro_bruto_antes_fornec = (lucro_bruto_antes_fornec / receita_bruta * 100) if receita_bruta > 0 else 0

                col_lucro1, col_lucro2 = st.columns(2)
                with col_lucro1:
                    st.metric(
                        "📊 Lucro Bruto (Antes de Fornecedores)",
                        format_brl(lucro_bruto_antes_fornec),
                        f"{perc_lucro_bruto_antes_fornec:.2f}% do Fat. Bruto",
                        delta_color="normal" if lucro_bruto_antes_fornec >=0 else "inverse"
                    )
                    st.caption("(Fat. Bruto - Impostos - Funcionário - Contadora)")
                
                with col_lucro2:
                    st.metric(
                        "🏆 Lucro Líquido Operacional Final",
                        format_brl(lucro_liq_op),
                        f"{perc_lucro_liq_op:.2f}% do Fat. Bruto",
                        delta_color="normal" if lucro_liq_op >= 0 else "inverse"
                    )
                    st.caption(f"(Lucro Bruto Antes de Fornecedores - Custo Fornecedores de {custo_fornecedores_percentual_input}%)")
                
                st.markdown("---")
                # Métrica específica: Faturamento Bruto - Faturamento Tributável
                res_bruto_menos_trib = resultados_financeiros['resultado_bruto_menos_tributavel']
                st.metric(
                    "💡 Receita Não Tributada (Dinheiro)",
                    format_brl(res_bruto_menos_trib)
                )
                st.caption("(Faturamento Bruto Total - Faturamento Tributável. Representa o valor recebido em dinheiro.)")
            st.markdown("---")
            
            if receita_bruta > 0:
                if perc_lucro_liq_op < 5:
                    st.error(f"🚨 Atenção! O Lucro Líquido Operacional de {perc_lucro_liq_op:.2f}% está baixo. Considere rever o percentual de Custo com Fornecedores ou outras despesas.")
                elif perc_lucro_liq_op < 15:
                    st.warning(f"⚠️ O Lucro Líquido Operacional de {perc_lucro_liq_op:.2f}% é moderado. Avalie a otimização de custos.")
                else:
                    st.success(f"✅ Ótimo! O Lucro Líquido Operacional de {perc_lucro_liq_op:.2f}% parece saudável.")
            
            st.info("Lembre-se: Esta é uma simulação simplificada. Outros custos (aluguel, marketing, taxas de cartão, etc.) e impostos sobre o lucro (ex: IRPJ, CSLL para regimes não-Simples) não estão incluídos.")

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    main()
