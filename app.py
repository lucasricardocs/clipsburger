import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os
import io
import tempfile
from PIL import Image as PILImage, ImageDraw, ImageFont
import base64
import numpy as np
import matplotlib.pyplot as plt

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

def create_pie_chart_matplotlib(df_filtered):
    """Cria gráfico de pizza usando matplotlib"""
    valores = [df_filtered['Cartão'].sum(), df_filtered['Dinheiro'].sum(), df_filtered['Pix'].sum()]
    labels = ['Cartão', 'Dinheiro', 'PIX']
    cores = ['#1f77b4', '#ff7f0e', '#2ca02c']
    
    plt.figure(figsize=(8, 6))
    plt.pie(valores, labels=labels, autopct='%1.1f%%', startangle=90, colors=cores)
    plt.axis('equal')
    plt.title('Distribuição por Método de Pagamento')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close()
    
    return buf

def create_bar_chart_matplotlib(df_filtered):
    """Cria gráfico de barras usando matplotlib"""
    date_column = 'DataFormatada' if 'DataFormatada' in df_filtered.columns else 'Data'
    
    # Agrupar por data
    daily = df_filtered.groupby(date_column)[['Cartão', 'Dinheiro', 'Pix']].sum().reset_index()
    
    # Configuração do gráfico
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Posições das barras
    x = np.arange(len(daily[date_column]))
    width = 0.25
    
    # Plotar barras para cada método de pagamento
    rects1 = ax.bar(x - width, daily['Cartão'], width, label='Cartão')
    rects2 = ax.bar(x, daily['Dinheiro'], width, label='Dinheiro')
    rects3 = ax.bar(x + width, daily['Pix'], width, label='PIX')
    
    # Configurações adicionais
    ax.set_ylabel('Valor (R$)')
    ax.set_title('Vendas Diárias por Método de Pagamento')
    ax.set_xticks(x)
    ax.set_xticklabels(daily[date_column], rotation=45, ha='right')
    ax.legend()
    
    fig.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close()
    
    return buf

def create_line_chart_matplotlib(df_filtered):
    """Cria gráfico de linha usando matplotlib"""
    # Ordenar por data
    df_acum = df_filtered.sort_values('Data').copy()
    df_acum['Total Acumulado'] = df_acum['Total'].cumsum()
    
    # Configuração do gráfico
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plotar linha
    ax.plot(df_acum['DataFormatada'], df_acum['Total Acumulado'], marker='o', linestyle='-')
    
    # Configurações adicionais
    ax.set_ylabel('Capital Acumulado (R$)')
    ax.set_title('Acúmulo de Capital ao Longo do Tempo')
    plt.xticks(rotation=45, ha='right')
    
    fig.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close()
    
    return buf

def generate_pdf_report(df_filtered):
    """Função para gerar o relatório em PDF com gráficos"""
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
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Título e introdução
        elements.append(Paragraph("Análise Detalhada de Vendas", styles['Heading1']))
        elements.append(Spacer(1, 12))

        # Tabela de dados
        if 'DataFormatada' in df_filtered.columns:
            data_cols = ['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']
            table_data = [[col for col in data_cols]]  # Cabeçalho
            
            # Limitar a 20 linhas para evitar PDFs gigantes
            max_rows = min(20, len(df_filtered))
            for i in range(max_rows):
                row = df_filtered.iloc[i]
                table_data.append([str(row[col]) for col in data_cols])
            
            if len(df_filtered) > max_rows:
                table_data.append(['...e mais registros', '', '', '', ''])
        else:
            table_data = [df_filtered.columns.tolist()] + df_filtered.values.tolist()

        # Criar e estilizar a tabela
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

        # Adicionar gráficos ao PDF
        if os.path.exists(pie_chart_path):
            elements.append(Paragraph("Distribuição por Método de Pagamento", styles['Heading2']))
            elements.append(Image(pie_chart_path, width=450, height=300))
            elements.append(Spacer(1, 12))
        
        if os.path.exists(bar_chart_path):
            elements.append(Paragraph("Vendas Diárias por Método de Pagamento", styles['Heading2']))
            elements.append(Image(bar_chart_path, width=450, height=300))
            elements.append(Spacer(1, 12))
        
        if os.path.exists(line_chart_path):
            elements.append(Paragraph("Acúmulo de Capital ao Longo do Tempo", styles['Heading2']))
            elements.append(Image(line_chart_path, width=450, height=300))
        
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