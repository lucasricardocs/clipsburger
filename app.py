from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import altair as alt
import pandas as pd

app = Flask(__name__)

# Função para inserir uma venda no banco de dados
def insert_venda(data, valor_cartao, valor_dinheiro, valor_pix):
    try:
        conn = sqlite3.connect('vendas.db')
        conn.execute('INSERT INTO vendas (data, valor_cartao, valor_dinheiro, valor_pix) VALUES (?, ?, ?, ?)', 
                     (data, valor_cartao, valor_dinheiro, valor_pix))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")

# Função para pegar os dados do banco de dados e convertê-los em um DataFrame
def get_vendas_data():
    conn = sqlite3.connect('vendas.db')
    query = 'SELECT * FROM vendas'
    df = pd.read_sql(query, conn)
    conn.close()
    return df

@app.route('/')
def index():
    # Pega os dados do banco de dados
    df = get_vendas_data()

    # Gráfico de vendas por forma de pagamento
    chart = alt.Chart(df).transform_fold(
        ['valor_cartao', 'valor_dinheiro', 'valor_pix'],
        as_=['Forma de Pagamento', 'Valor']
    ).mark_bar().encode(
        x='Forma de Pagamento:N',
        y='sum(Valor):Q',
        color='Forma de Pagamento:N',
        tooltip=['Forma de Pagamento:N', 'sum(Valor):Q']
    ).properties(
        title='Total de Vendas por Forma de Pagamento'
    )

    # Renderiza o template e passa o gráfico
    return render_template('index.html', chart=chart.to_html())

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        data = request.form['data']
        valor_cartao = request.form['valor_cartao']
        valor_dinheiro = request.form['valor_dinheiro']
        valor_pix = request.form['valor_pix']
        
        # Inserir os dados no banco de dados
        insert_venda(data, valor_cartao, valor_dinheiro, valor_pix)
        
        # Redirecionar para a página inicial
        return redirect(url_for('index'))
    
    return render_template('cadastrar.html')

if __name__ == '__main__':
    app.run(debug=True)
