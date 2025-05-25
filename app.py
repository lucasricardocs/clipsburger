import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
WORKSHEET_NAME = 'Vendas'

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema de Vendas e Análise Financeira", layout="wide", page_icon="📊")

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
                         df['MêsNome'] = df['Mês'].map(lambda x: meses_ordem[int(x)-1] if pd.notna(x) and 1 <= int(x) <= 12 else "Inválido")
                except Exception:
                    df['MêsNome'] = df['Mês'].map(lambda x: meses_ordem[int(x)-1] if pd.notna(x) and 1 <= int(x) <= 12 else "Inválido")

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

# --- Função para filtrar por somatório de últimos N dias ---
def filter_by_rolling_days(df, dias_selecionados):
    """Filtra o DataFrame para incluir apenas registros dos últimos N dias selecionados."""
    if df.empty or not dias_selecionados or 'Data' not in df.columns:
        return df
    
    # Pega a data mais recente dos dados
    data_mais_recente = df['Data'].max()
    
    # Calcula o maior período selecionado
    max_dias = max(dias_selecionados)
    
    # Filtra para incluir apenas os últimos N dias
    data_inicio = data_mais_recente - timedelta(days=max_dias - 1)
    df_filtrado = df[df['Data'] >= data_inicio].copy()
    
    return df_filtrado

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

# --- Função melhorada para gráfico de acumulação ---
def create_improved_accumulation_chart(df):
    """Cria um gráfico de acumulação melhorado com melhor espaçamento e estética."""
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        return None
    
    df_accumulated = df.sort_values('Data').copy()
    df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()
    
    # Adicionar padding nas datas para melhor visualização
    data_min = df_accumulated['Data'].min()
    data_max = df_accumulated['Data'].max()
    
    # Calcular padding (5% do range total)
    range_total = (data_max - data_min).total_seconds()
    padding_seconds = range_total * 0.05
    
    data_min_padded = data_min - timedelta(seconds=padding_seconds)
    data_max_padded = data_max + timedelta(seconds=padding_seconds)
    
    # Criar gráfico com melhor estética
    base_chart = alt.Chart(df_accumulated).add_selection(
        alt.selection_interval(bind='scales')
    )
    
    # Linha principal
    line_chart = base_chart.mark_line(
        point=alt.OverlayMarkDef(
            filled=True,
            size=80,
            color='white',
            stroke='#2E86AB',
            strokeWidth=2
        ),
        strokeWidth=4,
        color='#2E86AB',
        interpolate='monotone'
    ).encode(
        x=alt.X('Data:T', 
                title='Período',
                scale=alt.Scale(domain=[data_min_padded, data_max_padded]),
                axis=alt.Axis(
                    format="%d/%m/%y",
                    labelAngle=-45,
                    labelFontSize=11,
                    titleFontSize=13,
                    grid=True,
                    gridOpacity=0.3
                )),
        y=alt.Y('Total Acumulado:Q', 
                title='Capital Acumulado (R$)',
                scale=alt.Scale(nice=True, padding=0.1),
                axis=alt.Axis(
                    format=",.0f",
                    labelFontSize=11,
                    titleFontSize=13,
                    grid=True,
                    gridOpacity=0.3
                )),
        tooltip=[
            alt.Tooltip("DataFormatada:N", title="Data"),
            alt.Tooltip("Total:Q", title="Venda do Dia (R$)", format=",.2f"),
            alt.Tooltip("Total Acumulado:Q", title="Acumulado (R$)", format=",.2f")
        ]
    )
    
    # Área sombreada abaixo da linha
    area_chart = base_chart.mark_area(
        opacity=0.2,
        color='#2E86AB',
        interpolate='monotone'
    ).encode(
        x=alt.X('Data:T', scale=alt.Scale(domain=[data_min_padded, data_max_padded])),
        y=alt.Y('Total Acumulado:Q', scale=alt.Scale(nice=True, padding=0.1))
    )
    
    # Combinar área e linha
    combined_chart = (area_chart + line_chart).resolve_scale(
        y='shared'
    ).properties(
        title=alt.TitleParams(
            text="Evolução do Capital Acumulado",
            fontSize=16,
            fontWeight='bold',
            anchor='start',
            offset=20
        ),
        width='container',
        height=500,
        background='white'
    )
    
    return combined_chart

# --- Funções de Cálculos Financeiros ---
def calculate_financial_results(df, salario_minimo, custo_contadora, custo_fornecedores_percentual):
    """Calcula os resultados financeiros com base nos dados de vendas."""
    results = {
        'faturamento_bruto': 0, 'faturamento_tributavel': 0, 'faturamento_nao_tributavel': 0,
        'imposto_simples': 0, 'custo_funcionario': 0, 'custo_contadora': custo_contadora,
        'custo_fornecedores_valor': 0, 'total_custos': 0,
        'lucro_bruto': 0, 'margem_lucro_bruto': 0, 'lucro_liquido': 0, 'margem_lucro_liquido': 0
    }
    
    if df.empty: 
        return results
    
    # RECEITAS
    results['faturamento_bruto'] = df['Total'].sum()
    results['faturamento_tributavel'] = df['Cartão'].sum() + df['Pix'].sum()
    results['faturamento_nao_tributavel'] = df['Dinheiro'].sum()
    
    # CUSTOS E DESPESAS
    results['imposto_simples'] = results['faturamento_tributavel'] * 0.06
    results['custo_funcionario'] = salario_minimo * 1.55
    results['custo_fornecedores_valor'] = results['faturamento_bruto'] * (custo_fornecedores_percentual / 100)
    results['total_custos'] = results['imposto_simples'] + results['custo_funcionario'] + results['custo_contadora'] + results['custo_fornecedores_valor']
    
    # RESULTADOS
    results['lucro_bruto'] = results['faturamento_bruto'] - results['total_custos']
    results['lucro_liquido'] = results['faturamento_bruto'] - results['faturamento_tributavel']
    
    # MARGENS
    if results['faturamento_bruto'] > 0:
        results['margem_lucro_bruto'] = (results['lucro_bruto'] / results['faturamento_bruto']) * 100
        results['margem_lucro_liquido'] = (results['lucro_liquido'] / results['faturamento_bruto']) * 100
    
    return results

# Função para formatar valores em moeda brasileira
def format_brl(value):
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

# --- Interface Principal da Aplicação ---
def main():
    # Título melhorado com logo
    try:
        col_logo, col_title = st.columns([1, 8])
        with col_logo:
            st.image('logo.png', width=80)
        with col_title:
            st.title("🏪 Sistema Completo de Vendas & Análise Financeira")
            st.caption("Gestão inteligente de vendas com análise financeira em tempo real")
    except FileNotFoundError:
        st.title("🏪 Sistema Completo de Vendas & Análise Financeira")
        st.caption("Gestão inteligente de vendas com análise financeira em tempo real")
    except Exception as e:
        st.title("🏪 Sistema Completo de Vendas & Análise Financeira")
        st.caption("Gestão inteligente de vendas com análise financeira em tempo real")

    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    tab1, tab2, tab3, tab4 = st.tabs(["📝 Registrar Venda", "📈 Análise Detalhada", "💡 Estatísticas", "💰 Análise Contábil"])

    with tab1:
        st.header("📝 Registrar Nova Venda")
        with st.form("venda_form"):
            data_input = st.date_input("📅 Data da Venda", value=datetime.now(), format="DD/MM/YYYY")
            col1, col2, col3 = st.columns(3)
            with col1: cartao_input = st.number_input("💳 Cartão (R$)", min_value=0.0, value=0.0, format="%.2f", key="cartao_venda")
            with col2: dinheiro_input = st.number_input("💵 Dinheiro (R$)", min_value=0.0, value=0.0, format="%.2f", key="dinheiro_venda")
            with col3: pix_input = st.number_input("📱 PIX (R$)", min_value=0.0, value=0.0, format="%.2f", key="pix_venda")
            total_venda_form = (cartao_input or 0.0) + (dinheiro_input or 0.0) + (pix_input or 0.0)
            st.markdown(f"### **💰 Total da venda: {format_brl(total_venda_form)}**")
            submitted = st.form_submit_button("✅ Registrar Venda", type="primary")
            if submitted:
                if total_venda_form > 0:
                    formatted_date = data_input.strftime('%d/%m/%Y')
                    worksheet_obj = get_worksheet()
                    if worksheet_obj and add_data_to_sheet(formatted_date, cartao_input, dinheiro_input, pix_input, worksheet_obj):
                        read_sales_data.clear(); process_data.clear()
                        st.success("✅ Venda registrada e dados recarregados!")
                        st.rerun()
                    elif not worksheet_obj: st.error("❌ Falha ao conectar à planilha. Venda não registrada.")
                else: st.warning("⚠️ O valor total da venda deve ser maior que zero.")

    # --- SIDEBAR COM FILTROS MELHORADOS ---
    selected_anos_filter, selected_meses_filter, selected_dias_rolling = [], [], []
    
    with st.sidebar:
        st.header("🔍 Filtros de Período")
        st.markdown("---")
        
        # Filtro de Anos
        if not df_processed.empty and 'Ano' in df_processed.columns and not df_processed['Ano'].isnull().all():
            anos_disponiveis = sorted(df_processed['Ano'].dropna().unique().astype(int), reverse=True)
            if anos_disponiveis:
                default_ano = [datetime.now().year] if datetime.now().year in anos_disponiveis else [anos_disponiveis[0]] if anos_disponiveis else []
                selected_anos_filter = st.multiselect("📅 Ano(s):", options=anos_disponiveis, default=default_ano)
                
                # Filtro de Meses
                if selected_anos_filter:
                    df_para_filtro_mes = df_processed[df_processed['Ano'].isin(selected_anos_filter)]
                    if not df_para_filtro_mes.empty and 'Mês' in df_para_filtro_mes.columns and not df_para_filtro_mes['Mês'].isnull().all():
                        meses_numeros_disponiveis = sorted(df_para_filtro_mes['Mês'].dropna().unique().astype(int))
                        meses_opcoes_dict = {m_num: meses_ordem[m_num-1] for m_num in meses_numeros_disponiveis if 1 <= m_num <= 12}
                        meses_opcoes_display = [f"{m_num} - {m_nome}" for m_num, m_nome in meses_opcoes_dict.items()]
                        default_mes_num = datetime.now().month
                        default_mes_str = f"{default_mes_num} - {meses_ordem[default_mes_num-1]}" if 1 <= default_mes_num <= 12 and meses_opcoes_dict else None
                        default_meses_selecionados = [default_mes_str] if default_mes_str and default_mes_str in meses_opcoes_display else meses_opcoes_display
                        selected_meses_str = st.multiselect("📆 Mês(es):", options=meses_opcoes_display, default=default_meses_selecionados)
                        selected_meses_filter = [int(m.split(" - ")[0]) for m in selected_meses_str]
                        
                        # NOVO: Filtro de Somatório dos Últimos N Dias
                        st.markdown("### 📊 Análise de Últimos Dias")
                        dias_opcoes = [1, 2, 3, 5, 7]
                        selected_dias_rolling = st.multiselect(
                            "🔄 Somatório dos últimos:",
                            options=dias_opcoes,
                            default=[7],
                            format_func=lambda x: f"Últimos {x} dia{'s' if x > 1 else ''}"
                        )
            else: 
                st.info("📊 Nenhum ano disponível para filtro.")
        else: 
            st.info("📊 Não há dados processados para aplicar filtros.")

    # Aplicar filtros
    df_filtered = df_processed.copy()
    if not df_filtered.empty:
        if selected_anos_filter and 'Ano' in df_filtered.columns: 
            df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos_filter)]
        if selected_meses_filter and 'Mês' in df_filtered.columns: 
            df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses_filter)]
        
        # Aplicar filtro de rolling days se selecionado
        if selected_dias_rolling:
            df_filtered = filter_by_rolling_days(df_filtered, selected_dias_rolling)

    # Mostrar informações dos filtros aplicados na sidebar
    if not df_filtered.empty:
        total_registros_filtrados = len(df_filtered)
        total_faturamento_filtrado = df_filtered['Total'].sum()
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📈 Resumo dos Filtros Aplicados")
        st.sidebar.metric("Registros Filtrados", total_registros_filtrados)
        st.sidebar.metric("Faturamento Filtrado", format_brl(total_faturamento_filtrado))
        
        # Mostrar informação sobre filtro de dias se aplicado
        if selected_dias_rolling:
            max_dias = max(selected_dias_rolling)
            st.sidebar.info(f"📅 Exibindo dados dos últimos {max_dias} dias")
    elif not df_processed.empty:
        st.sidebar.markdown("---")
        st.sidebar.info("Nenhum registro corresponde aos filtros selecionados.")
    
    with tab2:
        st.header("🔎 Análise Detalhada de Vendas")
        if not df_filtered.empty and 'DataFormatada' in df_filtered.columns:
            st.subheader("🧾 Tabela de Vendas Filtradas")
            cols_to_display_tab2 = ['DataFormatada', 'DiaSemana', 'DiaDoMes', 'Cartão', 'Dinheiro', 'Pix', 'Total']
            cols_existentes_tab2 = [col for col in cols_to_display_tab2 if col in df_filtered.columns]
            
            if cols_existentes_tab2: 
                st.dataframe(df_filtered[cols_existentes_tab2], use_container_width=True, height=600, hide_index=True)
            else: 
                st.info("Colunas necessárias para a tabela de dados filtrados não estão disponíveis.")
            
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

            st.subheader("📈 Evolução do Capital Acumulado")
            if 'Data' in df_filtered.columns and not df_filtered.empty and not df_filtered['Data'].isnull().all() and 'Total' in df_filtered.columns:
                improved_chart = create_improved_accumulation_chart(df_filtered)
                if improved_chart:
                    st.altair_chart(improved_chart, use_container_width=True)
                else:
                    st.info("Não foi possível gerar o gráfico de acumulação.")
            else: 
                st.info("Dados insuficientes (Data ou Total) para o gráfico de acúmulo.")
        else:
             if df_processed.empty and df_raw.empty and get_worksheet() is None: st.warning("Não foi possível carregar os dados. Verifique configurações e credenciais.")
             elif df_processed.empty: st.info("Não há dados processados para exibir. Verifique a planilha de origem.")
             elif df_filtered.empty: st.info("Nenhum dado corresponde aos filtros selecionados.")
             else: st.info("Não há dados para exibir na Análise Detalhada. Pode ser um problema no processamento.")

    with tab3:
        st.header("💡 Estatísticas e Tendências de Vendas")
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
            
            st.subheader("📈 Evolução dos Métodos de Pagamento")
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

    # --- TAB4: ANÁLISE CONTÁBIL COMPLETA ---
    with tab4:
        st.header("📊 Análise Contábil e Financeira Detalhada")
        
        st.markdown("""
        ### 📋 **Sobre esta Análise**
        
        Esta seção apresenta uma **análise contábil completa** do seu negócio, baseada nos dados de vendas filtrados. 
        Os cálculos seguem as **normas contábeis brasileiras** e consideram:
        
        - **Regime Tributário:** Simples Nacional (6% sobre receita tributável)
        - **Receita Tributável:** Apenas vendas via Cartão e PIX
        - **Receita Não Tributável:** Vendas em dinheiro (não declaradas)
        - **Custos Operacionais:** Funcionários, contadora e fornecedores
        """)
        
        # Parâmetros Financeiros
        with st.container(border=True):
            st.subheader("⚙️ Parâmetros para Simulação Contábil")
            st.markdown("Configure os valores abaixo para simular diferentes cenários financeiros:")
            
            col_param1, col_param2, col_param3 = st.columns(3)
            with col_param1:
                salario_minimo_input = st.number_input(
                    "💼 Salário Base Funcionário (R$)",
                    min_value=0.0, value=1550.0, format="%.2f",
                    help="Salário base do funcionário. Os encargos (55%) serão calculados automaticamente.",
                    key="salario_tab4"
                )
            with col_param2:
                custo_contadora_input = st.number_input(
                    "📋 Honorários Contábeis (R$)",
                    min_value=0.0, value=316.0, format="%.2f",
                    help="Valor mensal pago pelos serviços contábeis.",
                    key="contadora_tab4"
                )
            with col_param3:
                custo_fornecedores_percentual = st.number_input(
                    "📦 Custo dos Produtos (%)",
                    min_value=0.0, max_value=100.0, value=30.0, format="%.1f",
                    help="Percentual do faturamento destinado à compra de produtos (bebidas, frios, pães, etc.).",
                    key="fornecedores_tab4"
                )

        st.markdown("---")

        if df_filtered.empty or 'Total' not in df_filtered.columns:
            st.warning("📊 **Não há dados suficientes para análise contábil.** Ajuste os filtros ou registre vendas.")
        else:
            # Calcular resultados financeiros
            resultados = calculate_financial_results(
                df_filtered, salario_minimo_input, custo_contadora_input, custo_fornecedores_percentual
            )

            # === SEÇÃO 1: DEMONSTRATIVO DE RECEITAS ===
            with st.container(border=True):
                st.subheader("💰 Demonstrativo de Receitas")
                st.markdown("""
                **Explicação:** As receitas são classificadas entre tributáveis e não tributáveis conforme a legislação brasileira.
                No Simples Nacional, apenas as receitas declaradas (cartão e PIX) são tributadas.
                """)
                
                col_rec1, col_rec2, col_rec3 = st.columns(3)
                
                with col_rec1:
                    st.metric(
                        "📈 Faturamento Bruto Total",
                        format_brl(resultados['faturamento_bruto']),
                        help="Soma de todas as vendas (cartão + PIX + dinheiro)"
                    )
                
                with col_rec2:
                    st.metric(
                        "🏦 Receita Tributável",
                        format_brl(resultados['faturamento_tributavel']),
                        f"{((resultados['faturamento_tributavel'] / resultados['faturamento_bruto'] * 100) if resultados['faturamento_bruto'] > 0 else 0):.1f}% do total",
                        help="Vendas via cartão e PIX (sujeitas à tributação)"
                    )
                
                with col_rec3:
                    st.metric(
                        "💵 Receita Não Tributável",
                        format_brl(resultados['faturamento_nao_tributavel']),
                        f"{((resultados['faturamento_nao_tributavel'] / resultados['faturamento_bruto'] * 100) if resultados['faturamento_bruto'] > 0 else 0):.1f}% do total",
                        help="Vendas em dinheiro (não declaradas)"
                    )

                # Gráfico de Receitas
                if resultados['faturamento_bruto'] > 0:
                    receitas_data = pd.DataFrame({
                        'Tipo de Receita': ['Receita Tributável\n(Cartão + PIX)', 'Receita Não Tributável\n(Dinheiro)'],
                        'Valor': [resultados['faturamento_tributavel'], resultados['faturamento_nao_tributavel']]
                    })
                    receitas_data = receitas_data[receitas_data['Valor'] > 0]
                    
                    if not receitas_data.empty:
                        chart_receitas = alt.Chart(receitas_data).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color='#1f77b4').encode(
                            x=alt.X('Tipo de Receita:N', title=None),
                            y=alt.Y('Valor:Q', title='Valor (R$)', axis=alt.Axis(format=",.0f")),
                            tooltip=[
                                alt.Tooltip('Tipo de Receita:N', title='Tipo'),
                                alt.Tooltip('Valor:Q', title='Valor (R$)', format=",.2f")
                            ]
                        ).properties(
                            title="Composição das Receitas",
                            height=400
                        )
                        st.altair_chart(chart_receitas, use_container_width=True)

            st.markdown("---")

            # === SEÇÃO 2: DEMONSTRATIVO DE CUSTOS E DESPESAS ===
            with st.container(border=True):
                st.subheader("💸 Demonstrativo de Custos e Despesas")
                st.markdown("""
                **Explicação:** Os custos são classificados conforme sua natureza contábil:
                - **Tributos:** Impostos obrigatórios sobre a receita declarada
                - **Pessoal:** Salários e encargos trabalhistas
                - **Serviços:** Honorários profissionais
                - **Produtos:** Custo das mercadorias vendidas
                """)
                
                # Criar DataFrame dos custos
                custos_data = pd.DataFrame({
                    'Tipo de Custo': [
                        'Simples Nacional\n(6% s/ Tributável)',
                        'Folha de Pagamento\n(Salário + Encargos)',
                        'Serviços Contábeis\n(Honorários)',
                        f'Custo dos Produtos\n({custo_fornecedores_percentual}% s/ Faturamento)'
                    ],
                    'Valor': [
                        resultados['imposto_simples'],
                        resultados['custo_funcionario'],
                        resultados['custo_contadora'],
                        resultados['custo_fornecedores_valor']
                    ],
                    'Categoria': ['Tributos', 'Pessoal', 'Serviços', 'Produtos']
                })
                custos_data = custos_data[custos_data['Valor'] > 0]
                
                if not custos_data.empty:
                    custos_data['Percentual do Faturamento'] = (custos_data['Valor'] / resultados['faturamento_bruto'] * 100) if resultados['faturamento_bruto'] > 0 else 0
                    
                    # Gráfico de custos por categoria
                    chart_custos = alt.Chart(custos_data).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                        x=alt.X('Tipo de Custo:N', title=None, axis=alt.Axis(labelAngle=-20)),
                        y=alt.Y('Valor:Q', title='Valor (R$)', axis=alt.Axis(format=",.0f")),
                        color=alt.Color('Categoria:N', 
                                      scale=alt.Scale(range=['#d62728', '#ff7f0e', '#2ca02c', '#9467bd']),
                                      legend=alt.Legend(title="Categoria")),
                        tooltip=[
                            alt.Tooltip('Tipo de Custo:N', title='Custo'),
                            alt.Tooltip('Categoria:N', title='Categoria'),
                            alt.Tooltip('Valor:Q', title='Valor (R$)', format=",.2f"),
                            alt.Tooltip('Percentual do Faturamento:Q', title='% do Faturamento', format=".2f")
                        ]
                    ).properties(
                        title="Composição dos Custos e Despesas por Categoria",
                        height=500
                    )
                    st.altair_chart(chart_custos, use_container_width=True)
                    
                    # Detalhamento textual dos custos
                    st.markdown("**📋 Detalhamento dos Custos:**")
                    for _, row in custos_data.iterrows():
                        st.markdown(f"- **{row['Tipo de Custo'].replace(chr(10), ' ')}:** {format_brl(row['Valor'])} ({row['Percentual do Faturamento']:.2f}% do faturamento)")
                    
                    st.markdown(f"""
                    **📊 Total Geral de Custos:** **{format_brl(resultados['total_custos'])}** 
                    ({(resultados['total_custos'] / resultados['faturamento_bruto'] * 100) if resultados['faturamento_bruto'] > 0 else 0:.2f}% do Faturamento Bruto)
                    """)

            st.markdown("---")

            # === SEÇÃO 3: DEMONSTRATIVO DE RESULTADOS ===
            with st.container(border=True):
                st.subheader("🎯 Demonstrativo de Resultados (DRE Simplificado)")
                st.markdown("""
                **Explicação:** O DRE mostra a formação do resultado financeiro do período, seguindo a estrutura contábil padrão.
                """)
                
                # Criar DRE estruturado
                dre_data = {
                    'Item': [
                        '(+) Receita Bruta Total',
                        '(-) Impostos sobre Vendas',
                        '(=) Receita Líquida',
                        '(-) Custo dos Produtos Vendidos',
                        '(=) Lucro Bruto',
                        '(-) Despesas Operacionais',
                        '    • Folha de Pagamento',
                        '    • Serviços Contábeis',
                        '(=) Lucro Operacional Final'
                    ],
                    'Valor': [
                        resultados['faturamento_bruto'],
                        -resultados['imposto_simples'],
                        resultados['faturamento_bruto'] - resultados['imposto_simples'],
                        -resultados['custo_fornecedores_valor'],
                        resultados['faturamento_bruto'] - resultados['imposto_simples'] - resultados['custo_fornecedores_valor'],
                        -(resultados['custo_funcionario'] + resultados['custo_contadora']),
                        -resultados['custo_funcionario'],
                        -resultados['custo_contadora'],
                        resultados['lucro_bruto']
                    ]
                }
                
                dre_df = pd.DataFrame(dre_data)
                
                # Exibir DRE em formato de tabela
                st.markdown("**📊 Demonstração do Resultado do Exercício (DRE):**")
                for i, row in dre_df.iterrows():
                    if row['Item'].startswith('(=)'):
                        st.markdown(f"**{row['Item']}** | **{format_brl(row['Valor'])}**")
                    elif row['Item'].startswith('    •'):
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{row['Item']} | {format_brl(row['Valor'])}")
                    else:
                        st.markdown(f"{row['Item']} | {format_brl(row['Valor'])}")
                
                st.markdown("---")
                
                # Métricas de resultado
                col_result1, col_result2 = st.columns(2)
                
                with col_result1:
                    st.metric(
                        "💰 Lucro Operacional",
                        format_brl(resultados['lucro_bruto']),
                        f"{resultados['margem_lucro_bruto']:.2f}% do Faturamento",
                        delta_color="normal" if resultados['lucro_bruto'] >= 0 else "inverse"
                    )
                    st.caption("Resultado após todos os custos e despesas operacionais")
                
                with col_result2:
                    st.metric(
                        "🏦 Diferença (Bruto - Tributável)",
                        format_brl(resultados['lucro_liquido']),
                        f"{resultados['margem_lucro_liquido']:.2f}% do Faturamento",
                        delta_color="off"
                    )
                    st.caption("Diferença entre faturamento total e receita declarada")

            st.markdown("---")

            # === SEÇÃO 4: ANÁLISE DE INDICADORES ===
            with st.container(border=True):
                st.subheader("📈 Análise de Indicadores Financeiros")
                st.markdown("""
                **Explicação:** Os indicadores financeiros ajudam a avaliar a saúde econômica do negócio e comparar com benchmarks do setor.
                """)
                
                # Calcular indicadores
                if resultados['faturamento_bruto'] > 0:
                    indicadores = {
                        'Margem Bruta': (resultados['faturamento_bruto'] - resultados['custo_fornecedores_valor']) / resultados['faturamento_bruto'] * 100,
                        'Margem Operacional': resultados['margem_lucro_bruto'],
                        'Carga Tributária': resultados['imposto_simples'] / resultados['faturamento_bruto'] * 100,
                        'Custo de Pessoal': resultados['custo_funcionario'] / resultados['faturamento_bruto'] * 100,
                        'Custo dos Produtos': resultados['custo_fornecedores_valor'] / resultados['faturamento_bruto'] * 100
                    }
                    
                    # Exibir indicadores
                    col_ind1, col_ind2, col_ind3 = st.columns(3)
                    
                    with col_ind1:
                        st.metric("📊 Margem Bruta", f"{indicadores['Margem Bruta']:.1f}%")
                        st.metric("🏛️ Carga Tributária", f"{indicadores['Carga Tributária']:.1f}%")
                    
                    with col_ind2:
                        st.metric("💼 Margem Operacional", f"{indicadores['Margem Operacional']:.1f}%")
                        st.metric("👥 Custo de Pessoal", f"{indicadores['Custo de Pessoal']:.1f}%")
                    
                    with col_ind3:
                        st.metric("📦 Custo dos Produtos", f"{indicadores['Custo dos Produtos']:.1f}%")
                    
                    # Gráfico de indicadores
                    indicadores_df = pd.DataFrame({
                        'Indicador': list(indicadores.keys()),
                        'Percentual': list(indicadores.values())
                    })
                    
                    chart_indicadores = alt.Chart(indicadores_df).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color='#17becf').encode(
                        x=alt.X('Indicador:N', title=None, axis=alt.Axis(labelAngle=-30)),
                        y=alt.Y('Percentual:Q', title='Percentual (%)', axis=alt.Axis(format=".1f")),
                        tooltip=[
                            alt.Tooltip('Indicador:N', title='Indicador'),
                            alt.Tooltip('Percentual:Q', title='Percentual (%)', format=".2f")
                        ]
                    ).properties(
                        title="Indicadores Financeiros (%)",
                        height=400
                    )
                    st.altair_chart(chart_indicadores, use_container_width=True)

            st.markdown("---")

            # === SEÇÃO 5: ALERTAS E RECOMENDAÇÕES ===
            with st.container(border=True):
                st.subheader("🚨 Alertas e Recomendações Contábeis")
                
                # Análise automática dos resultados
                if resultados['faturamento_bruto'] > 0:
                    margem_op = resultados['margem_lucro_bruto']
                    
                    if margem_op < 5:
                        st.error(f"""
                        🚨 **ALERTA CRÍTICO:** Margem operacional muito baixa ({margem_op:.1f}%)
                        
                        **Recomendações urgentes:**
                        - Revisar preços de venda
                        - Negociar melhores condições com fornecedores
                        - Analisar custos operacionais excessivos
                        - Considerar otimização de processos
                        """)
                    
                    elif margem_op < 15:
                        st.warning(f"""
                        ⚠️ **ATENÇÃO:** Margem operacional moderada ({margem_op:.1f}%)
                        
                        **Recomendações:**
                        - Monitorar custos de perto
                        - Buscar oportunidades de otimização
                        - Avaliar estratégias de aumento de receita
                        """)
                    
                    else:
                        st.success(f"""
                        ✅ **EXCELENTE:** Margem operacional saudável ({margem_op:.1f}%)
                        
                        **Recomendações:**
                        - Manter o controle atual
                        - Considerar investimentos em crescimento
                        - Criar reservas para contingências
                        """)
                    
                    # Alertas específicos
                    if resultados['faturamento_nao_tributavel'] / resultados['faturamento_bruto'] > 0.5:
                        st.info(f"""
                        💡 **OBSERVAÇÃO FISCAL:** Alto percentual de vendas em dinheiro ({(resultados['faturamento_nao_tributavel'] / resultados['faturamento_bruto'] * 100):.1f}%)
                        
                        Considere os aspectos legais e fiscais desta situação.
                        """)

            st.markdown("---")
            
            # Nota final
