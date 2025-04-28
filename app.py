import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
from streamlit_pdf import st_pdf

# Configuração da página
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="centered")

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

def main():
    st.title("📊 Sistema de Registro de Vendas")
    tab1, tab3 = st.tabs(["Registrar Venda", "Análise Detalhada"]) # Removendo tab2

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
                                 if 'DataFormatada' in df_filtered.columns else df_filtered, use_container_width=True)

                    st.subheader("Distribuição por Método de Pagamento")
                    payment_filtered = pd.DataFrame({
                        'Método': ['Cartão', 'Dinheiro', 'PIX'],
                        'Valor': [df_filtered['Cartão'].sum(), df_filtered['Dinheiro'].sum(), df_filtered['Pix'].sum()]
                    })
                    base_pie = alt.Chart(payment_filtered).encode(
                        theta=alt.Theta("Valor:Q", stack=True),
                        color=alt.Color("Método:N", legend=alt.Legend(title="Método de Pagamento")),
                        tooltip=["Método", "Valor"]
                    ).properties(
                        width=400,
                        height=400,
                    )
                    pie_chart = base_pie.mark_arc(outerRadius=150)
                    text_pie = base_pie.mark_text(radius=170).encode(text=alt.Text('Valor:Q', format='.1f'))
                    final_pie = pie_chart + text_pie
                    st.altair_chart(final_pie, use_container_width=True)

                    st.subheader("Vendas Diárias por Método de Pagamento")
                    date_column_filtered = 'DataFormatada' if 'DataFormatada' in df_filtered.columns else 'Data'
                    daily_filtered = df_filtered.groupby(date_column_filtered)[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
                    daily_filtered_long = pd.melt(daily_filtered, id_vars=[date_column_filtered],
                                                    value_vars=['Cartão', 'Dinheiro', 'Pix'],
                                                    var_name='Método', value_name='Valor')
                    bar_chart_filtered = alt.Chart(daily_filtered_long).mark_bar().encode(
                        x=alt.X(f'{date_column_filtered}:N', title='Data', sort=None, axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y('sum(Valor):Q', title='Valor (R$)'),
                        color=alt.Color('Método:N', legend=alt.Legend(title="Pagamento")),
                        tooltip=[date_column_filtered, 'Método', 'Valor']
                    ).properties(
                        width=600,
                        height=400,
                    )
                    st.altair_chart(bar_chart_filtered, use_container_width=True)

                    st.subheader("Acúmulo de Capital ao Longo do Tempo")
                    df_accumulated = df_filtered.sort_values('Data').copy()
                    df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()
                    acum_chart = alt.Chart(df_accumulated).mark_line(point=True).encode(
                        x=alt.X('Data:T', title='Data'), # Usando o tipo 'T' para temporal
                        y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
                        tooltip=['DataFormatada', 'Total Acumulado']
                    ).properties(
                        width=600,
                        height=400,
                    )
                    st.altair_chart(acum_chart, use_container_width=True)

                    # Botão de exportar para PDF
                    pdf_export = st_pdf(unsafe_allow_html=True)
                    if pdf_export:
                        st.success("PDF gerado com sucesso!")

                else:
                    st.info("Não há dados de data para análise.")
            else:
                st.info("Não há dados para exibir.")

if __name__ == "__main__":
    main()
