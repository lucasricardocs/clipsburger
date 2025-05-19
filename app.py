import streamlit as st
import gspread
import pandas as pd
from datetime import datetime
import pygwalker as pyg
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página - PyGWalker funciona melhor em layout wide
st.set_page_config(
    page_title="Sistema de Registro de Vendas", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS para o layout
st.markdown("""
<style>
    .resumo-container {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
        margin-bottom: 25px;
    }
    .resumo-item {
        background-color: #1e1e1e;
        color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333333;
    }
    .resumo-titulo {
        font-size: 1.1em;
        color: #4dabf7;
        margin-bottom: 10px;
        font-weight: 600;
    }
    .resumo-valor {
        font-size: 1.8em;
        color: #ffffff;
        font-weight: 700;
    }
    [data-testid="stElementToolbar"] {
        display: none;
    }
    /* Melhorias para o PyGWalker */
    iframe {
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def read_google_sheet():
    """Função para ler os dados da planilha Google Sheets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 
                 'https://www.googleapis.com/auth/spreadsheets.readonly', 
                 'https://www.googleapis.com/auth/drive.readonly']
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
        worksheet_name = 'Vendas'
        try:
            with st.spinner("Conectando à planilha..."):
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

def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet):
    """Função para adicionar dados à planilha Google Sheets"""
    if worksheet is None:
        st.error("Não foi possível acessar a planilha.")
        return False
    try:
        with st.spinner("Registrando venda..."):
            new_row = [date, float(cartao), float(dinheiro), float(pix)]
            worksheet.append_row(new_row)
            st.toast("Venda registrada com sucesso!", icon="✅")
            return True
    except Exception as e:
        st.error(f"Erro ao adicionar dados: {e}")
        return False

@st.cache_data(ttl=300)
def process_data(df_raw):
    """Função para processar e preparar os dados"""
    if df_raw.empty:
        return pd.DataFrame()
    
    df = df_raw.copy()
    
    # Processamento dos valores monetários
    for col in ['Cartão', 'Dinheiro', 'Pix']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Cálculo do total
    df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']
    
    # Processamento de datas
    if 'Data' in df.columns:
        try:
            df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
            df = df.dropna(subset=['Data'])
            
            if not df.empty:
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['MêsNome'] = df['Data'].dt.strftime('%B')
                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                df['DiaSemana'] = df['Data'].dt.day_name()
                
                dias_semana_map = {
                    'Monday': 'Segunda',
                    'Tuesday': 'Terça',
                    'Wednesday': 'Quarta',
                    'Thursday': 'Quinta',
                    'Friday': 'Sexta',
                    'Saturday': 'Sábado',
                    'Sunday': 'Domingo'
                }
                df['DiaSemana'] = df['DiaSemana'].map(dias_semana_map)
                
                # Remover domingos
                df = df[df['DiaSemana'] != 'Domingo'].copy()
                
                # Adicionar colunas para facilitar análise no PyGWalker
                df['DiaDaSemana_num'] = df['DiaSemana'].map({
                    'Segunda': 1, 'Terça': 2, 'Quarta': 3, 
                    'Quinta': 4, 'Sexta': 5, 'Sábado': 6
                })
                
                # Coluna para valor acumulado (será calculado posteriormente)
                df['Semana'] = df['Data'].dt.isocalendar().week
                df['Dia'] = df['Data'].dt.day
                
        except Exception as e:
            st.warning(f"Erro ao processar datas: {e}")
    
    return df

def calculate_metrics(df):
    """Calcula métricas resumidas dos dados"""
    if df.empty:
        return {'total_vendas': 0, 'total_faturamento': 0, 'media_por_venda': 0, 'melhor_dia': None}
    
    # Métricas básicas
    total_vendas = len(df)
    total_faturamento = df['Total'].sum()
    media_por_venda = df['Total'].mean()
    
    # Calcular o melhor dia da semana
    melhor_dia = None
    if 'DiaSemana' in df.columns and not df.empty:
        vendas_por_dia = df.groupby('DiaSemana')['Total'].sum()
        if not vendas_por_dia.empty:
            melhor_dia = vendas_por_dia.idxmax()
            
    return {
        'total_vendas': total_vendas,
        'total_faturamento': total_faturamento,
        'media_por_venda': media_por_venda,
        'melhor_dia': melhor_dia
    }

def main():
    st.title("📊 Sistema de Registro de Vendas")
    
    df_raw, worksheet = read_google_sheet()
    df = process_data(df_raw)
    
    # Abas principais do aplicativo
    tab1, tab2, tab3 = st.tabs([
        "📝 Registrar Venda", 
        "📊 Análise Interativa", 
        "📋 Dados"
    ])
    
    # Aba 1: Registro de Vendas
    with tab1:
        st.header("Registrar Nova Venda")
        
        with st.form("venda_form"):
            data = st.date_input("📅 Data da Venda", datetime.now())
            is_sunday = data.weekday() == 6  # 6 = Domingo
            
            col1, col2, col3 = st.columns(3)
            with col1:
                cartao = st.number_input("💳 Cartão (R$)", min_value=0.0, format="%.2f")
            with col2:
                dinheiro = st.number_input("💵 Dinheiro (R$)", min_value=0.0, format="%.2f")
            with col3:
                pix = st.number_input("📱 PIX (R$)", min_value=0.0, format="%.2f")
            
            total = cartao + dinheiro + pix
            st.write(f"Total da venda: R$ {total:.2f}")
            
            submitted = st.form_submit_button("💾 Registrar Venda", use_container_width=True)
            
            if submitted:
                if is_sunday:
                    st.error("⚠️ Não é possível registrar vendas aos domingos!")
                elif total > 0:
                    if add_data_to_sheet(data.strftime('%d/%m/%Y'), cartao, dinheiro, pix, worksheet):
                        st.cache_data.clear()
                        st.rerun()
                else:
                    st.warning("⚠️ O valor total deve ser maior que zero.")
    
    # Filtros na sidebar
    with st.sidebar:
        st.header("🔍 Filtros")
        
        if not df.empty and 'Data' in df.columns:
            # Filtro de Ano
            anos = sorted(df['Ano'].unique(), reverse=True)
            selected_anos = st.multiselect("Selecione o(s) Ano(s):", options=anos, default=anos[:1])
            
            # Filtro de Mês
            meses_disponiveis = sorted(df[df['Ano'].isin(selected_anos)]['Mês'].unique()) if selected_anos else []
            meses_opcoes = [f"{m:02d} - {datetime(2020, m, 1).strftime('%B')}" for m in meses_disponiveis]
            selected_meses_str = st.multiselect("Selecione o(s) Mês(es):", options=meses_opcoes, default=meses_opcoes)
            selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]
            
            # Aplicar filtros
            df_filtered = df.copy()
            if selected_anos:
                df_filtered = df_filtered[df_filtered['Ano'].isin(selected_anos)]
            if selected_meses:
                df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)]
        else:
            st.info("Não há dados disponíveis para filtrar.")
            df_filtered = pd.DataFrame()
        
        # Exibir informações sobre PyGWalker
        st.markdown("---")
        st.markdown("### 📊 PyGWalker")
        st.markdown("""
        O PyGWalker oferece uma interface interativa para análise de dados:
        - Arraste e solte campos para criar visualizações
        - Escolha entre diferentes tipos de gráficos
        - Explore os dados dinamicamente
        - Experimente combinações de dimensões e métricas
        """)
    
    # Aba 2: Análise Interativa (PyGWalker)
    with tab2:
        st.header("Análise Interativa com PyGWalker")
        
        if df_filtered.empty:
            st.info("Não há dados para visualizar. Selecione outro período nos filtros.")
        else:
            # Calcular e exibir métricas
            metrics = calculate_metrics(df_filtered)
            
            # Exibir resumo em formato de cards
            st.markdown(f"""
            <div class="resumo-container">
                <div class="resumo-item">
                    <div class="resumo-titulo">Total de Vendas</div>
                    <div class="resumo-valor">{metrics['total_vendas']}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Faturamento Total</div>
                    <div class="resumo-valor">R$ {metrics['total_faturamento']:,.2f}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Ticket Médio</div>
                    <div class="resumo-valor">R$ {metrics['media_por_venda']:,.2f}</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-titulo">Melhor Dia</div>
                    <div class="resumo-valor">{metrics['melhor_dia'] if metrics['melhor_dia'] else 'N/A'}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Preparar dados para o PyGWalker
            # Calculando o total acumulado para cada linha
            if 'Data' in df_filtered.columns:
                df_viz = df_filtered.sort_values('Data').copy()
                df_viz['Total Acumulado'] = df_viz['Total'].cumsum()
                
                # Adicionar métricas úteis para análise
                df_viz['% Cartão'] = (df_viz['Cartão'] / df_viz['Total'] * 100).round(2)
                df_viz['% Dinheiro'] = (df_viz['Dinheiro'] / df_viz['Total'] * 100).round(2)
                df_viz['% Pix'] = (df_viz['Pix'] / df_viz['Total'] * 100).round(2)
            else:
                df_viz = df_filtered.copy()
            
            st.write("### Arraste e solte para criar suas análises")
            st.write("""
            **Sugestões de visualizações:**
            - Tendência de vendas ao longo do tempo
            - Comparação entre os métodos de pagamento
            - Análise do ticket médio por dia da semana
            - Distribuição das vendas por valor
            """)
            
            # Configurar e renderizar o PyGWalker
            try:
                # Configuração personalizada para o PyGWalker
                config = {
                    "theme": "dark",  # Tema escuro para combinar com o modo escuro do Streamlit
                    "enableQueryEditor": False,  # Esconder o editor de consultas
                    "defaultConfigPanelCollapsed": False,  # Expandir o painel de configuração
                }
                
                # Renderizar o PyGWalker como um componente HTML
                pyg_html = pyg.walk(df_viz, env='Streamlit', return_html=True, config=config)
                st.components.v1.html(pyg_html, height=800)
                
            except Exception as e:
                st.error(f"Erro ao carregar o PyGWalker: {e}")
                st.warning("""
                O PyGWalker requer recursos avançados e pode não funcionar em alguns ambientes. 
                Caso esteja enfrentando problemas, verifique se o navegador é atualizado e se não 
                há bloqueio de scripts.
                """)
                # Carregar uma tabela como fallback
                st.write("### Visualizando dados como tabela (fallback)")
                st.dataframe(df_viz.head(100))
            
    # Aba 3: Dados
    with tab3:
        st.header("Dados de Vendas")
        
        if df_filtered.empty:
            st.info("Não há dados para exibir com os filtros selecionados.")
        else:
            # Dados de vendas filtrados
            st.subheader("🧾 Dados Filtrados")
            st.dataframe(df_filtered, use_container_width=True)
            
            # Análises resumidas
            st.subheader("📊 Análises Resumidas")
            
            # Vendas por Dia da Semana
            if 'DiaSemana' in df_filtered.columns:
                dias_vendas = df_filtered.groupby('DiaSemana').agg(
                    Total=('Total', 'sum'),
                    Quantidade=('Total', 'count'),
                    Média=('Total', 'mean')
                ).reset_index()
                
                st.write("#### Vendas por Dia da Semana")
                st.dataframe(
                    dias_vendas,
                    use_container_width=True,
                    column_config={
                        "DiaSemana": st.column_config.TextColumn("Dia"),
                        "Total": st.column_config.NumberColumn("Total (R$)", format="R$ %.2f"),
                        "Quantidade": st.column_config.NumberColumn("Quantidade"),
                        "Média": st.column_config.NumberColumn("Média (R$)", format="R$ %.2f")
                    }
                )
            
            # Vendas por Método de Pagamento
            metodos = pd.DataFrame({
                'Método': ['Cartão', 'Dinheiro', 'PIX'],
                'Valor': [
                    df_filtered['Cartão'].sum(),
                    df_filtered['Dinheiro'].sum(),
                    df_filtered['Pix'].sum()
                ]
            })
            metodos['Porcentagem'] = (metodos['Valor'] / metodos['Valor'].sum() * 100).round(2)
            
            st.write("#### Métodos de Pagamento")
            st.dataframe(
                metodos,
                use_container_width=True,
                column_config={
                    "Método": st.column_config.TextColumn("Método"),
                    "Valor": st.column_config.NumberColumn("Valor Total", format="R$ %.2f"),
                    "Porcentagem": st.column_config.NumberColumn("Percentual", format="%.2f%%")
                }
            )

if __name__ == "__main__":
    main()
