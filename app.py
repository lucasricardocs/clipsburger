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
        with st.expander("Clique para expandir o formulário"):
            with st.form("registro_form"):
                data = st.date_input("Data", datetime.now())
                col1, col2, col3 = st.columns(3)
                with col1:
                    cartao = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f")
                with col2:
                    dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f")
                with col3:
                    pix = st.number_input("PIX (R$)", min_value=0.0, format="%.2f")
                total = cartao + dinheiro + pix
                st.markdown(f"**Total da venda/compra: R$ {total:.2f}**")
                submitted = st.form_submit_button("Registrar")
                if submitted:
                    if cartao > 0 or dinheiro > 0 or pix > 0:
                        formatted_date = data.strftime('%d/%m/%Y')
                        _, worksheet = read_google_sheet()
                        if worksheet:
                            # Função para registrar na planilha, pode ser para vendas ou compras
                            new_row = [formatted_date, float(cartao), float(dinheiro), float(pix)]
                            worksheet.append_row(new_row)
                            st.success("Dados registrados com sucesso!")
                    else:
                        st.warning("Pelo menos um valor de venda/compra deve ser maior que zero.")
    
    with tab2:
        st.header("Análise de Vendas")
        # Filtros na sidebar
        with st.sidebar:
            st.header("🔍 Filtros")
            with st.spinner("Carregando dados..."):
                df_raw, _ = read_google_sheet()
                df = process_data(df_raw.copy()) if not df_raw.empty else pd.DataFrame()

                if not df.empty and 'Data' in df.columns:
                    # Obter mês e ano atual
                    current_month = datetime.now().month
                    current_year = datetime.now().year
                    
                    # Filtro de Ano
                    anos = sorted(df['Ano'].unique())
                    default_anos = [current_year] if current_year in anos else anos
                    selected_anos = st.multiselect(
                        "Selecione o(s) Ano(s):",
                        options=anos,
                        default=default_anos
                    )

                    # Filtro de Mês
                    meses_disponiveis = sorted(df[df['Ano'].isin(selected_anos)]['Mês'].unique()) if selected_anos else []
                    meses_nomes = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
                    meses_opcoes = [f"{m} - {meses_nomes[m]}" for m in meses_disponiveis]
                    
                    # Seleção de mês
                    selected_meses_str = st.multiselect(
                        "Selecione o(s) Mês(es):",
                        options=meses_opcoes,
                        default=meses_opcoes
                    )
                    selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]

        # Conteúdo principal da análise
        if not df_raw.empty:
            if 'Data' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Data']):
                # Aplicar filtros
                df_filtered = df[df['Ano'].isin(selected_anos)] if selected_anos else df
                df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)] if selected_meses else df_filtered

                st.subheader("Dados Filtrados")
                st.dataframe(df_filtered[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']]
                             if 'DataFormatada' in df_filtered.columns else df_filtered, 
                             use_container_width=True,
                             height=300)

                # Gráficos
                st.subheader("Distribuição por Método de Pagamento")
                payment_filtered = pd.DataFrame({
                    'Método': ['Cartão', 'Dinheiro', 'PIX'],
                    'Valor': [df_filtered['Cartão'].sum(), df_filtered['Dinheiro'].sum(), df_filtered['Pix'].sum()]
                })
                
                pie_chart = alt.Chart(payment_filtered).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta("Valor:Q", stack=True),
                    color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
                    tooltip=["Método", "Valor"]
                ).properties(
                    width=700,
                    height=500
                )
                text = pie_chart.mark_text(radius=120, size=16).encode(text="Valor:Q")
                st.altair_chart(pie_chart + text, use_container_width=True)

                st.subheader("Vendas Diárias por Método de Pagamento")
                date_column = 'DataFormatada' if 'DataFormatada' in df_filtered.columns else 'Data'
                daily_data = df_filtered.melt(id_vars=[date_column], 
                                            value_vars=['Cartão', 'Dinheiro', 'Pix'],
                                            var_name='Método', 
                                            value_name='Valor')
                
                bar_chart = alt.Chart(daily_data).mark_bar(size=30).encode(
                    x=alt.X(f'{date_column}:N', title='Data', axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y('Valor:Q', title='Valor (R$)'),
                    color=alt.Color('Método:N', legend=alt.Legend(title="Método")),
                    tooltip=[date_column, 'Método', 'Valor']
                ).properties(
                    width=700,
                    height=500
                )
                st.altair_chart(bar_chart, use_container_width=True)

                st.subheader("Acúmulo de Capital ao Longo do Tempo")
                df_accumulated = df_filtered.sort_values('Data').copy()
                df_accumulated['Total Acumulado'] = df_accumulated['Total'].cumsum()
                
                line_chart = alt.Chart(df_accumulated).mark_line(point=True, strokeWidth=3).encode(
                    x=alt.X('Data:T', title='Data'),
                    y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
                    tooltip=['DataFormatada', 'Total Acumulado']
                ).properties(
                    width=700,
                    height=500
                )
                st.altair_chart(line_chart, use_container_width=True)

            else:
                st.info("Não há dados de data para análise.")
        else:
            st.info("Não há dados para exibir.")

    with tab3:
        st.header("Análise de Compras")
        # O código da análise de compras será similar ao de vendas
        # Basta duplicar a lógica da tab2 para análise de compras

    # Adicionar rodapé
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
