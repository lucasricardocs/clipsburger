import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import os
import io
import tempfile
from PIL import Image as PILImage, ImageDraw, ImageFont
import base64
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

# Configuração da página
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="wide")

# Estilo CSS personalizado
st.markdown("""
<style>
    .stMultiSelect [data-baseweb=tag] {
        background-color: #4CAF50;
        color: white;
    }
    .stRadio > div {
        flex-direction: row;
        gap: 1rem;
    }
    .stRadio label {
        margin-right: 15px;
    }
    .st-bb {
        background-color: transparent;
    }
    .st-at {
        background-color: #f0f2f6;
    }
</style>
""", unsafe_allow_html=True)

# Configurando estilo dos gráficos matplotlib
plt.style.use('ggplot')
mpl.rcParams.update({
    'font.size': 14,
    'figure.figsize': (12, 9),
    'figure.facecolor': 'white',
    'axes.facecolor': '#f0f0f0',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'axes.labelsize': 16,
    'axes.titlesize': 20,
    'xtick.labelsize': 14,
    'ytick.labelsize': 14
})

@st.cache_data(ttl=3600)
def read_google_sheet():
    """Função para ler os dados da planilha Google Sheets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 
                 'https://www.googleapis.com/auth/drive']
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
    if not all(isinstance(val, (int, float)) for val in [cartao, dinheiro, pix]:
        st.error("Valores devem ser numéricos")
        return
    if cartao < 0 or dinheiro < 0 or pix < 0:
        st.error("Valores não podem ser negativos")
        return
    
    if worksheet is None:
        st.error("Não foi possível acessar a planilha.")
        return
    try:
        new_row = [date, float(cartao), float(dinheiro), float(pix)]
        worksheet.append_row(new_row)
        st.success("Dados registrados com sucesso!")
        st.balloons()
    except Exception as e:
        st.error(f"Erro ao adicionar dados: {e}")

def process_data(df):
    """Função para processar e preparar os dados"""
    if not df.empty:
        # Converter valores para numérico
        for col in ['Cartão', 'Dinheiro', 'Pix']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Calcular total
        df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']
        
        # Processar datas
        if 'Data' in df.columns:
            try:
                # Tentar múltiplos formatos de data
                date_formats = ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y']
                for fmt in date_formats:
                    try:
                        df['Data'] = pd.to_datetime(df['Data'], format=fmt, errors='raise')
                        break
                    except ValueError:
                        continue
                
                # Criar colunas temporais
                df['Ano'] = df['Data'].dt.year
                df['Mês'] = df['Data'].dt.month
                df['MêsNome'] = df['Data'].dt.strftime('%B')
                df['DiaSemana'] = df['Data'].dt.day_name()
                df['DiaSemana'] = pd.Categorical(df['DiaSemana'], 
                                                categories=['Monday','Tuesday','Wednesday','Thursday',
                                                            'Friday','Saturday','Sunday'],
                                                ordered=True)
                df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
                df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
                
            except Exception as e:
                st.error(f"Erro ao processar datas: {e}")
    return df

def main():
    st.title("📊 Sistema de Registro de Vendas")
    tab1, tab2, tab3 = st.tabs(["Registrar Venda", "Visualização Rápida", "Análise Detalhada"])

    with tab1:
        st.header("Registrar Nova Venda")
        with st.form("venda_form", clear_on_submit=True):
            data = st.date_input("Data", datetime.now())
            col1, col2, col3 = st.columns(3)
            with col1:
                cartao = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f")
            with col2:
                dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f")
            with col3:
                pix = st.number_input("PIX (R$)", min_value=0.0, format="%.2f")
            
            total = cartao + dinheiro + pix
            st.markdown(f"""
                <div style="background-color:#f0f2f6;padding:15px;border-radius:10px">
                    <h3 style="color:#2e86c1;text-align:center">Total da Venda: R$ {total:,.2f}</h3>
                </div>
            """, unsafe_allow_html=True)
            
            submitted = st.form_submit_button("📤 Registrar Venda")
            if submitted:
                if cartao > 0 or dinheiro > 0 or pix > 0:
                    formatted_date = data.strftime('%d/%m/%Y')
                    _, worksheet = read_google_sheet()
                    if worksheet:
                        add_data_to_sheet(formatted_date, cartao, dinheiro, pix, worksheet)
                else:
                    st.warning("⚠️ Pelo menos um valor de venda deve ser maior que zero.")

    with tab2:
        st.header("Visão Geral das Vendas")
        df_raw, _ = read_google_sheet()
        if not df_raw.empty:
            df = process_data(df_raw.copy())
            
            # Cartões de métricas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Vendido", f"R$ {df['Total'].sum():,.2f}")
            with col2:
                st.metric("Média Diária", f"R$ {df['Total'].mean():,.2f}")
            with col3:
                st.metric("Dias Registrados", len(df))
            with col4:
                st.metric("Melhor Dia", f"R$ {df['Total'].max():,.2f}")
            
            # Gráfico de linhas simples
            st.altair_chart(alt.Chart(df).mark_line(point=True).encode(
                x='DataFormatada:T',
                y='Total:Q',
                tooltip=['DataFormatada', 'Total']
            ).properties(width=800, height=400), use_container_width=True)
        else:
            st.info("Nenhum dado disponível para visualização.")

    with tab3:
        st.header("Análise Detalhada de Vendas")
        with st.spinner("Carregando dados..."):
            df_raw, _ = read_google_sheet()
            if not df_raw.empty:
                df = process_data(df_raw.copy())
                
                if 'Data' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Data']):
                    # Filtros
                    col1, col2 = st.columns(2)
                    with col1:
                        anos = sorted(df['Ano'].unique())
                        selected_anos = st.multiselect("Selecione o(s) Ano(s):", 
                                                      options=anos, 
                                                      default=anos)
                    with col2:
                        meses_opcoes = [f"{m} - {datetime(2020, m, 1).strftime('%B')}" 
                                       for m in sorted(df['Mês'].unique())]
                        selected_meses_str = st.multiselect("Selecione o(s) Mês(es):", 
                                                           options=meses_opcoes, 
                                                           default=meses_opcoes)
                        selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]
                    
                    df_filtered = df[df['Ano'].isin(selected_anos) & df['Mês'].isin(selected_meses)]
                    
                    # Seção de Heatmap
                    st.subheader("🔍 Padrões de Vendas por Dia da Semana")
                    metric = st.radio("Métrica para análise:", 
                                     ['Total', 'Cartão', 'Dinheiro', 'Pix'],
                                     horizontal=True,
                                     key='heatmap_metric')
                    
                    heat_data = df_filtered.groupby(['DataFormatada', 'DiaSemana', 'MêsNome']).agg({
                        'Cartão': 'sum',
                        'Dinheiro': 'sum',
                        'Pix': 'sum',
                        'Total': 'sum'
                    }).reset_index()
                    
                    heatmap = alt.Chart(heat_data).mark_rect().encode(
                        x=alt.X('DataFormatada:T', title='Data', axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y('DiaSemana:O', title='Dia da Semana'),
                        color=alt.Color(f'{metric}:Q', 
                                       legend=alt.Legend(title="Valor (R$)"),
                                       scale=alt.Scale(scheme='goldred')),
                        tooltip=[
                            'DataFormatada',
                            'DiaSemana',
                            alt.Tooltip('Cartão:Q', format='R$,.2f'),
                            alt.Tooltip('Dinheiro:Q', format='R$,.2f'),
                            alt.Tooltip('Pix:Q', format='R$,.2f'),
                            alt.Tooltip('Total:Q', format='R$,.2f')
                        ]
                    ).properties(
                        width=800,
                        height=400
                    ).interactive()
                    
                    st.altair_chart(heatmap, use_container_width=True)
                    
                    # Seção de Área Empilhada
                    st.subheader("📈 Evolução dos Métodos de Pagamento")
                    methods = st.multiselect(
                        "Selecione os métodos para análise:",
                        ['Cartão', 'Dinheiro', 'Pix'],
                        default=['Cartão', 'Dinheiro', 'Pix'],
                        key='area_methods'
                    )
                    
                    area_data = df_filtered.melt(
                        id_vars=['Data', 'DataFormatada'], 
                        value_vars=methods,
                        var_name='Método', 
                        value_name='Valor'
                    )
                    
                    area = alt.Chart(area_data).mark_area(
                        line={'color':'white', 'size':0.5},
                        opacity=0.8
                    ).encode(
                        x=alt.X('DataFormatada:T', title='Data', axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y('sum(Valor):Q', title='Valor Acumulado (R$)'),
                        color=alt.Color('Método:N', 
                                      scale=alt.Scale(scheme='category20'),
                                      legend=alt.Legend(
                                          orient='bottom',
                                          titleFontSize=14,
                                          labelFontSize=12
                                      )),
                        order=alt.Order('Método:N', sort='ascending'),
                        tooltip=[
                            'DataFormatada',
                            'Método',
                            alt.Tooltip('sum(Valor):Q', format='R$,.2f')
                        ]
                    ).properties(
                        width=800,
                        height=500
                    ).interactive()
                    
                    st.altair_chart(area, use_container_width=True)
                    
                    # Gráficos existentes (pizza, barras, linha) mantidos aqui...
                    # ... (código dos outros gráficos existentes)
                    
                    # Botão para gerar PDF
                    if st.button("📄 Exportar Análise para PDF", use_container_width=True):
                        with st.spinner("Gerando relatório PDF..."):
                            pdf_bytes = generate_pdf_report(df_filtered)
                            if pdf_bytes:
                                st.success("Relatório gerado com sucesso!")
                                st.download_button(
                                    label="⬇️ Baixar PDF",
                                    data=pdf_bytes,
                                    file_name=f"relatorio_vendas_{datetime.now().strftime('%Y%m%d')}.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                else:
                    st.warning("Dados de data não encontrados ou em formato inválido.")
            else:
                st.info("Nenhum dado disponível para análise.")

if __name__ == "__main__":
    main()