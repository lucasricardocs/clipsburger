import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
st.set_page_config(page_title="Sistema de Registro de Vendas e Compras", layout="centered")

# IDs e escopos
SPREADSHEET_ID = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def autenticar_google():
    """Autentica com o Google Sheets"""
    credentials_dict = st.secrets["google_credentials"]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def ler_aba(aba_nome):
    """Lê uma aba específica do Google Sheets"""
    try:
        gc = autenticar_google()
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(aba_nome)
        rows = worksheet.get_all_records()
        df = pd.DataFrame(rows)
        return df, worksheet
    except SpreadsheetNotFound:
        st.error(f"Aba '{aba_nome}' não encontrada.")
        return pd.DataFrame(), None
    except Exception as e:
        st.error(f"Erro ao acessar o Google Sheets: {e}")
        return pd.DataFrame(), None

def adicionar_linha(worksheet, dados):
    """Adiciona uma linha a uma worksheet"""
    try:
        worksheet.append_row(dados)
        st.success("Dados registrados com sucesso!")
    except Exception as e:
        st.error(f"Erro ao adicionar dados: {e}")

def processar_dataframe(df, colunas_valor, tipo="Venda"):
    """Processa e formata os dados"""
    if not df.empty:
        for col in colunas_valor:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df['Total'] = df[colunas_valor].sum(axis=1)
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
            df['Ano'] = df['Data'].dt.year
            df['Mês'] = df['Data'].dt.month
            df['MêsNome'] = df['Data'].dt.strftime('%B')
            df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
            df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
    return df

def interface_filtros(df):
    """Renderiza filtros de ano e mês"""
    selected_anos = selected_meses = []
    if not df.empty:
        with st.sidebar:
            st.header("🔍 Filtros")

            anos = sorted(df['Ano'].dropna().unique())
            current_year = datetime.now().year
            default_anos = [current_year] if current_year in anos else anos
            selected_anos = st.multiselect("Selecione o(s) Ano(s):", options=anos, default=default_anos)

            meses_disponiveis = sorted(df[df['Ano'].isin(selected_anos)]['Mês'].unique()) if selected_anos else []
            meses_nomes = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
            meses_opcoes = [f"{m} - {meses_nomes[m]}" for m in meses_disponiveis]
            current_month = datetime.now().month
            default_meses = [f"{current_month} - {meses_nomes[current_month]}"] if current_month in meses_nomes else meses_opcoes
            selected_meses_str = st.multiselect("Selecione o(s) Mês(es):", options=meses_opcoes, default=default_meses)
            selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]
    return selected_anos, selected_meses

def exibir_graficos(df, colunas_valor, titulo="Dados"):
    """Exibe gráficos e dados"""
    if not df.empty and 'Data' in df.columns:
        st.subheader("Dados Filtrados")
        st.dataframe(df[['DataFormatada'] + colunas_valor + ['Total']], use_container_width=True, height=300)

        st.subheader("Distribuição por Categoria")
        resumo = pd.DataFrame({
            'Categoria': colunas_valor,
            'Valor': [df[col].sum() for col in colunas_valor]
        })
        chart = alt.Chart(resumo).mark_arc(innerRadius=50).encode(
            theta=alt.Theta("Valor:Q"),
            color=alt.Color("Categoria:N"),
            tooltip=["Categoria", "Valor"]
        )
        st.altair_chart(chart, use_container_width=True)

        st.subheader("Valores Diários por Categoria")
        melted = df.melt(id_vars=['DataFormatada'], value_vars=colunas_valor, var_name='Categoria', value_name='Valor')
        bar_chart = alt.Chart(melted).mark_bar().encode(
            x=alt.X('DataFormatada:N', title='Data', axis=alt.Axis(labelAngle=-45)),
            y='Valor:Q',
            color='Categoria:N',
            tooltip=['DataFormatada', 'Categoria', 'Valor']
        )
        st.altair_chart(bar_chart, use_container_width=True)

        st.subheader("Acúmulo ao Longo do Tempo")
        df_ordenado = df.sort_values('Data')
        df_ordenado['Total Acumulado'] = df_ordenado['Total'].cumsum()
        line_chart = alt.Chart(df_ordenado).mark_line(point=True).encode(
            x='Data:T',
            y='Total Acumulado:Q',
            tooltip=['DataFormatada', 'Total Acumulado']
        )
        st.altair_chart(line_chart, use_container_width=True)

def main():
    st.title("📊 Sistema de Registro de Vendas e Compras")

    tab1, tab2, tab3 = st.tabs(["Registrar", "Análise de Vendas", "Análise de Compras"])

    # ========== REGISTRO ==========
    with tab1:
        st.header("Registrar Nova Venda")
        with st.form("venda_form"):
            data_venda = st.date_input("Data da venda", datetime.now())
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
                if total > 0:
                    _, worksheet = ler_aba("Vendas")
                    if worksheet:
                        adicionar_linha(worksheet, [
                            data_venda.strftime('%d/%m/%Y'),
                            float(cartao), float(dinheiro), float(pix)
                        ])
                else:
                    st.warning("Informe pelo menos um valor.")

        st.header("Registrar Nova Compra")
        with st.expander("➕ Adicionar Compra"):
            with st.form("compra_form"):
                data_compra = st.date_input("Data da compra", datetime.now())
                col1, col2, col3 = st.columns(3)
                with col1:
                    pao = st.number_input("Pão (R$)", min_value=0.0, format="%.2f", key="pao")
                with col2:
                    frios = st.number_input("Frios (R$)", min_value=0.0, format="%.2f", key="frios")
                with col3:
                    bebidas = st.number_input("Bebidas (R$)", min_value=0.0, format="%.2f", key="bebidas")
                total_compra = pao + frios + bebidas
                st.markdown(f"**Total da compra: R$ {total_compra:.2f}**")
                submitted_compra = st.form_submit_button("Registrar Compra")
                if submitted_compra:
                    if total_compra > 0:
                        _, worksheet_compras = ler_aba("Compras")
                        if worksheet_compras:
                            adicionar_linha(worksheet_compras, [
                                data_compra.strftime('%d/%m/%Y'),
                                float(pao), float(frios), float(bebidas)
                            ])
                    else:
                        st.warning("Informe pelo menos um valor.")

    # ========== ANÁLISE DE VENDAS ==========
    with tab2:
        st.header("📈 Análise Detalhada de Vendas")
        df_vendas_raw, _ = ler_aba("Vendas")
        df_vendas = processar_dataframe(df_vendas_raw.copy(), ['Cartão', 'Dinheiro', 'Pix'])
        anos, meses = interface_filtros(df_vendas)
        if not df_vendas.empty:
            df_filtrado = df_vendas[
                (df_vendas['Ano'].isin(anos)) & (df_vendas['Mês'].isin(meses))
            ]
            exibir_graficos(df_filtrado, ['Cartão', 'Dinheiro', 'Pix'], "Vendas")
        else:
            st.info("Sem dados de vendas disponíveis.")

    # ========== ANÁLISE DE COMPRAS ==========
    with tab3:
        st.header("📉 Análise Detalhada de Compras")
        df_compras_raw, _ = ler_aba("Compras")
        df_compras = processar_dataframe(df_compras_raw.copy(), ['Pão', 'Frios', 'Bebidas'])
        anos_c, meses_c = interface_filtros(df_compras)
        if not df_compras.empty:
            df_compras_filtrado = df_compras[
                (df_compras['Ano'].isin(anos_c)) & (df_compras['Mês'].isin(meses_c))
            ]
            exibir_graficos(df_compras_filtrado, ['Pão', 'Frios', 'Bebidas'], "Compras")
        else:
            st.info("Sem dados de compras disponíveis.")

if __name__ == "__main__":
    main()
