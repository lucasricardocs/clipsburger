import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
import io
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound, APIError

# Configuração da página
st.set_page_config(
    page_title="Sistema de Registro de Vendas",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para carregar credenciais e configurar conexão com Google Sheets
@st.cache_resource(ttl=3600)
def get_google_client():
    """Configurar e retornar cliente Google Sheets com cache para evitar múltiplas autenticações"""
    try:
        # Definindo os escopos corretos para o Google Sheets
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        # Carregando as credenciais do secrets do Streamlit
        credentials_dict = st.secrets["google_credentials"]
        
        # Obter ID da planilha dos secrets (mais seguro que hardcoded)
        spreadsheet_id = st.secrets.get("spreadsheet_id", "1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg")
        
        # Crie as credenciais a partir do dicionário do secrets com os escopos corretos
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)

        # Autenticação com o Google Sheets
        gc = gspread.authorize(creds)
        
        return gc, spreadsheet_id
    except Exception as e:
        st.error(f"Erro ao configurar cliente Google Sheets: {str(e)}")
        return None, None

# Função para ler os dados da planilha Google Sheets com cache
@st.cache_data(ttl=300)  # Cache por 5 minutos
def read_google_sheet(worksheet_name="Vendas"):
    """Função para ler os dados da planilha Google Sheets com cache para melhorar desempenho"""
    try:
        gc, spreadsheet_id = get_google_client()
        
        if not gc or not spreadsheet_id:
            return pd.DataFrame(), None
            
        # Abrindo a planilha e a aba
        try:
            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)

            # Lendo os dados da planilha
            rows = worksheet.get_all_records()

            # Convertendo para DataFrame
            df = pd.DataFrame(rows)
            
            if df.empty:
                st.info(f"A planilha '{worksheet_name}' está vazia ou não contém dados formatados corretamente.")
                
            return df, worksheet

        except SpreadsheetNotFound:
            st.error(f"Planilha não encontrada. Verifique o ID e as permissões.")
            return pd.DataFrame(), None
        except WorksheetNotFound:
            st.error(f"Aba '{worksheet_name}' não encontrada na planilha.")
            return pd.DataFrame(), None
        except APIError as e:
            st.error(f"Erro na API do Google Sheets: {str(e)}")
            return pd.DataFrame(), None

    except Exception as e:
        st.error(f"Erro ao ler dados: {str(e)}")
        return pd.DataFrame(), None

def add_data_to_sheet(date, cartao, dinheiro, pix, observacoes, worksheet):
    """Função para adicionar dados à planilha Google Sheets"""
    if worksheet is None:
        st.error("Não foi possível acessar a planilha para adicionar os dados.")
        return False
    try:
        # Validar dados antes de inserir
        for valor in [cartao, dinheiro, pix]:
            if not isinstance(valor, (int, float)) or valor < 0:
                st.error("Valores inválidos. Por favor verifique os dados.")
                return False
        
        # Preparar os dados para inserção (agora com campo de observações)
        new_row = [date, float(cartao), float(dinheiro), float(pix), observacoes]

        # Adicionar a nova linha à planilha
        worksheet.append_row(new_row)
        
        # Limpar cache para forçar recarga dos dados
        read_google_sheet.clear()
        
        # Mostrar mensagem de sucesso
        st.success("Dados registrados com sucesso!")
        return True

    except Exception as e:
        st.error(f"Erro ao adicionar dados: {str(e)}")
        return False

def update_record(row_index, date, cartao, dinheiro, pix, observacoes, worksheet):
    """Função para atualizar um registro existente"""
    if worksheet is None:
        st.error("Não foi possível acessar a planilha para atualizar os dados.")
        return False
    
    try:
        # O índice da linha na API é baseado em 1, e precisamos adicionar +1 para o cabeçalho
        actual_row = row_index + 2  # +1 para índice baseado em 0 e +1 para cabeçalho
        
        # Atualizar células individualmente
        worksheet.update_cell(actual_row, 1, date)
        worksheet.update_cell(actual_row, 2, float(cartao))
        worksheet.update_cell(actual_row, 3, float(dinheiro))
        worksheet.update_cell(actual_row, 4, float(pix))
        worksheet.update_cell(actual_row, 5, observacoes)
        
        # Limpar cache para forçar recarga dos dados
        read_google_sheet.clear()
        
        st.success("Registro atualizado com sucesso!")
        return True
        
    except Exception as e:
        st.error(f"Erro ao atualizar registro: {str(e)}")
        return False

def delete_record(row_index, worksheet):
    """Função para excluir um registro"""
    if worksheet is None:
        st.error("Não foi possível acessar a planilha para excluir o registro.")
        return False
    
    try:
        # O índice da linha na API é baseado em 1, e precisamos adicionar +1 para o cabeçalho
        actual_row = row_index + 2  # +1 para índice baseado em 0 e +1 para cabeçalho
        
        # Excluir linha
        worksheet.delete_rows(actual_row)
        
        # Limpar cache para forçar recarga dos dados
        read_google_sheet.clear()
        
        st.success("Registro excluído com sucesso!")
        return True
        
    except Exception as e:
        st.error(f"Erro ao excluir registro: {str(e)}")
        return False

def process_data(df):
    """Função para processar e preparar os dados"""
    if not df.empty:
        # Verificar se colunas esperadas existem
        expected_columns = ['Data', 'Cartão', 'Dinheiro', 'Pix']
        missing_columns = [col for col in expected_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Colunas necessárias ausentes na planilha: {', '.join(missing_columns)}")
            return df
        
        # Converter colunas numéricas
        for col in ['Cartão', 'Dinheiro', 'Pix']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Calcular total por linha
        df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']

        # Converter a coluna de data para datetime
        if 'Data' in df.columns:
            # Tentar converter a coluna Data com diferentes formatos
            try:
                # Primeiro tenta o formato brasileiro
                df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
                
                # Se houver NaT, tenta o formato ISO
                if df['Data'].isna().any():
                    mask = df['Data'].isna()
                    df.loc[mask, 'Data'] = pd.to_datetime(df.loc[mask, 'Data'].astype(str), format='%Y-%m-%d', errors='coerce')
                
                # Adicionar colunas de mês e ano para filtros
                if not df['Data'].isna().all():
                    df['Ano'] = df['Data'].dt.year
                    df['Mês'] = df['Data'].dt.month
                    df['MêsNome'] = df['Data'].dt.strftime('%B')  # Nome do mês
                    df['DiaSemana'] = df['Data'].dt.day_name()  # Dia da semana
                    df['Semana'] = df['Data'].dt.isocalendar().week  # Número da semana
                    df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')  # Formato AAAA-MM para ordenação

                    # Formatar a data de volta para exibição
                    df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                else:
                    st.warning("Não foi possível converter datas.")
            except Exception as e:
                st.error(f"Erro ao processar a coluna 'Data': {e}")

    return df

def export_dataframe(df, filename="dados_vendas.csv"):
    """Exporta o DataFrame para um arquivo CSV"""
    csv = df.to_csv(index=False).encode('utf-8')
    return csv

def export_excel(df, filename="dados_vendas.xlsx"):
    """Exporta o DataFrame para um arquivo Excel"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Vendas', index=False)
    
    return output.getvalue()

def detect_outliers(df, column, threshold=1.5):
    """Detecta valores atípicos usando o método IQR"""
    if df.empty or column not in df.columns:
        return pd.Series([False] * len(df))
    
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    
    lower_bound = Q1 - threshold * IQR
    upper_bound = Q3 + threshold * IQR
    
    return (df[column] < lower_bound) | (df[column] > upper_bound)

def calculate_growth_rate(current, previous):
    """Calcula taxa de crescimento entre dois valores"""
    if previous == 0:
        return float('inf') if current > 0 else 0
    return ((current - previous) / previous) * 100

def main():
    # Título e estilo da página
    st.title("📊 Sistema de Registro de Vendas")
    
    # Adicionar CSS personalizado para melhorar a aparência
    st.markdown("""
    <style>
    .big-font {font-size:24px !important; font-weight: bold;}
    .highlight {background-color: #f0f2f6; padding: 10px; border-radius: 10px;}
    .success {color: #28a745;}
    .warning {color: #ffc107;}
    .danger {color: #dc3545;}
    </style>
    """, unsafe_allow_html=True)

    # Criar abas
    tab1, tab2, tab3, tab4 = st.tabs([
        "Registrar Venda", 
        "Visualizar Vendas", 
        "Análise de Capital",
        "Gerenciar Registros"
    ])

    with tab1:
        st.header("Registrar Nova Venda")

        # Formulário para inserção de dados
        with st.form("venda_form"):
            # Campo de data
            data = st.date_input("Data", datetime.now())

            # Campos para valores financeiros
            col1, col2, col3 = st.columns(3)

            with col1:
                cartao = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f")

            with col2:
                dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f")

            with col3:
                pix = st.number_input("PIX (R$)", min_value=0.0, format="%.2f")

            # Campo para observações
            observacoes = st.text_area("Observações (opcional)", "", help="Adicione detalhes sobre a venda, como produtos vendidos ou informações do cliente")

            # Calcular e mostrar o total
            total = cartao + dinheiro + pix
            st.markdown(f"<p class='big-font'>Total da venda: R$ {total:.2f}</p>", unsafe_allow_html=True)

            # Botão para enviar os dados
            submitted = st.form_submit_button("Registrar Venda")

            if submitted:
                # Verificar se há pelo menos um valor
                if cartao > 0 or dinheiro > 0 or pix > 0:
                    # Formatar a data para string
                    formatted_date = data.strftime('%d/%m/%Y')

                    # Ler a planilha para obter o objeto worksheet
                    _, worksheet = read_google_sheet()

                    if worksheet:
                        # Adicionar os dados à planilha
                        success = add_data_to_sheet(formatted_date, cartao, dinheiro, pix, observacoes, worksheet)
                        if success:
                            # Limpar cache para forçar recarga dos dados
                            read_google_sheet.clear()
                else:
                    st.warning("Pelo menos um valor de venda deve ser maior que zero.")

    with tab2:
        st.header("Histórico de Vendas")

        # Botão para atualizar os dados
        col1, col2 = st.columns([1, 3])
        with col1:
            load_data = st.button("📊 Atualizar Dados", key="btn_update_history", use_container_width=True)
        
        # Botões de exportação em linha
        with col2:
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                export_csv = st.button("📄 Exportar CSV", key="btn_export_csv", use_container_width=True) 
            with export_col2:
                export_excel_btn = st.button("📊 Exportar Excel", key="btn_export_excel", use_container_width=True)

        # Estado para armazenar dados
        if 'display_df' not in st.session_state:
            st.session_state.display_df = pd.DataFrame()
            load_data = True

        # Carregar dados
        if load_data:
            with st.spinner("Carregando dados..."):
                # Carregar os dados da planilha
                df_raw, _ = read_google_sheet()

                if not df_raw.empty:
                    # Processar dados
                    df = process_data(df_raw.copy())
                    st.session_state.display_df = df
                    st.success("Dados carregados com sucesso!")
                else:
                    st.info("Não há dados para exibir ou houve um problema ao carregar a planilha.")
                    st.session_state.display_df = pd.DataFrame()

        # Processar exportação se solicitado
        if export_csv and not st.session_state.display_df.empty:
            csv = export_dataframe(st.session_state.display_df)
            st.download_button(
                label="Confirmar Download CSV",
                data=csv,
                file_name=f"vendas_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
        if export_excel_btn and not st.session_state.display_df.empty:
            excel_data = export_excel(st.session_state.display_df)
            st.download_button(
                label="Confirmar Download Excel",
                data=excel_data,
                file_name=f"vendas_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # Exibir dados se disponíveis
        if not st.session_state.display_df.empty:
            df = st.session_state.display_df
            
            # Adicionar filtros
            st.subheader("Filtros")
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            
            with filter_col1:
                if 'Ano' in df.columns:
                    anos_disponiveis = sorted(df['Ano'].dropna().unique().astype(int), reverse=True)
                    if anos_disponiveis:
                        selected_ano = st.selectbox("Ano", options=['Todos'] + list(anos_disponiveis), index=0)
                    else:
                        selected_ano = 'Todos'
                else:
                    selected_ano = 'Todos'
                    
            with filter_col2:
                if 'Mês' in df.columns:
                    meses = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 
                             5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 
                             9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
                    
                    meses_disponiveis = sorted(df['Mês'].dropna().unique().astype(int))
                    meses_opcoes = ['Todos'] + [meses[m] for m in meses_disponiveis if m in meses]
                    
                    selected_mes = st.selectbox("Mês", options=meses_opcoes, index=0)
                    
                    # Converter nome do mês de volta para número
                    selected_mes_num = None
                    if selected_mes != 'Todos':
                        for num, nome in meses.items():
                            if nome == selected_mes:
                                selected_mes_num = num
                                break
                else:
                    selected_mes = 'Todos'
                    selected_mes_num = None
                    
            with filter_col3:
                search_term = st.text_input("Buscar nas observações", "")
            
            # Aplicar filtros
            filtered_df = df.copy()
            
            if selected_ano != 'Todos' and 'Ano' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Ano'] == selected_ano]
                
            if selected_mes != 'Todos' and 'Mês' in filtered_df.columns and selected_mes_num is not None:
                filtered_df = filtered_df[filtered_df['Mês'] == selected_mes_num]
                
            if search_term and 'Observações' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Observações'].str.contains(search_term, case=False, na=False)]
            
            # Detectar valores atípicos (outliers)
            if 'Total' in filtered_df.columns and len(filtered_df) > 5:
                outliers = detect_outliers(filtered_df, 'Total')
                if outliers.any():
                    st.warning(f"Detectados {outliers.sum()} valores atípicos nas vendas!")
            
            # Exibir os dados em uma tabela interativa
            display_cols = ['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']
            
            if 'Observações' in filtered_df.columns:
                display_cols.append('Observações')
                
            visible_df = filtered_df[display_cols] if 'DataFormatada' in filtered_df.columns else filtered_df
            st.dataframe(visible_df, use_container_width=True)

            # Exibir estatísticas
            st.subheader("Resumo Financeiro")
            
            # Mostrar resultados em formato de métricas
            metric_cols = st.columns(5)

            with metric_cols[0]:
                st.metric("Total Cartão", f"R$ {filtered_df['Cartão'].sum():.2f}")

            with metric_cols[1]:
                st.metric("Total Dinheiro", f"R$ {filtered_df['Dinheiro'].sum():.2f}")

            with metric_cols[2]:
                st.metric("Total PIX", f"R$ {filtered_df['Pix'].sum():.2f}")

            with metric_cols[3]:
                st.metric("Total Geral", f"R$ {filtered_df['Total'].sum():.2f}")
                
            with metric_cols[4]:
                if len(filtered_df) > 0:
                    media = filtered_df['Total'].mean()
                    st.metric("Média por Venda", f"R$ {media:.2f}")

            # Criar gráficos com Altair
            st.subheader("Visualização dos Dados")

            # Preparar dados para o gráfico de pizza
            payment_data = pd.DataFrame({
                'Método': ['Cartão', 'Dinheiro', 'PIX'],
                'Valor': [filtered_df['Cartão'].sum(), filtered_df['Dinheiro'].sum(), filtered_df['Pix'].sum()]
            })
            
            # Calcular percentuais
            total_valor = payment_data['Valor'].sum()
            if total_valor > 0:
                payment_data['Percentual'] = (payment_data['Valor'] / total_valor * 100).round(1)
                payment_data['Label'] = payment_data.apply(lambda x: f"{x['Método']}: {x['Percentual']}%", axis=1)
            else:
                payment_data['Percentual'] = 0
                payment_data['Label'] = payment_data['Método']

            # Gráfico de pizza/donut com Altair
            viz_col1, viz_col2 = st.columns(2)
            
            with viz_col1:
                st.write("**Distribuição por Método de Pagamento**")

                # Criando o gráfico de donut com Altair
                base = alt.Chart(payment_data).encode(
                    theta=alt.Theta("Valor:Q", stack=True),
                    color=alt.Color("Método:N", 
                                  scale=alt.Scale(domain=['Cartão', 'Dinheiro', 'PIX'],
                                                range=['#4c78a8', '#72b7b2', '#54a24b']),
                                  legend=alt.Legend(title="Método de Pagamento")),
                    tooltip=["Método", "Valor", "Percentual"]
                )

                pie = base.mark_arc(innerRadius=50, outerRadius=100)
                text = base.mark_text(radius=130, size=14).encode(text="Label:N")

                donut_chart = (pie + text).properties(
                    height=300,
                    title="Distribuição por Método de Pagamento"
                )

                st.altair_chart(donut_chart, use_container_width=True)
            
            with viz_col2:
                if 'DiaSemana' in filtered_df.columns:
                    st.write("**Vendas por Dia da Semana**")
                    
                    # Ordem dos dias da semana
                    dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    dias_nomes = {'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta', 
                                'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
                    
                    # Agrupar por dia da semana
                    weekday_data = filtered_df.groupby('DiaSemana')['Total'].agg(['sum', 'count']).reset_index()
                    
                    # Renomear dias para português
                    weekday_data['DiaSemana'] = weekday_data['DiaSemana'].map(dias_nomes)
                    
                    # Ordenar os dias da semana
                    weekday_data['ordem'] = weekday_data['DiaSemana'].map({dias_nomes[d]: i for i, d in enumerate(dias_ordem)})
                    weekday_data = weekday_data.sort_values('ordem')
                    
                    # Criar gráfico de barras
                    bars = alt.Chart(weekday_data).mark_bar().encode(
                        x=alt.X('DiaSemana:N', title='Dia da Semana', sort=None),
                        y=alt.Y('sum:Q', title='Total de Vendas (R$)'),
                        color=alt.Color('DiaSemana:N', legend=None),
                        tooltip=['DiaSemana', 'sum', 'count']
                    ).properties(
                        title='Vendas por Dia da Semana',
                        height=300
                    )
                    
                    st.altair_chart(bars, use_container_width=True)

            # Adicionar gráfico de barras com os totais diários
            if 'Data' in filtered_df.columns:
                st.subheader("Vendas por Data")

                # Agrupar por data formatada e somar os valores
                date_column = 'DataFormatada' if 'DataFormatada' in filtered_df.columns else 'Data'
                daily_sales = filtered_df.groupby(date_column).sum().reset_index()

                # Convertendo para formato longo (tidy) para Altair
                daily_sales_long = pd.melt(
                    daily_sales,
                    id_vars=[date_column],
                    value_vars=['Cartão', 'Dinheiro', 'Pix'],
                    var_name='Método',
                    value_name='Valor'
                )

                # Criando o gráfico de barras empilhadas com Altair
                bar_chart = alt.Chart(daily_sales_long).mark_bar().encode(
                    x=alt.X(f'{date_column}:N', title='Data', sort=None),
                    y=alt.Y('sum(Valor):Q', title='Valor (R$)'),
                    color=alt.Color('Método:N', 
                                  scale=alt.Scale(domain=['Cartão', 'Dinheiro', 'Pix'],
                                                range=['#4c78a8', '#72b7b2', '#54a24b']),
                                  legend=alt.Legend(title="Método de Pagamento")),
                    tooltip=[date_column, 'Método', 'Valor']
                ).properties(
                    title='Vendas Diárias por Método de Pagamento'
                )

                st.altair_chart(bar_chart, use_container_width=True)

                # Adicionar gráfico de linha para tendência de vendas totais
                line_chart = alt.Chart(daily_sales).mark_line(point=True).encode(
                    x=alt.X(f'{date_column}:N', title='Data', sort=None),
                    y=alt.Y('Total:Q', title='Total de Vendas (R$)'),
                    tooltip=[date_column, 'Total']
                ).properties(
                    title='Tendência de Vendas Totais'
                )

                st.altair_chart(line_chart, use_container_width=True)

    with tab3:
        st.header("Análise de Acúmulo de Capital")

        # Botão para carregar dados
        if st.button("📈 Carregar Dados", key="btn_load_analysis", use_container_width=False):
            with st.spinner("Processando dados..."):
                # Carregar os dados da planilha
                df_raw, _ = read_google_sheet()

                if not df_raw.empty:
                    # Processar dados
                    df = process_data(df_raw.copy())

                    if 'Data' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Data']):
                        # Obter anos e meses únicos para os filtros
                        anos = sorted(df['Ano'].unique())

                        # Filtros de data
                        st.subheader("Filtros de Período")
                        
                        filter_container = st.container()
                        with filter_container:
                            filter_type = st.radio(
                                "Tipo de Filtro",
                                ["Por Ano/Mês", "Intervalo de Datas", "Períodos Predefinidos"],
                                horizontal=True
                            )
                            
                            if filter_type == "Por Ano/Mês":
                                col1, col2 = st.columns(2)

                                with col1:
                                    # Filtro de ano
                                    selected_anos = st.multiselect(
                                        "Selecione o(s) Ano(s):",
                                        options=anos,
                                        default=anos
                                    )

                                    # Filtrar por anos selecionados
                                    df_filtered = df[df['Ano'].isin(selected_anos)]

                                with col2:
                                    # Filtro de mês com números e nomes
                                    meses_disponiveis = sorted(df_filtered['Mês'].unique())
                                    meses_nomes = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
                                    meses_opcoes = [f"{m} - {meses_nomes[m]}" for m in meses_disponiveis]

                                    selected_meses_str = st.multiselect(
                                        "Selecione o(s) Mês(es):",
                                        options=meses_opcoes,
                                        default=meses_opcoes
                                    )

                                    # Extrair apenas o número do mês
                                    selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]

                                    # Aplicar filtro de meses
                                    df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)]
