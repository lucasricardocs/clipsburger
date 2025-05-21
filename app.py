import streamlit as st
import pandas as pd
import altair as alt
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
st.set_page_config(
    page_title="Sistema de Registro de Vendas", 
    layout="centered",
    initial_sidebar_state="expanded"
)

@st.cache_data(ttl=300)
def read_google_sheet():
    """Função para ler os dados da planilha Google Sheets"""
    try:
        # Usar método service_account diretamente do gspread
        credentials_dict = st.secrets["google_credentials"]
        
        # Criar arquivo temporário com as credenciais
        import json
        import tempfile
        import os
        
        # Criar arquivo temporário para as credenciais
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp:
            json.dump(credentials_dict, temp)
            temp_filename = temp.name
        
        try:
            # Usar service_account diretamente
            gc = gspread.service_account(filename=temp_filename)
            
            # ID da planilha e nome da worksheet
            spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
            worksheet_name = 'Vendas'
            
            with st.spinner("Conectando à planilha..."):
                # Abrir planilha e obter worksheet
                spreadsheet = gc.open_by_key(spreadsheet_id)
                worksheet = spreadsheet.worksheet(worksheet_name)
                
                # Obter todos os registros
                rows = worksheet.get_all_records()
                df = pd.DataFrame(rows)
                return df, worksheet
        except SpreadsheetNotFound:
            st.error(f"Planilha com ID {spreadsheet_id} não encontrada.")
            return pd.DataFrame(), None
        except Exception as e:
            st.error(f"Erro ao acessar a planilha: {e}")
            return pd.DataFrame(), None
        finally:
            # Remover o arquivo temporário
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
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
            # Preparar nova linha com os dados
            new_row = [date, float(cartao), float(dinheiro), float(pix)]
            
            # Adicionar linha à planilha
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
                
                # Adicionar ordem dos dias da semana para garantir ordenação correta
                ordem_dias = {'Segunda': 1, 'Terça': 2, 'Quarta': 3, 'Quinta': 4, 'Sexta': 5, 'Sábado': 6, 'Domingo': 7}
                df['DiaSemanaOrdem'] = df['DiaSemana'].map(ordem_dias)
                
                # Remover domingos
                df = df[df['DiaSemana'] != 'Domingo'].copy()
        except Exception as e:
            st.warning(f"Erro ao processar datas: {e}")
    
    return df

def main():
    st.title("📊 Sistema de Registro de Vendas")
    
    # Carregar dados
    df_raw, worksheet = read_google_sheet()
    df = process_data(df_raw)
    
    # Abas principais
    tab1, tab2, tab3 = st.tabs([
        "📝 Registrar Venda", 
        "📈 Análise Detalhada", 
        "📊 Estatísticas"
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
                        # Limpar cache e recarregar a página
                        st.cache_data.clear()
                        st.experimental_rerun()
                else:
                    st.warning("⚠️ O valor total deve ser maior que zero.")
    
    # Filtros na sidebar
    with st.sidebar:
        st.header("🔍 Filtros")
        
        if not df.empty and 'Data' in df.columns:
            # Obter mês e ano atual
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            # Filtro de Ano
            anos = sorted(df['Ano'].unique(), reverse=True)
            default_anos = [current_year] if current_year in anos else anos[:1] if anos else []
            selected_anos = st.multiselect(
                "Selecione o(s) Ano(s):",
                options=anos,
                default=default_anos,
                key="filter_years"
            )
            
            # Filtro de Mês
            meses_disponiveis = sorted(df[df['Ano'].isin(selected_anos)]['Mês'].unique()) if selected_anos else []
            meses_nomes = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
            meses_opcoes = [f"{m:02d} - {meses_nomes[m]}" for m in meses_disponiveis]
            
            # Default para o mês atual ou todos
            default_mes_opcao = [f"{current_month:02d} - {datetime(2020, current_month, 1).strftime('%B')}"]
            default_meses = [m for m in meses_opcoes if m.startswith(f"{current_month:02d} -")]
            
            selected_meses_str = st.multiselect(
                "Selecione o(s) Mês(es):",
                options=meses_opcoes,
                default=default_meses if default_meses else meses_opcoes,
                key="filter_months"
            )
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
    
    # Aba 2: Análise Detalhada
    with tab2:
        st.header("Análise Detalhada de Vendas")
        
        if df_filtered.empty:
            st.info("Não há dados para exibir com os filtros selecionados.")
        else:
            # Mostrar dados filtrados em uma tabela
            st.subheader("🧾 Dados Filtrados")
            
            # Tabela usando componente nativo do Streamlit
            st.dataframe(
                df_filtered[['DataFormatada', 'DiaSemana', 'Cartão', 'Dinheiro', 'Pix', 'Total']], 
                use_container_width=True,
                column_config={
                    "DataFormatada": st.column_config.TextColumn("Data"),
                    "DiaSemana": st.column_config.TextColumn("Dia da Semana"),
                    "Cartão": st.column_config.NumberColumn("Cartão (R$)", format="R$ %.2f"),
                    "Dinheiro": st.column_config.NumberColumn("Dinheiro (R$)", format="R$ %.2f"),
                    "Pix": st.column_config.NumberColumn("PIX (R$)", format="R$ %.2f"),
                    "Total": st.column_config.NumberColumn("Total (R$)", format="R$ %.2f")
                },
                height=300
            )
            
            # Resumo dos dados
            total_vendas = len(df_filtered)
            total_faturamento = df_filtered['Total'].sum()
            media_por_venda = df_filtered['Total'].mean() if total_vendas > 0 else 0
            maior_venda = df_filtered['Total'].max() if total_vendas > 0 else 0
            
            # Melhor dia da semana
            melhor_dia = None
            if 'DiaSemana' in df_filtered.columns and not df_filtered.empty:
                vendas_por_dia = df_filtered.groupby('DiaSemana')['Total'].sum()
                if not vendas_por_dia.empty:
                    melhor_dia = vendas_por_dia.idxmax()
            
            # Exibir métricas em cards usando colunas do Streamlit em vez de CSS personalizado
            st.subheader("📌 Resumo")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de Vendas", f"{total_vendas}")
                st.metric("Ticket Médio", f"R$ {media_por_venda:,.2f}")
            with col2:
                st.metric("Faturamento Total", f"R$ {total_faturamento:,.2f}")
                st.metric("Melhor Dia", f"{melhor_dia if melhor_dia else 'N/A'}")
            
            # Acúmulo de Capital
            st.subheader("💰 Acúmulo de Capital ao Longo do Tempo")
            
            # Usar vega-lite diretamente para garantir renderização
            if not df_filtered.empty:
                # Criar dados para o gráfico
                df_acumulado = df_filtered.sort_values('Data').copy()
                df_acumulado['Total Acumulado'] = df_acumulado['Total'].cumsum()
                df_acumulado['DataFormatada'] = df_acumulado['Data'].dt.strftime('%d/%m/%Y')
                
                # Converter para formato JSON para Vega-Lite
                data_json = df_acumulado[['DataFormatada', 'Total', 'Total Acumulado']].to_dict(orient='records')
                
                # Definir especificação Vega-Lite
                vega_spec = {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "data": {"values": data_json},
                    "mark": {"type": "line", "point": True},
                    "encoding": {
                        "x": {"field": "DataFormatada", "type": "nominal", "title": "Data"},
                        "y": {"field": "Total Acumulado", "type": "quantitative", "title": "Capital Acumulado (R$)"}
                    },
                    "width": "container",
                    "height": 400
                }
                
                # Renderizar usando st.vega_lite_chart
                st.vega_lite_chart(vega_spec, use_container_width=True)
    
    # Aba 3: Estatísticas
    with tab3:
        st.header("Estatísticas Avançadas de Vendas")
        
        if df_filtered.empty:
            st.info("Não há dados para exibir com os filtros selecionados.")
        else:
            # Layout em duas colunas para os primeiros gráficos
            col1, col2 = st.columns(2)
            
            with col1:
                # Análise por Dia da Semana
                st.subheader("📅 Vendas por Dia da Semana")
                
                # Usar vega-lite diretamente para garantir renderização
                if not df_filtered.empty:
                    # Agrupar por dia da semana
                    vendas_por_dia = df_filtered.groupby('DiaSemana')['Total'].sum().reset_index()
                    
                    # Converter para formato JSON para Vega-Lite
                    data_json = vendas_por_dia.to_dict(orient='records')
                    
                    # Definir especificação Vega-Lite
                    vega_spec = {
                        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                        "data": {"values": data_json},
                        "mark": "bar",
                        "encoding": {
                            "x": {"field": "DiaSemana", "type": "nominal", "title": "Dia da Semana", 
                                 "sort": ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]},
                            "y": {"field": "Total", "type": "quantitative", "title": "Faturamento Total (R$)"},
                            "color": {"value": "#4285F4"}
                        },
                        "width": "container",
                        "height": 350
                    }
                    
                    # Renderizar usando st.vega_lite_chart
                    st.vega_lite_chart(vega_spec, use_container_width=True)
            
            with col2:
                # Métodos de Pagamento
                st.subheader("💳 Métodos de Pagamento")
                
                # Usar vega-lite diretamente para garantir renderização
                if not df_filtered.empty:
                    # Calcular total por método de pagamento
                    cartao_total = df_filtered['Cartão'].sum()
                    dinheiro_total = df_filtered['Dinheiro'].sum()
                    pix_total = df_filtered['Pix'].sum()
                    
                    # Criar dados para o gráfico
                    data = [
                        {"metodo": "Cartão", "valor": cartao_total},
                        {"metodo": "Dinheiro", "valor": dinheiro_total},
                        {"metodo": "PIX", "valor": pix_total}
                    ]
                    
                    # Definir especificação Vega-Lite
                    vega_spec = {
                        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                        "data": {"values": data},
                        "mark": {"type": "arc", "innerRadius": 0, "outerRadius": 120},
                        "encoding": {
                            "theta": {"field": "valor", "type": "quantitative"},
                            "color": {
                                "field": "metodo", 
                                "type": "nominal",
                                "scale": {
                                    "domain": ["Cartão", "Dinheiro", "PIX"],
                                    "range": ["#4285F4", "#34A853", "#FBBC05"]
                                }
                            }
                        },
                        "width": "container",
                        "height": 350
                    }
                    
                    # Renderizar usando st.vega_lite_chart
                    st.vega_lite_chart(vega_spec, use_container_width=True)
            
            # Histograma dos valores
            st.subheader("📊 Distribuição dos Valores de Venda")
            
            # Usar vega-lite diretamente para garantir renderização
            if not df_filtered.empty:
                # Converter para formato JSON para Vega-Lite
                data_json = df_filtered[['Total']].to_dict(orient='records')
                
                # Definir especificação Vega-Lite
                vega_spec = {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "data": {"values": data_json},
                    "mark": "bar",
                    "encoding": {
                        "x": {
                            "field": "Total", 
                            "type": "quantitative", 
                            "bin": {"maxbins": 20},
                            "title": "Valor da Venda (R$)"
                        },
                        "y": {"aggregate": "count", "title": "Frequência"},
                        "color": {"value": "#FBBC05"}
                    },
                    "width": "container",
                    "height": 350
                }
                
                # Renderizar usando st.vega_lite_chart
                st.vega_lite_chart(vega_spec, use_container_width=True)
                
                # Estatísticas adicionais
                stats_cols = st.columns(4)
                stats_cols[0].metric("Média", f"R$ {df_filtered['Total'].mean():.2f}")
                stats_cols[1].metric("Mediana", f"R$ {df_filtered['Total'].median():.2f}")
                stats_cols[2].metric("Desvio Padrão", f"R$ {df_filtered['Total'].std():.2f}")
                # Correção: Adicionando verificação para evitar divisão por zero
                coef_var = 0
                if df_filtered['Total'].mean() > 0:
                    coef_var = (df_filtered['Total'].std() / df_filtered['Total'].mean() * 100)
                stats_cols[3].metric("Coef. de Variação", f"{coef_var:.1f}%")
            
            # Evolução mensal
            if 'AnoMês' in df_filtered.columns and df_filtered['AnoMês'].nunique() > 1:
                st.subheader("📈 Evolução Mensal de Vendas")
                
                # Usar vega-lite diretamente para garantir renderização
                # Agrupar por mês
                df_monthly = df_filtered.groupby('AnoMês').agg({
                    'Total': 'sum',
                    'Data': 'count'
                }).reset_index()
                
                df_monthly.rename(columns={'Data': 'Quantidade'}, inplace=True)
                
                # Converter para formato JSON para Vega-Lite
                data_json = df_monthly.to_dict(orient='records')
                
                # Definir especificação Vega-Lite
                vega_spec = {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "data": {"values": data_json},
                    "mark": {"type": "line", "point": True},
                    "encoding": {
                        "x": {"field": "AnoMês", "type": "nominal", "title": "Mês"},
                        "y": {"field": "Total", "type": "quantitative", "title": "Faturamento Total (R$)"},
                        "color": {"value": "#4285F4"}
                    },
                    "width": "container",
                    "height": 400
                }
                
                # Renderizar usando st.vega_lite_chart
                st.vega_lite_chart(vega_spec, use_container_width=True)

if __name__ == "__main__":
    main()
