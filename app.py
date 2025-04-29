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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

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

def save_chart_as_png(chart, filename, width=800, height=600):
    """Salva um gráfico Altair como imagem PNG usando Selenium"""
    try:
        # Criar um arquivo HTML temporário com o gráfico
        temp_html = tempfile.NamedTemporaryFile(suffix='.html', delete=False)
        chart_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Chart</title>
            <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
            <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
            <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
            <style>
                body {{ margin: 0; overflow: hidden; }}
                #vis {{ width: {width}px; height: {height}px; }}
            </style>
        </head>
        <body>
            <div id="vis"></div>
            <script>
                const spec = {chart.to_json()};
                vegaEmbed('#vis', spec).then(result => {{
                    document.body.style.width = '{width}px';
                    document.body.style.height = '{height}px';
                }}).catch(console.error);
            </script>
        </body>
        </html>
        """
        
        with open(temp_html.name, 'w', encoding='utf-8') as f:
            f.write(chart_html)
        
        # Configurar o navegador headless
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'--window-size={width},{height}')
        
        # Iniciar o navegador e capturar a screenshot
        try:
            # Tente usar o ChromeDriverManager primeiro
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        except:
            # Fallback para o caminho padrão do Chrome
            driver = webdriver.Chrome(options=options)
        
        driver.get(f'file://{temp_html.name}')
        # Aguardar que o gráfico seja renderizado
        time.sleep(3)
        
        # Capturar a screenshot
        driver.save_screenshot(filename)
        driver.quit()
        
        # Limpar o arquivo temporário
        os.unlink(temp_html.name)
        
        return True
    except Exception as e:
        st.error(f"Erro ao salvar o gráfico como PNG: {e}")
        return False

def generate_pdf_report(df_filtered, pie_chart, bar_chart, acum_chart):
    """Função para gerar o relatório em PDF com gráficos"""
    try:
        # Criar diretório temporário para os gráficos
        temp_dir = tempfile.mkdtemp()
        
        # Caminhos dos arquivos para os gráficos
        pie_chart_path = os.path.join(temp_dir, "pie_chart.png")
        bar_chart_path = os.path.join(temp_dir, "bar_chart.png")
        acum_chart_path = os.path.join(temp_dir, "acum_chart.png")
        
        # Salvar os gráficos como PNG
        save_chart_as_png(pie_chart, pie_chart_path)
        save_chart_as_png(bar_chart, bar_chart_path)
        save_chart_as_png(acum_chart, acum_chart_path)
        
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

        # Adicionar gráficos ao PDF (verificando se existem)
        if os.path.exists(pie_chart_path):
            elements.append(Paragraph("Distribuição por Método de Pagamento", styles['Heading2']))
            elements.append(Image(pie_chart_path, width=450, height=300))
            elements.append(Spacer(1, 12))
        
        if os.path.exists(bar_chart_path):
            elements.append(Paragraph("Vendas Diárias por Método de Pagamento", styles['Heading2']))
            elements.append(Image(bar_chart_path, width=450, height=300))
            elements.append(Spacer(1, 12))
        
        if os.path.exists(acum_chart_path):
            elements.append(Paragraph("Acúmulo de Capital ao Longo do Tempo", styles['Heading2']))
            elements.append(Image(acum_chart_path, width=450, height=300))
        
        # Construir o PDF
        doc.build(elements)
        
        # Ler o PDF gerado
        with open(pdf_path, "rb") as pdf_file:
            PDFbyte = pdf_file.read()
        
        # Limpar arquivos temporários
        for file_path in [pie_chart_path, bar_chart_path, acum_chart_path, pdf_path]:
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
                                pdf_bytes = generate_pdf_report(df_filtered, final_pie, bar_chart_filtered, acum_chart)
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