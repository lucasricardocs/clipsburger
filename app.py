import streamlit as st
import gspread
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import altair as alt

# Configuração da página
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="wide")

def read_google_sheet():
    """Função para ler os dados da planilha Google Sheets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/spreadsheets.readonly', 'https://www.googleapis.com/auth/drive.readonly']
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
        worksheet_name = 'Vendas'
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

def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet):
    """Função para adicionar dados à planilha Google Sheets"""
    if worksheet is None:
        st.error("Não foi possível acessar a planilha.")
        return
    try:
        new_row = [date, float(cartao), float(dinheiro), float(pix)]
        worksheet.append_row(new_row)
        st.success("Dados registrados com sucesso!")
    except Exception as e:
        st.error(f"Erro ao adicionar dados: {e}")

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

def create_pie_chart(df_filtered):
    """Cria gráfico de pizza usando Altair"""
    if df_filtered.empty:
        return alt.Chart(pd.DataFrame({'Método': [], 'Valor': []})).mark_arc().encode(theta=alt.Theta("Valor", stack=True), color="Método")

    data_melted = df_filtered[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index(name='Valor')
    data_melted.rename(columns={'index': 'Método'}, inplace=True)

    pie = alt.Chart(data_melted).mark_arc(outerRadius=120, innerRadius=40).encode(
        theta=alt.Theta("Valor", stack=True),
        color=alt.Color("Método"),
        order=alt.Order("Valor", sort="descending"),
        tooltip=["Método", alt.Tooltip("Valor", format=",.2f"), alt.Tooltip("Valor", format=".1%", calculate='datum.Valor / sum(datum.Valor) over ()')]
    ).properties(
        title='Distribuição por Método de Pagamento'
    )

    text = pie.mark_text(radius=140).encode(
        text=alt.Text('Valor', format='.1%'),
        order=alt.Order('Valor', sort='descending'),
        color=alt.value('black')
    )

    return pie + text

def create_bar_chart(df_filtered):
    """Cria gráfico de barras usando Altair"""
    date_column = 'DataFormatada' if 'DataFormatada' in df_filtered.columns else 'Data'
    daily = df_filtered.groupby(date_column)[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index().melt(id_vars=[date_column], var_name='Método', value_name='Valor')

    bar_chart = alt.Chart(daily).mark_bar().encode(
        x=alt.X(date_column, title='Data', sort='-x'),
        y=alt.Y('Valor', title='Valor (R$)'),
        color='Método',
        tooltip=[date_column, 'Método', alt.Tooltip('Valor', format=",.2f")]
    ).properties(
        title='Vendas Diárias por Método de Pagamento'
    ).interactive()

    return bar_chart

def create_line_chart(df_filtered):
    """Cria gráfico de linha usando Altair"""
    if df_filtered.empty:
        return alt.Chart(pd.DataFrame({'DataFormatada': [], 'Total Acumulado': []})).mark_line(point=True).encode(x='DataFormatada', y='Total Acumulado')

    df_acum = df_filtered.sort_values('Data').copy()
    df_acum['Total Acumulado'] = df_acum['Total'].cumsum()

    line_chart = alt.Chart(df_acum).mark_line(point=True).encode(
        x=alt.X('DataFormatada', title='Data', sort='-x'),
        y=alt.Y('Total Acumulado', title='Capital Acumulado (R$)'),
        tooltip=['DataFormatada', alt.Tooltip('Total Acumulado', format=",.2f")]
    ).properties(
        title='Acúmulo de Capital ao Longo do Tempo'
    ).interactive()

    return line_chart

def create_monthly_revenue_chart(df_filtered):
    """Cria gráfico de barras da receita mensal usando Altair"""
    if df_filtered.empty:
        return alt.Chart(pd.DataFrame({'AnoMês': [], 'Total': []})).mark_bar().encode(x='AnoMês', y='Total')

    monthly_revenue = df_filtered.groupby('AnoMês')['Total'].sum().reset_index()

    chart = alt.Chart(monthly_revenue).mark_bar().encode(
        x=alt.X('AnoMês', title='Mês'),
        y=alt.Y('Total', title='Receita Total (R$)'),
        tooltip=['AnoMês', alt.Tooltip('Total', format=",.2f")]
    ).properties(
        title='Receita Mensal Total'
    ).interactive()

    return chart

def create_payment_type_monthly_chart(df_filtered):
    """Cria gráfico de barras empilhadas da receita mensal por tipo de pagamento usando Altair"""
    if df_filtered.empty:
        return alt.Chart(pd.DataFrame({'AnoMês': [], 'Método': [], 'Valor': []})).mark_bar().encode(x='AnoMês', y='Valor', color='Método')

    monthly_payment = df_filtered.groupby('AnoMês')[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index().melt(id_vars=['AnoMês'], var_name='Método', value_name='Valor')

    chart = alt.Chart(monthly_payment).mark_bar().encode(
        x=alt.X('AnoMês', title='Mês'),
        y=alt.Y('Valor', title='Valor (R$)'),
        color='Método',
        tooltip=['AnoMês', 'Método', alt.Tooltip('Valor', format=",.2f")]
    ).properties(
        title='Receita Mensal por Tipo de Pagamento'
    ).interactive()

    return chart

def main():
    st.title("📊 Sistema de Registro de Vendas")
    tab1, tab3 = st.tabs(["Registrar Venda", "Análise Detalhada"])

    with tab1:
        st.header("Registrar Nova Venda")
        with st.form("venda_form"):
            data = st.date_input("Data", datetime.now())
            col1, col2, col3 = st.columns(3)
            with col1:
                cartao = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f")
            with col2:
                dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f")
            with col3:
                pix = st.number_input("PIX (R$)", min_value=0.0, format="%.2f")
            total = cartao + dinheiro + pix
            st.markdown(f"**Total da venda: R$ {total:.2f}**")
            submitted = st.form_submit_button("Registrar Venda")
            if submitted:
                if cartao > 0 or dinheiro > 0 or pix > 0:
                    formatted_date = data.strftime('%d/%m/%Y')
                    _, worksheet = read_google_sheet()
                    if worksheet:
                        add_data_to_sheet(formatted_date, cartao, dinheiro, pix, worksheet)
                else:
                    st.warning("Pelo menos um valor de venda deve ser maior que zero.")

        st.subheader("Estatísticas de Registros")
        df_raw, _ = read_google_sheet()
        if not df_raw.empty:
            df = process_data(df_raw.copy())
            if 'DataFormatada' in df.columns:
                num_registros = len(df)
                primeira_venda = df['DataFormatada'].min()
                ultima_venda = df['DataFormatada'].max()
                total_vendido = df['Total'].sum()

                st.markdown(f"**Número Total de Registros:** {num_registros}")
                st.markdown(f"**Primeira Venda Registrada:** {primeira_venda}")
                st.markdown(f"**Última Venda Registrada:** {ultima_venda}")
                st.markdown(f"**Total Vendido (R$):** {total_vendido:.2f}")
            else:
                st.info("Não há dados de data para calcular estatísticas.")
        else:
            st.info("Nenhum registro de venda encontrado.")

    with tab3:
        st.header("Análise Detalhada de Vendas")
        with st.spinner("Carregando dados..."):
            df_raw, _ = read_google_sheet()
            if not df_raw.empty:
                df = process_data(df_raw.copy())
                if 'Data' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Data']):
                    anos = sorted(df['Ano'].unique())
                    selected_anos = st.multiselect("Selecione o(s) Ano(s):", options=anos, default=anos)
                    df_filtered = df[df['Ano'].isin(selected_anos)]

                    meses_disponiveis = sorted(df_filtered['Mês'].unique())
                    meses_nomes = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
                    meses_opcoes = [f"{m} - {meses_nomes[m]}" for m in meses_disponiveis]
                    selected_meses_str = st.multiselect("Selecione o(s) Mês(es):", options=meses_opcoes, default=meses_opcoes)
                    selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]
                    df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)]

                    st.subheader("Dados Filtrados")
                    st.dataframe(df_filtered[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']]
                                 if 'DataFormatada' in df_filtered.columns else df_filtered,
                                 use_container_width=True)

                    st.subheader("Distribuição por Método de Pagamento")
                    fig_pie = create_pie_chart(df_filtered)
                    st.altair_chart(fig_pie, use_container_width=True)

                    st.subheader("Vendas Diárias por Método de Pagamento")
                    fig_bar = create_bar_chart(df_filtered)
                    st.altair_chart(fig_bar, use_container_width=True)

                    st.subheader("Acúmulo de Capital ao Longo do Tempo")
                    fig_line = create_line_chart(df_filtered)
                    st.altair_chart(fig_line, use_container_width=True)

                    st.subheader("Receita Mensal Total")
                    fig_monthly_revenue = create_monthly_revenue_chart(df_filtered)
                    st.altair_chart(fig_monthly_revenue, use_container_width=True)

                    st.subheader("Receita Mensal por Tipo de Pagamento")
                    fig_payment_monthly = create_payment_type_monthly_chart(df_filtered)
                    st.altair_chart(fig_payment_monthly, use_container_width=True)

                else:
                    st.info("Não há dados de data para análise.")
            else:
                st.info("Não há dados para exibir.")

if __name__ == "__main__":
    main()
