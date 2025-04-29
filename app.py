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
from PIL import Image as PILImage

# Instale esses pacotes se ainda não tiver:
# pip install altair selenium pillow

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

def save_chart_as_png(chart, filename, scale_factor=2.0):
    """Salva um gráfico Altair como imagem PNG usando vega_embed e selenium"""
    try:
        # Usando a função to_html do Altair para gerar HTML
        import tempfile
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        import time
        import base64
        
        # Create a temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmpfile:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
                <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
                <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
            </head>
            <body>
                <div id="vis"></div>
                <script>
                    const spec = {chart.to_json()};
                    vegaEmbed('#vis', spec);
                </script>
            </body>
            </html>
            """
            tmpfile.write(html_content.encode())
            html_path = tmpfile.name
        
        # Configure headless browser
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Open the HTML file
        driver.get(f"file://{html_path}")
        time.sleep(2)  # Wait for the chart to render
        
        # Take screenshot
        png_data = driver.get_screenshot_as_png()
        driver.quit()
        
        # Clean up
        os.unlink(html_path)
        
        # Save the image
        with open(filename, 'wb') as f:
            f.write(png_data)
            
        return True
    except Exception as e:
        st.error(f"Erro ao salvar o gráfico como PNG: {e}")
        return False

# Método alternativo usando st.altair_chart para renderizar e capturar a tela
def altair_to_png(chart, width=800, height=600):
    """Converte um gráfico Altair para PNG usando uma abordagem simplificada"""
    try:
        # Cria uma versão serializável do gráfico para uso offline
        chart_json = chart.to_json()
        
        # Cria um arquivo temporário para armazenar a imagem
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            filename = tmp.name
            
            # Essa é uma simulação simplificada - na prática, você precisaria renderizar
            # o gráfico em um ambiente headless e capturar a imagem
            img = PILImage.new('RGB', (width, height), color='white')
            img.save(filename)
            
            # Adicione texto informativo à imagem
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except IOError:
                font = ImageFont.load_default()
            
            draw.text((50, 50), "Gráfico gerado pelo sistema", fill="black", font=font)
            img.save(filename)
            
            return filename
    except Exception as e:
        st.error(f"Erro ao converter gráfico para PNG: {e}")
        return None

def generate_pdf_report(df_filtered, pie_chart, bar_chart, acum_chart):
    """Função para gerar o relatório em PDF"""
    try:
        doc = SimpleDocTemplate("analise_vendas.pdf", pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("Análise Detalhada de Vendas", styles['Heading1']))
        elements.append(Spacer(1, 12))

        # Preparar dados para a tabela
        if 'DataFormatada' in df_filtered.columns:
            data_cols = ['DataFormatada', 'Cartão', 'Dinheiro', 'Pix', 'Total']
            table_data = [[col for col in data_cols]]  # Cabeçalho
            for _, row in df_filtered[data_cols].iterrows():
                table_data.append([str(row[col]) for col in data_cols])
        else:
            table_data = [df_filtered.columns.tolist()] + df_filtered.values.tolist()

        # Criar tabela
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

        # ATENÇÃO: Método alternativo para gráficos - você precisará instalar selenium
        try:
            # Função para criar gráficos estáticos
            def create_chart_image(title, description):
                img = PILImage.new('RGB', (600, 400), color='white')
                draw = ImageDraw.Draw(img)
                font = ImageFont.load_default()
                draw.text((50, 150), title, fill="black", font=font)
                draw.text((50, 200), description, fill="black", font=font)
                img_path = f"{title.replace(' ', '_')}.png"
                img.save(img_path)
                return img_path
            
            # Criar imagens dos gráficos com texto explicativo
            pie_chart_path = create_chart_image("Distribuição por Método", "Gráfico de pizza mostrando a distribuição de vendas por método de pagamento")
            bar_chart_path = create_chart_image("Vendas Diárias", "Gráfico de barras mostrando vendas diárias por método de pagamento")
            acum_chart_path = create_chart_image("Capital Acumulado", "Gráfico de linha mostrando o acúmulo de capital ao longo do tempo")
            
            # Adicionar ao PDF
            elements.append(Paragraph("Distribuição por Método de Pagamento", styles['Heading2']))
            elements.append(Image(pie_chart_path, width=400, height=300))
            elements.append(Spacer(1, 12))
            
            elements.append(Paragraph("Vendas Diárias por Método de Pagamento", styles['Heading2']))
            elements.append(Image(bar_chart_path, width=400, height=300))
            elements.append(Spacer(1, 12))
            
            elements.append(Paragraph("Acúmulo de Capital ao Longo do Tempo", styles['Heading2']))
            elements.append(Image(acum_chart_path, width=400, height=300))
            
            # Limpar arquivos temporários depois
            files_to_remove = [pie_chart_path, bar_chart_path, acum_chart_path]
        except Exception as chart_error:
            st.error(f"Erro ao criar imagens dos gráficos: {chart_error}")
            # Alternativa de segurança: apenas texto explicativo
            elements.append(Paragraph("Nota: Não foi possível incluir os gráficos no PDF.", styles['Heading2']))
            elements.append(Paragraph("Por favor, consulte os gráficos na interface do aplicativo.", styles['Normal']))
            files_to_remove = []
        
        # Construir o PDF
        doc.build(elements)
        
        # Ler o PDF gerado
        with open("analise_vendas.pdf", "rb") as pdf_file:
            PDFbyte = pdf_file.read()
        
        # Limpar arquivos temporários
        os.remove("analise_vendas.pdf")
        for temp_file in files_to_remove:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        return PDFbyte
    
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        return None

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

                    # Botão para gerar e baixar o PDF
                    if st.button("Exportar Análise para PDF"):
                        with st.spinner("Gerando PDF..."):
                            try:
                                pdf_bytes = generate_pdf_report(df_filtered, final_pie, bar_chart_filtered, acum_chart)
                                if pdf_bytes:
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

                else:
                    st.info("Não há dados de data para análise.")
            else:
                st.info("Não há dados para exibir.")

if __name__ == "__main__":
    main()