import streamlit as st
import gspread
import pandas as pd
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
import base64
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    """Cria gráfico de pizza usando Plotly"""
    valores = [df_filtered['Cartão'].sum(), df_filtered['Dinheiro'].sum(), df_filtered['Pix'].sum()]
    labels = ['Cartão', 'Dinheiro', 'PIX']
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=valores,
        hole=0.3,
        marker_colors=['#3498db', '#f39c12', '#2ecc71'],
        textinfo='percent+value',
        texttemplate='%{label}<br>R$ %{value:,.2f}<br>(%{percent})',
        hoverinfo='label+percent+value',
        textfont_size=14
    )])
    
    fig.update_layout(
        title='Distribuição por Método de Pagamento',
        title_font_size=20,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        height=500,
        margin=dict(l=50, r=50, b=100, t=100, pad=4)
    )
    
    return fig

def create_bar_chart(df_filtered):
    """Cria gráfico de barras usando Plotly"""
    date_column = 'DataFormatada' if 'DataFormatada' in df_filtered.columns else 'Data'
    daily = df_filtered.groupby(date_column)[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=daily[date_column],
        y=daily['Cartão'],
        name='Cartão',
        marker_color='#3498db',
        text=daily['Cartão'].round(2),
        textposition='auto'
    ))
    
    fig.add_trace(go.Bar(
        x=daily[date_column],
        y=daily['Dinheiro'],
        name='Dinheiro',
        marker_color='#f39c12',
        text=daily['Dinheiro'].round(2),
        textposition='auto'
    ))
    
    fig.add_trace(go.Bar(
        x=daily[date_column],
        y=daily['Pix'],
        name='PIX',
        marker_color='#2ecc71',
        text=daily['Pix'].round(2),
        textposition='auto'
    ))
    
    fig.update_layout(
        barmode='group',
        title='Vendas Diárias por Método de Pagamento',
        xaxis_title='Data',
        yaxis_title='Valor (R$)',
        legend_title='Método de Pagamento',
        hovermode="x unified",
        height=500,
        margin=dict(l=50, r=50, b=100, t=100, pad=4)
    )
    
    fig.update_xaxes(tickangle=45)
    
    return fig

def create_line_chart(df_filtered):
    """Cria gráfico de linha usando Plotly"""
    df_acum = df_filtered.sort_values('Data').copy()
    df_acum['Total Acumulado'] = df_acum['Total'].cumsum()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_acum['DataFormatada'],
        y=df_acum['Total Acumulado'],
        mode='lines+markers+text',
        line=dict(width=4, color='#3498db'),
        marker=dict(size=10, color='#2980b9'),
        text=df_acum['Total Acumulado'].round(2),
        textposition="top center",
        name='Total Acumulado',
        fill='tozeroy',
        fillcolor='rgba(52, 152, 219, 0.2)'
    ))
    
    fig.update_layout(
        title='Acúmulo de Capital ao Longo do Tempo',
        xaxis_title='Data',
        yaxis_title='Capital Acumulado (R$)',
        height=500,
        margin=dict(l=50, r=50, b=100, t=100, pad=4),
        hovermode="x unified"
    )
    
    fig.update_xaxes(tickangle=45)
    
    return fig

def generate_pdf_report(df_filtered):
    """Função para gerar o relatório em PDF com gráficos Plotly"""
    try:
        # Criar diretório temporário para os gráficos
        temp_dir = tempfile.mkdtemp()
        
        # Gerar gráficos usando Plotly
        pie_chart = create_pie_chart(df_filtered)
        bar_chart = create_bar_chart(df_filtered)
        line_chart = create_line_chart(df_filtered)
        
        # Salvar gráficos como imagens
        pie_chart_path = os.path.join(temp_dir, "pie_chart.png")
        bar_chart_path = os.path.join(temp_dir, "bar_chart.png")
        line_chart_path = os.path.join(temp_dir, "line_chart.png")
        
        pie_chart.write_image(pie_chart_path, scale=2)
        bar_chart.write_image(bar_chart_path, scale=2)
        line_chart.write_image(line_chart_path, scale=2)
        
        # Criar o PDF
        pdf_path = os.path.join(temp_dir, "analise_vendas.pdf")
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        elements = []
        
        # Estilos personalizados
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            alignment=1,
            spaceAfter=30,
            textColor=colors.darkblue
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=20,
            alignment=1,
            spaceAfter=20,
            textColor=colors.darkblue
        )
        
        # Página de capa
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph("Análise Detalhada de Vendas", title_style))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y')}", styles['Italic']))
        elements.append(PageBreak())
        
        # Página com tabela de dados
        elements.append(Paragraph("Resumo dos Dados", subtitle_style))
        elements.append(Spacer(1, 0.5*inch))
        
        total_cartao = df_filtered['Cartão'].sum()
        total_dinheiro = df_filtered['Dinheiro'].sum()
        total_pix = df_filtered['Pix'].sum()
        total_geral = total_cartao + total_dinheiro + total_pix
        
        data = [
            ["Método de Pagamento", "Valor Total (R$)", "Percentual (%)"],
            ["Cartão", f"R$ {total_cartao:.2f}", f"{(total_cartao/total_geral*100):.1f}%"],
            ["Dinheiro", f"R$ {total_dinheiro:.2f}", f"{(total_dinheiro/total_geral*100):.1f}%"],
            ["PIX", f"R$ {total_pix:.2f}", f"{(total_pix/total_geral*100):.1f}%"],
            ["TOTAL", f"R$ {total_geral:.2f}", "100.0%"]
        ]
        
        table = Table(data, colWidths=[doc.width/3.0]*3)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 1*inch))
        
        # Informações gerais
        elements.append(Paragraph(f"Período da análise: {df_filtered['DataFormatada'].min()} a {df_filtered['DataFormatada'].max()}", styles['Normal']))
        elements.append(Paragraph(f"Total de dias analisados: {len(df_filtered['DataFormatada'].unique())}", styles['Normal']))
        elements.append(Paragraph(f"Média diária de vendas: R$ {(total_geral / len(df_filtered['DataFormatada'].unique())):.2f}", styles['Normal']))
        
        elements.append(PageBreak())
        
        # Página com gráfico de pizza
        if os.path.exists(pie_chart_path):
            elements.append(Paragraph("Distribuição por Método de Pagamento", subtitle_style))
            elements.append(Spacer(1, 0.5*inch))
            img = Image(pie_chart_path, width=6*inch, height=6*inch)
            elements.append(img)
            elements.append(PageBreak())
        
        # Página com gráfico de barras
        if os.path.exists(bar_chart_path):
            elements.append(Paragraph("Vendas Diárias por Método de Pagamento", subtitle_style))
            elements.append(Spacer(1, 0.5*inch))
            img = Image(bar_chart_path, width=8*inch, height=6*inch)
            elements.append(img)
            elements.append(PageBreak())
        
        # Página com gráfico de linha
        if os.path.exists(line_chart_path):
            elements.append(Paragraph("Acúmulo de Capital ao Longo do Tempo", subtitle_style))
            elements.append(Spacer(1, 0.5*inch))
            img = Image(line_chart_path, width=8*inch, height=6*inch)
            elements.append(img)
        
        # Construir o PDF
        doc.build(elements)
        
        # Ler o PDF gerado
        with open(pdf_path, "rb") as pdf_file:
            PDFbyte = pdf_file.read()
        
        # Limpar arquivos temporários
        for file_path in [pie_chart_path, bar_chart_path, line_chart_path, pdf_path]:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        try:
            os.rmdir(temp_dir)
        except:
            pass
        
        return PDFbyte
    
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None

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
                    fig_pie = create_pie_chart(df_filtered)
                    st.plotly_chart(fig_pie, use_container_width=True)

                    st.subheader("Vendas Diárias por Método de Pagamento")
                    fig_bar = create_bar_chart(df_filtered)
                    st.plotly_chart(fig_bar, use_container_width=True)

                    st.subheader("Acúmulo de Capital ao Longo do Tempo")
                    fig_line = create_line_chart(df_filtered)
                    st.plotly_chart(fig_line, use_container_width=True)

                    # Botão para gerar e baixar o PDF
                    if st.button("Exportar Análise para PDF"):
                        with st.spinner("Gerando PDF... Isso pode levar alguns segundos."):
                            try:
                                pdf_bytes = generate_pdf_report(df_filtered)
                                if pdf_bytes:
                                    st.success("PDF gerado com sucesso!")
                                    st.download_button(
                                        label="Baixar PDF",
                                        data=pdf_bytes,
                                        file_name="analise_vendas.pdf",
                                        mime="application/pdf"
                                    )
                                else:
                                    st.error("Não foi possível gerar o PDF. Verifique os logs para mais detalhes.")
                            except Exception as e:
                                st.error(f"Erro ao gerar ou baixar o PDF: {e}")
                                import traceback
                                st.error(traceback.format_exc())

                else:
                    st.info("Não há dados de data para análise.")
            else:
                st.info("Não há dados para exibir.")

if __name__ == "__main__":
    main()