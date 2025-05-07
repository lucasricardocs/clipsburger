import gspread
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import time
import re

# Configuração da página
st.set_page_config(page_title="Sistema de Registro do Clips Burger", layout="centered", initial_sidebar_state="expanded")

def sanitize_number(value):
    """Limpa e valida valores numéricos"""
    if isinstance(value, str):
        # Remove caracteres não numéricos, exceto o ponto decimal
        value = re.sub(r'[^\d.]', '', value)
        # Converte para float se possível
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
    return f"R$ {value:.2f}".replace('.', ',')

def read_google_sheet(worksheet_name="Vendas"):
    """Função para ler os dados da planilha Google Sheets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 
                 'https://www.googleapis.com/auth/spreadsheets.readonly', 
                 'https://www.googleapis.com/auth/drive.readonly']
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'  # ID da planilha "VendasPitDog"
        try:
            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            rows = worksheet.get_all_records()
            df = pd.DataFrame(rows)
            return df, worksheet
        except SpreadsheetNotFound:
            st.error(f"Planilha com ID {spreadsheet_id} não encontrada.")
            return pd.DataFrame(), None
    except Exception as e:
        st.error(f"Erro de autenticação: {e}")
        return pd.DataFrame(), None

def append_row(worksheet_name, row_data):
    """Função para adicionar uma linha à planilha Google Sheets"""
    try:
        _, worksheet = read_google_sheet(worksheet_name)
        if worksheet:
            worksheet.append_row(row_data)
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao adicionar linha: {e}")
        return False

def process_data(df):
    """Função para processar e preparar os dados"""
    if not df.empty:
        # Aplicar conversão de tipo para colunas numéricas
        for col in ['Cartão', 'Dinheiro', 'Pix', 'PIX']:
            if col in df.columns:
                df[col] = df[col].apply(sanitize_number)
        
        # Calcular o total das vendas
        if all(col in df.columns for col in ['Cartão', 'Dinheiro', 'Pix']):
            df['Total'] = df['Cartão'].fillna(0) + df['Dinheiro'].fillna(0) + df['Pix'].fillna(0)
        elif all(col in df.columns for col in ['Cartão', 'Dinheiro', 'PIX']):
            df['Total'] = df['Cartão'].fillna(0) + df['Dinheiro'].fillna(0) + df['PIX'].fillna(0)
            
        # Processar coluna de data
        if 'Data' in df.columns:
            try:
                # Converter strings de data para datetime
                date_mask = df['Data'].apply(lambda x: validate_date_format(str(x)) if x else False)
                valid_dates = df[date_mask]
                invalid_dates = df[~date_mask]
                
                if not invalid_dates.empty:
                    st.warning(f"Encontradas {len(invalid_dates)} linhas com datas em formato inválido.")
                
                df.loc[date_mask, 'Data'] = pd.to_datetime(df.loc[date_mask, 'Data'], format='%d/%m/%Y')
                
                # Extrair componentes da data
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['Dia'] = df['Data'].dt.day
                df['DiaSemana'] = df['Data'].dt.day_name()
                df['MêsNome'] = df['Data'].dt.strftime('%B')
                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                
                # Ordenar o DataFrame por data (mais recente primeiro)
                df = df.sort_values('Data', ascending=False)
            except Exception as e:
                st.error(f"Erro ao processar datas: {e}")
    return df

def process_vendas(df):
    """Função para processar dados de vendas"""
    if not df.empty:
        # Padronizar nomes de colunas
        if 'Pix' in df.columns and 'PIX' not in df.columns:
            df.rename(columns={'Pix': 'PIX'}, inplace=True)
            
        # Aplicar conversão para valores numéricos
        for col in ['Cartão', 'Dinheiro', 'PIX']:
            if col in df.columns:
                df[col] = df[col].apply(sanitize_number)
                
        # Calcular total
        df['Total'] = df['Cartão'].fillna(0) + df['Dinheiro'].fillna(0) + df['PIX'].fillna(0)
        
        # Processar datas
        if 'Data' in df.columns:
            try:
                # Verificar formato das datas
                date_mask = df['Data'].apply(lambda x: validate_date_format(str(x)) if x else False)
                df.loc[date_mask, 'Data'] = pd.to_datetime(df.loc[date_mask, 'Data'], format='%d/%m/%Y')
                
                # Extrair componentes
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['DiaSemana'] = df['Data'].dt.day_name()
                df['MêsNome'] = df['Data'].dt.strftime('%B')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                df['DiaMês'] = df['Data'].dt.strftime('%d/%m')
                
                # Ordenar do mais recente para o mais antigo
                df = df.sort_values('Data', ascending=False)
            except Exception as e:
                st.error(f"Erro ao processar datas de vendas: {e}")
    return df

def process_compras(df):
    """Função para processar dados de compras"""
    if not df.empty:
        # Aplicar conversão para valores numéricos
        for col in ['Pão', 'Frios', 'Bebidas']:
            if col in df.columns:
                df[col] = df[col].apply(sanitize_number)
                
        # Calcular total de compras
        df['Total'] = df['Pão'].fillna(0) + df['Frios'].fillna(0) + df['Bebidas'].fillna(0)
        
        # Processar datas
        if 'Data' in df.columns:
            try:
                # Verificar formato das datas
                date_mask = df['Data'].apply(lambda x: validate_date_format(str(x)) if x else False)
                df.loc[date_mask, 'Data'] = pd.to_datetime(df.loc[date_mask, 'Data'], format='%d/%m/%Y')
                
                # Extrair componentes
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['DiaSemana'] = df['Data'].dt.day_name()
                df['MêsNome'] = df['Data'].dt.strftime('%B')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                df['DiaMês'] = df['Data'].dt.strftime('%d/%m')
                
                # Ordenar do mais recente para o mais antigo
                df = df.sort_values('Data', ascending=False)
            except Exception as e:
                st.error(f"Erro ao processar datas de compras: {e}")
    return df

def get_current_month_stats(df):
    """Calcula estatísticas do mês atual"""
    if df.empty:
        return None
    
    # Identificar mês atual
    hoje = datetime.now()
    primeiro_dia_mes = datetime(hoje.year, hoje.month, 1)
    df_mes_atual = df[df['Data'] >= primeiro_dia_mes]
    
    if df_mes_atual.empty:
        return None
    
    stats = {
        'total_vendas': df_mes_atual['Total'].sum(),
        'media_diaria': df_mes_atual.groupby('Data').sum()['Total'].mean(),
        'total_dias': df_mes_atual['Data'].dt.date.nunique(),
        'dia_maior_venda': df_mes_atual.loc[df_mes_atual['Total'].idxmax()]['DataFormatada'] if not df_mes_atual.empty else "N/A",
        'valor_maior_venda': df_mes_atual['Total'].max() if not df_mes_atual.empty else 0
    }
    
    return stats

def get_date_range_options():
    """Gera opções de intervalos de datas para relatórios"""
    hoje = datetime.now()
    
    # Datas pré-definidas
    opcoes = {
        "Hoje": (hoje.date(), hoje.date()),
        "Ontem": ((hoje - timedelta(days=1)).date(), (hoje - timedelta(days=1)).date()),
        "Últimos 7 dias": ((hoje - timedelta(days=7)).date(), hoje.date()),
        "Últimos 30 dias": ((hoje - timedelta(days=30)).date(), hoje.date()),
        "Este mês": (datetime(hoje.year, hoje.month, 1).date(), hoje.date()),
        "Mês passado": (datetime(hoje.year if hoje.month > 1 else hoje.year - 1, 
                               hoje.month - 1 if hoje.month > 1 else 12, 1).date(),
                     (datetime(hoje.year if hoje.month > 1 else hoje.year - 1, 
                               hoje.month - 1 if hoje.month > 1 else 12, 1) + 
                      timedelta(days=32)).replace(day=1).date() - timedelta(days=1))
    }
    
    return opcoes

def main():
    st.title("📊 Sistema de Registro do Clips Burger")
    
    try:
        st.image("logo.png", width=200)
    except:
        st.info("💡 Dica: Adicione um arquivo 'logo.png' na pasta do aplicativo para personalizar o sistema.")
    
    # Sidebar para informações gerais
    st.sidebar.title("🍔 Clips Burger")
    
    # Carregar dados para exibir resumo rápido na sidebar
    with st.sidebar:
        with st.spinner("Carregando resumo..."):
            df_vendas_all, _ = read_google_sheet("Vendas")
            if not df_vendas_all.empty:
                df_vendas_all = process_vendas(df_vendas_all)
                stats = get_current_month_stats(df_vendas_all)
                
                st.subheader("📈 Resumo do Mês")
                if stats:
                    st.metric("Total de Vendas", format_currency(stats['total_vendas']))
                    st.metric("Média Diária", format_currency(stats['media_diaria']))
                else:
                    st.info("Sem dados para o mês atual")
                
                # Exibir últimas 5 vendas
                st.subheader("🔄 Últimas Vendas")
                if not df_vendas_all.empty:
                    for _, row in df_vendas_all.head(5).iterrows():
                        st.markdown(f"**{row['DataFormatada']}**: {format_currency(row['Total'])}")
        
        st.divider()
        st.info("Use as abas acima para registrar vendas/compras e visualizar relatórios detalhados.")
        
    # Abas principais do sistema
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Registro", "📊 Análise de Vendas", "🛒 Análise de Compras", "📈 Estatísticas"])

    with tab1:
        st.header("Registro de Dados")
        
        # Opção para selecionar registro de vendas ou compras
        reg_type = st.radio("Selecione o tipo de registro:", ["💰 Vendas", "🛍️ Compras"], horizontal=True)
        
        st.divider()
        
        if reg_type == "💰 Vendas":
            # Registro de Vendas
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
                st.metric("Total da Venda", f"R$ {total:.2f}")
                
                col1, col2 = st.columns(2)
                with col1:
                    enviar_venda = st.form_submit_button("📥 Registrar Venda", use_container_width=True)
                with col2:
                    cancel_button = st.form_submit_button("❌ Cancelar", use_container_width=True)
                
                if enviar_venda:
                    if total > 0:
                        with st.spinner("Registrando venda..."):
                            time.sleep(0.5)  # Pequeno delay para feedback visual
                            if append_row("Vendas", [data_venda.strftime('%d/%m/%Y'), cartao, dinheiro, pix]):
                                st.success("✅ Venda registrada com sucesso!")
                                st.balloons()
                    else:
                        st.warning("⚠️ O valor total precisa ser maior que zero.")
            
            # Exibir últimas vendas registradas
            st.subheader("📋 Últimas Vendas Registradas")
            with st.spinner("Carregando vendas recentes..."):
                df_ultimas_vendas, _ = read_google_sheet("Vendas")
                if not df_ultimas_vendas.empty:
                    df_ultimas_vendas = process_vendas(df_ultimas_vendas)
                    st.dataframe(
                        df_ultimas_vendas[['DataFormatada', 'Cartão', 'Dinheiro', 'PIX', 'Total']].head(10),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'DataFormatada': 'Data',
                            'Cartão': st.column_config.NumberColumn('Cartão (R$)', format="R$ %.2f"),
                            'Dinheiro': st.column_config.NumberColumn('Dinheiro (R$)', format="R$ %.2f"),
                            'PIX': st.column_config.NumberColumn('PIX (R$)', format="R$ %.2f"),
                            'Total': st.column_config.NumberColumn('Total (R$)', format="R$ %.2f")
                        }
                    )
                else:
                    st.info("Nenhuma venda registrada até o momento.")
        
        else:
            # Registro de Compras
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
                st.metric("Total da Compra", f"R$ {total_compra:.2f}")
                
                col1, col2 = st.columns(2)
                with col1:
                    enviar_compra = st.form_submit_button("📥 Registrar Compra", use_container_width=True)
                with col2:
                    cancel_button = st.form_submit_button("❌ Cancelar", use_container_width=True)
                
                if enviar_compra:
                    if total_compra > 0:
                        with st.spinner("Registrando compra..."):
                            time.sleep(0.5)  # Pequeno delay para feedback visual
                            if append_row("compras", [data_compra.strftime('%d/%m/%Y'), pao, frios, bebidas]):
                                st.success("✅ Compra registrada com sucesso!")
                    else:
                        st.warning("⚠️ O valor total precisa ser maior que zero.")
            
            # Exibir últimas compras registradas
            st.subheader("📋 Últimas Compras Registradas")
            with st.spinner("Carregando compras recentes..."):
                df_ultimas_compras, _ = read_google_sheet("compras")
                if not df_ultimas_compras.empty:
                    df_ultimas_compras = process_compras(df_ultimas_compras)
                    st.dataframe(
                        df_ultimas_compras[['DataFormatada', 'Pão', 'Frios', 'Bebidas', 'Total']].head(10),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'DataFormatada': 'Data',
                            'Pão': st.column_config.NumberColumn('Pão (R$)', format="R$ %.2f"),
                            'Frios': st.column_config.NumberColumn('Frios (R$)', format="R$ %.2f"),
                            'Bebidas': st.column_config.NumberColumn('Bebidas (R$)', format="R$ %.2f"),
                            'Total': st.column_config.NumberColumn('Total (R$)', format="R$ %.2f")
                        }
                    )
                else:
                    st.info("Nenhuma compra registrada até o momento.")

    with tab2:
        st.header("Análise de Vendas")
        
        # Carregar dados de vendas
        df_vendas, _ = read_google_sheet("Vendas")
        df_vendas = process_vendas(df_vendas)

        if not df_vendas.empty:
            # Filtros de Ano e Mês na barra lateral
            st.sidebar.header("Filtros de Vendas")
            anos = sorted(df_vendas['Ano'].unique())
            selected_anos = st.sidebar.multiselect(
                "Ano(s):", 
                anos, 
                default=anos[-1:] if anos else []
            )
            
            if selected_anos:
                meses_disponiveis = sorted(df_vendas[df_vendas['Ano'].isin(selected_anos)]['Mês'].unique())
                nomes_meses = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
                mes_opcoes = [f"{m} - {nomes_meses[m]}" for m in meses_disponiveis]
                
                selected_meses_str = st.sidebar.multiselect(
                    "Mês(es):", 
                    mes_opcoes, 
                    default=mes_opcoes[-1:] if mes_opcoes else []
                )
                
                selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]
                
                # Filtrar dados
                df_filtered = df_vendas[df_vendas['Ano'].isin(selected_anos)]
                if selected_meses:
                    df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)]
                
                # Exibir dados filtrados
                st.subheader("Resumo das Vendas")
                st.dataframe(df_filtered[['DataFormatada', 'Cartão', 'Dinheiro', 'PIX', 'Total']], use_container_width=True)
                
                # Gráfico de barras por categoria de pagamento
                st.subheader("Gráfico de Totais por Categoria")
                if not df_filtered.empty:
                    melted_df = df_filtered.melt(
                        id_vars=['DataFormatada'], 
                        value_vars=['Cartão', 'Dinheiro', 'PIX'], 
                        var_name='Meio', 
                        value_name='Valor'
                    )
                    
                    chart = alt.Chart(melted_df).mark_bar().encode(
                        x=alt.X('DataFormatada:N', title='Data', axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y('Valor:Q', title='Valor (R$)'),
                        color='Meio:N',
                        tooltip=['DataFormatada', 'Meio', 'Valor']
                    ).properties(width=700, height=400)
                    
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.info("Nenhum dado para o período selecionado.")
            else:
                st.info("Selecione pelo menos um ano para visualizar os dados.")
        else:
            st.info("Nenhuma venda encontrada.")

    with tab3:
        st.header("Análise de Compras")
        
        # Carregar dados de compras
        df_compras, _ = read_google_sheet("compras")
        df_compras = process_compras(df_compras)

        if not df_compras.empty:
            # Filtros de Ano e Mês na barra lateral
            st.sidebar.header("Filtros de Compras")
            anos_compras = sorted(df_compras['Ano'].unique())
            selected_anos_compras = st.sidebar.multiselect(
                "Ano(s) para Compras:", 
                anos_compras, 
                default=anos_compras[-1:] if anos_compras else []
            )
            
            if selected_anos_compras:
                meses_compras = sorted(df_compras[df_compras['Ano'].isin(selected_anos_compras)]['Mês'].unique())
                nomes_meses_compras = {m: datetime(2020, m, 1).strftime('%B') for m in meses_compras}
                mes_opcoes_compras = [f"{m} - {nomes_meses_compras[m]}" for m in meses_compras]
                
                selected_meses_compras_str = st.sidebar.multiselect(
                    "Mês(es) para Compras:", 
                    mes_opcoes_compras, 
                    default=mes_opcoes_compras[-1:] if mes_opcoes_compras else []
                )
                
                selected_meses_compras = [int(m.split(" - ")[0]) for m in selected_meses_compras_str]
                
                # Filtrar dados
                df_filtered_compras = df_compras[df_compras['Ano'].isin(selected_anos_compras)]
                if selected_meses_compras:
                    df_filtered_compras = df_filtered_compras[df_filtered_compras['Mês'].isin(selected_meses_compras)]
                
                # Exibir dados filtrados
                st.subheader("Compras Filtradas")
                st.dataframe(df_filtered_compras[['DataFormatada', 'Pão', 'Frios', 'Bebidas']], use_container_width=True, height=300)
                
                if not df_filtered_compras.empty:
                    # Gráfico de pizza para distribuição de compras
                    st.subheader("Distribuição de Compras por Categoria")
                    compras_sum = {
                        'Categoria': ['Pão', 'Frios', 'Bebidas'],
                        'Valor': [
                            df_filtered_compras['Pão'].sum(),
                            df_filtered_compras['Frios'].sum(),
                            df_filtered_compras['Bebidas'].sum()
                        ]
                    }
                    compras_df = pd.DataFrame(compras_sum)
                    
                    chart = alt.Chart(compras_df).mark_arc(innerRadius=50).encode(
                        theta=alt.Theta("Valor:Q", stack=True),
                        color=alt.Color("Categoria:N"),
                        tooltip=["Categoria", "Valor"]
                    ).properties(width=700, height=500)
                    
                    text = chart.mark_text(radius=120, size=16).encode(text="Valor:Q")
                    st.altair_chart(chart + text, use_container_width=True)
                    
                    # Gráfico de barras para compras diárias
                    st.subheader("Compras Diárias por Categoria")
                    daily_compras = df_filtered_compras.melt(
                        id_vars=['DataFormatada'],
                        value_vars=['Pão', 'Frios', 'Bebidas'],
                        var_name='Categoria',
                        value_name='Valor'
                    )
                    
                    chart2 = alt.Chart(daily_compras).mark_bar(size=30).encode(
                        x=alt.X('DataFormatada:N', title='Data', axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y('Valor:Q', title='Valor (R$)'),
                        color='Categoria:N',
                        tooltip=['DataFormatada', 'Categoria', 'Valor']
                    ).properties(width=700, height=500)
                    
                    st.altair_chart(chart2, use_container_width=True)
                else:
                    st.info("Nenhum dado para o período selecionado.")
            else:
                st.info("Selecione pelo menos um ano para visualizar os dados.")
        else:
            st.info("Não há dados de compras para exibir.")

    with tab4:
        st.header("📈 Estatísticas de Vendas")

        # Carregar dados
        with st.spinner("Carregando dados..."):
            df_raw, _ = read_google_sheet("Vendas")
            df = process_data(df_raw.copy()) if not df_raw.empty else pd.DataFrame()

            if not df.empty:
                # Filtros de Ano e Mês
                st.sidebar.header("🔍 Filtros Estatísticos")
                anos = sorted(df['Ano'].unique())
                
                if anos:
                    ano_selecionado = st.sidebar.selectbox(
                        "Selecione o Ano para Estatísticas:", 
                        anos, 
                        index=len(anos) - 1
                    )
                    
                    meses_disponiveis = sorted(df[df['Ano'] == ano_selecionado]['Mês'].unique())
                    
                    if meses_disponiveis:
                        nomes_meses = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
                        mes_opcoes = [f"{m} - {nomes_meses[m]}" for m in meses_disponiveis]
                        
                        mes_selecionado_str = st.sidebar.selectbox(
                            "Selecione o Mês para Estatísticas:", 
                            mes_opcoes, 
                            index=len(mes_opcoes)-1 if mes_opcoes else 0
                        )
                        
                        mes_selecionado = int(mes_selecionado_str.split(" - ")[0])
                        
                        df_filtrado = df[(df['Ano'] == ano_selecionado) & (df['Mês'] == mes_selecionado)]
                        
                        if df_filtrado.empty:
                            st.warning("Nenhuma venda registrada para o mês selecionado.")
                        else:
                            # Estatísticas principais
                            total_mes = df_filtrado['Total'].sum()
                            media_dia = df_filtrado.groupby('Data').sum()['Total'].mean()
                            dias_trabalhados = df_filtrado['Data'].dt.date.nunique()
                            
                            # Dia com maior venda
                            dia_maior_venda = df_filtrado.loc[df_filtrado['Total'].idxmax(), 'DataFormatada']
                            valor_maior_venda = df_filtrado['Total'].max()
                            
                            # Médias por dia da semana
                            df_filtrado['DiaSemana'] = df_filtrado['Data'].dt.day_name()
                            media_semana = df_filtrado.groupby('DiaSemana').mean(numeric_only=True)['Total'].sort_values(ascending=False)
                            dia_mais_vende = media_semana.idxmax() if not media_semana.empty else "N/A"
                            dia_menos_vende = media_semana.idxmin() if not media_semana.empty else "N/A"
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("💰 Faturamento Total", f"R$ {total_mes:.2f}")
                                st.metric("📆 Dias Trabalhados", dias_trabalhados)
                            with col2:
                                st.metric("📊 Média por Dia", f"R$ {media_dia:.2f}")
                                st.metric("📅 Dia com Maior Venda", f"{dia_maior_venda} → R$ {valor_maior_venda:.2f}")
                            with col3:
                                st.metric("📈 Dia da Semana + Forte", dia_mais_vende)
                                st.metric("📉 Dia da Semana + Fraco", dia_menos_vende)
                            
                            st.markdown("---")
                            st.subheader("📊 Evolução de Vendas Diárias no Mês")
                            
                            chart1 = alt.Chart(df_filtrado).mark_bar(size=30).encode(
                                x=alt.X('Data:T', title='Data'),
                                y=alt.Y('Total:Q', title='Total (R$)'),
                                tooltip=['DataFormatada', 'Total']
                            ).properties(
                                width=700,
                                height=400
                            )
                            st.altair_chart(chart1, use_container_width=True)
                            
                            st.markdown("---")
                            st.subheader("📆 Comparativo por Dia da Semana")
                            
                            if not media_semana.empty:
                                dias_df = pd.DataFrame({
                                    'Dia da Semana': media_semana.index,
                                    'Média de Vendas': media_semana.values
                                })
                                
                                chart2 = alt.Chart(dias_df).mark_bar(size=40).encode(
                                    x=alt.X('Dia da Semana:N', sort=list(media_semana.index)),
                                    y=alt.Y('Média de Vendas:Q'),
                                    color=alt.Color('Dia da Semana:N', legend=None),
                                    tooltip=['Dia da Semana', 'Média de Vendas']
                                ).properties(
                                    width=700,
                                    height=400
                                )
                                st.altair_chart(chart2, use_container_width=True)
                            else:
                                st.info("Dados insuficientes para análise por dia da semana.")
                    else:
                        st.warning(f"Nenhum mês encontrado para o ano {ano_selecionado}.")
                else:
                    st.warning("Nenhum ano encontrado nos dados.")
            else:
                st.info("Ainda não há dados suficientes para exibir estatísticas.")

    # Rodapé
    st.divider()
    st.markdown(
        """
        <div style='text-align: center; color: gray; font-size: small;'>
            © 2025 Clips Burger - Sistema de Gestão | Desenvolvido com ❤️ e Streamlit
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
