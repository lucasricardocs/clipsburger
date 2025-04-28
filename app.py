import streamlit as st
import sqlite3
import altair as alt
import pandas as pd
from datetime import datetime, timedelta
import calendar

# Configuração inicial do banco de dados
def setup_database():
    conn = sqlite3.connect('vendas.db')
    conn.execute('''
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        valor_cartao REAL,
        valor_dinheiro REAL,
        valor_pix REAL
    )
    ''')
    conn.commit()
    conn.close()

# Função para inserir uma venda no banco de dados
def insert_venda(data, valor_cartao, valor_dinheiro, valor_pix):
    try:
        conn = sqlite3.connect('vendas.db')
        conn.execute('INSERT INTO vendas (data, valor_cartao, valor_dinheiro, valor_pix) VALUES (?, ?, ?, ?)', 
                     (data, valor_cartao, valor_dinheiro, valor_pix))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        st.error(f"Erro ao acessar o banco de dados: {e}")
        return False

# Função para pegar os dados do banco de dados e convertê-los em um DataFrame
def get_vendas_data():
    conn = sqlite3.connect('vendas.db')
    query = 'SELECT * FROM vendas'
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Convertendo a coluna de data para datetime
    df['data'] = pd.to_datetime(df['data'])
    
    # Adicionando colunas para facilitar filtragem
    df['ano'] = df['data'].dt.year
    df['mes'] = df['data'].dt.month
    df['mes_nome'] = df['data'].dt.month_name()
    df['dia'] = df['data'].dt.day
    df['dia_semana'] = df['data'].dt.day_name()
    
    # Adicionando coluna de valor total
    df['valor_total'] = df['valor_cartao'] + df['valor_dinheiro'] + df['valor_pix']
    
    return df

# Aplicação Streamlit
def main():
    setup_database()
    
    st.set_page_config(page_title="Dashboard de Vendas", layout="wide")
    st.title('Dashboard de Vendas')
    
    # Sidebar para filtros
    st.sidebar.header("Filtros")
    
    # Obter dados para popular os filtros
    df = get_vendas_data()
    
    if not df.empty:
        anos_disponiveis = sorted(df['ano'].unique())
        meses_disponiveis = range(1, 13)  # 1 a 12
        
        # Filtros de data
        ano_selecionado = st.sidebar.selectbox("Ano", anos_disponiveis, index=len(anos_disponiveis)-1 if anos_disponiveis else 0)
        mes_selecionado = st.sidebar.selectbox("Mês", meses_disponiveis, format_func=lambda x: calendar.month_name[x])
        
        # Aplicar filtros
        df_filtrado = df[(df['ano'] == ano_selecionado) & (df['mes'] == mes_selecionado)]
    else:
        df_filtrado = df
    
    # Layout usando abas
    tab1, tab2, tab3 = st.tabs(["Cadastro", "Resumo Mensal", "Análise Detalhada"])
    
    with tab1:
        st.header('Cadastrar Nova Venda')
        col1, col2 = st.columns(2)
        
        with col1:
            data = st.date_input("Data", value=datetime.now())
            valor_cartao = st.number_input("Valor Cartão (R$)", min_value=0.0, step=0.01, format="%.2f")
        
        with col2:
            valor_dinheiro = st.number_input("Valor Dinheiro (R$)", min_value=0.0, step=0.01, format="%.2f")
            valor_pix = st.number_input("Valor PIX (R$)", min_value=0.0, step=0.01, format="%.2f")
        
        total = valor_cartao + valor_dinheiro + valor_pix
        st.info(f"Valor Total: R$ {total:.2f}")
        
        if st.button('Cadastrar Venda', use_container_width=True):
            if data and valor_cartao >= 0 and valor_dinheiro >= 0 and valor_pix >= 0:
                if insert_venda(str(data), valor_cartao, valor_dinheiro, valor_pix):
                    st.success('Venda cadastrada com sucesso!')
                    st.rerun()
            else:
                st.error('Por favor, preencha todos os campos corretamente.')
    
    with tab2:
        if df_filtrado.empty:
            st.warning(f"Não há dados disponíveis para {calendar.month_name[mes_selecionado]} de {ano_selecionado}.")
        else:
            st.header(f'Resumo de Vendas - {calendar.month_name[mes_selecionado]} de {ano_selecionado}')
            
            # Estatísticas resumidas
            col1, col2, col3, col4 = st.columns(4)
            
            total_vendas = df_filtrado['valor_total'].sum()
            total_cartao = df_filtrado['valor_cartao'].sum()
            total_dinheiro = df_filtrado['valor_dinheiro'].sum()
            total_pix = df_filtrado['valor_pix'].sum()
            
            col1.metric("Total Vendas", f"R$ {total_vendas:.2f}")
            col2.metric("Total Cartão", f"R$ {total_cartao:.2f}")
            col3.metric("Total Dinheiro", f"R$ {total_dinheiro:.2f}")
            col4.metric("Total PIX", f"R$ {total_pix:.2f}")
            
            # Gráfico de vendas por forma de pagamento
            st.subheader('Vendas por Forma de Pagamento')
            
            # Preparando dados para o gráfico
            formas_pagamento = pd.DataFrame({
                'Forma': ['Cartão', 'Dinheiro', 'PIX'],
                'Valor': [total_cartao, total_dinheiro, total_pix]
            })
            
            grafico_pagamento = alt.Chart(formas_pagamento).mark_bar().encode(
                x=alt.X('Forma:N', title='Forma de Pagamento'),
                y=alt.Y('Valor:Q', title='Valor Total (R$)'),
                color=alt.Color('Forma:N', scale=alt.Scale(domain=['Cartão', 'Dinheiro', 'PIX'], 
                                                         range=['#FF9671', '#845EC2', '#00C9A7'])),
                tooltip=['Forma:N', alt.Tooltip('Valor:Q', format=',.2f')]
            ).properties(
                height=300
            )
            
            st.altair_chart(grafico_pagamento, use_container_width=True)
            
            # Gráfico de vendas diárias e acumuladas
            st.subheader('Vendas Diárias e Acumuladas')
            
            # Agrupando por dia
            df_diario = df_filtrado.groupby('data').agg({'valor_total': 'sum'}).reset_index()
            df_diario = df_diario.sort_values('data')
            
            # Calculando valores acumulados
            df_diario['valor_acumulado'] = df_diario['valor_total'].cumsum()
            
            # Convertendo para formato adequado para o Altair
            df_diario['dia'] = df_diario['data'].dt.day
            
            # Gráfico de barras para valores diários
            grafico_diario = alt.Chart(df_diario).mark_bar().encode(
                x=alt.X('dia:O', title='Dia do Mês'),
                y=alt.Y('valor_total:Q', title='Valor Diário (R$)'),
                tooltip=[
                    alt.Tooltip('dia:O', title='Dia'),
                    alt.Tooltip('valor_total:Q', title='Valor Diário', format=',.2f')
                ]
            ).properties(
                width=600,
                height=300
            )
            
            # Gráfico de linha para valores acumulados
            grafico_acumulado = alt.Chart(df_diario).mark_line(point=True, color='red').encode(
                x=alt.X('dia:O', title='Dia do Mês'),
                y=alt.Y('valor_acumulado:Q', title='Valor Acumulado (R$)'),
                tooltip=[
                    alt.Tooltip('dia:O', title='Dia'),
                    alt.Tooltip('valor_acumulado:Q', title='Valor Acumulado', format=',.2f')
                ]
            )
            
            # Combinando os dois gráficos
            grafico_combinado = alt.layer(grafico_diario, grafico_acumulado).resolve_scale(
                y='independent'
            ).properties(
                title=f'Vendas Diárias e Acumuladas - {calendar.month_name[mes_selecionado]} de {ano_selecionado}'
            )
            
            st.altair_chart(grafico_combinado, use_container_width=True)
            
    with tab3:
        if df_filtrado.empty:
            st.warning(f"Não há dados disponíveis para {calendar.month_name[mes_selecionado]} de {ano_selecionado}.")
        else:
            st.header(f'Análise Detalhada - {calendar.month_name[mes_selecionado]} de {ano_selecionado}')
            
            # Distribuição percentual por forma de pagamento
            st.subheader('Distribuição por Forma de Pagamento')
            
            # Calculando totais para o gráfico de pizza
            total = total_cartao + total_dinheiro + total_pix
            
            if total > 0:
                dados_pizza = pd.DataFrame({
                    'Forma': ['Cartão', 'Dinheiro', 'PIX'],
                    'Valor': [total_cartao, total_dinheiro, total_pix],
                    'Percentual': [total_cartao/total*100, total_dinheiro/total*100, total_pix/total*100]
                })
                
                grafico_pizza = alt.Chart(dados_pizza).mark_arc().encode(
                    theta=alt.Theta('Valor:Q'),
                    color=alt.Color('Forma:N', scale=alt.Scale(domain=['Cartão', 'Dinheiro', 'PIX'], 
                                                             range=['#FF9671', '#845EC2', '#00C9A7'])),
                    tooltip=[
                        alt.Tooltip('Forma:N'),
                        alt.Tooltip('Valor:Q', format=',.2f'),
                        alt.Tooltip('Percentual:Q', format='.1f', title='Percentual (%)')
                    ]
                ).properties(
                    width=400,
                    height=300,
                    title='Distribuição Percentual por Forma de Pagamento'
                )
                
                st.altair_chart(grafico_pizza, use_container_width=True)
            
            # Análise por dia da semana
            st.subheader('Vendas por Dia da Semana')
            
            df_dia_semana = df_filtrado.groupby('dia_semana').agg({'valor_total': 'sum'}).reset_index()
            
            # Obtendo a ordem correta dos dias da semana
            ordem_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            nomes_dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
            
            # Mapeando nomes em inglês para português
            df_dia_semana['dia_semana_pt'] = df_dia_semana['dia_semana'].map(dict(zip(ordem_dias, nomes_dias)))
            
            # Criando o gráfico de barras por dia da semana
            grafico_dia_semana = alt.Chart(df_dia_semana).mark_bar().encode(
                x=alt.X('dia_semana:N', 
                      sort=ordem_dias,
                      title='Dia da Semana',
                      axis=alt.Axis(labelExpr="datum.value == 'Monday' ? 'Segunda' : datum.value == 'Tuesday' ? 'Terça' : datum.value == 'Wednesday' ? 'Quarta' : datum.value == 'Thursday' ? 'Quinta' : datum.value == 'Friday' ? 'Sexta' : datum.value == 'Saturday' ? 'Sábado' : 'Domingo'")),
                y=alt.Y('valor_total:Q', title='Valor Total (R$)'),
                color=alt.condition(
                    alt.datum.dia_semana == 'Saturday' or alt.datum.dia_semana == 'Sunday',
                    alt.value('#FF9671'),
                    alt.value('#00C9A7')
                ),
                tooltip=[
                    alt.Tooltip('dia_semana_pt:N', title='Dia da Semana'),
                    alt.Tooltip('valor_total:Q', title='Valor Total', format=',.2f')
                ]
            ).properties(
                height=300,
                title='Vendas por Dia da Semana'
            )
            
            st.altair_chart(grafico_dia_semana, use_container_width=True)
            
            # Tabela com todos os registros do mês
            st.subheader('Registros de Vendas')
            
            colunas_exibir = ['data', 'valor_cartao', 'valor_dinheiro', 'valor_pix', 'valor_total']
            st.dataframe(
                df_filtrado[colunas_exibir].sort_values('data', ascending=False).reset_index(drop=True),
                column_config={
                    'data': st.column_config.DateColumn('Data', format="DD/MM/YYYY"),
                    'valor_cartao': st.column_config.NumberColumn('Cartão (R$)', format="R$ %.2f"),
                    'valor_dinheiro': st.column_config.NumberColumn('Dinheiro (R$)', format="R$ %.2f"),
                    'valor_pix': st.column_config.NumberColumn('PIX (R$)', format="R$ %.2f"),
                    'valor_total': st.column_config.NumberColumn('Total (R$)', format="R$ %.2f"),
                },
                use_container_width=True,
                hide_index=True
            )

if __name__ == "__main__":
    main()
