import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
st.set_page_config(page_title="Sistema de Registro do Clips Burger", layout="centered")

def read_google_sheet(worksheet_name="Vendas"):
    """Função para ler os dados da planilha Google Sheets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 
                 'https://www.googleapis.com/auth/spreadsheets.readonly', 
                 'https://www.googleapis.com/auth/drive.readonly']
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet_id = '1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg'
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

def process_vendas(df):
    """Função para processar dados de vendas"""
    if not df.empty:
        for col in ['Cartão', 'Dinheiro', 'PIX']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df['Total'] = df['Cartão'].fillna(0) + df['Dinheiro'].fillna(0) + df['PIX'].fillna(0)
        if 'Data' in df.columns:
            try:
                df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['MêsNome'] = df['Data'].dt.strftime('%B')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
            except Exception as e:
                st.error(f"Erro ao processar a coluna 'Data': {e}")
    return df

def process_compras(df):
    """Função para processar dados de compras"""
    if not df.empty:
        for col in ['Pão', 'Frios', 'Bebidas']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        if 'Data' in df.columns:
            try:
                df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['MêsNome'] = df['Data'].dt.strftime('%B')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
            except Exception as e:
                st.error(f"Erro ao processar a coluna 'Data': {e}")
    return df

def main():
    st.title("📊 Sistema de Registro do Clips Burger")
    
    try:
        st.image("logo.png", width=200)
    except:
        st.warning("Logo não encontrado. Verifique se o arquivo 'logo.png' está no diretório do aplicativo.")
    
    # Sidebar para filtros comuns
    st.sidebar.title("🔍 Filtros")

    # Abas principais do sistema
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Registro", "📊 Análise de Vendas", "🛒 Análise de Compras", "📈 Estatísticas"])

    with tab1:
        st.header("Registro de Dados")
        
        # Registro de Vendas
        st.subheader("Registro de Vendas")
        with st.form("form_vendas"):
            data_venda = st.date_input("Data da Venda", value=datetime.today())
            col1, col2, col3 = st.columns(3)
            with col1:
                cartao = st.number_input("Cartão (R$)", min_value=0.0, step=0.01)
            with col2:
                dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, step=0.01)
            with col3:
                pix = st.number_input("PIX (R$)", min_value=0.0, step=0.01)
            total = cartao + dinheiro + pix
            st.write(f"**Total: R${total:.2f}**")
            enviar_venda = st.form_submit_button("Registrar Venda")
            if enviar_venda:
                if total > 0:
                    if append_row("Vendas", [data_venda.strftime('%d/%m/%Y'), cartao, dinheiro, pix]):
                        st.success("Venda registrada com sucesso!")
                else:
                    st.warning("O valor total precisa ser maior que zero.")

        # Registro de Compras
        st.subheader("Registro de Compras")
        with st.form("form_compras"):
            data_compra = st.date_input("Data da Compra", value=datetime.today())
            col1, col2, col3 = st.columns(3)
            with col1:
                pao = st.number_input("Pão (R$)", min_value=0.0, step=0.01)
            with col2:
                frios = st.number_input("Frios (R$)", min_value=0.0, step=0.01)
            with col3:
                bebidas = st.number_input("Bebidas (R$)", min_value=0.0, step=0.01)
            total_compra = pao + frios + bebidas
            st.write(f"**Total da compra: R${total_compra:.2f}**")
            enviar_compra = st.form_submit_button("Registrar Compra")
            if enviar_compra:
                if total_compra > 0:
                    if append_row("Compras", [data_compra.strftime('%d/%m/%Y'), pao, frios, bebidas]):
                        st.success("Compra registrada com sucesso!")
                else:
                    st.warning("O valor total precisa ser maior que zero.")

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
        df_compras, _ = read_google_sheet("Compras")
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
