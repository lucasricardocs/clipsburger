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
import altair_saver

# Configuração da página
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="centered")

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
    """Função para processar e preparar os dados com tratamento robusto"""
    if df.empty:
        return df
    
    required_columns = ['Data', 'Cartão', 'Dinheiro', 'Pix']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        st.warning(f"Colunas essenciais faltando: {', '.join(missing_cols)}")
        return pd.DataFrame()
    
    try:
        for col in ['Cartão', 'Dinheiro', 'Pix']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df['Total'] = df['Cartão'] + df['Dinheiro'] + df['Pix']
        
        try:
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            
            if df['Data'].isnull().any():
                df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
            
            df['Ano'] = df['Data'].dt.year
            df['Mês'] = df['Data'].dt.month
            df['MêsNome'] = df['Data'].dt.strftime('%B')
            df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
            df['DataFormatada'] = df['Data'].dt.strftime('%d/%m/%Y')
            
            df = df.dropna(subset=['Data'])
        except Exception as e:
            st.error(f"Erro ao processar datas: {str(e)}")
            return pd.DataFrame()
        
        return df
    
    except Exception as e:
        st.error(f"Erro inesperado ao processar dados: {str(e)}")
        return pd.DataFrame()

def generate_sales_stats(df):
    """Gera um dicionário com diversas estatísticas de vendas"""
    if df.empty:
        return {}
    
    stats = {}
    stats['total_days'] = len(df['Data'].unique())
    stats['start_date'] = df['Data'].min().strftime('%d/%m/%Y')
    stats['end_date'] = df['Data'].max().strftime('%d/%m/%Y')
    
    stats['total_cartao'] = df['Cartão'].sum()
    stats['total_dinheiro'] = df['Dinheiro'].sum()
    stats['total_pix'] = df['Pix'].sum()
    stats['total_geral'] = stats['total_cartao'] + stats['total_dinheiro'] + stats['total_pix']
    
    stats['media_diaria'] = stats['total_geral'] / stats['total_days'] if stats['total_days'] > 0 else 0
    stats['media_cartao'] = stats['total_cartao'] / stats['total_days'] if stats['total_days'] > 0 else 0
    stats['media_dinheiro'] = stats['total_dinheiro'] / stats['total_days'] if stats['total_days'] > 0 else 0
    stats['media_pix'] = stats['total_pix'] / stats['total_days'] if stats['total_days'] > 0 else 0
    
    stats['perc_cartao'] = (stats['total_cartao'] / stats['total_geral']) * 100 if stats['total_geral'] > 0 else 0
    stats['perc_dinheiro'] = (stats['total_dinheiro'] / stats['total_geral']) * 100 if stats['total_geral'] > 0 else 0
    stats['perc_pix'] = (stats['total_pix'] / stats['total_geral']) * 100 if stats['total_geral'] > 0 else 0
    
    max_day = df.loc[df['Total'].idxmax()] if not df.empty else None
    min_day = df.loc[df['Total'].idxmin()] if not df.empty else None
    
    stats['best_day'] = {
        'date': max_day['Data'].strftime('%d/%m/%Y') if max_day is not None else 'N/A',
        'total': max_day['Total'] if max_day is not None else 0,
        'method': max_day[['Cartão', 'Dinheiro', 'Pix']].idxmax() if max_day is not None else 'N/A'
    }
    
    stats['worst_day'] = {
        'date': min_day['Data'].strftime('%d/%m/%Y') if min_day is not None else 'N/A',
        'total': min_day['Total'] if min_day is not None else 0,
        'method': min_day[['Cartão', 'Dinheiro', 'Pix']].idxmax() if min_day is not None else 'N/A'
    }
    
    last_7_days = df.sort_values('Data', ascending=False).head(7)
    if len(last_7_days) >= 7:
        stats['last_7_avg'] = last_7_days['Total'].mean()
        stats['trend'] = "↑ Crescente" if stats['last_7_avg'] > stats['media_diaria'] else \
                         "↓ Decrescente" if stats['last_7_avg'] < stats['media_diaria'] else \
                         "→ Estável"
        stats['trend_perc'] = abs((stats['last_7_avg'] - stats['media_diaria']) / stats['media_diaria'] * 100) if stats['media_diaria'] > 0 else 0
    else:
        stats['trend'] = "Dados insuficientes"
        stats['trend_perc'] = 0
    
    days_remaining = 30 - stats['total_days'] if stats['total_days'] < 30 else 0
    stats['projection'] = stats['total_geral'] + (stats['media_diaria'] * days_remaining) if days_remaining > 0 else stats['total_geral']
    
    stats['preferred_method'] = pd.Series({
        'Cartão': stats['perc_cartao'],
        'Dinheiro': stats['perc_dinheiro'],
        'Pix': stats['perc_pix']
    }).idxmax()
    
    return stats

def create_pie_chart_altair(df_filtered):
    """Cria gráfico de pizza usando Altair"""
    data = pd.DataFrame({
        'Método': ['Cartão', 'Dinheiro', 'PIX'],
        'Valor': [df_filtered['Cartão'].sum(), df_filtered['Dinheiro'].sum(), df_filtered['Pix'].sum()]
    })
    
    pie = alt.Chart(data).mark_arc(outerRadius=150).encode(
        theta=alt.Theta('Valor:Q', stack=True),
        color=alt.Color('Método:N', scale=alt.Scale(range=['#3498db', '#f39c12', '#2ecc71']),
        tooltip=['Método', 'Valor']
    ).properties(
        title='Distribuição por Método de Pagamento',
        width=500,
        height=400
    )
    
    text = pie.mark_text(radius=180, size=14, color='black', fontWeight='bold').encode(
        text=alt.Text('Valor:Q', format='.1f')
    )
    
    return (pie + text).configure_view(
        strokeWidth=0
    ).configure_title(
        fontSize=20,
        anchor='middle'
    )

def create_bar_chart_altair(df_filtered):
    """Cria gráfico de barras usando Altair"""
    date_column = 'DataFormatada' if 'DataFormatada' in df_filtered.columns else 'Data'
    daily = df_filtered.groupby(date_column)[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
    daily_long = daily.melt(id_vars=[date_column], var_name='Método', value_name='Valor')
    
    bar_chart = alt.Chart(daily_long).mark_bar(size=20).encode(
        x=alt.X(f'{date_column}:N', title='Data', axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Valor:Q', title='Valor (R$)'),
        color=alt.Color('Método:N', scale=alt.Scale(range=['#3498db', '#f39c12', '#2ecc71'])),
        tooltip=[date_column, 'Método', 'Valor']
    ).properties(
        title='Vendas Diárias por Método de Pagamento',
        width=600,
        height=400
    ).facet(
        column='Método:N'
    ).resolve_scale(
        y='independent'
    ).configure_view(
        stroke='transparent'
    ).configure_title(
        fontSize=20,
        anchor='middle'
    )
    
    return bar_chart

def create_line_chart_altair(df_filtered):
    """Cria gráfico de linha usando Altair"""
    df_acum = df_filtered.sort_values('Data').copy()
    df_acum['Total Acumulado'] = df_acum['Total'].cumsum()
    
    line = alt.Chart(df_acum).mark_line(point=True, size=3).encode(
        x=alt.X('DataFormatada:N', title='Data', axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
        tooltip=['DataFormatada', 'Total Acumulado']
    ).properties(
        title='Acúmulo de Capital ao Longo do Tempo',
        width=600,
        height=400
    ).configure_title(
        fontSize=20,
        anchor='middle'
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    )
    
    points = line.mark_point(
        filled=True,
        size=100,
        color='#3498db'
    ).encode(
        color=alt.value('#2980b9'),
        stroke=alt.value('white'),
        strokeWidth=alt.value(2)
    )
    
    return line + points

def generate_pdf_report(df_filtered):
    """Função para gerar o relatório em PDF com gráficos Altair"""
    try:
        stats = generate_sales_stats(df_filtered)
        temp_dir = tempfile.mkdtemp()
        
        # Gerar gráficos Altair e salvar como PNG
        pie_chart = create_pie_chart_altair(df_filtered)
        bar_chart = create_bar_chart_altair(df_filtered)
        line_chart = create_line_chart_altair(df_filtered)
        
        pie_chart_path = os.path.join(temp_dir, "pie_chart.png")
        bar_chart_path = os.path.join(temp_dir, "bar_chart.png")
        line_chart_path = os.path.join(temp_dir, "line_chart.png")
        
        # Salvar gráficos Altair como PNG
        pie_chart.save(pie_chart_path, scale_factor=2.0)
        bar_chart.save(bar_chart_path, scale_factor=2.0)
        line_chart.save(line_chart_path, scale_factor=2.0)
        
        # Criar o PDF
        pdf_path = os.path.join(temp_dir, "analise_vendas.pdf")
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        elements = []
        
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
        
        stats_style = ParagraphStyle(
            'StatsStyle',
            parent=styles['Normal'],
            fontSize=12,
            leading=18,
            spaceAfter=12
        )
        
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph("Análise Detalhada de Vendas", title_style))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y')}", styles['Italic']))
        elements.append(PageBreak())
        
        elements.append(Paragraph("Resumo Estatístico", subtitle_style))
        elements.append(Spacer(1, 0.5*inch))
        
        stats_data = [
            ["Período Analisado", f"{stats['start_date']} a {stats['end_date']} ({stats['total_days']} dias)"],
            ["Total Geral de Vendas", f"R$ {stats['total_geral']:,.2f}"],
            ["Média Diária", f"R$ {stats['media_diaria']:,.2f}"],
            ["Tendência Atual", f"{stats['trend']} ({stats['trend_perc']:.1f}% vs média)"],
            ["Previsão Mensal", f"R$ {stats['projection']:,.2f}"],
            ["Método Preferido", f"{stats['preferred_method']} ({max(stats['perc_cartao'], stats['perc_dinheiro'], stats['perc_pix']):.1f}%)"],
            ["Melhor Dia", f"{stats['best_day']['date']} - R$ {stats['best_day']['total']:,.2f} ({stats['best_day']['method']})"],
            ["Pior Dia", f"{stats['worst_day']['date']} - R$ {stats['worst_day']['total']:,.2f} ({stats['worst_day']['method']})"]
        ]
        
        stats_table = Table(stats_data, colWidths=[doc.width/2.5, doc.width/1.5])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 0.5*inch))
        
        elements.append(Paragraph("Detalhes por Método de Pagamento", styles['Heading2']))
        elements.append(Spacer(1, 0.25*inch))
        
        payment_data = [
            ["Método", "Total", "Média Diária", "Participação"],
            ["Cartão", f"R$ {stats['total_cartao']:,.2f}", f"R$ {stats['media_cartao']:,.2f}", f"{stats['perc_cartao']:.1f}%"],
            ["Dinheiro", f"R$ {stats['total_dinheiro']:,.2f}", f"R$ {stats['media_dinheiro']:,.2f}", f"{stats['perc_dinheiro']:.1f}%"],
            ["PIX", f"R$ {stats['total_pix']:,.2f}", f"R$ {stats['media_pix']:,.2f}", f"{stats['perc_pix']:.1f}%"],
            ["TOTAL", f"R$ {stats['total_geral']:,.2f}", f"R$ {stats['media_diaria']:,.2f}", "100%"]
        ]
        
        payment_table = Table(payment_data)
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        elements.append(payment_table)
        elements.append(PageBreak())
        
        if os.path.exists(pie_chart_path):
            elements.append(Paragraph("Distribuição por Método de Pagamento", subtitle_style))
            elements.append(Spacer(1, 0.5*inch))
            img = Image(pie_chart_path)
            img.drawHeight = 6*inch
            img.drawWidth = 6*inch
            elements.append(img)
            elements.append(PageBreak())
        
        if os.path.exists(bar_chart_path):
            elements.append(Paragraph("Vendas Diárias por Método de Pagamento", subtitle_style))
            elements.append(Spacer(1, 0.5*inch))
            img = Image(bar_chart_path)
            img.drawHeight = 6*inch
            img.drawWidth = 8*inch
            elements.append(img)
            elements.append(PageBreak())
        
        if os.path.exists(line_chart_path):
            elements.append(Paragraph("Acúmulo de Capital ao Longo do Tempo", subtitle_style))
            elements.append(Spacer(1, 0.5*inch))
            img = Image(line_chart_path)
            img.drawHeight = 6*inch
            img.drawWidth = 8*inch
            elements.append(img)
        
        doc.build(elements)
        
        with open(pdf_path, "rb") as pdf_file:
            PDFbyte = pdf_file.read()
        
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
    
    if 'google_credentials' not in st.secrets:
        st.error("Credenciais não configuradas. Verifique as configurações do aplicativo.")
        return
    
    tab1, tab3 = st.tabs(["Registrar Venda", "Análise Detalhada"])

    with tab1:
        st.header("Registrar Nova Venda")
        with st.form("venda_form"):
            data = st.date_input("Data", datetime.now())
            col1, col2, col3 = st.columns(3)
            with col1:
                cartao = st.number_input("Cartão (R$)", min_value=0.0, format="%.2f", step=0.01)
            with col2:
                dinheiro = st.number_input("Dinheiro (R$)", min_value=0.0, format="%.2f", step=0.01)
            with col3:
                pix = st.number_input("PIX (R$)", min_value=0.0, format="%.2f", step=0.01)
            
            total = cartao + dinheiro + pix
            st.markdown(f"**Total da venda: R$ {total:.2f}**")
            
            submitted = st.form_submit_button("Registrar Venda")
            if submitted:
                if total <= 0:
                    st.warning("O valor total da venda deve ser maior que zero.")
                else:
                    with st.spinner("Salvando dados..."):
                        try:
                            formatted_date = data.strftime('%d/%m/%Y')
                            _, worksheet = read_google_sheet()
                            if worksheet:
                                add_data_to_sheet(formatted_date, cartao, dinheiro, pix, worksheet)
                                st.success("Venda registrada com sucesso!")
                                st.balloons()
                            else:
                                st.error("Não foi possível acessar a planilha.")
                        except Exception as e:
                            st.error(f"Erro ao registrar venda: {str(e)}")

    with tab3:
        st.header("Análise Detalhada de Vendas")
        with st.spinner("Carregando dados..."):
            df_raw, _ = read_google_sheet()
            df = process_data(df_raw.copy())
            
            if not df.empty:
                anos = sorted(df['Ano'].unique())
                selected_anos = st.multiselect("Selecione o(s) Ano(s):", options=anos, default=anos)
                df_filtered = df[df['Ano'].isin(selected_anos)]

                meses_disponiveis = sorted(df_filtered['Mês'].unique())
                meses_nomes = {m: datetime(2020, m, 1).strftime('%B') for m in meses_disponiveis}
                meses_opcoes = [f"{m} - {meses_nomes[m]}" for m in meses_disponiveis]
                selected_meses_str = st.multiselect("Selecione o(s) Mês(es):", options=meses_opcoes, default=meses_opcoes)
                selected_meses = [int(m.split(" - ")[0]) for m in selected_meses_str]
                df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)]

                st.subheader("📈 Painel de Estatísticas")
                stats = generate_sales_stats(df_filtered)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Geral", f"R$ {stats['total_geral']:,.2f}")
                    st.metric("Média Diária", f"R$ {stats['media_diaria']:,.2f}")
                    
                with col2:
                    st.metric("Melhor Dia", 
                             f"R$ {stats['best_day']['total']:,.2f}", 
                             stats['best_day']['date'])
                    st.metric("Pior Dia", 
                             f"R$ {stats['worst_day']['total']:,.2f}", 
                             stats['worst_day']['date'])
                    
                with col3:
                    st.metric("Tendência Atual", 
                             stats['trend'], 
                             f"{stats['trend_perc']:.1f}% vs média")
                    st.metric("Método Preferido", 
                             stats['preferred_method'], 
                             f"{max(stats['perc_cartao'], stats['perc_dinheiro'], stats['perc_pix']):.1f}%")
                
                st.subheader("💳 Distribuição por Método de Pagamento")
                pie_chart = create_pie_chart_altair(df_filtered)
                st.altair_chart(pie_chart, use_container_width=True)
                
                st.subheader("Vendas Diárias por Método de Pagamento")
                bar_chart = create_bar_chart_altair(df_filtered)
                st.altair_chart(bar_chart, use_container_width=True)
                
                st.subheader("Acúmulo de Capital ao Longo do Tempo")
                line_chart = create_line_chart_altair(df_filtered)
                st.altair_chart(line_chart, use_container_width=True)
                
                st.subheader("Dados Filtrados")
                st.dataframe(df_filtered[['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']]
                             if 'DataFormatada' in df_filtered.columns else df_filtered, use_container_width=True)

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
                st.info("Não há dados disponíveis para análise.")

if __name__ == "__main__":
    main()