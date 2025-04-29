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

# Configurando estilo dos gráficos matplotlib para serem mais atraentes
plt.style.use('ggplot')
mpl.rcParams['font.size'] = 14
mpl.rcParams['figure.figsize'] = (12, 9)  # Gráficos maiores
mpl.rcParams['figure.facecolor'] = 'white'
mpl.rcParams['axes.facecolor'] = '#f0f0f0'
mpl.rcParams['axes.grid'] = True
mpl.rcParams['grid.alpha'] = 0.3
mpl.rcParams['axes.labelsize'] = 16
mpl.rcParams['axes.titlesize'] = 20
mpl.rcParams['xtick.labelsize'] = 14
mpl.rcParams['ytick.labelsize'] = 14

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

def create_pie_chart_matplotlib(df_filtered):
    """Cria gráfico de pizza usando matplotlib - versão melhorada"""
    valores = [df_filtered['Cartão'].sum(), df_filtered['Dinheiro'].sum(), df_filtered['Pix'].sum()]
    labels = ['Cartão', 'Dinheiro', 'PIX']
    
    # Cores mais vibrantes e agradáveis
    cores = ['#3498db', '#f39c12', '#2ecc71']
    
    # Criar figura com tamanho maior
    plt.figure(figsize=(12, 9))
    
    # Criar o gráfico de pizza com efeito de explosão para destacar as fatias
    explode = (0.05, 0.05, 0.05)  # Destacar todas as fatias levemente
    wedges, texts, autotexts = plt.pie(
        valores, 
        labels=labels, 
        autopct='%1.1f%%', 
        startangle=90, 
        colors=cores,
        explode=explode,
        shadow=True,
        textprops={'fontsize': 16, 'fontweight': 'bold'},
        wedgeprops={'edgecolor': 'white', 'linewidth': 2}
    )
    
    # Personalizar os textos das porcentagens
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(14)
        autotext.set_fontweight('bold')
    
    plt.axis('equal')  # Manter o aspecto circular
    plt.title('Distribuição por Método de Pagamento', fontsize=24, pad=20, fontweight='bold')
    
    # Adicionar um círculo branco no meio para efeito de donut
    centre_circle = plt.Circle((0, 0), 0.5, fc='white')
    plt.gca().add_artist(centre_circle)
    
    # Adicionar legenda com valores absolutos
    total = sum(valores)
    legendas = [f'{l}: R$ {v:.2f} ({v/total*100:.1f}%)' for l, v in zip(labels, valores)]
    plt.legend(legendas, loc="center", bbox_to_anchor=(0.5, -0.1), fontsize=14)
    
    # Salvar em buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return buf

def create_bar_chart_matplotlib(df_filtered):
    """Cria gráfico de barras usando matplotlib - versão melhorada"""
    date_column = 'DataFormatada' if 'DataFormatada' in df_filtered.columns else 'Data'
    
    # Agrupar por data
    daily = df_filtered.groupby(date_column)[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
    
    # Cores bonitas para cada método de pagamento
    cores = ['#3498db', '#f39c12', '#2ecc71']
    
    # Configuração do gráfico com estilo moderno
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Posições das barras
    x = np.arange(len(daily[date_column]))
    width = 0.25
    
    # Plotar barras para cada método de pagamento
    rects1 = ax.bar(x - width, daily['Cartão'], width, label='Cartão', color=cores[0], 
                    edgecolor='white', linewidth=1.5, alpha=0.9)
    rects2 = ax.bar(x, daily['Dinheiro'], width, label='Dinheiro', color=cores[1],
                   edgecolor='white', linewidth=1.5, alpha=0.9)
    rects3 = ax.bar(x + width, daily['Pix'], width, label='PIX', color=cores[2],
                   edgecolor='white', linewidth=1.5, alpha=0.9)
    
    # Adicionar valor no topo de cada barra
    def add_value_labels(rects):
        for rect in rects:
            height = rect.get_height()
            if height > 0:  # Apenas mostrar valor se for maior que zero
                ax.text(rect.get_x() + rect.get_width()/2., height + 5,
                        f'R${height:.0f}', ha='center', va='bottom', 
                        fontsize=12, fontweight='bold')
    
    add_value_labels(rects1)
    add_value_labels(rects2)
    add_value_labels(rects3)
    
    # Configurações adicionais
    ax.set_ylabel('Valor (R$)', fontsize=18, fontweight='bold')
    ax.set_title('Vendas Diárias por Método de Pagamento', fontsize=22, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(daily[date_column], rotation=45, ha='right')
    
    # Adicionar grade apenas no eixo y para facilitar a leitura
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    # Remover bordas
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # Legenda melhorada
    ax.legend(fontsize=14, frameon=True, facecolor='white', edgecolor='#dddddd')
    
    fig.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return buf

def create_line_chart_matplotlib(df_filtered):
    """Cria gráfico de linha usando matplotlib - versão melhorada"""
    # Ordenar por data
    df_acum = df_filtered.sort_values('Data').copy()
    df_acum['Total Acumulado'] = df_acum['Total'].cumsum()
    
    # Configuração do gráfico
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Cores e estilo moderno
    cor_linha = '#3498db'
    cor_area = '#3498db'
    cor_ponto = '#2980b9'
    
    # Plotar linha com área sombreada abaixo e pontos destacados
    x = np.arange(len(df_acum['DataFormatada']))
    y = df_acum['Total Acumulado']
    
    # Adicionar área sombreada sob a linha
    ax.fill_between(x, y, alpha=0.3, color=cor_area)
    
    # Adicionar linha principal
    linha = ax.plot(x, y, marker='o', linestyle='-', linewidth=3, 
             markersize=10, color=cor_linha, markerfacecolor=cor_ponto, 
             markeredgecolor='white', markeredgewidth=2)
    
    # Adicionar rótulos nos pontos
    for i, valor in enumerate(y):
        ax.annotate(f'R${valor:.0f}', 
                   (x[i], valor), 
                   xytext=(0, 10),
                   textcoords='offset points',
                   ha='center',
                   fontsize=12,
                   fontweight='bold')
    
    # Configurações adicionais
    ax.set_ylabel('Capital Acumulado (R$)', fontsize=18, fontweight='bold')
    ax.set_title('Acúmulo de Capital ao Longo do Tempo', fontsize=22, fontweight='bold', pad=20)
    
    # Configurar eixo X com as datas formatadas
    ax.set_xticks(x)
    ax.set_xticklabels(df_acum['DataFormatada'], rotation=45, ha='right')
    
    # Adicionar grade para facilitar a leitura
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    # Remover bordas
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    fig.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return buf

def generate_pdf_report(df_filtered):
    """Função para gerar o relatório em PDF com gráficos em páginas separadas"""
    try:
        # Criar diretório temporário para os gráficos
        temp_dir = tempfile.mkdtemp()
        
        # Gerar gráficos usando matplotlib
        pie_chart_buf = create_pie_chart_matplotlib(df_filtered)
        bar_chart_buf = create_bar_chart_matplotlib(df_filtered)
        line_chart_buf = create_line_chart_matplotlib(df_filtered)
        
        # Salvar buffers como arquivos PNG
        pie_chart_path = os.path.join(temp_dir, "pie_chart.png")
        bar_chart_path = os.path.join(temp_dir, "bar_chart.png")
        line_chart_path = os.path.join(temp_dir, "line_chart.png")
        
        # Salvar os buffers como arquivos PNG
        with open(pie_chart_path, 'wb') as f:
            f.write(pie_chart_buf.getvalue())
        
        with open(bar_chart_path, 'wb') as f:
            f.write(bar_chart_buf.getvalue())
        
        with open(line_chart_path, 'wb') as f:
            f.write(line_chart_buf.getvalue())
        
        # Criar o PDF
        pdf_path = os.path.join(temp_dir, "analise_vendas.pdf")
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)  # Usando A4 para ter mais espaço
        elements = []
        
        # Criar estilos personalizados
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            alignment=1,  # Centralizado
            spaceAfter=30,
            textColor=colors.darkblue
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=20,
            alignment=1,  # Centralizado
            spaceAfter=20,
            textColor=colors.darkblue
        )
        
        # Página de capa com título
        elements.append(Spacer(1, 2*inch))  # Espaço no topo
        elements.append(Paragraph("Análise Detalhada de Vendas", title_style))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y')}", styles['Italic']))
        elements.append(PageBreak())  # Nova página após a capa
        
        # Página com tabela de dados
        elements.append(Paragraph("Resumo dos Dados", subtitle_style))
        elements.append(Spacer(1, 0.5*inch))
        
        # Tabela de resumo
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
        
        elements.append(PageBreak())  # Nova página antes do próximo gráfico
        
        # Página 1: Gráfico de Pizza
        if os.path.exists(pie_chart_path):
            elements.append(Paragraph("Distribuição por Método de Pagamento", subtitle_style))
            elements.append(Spacer(1, 0.5*inch))
            img = Image(pie_chart_path)
            img.drawHeight = 6*inch  # Altura fixa para garantir tamanho adequado
            img.drawWidth = 6*inch   # Largura fixa para garantir tamanho adequado
            elements.append(img)
            elements.append(PageBreak())  # Nova página após este gráfico
        
        # Página 2: Gráfico de Barras
        if os.path.exists(bar_chart_path):
            elements.append(Paragraph("Vendas Diárias por Método de Pagamento", subtitle_style))
            elements.append(Spacer(1, 0.5*inch))
            img = Image(bar_chart_path)
            img.drawHeight = 6*inch
            img.drawWidth = 8*inch
            elements.append(img)
            elements.append(PageBreak())  # Nova página após este gráfico
        
        # Página 3: Gráfico de Linha
        if os.path.exists(line_chart_path):
            elements.append(Paragraph("Acúmulo de Capital ao Longo do Tempo", subtitle_style))
            elements.append(Spacer(1, 0.5*inch))
            img = Image(line_chart_path)
            img.drawHeight = 6*inch
            img.drawWidth = 8*inch
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
        
        # Tentar remover o diretório temporário
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
                        x=alt.X('Data:T', title='Data'), 
                        y=alt.Y('Total Acumulado:Q', title='Capital Acumulado (R$)'),
                        tooltip=['DataFormatada', 'Total Acumulado']
                    ).properties(
                        width=600,
                        height=400,
                    )
                    st.altair_chart(acum_chart, use_container_width=True)

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