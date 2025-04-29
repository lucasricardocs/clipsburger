import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração de tema customizado
def set_custom_style():
    st.markdown("""
        <style>
            .stDataFrame {border: 1px solid #e0e0e0; border-radius: 8px;}
            .st-bb {background-color: #f8f9fa;}
            .st-at {background-color: #ffffff;}
            div[data-testid="stHorizontalBlock"] {gap: 1rem;}
            header {box-shadow: 0 2px 6px rgba(0,0,0,0.1);}
            .stPlotlyChart {border-radius: 8px; overflow: hidden;}
            .css-1q8dd3e {padding: 1.5rem 1rem;}
        </style>
    """, unsafe_allow_html=True)

# Configuração da página
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="wide")
set_custom_style()

# [...] (As funções read_google_sheet, add_data_to_sheet e process_data permanecem iguais)

def main():
    st.title("📈 Painel de Gestão Comercial")
    
    tab1, tab3 = st.tabs(["📤 Registrar Venda", "📊 Análise Avançada"])

    with tab1:
        # [...] (O formulário de registro permanece igual)

    with tab3:
        # Filtros na sidebar
        with st.sidebar:
            st.header("⚙️ Configurações de Análise")
            df_raw, _ = read_google_sheet()
            df = process_data(df_raw.copy()) if not df_raw.empty else pd.DataFrame()

            if not df.empty and 'Data' in df.columns:
                # Filtro de Período
                min_date = df['Data'].min().date()
                max_date = df['Data'].max().date()
                selected_dates = st.date_input(
                    "Selecione o período:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )

                # Filtro de Agrupamento
                group_by = st.selectbox(
                    "Agrupar dados por:",
                    options=["Dia", "Semana", "Mês"],
                    index=0
                )

        # Conteúdo principal
        if not df_raw.empty:
            df_filtered = df[(df['Data'].dt.date >= selected_dates[0]) & 
                            (df['Data'].dt.date <= selected_dates[1])] if len(selected_dates) == 2 else df

            # Agrupamento de dados
            if group_by == "Semana":
                df_grouped = df_filtered.groupby(pd.Grouper(key='Data', freq='W-MON'))[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
                df_grouped['DataFormatada'] = df_grouped['Data'].dt.strftime('Semana %W/%Y')
            elif group_by == "Mês":
                df_grouped = df_filtered.groupby(pd.Grouper(key='Data', freq='M'))[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
                df_grouped['DataFormatada'] = df_grouped['Data'].dt.strftime('%b/%Y')
            else:
                df_grouped = df_filtered.copy()
                df_grouped['DataFormatada'] = df_grouped['Data'].dt.strftime('%d/%m/%Y')

            # Layout de métricas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total em Cartão", f"R$ {df_grouped['Cartão'].sum():,.2f}")
            with col2:
                st.metric("Total em Dinheiro", f"R$ {df_grouped['Dinheiro'].sum():,.2f}")
            with col3:
                st.metric("Total PIX", f"R$ {df_grouped['Pix'].sum():,.2f}")
            with col4:
                st.metric("Total Geral", f"R$ {df_grouped[['Cartão', 'Dinheiro', 'Pix']].sum().sum():,.2f}")

            # Gráfico de Evolução Temporal
            st.subheader("Evolução Temporal das Vendas")
            line_chart = alt.Chart(df_grouped).transform_fold(
                ['Cartão', 'Dinheiro', 'Pix'],
                as_=['Método', 'Valor']
            ).mark_line(point=True, strokeWidth=2).encode(
                x=alt.X('Data:T', axis=alt.Axis(title='Data', format='%d/%m/%Y', labelAngle=-45)),
                y=alt.Y('Valor:Q', axis=alt.Axis(title='Valor (R$)', format='$,.0f')),
                color=alt.Color('Método:N', scale=alt.Scale(range=['#3A86FF', '#FFBE0B', '#FF006E'])),
                tooltip=['DataFormatada:N', 'Método:N', 'Valor:Q']
            ).properties(
                height=400
            ).configure_axis(
                gridColor='#f0f0f0',
                labelFontSize=12,
                titleFontSize=14
            ).configure_point(
                size=60
            )
            st.altair_chart(line_chart, use_container_width=True)

            # Gráfico de Comparação de Métodos
            st.subheader("Distribuição por Método de Pagamento")
            col5, col6 = st.columns([2,1])
            
            with col5:
                bar_chart = alt.Chart(df_grouped).transform_fold(
                    ['Cartão', 'Dinheiro', 'Pix'],
                    as_=['Método', 'Valor']
                ).mark_bar().encode(
                    x=alt.X('sum(Valor):Q', title='Valor Total (R$)', axis=alt.Axis(format='$,.0f')),
                    y=alt.Y('Método:N', title='Método de Pagamento', sort='-x'),
                    color=alt.Color('Método:N', scale=alt.Scale(range=['#3A86FF', '#FFBE0B', '#FF006E'])),
                    tooltip=[alt.Tooltip('sum(Valor):Q', format='$,.0f')]
                ).properties(
                    height=300
                )
                st.altair_chart(bar_chart, use_container_width=True)

            with col6:
                total = df_grouped[['Cartão', 'Dinheiro', 'Pix']].sum().sum()
                pie_data = pd.DataFrame({
                    'Método': ['Cartão', 'Dinheiro', 'PIX'],
                    'Percentual': [
                        df_grouped['Cartão'].sum()/total,
                        df_grouped['Dinheiro'].sum()/total,
                        df_grouped['Pix'].sum()/total
                    ]
                })
                
                pie_chart = alt.Chart(pie_data).mark_arc(innerRadius=80).encode(
                    theta='Percentual:Q',
                    color=alt.Color('Método:N', scale=alt.Scale(range=['#3A86FF', '#FFBE0B', '#FF006E'])),
                    tooltip=['Método:N', alt.Tooltip('Percentual:Q', format='.1%')]
                ).properties(
                    height=300
                )
                st.altair_chart(pie_chart, use_container_width=True)

            # Tabela Detalhada
            st.subheader("Detalhamento por Período")
            st.dataframe(
                df_grouped.sort_values('Data', ascending=False)[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix']],
                column_config={
                    "DataFormatada": "Período",
                    "Cartão": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Dinheiro": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Pix": st.column_config.NumberColumn(format="R$ %.2f")
                },
                use_container_width=True,
                height=400
            )

        else:
            st.info("Nenhum dado disponível para análise")

if __name__ == "__main__":
    main()
