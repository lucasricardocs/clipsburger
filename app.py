import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="centered")

def read_google_sheet():
    """Função para ler os dados da planilha Google Sheets"""
    try:
        # Definindo os escopos corretos para o Google Sheets
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        # Carregando as credenciais do secrets do Streamlit
        credentials_dict = st.secrets["google_credentials"]

        # Crie as credenciais a partir do dicionário do secrets com os escopos corretos
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)

        # Autenticação com o Google Sheets
        gc = gspread.authorize(creds)

        # ID da planilha e nome da aba
        spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
        worksheet_name = 'Vendas'

        # Abrindo a planilha e a aba
        try:
            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)

            # Lendo os dados da planilha
            rows = worksheet.get_all_records()

            # Convertendo para DataFrame
            df = pd.DataFrame(rows)

            return df, worksheet

        except SpreadsheetNotFound:
            st.error(f"Planilha com ID {spreadsheet_id} não encontrada. Verifique o ID e as permissões.")
            return pd.DataFrame(), None

    except Exception as e:
        st.error(f"Erro de autenticação: {str(e)}")
        return pd.DataFrame(), None

def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet):
    """Função para adicionar dados à planilha Google Sheets"""
    if worksheet is None:
        st.error("Não foi possível acessar a planilha para adicionar os dados.")
        return
    try:
        # Preparar os dados para inserção
        new_row = [date, float(cartao), float(dinheiro), float(pix)]

        # Adicionar a nova linha à planilha
        worksheet.append_row(new_row)

        # Mostrar mensagem de sucesso
        st.success("Dados registrados com sucesso!")

    except Exception as e:
        st.error(f"Erro ao adicionar dados: {str(e)}")

def process_data(df):
    """Função para processar e preparar os dados"""
    if not df.empty:
        # Converter colunas numéricas
        for col in ['Cartão', 'Dinheiro', 'Pix']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Calcular total por linha
        df['Total'] = df['Cartão'].fillna(0) + df['Dinheiro'].fillna(0) + df['Pix'].fillna(0)

        # Converter a coluna de data para datetime
        if 'Data' in df.columns:
            # Tentar converter a coluna Data
            try:
                df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')

                # Adicionar colunas de mês e ano para filtros
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['MêsNome'] = df['Data'].dt.strftime('%B')  # Nome do mês
                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')  # Formato AAAA-MM para ordenação

                # Formatar a data de volta para exibição
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
            except ValueError:
                st.warning("Formato de data na planilha é inconsistente. Alguns filtros podem não funcionar.")
            except Exception as e:
                st.error(f"Erro ao processar a coluna 'Data': {e}")

    return df

def main():
    st.title("📊 Sistema de Registro de Vendas")

    # Criar abas
    tab1, tab2, tab3 = st.tabs(["Registrar Venda", "Visualizar Vendas", "Análise de Capital"])

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

            # Calcular e mostrar o total
            total = cartao + dinheiro + pix
            st.markdown(f"**Total da venda: R$ {total:.2f}**")

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
                        add_data_to_sheet(formatted_date, cartao, dinheiro, pix, worksheet)
                else:
                    st.warning("Pelo menos um valor de venda deve ser maior que zero.")

    with tab2:
        st.header("Histórico de Vendas")

        # Botão para atualizar os dados
        if st.button("Atualizar Dados", key="btn_update_history"):
            with st.spinner("Carregando dados..."):
                # Carregar os dados da planilha
                df_raw, _ = read_google_sheet()

                if not df_raw.empty:
                    # Processar dados
                    df = process_data(df_raw.copy())

                    # Exibir os dados em uma tabela interativa
                    st.dataframe(df[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']]
                                 if 'DataFormatada' in df.columns
                                 else df, use_container_width=True)

                    # Exibir estatísticas
                    st.subheader("Resumo Financeiro")
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Total Cartão", f"R$ {df['Cartão'].sum():.2f}")

                    with col2:
                        st.metric("Total Dinheiro", f"R$ {df['Dinheiro'].sum():.2f}")

                    with col3:
                        st.metric("Total PIX", f"R$ {df['Pix'].sum():.2f}")

                    with col4:
                        st.metric("Total Geral", f"R$ {df['Total'].sum():.2f}")

                    # Criar gráficos com Altair
                    st.subheader("Visualização dos Dados")

                    # Preparar dados para o gráfico de pizza
                    payment_data = pd.DataFrame({
                        'Método': ['Cartão', 'Dinheiro', 'PIX'],
                        'Valor': [df['Cartão'].sum(), df['Dinheiro'].sum(), df['Pix'].sum()]
                    })

                    # Gráfico de pizza simplificado com Altair
                    st.write("**Distribuição por Método de Pagamento**")

                    # Criando o gráfico de donut com Altair
                    base = alt.Chart(payment_data).encode(
                        theta=alt.Theta("Valor:Q", stack=True),
                        color=alt.Color("Método:N", legend=alt.Legend(title="Método de Pagamento")),
                        tooltip=["Método", "Valor"]
                    )

                    pie = base.mark_arc(innerRadius=50, outerRadius=100)
                    text = base.mark_text(radius=130, size=14).encode(text="Método:N")

                    donut_chart = (pie + text).properties(
                        width=400,
                        height=400,
                        title="Distribuição por Método de Pagamento"
                    )

                    st.altair_chart(donut_chart, use_container_width=True)

                    # Adicionar gráfico de barras com os totais diários
                    if 'Data' in df.columns:
                        st.subheader("Vendas por Data")

                        # Agrupar por data formatada e somar os valores
                        date_column = 'DataFormatada' if 'DataFormatada' in df.columns else 'Data'
                        daily_sales = df.groupby(date_column).sum().reset_index()

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
                            color=alt.Color('Método:N', legend=alt.Legend(title="Método de Pagamento")),
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

                    else:
                        st.info("Não há dados para exibir ou houve um problema ao carregar a planilha.")
                    st.success("Dados atualizados!")
                else:
                    st.info("Não há dados para exibir ou houve um problema ao carregar a planilha.")

    with tab3:
        st.header("Análise de Acúmulo de Capital")

        # Botão para carregar dados
        if st.button("Carregar Dados", key="btn_load_analysis"):
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

                        # Ordenar por data para o gráfico de acúmulo
                        df_filtered = df_filtered.sort_values('Data')

                        # Criar DataFrame para o gráfico de acúmulo
                        df_accumulated = df_filtered.copy()
                        df_accumulated['Data'] = df_accumulated['Data'].dt.strftime('%Y-%m-%d')

                        # Calcular valores acumulados
                        df_accumulated['Cartão Acumulado'] = df_accumulated['Cartão'].cumsum()
                        df_accumulated['Dinheiro Acumulado'] = df_accumulated['Dinheiro'].cumsum()
                        df_accumulated['PIX Acumulado'] = df_accumulated['Pix'].cumsum()
                        df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()

                        # Exibir tabela de acúmulo
                        st.subheader("Valores Acumulados")
                        st.dataframe(df_accumulated[[
                            'Data', 'Total', 'Total Acumulado',
                            'Cartão', 'Cartão Acumulado',
                            'Dinheiro', 'Dinheiro Acumulado',
                            'Pix', 'PIX Acumulado'
                        ]], use_container_width=True)

                        # Gráfico de acúmulo de capital total
                        st.subheader("Gráfico de Acúmulo de Capital")

                        # Criar gráfico de linha para o acúmulo total
                        acum_chart = alt.Chart(df_accumulated).mark_area(
                            opacity=0.5,
                            line=True
                        ).encode(
                            x=alt.X('Data:T', title='Data'),
                            y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
                            tooltip=['Data', 'Total', 'Total Acumulado']
                        ).properties(
                            title='Acúmulo de Capital ao Longo do Tempo'
                        )

                        st.altair_chart(acum_chart, use_container_width=True)

                        # Gráfico de acúmulo por método de pagamento
                        st.subheader("Acúmulo por Método de Pagamento")

                        # Transformar dados para formato longo
                        df_acum_long = pd.melt(
                            df_accumulated,
                            id_vars=['Data'],
                            value_vars=['Cartão Acumulado', 'Dinheiro Acumulado', 'PIX Acumulado'],
                            var_name='Método',
                            value_name='Valor Acumulado'
                        )

                        # Limpar os nomes dos métodos
                        df_acum_long['Método'] = df_acum_long['Método'].str.replace(' Acumulado', '')

                        # Criar gráfico de linha múltipla
                        multi_line = alt.Chart(df_acum_long).mark_line().encode(
                            x=alt.X('Data:T', title='Data'),
                            y=alt.Y('Valor Acumulado:Q', title='Valor Acumulado (R$)'),
                            color=alt.Color('Método:N', legend=alt.Legend(title="Método de Pagamento")),
                            tooltip=['Data', 'Método', 'Valor Acumulado']
                        ).properties(
                            title='Acúmulo de Capital por Método de Pagamento'
                        )

                        st.altair_chart(multi_line, use_container_width=True)

                        # Resumo do período selecionado
                        st.subheader("Resumo do Período Selecionado")

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Cartão", f"R$ {df_filtered['Cartão'].sum():.2f}")
                        with col2:
                            st.metric("Total Dinheiro", f"R$ {df_filtered['Dinheiro'].sum():.2f}")
                        with col3:
                            st.metric("Total PIX", f"R$ {df_filtered['Pix'].sum():.2f}")
                        with col4:
                            st.metric("Total Geral", f"R$ {df_filtered['Total'].sum():.2f}")

                       # Calcular média diária para o período selecionado
                        dias_unicos = df_filtered['Data'].nunique()
                        if dias_unicos > 0:
                            media_diaria = df_filtered['Total'].sum() / dias_unicos
                            st.metric("Média Diária", f"R$ {media_diaria:.2f}")
                        else:
                            st.warning("Selecione pelo menos um dia dentro do período para calcular a média diária.")
                    else:
                        st.warning("Selecione pelo menos um ano para visualizar os dados.")
                else:
                    st.error("Formato de data não reconhecido. Não é possível criar a análise temporal.")
            else:
                st.info("Não há dados para analisar ou houve um problema ao carregar a planilha.")

if __name__ == "__main__":
    main()
