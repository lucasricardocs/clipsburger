import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# Configuração da página
st.set_page_config(page_title="Sistema de Registro de Vendas", layout="centered")

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

def main():
    st.title("📊 Sistema de Registro de Vendas")
    tab1, tab2, tab3 = st.tabs(["Registrar Venda", "Análise Detalhada", "Estatística"])

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

    with tab2:
        st.header("Análise Detalhada de Vendas")
        
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
                    # Por padrão, selecionar o ano atual se disponível, senão todos os anos
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
                    
                    # Por padrão, selecionar apenas o mês atual se disponível
                    default_mes_opcao = [f"{current_month} - {datetime(2020, current_month, 1).strftime('%B')}"]
                    default_meses = [m for m in meses_opcoes if m.startswith(f"{current_month} -")]
                    
                    selected_meses_str = st.multiselect(
                        "Selecione o(s) Mês(es):",
                        options=meses_opcoes,
                        default=default_meses if default_meses else meses_opcoes
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
        st.header("📊 Estatísticas de Vendas")
        
        # Verifica se há dados disponíveis
        if not df_raw.empty and 'Data' in df.columns:
            # Aplica os filtros selecionados
            df_filtered = df[df['Ano'].isin(selected_anos)] if selected_anos else df
            df_filtered = df_filtered[df_filtered['Mês'].isin(selected_meses)] if selected_meses else df_filtered
            
            # Estatísticas Gerais
            st.subheader("💰 Resumo Financeiro")
            
            # Estatísticas básicas
            total_vendas = len(df_filtered)
            total_faturamento = df_filtered['Total'].sum()
            media_por_venda = df_filtered['Total'].mean() if total_vendas > 0 else 0
            maior_venda = df_filtered['Total'].max() if total_vendas > 0 else 0
            menor_venda = df_filtered['Total'].min() if total_vendas > 0 else 0
            
            # Exibição em linha única das métricas principais
            cols = st.columns(5)
            cols[0].metric("🔢 Total de Vendas", f"{total_vendas}")
            cols[1].metric("💵 Faturamento Total", f"R$ {total_faturamento:.2f}")
            cols[2].metric("📈 Média por Venda", f"R$ {media_por_venda:.2f}")
            cols[3].metric("⬆️ Maior Venda", f"R$ {maior_venda:.2f}")
            cols[4].metric("⬇️ Menor Venda", f"R$ {menor_venda:.2f}")
            
            # Métodos de pagamento
            st.markdown("---")
            st.subheader("💳 Métodos de Pagamento")
            
            cartao_total = df_filtered['Cartão'].sum()
            dinheiro_total = df_filtered['Dinheiro'].sum()
            pix_total = df_filtered['Pix'].sum()
            
            # Porcentagens
            total_pagamentos = cartao_total + dinheiro_total + pix_total
            cartao_pct = (cartao_total / total_pagamentos * 100) if total_pagamentos > 0 else 0
            dinheiro_pct = (dinheiro_total / total_pagamentos * 100) if total_pagamentos > 0 else 0
            pix_pct = (pix_total / total_pagamentos * 100) if total_pagamentos > 0 else 0
            
            # Mostra os valores e porcentagens em uma linha
            payment_cols = st.columns(3)
            payment_cols[0].markdown(f"**💳 Cartão:** R$ {cartao_total:.2f} ({cartao_pct:.1f}%)")
            payment_cols[1].markdown(f"**💵 Dinheiro:** R$ {dinheiro_total:.2f} ({dinheiro_pct:.1f}%)")
            payment_cols[2].markdown(f"**📱 PIX:** R$ {pix_total:.2f} ({pix_pct:.1f}%)")
            
            # Gráfico de pizza para métodos de pagamento
            payment_data = pd.DataFrame({
                'Método': ['Cartão', 'Dinheiro', 'PIX'],
                'Valor': [cartao_total, dinheiro_total, pix_total]
            })
            
            if total_pagamentos > 0:
                pie_chart = alt.Chart(payment_data).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta("Valor:Q", stack=True),
                    color=alt.Color("Método:N", legend=alt.Legend(title="Método")),
                    tooltip=["Método", "Valor"]
                ).properties(
                    height=300
                )
                text = pie_chart.mark_text(radius=120, size=16).encode(text="Valor:Q")
                st.altair_chart(pie_chart + text, use_container_width=True)
            
            # Análise Temporal
            st.markdown("---")
            st.subheader("📅 Análise Temporal")
            
            if total_vendas > 1:
                # Método de pagamento mais utilizado
                metodo_preferido = "Cartão" if cartao_total >= max(dinheiro_total, pix_total) else \
                                  "Dinheiro" if dinheiro_total >= max(cartao_total, pix_total) else "PIX"
                emoji_metodo = "💳" if metodo_preferido == "Cartão" else \
                              "💵" if metodo_preferido == "Dinheiro" else "📱"
                
                stats_cols = st.columns(3)
                stats_cols[0].markdown(f"**{emoji_metodo} Método Preferido:** {metodo_preferido}")
                
                # Média diária
                dias_distintos = df_filtered['Data'].nunique()
                media_diaria = total_faturamento / dias_distintos if dias_distintos > 0 else 0
                stats_cols[1].markdown(f"**📊 Média Diária:** R$ {media_diaria:.2f}")
                
                # Dia da semana com mais vendas
                if 'Data' in df_filtered.columns:
                    df_filtered['DiaSemana'] = df_filtered['Data'].dt.day_name()
                    dia_mais_vendas = df_filtered.groupby('DiaSemana')['Total'].sum().idxmax() \
                        if not df_filtered.empty else "N/A"
                    stats_cols[2].markdown(f"**📆 Dia com Mais Vendas:** {dia_mais_vendas}")
                
                # Gráfico de média por dia da semana
                if 'DiaSemana' in df_filtered.columns:
                    # Mapeando dias da semana para ordem correta
                    dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    dias_pt = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
                    mapa_dias = dict(zip(dias_ordem, dias_pt))
                    
                    vendas_por_dia = df_filtered.groupby('DiaSemana')['Total'].mean().reset_index()
                    
                    if not vendas_por_dia.empty:
                        vendas_por_dia['DiaSemana'] = vendas_por_dia['DiaSemana'].map(mapa_dias)
                        
                        chart = alt.Chart(vendas_por_dia).mark_bar().encode(
                            x=alt.X('DiaSemana:N', title='Dia da Semana', sort=dias_pt),
                            y=alt.Y('Total:Q', title='Média de Vendas (R$)'),
                            tooltip=['DiaSemana', 'Total']
                        ).properties(
                            title='Média de Vendas por Dia da Semana',
                            height=300
                        )
                        st.altair_chart(chart, use_container_width=True)
            
            # Análise mensal se houver dados suficientes
            if 'AnoMês' in df_filtered.columns and df_filtered['AnoMês'].nunique() > 1:
                st.subheader("📈 Tendência Mensal")
                
                # Agrupando por mês
                vendas_mensais = df_filtered.groupby('AnoMês')['Total'].sum().reset_index()
                
                # Calculando crescimento
                if len(vendas_mensais) >= 2:
                    ultimo_mes = vendas_mensais.iloc[-1]['Total']
                    penultimo_mes = vendas_mensais.iloc[-2]['Total']
                    variacao = ((ultimo_mes - penultimo_mes) / penultimo_mes * 100) if penultimo_mes > 0 else 0
                    
                    emoji_tendencia = "🚀" if variacao > 10 else "📈" if variacao > 0 else "📉" if variacao < 0 else "➡️"
                    st.markdown(f"**{emoji_tendencia} Variação Mensal:** {variacao:.1f}%")
                    
                    # Gráfico de tendência mensal
                    trend_chart = alt.Chart(vendas_mensais).mark_line(point=True).encode(
                        x=alt.X('AnoMês:N', title='Mês'),
                        y=alt.Y('Total:Q', title='Total de Vendas (R$)'),
                        tooltip=['AnoMês', 'Total']
                    ).properties(
                        title='Tendência Mensal de Vendas',
                        height=300
                    )
                    st.altair_chart(trend_chart, use_container_width=True)
            
            # Estatísticas Avançadas
            st.markdown("---")
            st.subheader("🔍 Estatísticas Avançadas")
            
            # Estatísticas de distribuição
            if total_vendas > 1:
                st.markdown("### 📊 Distribuição de Vendas")
                
                mediana = df_filtered['Total'].median()
                desvio_padrao = df_filtered['Total'].std()
                
                # Coeficiente de variação
                cv = (desvio_padrao / media_por_venda * 100) if media_por_venda > 0 else 0
                
                # Quartis para entender a distribuição
                q1 = df_filtered['Total'].quantile(0.25)
                q3 = df_filtered['Total'].quantile(0.75)
                iqr = q3 - q1
                
                # Mostra medidas de distribuição em uma linha
                dist_cols = st.columns(4)
                dist_cols[0].markdown(f"**↔️ Mediana:** R$ {mediana:.2f}")
                dist_cols[1].markdown(f"**🔄 Desvio Padrão:** R$ {desvio_padrao:.2f}")
                dist_cols[2].markdown(f"**📏 Coef. Variação:** {cv:.1f}%")
                dist_cols[3].markdown(f"**🔍 Amplitude Interquartil:** R$ {iqr:.2f}")
                
                # Histograma de distribuição dos valores de venda
                if len(df_filtered) >= 5:  # Pelo menos 5 registros para um histograma significativo
                    st.markdown("#### Histograma de Valores de Venda")
                    hist = alt.Chart(df_filtered).mark_bar().encode(
                        alt.X('Total:Q', bin=True, title='Valor da Venda (R$)'),
                        alt.Y('count()', title='Frequência')
                    ).properties(height=250)
                    st.altair_chart(hist, use_container_width=True)
            
            # Projeções e Metas
            st.markdown("---")
            st.subheader("🎯 Projeções e Metas")
            
            if total_vendas > 1:
                # Projeção simples baseada na média diária
                projecao_mensal = media_diaria * 30 if media_diaria > 0 else 0
                meta_mensal = projecao_mensal * 1.2
                meta_diaria = meta_mensal / 30
                
                # Mostrar projeções em linha
                proj_cols = st.columns(2)
                proj_cols[0].markdown(f"**📅 Projeção Mensal:** R$ {projecao_mensal:.2f}")
                proj_cols[1].markdown(f"**🌟 Meta Diária:** R$ {meta_diaria:.2f}")
                
                # Taxa de crescimento se houver dados suficientes
                if 'AnoMês' in df_filtered.columns and df_filtered['AnoMês'].nunique() > 1:
                    vendas_mensais = df_filtered.groupby('AnoMês')['Total'].sum().reset_index()
                    if len(vendas_mensais) >= 3:  # Pelo menos 3 meses para calcular taxa
                        # Calcula taxa média de crescimento mensal
                        taxas = []
                        for i in range(1, len(vendas_mensais)):
                            if vendas_mensais.iloc[i-1]['Total'] > 0:
                                taxa = (vendas_mensais.iloc[i]['Total'] / vendas_mensais.iloc[i-1]['Total']) - 1
                                taxas.append(taxa)
                        
                        if taxas:
                            taxa_media = sum(taxas) / len(taxas)
                            
                            # Previsão para próximo mês com base na taxa média
                            ultimo_mes = vendas_mensais.iloc[-1]['Total']
                            previsao_proximo = ultimo_mes * (1 + taxa_media)
                            
                            taxa_cols = st.columns(2)
                            taxa_cols[0].markdown(f"**📈 Taxa Média de Crescimento:** {taxa_media*100:.1f}%")
                            taxa_cols[1].markdown(f"**🔮 Previsão Próximo Mês:** R$ {previsao_proximo:.2f}")
            
            # Análise de Frequência 
            st.markdown("---")
            st.subheader("🗓️ Análise de Frequência")
            
            if 'Data' in df_filtered.columns and not df_filtered.empty:
                data_min = df_filtered['Data'].min()
                data_max = df_filtered['Data'].max()
                
                # Criar série com todas as datas no intervalo
                todas_datas = pd.date_range(start=data_min, end=data_max)
                datas_com_vendas = df_filtered['Data'].unique()
                
                # Quantos dias sem vendas
                dias_sem_vendas = len(todas_datas) - len(datas_com_vendas)
                
                freq_cols = st.columns(2)
                freq_cols[0].markdown(f"**⚠️ Dias Sem Vendas:** {dias_sem_vendas}")
                
                # Frequência média entre vendas (em dias)
                if len(datas_com_vendas) > 1:
                    dias_entre_vendas = (data_max - data_min).days / len(datas_com_vendas)
                    freq_cols[1].markdown(f"**⏱️ Intervalo Médio:** {dias_entre_vendas:.1f} dias")
                
                # Calcular dias da semana mais frequentes
                if len(df_filtered) > 3 and 'DiaSemana' in df_filtered.columns:  # Mais de 3 registros
                    freq_cols = st.columns(2)
                    freq_cols[0].markdown(f"**🏆 Dia Mais Frequente:** {dia_mais_vendas}")
                    
                    # Encontrar dia menos frequente
                    dia_menos_vendas = df_filtered.groupby('DiaSemana')['Total'].sum().idxmin() \
                        if not df_filtered.empty else "N/A"
                    freq_cols[1].markdown(f"**📉 Dia Menos Frequente:** {dia_menos_vendas}")
            
            # Sazonalidade Semanal
            st.markdown("---")
            st.subheader("📅 Sazonalidade Semanal")
            
            if 'Data' in df_filtered.columns and len(df_filtered) > 6:  # Pelo menos uma semana
                # Gráfico do volume de vendas por dia da semana
                if 'DiaSemana' in df_filtered.columns:
                    vendas_por_dia_semana = df_filtered.groupby('DiaSemana')['Total'].sum().reset_index()
                    
                    # Calcular porcentagem do total
                    total_semana = vendas_por_dia_semana['Total'].sum()
                    if total_semana > 0:
                        vendas_por_dia_semana['Porcentagem'] = vendas_por_dia_semana['Total'] / total_semana * 100
                        
                        # Traduzir dias para português e ordenar
                        dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                        dias_pt = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
                        mapa_dias = dict(zip(dias_ordem, dias_pt))
                        
                        if vendas_por_dia_semana['DiaSemana'].iloc[0] in mapa_dias:
                            vendas_por_dia_semana['DiaSemana'] = vendas_por_dia_semana['DiaSemana'].map(mapa_dias)
                        
                        # Criar gráfico de barras com porcentagem
                        chart_sazonalidade = alt.Chart(vendas_por_dia_semana).mark_bar().encode(
                            x=alt.X('DiaSemana:N', title='Dia da Semana', sort=dias_pt),
                            y=alt.Y('Porcentagem:Q', title='% do Volume Semanal'),
                            tooltip=['DiaSemana', 'Total', 'Porcentagem']
                        ).properties(
                            title='Distribuição Semanal de Vendas',
                            height=300
                        )
                        st.altair_chart(chart_sazonalidade, use_container_width=True)
                        
                        # Destacar dias mais importantes
                        melhor_dia = vendas_por_dia_semana.loc[vendas_por_dia_semana['Total'].idxmax()]
                        pior_dia = vendas_por_dia_semana.loc[vendas_por_dia_semana['Total'].idxmin()]
                        
                        best_worst_cols = st.columns(2)
                        best_worst_cols[0].markdown(f"**🔝 Melhor dia:** {melhor_dia['DiaSemana']} ({melhor_dia['Porcentagem']:.1f}% do total)")
                        best_worst_cols[1].markdown(f"**🔻 Pior dia:** {pior_dia['DiaSemana']} ({pior_dia['Porcentagem']:.1f}% do total)")
            
            # Evolução dos Métodos de Pagamento
            st.markdown("---")
            st.subheader("💰 Evolução dos Métodos de Pagamento")
            
            if 'AnoMês' in df_filtered.columns and df_filtered['AnoMês'].nunique() >= 2:
                # Agregar por mês e método de pagamento
                df_pagamentos = df_filtered.groupby(['AnoMês']).agg({
                    'Cartão': 'sum',
                    'Dinheiro': 'sum',
                    'Pix': 'sum'
                }).reset_index()
                
                # Preparar dados para o gráfico
                df_pagamentos_long = pd.melt(
                    df_pagamentos, 
                    id_vars=['AnoMês'],
                    value_vars=['Cartão', 'Dinheiro', 'Pix'],
                    var_name='Método',
                    value_name='Valor'
                )
                
                # Criar gráfico de linhas para evolução de métodos
                chart_evolucao = alt.Chart(df_pagamentos_long).mark_line(point=True).encode(
                    x=alt.X('AnoMês:N', title='Mês'),
                    y=alt.Y('Valor:Q', title='Valor (R$)'),
                    color=alt.Color('Método:N', title='Método de Pagamento'),
                    tooltip=['AnoMês', 'Método', 'Valor']
                ).properties(
                    title='Evolução dos Métodos de Pagamento',
                    height=300
                )
                st.altair_chart(chart_evolucao, use_container_width=True)
                
                # Identificar tendências na preferência de pagamento
                if df_pagamentos.shape[0] >= 3:  # Pelo menos 3 meses
                    primeiro_mes = df_pagamentos.iloc[0]
                    ultimo_mes = df_pagamentos.iloc[-1]
                    
                    # Calcular mudanças nas proporções
                    total_primeiro = primeiro_mes[['Cartão', 'Dinheiro', 'Pix']].sum()
                    total_ultimo = ultimo_mes[['Cartão', 'Dinheiro', 'Pix']].sum()
                    
                    if total_primeiro > 0 and total_ultimo > 0:
                        prop_cartao_inicio = primeiro_mes['Cartão'] / total_primeiro * 100
                        prop_cartao_fim = ultimo_mes['Cartão'] / total_ultimo * 100
                        
                        prop_dinheiro_inicio = primeiro_mes['Dinheiro'] / total_primeiro * 100
                        prop_dinheiro_fim = ultimo_mes['Dinheiro'] / total_ultimo * 100
                        
                        prop_pix_inicio = primeiro_mes['Pix'] / total_primeiro * 100
                        prop_pix_fim = ultimo_mes['Pix'] / total_ultimo * 100
                        
                        # Mostrar mudanças significativas
                        st.markdown("**📊 Mudanças na Preferência:**")
                        
                        delta_cartao = prop_cartao_fim - prop_cartao_inicio
                        delta_dinheiro = prop_dinheiro_fim - prop_dinheiro_inicio
                        delta_pix = prop_pix_fim - prop_pix_inicio
                        
                        pref_cols = st.columns(3)
                        pref_cols[0].markdown(f"💳 **Cartão:** {delta_cartao:+.1f}%")
                        pref_cols[1].markdown(f"💵 **Dinheiro:** {delta_dinheiro:+.1f}%")
                        pref_cols[2].markdown(f"📱 **PIX:** {delta_pix:+.1f}%")
            
            # Indicadores-chave de desempenho (KPIs)
            st.markdown("---")
            st.subheader("🎯 Indicadores-Chave de Desempenho (KPIs)")
            
            # Cálculo de indicadores se houver dados suficientes
            if not df_filtered.empty and len(df_filtered) > 1:
                # Filtrar para o último mês completo
                if 'AnoMês' in df_filtered.columns:
                    meses_ordenados = sorted(df_filtered['AnoMês'].unique())
                    
                    if len(meses_ordenados) >= 2:
                        ultimo_mes_completo = meses_ordenados[-1]
                        penultimo_mes = meses_ordenados[-2]
                        
                        df_ultimo_mes = df_filtered[df_filtered['AnoMês'] == ultimo_mes_completo]
                        df_penultimo_mes = df_filtered[df_filtered['AnoMês'] == penultimo_mes]
                        
                        # KPIs em 2 linhas de 2 métricas cada
                        kpi_row1 = st.columns(2)
                        kpi_row2 = st.columns(2)
                        
                        # KPI 1: Ticket Médio
                        ticket_atual = df_ultimo_mes['Total'].mean() if len(df_ultimo_mes) > 0 else 0
                        ticket_anterior = df_penultimo_mes['Total'].mean() if len(df_penultimo_mes) > 0 else 0
                        
                        delta_ticket = ((ticket_atual / ticket_anterior) - 1) * 100 if ticket_anterior > 0 else 0
                        
                        kpi_row1[0].metric(
                            label="🧾 Ticket Médio", 
                            value=f"R$ {ticket_atual:.2f}",
                            delta=f"{delta_ticket:.1f}%" if ticket_anterior > 0 else None
                        )
                        
                        # KPI 2: Volume de Vendas
                        volume_atual = len(df_ultimo_mes)
                        volume_anterior = len(df_penultimo_mes)
                        
                        delta_volume = ((volume_atual / volume_anterior) - 1) * 100 if volume_anterior > 0 else 0
                        
                        kpi_row1[1].metric(
                            label="📊 Volume de Vendas", 
                            value=f"{volume_atual}",
                            delta=f"{delta_volume:.1f}%" if volume_anterior > 0 else None
                        )
                        
                        # KPI 3: Taxa de Conversão Digital
                        pag_digital_atual = df_ultimo_mes['Cartão'].sum() + df_ultimo_mes['Pix'].sum()
                        total_atual = df_ultimo_mes['Total'].sum()
                        
                        pag_digital_anterior = df_penultimo_mes['Cartão'].sum() + df_penultimo_mes['Pix'].sum()
                        total_anterior = df_penultimo_mes['Total'].sum()
                        
                        taxa_digital_atual = (pag_digital_atual / total_atual * 100) if total_atual > 0 else 0
                        taxa_digital_anterior = (pag_digital_anterior / total_anterior * 100) if total_anterior > 0 else 0
                        
                        delta_digital = taxa_digital_atual - taxa_digital_anterior
                        
                        kpi_row2[0].metric(
                            label="💻 Taxa de Pagto. Digital", 
                            value=f"{taxa_digital_atual:.1f}%",
                            delta=f"{delta_digital:.1f}%" if total_anterior > 0 else None
                        )
                        
                        # KPI 4: Receita Total
                        receita_atual = df_ultimo_mes['Total'].sum()
                        receita_anterior = df_penultimo_mes['Total'].sum()
                        
                        delta_receita = ((receita_atual / receita_anterior) - 1) * 100 if receita_anterior > 0 else 0
                        
                        kpi_row2[1].metric(
                            label="💰 Receita Total", 
                            value=f"R$ {receita_atual:.2f}",
                            delta=f"{delta_receita:.1f}%" if receita_anterior > 0 else None
                        )
                else:
                    st.info("Dados temporais insuficientes para calcular KPIs comparativos. Registre vendas por pelo menos dois meses para visualizar estes indicadores.")
            
            # Análise de Pareto
            st.markdown("---")
            st.subheader("📈 Análise de Pareto")
            
            if not df_filtered.empty and len(df_filtered) >= 5:
                st.markdown("""
                A análise de Pareto, também conhecida como regra 80/20, identifica quais elementos são responsáveis 
                pela maior parte dos resultados. Abaixo, analisamos a concentração de suas vendas.
                """)
                
                # Análise por dia da semana
                if 'DiaSemana' in df_filtered.columns:
                    st.markdown("### 📆 Pareto por Dia da Semana")
                    
                    # Agrupa por dia da semana e calcula a soma
                    pareto_dia = df_filtered.groupby('DiaSemana')['Total'].sum().reset_index()
                    # Ordena em ordem decrescente
                    pareto_dia = pareto_dia.sort_values('Total', ascending=False)
                    # Calcula porcentagem do total
                    total_geral = pareto_dia['Total'].sum()
                    pareto_dia['Porcentagem'] = pareto_dia['Total'] / total_geral * 100
                    # Calcula porcentagem acumulada
                    pareto_dia['Acumulado'] = pareto_dia['Porcentagem'].cumsum()
                    
                    # Criar gráfico de Pareto
                    base = alt.Chart(pareto_dia).encode(
                        x=alt.X('DiaSemana:N', sort='-y', title='Dia da Semana')
                    )
                    
                    bars = base.mark_bar().encode(
                        y=alt.Y('Total:Q', title='Valor Total (R$)'),
                        tooltip=['DiaSemana', 'Total', 'Porcentagem', 'Acumulado']
                    )
                    
                    line = base.mark_line(color='red', strokeWidth=2).encode(
                        y=alt.Y('Acumulado:Q', title='% Acumulada', axis=alt.Axis(titleColor='red')),
                    )
                    
                    # Linha de 80%
                    rule = alt.Chart(pd.DataFrame({'y': [80]})).mark_rule(color='gray', strokeDash=[5, 5]).encode(y='y:Q')
                    
                    # Combinar no mesmo gráfico
                    pareto_chart = alt.layer(bars, line, rule).resolve_scale(
                        y=alt.ResolveScale('independent')
                    ).properties(
                        width=600,
                        height=350,
                        title='Análise de Pareto - Vendas por Dia da Semana'
                    )
                    
                    st.altair_chart(pareto_chart, use_container_width=True)
                    
                    # Encontrar dias que compõem 80% das vendas
                    dias_80pct = pareto_dia[pareto_dia['Acumulado'] <= 80]
                    if not dias_80pct.empty:
                        st.markdown(f"**🔍 {len(dias_80pct)} dia(s) da semana representam cerca de 80% do seu faturamento.**")
                        dias_80pct_list = ', '.join(dias_80pct['DiaSemana'].tolist())
                        st.markdown(f"**📊 Dias principais:** {dias_80pct_list}")
                
                # Análise por método de pagamento
                st.markdown("### 💸 Pareto por Método de Pagamento")
                
                # Calcula o total por método de pagamento
                pareto_metodos = pd.DataFrame({
                    'Método': ['Cartão', 'Dinheiro', 'PIX'],
                    'Total': [cartao_total, dinheiro_total, pix_total]
                })
                
                # Ordena em ordem decrescente
                pareto_metodos = pareto_metodos.sort_values('Total', ascending=False)
                
                # Calcula porcentagens e acumulado
                total_metodos = pareto_metodos['Total'].sum()
                pareto_metodos['Porcentagem'] = pareto_metodos['Total'] / total_metodos * 100
                pareto_metodos['Acumulado'] = pareto_metodos['Porcentagem'].cumsum()
                
                # Cria gráfico de Pareto
                base_metodo = alt.Chart(pareto_metodos).encode(
                    x=alt.X('Método:N', sort='-y', title='Método de Pagamento')
                )
                
                bars_metodo = base_metodo.mark_bar().encode(
                    y=alt.Y('Total:Q', title='Valor Total (R$)'),
                    tooltip=['Método', 'Total', 'Porcentagem', 'Acumulado']
                )
                
                line_metodo = base_metodo.mark_line(color='red', strokeWidth=2).encode(
                    y=alt.Y('Acumulado:Q', title='% Acumulada', axis=alt.Axis(titleColor='red')),
                )
                
                # Linha de 80%
                rule_metodo = alt.Chart(pd.DataFrame({'y': [80]})).mark_rule(color='gray', strokeDash=[5, 5]).encode(y='y:Q')
                
                # Combina os gráficos
                pareto_metodo_chart = alt.layer(bars_metodo, line_metodo, rule_metodo).resolve_scale(
                    y=alt.ResolveScale('independent')
                ).properties(
                    width=600,
                    height=350,
                    title='Análise de Pareto - Vendas por Método de Pagamento'
                )
                
                st.altair_chart(pareto_metodo_chart, use_container_width=True)
                
                # Identifica métodos que compõem 80% das vendas
                metodos_80pct = pareto_metodos[pareto_metodos['Acumulado'] <= 80]
                if not metodos_80pct.empty:
                    st.markdown(f"**🔍 {len(metodos_80pct)} método(s) representam cerca de 80% do seu faturamento.**")
                    metodos_list = ', '.join(metodos_80pct['Método'].tolist())
                    st.markdown(f"**💡 Métodos principais:** {metodos_list}")
                    st.markdown("""
                    **Dica:** Considere oferecer incentivos para os métodos predominantes ou 
                    analisar se há dependência excessiva em um único método.
                    """)
            
        else:
            st.warning("⚠️ Dados insuficientes para análises detalhadas. Verifique os filtros ou importe mais dados.")
            
if __name__ == "__main__":
    main()
