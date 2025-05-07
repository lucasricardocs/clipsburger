import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, APIError
import time
import re

# =============================================
# CONFIGURAÇÃO INICIAL
# =============================================

st.set_page_config(
    page_title="Sistema de Registro do Clips Burger",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Dicionário de meses para exibição
MESES_NOMES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# =============================================
# FUNÇÕES AUXILIARES
# =============================================

def sanitize_number(value):
    """Limpa e valida valores numéricos"""
    if isinstance(value, str):
        value = re.sub(r'[^\d.]', '', value)
        try:
            return float(value) if value else 0.0
        except ValueError:
            return 0.0
    return float(value) if value is not None else 0.0

def validate_date_format(date_str):
    """Valida se a string de data está no formato correto dd/mm/yyyy"""
    try:
        datetime.strptime(date_str, '%d/%m/%Y')
        return True
    except ValueError:
        return False

def format_currency(value):
    """Formata valor como moeda brasileira"""
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# =============================================
# CONEXÃO COM GOOGLE SHEETS
# =============================================

@st.cache_data(ttl=300)
def read_google_sheet(worksheet_name="Vendas"):
    """Função para ler os dados da planilha Google Sheets"""
    try:
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        
        spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
        
        try:
            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            rows = worksheet.get_all_records()
            df = pd.DataFrame(rows)
            return df, worksheet
        except SpreadsheetNotFound:
            st.error(f"Aba '{worksheet_name}' não encontrada na planilha!")
            return pd.DataFrame(), None
        except APIError as e:
            st.error(f"Erro na API do Google Sheets: {e}")
            return pd.DataFrame(), None
    except Exception as e:
        st.error(f"Erro de autenticação: {e}")
        return pd.DataFrame(), None

def append_row(worksheet_name, row_data):
    """Função para adicionar uma linha à planilha Google Sheets"""
    try:
        df, worksheet = read_google_sheet(worksheet_name)
        if worksheet:
            worksheet.append_row(row_data)
            time.sleep(1)  # Delay para evitar rate limits
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao adicionar linha: {e}")
        return False

# =============================================
# PROCESSAMENTO DE DADOS
# =============================================

def safe_date_conversion(df, date_column='Data'):
    """Conversão segura de datas com tratamento de erros"""
    if date_column not in df.columns:
        return df
    
    # Tentar converter para datetime
    df[date_column] = pd.to_datetime(df[date_column], errors='coerce', format='%d/%m/%Y')
    
    # Verificar se alguma data não foi convertida
    if df[date_column].isna().any():
        st.warning(f"Algumas datas na coluna '{date_column}' não puderam ser convertidas")
    
    return df

def process_vendas(df):
    """Função para processar dados de vendas"""
    if df.empty:
        return df
    
    # Padronizar nomes de colunas
    df.columns = [col.strip().capitalize() for col in df.columns]
    
    # Verificar colunas de pagamento
    payment_cols = []
    for col in ['Cartão', 'Dinheiro', 'Pix']:
        if col in df.columns:
            payment_cols.append(col)
            df[col] = df[col].apply(sanitize_number)
    
    if payment_cols:
        df['Total'] = df[payment_cols].sum(axis=1)
    
    # Processar datas de forma segura
    df = safe_date_conversion(df)
    
    if 'Data' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Data']):
        # Extrair componentes da data
        df['Ano'] = df['Data'].dt.year
        df['Mês'] = df['Data'].dt.month
        df['Dia'] = df['Data'].dt.day
        df['DiaSemana'] = df['Data'].dt.day_name()
        df['MêsNome'] = df['Data'].dt.month.map(MESES_NOMES)
        df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
        df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
        
        df = df.sort_values('Data', ascending=False)
    
    return df

def process_compras(df):
    """Função para processar dados de compras"""
    if df.empty:
        return df
    
    # Padronizar nomes de colunas
    df.columns = [col.strip().capitalize() for col in df.columns]
    
    # Processar valores
    for col in ['Pão', 'Frios', 'Bebidas']:
        if col in df.columns:
            df[col] = df[col].apply(sanitize_number)
    
    if all(col in df.columns for col in ['Pão', 'Frios', 'Bebidas']):
        df['Total'] = df['Pão'] + df['Frios'] + df['Bebidas']
    
    # Processar datas de forma segura
    df = safe_date_conversion(df)
    
    if 'Data' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Data']):
        # Extrair componentes da data
        df['Ano'] = df['Data'].dt.year
        df['Mês'] = df['Data'].dt.month
        df['DiaSemana'] = df['Data'].dt.day_name()
        df['MêsNome'] = df['Data'].dt.month.map(MESES_NOMES)
        df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
        df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
        
        df = df.sort_values('Data', ascending=False)
    
    return df

# =============================================
# INTERFACE DO USUÁRIO
# =============================================

def get_date_filters(df):
    """Cria filtros de data na sidebar e retorna os valores selecionados"""
    hoje = datetime.now()
    ano_atual = hoje.year
    mes_atual = hoje.month
    
    if df.empty or 'Ano' not in df.columns:
        return ano_atual, mes_atual
    
    anos_disponiveis = sorted(df['Ano'].unique(), reverse=True)
    
    with st.sidebar:
        st.subheader("🔍 Filtros de Período")
        
        # Filtro de Ano
        ano_selecionado = st.selectbox(
            "Ano:",
            options=anos_disponiveis,
            index=0 if not anos_disponiveis else anos_disponiveis.index(ano_atual) if ano_atual in anos_disponiveis else 0
        )
        
        # Filtro de Mês
        meses_disponiveis = sorted(df[df['Ano'] == ano_selecionado]['Mês'].unique(), reverse=True) if 'Mês' in df.columns else []
        
        if not meses_disponiveis:
            return ano_selecionado, None
        
        # Criar opções de mês com nome
        meses_opcoes = [f"{mes} - {MESES_NOMES[mes]}" for mes in meses_disponiveis]
        
        # Encontrar índice do mês atual
        indice_mes_atual = 0
        if ano_selecionado == ano_atual and mes_atual in meses_disponiveis:
            indice_mes_atual = meses_disponiveis.index(mes_atual)
        
        mes_selecionado_str = st.selectbox(
            "Mês:",
            options=meses_opcoes,
            index=indice_mes_atual
        )
        
        # Extrair número do mês selecionado
        mes_selecionado = int(mes_selecionado_str.split(" - ")[0]) if mes_selecionado_str else None
        
        st.divider()
        
    return ano_selecionado, mes_selecionado

def show_sidebar_summary(df_vendas, df_compras):
    """Mostra resumo na sidebar"""
    with st.sidebar:
        st.subheader("📊 Resumo Rápido")
        
        if not df_vendas.empty and 'Total' in df_vendas.columns:
            total_vendas = df_vendas['Total'].sum()
            st.metric("Total de Vendas", format_currency(total_vendas))
            
            if 'Data' in df_vendas.columns and pd.api.types.is_datetime64_any_dtype(df_vendas['Data']):
                ultima_data = df_vendas['Data'].max()
                ultimo_total = df_vendas[df_vendas['Data'] == ultima_data]['Total'].sum()
                st.metric(f"Último Dia ({ultima_data.strftime('%d/%m')})", format_currency(ultimo_total))
        
        if not df_compras.empty and 'Total' in df_compras.columns:
            total_compras = df_compras['Total'].sum()
            st.metric("Total de Compras", format_currency(total_compras))
        
        st.divider()

def show_vendas_tab(df_vendas_filtrado):
    """Mostra a aba de Análise de Vendas"""
    st.header("Análise de Vendas")
    
    if not df_vendas_filtrado.empty:
        st.subheader(f"Vendas de {MESES_NOMES.get(mes_selecionado, '')} {ano_selecionado}")
        
        # Métricas principais
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total do Período", format_currency(df_vendas_filtrado['Total'].sum()))
        with col2:
            st.metric("Média Diária", format_currency(df_vendas_filtrado.groupby('Data')['Total'].sum().mean()))
        with col3:
            st.metric("Dias com Venda", df_vendas_filtrado['Data'].nunique())
        
        # Gráfico de vendas diárias
        st.subheader("Vendas Diárias")
        vendas_diarias = df_vendas_filtrado.groupby('Data')['Total'].sum().reset_index()
        
        chart = alt.Chart(vendas_diarias).mark_bar().encode(
            x=alt.X('Data:T', title='Data'),
            y=alt.Y('Total:Q', title='Valor (R$)'),
            tooltip=['Data', 'Total']
        ).properties(height=400)
        
        st.altair_chart(chart, use_container_width=True)
        
        # Gráfico por forma de pagamento
        st.subheader("Distribuição por Forma de Pagamento")
        if all(col in df_vendas_filtrado.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
            pagamentos = df_vendas_filtrado[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
            pagamentos.columns = ['Meio', 'Valor']
            
            pie_chart = alt.Chart(pagamentos).mark_arc().encode(
                theta='Valor',
                color='Meio',
                tooltip=['Meio', 'Valor']
            ).properties(height=300)
            
            st.altair_chart(pie_chart, use_container_width=True)
        
        # Tabela detalhada
        st.subheader("Detalhes das Vendas")
        st.dataframe(
            df_vendas_filtrado[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Nenhuma venda encontrada para o período selecionado")

def show_compras_tab(df_compras_filtrado):
    """Mostra a aba de Análise de Compras"""
    st.header("Análise de Compras")
    
    if not df_compras_filtrado.empty:
        st.subheader(f"Compras de {MESES_NOMES.get(mes_selecionado, '')} {ano_selecionado}")
        
        # Métricas principais
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total do Período", format_currency(df_compras_filtrado['Total'].sum()))
        with col2:
            st.metric("Média Diária", format_currency(df_compras_filtrado.groupby('Data')['Total'].sum().mean()))
        with col3:
            st.metric("Dias com Compra", df_compras_filtrado['Data'].nunique())
        
        # Gráfico de compras por categoria
        st.subheader("Distribuição por Categoria")
        if all(col in df_compras_filtrado.columns for col in ['Pão', 'Frios', 'Bebidas']):
            categorias = df_compras_filtrado[['Pão', 'Frios', 'Bebidas']].sum().reset_index()
            categorias.columns = ['Categoria', 'Valor']
            
            bar_chart = alt.Chart(categorias).mark_bar().encode(
                x='Categoria',
                y='Valor',
                color='Categoria',
                tooltip=['Categoria', 'Valor']
            ).properties(height=400)
            
            st.altair_chart(bar_chart, use_container_width=True)
        
        # Tabela detalhada
        st.subheader("Detalhes das Compras")
        st.dataframe(
            df_compras_filtrado[['DataFormatada', 'Pão', 'Frios', 'Bebidas', 'Total']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Nenhuma compra encontrada para o período selecionado")

def show_estatisticas_tab(df_vendas):
    """Mostra a aba de Estatísticas"""
    st.header("📈 Estatísticas Comparativas")
    
    if not df_vendas.empty:
        # Estatísticas mensais
        st.subheader("Desempenho Mensal")
        
        if 'Ano' in df_vendas.columns and 'Mês' in df_vendas.columns and 'Total' in df_vendas.columns:
            vendas_mensais = df_vendas.groupby(['Ano', 'Mês'])['Total'].sum().reset_index()
            vendas_mensais['AnoMês'] = vendas_mensais['Ano'].astype(str) + '-' + vendas_mensais['Mês'].astype(str).str.zfill(2)
            vendas_mensais['MêsNome'] = vendas_mensais['Mês'].map(MESES_NOMES)
            
            # Gráfico de linhas - Evolução mensal
            line_chart = alt.Chart(vendas_mensais).mark_line(point=True).encode(
                x=alt.X('AnoMês:N', title='Período', sort=None),
                y=alt.Y('Total:Q', title='Total de Vendas (R$)'),
                tooltip=['Ano', 'MêsNome', 'Total']
            ).properties(height=400)
            
            st.altair_chart(line_chart, use_container_width=True)
            
            # Comparativo com meses anteriores
            if mes_selecionado:
                st.subheader(f"Comparativo de {MESES_NOMES.get(mes_selecionado, '')}")
                
                meses_anteriores = df_vendas[
                    (df_vendas['Mês'] == mes_selecionado) & 
                    (df_vendas['Ano'] < ano_selecionado)
                ]
                
                if not meses_anteriores.empty:
                    comparativo = meses_anteriores.groupby('Ano')['Total'].sum().reset_index()
                    comparativo['Ano'] = comparativo['Ano'].astype(str)
                    
                    current_year_total = df_vendas_filtrado['Total'].sum() if not df_vendas_filtrado.empty else 0
                    
                    bar_chart = alt.Chart(comparativo).mark_bar().encode(
                        x='Ano',
                        y='Total',
                        color=alt.value('#1f77b4'),
                        tooltip=['Ano', 'Total']
                    ).properties(height=300)
                    
                    current_rule = alt.Chart(pd.DataFrame({'Total': [current_year_total]})).mark_rule(
                        color='red',
                        strokeWidth=2
                    ).encode(y='Total')
                    
                    st.altair_chart(bar_chart + current_rule, use_container_width=True)
                    st.caption(f"Linha vermelha mostra o total de {ano_selecionado}")
                else:
                    st.info("Não há dados de meses anteriores para comparação")
    else:
        st.warning("Nenhum dado de vendas disponível para análise")

def show_registro_tab():
    """Mostra a aba de Registro de Dados"""
    st.header("Registro de Dados")
    
    reg_type = st.radio("Selecione o tipo de registro:", ["💰 Vendas", "🛍️ Compras"], horizontal=True)
    st.divider()
    
    if reg_type == "💰 Vendas":
        st.subheader("📝 Registro de Vendas")
        with st.form("form_vendas"):
            data_venda = st.date_input("Data da Venda", value=datetime.today())
            
            col1, col2, col3 = st.columns(3)
            with col1:
                cartao = st.number_input("Cartão (R$)", min_value=0.0, step=0.01, format="%.2f")
            with col2:
                dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, step=0.01, format="%.2f")
            with col3:
                pix = st.number_input("PIX (R$)", min_value=0.0, step=0.01, format="%.2f")
            
            total = cartao + dinheiro + pix
            st.metric("Total da Venda", format_currency(total))
            
            col1, col2 = st.columns(2)
            with col1:
                enviar_venda = st.form_submit_button("📥 Registrar Venda", use_container_width=True)
            with col2:
                cancel_button = st.form_submit_button("❌ Cancelar", use_container_width=True)
            
            if enviar_venda:
                if total > 0:
                    with st.spinner("Registrando venda..."):
                        if append_row("Vendas", [data_venda.strftime('%d/%m/%Y'), cartao, dinheiro, pix]):
                            st.success("✅ Venda registrada com sucesso!")
                            st.balloons()
                            time.sleep(1)
                            st.experimental_rerun()
                else:
                    st.warning("⚠️ O valor total precisa ser maior que zero.")
        
        st.subheader("📋 Últimas Vendas Registradas")
        df_ultimas_vendas, _ = read_google_sheet("Vendas")
        if not df_ultimas_vendas.empty:
            df_ultimas_vendas = process_vendas(df_ultimas_vendas)
            st.dataframe(
                df_ultimas_vendas[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']].head(10),
                use_container_width=True,
                hide_index=True,
                column_config={
                    'DataFormatada': st.column_config.TextColumn('Data'),
                    'Cartão': st.column_config.NumberColumn('Cartão (R$)', format="R$ %.2f"),
                    'Dinheiro': st.column_config.NumberColumn('Dinheiro (R$)', format="R$ %.2f"),
                    'Pix': st.column_config.NumberColumn('PIX (R$)', format="R$ %.2f"),
                    'Total': st.column_config.NumberColumn('Total (R$)', format="R$ %.2f")
                }
            )
    
    else:
        st.subheader("📝 Registro de Compras")
        with st.form("form_compras"):
            data_compra = st.date_input("Data da Compra", value=datetime.today())
            
            col1, col2, col3 = st.columns(3)
            with col1:
                pao = st.number_input("Pão (R$)", min_value=0.0, step=0.01, format="%.2f")
            with col2:
                frios = st.number_input("Frios (R$)", min_value=0.0, step=0.01, format="%.2f")
            with col3:
                bebidas = st.number_input("Bebidas (R$)", min_value=0.0, step=0.01, format="%.2f")
            
            total_compra = pao + frios + bebidas
            st.metric("Total da Compra", format_currency(total_compra))
            
            col1, col2 = st.columns(2)
            with col1:
                enviar_compra = st.form_submit_button("📥 Registrar Compra", use_container_width=True)
            with col2:
                cancel_button = st.form_submit_button("❌ Cancelar", use_container_width=True)
            
            if enviar_compra:
                if total_compra > 0:
                    with st.spinner("Registrando compra..."):
                        if append_row("Compras", [data_compra.strftime('%d/%m/%Y'), pao, frios, bebidas]):
                            st.success("✅ Compra registrada com sucesso!")
                            time.sleep(1)
                            st.experimental_rerun()
                else:
                    st.warning("⚠️ O valor total precisa ser maior que zero.")
        
        st.subheader("📋 Últimas Compras Registradas")
        df_ultimas_compras, _ = read_google_sheet("Compras")
        if not df_ultimas_compras.empty:
            df_ultimas_compras = process_compras(df_ultimas_compras)
            st.dataframe(
                df_ultimas_compras[['DataFormatada', 'Pão', 'Frios', 'Bebidas', 'Total']].head(10),
                use_container_width=True,
                hide_index=True,
                column_config={
                    'DataFormatada': st.column_config.TextColumn('Data'),
                    'Pão': st.column_config.NumberColumn('Pão (R$)', format="R$ %.2f"),
                    'Frios': st.column_config.NumberColumn('Frios (R$)', format="R$ %.2f"),
                    'Bebidas': st.column_config.NumberColumn('Bebidas (R$)', format="R$ %.2f"),
                    'Total': st.column_config.NumberColumn('Total (R$)', format="R$ %.2f")
                }
            )

# =============================================
# FUNÇÃO PRINCIPAL
# =============================================

def main():
    st.title("📊 Sistema de Registro do Clips Burger")
    
    try:
        st.image("logo.png", width=200)
    except:
        st.info("💡 Adicione um arquivo 'logo.png' na pasta do aplicativo para personalizar o sistema.")
    
    # Carregar dados
    with st.spinner("Carregando dados..."):
        df_vendas, _ = read_google_sheet("Vendas")
        df_compras, _ = read_google_sheet("Compras")
        
        df_vendas = process_vendas(df_vendas)
        df_compras = process_compras(df_compras)
    
    # Filtros na sidebar
    global ano_selecionado, mes_selecionado, df_vendas_filtrado, df_compras_filtrado
    ano_selecionado, mes_selecionado = get_date_filters(df_vendas)
    
    # Filtrar dados pelo período selecionado (com verificações de segurança)
    df_vendas_filtrado = pd.DataFrame()
    if not df_vendas.empty:
        filter_conditions = []
        if 'Ano' in df_vendas.columns and ano_selecionado:
            filter_conditions.append(df_vendas['Ano'] == ano_selecionado)
        if 'Mês' in df_vendas.columns and mes_selecionado:
            filter_conditions.append(df_vendas['Mês'] == mes_selecionado)
        
        if filter_conditions:
            df_vendas_filtrado = df_vendas[pd.concat(filter_conditions, axis=1).all(axis=1)]
        else:
            df_vendas_filtrado = df_vendas
    
    df_compras_filtrado = pd.DataFrame()
    if not df_compras.empty:
        filter_conditions = []
        if 'Ano' in df_compras.columns and ano_selecionado:
            filter_conditions.append(df_compras['Ano'] == ano_selecionado)
        if 'Mês' in df_compras.columns and mes_selecionado:
            filter_conditions.append(df_compras['Mês'] == mes_selecionado)
        
        if filter_conditions:
            df_compras_filtrado = df_compras[pd.concat(filter_conditions, axis=1).all(axis=1)]
        else:
            df_compras_filtrado = df_compras
    
    # Resumo na sidebar
    show_sidebar_summary(df_vendas_filtrado, df_compras_filtrado)
    
    # Abas principais
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Registro", "📊 Análise de Vendas", "🛒 Análise de Compras", "📈 Estatísticas"])

    with tab1:
        show_registro_tab()

    with tab2:
        show_vendas_tab(df_vendas_filtrado)

    with tab3:
        show_compras_tab(df_compras_filtrado)

    with tab4:
        show_estatisticas_tab(df_vendas)

    # Rodapé
    st.divider()
    st.markdown(
        """
        <div style='text-align: center; color: gray; font-size: small;'>
            © 2023 Clips Burger - Sistema de Gestão | Desenvolvido com Streamlit
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
