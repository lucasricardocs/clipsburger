import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
st.set_page_config(page_title="Sistema de Registro do Clips Burger", layout="centered")

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
        worksheet_name = 'Vendas'  # Defina aqui a aba padrão que será lida
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

def process_data(df):
    """Função para processar e preparar os dados"""
    if not df.empty:
        for col in ['Cartão', 'Dinheiro', 'Pix']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df['Total'] = df['Cartão'].fillna(0) + df['Dinheiro'].fillna(0) + df['Pix'].fillna(0)
        if 'Data' in df.columns:
            try:
                df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['MêsNome'] = df['Data'].dt.strftime('%B')
                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
            except ValueError:
                st.warning("Formato de data inconsistente na planilha.")
            except Exception as e:
                st.error(f"Erro ao processar a coluna 'Data': {e}")
    return df

def main():
    st.title("📊 Sistema de Registro do Clips Burger")
    st.image("logo.png", width=200)
    
    tab1, tab2, tab3 = st.tabs(["Registrar Vendas e Compras", "Análise de Vendas", "Análise de Compras"])

    with tab1:
        st.header("Registrar Nova Venda ou Compra")
        
        # Caixa de Registro de Vendas
        st.subheader("Registrar Venda")
        with st.form("venda_form"):
            data_venda = st.date_input("Data da Venda", datetime.now())
            col1, col2, col3 = st.columns(3)
            with col1:
                cartao = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f")
            with col2:
                dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f")
            with col3:
                pix = st.number_input("PIX (R$)", min_value=0.0, format="%.2f")
            total_venda = cartao + dinheiro + pix
            st.markdown(f"**Total da Venda: R$ {total_venda:.2f}**")
            submitted_venda = st.form_submit_button("Registrar Venda")
            if submitted_venda:
                if cartao > 0 or dinheiro > 0 or pix > 0:
                    formatted_date = data_venda.strftime('%d/%m/%Y')
                    _, worksheet = read_google_sheet()
                    if worksheet:
                        # Registrar venda na planilha
                        new_row_venda = [formatted_date, float(cartao), float(dinheiro), float(pix)]
                        worksheet.append_row(new_row_venda)
                        st.success("Venda registrada com sucesso!")
                else:
                    st.warning("Pelo menos um valor de venda deve ser maior que zero.")
        
        # Caixa de Registro de Compras
        st.subheader("Registrar Compra")
        with st.form("compra_form"):
            data_compra = st.date_input("Data da Compra", datetime.now())
            col1, col2, col3 = st.columns(3)
            with col1:
                cartao_compra = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f")
            with col2:
                dinheiro_compra = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f")
            with col3:
                pix_compra = st.number_input("PIX (R$)", min_value=0.0, format="%.2f")
            total_compra = cartao_compra + dinheiro_compra + pix_compra
            st.markdown(f"**Total da Compra: R$ {total_compra:.2f}**")
            submitted_compra = st.form_submit_button("Registrar Compra")
            if submitted_compra:
                if cartao_compra > 0 or dinheiro_compra > 0 or pix_compra > 0:
                    formatted_date = data_compra.strftime('%d/%m/%Y')
                    _, worksheet = read_google_sheet()
                    if worksheet:
                        # Registrar compra na planilha
                        new_row_compra = [formatted_date, float(cartao_compra), float(dinheiro_compra), float(pix_compra)]
                        worksheet.append_row(new_row_compra)
                        st.success("Compra registrada com sucesso!")
                else:
                    st.warning("Pelo menos um valor de compra deve ser maior que zero.")

# Tabs
aba1, aba2, aba3, aba4 = st.tabs(["📋 Registro", "📊 Análise de Vendas", "🛒 Análise de Compras", "📈 Estatísticas"])

with aba1:
    st.subheader("Registro de Vendas")
    with st.form("form_vendas"):
        data_venda = st.date_input("Data da Venda", value=datetime.today())
        col1, col2, col3 = st.columns(3)
        with col1:
            cartao = st.number_input("Cartão", min_value=0.0, step=0.01)
        with col2:
            dinheiro = st.number_input("Dinheiro", min_value=0.0, step=0.01)
        with col3:
            pix = st.number_input("PIX", min_value=0.0, step=0.01)
        total = cartao + dinheiro + pix
        st.write(f"**Total: R${total:.2f}**")
        enviar_venda = st.form_submit_button("Registrar Venda")
        if enviar_venda:
            append_row("Vendas", [data_venda.strftime('%d/%m/%Y'), cartao, dinheiro, pix, total])
            st.success("Venda registrada com sucesso!")

    st.subheader("Registro de Compras")
    with st.form("form_compras"):
        data_compra = st.date_input("Data da Compra", value=datetime.today())
        col1, col2, col3 = st.columns(3)
        with col1:
            pao = st.number_input("Pão", min_value=0.0, step=0.01)
        with col2:
            frios = st.number_input("Frios", min_value=0.0, step=0.01)
        with col3:
            bebidas = st.number_input("Bebidas", min_value=0.0, step=0.01)
        enviar_compra = st.form_submit_button("Registrar Compra")
        if enviar_compra:
            append_row("Compras", [data_compra.strftime('%d/%m/%Y'), pao, frios, bebidas])
            st.success("Compra registrada com sucesso!")

with aba2:
    st.header("Análise de Vendas")
    df_vendas, _ = read_worksheet("Vendas")
    df_vendas = process_vendas(df_vendas)

    if not df_vendas.empty:
        current_month = datetime.now().month
        current_year = datetime.now().year
        anos = sorted(df_vendas['Ano'].unique())
        selected_anos = st.sidebar.multiselect("Ano(s):", anos, default=[current_year])
        meses_disponiveis = sorted(df_vendas[df_vendas['Ano'].isin(selected_anos)]['Mês'].unique())
        meses_nomes = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
        selected_meses_str = st.sidebar.multiselect("Mês(es):", [f"{m} - {meses_nomes[m]}" for m in meses_disponiveis], default=[f"{current_month} - {meses_nomes[current_month]}"])
        selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]

        df_filtered = df_vendas[df_vendas['Ano'].isin(selected_anos)]
        df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)]

        st.subheader("Resumo das Vendas")
        st.dataframe(df_filtered[['DataFormatada', 'Cartão', 'Dinheiro', 'PIX', 'Total']], use_container_width=True)

        st.subheader("Gráfico de Totais por Categoria")
        melted_df = df_filtered.melt(id_vars=['DataFormatada'], value_vars=['Cartão', 'Dinheiro', 'PIX'], var_name='Meio', value_name='Valor')
        chart = alt.Chart(melted_df).mark_bar().encode(
            x=alt.X('DataFormatada:N', title='Data', axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('Valor:Q', title='Valor (R$)'),
            color='Meio:N',
            tooltip=['DataFormatada', 'Meio', 'Valor']
        ).properties(width=700, height=400)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Nenhuma venda encontrada.")

with aba3:
    st.header("Análise Detalhada de Compras")
    df_compras, _ = read_worksheet("Compras")
    df_compras = process_compras(df_compras)

    if not df_compras.empty:
        current_month = datetime.now().month
        current_year = datetime.now().year
        anos = sorted(df_compras['Ano'].unique())
        selected_anos = st.sidebar.multiselect("Ano(s):", anos, default=[current_year])
        meses_disponiveis = sorted(df_compras[df_compras['Ano'].isin(selected_anos)]['Mês'].unique())
        meses_nomes = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
        selected_meses_str = st.sidebar.multiselect("Mês(es):", [f"{m} - {meses_nomes[m]}" for m in meses_disponiveis], default=[f"{current_month} - {meses_nomes[current_month]}"])
        selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]

        df_filtered = df_compras[df_compras['Ano'].isin(selected_anos)]
        df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)]

        st.subheader("Compras Filtradas")
        st.dataframe(df_filtered[['DataFormatada', 'Pão', 'Frios', 'Bebidas']], use_container_width=True, height=300)

        st.subheader("Distribuição de Compras por Categoria")
        compras_sum = {
            'Categoria': ['Pão', 'Frios', 'Bebidas'],
            'Valor': [
                df_filtered['Pão'].sum(),
                df_filtered['Frios'].sum(),
                df_filtered['Bebidas'].sum()
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

        st.subheader("Compras Diárias por Categoria")
        daily_compras = df_filtered.melt(
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
        st.info("Não há dados de compras para exibir.")


with aba4:
    st.header("📈 Estatísticas de Vendas")

    with st.spinner("Carregando dados..."):
        df_raw, _ = read_google_sheet()
        df = process_data(df_raw.copy()) if not df_raw.empty else pd.DataFrame()

        if not df.empty:
            # Filtros de Ano e Mês
            st.sidebar.header("🔍 Filtros Estatísticos")
            anos = sorted(df['Ano'].unique())
            ano_selecionado = st.sidebar.selectbox("Selecione o Ano:", anos, index=len(anos) - 1)

            meses_disponiveis = sorted(df[df['Ano'] == ano_selecionado]['Mês'].unique())
            nomes_meses = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
            mes_opcoes = [f"{m} - {nomes_meses[m]}" for m in meses_disponiveis]
            mes_selecionado_str = st.sidebar.selectbox("Selecione o Mês:", mes_opcoes)
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
                dia_mais_vende = media_semana.idxmax()
                dia_menos_vende = media_semana.idxmin()

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

                st.markdown("""
                <div style='text-align: center; color: gray; font-size: small;'>
                    Estatísticas baseadas nas vendas registradas para o mês e ano selecionados.
                </div>
                """, unsafe_allow_html=True)

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
